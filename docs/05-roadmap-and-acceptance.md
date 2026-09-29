# Roadmap and acceptance gates

Each phase ends with a decision to proceed, revise or stop. A calendar date is not a substitute for evidence or approval.

| Phase | Deliverables | Exit evidence |
|---|---|---|
| 0. Validate the problem | Stakeholder map, observed workflow, target event, constraints, pilot cohort | Institution owner and representative users confirm problem and scope |
| 1. Validate data and governance | Source inventory, access basis, field lineage, data profile, privacy/security review, baseline definitions | Data owner approves sample and intended use; quality and label gaps documented |
| 2. Build foundation | Canonical schemas, import validation, identity resolution, history view and quality report | Repeatable import; duplicate/replay behavior safe; source-to-output traceability |
| 3. Test operational MVP | Searchable asset history, transparent triage rules, role-based workflow, recommendation ledger | Users complete agreed tasks; audit and accessibility/usability issues addressed |
| 4. Evaluate prediction | Baseline benchmark, time-aware backtest, calibration/coverage, explanation review, shadow-mode report | Model adds value over baseline at acceptable alert capacity; abstention and rollback approved |
| 5. Run controlled pilot | Trained users, support/escalation process, monitored recommendations, feedback | Safety/privacy/security sign-off; outcomes and adverse effects reviewed |
| 6. Decide next investment | KPI comparison, qualitative feedback, cost/benefit assumptions, lessons, scale plan | Sponsor documents continue/change/stop decision and unresolved risks |

## Product acceptance criteria

- A user can trace each displayed item to its source and “as of” time.
- Imports validate required fields, identify duplicate/conflicting records and produce actionable error summaries.
- The system distinguishes unavailable/stale data from a healthy asset.
- Each recommendation can be reviewed, accepted, deferred or rejected with a reason; history is auditable.
- Data outside the evaluated coverage is visibly flagged or receives no model prediction.
- Role and institution boundaries are enforced by the API and covered by tests before deployment.
- Users can export authorized reports without exposing records beyond their role.
- A pilot can be stopped and the prior rule/model version restored without losing decision history.

## Pilot scorecard template

Fill in definitions and baselines with the pilot institution before launch:

| Measure | Operational definition | Baseline | Target | Owner/source |
|---|---|---:|---:|---|
| Alert precision at weekly capacity | Verified target events among top-k alerts | TBD | TBD | TBD |
| Median useful lead time | Days from alert to verified event, excluding post-event alerts | TBD | TBD | TBD |
| Unplanned downtime | Agreed unavailable-time measure per asset-period | TBD | TBD | TBD |
| Planned/reactive share | Agreed completed work classification | TBD | TBD | TBD |
| Data coverage/freshness | Required fields and refresh lag by cohort | TBD | TBD | TBD |
| User disposition | Reviewed recommendations and accept/defer/reject reasons | TBD | TBD | TBD |
| False-alert burden | Alerts not actionable per staff/week or asset-month | TBD | TBD | TBD |

## Release blockers

Do not release user-facing predictive recommendations until the target event, authorized data use, time-aware evaluation, minimum coverage, acceptable alert burden, human review, audit, incident/escalation and rollback procedures are approved. Do not expand to a second institution or asset class until the pilot review documents portability, local data differences, and required governance changes.
