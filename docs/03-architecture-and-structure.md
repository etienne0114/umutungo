# Architecture and repository organization

## Architecture direction

Begin with a modular application and a separately testable data/analytics pipeline. Defer microservices, streaming, Redis, object storage, feature stores and model registries until a measured requirement justifies them. An approved file import can be a valid pilot integration; do not assume direct production-system access.

```text
Approved source systems / files
             |
      adapters + validation
             |
   canonical asset/event model ---- data-quality and lineage report
             |
  application API + authorization
       |                    |
  operational store    prediction artifacts/service
       |                    |
       +---- triage queue --+
                  |
       human disposition + outcome
                  |
             audit/evaluation
```

The system of record for asset identity, finance, inventory, and work orders must be decided with each source owner. Umutungo stores only the operational data necessary for its approved functions and references external identifiers where feasible.

## Proposed repository layout

Use domain boundaries to keep duplicated definitions and mixed responsibilities out of the project:

```text
.
├── README.md
├── project.yaml                 # project metadata, scope and decision gates
├── docs/
│   ├── 01-problem-and-scope.md
│   ├── 02-research-and-innovation.md
│   ├── 03-architecture-and-structure.md
│   ├── 04-data-and-ml.md
│   ├── 05-roadmap-and-acceptance.md
│   ├── decisions/               # approved architecture/scope decisions
│   └── source/                  # preserved original workshop inputs
├── apps/
│   ├── api/                     # implemented local FastAPI prototype
│   └── web/                     # user interface
├── packages/
│   └── contracts/               # shared API schemas; one definition of each contract
├── ml/
│   ├── pipelines/               # reproducible preparation and evaluation
│   ├── models/                  # training/inference code, not committed model binaries
│   └── reports/                 # sanitized evaluation outputs
├── data/
│   ├── schemas/                 # canonical source and normalized schemas
│   └── samples/                 # synthetic, non-sensitive fixtures only
├── infra/                       # deployment configuration and environment templates
├── scripts/                     # repeatable local data/setup utilities
└── tests/
    ├── integration/
    ├── contracts/
    └── acceptance/
```

Create implementation directories only as the corresponding component is approved. Keep one canonical definition per concept: API contracts in `packages/contracts`, canonical data definitions in `data/schemas`, project requirements in `docs/`, and environment-specific values outside committed secrets. Do not copy model features or enumerations independently into UI, API and ML code.

The current API keeps Pydantic contracts beside its domain implementation; extract them into `packages/contracts` only when a second consumer (such as the web client) exists. Development startup may create tables and apply the single backward-compatible nullable inspection-date addition. Adopt versioned migrations before adding deployment environments or operational data.

## Module ownership

| Concern | Owns | Must not own |
|---|---|---|
| Web | User journeys, accessible presentation, input validation feedback | Prediction logic, authoritative asset records |
| API | Authorization, workflow, asset/event references, recommendation ledger | Model training |
| Integration | Source-specific mapping, idempotent import, validation and lineage | UI-specific aliases as canonical data |
| ML pipeline | Time-correct labels/features, benchmark, evaluation, versioned artifact | Work-order authorization |
| Shared contracts | Request/response schemas and stable identifiers | Duplicate database/business logic |
| Infrastructure | Reproducible deployment and secret references | Credentials or real data checked in |

## Configuration policy

`project.yaml` is the canonical project-level configuration for metadata, scope, principles and gates. Application runtime configuration should later be environment-driven and schema-validated, with safe defaults only for non-sensitive development settings. Keep credentials in an approved secret manager or local ignored environment file; commit only a redacted template. Never put personal, operational or production records in samples, tests, logs or documentation.

## Boundary and reliability requirements

- Every import is repeatable/idempotent and reports source, extraction time, schema version and validation outcome.
- Store event time and ingestion time separately; preserve original source values for traceability.
- Version recommendations and explanations; previously issued recommendations must remain reproducible.
- Enforce institution and role boundaries server-side; never rely on hidden UI controls for access control.
- Make data freshness, missing coverage and synchronization state visible.
- Use a tested export/backup and restore path before pilot deployment.
- Add audit logs for access to sensitive records and all recommendation dispositions.
