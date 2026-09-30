# Pilot API

This local prototype implements asset registration, maintenance history, and deterministic maintenance triage. Triage uses recorded condition and scheduled-service dates; it is **not** a predictive model, mechanical diagnosis, or repair authorization.

## Run locally

From this directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn govasset_api.main:app --reload --host 127.0.0.1 --port 8000
```

Apply Alembic migrations before starting against Supabase PostgreSQL. `DATABASE_URL` is required; the application has no implicit SQLite runtime database. Back up and verify any pre-Alembic database before stamping or upgrading it.

From the API directory, Uvicorn automatically loads `apps/api/.env.local` during local startup; application environment variables already set in the shell take precedence. The loader is disabled for Render (`RENDER_SERVICE_ID`) and production (`APP_ENV=production`). Keep this file ignored by git. The API `.env` file is not loaded automatically. Set `SUPABASE_URL` to the same Supabase project used by `apps/web/.env.local`. Configure `DATABASE_URL` with the Supabase PostgreSQL pooler connection used by this environment. The automated unit tests construct isolated in-memory SQLite engines explicitly; the application runtime does not default to SQLite. Keep `AUTH_REQUIRED=true` when testing real sign-in and approval claims; use `AUTH_REQUIRED=false` only for isolated local development where authentication is intentionally disabled. Never use development settings for a deployed service.

Alternatively, run `npm run dev` from `apps/web` to start the API and frontend together. That command checks the local API health endpoint before launching the frontend.

To use a different Supabase environment, change `DATABASE_URL` in the ignored `.env.local` and confirm the target before running migrations. Browser requests from localhost and `127.0.0.1` development origins are allowed on any port; hosted CORS only allows the configured production and Umutungo preview domains.

Open `http://127.0.0.1:8000/docs` for interactive API documentation.

## Current triage rules

The initial demonstration rules mark recorded `critical` condition as critical; `poor` condition or service more than 30 days overdue as high; `fair` condition, overdue service, or service due within 14 days as medium; and `good` condition with a known non-imminent service date as low. Missing service/condition evidence yields `insufficient_data`. The 14/30-day cutoffs are provisional examples, not institution-approved policy or learned predictions; validate or replace them with the pilot users before any operational use.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Process health |
| `GET` | `/api/v1/admin/users` | Admin-only list of registered account summaries; supports `page` and `per_page` (maximum 100) |
| `PUT` | `/api/v1/admin/users/{user_id}/access` | Admin-only approve/revoke action for a confirmed account |
| `GET` | `/api/v1/institutions` | List institutions visible to the signed-in user (global administrators see all) |
| `GET` | `/api/v1/admin/institutions` | Global-administrator institution catalog |
| `POST` | `/api/v1/admin/institutions` | Create an institution |
| `POST` | `/api/v1/admin/institutions/sync-official-catalog` | Idempotently synchronize the dated, sourced Rwanda government reference catalog |
| `PATCH` | `/api/v1/admin/institutions/{institution_id}` | Update institution details and hierarchy |
| `GET` | `/api/v1/admin/memberships` | Global-administrator membership listing |
| `POST` | `/api/v1/admin/memberships` | Assign an approved Supabase user an institution role |
| `PATCH` | `/api/v1/admin/memberships/{user_id}/{institution_id}` | Update an institution membership role |
| `DELETE` | `/api/v1/admin/memberships/{user_id}/{institution_id}` | Remove an institution membership |
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
| `GET` | `/api/v1/reports/operations` | View scoped asset coverage and actual activity; administrators may include the selected institution subtree |
| `GET` | `/api/v1/reports/institution-tree` | Administrator report grouped by top-level ministry, province, or City of Kigali |
| `GET` | `/api/v1/exports/assets.csv` | Export up to 10,000 asset register rows |
| `GET` | `/api/v1/exports/maintenance.csv` | Export up to 10,000 maintenance rows |
| `GET` | `/api/v1/exports/inspections.csv` | Export up to 10,000 inspection rows |

Run generation snapshots the current asset fields and rule output so later changes do not rewrite the recommendation. Review events require a disposition and reason; outcome events require an outcome type and event date. The prototype API exposes no update/delete operation for these records. Recommendation event actor identity is not yet captured.

