from fastapi.testclient import TestClient
import pytest
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


def test_verified_catalog_contains_ministries_and_local_administration(client):
    response = client.get("/api/v1/institutions")

    assert response.status_code == 200
    institutions = response.json()
    assert len(institutions) == 120
    assert sum(item["institution_type"] == "ministry" for item in institutions) == 19
    assert sum(item["institution_type"] == "province" for item in institutions) == 4
    assert sum(item["institution_type"] == "city" for item in institutions) == 1
    assert sum(item["institution_type"] == "district" for item in institutions) == 30
    assert len({item["code"] for item in institutions}) == len(institutions)
    assert all(item["source_verified_on"] == "2026-09-30" for item in institutions)

    by_code = {item["code"]: item for item in institutions}
    assert by_code["LODA"]["parent_institution_id"] == by_code["MINALOC"]["id"]
    assert by_code["RIB"]["parent_institution_id"] == by_code["MINIJUST"]["id"]
    assert by_code["DIST-GASABO"]["parent_institution_id"] == by_code["COK"]["id"]
    assert by_code["RCS"]["parent_institution_id"] == by_code["MININTER"]["id"]
    assert by_code["RFL-FINANCE"]["short_name"] == "RFL"
    assert by_code["RFL-FORENSIC"]["short_name"] == "RFL"


def test_ministry_report_rolls_up_assets_from_descendants_once(client):
    institutions = client.get("/api/v1/institutions").json()
    by_code = {item["code"]: item for item in institutions}
    minaloc = by_code["MINALOC"]
    loda = by_code["LODA"]

    ministry_asset = client.post(
        "/api/v1/assets",
        params={"institution_id": minaloc["id"]},
        json={"asset_code": "MINALOC-001", "asset_type": "vehicle", "condition": "good"},
    )
    agency_asset = client.post(
        "/api/v1/assets",
        params={"institution_id": loda["id"]},
        json={"asset_code": "LODA-001", "asset_type": "vehicle", "condition": "poor"},
    )
    assert ministry_asset.status_code == agency_asset.status_code == 201

    direct = client.get(
        "/api/v1/reports/operations",
        params={"institution_id": minaloc["id"]},
    ).json()
    rolled_up = client.get(
        "/api/v1/reports/operations",
        params={"institution_id": minaloc["id"], "include_descendants": True},
    ).json()
    tree = client.get("/api/v1/reports/institution-tree").json()
    minaloc_row = next(
        row for row in tree["rows"] if row["institution"]["code"] == "MINALOC"
    )

    assert direct["total_assets"] == 1
    assert direct["included_institutions"] == 1
    assert rolled_up["scope_name"] == "Ministry of Local Government"
    assert rolled_up["total_assets"] == 2
    assert rolled_up["included_institutions"] == 8
    assert minaloc_row["descendant_count"] == 7
    assert minaloc_row["report"]["total_assets"] == 2
