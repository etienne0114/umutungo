# Umutungo

**Status:** Institution-aware pilot under active development
**Purpose:** Help public-sector maintenance teams prioritize inspections and planned work using authorized asset and maintenance data. Umutungo is decision support; authorized people retain operational and financial authority.

## Start here

1. [Problem, users, and pilot boundaries](docs/01-problem-and-scope.md)
2. [Research findings and proposed innovation](docs/02-research-and-innovation.md)
3. [Architecture and repository organization](docs/03-architecture-and-structure.md)
4. [Data and predictive-analytics approach](docs/04-data-and-ml.md)
5. [Roadmap and acceptance gates](docs/05-roadmap-and-acceptance.md)
6. [Implemented codebase guide](docs/06-codebase-guide.md)
7. [Deployment guide](DEPLOYMENT.md)
8. [Project configuration](project.yaml)
9. [Pilot API and hosted setup](apps/api/README.md)
10. [Web application](apps/web/README.md)

## Project principle

Prove that an institution has usable, authorized, sufficiently complete data and a maintenance workflow that can act on recommendations before investing in a predictive model. Begin with transparent rules and descriptive analytics; add a trained model only when historical outcomes and time-based evaluation support it.

The platform must complement—not replace or duplicate—official asset, fleet, finance, or inventory systems. The integration boundary and system of record for each field must be agreed with the responsible institution before implementation.

## Current implementation

The repository contains a FastAPI service and a Next.js dashboard. Supabase provides identity and account approval; Supabase PostgreSQL owns the sourced Rwanda government-institution hierarchy, institution memberships, assets, inspections, maintenance history, recommendation snapshots, and human review/outcome events.

The API enforces institution scope before data access. A system administrator can manage institution records and memberships. Institution roles cannot cross into another tenant by changing an `institution_id` request value, and read-only roles cannot mutate operational data. Asset codes are unique inside an institution rather than globally.

Maintenance triage is currently a deterministic, versioned rule set based on recorded condition and service dates. It is explicitly advisory—not a trained predictive model, mechanical diagnosis, confirmed failure, or repair authorization. Usage readings, drivers and assignments, inventory, costs, audit logs, persisted rule configuration, notifications, and trained predictive analytics are not presented as implemented features.

## Run and verify

Start the full local application from `apps/web`:

```bash
npm run dev
```

Run the backend and frontend verification separately:

```bash
cd apps/api
../../.venv/bin/pytest -q

cd ../web
npm run lint
npm run build
```

See the application-specific READMEs for environment variables, Supabase configuration, migrations, and deployment details. Never commit operational data, credentials, service-role keys, access tokens, or database connection strings.

## Source-of-truth policy

The numbered documents in `docs/` are the maintained project specification. Files in `docs/source/` preserve original workshop and requirement inputs. Update the maintained specification when decisions change; do not create competing requirement copies or parallel application modules.
