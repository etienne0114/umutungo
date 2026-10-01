"""Tests for the deterministic risk engine and the triage analytics endpoints."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from govasset_api.main import create_app
from govasset_api.models import Asset
from govasset_api.services.institution_analysis import build_institution_assessments
from govasset_api.services.risk_engine import (
    MaintenanceAggregate,
    assess_asset,
    compute_asset_age_years,
)

AS_OF = date(2026, 1, 1)


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


def _asset(**kwargs) -> Asset:
    defaults = {
        "asset_code": "TEST-1",
        "asset_type": "Vehicle",
        "condition": "good",
        "criticality": "standard",
    }
    defaults.update(kwargs)
    return Asset(**defaults)


def test_asset_age_prefers_acquisition_then_manufacture_year():
    acquired = _asset(acquisition_date=date(2016, 1, 1))
    assert compute_asset_age_years(acquired, AS_OF) == pytest.approx(10.0, abs=0.05)

    manufactured = _asset(acquisition_date=None, manufacture_year=2016)
    assert compute_asset_age_years(manufactured, AS_OF) == pytest.approx(9.5, abs=0.1)

    unknown = _asset(acquisition_date=None, manufacture_year=None)
    assert compute_asset_age_years(unknown, AS_OF) is None


def test_missing_history_is_not_treated_as_maximum_risk():
    asset = _asset(condition="good", acquisition_date=date(2024, 1, 1))
    assessment = assess_asset(asset, MaintenanceAggregate(), AS_OF)
    assert assessment.risk_level == "low"
    assert assessment.has_maintenance_history is False
    assert assessment.risk_score is not None
    assert assessment.risk_score < 30


def test_insufficient_data_when_nothing_to_score():
    asset = _asset(condition="unknown", acquisition_date=None, manufacture_year=None)
    assessment = assess_asset(asset, MaintenanceAggregate(), AS_OF)
    assert assessment.risk_level == "insufficient_data"
    assert assessment.risk_score is None
    assert assessment.recommendation


def test_condition_only_asset_renormalises_to_medium():
    asset = _asset(condition="fair", acquisition_date=None)
    assessment = assess_asset(asset, MaintenanceAggregate(), AS_OF)
    assert assessment.risk_score == 35
    assert assessment.risk_level == "medium"


def test_aged_high_frequency_asset_is_replacement_candidate():
    old = _asset(condition="poor", acquisition_date=date(2014, 1, 1), criticality="important")
    aggregate = MaintenanceAggregate(
        maintenance_count=20,
        last_event_date=date(2025, 12, 8),
        recent_window_count=5,
        recent_repeat_count=3,
        unplanned_count=10,
        total_downtime_hours=150.0,
        downtime_records=20,
    )
    assessment = assess_asset(old, aggregate, AS_OF)

    assert assessment.maintenance_frequency == pytest.approx(1.67, abs=0.02)
    assert assessment.days_since_last_maintenance == 24
    assert assessment.replacement_candidate is True
    assert assessment.risk_level in ("high", "critical")
    assert assessment.maintenance_priority in ("high", "urgent")
    assert assessment.evidence
    assert any("replacement" in reason.lower() for reason in assessment.reasons)

    new = _asset(condition="good", acquisition_date=date(2024, 1, 1))
    new_assessment = assess_asset(new, MaintenanceAggregate(maintenance_count=1), AS_OF)
    assert new_assessment.risk_score < assessment.risk_score
    assert new_assessment.replacement_candidate is False


def test_institution_priority_uses_normalised_ratios_not_totals():
    assessments = [
        assess_asset(
            _asset(asset_code=f"A{i}", condition="poor", acquisition_date=date(2013, 1, 1)),
            MaintenanceAggregate(maintenance_count=12, last_event_date=date(2025, 11, 1)),
            AS_OF,
        )
        for i in range(4)
    ]
    for item in assessments:
        item.institution_id = 1

    single = assess_asset(
        _asset(asset_code="B0", condition="good", acquisition_date=date(2024, 1, 1)),
        MaintenanceAggregate(),
        AS_OF,
    )
    single.institution_id = 2

    institutions_by_id = {1: ("High burden", "HB"), 2: ("Low burden", "LB")}
    rows = build_institution_assessments(
        assessments + [single], institutions_by_id, AS_OF
    )
    by_id = {row.institution_id: row for row in rows}

    assert by_id[1].total_assets == 4
    assert by_id[1].high_risk_ratio > by_id[2].high_risk_ratio
    assert by_id[1].priority_score > by_id[2].priority_score
    assert rows[0].institution_id == 1
    assert by_id[1].reasons


def _seed_fleet(client: TestClient) -> None:
    client.post(
        "/api/v1/assets",
        json={
            "asset_code": "AGED-1",
            "asset_type": "Vehicle",
            "condition": "poor",
            "criticality": "important",
            "acquisition_date": "2014-01-01",
            "next_service_due": "2025-12-01",
        },
    )
    client.post(
        "/api/v1/assets",
        json={
            "asset_code": "NEW-1",
            "asset_type": "Vehicle",
            "condition": "good",
            "acquisition_date": "2024-01-01",
            "next_service_due": "2027-01-01",
        },
    )
    aged = client.get("/api/v1/assets").json()
    aged_id = next(asset["id"] for asset in aged if asset["asset_code"] == "AGED-1")
    for index, event_date in enumerate(
        ["2025-06-01", "2025-09-01", "2025-11-15", "2025-12-10"]
    ):
        client.post(
            f"/api/v1/assets/{aged_id}/maintenance",
            json={
                "event_date": event_date,
                "category": "repair",
                "planned": index % 2 == 0,
                "downtime_hours": 20.0,
            },
        )


def test_analysis_preview_and_saved_run_reproduce(client):
    _seed_fleet(client)

    preview = client.get("/api/v1/triage/analysis", params={"as_of": "2026-01-01"})
    assert preview.status_code == 200
    analysis = preview.json()
    assert analysis["persisted_run_id"] is None
    assert analysis["summary"]["total_assets"] == 2
    assert analysis["summary"]["maintenance_events"] == 4
    assert analysis["assets"][0]["risk_score"] >= analysis["assets"][-1]["risk_score"]

    save = client.post("/api/v1/triage-runs", params={"as_of": "2026-01-01"})
    assert save.status_code == 201
    run = save.json()
    assert run["total_assets"] == 2
    assert run["engine_version"] == "maintenance-risk-engine-v1"

    saved = client.get(f"/api/v1/triage-runs/{run['id']}/analysis").json()
    assert saved["persisted_run_id"] == run["id"]
    assert saved["summary"]["total_assets"] == analysis["summary"]["total_assets"]
    assert saved["summary"]["high_risk_assets"] == analysis["summary"]["high_risk_assets"]
    assert saved["summary"]["replacement_candidates"] == analysis["summary"]["replacement_candidates"]

    institutions = client.get(f"/api/v1/triage-runs/{run['id']}/institutions").json()
    assert institutions
    assets = client.get(f"/api/v1/triage-runs/{run['id']}/assets").json()
    assert len(assets) == 2
    assert assets[0]["evidence"]


def test_analysis_handles_empty_database(client):
    analysis = client.get("/api/v1/triage/analysis", params={"as_of": "2026-01-01"}).json()
    assert analysis["summary"]["total_assets"] == 0
    assert analysis["summary"]["high_risk_assets"] == 0
    assert analysis["assets"] == []
    assert analysis["institutions"] == []
