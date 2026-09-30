from datetime import date
import os

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


def create_asset(client: TestClient, **overrides):
    data = {
        "asset_code": "FLEET-001",
        "asset_type": "vehicle",
        "condition": "good",
        "next_service_due": "2030-01-01",
    }
    data.update(overrides)
    return client.post("/api/v1/assets", json=data)


def set_claims(client: TestClient, monkeypatch, claims: dict):
    from govasset_api import auth

    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setattr("govasset_api.main.supabase_admin_configured", lambda: False)
    client.app.dependency_overrides[auth.require_authenticated_user] = lambda: claims


def register_institution(client: TestClient, code: str, parent_id: int | None = None):
    return client.post(
        "/api/v1/admin/institutions",
        json={
            "name": f"Institution {code}",
            "code": code,
            "institution_type": "agency",
            "parent_institution_id": parent_id,
        },
    )


def register_membership(client: TestClient, user_id: str, institution_id: int, role: str):
    return client.post(
        "/api/v1/admin/memberships",
        json={"user_id": user_id, "institution_id": institution_id, "role": role},
    )


def test_create_asset_and_reject_duplicate_code(client):
    first = create_asset(client)
    assert first.status_code == 201
    assert first.json()["asset_code"] == "FLEET-001"
    assert create_asset(client).status_code == 409


def test_update_asset_validates_partial_changes_and_preserves_history(client):
    asset = create_asset(
        client,
        asset_code="EDIT-001",
        last_service_date="2026-01-01",
        next_service_due="2026-06-01",
    ).json()

    updated = client.patch(
        f"/api/v1/assets/{asset['id']}",
        json={"asset_code": "EDIT-001A", "condition": "fair"},
    )
    assert updated.status_code == 200
    assert updated.json()["asset_code"] == "EDIT-001A"
    assert updated.json()["condition"] == "fair"
    assert updated.json()["last_service_date"] == "2026-01-01"
    assert updated.json()["next_service_due"] == "2026-06-01"

    invalid_dates = client.patch(
        f"/api/v1/assets/{asset['id']}",
        json={"next_service_due": "2025-12-31"},
    )
    assert invalid_dates.status_code == 422

    null_required = client.patch(
        f"/api/v1/assets/{asset['id']}",
        json={"asset_type": None},
    )
    assert null_required.status_code == 422

    duplicate = create_asset(client, asset_code="EDIT-002").json()
    conflict = client.patch(
        f"/api/v1/assets/{asset['id']}",
        json={"asset_code": duplicate["asset_code"]},
    )
    assert conflict.status_code == 409

    deactivate = client.patch(f"/api/v1/assets/{asset['id']}", json={"active": False})
    assert deactivate.status_code == 200
    assert deactivate.json()["active"] is False


def test_local_environment_file_loads_for_uvicorn_without_overriding_shell_values(
    monkeypatch, tmp_path
):
    from govasset_api.config import load_local_environment

    env_file = tmp_path / ".env.local"
    env_file.write_text(
        "SUPABASE_URL=https://local-project.supabase.co\n"
        "SUPABASE_SERVICE_ROLE_KEY=local-test-secret\n"
    )
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "shell-secret")

    load_local_environment(env_file)

    assert os.environ["SUPABASE_URL"] == "https://local-project.supabase.co"
    assert os.environ["SUPABASE_SERVICE_ROLE_KEY"] == "shell-secret"


def test_local_environment_file_is_not_loaded_on_render(monkeypatch, tmp_path):
    from govasset_api.config import load_local_environment

    env_file = tmp_path / ".env.local"
    env_file.write_text("SUPABASE_URL=https://local-project.supabase.co\n")
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-production")
    monkeypatch.delenv("SUPABASE_URL", raising=False)

    load_local_environment(env_file)

    assert "SUPABASE_URL" not in os.environ


def test_operations_report_exposes_data_gaps_and_operational_totals(client):
    create_asset(
        client,
        asset_code="DATA-001",
        condition="good",
        last_service_date="2026-01-01",
        next_service_due="2026-02-01",
    )
    inactive = create_asset(
        client,
        asset_code="DATA-002",
        active=False,
        condition="unknown",
    )
    asset_id = inactive.json()["id"]
    client.post(
        f"/api/v1/assets/{asset_id}/maintenance",
        json={
            "event_date": "2026-03-01",
            "category": "repair",
            "planned": False,
            "downtime_hours": 2.5,
        },
    )

    response = client.get("/api/v1/reports/operations?as_of=2026-09-30")

    assert response.status_code == 200
    report = response.json()
    assert report["total_assets"] == 2
    assert report["active_assets"] == 1
    assert report["inactive_assets"] == 1
    assert report["condition_unknown_assets"] == 1
    assert report["overdue_service_assets"] == 1
    assert report["unplanned_maintenance_records"] == 1
    assert report["downtime_hours_recorded"] == 2.5
    assert "maintenance costs" not in report["untracked_domains"]
    assert "parts used" in report["untracked_domains"]