The operations report explicitly lists fields and governance boundaries the current data model does not capture. It is descriptive only: recorded downtime is not availability, and rule-based risk totals are not model predictions. CSV exports are scoped to the requesting user's institution, escape spreadsheet formula-leading values, and reject datasets over 10,000 rows rather than silently truncating them.

## Institution tenancy and roles

The additive revisions `5c27b67a1f4d` and `9f4e2b7a6c31` introduce a database-managed institution hierarchy, memberships, nullable institution ownership on assets and triage runs, and the verified Rwanda government reference catalog. Apply them with `alembic upgrade head` before deploying the updated API. Existing operational records are preserved and remain unassigned (`institution_id` stays null); ownership is never inferred from organization labels, emails, asset codes, or other legacy fields. Catalog records do not create memberships or grant access. A global administrator must assign approved users to institutions before they can access operational data. Legacy null-owned records remain visible to global administrators and `AUTH_REQUIRED=false` local development only.

Only a token with the existing trusted `app_metadata.govasset_role=admin` claim can manage institutions and memberships. Administrators can synchronize the versioned Rwanda government reference catalog from the Institutions screen; matching official codes are updated, while memberships and asset records remain unchanged. The API returns catalog counts, verification date, and source URLs. Assignments require an active institution and a stable membership role (`institution_admin`, `fleet_manager`, `maintenance_officer`, `technician`, `driver`, `auditor`, or `viewer`). When the Supabase Admin API is configured, assignment verifies the UUID exists and has `govasset_access=approved`; without that server-side API configuration the UUID cannot be verified. No service key is returned by these endpoints.

Within their institution, institution admins and fleet managers can register assets, record maintenance/inspections, run triage, review recommendations, and record outcomes. Maintenance officers can record maintenance/inspections, run triage, and review recommendations or outcomes, but cannot change the asset register. Technicians can record maintenance/inspections and recommendation outcomes, but cannot register assets, run triage, or review recommendations. Drivers, auditors, and viewers are read-only until their dedicated workflows and permissions are implemented. All current asset, history, triage, recommendation, report, and CSV routes apply the same tenant boundary; resource IDs outside the caller's tenant return `404`. Global administrators can optionally select an institution with `?institution_id=<id>`; omitting it grants their existing global view. In the web application, users select an institution from the workspace header; the browser includes that institution on operational requests and remembers the selection for that browser. A user with more than one membership must select one institution before viewing operational data. There is no department-level RBAC, user invite flow, membership audit trail, or actor identity on recommendation events yet.

The existing rule-based triage remains advisory and is not machine learning or a predictive maintenance claim. Do not seed demonstration assets or assign existing production records without an independently verified ownership process.

## Hosted development

The API supports Supabase Auth bearer-token verification and PostgreSQL for hosted development. Set these values in the API host's secret/environment settings (never commit a real `.env` file):

| Variable | Requirement |
|---|---|
| `AUTH_REQUIRED` | `true` for hosted deployment |
| `SUPABASE_URL` | Supabase project URL used to validate token issuer and JWKS |
| `DATABASE_URL` | Persistent PostgreSQL connection URL; `postgresql://` URLs use psycopg |
| `CORS_ORIGINS` | Comma-separated exact frontend origins, with no wildcard |
| `SUPABASE_SECRET_KEY` | Preferred server-only key for admin user-management endpoints; never expose it to the browser |
| `SUPABASE_SERVICE_ROLE_KEY` | Compatible legacy server-only key when the project has not adopted secret keys |

The web app supports Supabase email/password registration, email confirmation, sign-in, and password recovery. Supabase Auth must allow email registration and have the production/preview redirect URLs configured. New accounts do not receive application access automatically: only an administrator may set trusted `app_metadata.govasset_access=approved`. Until then, API requests return `403` with an approval-pending message. Approval alone does not grant operational access: a user must also receive an active institution membership.

The API stores its tables in the isolated PostgreSQL `govasset` schema. Apply versioned schema changes with Alembic. The Render start command runs `alembic upgrade head` before starting Uvicorn. For local database migration work, run commands from this directory:

```bash
alembic upgrade head
alembic downgrade -1
```

