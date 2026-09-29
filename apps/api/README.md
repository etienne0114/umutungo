# Pilot API

This local prototype implements asset registration, maintenance history, and deterministic maintenance triage. Triage uses recorded condition and scheduled-service dates; it is **not** a predictive model, mechanical diagnosis, or repair authorization.

## Run locally

From this directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn govasset_api.main:app --reload --host 127.0.0.1
```

The default database is `./govasset.db` (SQLite). Set `DATABASE_URL` to a SQLAlchemy-supported URL to use a different database. Never put production data in this local prototype.

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Current triage rules

The initial demonstration rules mark recorded `critical` condition as critical; `poor` condition or service more than 30 days overdue as high; `fair` condition, overdue service, or service due within 14 days as medium; and `good` condition with a known non-imminent service date as low. Missing service/condition evidence yields `insufficient_data`. The 14/30-day cutoffs are provisional examples, not institution-approved policy or learned predictions; validate or replace them with the pilot users before any operational use.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Process health |
| `POST` | `/api/v1/assets` | Register an asset |
| `GET` | `/api/v1/assets` | List assets; optionally filter with `?active=true` |
| `GET` | `/api/v1/assets/{asset_id}` | Get asset details |
| `POST` | `/api/v1/assets/{asset_id}/maintenance` | Record maintenance |
| `GET` | `/api/v1/assets/{asset_id}/maintenance` | List an asset's maintenance history |
| `POST` | `/api/v1/assets/{asset_id}/inspections` | Record an inspection; the latest-dated inspection updates current asset condition |
| `GET` | `/api/v1/assets/{asset_id}/inspections` | List inspection history, newest first |
| `GET` | `/api/v1/triage` | View active assets ranked by rules; supports `as_of` and `risk_level` filters |
| `POST` | `/api/v1/triage-runs` | Persist a dated, versioned triage run and asset snapshots |
| `GET` | `/api/v1/triage-runs/{run_id}` | Read run metadata and recommendation count |
| `GET` | `/api/v1/recommendations` | List persisted recommendations; filter by `run_id`/`risk_level` and page with `limit`/`offset` |
| `GET` | `/api/v1/recommendations/{recommendation_id}` | Read a recommendation and its captured asset snapshot |
| `POST` | `/api/v1/recommendations/{recommendation_id}/events` | Append a review disposition or verified outcome |
| `GET` | `/api/v1/recommendations/{recommendation_id}/events` | Read the append-only recommendation event history |

Run generation snapshots the current asset fields and rule output so later changes do not rewrite the recommendation. Review events require a disposition and reason; outcome events require an outcome type and event date. The prototype API exposes no update/delete operation for these records. Actor identity is not captured until authentication is implemented.

## Safety and maturity boundary

This prototype has no authentication, authorization, tenant isolation, actor attribution, or production migration/backup process. Development startup creates missing tables and adds the nullable inspection-date field to the earlier local schema without deleting existing rows; this is not a replacement for versioned production migrations. Bind to loopback as shown. Do not expose it to a network, connect it to government systems, or enter personal/operational records until security, privacy, access-control, migration, backup, and pilot approvals are implemented and reviewed.

## Tests

From this directory, install the development extra and run:

```bash
pytest
```
