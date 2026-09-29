# AI-Powered Predictive Maintenance for Government Vehicles & Assets

## Project Overview

### Problem Statement

Government institutions manage vehicles and other physical assets using
asset registers, fleet information, inspections, maintenance records,
usage/mileage data, and scheduled maintenance plans. However,
maintenance decisions can remain largely schedule- or rule-driven,
making it difficult to identify assets that are deteriorating or
becoming high-risk before their next scheduled service.

This can contribute to unexpected failures, asset downtime, emergency
repairs, inefficient maintenance-resource allocation, and difficulty
planning future maintenance needs.

### Proposed Solution

Develop an **AI-powered predictive maintenance platform** that uses
existing government asset, maintenance, inspection, usage, and inventory
data to:

-   Assess asset health and maintenance risk.
-   Identify assets likely to require maintenance.
-   Prioritize high-risk assets for inspection or preventive
    intervention.
-   Provide understandable explanations for AI-generated risk alerts.
-   Support maintenance officers and managers in making data-driven
    decisions.
-   Learn from historical maintenance outcomes over time.

The platform should be a **decision-support system**, not an autonomous
repair-authorization system. Authorized personnel remain responsible for
final maintenance decisions.

------------------------------------------------------------------------

# A1. Problem Definition --- Users, Process & Pain Points

## 1. Primary User(s)

The primary users are **government fleet/asset managers and maintenance
officers/technicians** who are responsible for monitoring, inspecting,
and maintaining government vehicles and assets.

They manage assets with different ages, usage levels, conditions, and
maintenance histories, but often rely on fixed schedules, mileage,
inspection dates, and historical records to plan maintenance.

The main pain point is that they need better visibility into **which
assets are actually becoming high-risk**, rather than only knowing which
assets are due for scheduled maintenance. This can make it difficult to
identify deterioration early and act before unexpected failure.

Drivers and operators are important secondary users because they use
assets daily and can report unusual conditions or problems.

## 2. Current Situation

Government vehicles and assets are managed through asset registers,
fleet systems, inspections, maintenance records, usage/mileage
information, and scheduled maintenance plans.

A typical workflow is:

1.  Asset is registered.
2.  Asset is operated.
3.  Usage, mileage, inspections, and defects are recorded.
4.  Maintenance is triggered by a schedule, mileage, inspection
    interval, or reported problem.
5.  Technician inspects and repairs the asset.
6.  Maintenance cost, parts, and outcomes are recorded.
7.  Managers use historical records and professional judgment to plan
    future maintenance.

The key limitation is that these processes mainly answer:

> **"When is maintenance due?"**

rather than:

> **"Which asset is becoming high-risk and needs attention first?"**

## 3. Pain Points & Bottlenecks

The main pain point is that **maintenance decisions are not sufficiently
condition- and risk-driven**.

This makes it difficult to identify high-risk or deteriorating assets
early. As a result, institutions may experience:

-   Unexpected breakdowns.
-   Unplanned asset downtime.
-   Emergency repairs.
-   Inefficient use of maintenance resources.
-   Difficulties planning spare parts and maintenance budgets.
-   Underuse of historical maintenance and inspection data.

------------------------------------------------------------------------

# A1 Continued --- Evidence, Root Causes & Existing Solutions

## 4. Evidence & Data

The project can use existing information from:

-   Government asset registers.
-   Fleet-management systems.
-   Maintenance records.
-   Inspection records.
-   Mileage and usage data.
-   Inventory and spare-parts records.
-   Repair history.
-   Maintenance costs.
-   Downtime.
-   Accident or incident records where available.
-   Operator/driver reports where available.

The most valuable evidence is the historical pattern in these records:

-   How often an asset is repaired.
-   How its condition changes over time.
-   Which parts repeatedly fail.
-   How usage relates to maintenance needs.
-   How much maintenance costs.
-   How long assets remain unavailable.

### Evidence principle

Do not invent statistics before the pilot data is audited. Establish
baseline values from the selected institution first.

------------------------------------------------------------------------

## 5. Root Causes

### Root Cause 1 --- Schedule-driven maintenance

