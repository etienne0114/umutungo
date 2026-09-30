# Research findings and proposed innovation

**Research boundary:** This is an evidence-led project review, not a claim that a particular government integration, legal interpretation, or model has already been validated. Publicly accessible primary sources are cited at the end. System-specific assertions in the workshop inputs remain items to verify with the relevant institution.

## Findings from the supplied material

The two inputs describe the same central opportunity: use information already collected for asset, inspection, usage and maintenance management to improve prioritization. They also agree on a modular application plus separate analytics workflow, human review and data readiness before complex ML.

The requirements draft goes further into a large technology stack, multiple asset types, model choices, integrations and success measures than the problem canvas can currently substantiate. These are options, not approved requirements. The pilot is not yet anchored to a named institution, exact asset class, authorized data sample, confirmed operating workflow, or baseline. Those gaps should determine the next work—not a premature framework or infrastructure choice.

The source notes state that Rwanda has digital fleet and Smart IFMIS asset/inventory capabilities. This research pass did not independently verify the scope, interfaces, data ownership or present operational status of those systems. Treat them as leads for stakeholder discovery; do not publish them as confirmed integration commitments.

## Gaps to close before build

1. **Define the event.** “Needs maintenance,” “breakdown,” “inspection finding,” and “work order” are not interchangeable labels. Agree which observable event is predicted, who records it, and whether scheduled servicing counts.
2. **Define the decision.** Determine how many inspections/work items staff can actually handle, what actions are safe, and whether the useful output is a ranking, due date, rule flag or probability.
3. **Establish provenance and rights.** Identify each source owner, system of record, lawful purpose, permitted fields, retention, export/API path, data-residency constraints and approval process.
4. **Resolve identity and time.** Asset codes may change or be reused; odometer readings can reset or be mistyped; maintenance and inspection dates may be delayed. Preserve source identifiers and effective/event timestamps.
5. **Prevent false confidence.** An absent maintenance record is not proof that no maintenance occurred. A model should not be trained against incomplete labels without documented caveats.
6. **Design for the operating environment.** Test language, connectivity, device access, power, user roles and offline requirements with actual staff before selecting a UI or deployment design.
7. **Separate prediction from impact.** A model can rank risk without reducing downtime; intervention capacity, parts availability, budgets and staff behavior determine whether an alert changes outcomes.

## Innovation that strengthens the proposal

### 1. Data-readiness gate with honest fallback

Build the first useful product around data lineage and quality: source freshness, unmatched assets, missingness, duplicate events, invalid units and coverage by asset. Display the limits directly. Continue to provide useful history and transparent schedule/rule indicators when the predictive gate is not met; never dress a rule as AI.

### 2. Capacity-aware, explainable work queue

Optimize for a real maintenance team's weekly inspection capacity rather than an abstract probability threshold. Let managers set operational constraints (available inspection slots, geography, criticality and approved safety rules) and see why rank changed. Do not automatically trade off safety against cost.

### 3. Closed-loop recommendation ledger

Record each recommendation as an immutable versioned event: evidence snapshot, rule/model version, horizon, explanation, recipient, user disposition, reason and verified outcome. This enables audit, feedback, evaluation and rollback, and discourages silent rewriting of past predictions.

### 4. Human knowledge as structured evidence

Allow technicians to correct an asset history, confirm/decline a suggested issue category, and record observations using a small controlled vocabulary plus notes. Keep the original source value and the correction trail. Use this to improve data quality before assuming more sophisticated ML will solve sparse records.

### 5. Maintenance and parts readiness signal

Where inventory data is authorized and reliable, show whether a proposed intervention is actionable given part availability and expected lead time. Keep this as planning context—not an automatically generated procurement or expenditure decision. This creates a practical link between prediction and execution.

### 6. Offline-tolerant field workflow

Assess connectivity during discovery. If needed, design inspection capture to save locally, visibly show unsynchronized records, and reconcile safely when online. Avoid offline storage of sensitive data unless threat modeling, device controls and retention are approved.

### 7. Value and fairness evaluation

Measure false-alert burden, missed-event cost, lead time and staff capacity alongside model metrics. Compare performance by asset class, age, usage intensity, institution unit and data-coverage group where sample sizes and lawful use allow. Report uncertainty and avoid comparisons that expose individuals or imply unsupported causality.

## Recommended innovation sequence

| Stage | What is novel/useful | Evidence required to advance |
|---|---|---|
| Discover | Shared event definitions, system-of-record map and service blueprint | Institution owners and users validate workflow |
| Foundation | Asset identity resolution, data quality scorecard, source lineage | Authorized sample data passes documented checks |
| MVP | History, rules, triage queue, disposition ledger | Staff can use and explain the queue in a workflow trial |
| Predictive pilot | Time-aware, calibrated model with abstention and explanations | Adequate labels, benchmark improvement and acceptable alert burden |
| Optimize | Capacity/parts-aware planning and feedback evaluation | Measured operational value and governance approval |

## Primary references

- NIST, *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*, NIST AI 100-1 (2023): <https://doi.org/10.6028/NIST.AI.100-1>. Voluntary, use-case-agnostic risk management framework; informs the project’s govern/map/measure/manage review, not Rwanda legal compliance.
- NIST, AI RMF overview and current revision status: <https://www.nist.gov/itl/ai-risk-management-framework>. The page notes that AI RMF 1.0 is being revised; recheck before a formal governance baseline.
- NIST, AI RMF Playbook: <https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook>. Practical voluntary suggestions for applying the framework.
- Government of Rwanda ministry directory: <https://www.gov.rw/government/institutions/ministries>. Source for the dated central-government catalog snapshot; office-holder data is intentionally not stored.
- Government of Rwanda local-government directory: <https://www.gov.rw/government/directory/local-government>. Source for the City of Kigali, four provinces, and 30 districts.
- Government of Rwanda overview: <https://www.gov.rw/overview>. Cross-check for 19 ministries, four provinces plus the City of Kigali, and 30 districts.
- Government of Rwanda portal: <https://www.gov.rw/>. A starting point for locating official services and agency contacts; not evidence for a particular system’s API or data availability.
- Rwanda Law No. 058/2021 relating to the protection of personal data and privacy: locate and verify the authoritative current text through the [Rwanda laws portal](https://amategeko.gov.rw/) and [Rwanda Law Reform Commission](https://www.rlrc.gov.rw/mandate/laws-of-rwanda), then confirm implementing requirements and applicability with the institution’s legal/data-protection officer before processing. The source materials identify compliance as a constraint, but this repository does not provide a legal determination.

**Source quality note:** Searches did not yield a retrievable official publication in this pass confirming the cited fleet-management and IFMIS capabilities or their integration interfaces. Do not cite the supplied project notes as independent proof. Record the institutional owner, official document/URL, verification date and confirmed interface in a decision record when obtained.