Alembic requires `DATABASE_URL` and targets the configured Supabase PostgreSQL database; there is no fallback database. Never run downgrade or apply a migration against a real hosted database without confirming the target, backup, and migration plan.

### Administrator access

The requested initial administrator is `etiennetuyihamye@gmail.com`. Its trusted Supabase `app_metadata` contains `govasset_access=approved` and `govasset_role=admin`. After provisioning or changing trusted claims, the user must sign out and sign back in to receive a token with the new claims.

Administrators can review registered accounts in the web app's **User access** view, search/filter loaded users, and load additional pages of up to 100 accounts. Newly registered users remain pending; only email-confirmed accounts can be approved. After approval, a user must sign out and back in to refresh their token claims before API access works. Revocation updates trusted metadata, but an already-issued access token may remain valid until it expires or refreshes. The API prefers the server-only `SUPABASE_SECRET_KEY` and accepts `SUPABASE_SERVICE_ROLE_KEY` for legacy projects. Keep that value only in Render's private environment (or a secured operator env file); never put it in `NEXT_PUBLIC_*`, frontend configuration, source control, or browser code. To promote the initial administrator manually, run `python scripts/promote_admin.py --email etiennetuyihamye@gmail.com` from `apps/api` with `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (or the legacy service-role key) set in the process environment. The script requires the account to exist and have confirmed its email, preserves unrelated app metadata, and does not set a password.

For local administrator API testing, add `SUPABASE_SECRET_KEY` from the Supabase project's server-side API-key settings (or use the legacy `SUPABASE_SERVICE_ROLE_KEY`) to the ignored `apps/api/.env.local`. The local admin endpoints intentionally return a configuration error without this key. Never copy it into `apps/web/.env.local`, a `NEXT_PUBLIC_*` variable, or source control.

### Render deployment

The repository-root `render.yaml` defines a Python web service at `https://umutungo.onrender.com`, rooted at `apps/api`, and configures `/health` as its health check. The service installs `apps/api/requirements.txt`, which delegates dependency definitions to `pyproject.toml`. Connect this repository to Render as a Blueprint and select the `main` branch. During initial Blueprint setup, enter the following values directly in the Render Dashboard:

| Render environment variable | Source |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection URL |
| `SUPABASE_URL` | Supabase project HTTPS URL (the same project as the browser Auth settings) |
| `AUTH_REQUIRED` | `true` |
| `CORS_ORIGINS` | Comma-separated stable frontend origins, including `https://umutungo7.vercel.app`, `https://umutungo-five.vercel.app`, and `https://umutungo-etienne0114s-projects.vercel.app` |
| `CORS_ORIGIN_REGEX` | Optional, narrowly scoped regex for this Vercel project's generated deployment URLs; do not use a wildcard that accepts arbitrary origins |

`DATABASE_URL` and `SUPABASE_URL` use `sync: false` so Render requests those values in its setup flow instead of storing them in this repository. Use the Supabase session-pooler connection URL for `DATABASE_URL`; the direct database hostname is IPv6-only and is unreachable from Render's current service network. `SUPABASE_URL` must be the Supabase project HTTPS URL. `CORS_ORIGINS` must contain each stable Vercel hostname users may visit; the narrowly scoped `CORS_ORIGIN_REGEX` covers generated deployment URLs for this Vercel project. Do not use `*` for origins. A CORS rejection in a browser looks like a network failure even when the API is healthy. The container applies the Alembic migration on startup, creating application tables in the isolated `govasset` schema. Set production secrets directly in Render; never commit them or send them in chat.

## Safety and maturity boundary

Local and hosted application runtimes require an explicit Supabase PostgreSQL `DATABASE_URL`. Hosted mode must also enable authentication; startup rejects missing hosted configuration. SQLite is used only by explicitly constructed isolated unit-test engines. Authentication verifies identity and an administrator-approved access flag, but is not a substitute for tenant isolation, fine-grained authorization, institutional approval, security/privacy review, or backups. Do not enter personal or operational records, connect government systems, or claim operational readiness until these controls and pilot approvals are in place.

## Tests

From this directory, install the development extra and run:

```bash
pytest
```