Maintenance planning can depend heavily on dates, mileage, or predefined
service intervals. These rules do not always represent the actual
condition of an individual asset.

### Root Cause 2 --- Data fragmentation

Asset, inspection, maintenance, usage, and inventory information may
exist in different systems, databases, or records. The data is therefore
not automatically converted into a single asset-health view.

### Root Cause 3 --- Lack of predictive intelligence

Existing records can tell the institution what happened in the past, but
a dedicated predictive analytics layer is needed to estimate future
maintenance risk and prioritize intervention.

------------------------------------------------------------------------

## 6. What Has Already Been Tried?

Rwanda already has digital asset and fleet-management capabilities. The
government has a **Digitized Fleet Management System**, and Smart IFMIS
includes **Asset & Inventory** functionality.

These systems address important needs such as recording, managing, and
monitoring asset information.

The proposed project should therefore **not duplicate existing
asset-management systems**.

Instead, it should add an intelligence layer:

``` text
Existing Government Systems
        ↓
Data Integration
        ↓
Data Quality & Processing
        ↓
AI Risk Prediction
        ↓
Maintenance Priority
        ↓
Human Review
        ↓
Preventive Maintenance
```

The innovation is the transformation of existing data into **predictive
and actionable maintenance intelligence**.

------------------------------------------------------------------------

# 7. Operational & Systemic Constraints

## Policy & Legal Constraints

The platform must comply with applicable government data-governance,
cybersecurity, and personal-data protection requirements.

If the system processes personal information such as driver/operator
information, appropriate data-protection controls must be applied.

Required controls include:

-   Lawful data processing.
-   Role-based access.
-   Data security.
-   Audit logging.
-   Controlled data sharing.
-   Appropriate retention policies.
-   Secure storage and transmission.

## Technical & Infrastructure Constraints

The project depends on:

-   Sufficient historical maintenance data.
-   Reliable asset records.
-   Consistent inspection records.
-   Consistent maintenance records.
-   Access to usage/mileage information.
-   Data integration mechanisms.
-   Reliable infrastructure.
-   Approved APIs or data-export mechanisms.

Different government systems may use different formats, so data
cleaning, mapping, validation, and integration will be required.

## Financial & Operational Constraints

The initial pilot should be limited to **one public institution** and a
manageable asset population.

The pilot should reuse existing systems and infrastructure where
possible rather than replacing them.

Avoid unnecessary infrastructure complexity during the pilot.

## User & Language Constraints

The system should provide a simple interface that maintenance staff can
use without AI expertise.

Risk information should be expressed clearly:

-   Low Risk.
-   Medium Risk.
-   High Risk.
-   Critical Risk.

Each prediction should explain the major contributing factors.

------------------------------------------------------------------------

# 8. Unvalidated Assumptions

These assumptions must be validated during the initial field assessment.

## User Behavior Assumption

We assume fleet managers and maintenance officers will use AI-generated
risk alerts when planning inspections and maintenance.

### Validation

Interview maintenance staff and demonstrate a simple dashboard. Confirm
whether recommendations fit their workflow and what information they
require before trusting an alert.

## Institutional Capability Assumption

We assume the selected institution has staff capable of recording
maintenance, inspection, and asset information consistently.

### Validation

Map the existing maintenance workflow and interview responsible staff.

## Data Access Assumption

We assume the institution can provide sufficient historical asset,
maintenance, inspection, and usage data.

### Validation

Conduct a data audit covering:

-   Number of assets.
-   Historical period.
-   Available fields.
-   Missing values.
-   Duplicate records.
-   Maintenance outcomes.
-   Inspection history.
-   Usage/mileage history.

## Integration Assumption

We assume the required data can be accessed through approved APIs,
exports, or other authorized mechanisms.

### Validation

Meet the institution's ICT/data team and document the available systems,
access mechanisms, formats, and restrictions.

## AI Feasibility Assumption

We assume historical data contains enough useful patterns to predict
future maintenance needs.

### Validation

Run data-quality analysis and a simple baseline ML experiment before
developing complex models.

------------------------------------------------------------------------

