# ADR 0001: Modular pilot architecture

- **Status:** Proposed
- **Date:** 2026-09-29
- **Decision owners:** To be confirmed with project and pilot institution

## Context

The source requirements describe a broad stack and future multi-institution capabilities, but no pilot institution, integration contract, workload, hosting decision, or data sample has been confirmed. A large distributed architecture would add operational cost before the primary data and workflow risks are understood.

## Decision

Start with a modular application, explicit source adapters, shared data/API contracts and a separately testable analytics pipeline. Prefer a secure, repeatable batch import unless the institution confirms an authorized API and a real freshness need. Choose implementation frameworks and managed services after environment, procurement, identity and hosting constraints are established.

The existing recommendation is Python/FastAPI, a TypeScript web client and PostgreSQL as a candidate stack—not an approved commitment. Defer selecting queues, cache, object store, orchestration and model registry until measurable needs exist.

## Consequences

- Easier pilot deployment, testing and ownership with fewer operational components.
- Clear boundaries reduce duplicated data and business rules.
- Interfaces and modules can be separated later if scale, availability or independent release needs justify it.
- Batch freshness may be insufficient for some workflows; verify this during discovery.
- This decision does not authorize connections to any government system.

## Revisit when

The institution’s requirements establish deployment environment, integration mode, availability/freshness objectives, data volume, support ownership or scaling needs that materially change this tradeoff.
