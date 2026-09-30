# Pilot API

This local prototype implements asset registration, maintenance history, and deterministic maintenance triage. Triage uses recorded condition and scheduled-service dates; it is **not** a predictive model, mechanical diagnosis, or repair authorization.

## Run locally

From this directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn govasset_api.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env.local
```

The API explicitly loads `apps/api/.env.local` for local development. This local-only config uses SQLite and sets `AUTH_REQUIRED=false`; it avoids writing test records to the hosted Supabase database. The web frontend still signs in through Supabase, but the local API skips bearer-token enforcement. Never use this configuration for a deployed service or put production data in this local prototype. The separate `apps/api/.env` file is not loaded by this command.

To use a different local database, change `DATABASE_URL` in `.env.local`. Browser requests from the two localhost Next.js origins are allowed by default; configure `CORS_ORIGINS` as a comma-separated exact-origin allowlist for other local frontend origins.

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Current triage rules

The initial demonstration rules mark recorded `critical` condition as critical; `poor` condition or service more than 30 days overdue as high; `fair` condition, overdue service, or service due within 14 days as medium; and `good` condition with a known non-imminent service date as low. Missing service/condition evidence yields `insufficient_data`. The 14/30-day cutoffs are provisional examples, not institution-approved policy or learned predictions; validate or replace them with the pilot users before any operational use.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Process health |
| `GET` | `/api/v1/admin/users` | Admin-only list of registered account summaries |
| `PUT` | `/api/v1/admin/users/{user_id}/access` | Admin-only approve/revoke action for a confirmed account |
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
| `GET` | `/api/v1/triage-runs` | List saved runs, newest first; supports bounded `limit` and `offset` |
| `GET` | `/api/v1/recommendations` | List persisted recommendations; filter by `run_id`/`risk_level` and page with `limit`/`offset` |
| `GET` | `/api/v1/recommendations/{recommendation_id}` | Read a recommendation and its captured asset snapshot |
| `POST` | `/api/v1/recommendations/{recommendation_id}/events` | Append a review disposition or verified outcome |
| `GET` | `/api/v1/recommendations/{recommendation_id}/events` | Read the append-only recommendation event history |

Run generation snapshots the current asset fields and rule output so later changes do not rewrite the recommendation. Review events require a disposition and reason; outcome events require an outcome type and event date. The prototype API exposes no update/delete operation for these records. Actor identity is not captured until authentication is implemented.

## Hosted development

The API supports Supabase Auth bearer-token verification and PostgreSQL for hosted development. Set these values in the API host's secret/environment settings (never commit a real `.env` file):

| Variable | Requirement |
|---|---|
| `AUTH_REQUIRED` | `true` for hosted deployment |
| `SUPABASE_URL` | Supabase project URL used to validate token issuer and JWKS |
| `DATABASE_URL` | Persistent PostgreSQL connection URL; `postgresql://` URLs use psycopg |
| `CORS_ORIGINS` | Comma-separated exact frontend origins, with no wildcard |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only key used by admin user-management endpoints; never expose it to the browser |

The web app supports Supabase email/password registration, email confirmation, sign-in, and password recovery. Supabase Auth must allow email registration and have the production/preview redirect URLs configured. New accounts do not receive application access automatically: only an administrator may set trusted `app_metadata.govasset_access=approved`. Until then, API requests return `403` with an approval-pending message. The API does not currently implement institution-level or role-level authorization; do not grant access to users from multiple institutions until that boundary is implemented.

The API stores its tables in the isolated PostgreSQL `govasset` schema. Apply versioned schema changes with Alembic. The Render start command runs `alembic upgrade head` before starting Uvicorn. For local database migration work, run commands from this directory:

```bash
alembic upgrade head
alembic downgrade -1
```

The Alembic default is local SQLite. Use `DATABASE_URL` to override it. Never run downgrade or apply a migration against a real hosted database without confirming the target, backup, and migration plan.

### Administrator access

The requested initial administrator is `etiennetuyihamye@gmail.com`. Its trusted Supabase `app_metadata` contains `govasset_access=approved` and `govasset_role=admin`. After provisioning or changing trusted claims, the user must sign out and sign back in to receive a token with the new claims.

Administrators can review email-confirmed accounts in the web app's **User access** view. Newly registered users remain pending; only email-confirmed accounts can be approved. The API uses the server-only `SUPABASE_SERVICE_ROLE_KEY` to manage Auth users. Keep that value only in Render's private environment (or a secured operator env file); never put it in `NEXT_PUBLIC_*`, frontend configuration, source control, or browser code. To promote the initial administrator manually, run `python scripts/promote_admin.py --email etiennetuyihamye@gmail.com` from `apps/api` with `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` set in the process environment. The script requires the account to exist and have confirmed its email, preserves unrelated app metadata, and does not set a password.

### Render deployment

The repository-root `render.yaml` defines a Python web service at `https://umutungo.onrender.com`, rooted at `apps/api`, and configures `/health` as its health check. The service installs `apps/api/requirements.txt`, which delegates dependency definitions to `pyproject.toml`. Connect this repository to Render as a Blueprint and select the `main` branch. During initial Blueprint setup, enter the following values directly in the Render Dashboard:

| Render environment variable | Source |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection URL |
| `SUPABASE_URL` | Supabase project HTTPS URL (the same project as the browser Auth settings) |
| `AUTH_REQUIRED` | `true` |
| `CORS_ORIGINS` | Exact production frontend origin: `https://umutungo7.vercel.app` |

`DATABASE_URL` and `SUPABASE_URL` use `sync: false` so Render requests those values in its setup flow instead of storing them in this repository. Use the Supabase session-pooler connection URL for `DATABASE_URL`; the direct database hostname is IPv6-only and is unreachable from Render's current service network. `SUPABASE_URL` must be the Supabase project HTTPS URL. `CORS_ORIGINS` must contain each Vercel hostname users may visit, including the stable `umutungo7.vercel.app` and the active project aliases. A CORS rejection in a browser looks like a network failure even when the API is healthy. The container applies the Alembic migration on startup, creating application tables in the isolated `govasset` schema. Set production secrets directly in Render; never commit them or send them in chat.

## Safety and maturity boundary

Local development defaults to `AUTH_REQUIRED=false` and SQLite. Hosted mode must enable authentication and use persistent PostgreSQL; startup rejects missing hosted configuration. Authentication verifies identity and an administrator-approved access flag, but is not a substitute for tenant isolation, fine-grained authorization, institutional approval, security/privacy review, or backups. Do not enter personal or operational records, connect government systems, or claim operational readiness until these controls and pilot approvals are in place.

## Tests

From this directory, install the development extra and run:

```bash
pytest
```