# A2. Success Definition --- Desired Change, Metrics & Failure Boundaries

## 1. Desired Change

### For the Primary User

Enable maintenance officers to identify deteriorating and high-risk
assets before failure instead of relying mainly on fixed maintenance
schedules.

The system should provide:

-   Asset-health score.
-   Maintenance-risk score.
-   Predicted maintenance probability.
-   Risk level.
-   Main contributing factors.
-   Recommended inspection or maintenance action.

### For the Institution

Improve maintenance planning by using existing asset, inspection,
maintenance, and usage data to prioritize interventions.

Managers should have better visibility into:

-   Current asset condition.
-   High-risk assets.
-   Upcoming maintenance needs.
-   Maintenance history.
-   Maintenance costs.
-   Asset downtime.

### Systemic Impact

Support a shift from mainly schedule-driven and reactive maintenance
toward:

> **Data-driven preventive and predictive asset management.**

------------------------------------------------------------------------

# 2. Measurable Success Indicators

The pilot should establish baseline values before setting final
numerical targets.

## Metric 1 --- Prediction Accuracy

Measure whether the AI can reliably identify assets that later require
maintenance.

Possible metrics:

-   Precision.
-   Recall.
-   F1-score.
-   ROC-AUC where appropriate.
-   Calibration.

## Metric 2 --- Early Identification

Measure the percentage of maintenance events that the system
successfully identifies before the actual maintenance/failure event.

## Metric 3 --- Planned vs Reactive Maintenance

Measure whether the proportion of planned/preventive maintenance
increases during the pilot.

## Metric 4 --- Unplanned Downtime

Measure changes in downtime caused by unexpected failures compared with
the baseline period.

## Metric 5 --- User Adoption

Measure whether maintenance officers and managers actually use AI
recommendations in maintenance planning.

------------------------------------------------------------------------

# Failure Boundaries

The system should have clear limits.

The AI should **not**:

-   Automatically authorize expensive repairs.
-   Automatically remove assets from service without human confirmation.
-   Invent mechanical faults.
-   Present an uncertain prediction as a fact.
-   Replace qualified technicians.
-   Make predictions when required data is insufficient.
-   Override official government asset records without authorization.

If the model confidence is too low, the system should say:

> **Insufficient data for reliable prediction --- manual inspection
> recommended.**

This is important for safety, trust, and responsible AI.

------------------------------------------------------------------------

# Pilot Scope

## Target

**One public institution.**

The pilot should include a defined group of government vehicles/assets
with sufficient historical data.

## Pilot objectives

1.  Understand the institution's current maintenance workflow.
2.  Audit available data.
3.  Integrate selected datasets.
4.  Build an asset-health dataset.
5.  Establish baseline analytics.
6.  Train an initial predictive model.
7.  Validate model performance.
8.  Deploy a maintenance-risk dashboard.
9.  Test recommendations with maintenance personnel.
10. Measure operational outcomes.

------------------------------------------------------------------------

# Recommended Technical Architecture

``` text
                    GOVERNMENT SYSTEMS
                          │
          ┌───────────────┼────────────────┐
          │               │                │
        IFMIS          Fleet System    Maintenance
       / Assets                         / Inspection
          │               │                │
          └───────────────┼────────────────┘
                          ↓
                 DATA INTEGRATION
                          ↓
                 DATA VALIDATION
                          ↓
                 DATA PROCESSING
                          ↓
                    PostgreSQL
                          │
              ┌───────────┴───────────┐
              ↓                       ↓
        Operational Data        ML Feature Data
                                      ↓
                               ML Training
                                      ↓
                            XGBoost / sklearn
                                      ↓
                              Model Validation
                                      ↓
                                  MLflow
                                      ↓
                              Prediction API
                                      ↓
                              FastAPI Backend
                                      ↓
                              Web Dashboard
                                      ↓
                         Maintenance Officers
                                      ↓
                              Human Decision
                                      ↓
                            Maintenance Action
                                      ↓
                            Outcome Feedback
                                      ↓
                              Future Training
```

------------------------------------------------------------------------

# Recommended Technology Stack

