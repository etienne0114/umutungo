# Government Asset Maintenance Intelligence

**Working title:** GovAsset Insight  
**Status:** Frontend deployed to Vercel; Render API deployment is pending repository sync and secret setup
**Purpose:** Help public-sector maintenance teams prioritize inspections and planned work using existing asset and maintenance data. The product is decision support; authorized people retain operational authority.

## Start here

1. [Problem, users, and pilot boundaries](docs/01-problem-and-scope.md)
2. [Research findings and proposed innovation](docs/02-research-and-innovation.md)
3. [Architecture and repository organization](docs/03-architecture-and-structure.md)
4. [Data and predictive-analytics approach](docs/04-data-and-ml.md)
5. [Roadmap and acceptance gates](docs/05-roadmap-and-acceptance.md)
6. [Project configuration](project.yaml)
7. [Original workshop and requirements inputs](docs/source/)
8. [Pilot API and hosted setup](apps/api/README.md)
9. [Web application](apps/web/README.md)

## Project principle

Prove that the institution has usable, authorized, sufficiently complete data and a maintenance workflow that can act on recommendations before investing in a predictive model. Begin with transparent rules and descriptive analytics; add a model only when historical outcomes and time-based evaluation support it.

The platform must complement—not replace or duplicate—official asset, fleet, finance, or inventory systems. The integration boundary and system of record for each field must be agreed with the pilot institution before implementation.

## Current maturity

This repository contains the project definition, a local API prototype, and a Next.js dashboard intended to connect to the API. The dashboard is deployed to Vercel as `titans` and supports invitation-only Supabase sign-in; hosted API requests verify Supabase access tokens and require an administrator-approved account. PostgreSQL migrations and a Render Docker-service Blueprint are in place. The API has not been deployed, and no remote database migration has been applied. The product does not run AI models and is not approved for operational data or network deployment.

## Source-of-truth policy

The numbered documents in `docs/` are the maintained project specification. Files in `docs/source/` are preserved workshop/reference inputs. Update the specification when decisions change; do not maintain competing copies of requirements.
