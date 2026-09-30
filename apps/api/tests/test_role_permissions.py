import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from govasset_api.main import create_app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with TestClient(create_app(engine)) as test_client:
        yield test_client
    engine.dispose()


def set_claims(client: TestClient, monkeypatch, user_id: str, *, admin: bool = False):
    from govasset_api import auth

    monkeypatch.setenv("AUTH_REQUIRED", "true")
    claims = {
        "sub": user_id,
        "app_metadata": {
            "govasset_access": "approved",
            **({"govasset_role": "admin"} if admin else {}),
        },
    }
    client.app.dependency_overrides[auth.require_authenticated_user] = lambda: claims


def add_membership(
    client: TestClient,
    monkeypatch,
    *,
    role: str,
    user_id: str,
    institution_id: int,
):
    set_claims(client, monkeypatch, "global-admin", admin=True)
    response = client.post(
        "/api/v1/admin/memberships",
        json={
            "user_id": user_id,
            "institution_id": institution_id,
            "role": role,
        },
    )
    assert response.status_code == 201


def test_operational_roles_receive_only_their_capabilities(client, monkeypatch):
    set_claims(client, monkeypatch, "global-admin", admin=True)
    institution = client.post(
        "/api/v1/admin/institutions",
        json={
            "name": "Capability Test Institution",
            "code": "CAPABILITY-TEST",
            "institution_type": "agency",
        },
    ).json()
    asset = client.post(
        "/api/v1/assets",
        params={"institution_id": institution["id"]},
        json={"asset_code": "CAP-001", "asset_type": "vehicle"},
    ).json()

    technician_id = "b90365c9-3165-42ab-8021-6bdb7ea2a73c"
    add_membership(
        client,
        monkeypatch,
        role="technician",
        user_id=technician_id,
        institution_id=institution["id"],
    )
    set_claims(client, monkeypatch, technician_id)
    asset_write = client.post(
        "/api/v1/assets",
        json={"asset_code": "DENIED-TECH", "asset_type": "vehicle"},
    )
    maintenance_write = client.post(
        f"/api/v1/assets/{asset['id']}/maintenance",
        json={"event_date": "2026-09-30", "category": "repair"},
    )
    triage_run = client.post("/api/v1/triage-runs")

    assert asset_write.status_code == 403
    assert "asset:write" in asset_write.json()["detail"]
    assert maintenance_write.status_code == 201
    assert triage_run.status_code == 403
    assert "triage:run" in triage_run.json()["detail"]

    maintenance_officer_id = "4ca0c67b-d051-454f-99fc-b6ef398e8957"
    add_membership(
        client,
        monkeypatch,
        role="maintenance_officer",
        user_id=maintenance_officer_id,
        institution_id=institution["id"],
    )
    set_claims(client, monkeypatch, maintenance_officer_id)
    officer_asset_write = client.post(
        "/api/v1/assets",
        json={"asset_code": "DENIED-OFFICER", "asset_type": "vehicle"},
    )
    inspection_write = client.post(
        f"/api/v1/assets/{asset['id']}/inspections",
        json={"inspected_on": "2026-09-30", "condition": "fair"},
    )

    assert officer_asset_write.status_code == 403
    assert inspection_write.status_code == 201

    fleet_manager_id = "14eb13af-cd4f-43b2-939f-c22f168a05e8"
    add_membership(
        client,
        monkeypatch,
        role="fleet_manager",
        user_id=fleet_manager_id,
        institution_id=institution["id"],
    )
    set_claims(client, monkeypatch, fleet_manager_id)
    fleet_asset_write = client.post(
        "/api/v1/assets",
        json={"asset_code": "ALLOWED-FLEET", "asset_type": "vehicle"},
    )

    assert fleet_asset_write.status_code == 201