## Frontend

**Next.js + React + TypeScript**

Use for:

-   Asset dashboard.
-   Risk dashboard.
-   Maintenance planning.
-   Inspection views.
-   Reports.
-   User management.
-   Analytics.

## Backend

**Python + FastAPI**

Use for:

-   REST APIs.
-   Authentication/authorization integration.
-   Asset services.
-   Maintenance services.
-   Prediction endpoints.
-   Analytics endpoints.
-   Integration with ML models.

Python is preferred because the application and ML/data-processing
components can use the same ecosystem.

## Database

**PostgreSQL**

Core entities:

``` text
assets
asset_usage
inspections
maintenance_records
repairs
parts
inventory
work_orders
predictions
users
audit_logs
```

## Data Engineering

Use:

-   Python.
-   Pandas and/or Polars.
-   Prefect for scheduled workflows.

Pipeline:

``` text
Source Data
    ↓
Extract
    ↓
Validate
    ↓
Clean
    ↓
Normalize
    ↓
Transform
    ↓
Feature Engineering
    ↓
ML-ready Dataset
```

## Machine Learning

### Initial models

Start with:

-   Logistic Regression as a baseline.
-   Random Forest where useful.
-   XGBoost for the main tabular-data model.

Do not begin with deep learning unless the data demonstrates a need for
it.

### Example features

``` text
asset_age
mileage
days_since_last_service
maintenance_count
repair_count
inspection_score
maintenance_cost
fault_frequency
downtime
usage_frequency
parts_replacement_frequency
```

### Example output

``` text
Asset: GOV-00125

Risk Score: 81%
Risk Level: HIGH

Predicted maintenance:
Within next 30 days

Main factors:
- High mileage
- Increasing repair frequency
- Long period since inspection
- Previous recurring fault

Recommended action:
Schedule inspection
```

## Explainable AI

Use **SHAP** or another appropriate explainability method to show the
main factors contributing to predictions.

The user should understand:

> **Why did the system flag this asset?**

not simply:

> **The AI says HIGH RISK.**

## ML Operations

Use **MLflow** for:

-   Experiment tracking.
-   Model versions.
-   Model parameters.
-   Evaluation metrics.
-   Model artifacts.
-   Production model identification.

Example:

``` text
Model v1 → Baseline
Model v2 → Random Forest
Model v3 → XGBoost
Model v4 → Improved XGBoost
```

## Data Pipeline

Use **Prefect** for:

-   Scheduled data synchronization.
-   Data validation.
-   Feature generation.
-   Prediction jobs.
-   Periodic model workflows.

## Cache and Background Jobs

Use **Redis** for:

-   Caching.
-   Background jobs.
-   Prediction queues.
-   Temporary computation.

Redis should not replace PostgreSQL as the primary database.

## File Storage

Use **S3-compatible object storage or MinIO** for:

-   Inspection documents.
-   Photos.
-   Invoices.
-   Reports.
-   Datasets.
-   Model artifacts.

Store file metadata and references in PostgreSQL.

------------------------------------------------------------------------

# Security Architecture

## Authentication

Use:

-   OAuth2/OIDC.
-   Government identity integration where available.
-   MFA where required.

## Role-Based Access Control

Suggested roles:

``` text
Super Admin
    ↓
Institution Admin
    ↓
Fleet/Asset Manager
    ↓
Maintenance Officer
    ↓
Technician
    ↓
Viewer/Auditor
```

## Security Requirements

Implement:

-   TLS/HTTPS.
-   Encryption at rest where appropriate.
-   Role-based authorization.
-   Least-privilege access.
-   Secure secrets management.
-   Audit logging.
-   API authentication.
-   Input validation.
-   Database access controls.
-   Backup and recovery.
-   Security monitoring.

------------------------------------------------------------------------

# Monitoring

## System Monitoring

Use:

**Prometheus + Grafana**

Monitor:

-   API availability.
-   CPU/memory.
-   Database health.
-   Request latency.
-   Error rates.
-   Background jobs.
-   Prediction-service health.

## ML Monitoring

Monitor:

