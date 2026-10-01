"""Triage analysis orchestration.

Turns scoped assets and their maintenance history into a deterministic
:class:`TriageAnalysis` (summary + institution priorities + per-asset
assessments) using the rule/math engine. The same structures back both the
live preview and the persisted, reproducible triage-run snapshot.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from govasset_api.models import Asset, MaintenanceRecord
from govasset_api.services.institution_analysis import (
    InstitutionAssessment,
    InstitutionPriorityConfig,
    DEFAULT_INSTITUTION_CONFIG,
    build_institution_assessments,
)
from govasset_api.services.risk_engine import (
    DEFAULT_CONFIG,
    AssetAssessment,
    MaintenanceAggregate,
    RiskConfig,
    assess_asset,
)

ATTENTION_PRIORITIES = ("urgent", "high", "medium")


@dataclass
class TriageSummary:
    total_institutions: int = 0
    total_assets: int = 0
    high_risk_assets: int = 0
    critical_assets: int = 0
    medium_risk_assets: int = 0
    low_risk_assets: int = 0
    insufficient_data_assets: int = 0
    maintenance_candidates: int = 0
    replacement_candidates: int = 0
    maintenance_events: int = 0
    assets_with_maintenance_history: int = 0
    data_quality_notes: list[str] = field(default_factory=list)


@dataclass
class TriageAnalysis:
    generated_on: date
    scope_name: str
    summary: TriageSummary
    institutions: list[InstitutionAssessment]
    assets: list[AssetAssessment]


def load_maintenance_aggregates(
    session: Session,
    asset_ids: Sequence[int],
    as_of: date,
    config: RiskConfig = DEFAULT_CONFIG,
) -> dict[int, MaintenanceAggregate]:
    """One grouped query produces every per-asset maintenance total we need."""

    if not asset_ids:
        return {}
    recent_window_start = as_of - timedelta(days=config.recent_window_days)
    recent_repeat_start = as_of - timedelta(days=config.recent_repeat_window_days)
    rows = session.execute(
        select(
            MaintenanceRecord.asset_id,
            func.count(MaintenanceRecord.id),
            func.max(MaintenanceRecord.event_date),
            func.sum(case((MaintenanceRecord.event_date >= recent_window_start, 1), else_=0)),
            func.sum(case((MaintenanceRecord.event_date >= recent_repeat_start, 1), else_=0)),
            func.sum(case((MaintenanceRecord.planned.is_(False), 1), else_=0)),
            func.sum(func.coalesce(MaintenanceRecord.downtime_hours, 0.0)),
            func.count(MaintenanceRecord.downtime_hours),
        )
        .where(MaintenanceRecord.asset_id.in_(list(asset_ids)))
        .group_by(MaintenanceRecord.asset_id)
    ).all()

    aggregates: dict[int, MaintenanceAggregate] = {}
    for (
        asset_id,
        count,
        last_event_date,
        recent_window_count,
        recent_repeat_count,
        unplanned_count,
        total_downtime,
        downtime_records,
    ) in rows:
        aggregates[int(asset_id)] = MaintenanceAggregate(
            maintenance_count=int(count or 0),
            last_event_date=last_event_date,
            recent_window_count=int(recent_window_count or 0),
            recent_repeat_count=int(recent_repeat_count or 0),
            unplanned_count=int(unplanned_count or 0),
            total_downtime_hours=float(total_downtime or 0.0),
            downtime_records=int(downtime_records or 0),
        )
    return aggregates


def summarize(
    assessments: Sequence[AssetAssessment],
    institutions: Sequence[InstitutionAssessment],
) -> TriageSummary:
    summary = TriageSummary(
        total_institutions=len([item for item in institutions if item.institution_id is not None]),
        total_assets=len(assessments),
        assets_with_maintenance_history=sum(
            1 for item in assessments if item.has_maintenance_history
        ),
        maintenance_events=sum(item.maintenance_count for item in assessments),
    )
    for item in assessments:
        if item.risk_level == "critical":
            summary.critical_assets += 1
        elif item.risk_level == "high":
            summary.high_risk_assets += 1
        elif item.risk_level == "medium":
            summary.medium_risk_assets += 1
        elif item.risk_level == "low":
            summary.low_risk_assets += 1
        else:
            summary.insufficient_data_assets += 1
        if item.maintenance_priority in ATTENTION_PRIORITIES:
            summary.maintenance_candidates += 1
        if item.replacement_candidate:
            summary.replacement_candidates += 1
    # ``high_risk_assets`` reports the combined high + critical count for KPI display.
    summary.high_risk_assets += summary.critical_assets
    return summary


def build_triage_analysis(
    session: Session,
    assets: Sequence[Asset],
    as_of: date,
    institutions_by_id: dict[int, tuple[str, str | None]],
    *,
    scope_name: str = "All government institutions",
    config: RiskConfig = DEFAULT_CONFIG,
    institution_config: InstitutionPriorityConfig = DEFAULT_INSTITUTION_CONFIG,
) -> TriageAnalysis:
    """Compute the full deterministic analysis for a set of scoped assets."""

    aggregates = load_maintenance_aggregates(session, [asset.id for asset in assets], as_of, config)
    assessments = [
        assess_asset(
            asset,
            aggregates.get(asset.id, MaintenanceAggregate()),
            as_of,
            config,
            institution_name=(
                institutions_by_id.get(asset.institution_id, (None, None))[0]
                if asset.institution_id is not None
                else None
            ),
        )
        for asset in assets
    ]
    institutions = build_institution_assessments(
        assessments, institutions_by_id, as_of, institution_config
    )
    summary = summarize(assessments, institutions)
    summary.data_quality_notes = _data_quality_notes(assets, assessments)
    return TriageAnalysis(
        generated_on=as_of,
        scope_name=scope_name,
        summary=summary,
        institutions=institutions,
        assets=assessments,
    )


def _data_quality_notes(
    assets: Sequence[Asset],
    assessments: Sequence[AssetAssessment],
) -> list[str]:
    notes: list[str] = []
    without_age = sum(
        1
        for asset in assets
        if asset.acquisition_date is None and asset.manufacture_year is None
    )
    without_history = sum(1 for item in assessments if not item.has_maintenance_history)
    unknown_condition = sum(1 for asset in assets if asset.condition == "unknown")
    without_schedule = sum(1 for asset in assets if asset.next_service_due is None)

    if without_history:
        notes.append(
            f"{without_history} asset(s) have no recorded maintenance history; risk reflects age and condition only."
        )
    if without_age:
        notes.append(
            f"{without_age} asset(s) are missing an acquisition date and manufacture year, so age-based factors are excluded."
        )
    if unknown_condition:
        notes.append(
            f"{unknown_condition} asset(s) have an unknown recorded condition."
        )
    if without_schedule:
        notes.append(
            f"{without_schedule} asset(s) have no scheduled next service date."
        )
    return notes
