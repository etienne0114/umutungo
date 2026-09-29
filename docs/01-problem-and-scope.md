# Problem, users, and pilot boundaries

## Validated-problem draft

Government fleet and asset teams need to decide which assets to inspect or maintain first. Fixed schedules, operator reports, inspections, asset registers, and maintenance histories provide useful information, but fragmented records and limited condition-based prioritization can make it difficult to identify emerging maintenance needs early. The result may be avoidable downtime, reactive work, or maintenance effort spent on lower-priority assets. The scale and causes of these effects have not yet been quantified for a participating institution.

**For fleet/asset managers and maintenance officers, GovAsset Insight will combine authorized asset, inspection, usage, and work-history information into a traceable prioritized work queue. It will show the evidence and uncertainty behind each flag, let staff record a decision and outcome, and measure whether it improves maintenance planning against an agreed baseline. It will not diagnose a mechanical fault or autonomously authorize a repair.**

This wording is a discovery hypothesis, not a claim that all government institutions have the same workflow or data.

## Users and jobs

| User | Job to be done | Product support |
|---|---|---|
| Fleet or asset manager | See exposure, prioritize work, plan budgets and resources | Fleet-wide queue, filters, workload and outcome summaries |
| Maintenance officer | Decide which assets need inspection or preventive work | Actionable flags with reason, evidence date, confidence/coverage, and due-by guidance |
| Technician/inspector | Record observations, defects, work and verified outcomes | Mobile-friendly inspection and work-history capture, including offline-safe draft workflow if discovery confirms need |
| Driver/operator | Report an observed issue | Structured issue submission with clear severity and asset identification |
| ICT/data steward | Control integrations, data quality and access | Import status, field lineage, validation errors, role controls and audit trail |
| Auditor/leadership | Understand decisions and pilot impact | Read-only reports linking recommendations, human decisions and outcomes |

## Proposed workflow

1. Ingest approved extracts or interfaces from the systems designated as authoritative.
2. Validate identifiers, dates, units, duplicate records, missing values and source freshness.
3. Present asset history and schedule/rule-based indicators even if predictive data is not ready.
4. When validated, rank assets by a defined maintenance event and prediction horizon.
5. Show supporting observations, model/rule version, uncertainty and a recommended next step.
6. A responsible user accepts, defers or rejects the recommendation and records a reason.
7. Record the inspection/work outcome and compare it with the flag to evaluate usefulness.

## Scope for a first pilot

**In scope:** one participating institution; a mutually selected asset class and cohort; data inventory and baseline; authorized import/integration; asset timeline; inspection and maintenance capture or linking; transparent prioritization; human review; auditability; pilot evaluation.

**Out of scope unless separately approved:** replacing official fleet, IFMIS, procurement, finance, or inventory functions; autonomous work orders or spending; automatic removal of assets from service; vehicle telematics/IoT hardware procurement; generative-AI diagnosis; multi-institution rollout; claims of reduced costs or failures before measured evidence.

## Evidence status and open assumptions

| Claim or assumption | Current status | How to validate |
|---|---|---|
| A participating institution has a prioritization problem worth solving | Problem-framing hypothesis | Interviews, workflow walk-through, maintenance planning observation |
| Existing fleet, asset, finance or inventory systems contain useful data | Mentioned in source notes; not independently confirmed for a specific institution | Institution ICT/data-system inventory and authorized sample export |
| Staff can act on ranked inspection recommendations | Unvalidated | Co-design queue and observe a tabletop/workflow trial |
| Historical data can support prediction | Unknown | Data profiling, label assessment, leakage audit and baseline experiment |
| Integration can be authorized and maintained | Unknown | Data-sharing, security, procurement and system-owner review |

## Success and guardrails

Agree a baseline and target definitions with the institution before the pilot. Track:

- Recommendation quality at an actionable inspection capacity (precision/recall or precision-at-k, not accuracy alone).
- Lead time between an alert and a verified maintenance event.
- Planned versus reactive work and unplanned downtime, with definitions and comparable observation periods.
- Recommendation review, acceptance/defer/reject rates and recorded reasons.
- Data completeness, freshness, duplicate rate and successful asset-identity matching.
- User task completion and time-to-triage.
- Cost measures only where reliable cost and attribution data exists.

Do not carry forward unsupported fixed targets such as 80% detection, 30% downtime reduction, 20% cost reduction, or 90% adoption as commitments. Establish achievable thresholds after baseline, sample size and operational capacity are known.

The system must abstain or fall back to clearly labeled schedule/rule information when coverage is inadequate. Predictions are prioritization aids, not confirmations of failure. Human approval and existing safety procedures always take precedence.