-   Prediction accuracy.
-   Data drift.
-   Feature drift.
-   Model performance.
-   False positives.
-   False negatives.
-   Prediction volume.
-   Model confidence.

------------------------------------------------------------------------

# Development Architecture

## Pilot Recommendation

Do **not** start with a large microservices architecture.

Use a:

> **Modular monolith + separate ML pipeline**

Example:

``` text
                 Next.js
                    │
                    ↓
               FastAPI App
                    │
       ┌────────────┼────────────┐
       ↓            ↓            ↓
    Assets      Maintenance   Analytics
       │            │            │
       └────────────┼────────────┘
                    ↓
                PostgreSQL
                    │
                    ↓
              ML Pipeline
        Python + XGBoost + MLflow
```

This is easier to:

-   Develop.
-   Test.
-   Deploy.
-   Maintain.
-   Demonstrate during the pilot.

If the platform later grows to many institutions and high workloads,
selected components can be separated into services.

------------------------------------------------------------------------

# Core Functional Requirements

## Asset Management

The system should allow authorized users to:

-   View assets.
-   Search assets.
-   Filter assets.
-   View asset history.
-   View asset condition.
-   View asset usage.
-   View maintenance history.

## Inspection Management

Users should be able to:

-   Record inspections.
-   Record defects.
-   Record inspection scores.
-   Attach evidence where appropriate.
-   View previous inspections.

## Maintenance Management

Users should be able to:

-   Create maintenance records.
-   Record faults.
-   Record repairs.
-   Record parts used.
-   Record costs.
-   Record downtime.
-   Track maintenance status.

## Predictive Maintenance

The system should:

-   Calculate asset risk.
-   Predict maintenance probability.
-   Identify high-risk assets.
-   Explain predictions.
-   Recommend inspection/maintenance priority.
-   Record whether recommendations were accepted or rejected.

## Dashboard

Show:

-   Total assets.
-   Healthy assets.
-   Medium-risk assets.
-   High-risk assets.
-   Critical assets.
-   Maintenance due.
-   Predicted maintenance.
-   Unplanned downtime.
-   Maintenance costs.
-   Asset availability.

------------------------------------------------------------------------

# Data Model --- Initial Version

``` text
Institution
    │
    └── Assets
          │
          ├── Usage Records
          │
          ├── Inspections
          │
          ├── Maintenance Records
          │       │
          │       └── Parts Used
          │
          ├── Work Orders
          │
          ├── Downtime Records
          │
          └── AI Predictions
```

## Important Asset Fields

``` text
asset_id
asset_code
asset_type
make
model
acquisition_date
institution_id
location
status
condition
```

## Important Maintenance Fields

``` text
maintenance_id
asset_id
date
maintenance_type
fault_type
description
cost
parts_used
downtime
technician
outcome
```

## Important Prediction Fields

``` text
prediction_id
asset_id
prediction_date
risk_score
risk_level
prediction_window
model_version
confidence
explanation
recommended_action
actual_outcome
```

------------------------------------------------------------------------

# AI Development Process

## Step 1 --- Data Audit

Before ML:

``` text
How many assets?
How many years of history?
How many maintenance events?
How many failures?
How much missing data?
How many duplicate records?
How consistent are inspection records?
```

## Step 2 --- Data Cleaning

Handle:

-   Missing values.
-   Duplicate assets.
-   Incorrect dates.
-   Inconsistent categories.
-   Invalid mileage.
-   Inconsistent maintenance labels.

## Step 3 --- Feature Engineering

Create features such as:

``` text
asset_age
days_since_service
maintenance_frequency
repair_frequency
average_repair_cost
mileage_since_service
inspection_trend
downtime_frequency
```

## Step 4 --- Baseline Model

Start with a simple model.

## Step 5 --- Advanced Model

Evaluate XGBoost or another suitable model.

## Step 6 --- Validation

Use time-aware validation where appropriate so the model does not learn
from future information.

## Step 7 --- Explainability

Add SHAP or another appropriate explanation mechanism.

## Step 8 --- Pilot Deployment

Deploy the validated model behind a prediction API.

