from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from govasset_api.main import create_app


@pytest.fixture()
def client():
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


def test_create_asset_and_reject_duplicate_code(client):
    first = create_asset(client)
    assert first.status_code == 201
    assert first.json()["asset_code"] == "FLEET-001"
    assert create_asset(client).status_code == 409


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


def test_startup_adds_inspection_date_column_to_legacy_database():
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
