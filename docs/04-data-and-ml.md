# Data and predictive-analytics approach

## First define the prediction target

Do not train against the vague target “maintenance needed.” For the selected asset class, agree:

- Observable event (for example, a verified unscheduled repair/work order, not a presumed failure).
- Event timestamp and authoritative record.
- Prediction horizon and the minimum useful lead time.
- How scheduled maintenance, inspections, duplicate work orders, and unresolved reports are treated.
- What action a user can take and the acceptable alert volume.

If these definitions or labels are not dependable, deliver data quality, history and rule-based triage only.

## Data domains and minimum lineage

| Domain | Example fields | Important controls |
|---|---|---|
| Asset identity | source system, source ID, stable internal ID, type, make/model, in-service status | Preserve source ID; resolve aliases/reuse; record match confidence |
| Usage | reading, unit, effective time, source | Validate monotonicity/reset; never mix km and miles |
| Inspection | inspection time, checklist/version, observation, severity, inspector role | Distinguish not inspected from no defect; preserve original entry |
| Maintenance/work | event time, planned/unplanned, fault category, action, completion, outcome | Define status transitions and event time; deduplicate cautiously |
| Cost/parts/downtime | amount/currency, part reference, downtime interval | Define completeness, currency/year and causal attribution |
| Recommendation | model/rule version, input snapshot reference, horizon, score, reason, disposition | Immutable history; audit all updates |

For every imported field, document source, owner, purpose, transformation, units, allowed values, sensitivity, retention, quality checks and refresh expectations. Minimize personal data; do not use driver identity as a predictive feature by default.

## Data readiness checks

Profile asset coverage, history length, event counts, missingness, duplicates, conflicting identifiers, timestamp quality, usage-reading anomalies, category consistency and source freshness. Inspect outcome-label completeness and whether record-keeping practices changed over time. Report coverage by asset class and time period. Obtain approval and a data-sharing basis before extraction.

An empty or missing record is not automatically a negative outcome. Avoid imputing a “no failure” label from missing work orders. Keep train/evaluation splits chronological; fit preprocessing only on training periods; prevent post-event fields, work-order close dates and future observations from leaking into prediction features.

## Modeling sequence

1. **Descriptive baseline:** Asset history, maintenance intervals, overdue rules and transparent thresholds.
2. **Operational baseline:** Rank using an agreed rule and measure precision-at-k, lead time and alert burden at real inspection capacity.
3. **Simple model:** Only if label volume and quality justify it; compare to the rule baseline using chronological backtesting.
4. **Calibrated, interpretable model:** Select by decision value and stability, not only ROC-AUC. Report calibration and uncertainty.
5. **Shadow mode:** Generate recommendations without changing work; review false positives, misses, coverage and user interpretation.
6. **Controlled pilot:** Release to approved users with human decisions, monitoring, rollback and model/rule versioning.

Use separate event definitions and evaluations when asset classes have materially different failure/maintenance patterns. Do not assume XGBoost, SHAP, deep learning, or a particular MLOps stack is necessary before benchmarking.

## Recommendation contract

Every displayed recommendation should include:

- Asset/source identity and “as of” time.
- Target event and prediction horizon.
- Risk band and, only if validated, probability with calibration context.
- Main contributing observed factors and their freshness.
- Coverage/confidence or explicit abstention reason.
- Suggested next action, clearly labeled as advisory.
- Rule/model identifier and a link to relevant history.
- Human disposition and outcome capture.

Abstain when required data is stale, out of scope, materially incomplete or outside validated populations. Do not present a score as a diagnosis or a guaranteed failure.

## Evaluation

Evaluate against a chronological holdout and an agreed operational baseline. Report sample size and uncertainty. Recommended measures include precision/recall, precision-at-k, lead time, calibration, false alerts per asset-month, missed events, data coverage, subgroup performance and staff workload. Evaluate operational impact separately: comparison design and confounders should be documented; before/after change alone does not prove the system caused an outcome.

## Privacy, security and responsible use

Before processing, the institution’s accountable legal/privacy/security functions must confirm lawful purpose, data minimization, access, retention, sharing, hosting and incident response against applicable Rwanda requirements. Use least privilege, institution-level isolation, secure transport/storage, secrets management, auditability and tested backup/restore. These are design controls, not a substitute for legal approval or security assessment.