def test_csv_exports_have_headers_and_prevent_spreadsheet_formula_injection(client):
    create_asset(
        client,
        asset_code="=HYPERLINK(\"https://example.org\")",
    )

    response = client.get("/api/v1/exports/assets.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="umutungo-assets.csv"' in response.headers["content-disposition"]
    assert "'=HYPERLINK" in response.text
    assert response.text.splitlines()[0].startswith(
        "institution_id,asset_code,asset_type"
    )


def test_csv_export_rejects_more_than_the_safe_row_limit(client, monkeypatch):
    from govasset_api import reporting

    monkeypatch.setattr(reporting, "MAX_EXPORT_ROWS", 1)
    create_asset(client, asset_code="EXPORT-001")
    create_asset(client, asset_code="EXPORT-002")

    response = client.get("/api/v1/exports/assets.csv")

    assert response.status_code == 413
    assert "Narrow the dataset" in response.json()["detail"]


def test_cors_allows_local_dev_ports_and_project_previews_but_not_other_projects(
    monkeypatch,
):
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    monkeypatch.delenv("CORS_ORIGIN_REGEX", raising=False)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    try:
        with TestClient(create_app(engine)) as test_client:
            local_dev_port = test_client.options(
                "/api/v1/assets",
                headers={
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization",
                },
            )
            preview = test_client.options(
                "/api/v1/assets",
                headers={
                    "Origin": "https://umutungo-preview-123-etienne0114s-projects.vercel.app",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization",
                },
            )
            rejected = test_client.options(
                "/api/v1/assets",
                headers={
                    "Origin": "https://other-project-etienne0114s-projects.vercel.app",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization",
                },
            )
    finally:
        engine.dispose()

    assert local_dev_port.status_code == 200
    assert local_dev_port.headers["access-control-allow-origin"] == "http://localhost:3001"
    assert preview.status_code == 200
    assert (
        preview.headers["access-control-allow-origin"]
        == "https://umutungo-preview-123-etienne0114s-projects.vercel.app"
    )
    assert "access-control-allow-origin" not in rejected.headers


def test_asset_dates_must_be_ordered(client):
    response = create_asset(
        client,
        last_service_date="2025-01-01",
        next_service_due="2024-12-31",
    )
    assert response.status_code == 422


def test_maintenance_record_is_validated_and_listed(client):
    asset = create_asset(client).json()
    response = client.post(
        f"/api/v1/assets/{asset['id']}/maintenance",
        json={
            "event_date": "2026-01-15",
            "category": "inspection",
            "planned": True,
            "downtime_hours": 2.5,
        },
    )
    assert response.status_code == 201
    assert response.json()["asset_id"] == asset["id"]
    assert len(client.get(f"/api/v1/assets/{asset['id']}/maintenance").json()) == 1


def test_inspection_updates_asset_condition_and_preserves_history(client):
    asset = create_asset(client, condition="unknown", next_service_due=None).json()

    current = client.post(
        f"/api/v1/assets/{asset['id']}/inspections",
        json={
            "inspected_on": "2026-09-20",
            "condition": "poor",
            "observations": "Visible wear recorded during inspection.",
        },
    )
    older = client.post(
        f"/api/v1/assets/{asset['id']}/inspections",
        json={"inspected_on": "2026-08-01", "condition": "good"},
    )

    assert current.status_code == older.status_code == 201
    updated_asset = client.get(f"/api/v1/assets/{asset['id']}").json()
    assert updated_asset["condition"] == "poor"
    assert updated_asset["last_inspected_on"] == "2026-09-20"
    inspections = client.get(f"/api/v1/assets/{asset['id']}/inspections").json()
    assert [inspection["inspected_on"] for inspection in inspections] == [
        "2026-09-20",
        "2026-08-01",
    ]


def test_inspection_rejects_unknown_condition_and_future_date(client):
    asset = create_asset(client).json()
    base_path = f"/api/v1/assets/{asset['id']}/inspections"

    unknown = client.post(
        base_path,
        json={"inspected_on": "2026-09-20", "condition": "unknown"},
    )
    future = client.post(
        base_path,
        json={"inspected_on": "2999-01-01", "condition": "good"},
    )

    assert unknown.status_code == 422
    assert future.status_code == 422


@pytest.mark.parametrize(
    ("asset_data", "expected"),
    [
        ({"condition": "critical"}, "critical"),
        ({"condition": "poor", "next_service_due": "2030-01-01"}, "high"),
        ({"condition": "good", "next_service_due": "2026-06-20"}, "high"),
        ({"condition": "fair", "next_service_due": "2030-01-01"}, "medium"),
        ({"condition": "good", "next_service_due": "2030-01-01"}, "low"),
        ({"condition": "unknown", "next_service_due": None}, "insufficient_data"),
    ],
)
def test_triage_is_explainable_and_ordered(client, asset_data, expected):
    code = f"FLEET-{expected}-{asset_data['condition']}"
    create_asset(client, asset_code=code, **asset_data)

    response = client.get("/api/v1/triage", params={"as_of": date(2026, 9, 29).isoformat()})

    assert response.status_code == 200
    item = next(entry for entry in response.json() if entry["asset"]["asset_code"] == code)
    assert item["risk_level"] == expected
    assert item["reasons"]
    assert item["rule_version"] == "maintenance-triage-v1"
    assert item["recommended_action"]


def test_triage_orders_critical_before_medium(client):
    create_asset(client, asset_code="FLEET-MED", condition="fair")
    create_asset(client, asset_code="FLEET-CRIT", condition="critical")

    response = client.get("/api/v1/triage", params={"as_of": "2026-09-29"})

    assert [item["asset"]["asset_code"] for item in response.json()] == [
        "FLEET-CRIT",
        "FLEET-MED",
    ]


def test_triage_can_filter_and_excludes_inactive_assets(client):
    create_asset(client, asset_code="FLEET-A", condition="critical")
    create_asset(client, asset_code="FLEET-B", active=False, condition="good")

    response = client.get("/api/v1/triage", params={"risk_level": "critical"})

    assert response.status_code == 200
    assert [item["asset"]["asset_code"] for item in response.json()] == ["FLEET-A"]


def test_missing_asset_returns_not_found(client):
    response = client.post(
        "/api/v1/assets/999/maintenance",
        json={"event_date": "2026-09-29", "category": "repair"},
    )
    assert response.status_code == 404


def test_triage_run_persists_versioned_recommendations_and_asset_snapshot(client):
    asset = create_asset(
        client,
        asset_code="FLEET-SNAPSHOT",
        condition="fair",
        next_service_due="2026-10-05",
    ).json()

    run_response = client.post("/api/v1/triage-runs", params={"as_of": "2026-09-29"})

    assert run_response.status_code == 201
    run = run_response.json()
    assert run["recommendation_count"] == 1
    assert run["rule_version"] == "maintenance-triage-v1"
    assert client.get(f"/api/v1/triage-runs/{run['id']}").json() == run

    recommendations = client.get(
        "/api/v1/recommendations",
        params={"run_id": run["id"], "risk_level": "medium"},
    ).json()
    assert len(recommendations) == 1
    recommendation = recommendations[0]
    assert recommendation["asset_id"] == asset["id"]
    assert recommendation["asset_snapshot"]["condition"] == "fair"
    assert recommendation["evaluated_on"] == "2026-09-29"

    inspection = client.post(
        f"/api/v1/assets/{asset['id']}/inspections",
        json={"inspected_on": date.today().isoformat(), "condition": "critical"},
    )
    assert inspection.status_code == 201
    assert client.get(f"/api/v1/assets/{asset['id']}").json()["condition"] == "critical"
    assert (
        client.get(f"/api/v1/recommendations/{recommendation['id']}").json()["asset_snapshot"][
            "condition"
        ]
        == "fair"
    )

    filtered = client.get(
        "/api/v1/recommendations",
        params={"run_id": run["id"], "risk_level": "critical"},
    )
    assert filtered.json() == []


def test_recommendation_review_and_outcome_are_append_only_events(client):
    create_asset(client, asset_code="FLEET-FEEDBACK", condition="poor")
    run = client.post("/api/v1/triage-runs", params={"as_of": "2026-09-29"}).json()
    recommendation = client.get(
        "/api/v1/recommendations", params={"run_id": run["id"]}
    ).json()[0]
    recommendation_id = recommendation["id"]

    review = client.post(
        f"/api/v1/recommendations/{recommendation_id}/events",
        json={
            "event_type": "review",
            "disposition": "accepted",
            "reason": "Inspection capacity available this week.",
        },
    )
    outcome = client.post(
        f"/api/v1/recommendations/{recommendation_id}/events",
        json={
            "event_type": "outcome",
            "outcome": "unscheduled_repair",
            "occurred_on": "2026-10-02",
            "reason": "Inspection confirmed repair was required.",
        },
    )

    assert review.status_code == 201
    assert outcome.status_code == 201
    events = client.get(f"/api/v1/recommendations/{recommendation_id}/events").json()
    assert [event["event_type"] for event in events] == ["review", "outcome"]
    assert events[0]["disposition"] == "accepted"
    assert events[1]["outcome"] == "unscheduled_repair"
    assert client.get(f"/api/v1/recommendations/{recommendation_id}").json() == recommendation


@pytest.mark.parametrize(
    "payload",
    [
        {"event_type": "review", "disposition": "accepted"},
        {
            "event_type": "review",
            "disposition": "rejected",
            "reason": "Not relevant.",
            "outcome": "no_maintenance_found",
        },
        {"event_type": "outcome", "outcome": "unscheduled_repair"},
    ],
)
def test_invalid_recommendation_events_are_rejected(client, payload):
    create_asset(client, condition="critical")
    run = client.post("/api/v1/triage-runs").json()
    recommendation = client.get(
        "/api/v1/recommendations", params={"run_id": run["id"]}
    ).json()[0]

    response = client.post(
        f"/api/v1/recommendations/{recommendation['id']}/events",
        json=payload,
    )

    assert response.status_code == 422


def test_empty_triage_run_and_missing_recommendation(client):
    run = client.post("/api/v1/triage-runs", params={"as_of": "2026-09-29"}).json()
    assert run["recommendation_count"] == 0
    assert client.get("/api/v1/recommendations/999").status_code == 404
    listed = client.get("/api/v1/triage-runs").json()
    assert listed[0] == run
    assert client.get("/api/v1/triage-runs", params={"limit": 0}).status_code == 422


def test_startup_adds_inspection_date_column_to_legacy_database(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "false")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE assets (
                id INTEGER PRIMARY KEY,
                institution_id INTEGER,
                asset_code VARCHAR(80) NOT NULL UNIQUE,
                asset_type VARCHAR(80) NOT NULL,
                make VARCHAR(80),
                model VARCHAR(80),
                acquisition_date DATE,
                last_service_date DATE,
                next_service_due DATE,
                condition VARCHAR(20) NOT NULL,
                active BOOLEAN NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )
        connection.exec_driver_sql(
            """
            INSERT INTO assets (
                id, asset_code, asset_type, condition, active, created_at
            ) VALUES (1, 'LEGACY-001', 'vehicle', 'fair', 1, '2026-09-01 00:00:00')
            """
        )

    with TestClient(create_app(engine)) as test_client:
        response = test_client.get("/api/v1/assets/1")

    assert response.status_code == 200
    assert response.json()["asset_code"] == "LEGACY-001"
    assert response.json()["condition"] == "fair"
    assert response.json()["last_inspected_on"] is None
    engine.dispose()


def test_frontend_cors_preflight_allows_local_next_app(client):
    response = client.options(
        "/api/v1/assets",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_frontend_cors_rejects_unconfigured_origin(client):
    response = client.options(
        "/api/v1/assets",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_hosted_api_requires_supabase_authentication(client, monkeypatch):
    from govasset_api import auth

    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")

    unauthenticated = client.get("/api/v1/assets")
    assert unauthenticated.status_code == 401

    monkeypatch.setattr(
        auth,
        "verify_supabase_token",
        lambda _token, _url: {
            "sub": "user-123",
            "role": "authenticated",
            "app_metadata": {"govasset_access": "approved"},
        },
    )
    authenticated = client.get(
        "/api/v1/assets",
        headers={"Authorization": "Bearer valid-test-token"},
    )
    assert authenticated.status_code == 403
    assert "no active institution membership" in authenticated.json()["detail"]


def test_authentication_fails_closed_without_project_url(client, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.delenv("SUPABASE_URL", raising=False)

    response = client.get("/api/v1/assets")

    assert response.status_code == 503


def test_authenticated_but_unapproved_user_is_forbidden(client, monkeypatch):
    from govasset_api import auth

    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")

    def reject_unapproved_user(_token, _url):
        raise auth.UserAccessNotApproved

    monkeypatch.setattr(
        auth,
        "verify_supabase_token",
        reject_unapproved_user,
    )

    response = client.get("/api/v1/assets", headers={"Authorization": "Bearer test-token"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Your account is awaiting administrator approval."


def test_supabase_token_validation_checks_signature_issuer_and_audience(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    from govasset_api import auth

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    project_url = "https://example.supabase.co"
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "user-123",
        "role": "authenticated",
        "aud": "authenticated",
        "iss": f"{project_url}/auth/v1",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "app_metadata": {"govasset_access": "approved"},
    }
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})

    class TestJwksClient:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(auth, "_jwks_client", lambda _url: TestJwksClient())

    assert auth.verify_supabase_token(token, project_url)["sub"] == "user-123"
    with pytest.raises(jwt.InvalidIssuerError):
        auth.verify_supabase_token(token, "https://other.supabase.co")

    bad_audience_token = jwt.encode(
        {**claims, "aud": "anon"},
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    with pytest.raises(jwt.InvalidAudienceError):
        auth.verify_supabase_token(bad_audience_token, project_url)


def test_valid_supabase_token_requires_admin_approval(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    from govasset_api import auth

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    project_url = "https://example.supabase.co"
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "user-123",
        "role": "authenticated",
        "aud": "authenticated",
        "iss": f"{project_url}/auth/v1",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "app_metadata": {},
    }
    token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})

    class TestJwksClient:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=private_key.public_key())

    monkeypatch.setattr(auth, "_jwks_client", lambda _url: TestJwksClient())

    with pytest.raises(auth.UserAccessNotApproved):
        auth.verify_supabase_token(token, project_url)


def test_admin_user_listing_requires_admin_role(client, monkeypatch):
    from govasset_api import auth

    client.app.dependency_overrides[auth.require_authenticated_user] = lambda: {
        "sub": "user-123",
        "app_metadata": {"govasset_access": "approved"},
    }
    monkeypatch.setattr(
        "govasset_api.main.list_supabase_users_page",
        lambda **_kwargs: pytest.fail(
            "Non-admin users must not reach the Supabase admin API."
        ),
    )

    response = client.get("/api/v1/admin/users")

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator access is required."


def test_admin_can_list_users_and_approve_confirmed_accounts(client, monkeypatch):
    from govasset_api import auth

    client.app.dependency_overrides[auth.require_authenticated_user] = lambda: {
        "sub": "admin-123",
        "app_metadata": {
            "govasset_access": "approved",
            "govasset_role": "admin",
        },
    }
    user = {
        "id": "245f7915-1c43-43d9-a63e-e40131024452",
        "email": "staff@example.org",
        "created_at": "2026-09-20T10:00:00Z",
        "email_confirmed_at": "2026-09-20T10:02:00Z",
        "last_sign_in_at": None,
        "app_metadata": {"provider": "email", "govasset_access": "pending"},
        "user_metadata": {"full_name": "Staff Member", "organization": "Health"},
    }
    requested_page = {}

    def list_users_page(*, page, per_page):
        requested_page.update(page=page, per_page=per_page)
        return [user]

    monkeypatch.setattr("govasset_api.main.list_supabase_users_page", list_users_page)
    monkeypatch.setattr("govasset_api.main.get_supabase_user", lambda _user_id: user)

    def update_user_app_metadata(user_id, metadata):
        assert user_id == "245f7915-1c43-43d9-a63e-e40131024452"
        assert metadata == {
            "provider": "email",
            "govasset_access": "approved",
        }
        return {**user, "app_metadata": metadata}

    monkeypatch.setattr(
        "govasset_api.main.update_supabase_user_app_metadata",
        update_user_app_metadata,
    )

    listed = client.get("/api/v1/admin/users?page=2&per_page=50")
    updated = client.put(
        "/api/v1/admin/users/245f7915-1c43-43d9-a63e-e40131024452/access",
        json={"approved": True},
    )

    assert listed.status_code == 200
    assert requested_page == {"page": 2, "per_page": 50}
    assert listed.json()[0]["access"] == "pending"
    assert listed.json()[0]["role"] == "user"
    assert listed.json()[0]["full_name"] == "Staff Member"
    assert "user_metadata" not in listed.json()[0]
    assert updated.status_code == 200
    assert updated.json()["access"] == "approved"


def test_admin_access_endpoint_fails_if_supabase_does_not_apply_change(
    client, monkeypatch
):
    from govasset_api import auth

    client.app.dependency_overrides[auth.require_authenticated_user] = lambda: {
        "sub": "admin-123",
        "app_metadata": {
            "govasset_access": "approved",
            "govasset_role": "admin",
        },
    }
    monkeypatch.setattr(
        "govasset_api.main.get_supabase_user",
        lambda user_id: {
            "id": user_id,
            "email": "staff@example.org",
            "created_at": "2026-09-20T10:00:00Z",
            "email_confirmed_at": "2026-09-20T10:02:00Z",
            "app_metadata": {"govasset_access": "pending"},
        },
    )
    monkeypatch.setattr(
        "govasset_api.main.update_supabase_user_app_metadata",
        lambda user_id, _metadata: {
            "id": user_id,
            "email": "staff@example.org",
            "created_at": "2026-09-20T10:00:00Z",
            "email_confirmed_at": "2026-09-20T10:02:00Z",
            "app_metadata": {"govasset_access": "pending"},
        },
    )

    response = client.put(
        "/api/v1/admin/users/245f7915-1c43-43d9-a63e-e40131024452/access",
        json={"approved": True},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Supabase did not confirm the requested account access change."
    )


def test_admin_cannot_revoke_own_access(client):
    from govasset_api import auth

    client.app.dependency_overrides[auth.require_authenticated_user] = lambda: {
        "sub": "4ccf50b3-128c-4703-b9ed-e349f7433c24",
        "app_metadata": {
            "govasset_access": "approved",
            "govasset_role": "admin",
        },
    }

    response = client.put(
        "/api/v1/admin/users/4ccf50b3-128c-4703-b9ed-e349f7433c24/access",
        json={"approved": False},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Administrators cannot revoke their own access."


def test_admin_cannot_approve_unconfirmed_account(client, monkeypatch):
    from govasset_api import auth

    client.app.dependency_overrides[auth.require_authenticated_user] = lambda: {
        "sub": "4ccf50b3-128c-4703-b9ed-e349f7433c24",
        "app_metadata": {
            "govasset_access": "approved",
            "govasset_role": "admin",
        },
    }
    monkeypatch.setattr(
        "govasset_api.main.get_supabase_user",
        lambda _user_id: {
            "id": "245f7915-1c43-43d9-a63e-e40131024452",
            "email": "unconfirmed@example.org",
            "email_confirmed_at": None,
        },
    )
    monkeypatch.setattr(
        "govasset_api.main.update_supabase_user_app_metadata",
        lambda *_args: pytest.fail("Unconfirmed users cannot be approved."),
    )

    response = client.put(
        "/api/v1/admin/users/245f7915-1c43-43d9-a63e-e40131024452/access",
        json={"approved": True},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Users must confirm their email before approval."


def test_admin_user_pagination_rejects_out_of_range_page_size(client, monkeypatch):
    from govasset_api import auth

    client.app.dependency_overrides[auth.require_authenticated_user] = lambda: {
        "sub": "admin-123",
        "app_metadata": {
            "govasset_access": "approved",
            "govasset_role": "admin",
        },
    }
    monkeypatch.setattr(
        "govasset_api.main.list_supabase_users_page",
        lambda **_kwargs: pytest.fail("Invalid page size must not call Supabase."),
    )

    response = client.get("/api/v1/admin/users?page=1&per_page=101")

    assert response.status_code == 422


def test_supabase_admin_user_pages_request_the_requested_page(monkeypatch):
    from govasset_api import supabase_admin

    requested = []
    monkeypatch.setattr(
        supabase_admin,
        "_admin_request",
        lambda path: requested.append(path) or {"users": [{"id": "page-user"}]},
    )

    users = supabase_admin.list_supabase_users_page(page=3, per_page=25)

    assert users == [{"id": "page-user"}]
    assert requested == ["users?page=3&per_page=25"]


def test_supabase_admin_page_size_is_bounded():
    from govasset_api import supabase_admin

    with pytest.raises(ValueError, match="cannot exceed 100"):
        supabase_admin.list_supabase_users_page(page=1, per_page=101)


def test_institution_hierarchy_and_membership_administration(client, monkeypatch):
    set_claims(
        client,
        monkeypatch,
        {"sub": "global-admin", "app_metadata": {"govasset_role": "admin"}},
    )
    parent = register_institution(client, "ROOT")
    assert parent.status_code == 201
    child = register_institution(client, "CHILD", parent.json()["id"])
    assert child.status_code == 201
    assert child.json()["parent_institution_id"] == parent.json()["id"]

    assert register_institution(client, "ROOT").status_code == 409
    assert (
        client.post(
            "/api/v1/admin/institutions",
            json={
                "name": "Missing parent",
                "code": "MISSING-PARENT",
                "institution_type": "agency",
                "parent_institution_id": 9999,
            },
        ).status_code
        == 422
    )
    cycle = client.patch(
        f"/api/v1/admin/institutions/{parent.json()['id']}",
        json={"parent_institution_id": child.json()["id"]},
    )
    assert cycle.status_code == 422
    self_parent = client.patch(
        f"/api/v1/admin/institutions/{parent.json()['id']}",
        json={"parent_institution_id": parent.json()["id"]},
    )
    assert self_parent.status_code == 422

    user_id = "8bb5e1ce-2620-4b79-91ce-a38c8b8799d1"
    created = register_membership(client, user_id, child.json()["id"], "viewer")
    assert created.status_code == 201
    assert created.json()["role"] == "viewer"
    set_claims(
        client,
        monkeypatch,
        {"sub": user_id, "app_metadata": {"govasset_access": "approved"}},
    )
    available = client.get("/api/v1/institutions")
    assert available.status_code == 200
    assert available.json()[0]["membership_role"] == "viewer"
    set_claims(
        client,
        monkeypatch,
        {"sub": "global-admin", "app_metadata": {"govasset_role": "admin"}},
    )
    assert register_membership(client, user_id, child.json()["id"], "driver").status_code == 409
    updated = client.patch(
        f"/api/v1/admin/memberships/{user_id}/{child.json()['id']}",
        json={"role": "auditor"},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "auditor"
    set_claims(
        client,
        monkeypatch,
        {"sub": user_id, "app_metadata": {"govasset_access": "approved"}},
    )
    assert client.get("/api/v1/institutions").json()[0]["membership_role"] == "auditor"
    set_claims(
        client,
        monkeypatch,
        {"sub": "global-admin", "app_metadata": {"govasset_role": "admin"}},
    )
    assert client.delete(
        f"/api/v1/admin/memberships/{user_id}/{child.json()['id']}"
    ).status_code == 204
    assert client.get("/api/v1/admin/memberships").json() == []


def test_system_admin_can_sync_the_verified_rwanda_institution_catalog(client, monkeypatch):
    set_claims(
        client,
        monkeypatch,
        {"sub": "global-admin", "app_metadata": {"govasset_role": "admin"}},
    )
    first = client.post("/api/v1/admin/institutions/sync-official-catalog")
    assert first.status_code == 200
    summary = first.json()
    assert summary["total"] > 0
    assert summary["created"] + summary["updated"] + summary["unchanged"] == summary["total"]
    assert summary["verified_on"] == "2026-09-30"
    assert summary["source_urls"]

    second = client.post("/api/v1/admin/institutions/sync-official-catalog")
    assert second.status_code == 200
    assert second.json()["created"] == 0
    assert second.json()["updated"] == 0
    assert second.json()["unchanged"] == summary["total"]

    institutions = client.get("/api/v1/admin/institutions").json()
    ministry = next(item for item in institutions if item["code"] == "MINALOC")
    district = next(item for item in institutions if item["code"] == "DIST-GASABO")
    assert ministry["is_official"] is True
    assert ministry["source_url"] in summary["source_urls"]
    assert district["institution_type"] == "district"
    assert district["parent_institution_id"] is not None

    set_claims(
        client,
        monkeypatch,
        {"sub": "non-admin", "app_metadata": {"govasset_access": "approved"}},
    )
    assert (
        client.post("/api/v1/admin/institutions/sync-official-catalog").status_code
        == 403
    )


def test_membership_assignment_verifies_supabase_approval_when_admin_api_is_configured(
    client, monkeypatch
):
    set_claims(
        client,
        monkeypatch,
        {"sub": "global-admin", "app_metadata": {"govasset_role": "admin"}},
    )
    institution = register_institution(client, "VERIFIED-USER").json()
    user_id = "efee9e51-3313-447f-8582-1e9261246c39"
    monkeypatch.setattr("govasset_api.main.supabase_admin_configured", lambda: True)
    monkeypatch.setattr(
        "govasset_api.main.get_supabase_user",
        lambda requested_id: {
            "id": requested_id,
            "app_metadata": {"govasset_access": "pending"},
        },
    )
    pending = register_membership(client, user_id, institution["id"], "viewer")
    assert pending.status_code == 409
    assert "approved Supabase user" in pending.json()["detail"]

    monkeypatch.setattr(
        "govasset_api.main.get_supabase_user",
        lambda requested_id: {
            "id": requested_id,
            "app_metadata": {"govasset_access": "approved"},
        },
    )
    assert register_membership(client, user_id, institution["id"], "viewer").status_code == 201


def test_tenant_data_isolation_for_assets_reports_exports_triage_and_events(
    client, monkeypatch
):
    set_claims(
        client,
        monkeypatch,
        {"sub": "global-admin", "app_metadata": {"govasset_role": "admin"}},
    )
    first = register_institution(client, "TENANT-A").json()
    second = register_institution(client, "TENANT-B").json()
    user_a = "597b5925-ea3b-4195-aaf0-01f63230127c"
    user_b = "137227bc-1e70-4f67-87fb-a0a0f92078b6"
    assert register_membership(client, user_a, first["id"], "fleet_manager").status_code == 201
    assert register_membership(client, user_b, second["id"], "fleet_manager").status_code == 201

    unassigned = create_asset(client, asset_code="LEGACY-NULL", condition="poor")
    assert unassigned.status_code == 422
    asset_a = client.post(
        f"/api/v1/assets?institution_id={first['id']}",
        json={
            "asset_code": "TENANT-A-ASSET",
            "asset_type": "vehicle",
            "condition": "critical",
            "institution_id": second["id"],
        },
    )
    assert asset_a.status_code == 201
    asset_a = asset_a.json()
    asset_b = client.post(
        f"/api/v1/assets?institution_id={second['id']}",
        json={"asset_code": "TENANT-B-ASSET", "asset_type": "vehicle", "condition": "poor"},
    ).json()
    same_code_other_tenant = client.post(
        f"/api/v1/assets?institution_id={second['id']}",
        json={"asset_code": "TENANT-A-ASSET", "asset_type": "vehicle"},
    )
    assert same_code_other_tenant.status_code == 201
    assert client.post(
        f"/api/v1/assets/{asset_b['id']}/maintenance",
        json={
            "event_date": "2026-09-29",
            "category": "tenant-b-private",
            "description": "TENANT-B-MAINTENANCE",
        },
    ).status_code == 201
    assert client.post(
        f"/api/v1/assets/{asset_b['id']}/inspections",
        json={
            "inspected_on": "2026-09-29",
            "condition": "poor",
            "observations": "TENANT-B-INSPECTION",
        },
    ).status_code == 201
    assert client.post(
        f"/api/v1/assets?institution_id={second['id']}",
        json={"asset_code": "TENANT-A-ASSET", "asset_type": "vehicle"},
    ).status_code == 409

    run_a = client.post("/api/v1/triage-runs?institution_id={}".format(first["id"])).json()
    run_b = client.post("/api/v1/triage-runs?institution_id={}".format(second["id"])).json()
    recommendations_b = client.get(
        "/api/v1/recommendations", params={"run_id": run_b["id"]}
    ).json()
    rec_b = recommendations_b[0]
    assert client.post(
        f"/api/v1/recommendations/{rec_b['id']}/events",
        json={
            "event_type": "review",
            "disposition": "accepted",
            "reason": "Reviewed by the system administrator.",
        },
    ).status_code == 201

    set_claims(
        client,
        monkeypatch,
        {"sub": user_a, "app_metadata": {"govasset_access": "approved"}},
    )
    assert client.get("/api/v1/institutions").json()[0]["id"] == first["id"]
    assert [row["asset_code"] for row in client.get("/api/v1/assets").json()] == [
        "TENANT-A-ASSET"
    ]
    assert client.get("/api/v1/assets", params={"institution_id": second["id"]}).status_code == 403
    assert client.get(f"/api/v1/assets/{asset_b['id']}").status_code == 404
    assert client.patch(
        f"/api/v1/assets/{asset_b['id']}",
        json={"asset_code": "CROSS-TENANT"},
    ).status_code == 404
    assert client.post(
        f"/api/v1/assets/{asset_b['id']}/maintenance",
        json={"event_date": "2026-09-30", "category": "repair"},
    ).status_code == 404
    assert client.post(
        f"/api/v1/assets/{asset_b['id']}/inspections",
        json={"inspected_on": "2026-09-30", "condition": "good"},
    ).status_code == 404
    assert client.get(f"/api/v1/assets/{asset_b['id']}/maintenance").status_code == 404
    assert client.get(f"/api/v1/assets/{asset_b['id']}/inspections").status_code == 404

    report = client.get("/api/v1/reports/operations").json()
    assert report["total_assets"] == 1
    assert report["scope_institution_id"] == first["id"]
    assert report["scope_name"] == "Institution TENANT-A"
    assert report["maintenance_records"] == 0
    assert report["inspection_records"] == 0
    assert "LEGACY-NULL" not in client.get("/api/v1/exports/assets.csv").text
    assert "TENANT-B-ASSET" not in client.get("/api/v1/exports/assets.csv").text
    assert "TENANT-B-MAINTENANCE" not in client.get(
        "/api/v1/exports/maintenance.csv"
    ).text
    assert "TENANT-B-INSPECTION" not in client.get(
        "/api/v1/exports/inspections.csv"
    ).text
    assert "LEGACY-NULL" not in client.get("/api/v1/triage").text
    runs = client.get("/api/v1/triage-runs").json()
    assert [row["id"] for row in runs] == [run_a["id"]]
    assert client.get(f"/api/v1/triage-runs/{run_b['id']}").status_code == 404
    tenant_recommendations = client.get("/api/v1/recommendations").json()
    assert len(tenant_recommendations) == 1
    assert tenant_recommendations[0]["run_id"] == run_a["id"]
    assert client.get(f"/api/v1/recommendations/{rec_b['id']}").status_code == 404
    assert client.get(
        f"/api/v1/recommendations/{rec_b['id']}/events"
    ).status_code == 404
    assert client.post(
        f"/api/v1/recommendations/{rec_b['id']}/events",
        json={
            "event_type": "review",
            "disposition": "accepted",
            "reason": "Must not write across institution boundaries.",
        },
    ).status_code == 404

    set_claims(
        client,
        monkeypatch,
        {"sub": "global-admin", "app_metadata": {"govasset_role": "admin"}},
    )
    assert len(client.get("/api/v1/assets").json()) == 3


def test_membership_required_and_read_only_roles_cannot_mutate(client, monkeypatch):
    set_claims(
        client,
        monkeypatch,
        {"sub": "user-without-membership", "app_metadata": {"govasset_access": "approved"}},
    )
    response = client.get("/api/v1/assets")
    assert response.status_code == 403
    assert "no active institution membership" in response.json()["detail"]

    set_claims(
        client,
        monkeypatch,
        {"sub": "global-admin", "app_metadata": {"govasset_role": "admin"}},
    )
    institution = register_institution(client, "VIEW-ONLY").json()
    user_id = "bf32c33d-22fb-4fd5-93f8-4f2d9cd94bf5"
    assert register_membership(client, user_id, institution["id"], "viewer").status_code == 201
    asset = client.post(
        f"/api/v1/assets?institution_id={institution['id']}",
        json={"asset_code": "VIEW-ASSET", "asset_type": "vehicle"},
    ).json()

    set_claims(
        client,
        monkeypatch,
        {"sub": user_id, "app_metadata": {"govasset_access": "approved"}},
    )
    denied_asset = client.post(
        "/api/v1/assets",
        json={
            "asset_code": "FORGED",
            "asset_type": "vehicle",
            "institution_id": institution["id"],
        },
    )
    assert denied_asset.status_code == 403
    assert "read-only" in denied_asset.json()["detail"]
    assert client.patch(
        f"/api/v1/assets/{asset['id']}",
        json={"asset_code": "FORGED"},
    ).status_code == 403
    denied_maintenance = client.post(
        f"/api/v1/assets/{asset['id']}/maintenance",
        json={"event_date": "2026-09-30", "category": "repair"},
    )
    assert denied_maintenance.status_code == 403
    assert client.get("/api/v1/admin/institutions").status_code == 403


def test_tenant_migration_preserves_unassigned_legacy_rows_and_guards_cycles():
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    engine = create_engine("sqlite://")
    migration_dir = Path(__file__).parents[1] / "migrations" / "versions"
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            for filename in (
                "1ded697490a9_create_asset_maintenance_tables.py",
                "5c27b67a1f4d_add_institution_tenancy.py",
            ):
                path = migration_dir / filename
                spec = spec_from_file_location(path.stem, path)
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                if filename.startswith("1ded"):
                    module.upgrade()
                    connection.execute(
                        text(
                            "INSERT INTO assets (asset_code, asset_type, condition, active, "
                            "created_at) VALUES ('LEGACY-PRESERVED', 'vehicle', 'fair', 1, "
                            "'2026-09-01 00:00:00')"
                        )
                    )
                else:
                    module.upgrade()
        legacy = connection.execute(
            text("SELECT asset_code, institution_id FROM assets")
        ).one()
        assert legacy == ("LEGACY-PRESERVED", None)

        connection.execute(
            text(
                "INSERT INTO institutions (id, name, code, institution_type, active) "
                "VALUES (1, 'Parent', 'PARENT', 'agency', 1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO institutions (id, name, code, institution_type, active, "
                "parent_institution_id) VALUES (2, 'Child', 'CHILD', 'agency', 1, 1)"
            )
        )
        with pytest.raises(Exception, match="institution hierarchy cycle"):
            connection.execute(
                text("UPDATE institutions SET parent_institution_id=2 WHERE id=1")
            )
    engine.dispose()
