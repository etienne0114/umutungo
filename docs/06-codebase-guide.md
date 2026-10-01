# Codebase guide

This guide describes the implemented repository, not a proposed parallel architecture. New work should extend these boundaries instead of adding another application, authentication flow, or database.

## Repository map

```text
titans/
├── apps/
│   ├── api/
│   │   ├── migrations/versions/       # ordered, data-preserving Alembic changes
│   │   ├── vercel.json                # FastAPI function and region configuration
│   │   ├── scripts/                   # explicit operator utilities
│   │   ├── src/govasset_api/
│   │   │   ├── api/
│   │   │   │   ├── dependencies.py    # tenant-aware HTTP dependencies/lookups
│   │   │   │   └── routers/           # routes grouped by business capability
│   │   │   ├── catalogs/              # immutable, dated official reference snapshots
│   │   │   ├── services/              # business validation independent of HTTP
│   │   │   ├── auth.py                # Supabase JWT authentication
│   │   │   ├── authorization.py       # institution scope and role enforcement
│   │   │   ├── database.py            # engine/session lifecycle
│   │   │   ├── main.py                # application composition only
│   │   │   ├── models.py              # current relational model
│   │   │   ├── schemas.py             # validated API contracts
│   │   │   ├── reporting.py           # descriptive reporting/export logic
│   │   │   ├── supabase_admin.py      # server-only identity administration
│   │   │   └── triage.py              # deterministic, versioned rule engine
│   │   └── tests/                      # API, authorization, and migration tests
│   └── web/
│       └── src/
│           ├── app/                    # Next.js route and layout entry points
│           ├── components/             # shared presentation primitives
│           ├── features/               # UI grouped by user capability
│           └── lib/
│               ├── api/                # one browser-to-API boundary
│               └── supabase/           # browser authentication client
├── docs/                               # maintained product and architecture record
├── scripts/                            # repository-level development workflows
├── project.yaml                        # scope, principles, and delivery gates
└── render.yaml                         # existing Render fallback definition
```

## Backend request flow

```text
Bearer token
    -> Supabase JWT verification
    -> approved-account check
    -> global-admin or institution membership resolution
    -> institution-scoped query/mutation
    -> validated response contract
```

`main.py` must remain a composition root. A new business capability belongs in a route module under `api/routers/`; reusable business validation belongs under `services/`. Tenant filtering belongs in `authorization.py` or a domain-specific query service and must be applied before records are loaded.

## Data ownership rules

- Institutions are Supabase PostgreSQL rows. The dated official catalog is migration-backed seed data with source provenance; administrators may extend it without changing application enums.
- Stable classifications such as institution type, membership role, condition, and risk level use validated enums.
- Institution-owned records receive their institution from the authenticated server-side scope, never from an untrusted request body.
- Historical maintenance, inspections, recommendations, and recommendation events are append-only through the public API.
- Global administrators may request all institutions or explicitly select one. Institution users may only resolve active memberships assigned to their Supabase user ID.
- Supabase `app_metadata` is used for trusted application access flags. User-editable profile metadata is never used for authorization.

## Adding a capability

1. Extend the existing SQLAlchemy model and Pydantic contract; do not create a second representation of the same concept.
2. Add a forward-only, data-preserving Alembic migration with institution and lookup indexes required by the access pattern.
3. Put cross-route business rules in a service and expose them through a focused router.
4. Apply tenant scope before entity lookup so unauthorized records return the same not-found behavior as missing records.
5. Add authorization, integration, validation, and migration tests.
6. Add typed browser API methods in `apps/web/src/lib/api/`; UI features must not connect directly to PostgreSQL.
7. Run the backend suite, a clean and legacy-copy migration check, frontend lint, and the production build.

## Implemented boundary

The current implementation includes Supabase authentication and approval, government-institution hierarchy (19 ministries, affiliated agencies, provinces, City of Kigali, and 30 districts), institution memberships and roles, server-side tenant isolation, asset registration, inspection and maintenance history, transparent rule-based triage, versioned recommendation snapshots, human review/outcome events, descriptive data-quality reporting with ministry/local-government tree rollups, and bounded CSV exports.

Drivers, time-bounded driver assignments, inventory, configurable persisted rules, audit logs, notifications, maintenance cost detail, and a trained predictive model remain later capabilities. They should only be presented in the product after their real database-backed workflow exists. Until sufficient approved outcome data exists, the rule engine must continue to be labelled as advisory triage rather than AI failure prediction.