## Step 9 --- Monitor

Track model performance and operational outcomes.

------------------------------------------------------------------------

# Important Data Science Risk

The biggest technical risk is **not the ML algorithm**.

It is insufficient or poor-quality historical data.

If the institution only has:

``` text
Asset
Purchase date
Last service
Repair cost
```

the model will have limited predictive capability.

If it has:

``` text
Mileage over time
Inspection history
Repair history
Fault types
Parts replaced
Maintenance costs
Downtime
Usage
```

the predictive capability can be much stronger.

Therefore:

> **Data readiness must be validated before committing to an advanced ML
> model.**

------------------------------------------------------------------------

# Recommended Pilot Phases

## Phase 1 --- Discovery & Data Audit

-   Identify stakeholders.
-   Map current workflow.
-   Identify data sources.
-   Confirm access.
-   Audit data quality.
-   Define baseline KPIs.

## Phase 2 --- Data Platform

-   Set up PostgreSQL.
-   Build data-import/integration layer.
-   Clean and normalize data.
-   Build asset and maintenance views.

## Phase 3 --- MVP Dashboard

Build:

-   Asset dashboard.
-   Maintenance history.
-   Inspection records.
-   Risk overview.
-   Basic analytics.

## Phase 4 --- AI Prototype

Build:

-   Baseline model.
-   XGBoost model.
-   Risk scoring.
-   Explainability.
-   Model evaluation.

## Phase 5 --- Pilot

Deploy to selected users.

Collect:

-   Predictions.
-   User feedback.
-   Accepted/rejected recommendations.
-   Actual maintenance outcomes.

## Phase 6 --- Evaluation

Compare:

``` text
Before Pilot
      vs
During Pilot
```

Measure:

-   Prediction performance.
-   Early identification.
-   Planned maintenance.
-   Unplanned downtime.
-   User adoption.
-   Maintenance cost indicators.

------------------------------------------------------------------------

# Technology Summary

  Layer             Recommended Technology
  ----------------- -----------------------------------------
  Frontend          Next.js + React + TypeScript
  Backend           Python + FastAPI
  Database          PostgreSQL
  Data Processing   Pandas / Polars
  ML                scikit-learn + XGBoost
  Explainability    SHAP
  ML Tracking       MLflow
  Workflow/ETL      Prefect
  Cache/Queue       Redis
  Object Storage    MinIO / S3-compatible storage
  Authentication    OAuth2 / OIDC
  Authorization     RBAC
  Containers        Docker
  Monitoring        Prometheus + Grafana
  API               REST + OpenAPI
  OS                Linux
  Architecture      Modular monolith + separate ML pipeline

------------------------------------------------------------------------

# Institutional Focal Person

The **Institutional Focal Person** should be the person designated by
the pilot institution to coordinate the project.

Suitable roles include:

-   Fleet Manager.
-   Asset Management Officer.
-   Maintenance Manager/Officer.
-   ICT/Digital Transformation Officer.
-   Operations/Planning Officer.

If the institution has not yet designated someone:

> **Institutional Focal Person: To be designated by the pilot
> institution.**

The focal person should ideally understand the institution's
asset-maintenance workflow and be able to coordinate access to relevant
staff, systems, and data.

------------------------------------------------------------------------

# Final Project Positioning

The project should be positioned as:

> **An AI-powered decision-support platform that transforms existing
> government asset and maintenance data into predictive asset-health
> insights, enabling maintenance teams to identify high-risk assets
> earlier, prioritize preventive interventions, and improve asset
> availability and maintenance planning.**

The project should **complement existing government systems rather than
replace them**.

The core innovation is:

``` text
Existing Government Data
        ↓
Integration
        ↓
Data Quality
        ↓
Predictive Analytics
        ↓
Asset Risk
        ↓
Explainable Recommendation
        ↓
Human Decision
        ↓
Preventive Maintenance
        ↓
Outcome Feedback
        ↓
Continuous Improvement
```

# Key Principle

> **Do not build AI first. Build the data foundation first, prove that
> the data can support prediction, then introduce the simplest model
> that provides reliable value.**
