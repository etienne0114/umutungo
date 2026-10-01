"""Explainable rule-based triage and recommendation history endpoints."""

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from govasset_api.api.dependencies import find_recommendation
from govasset_api.authorization import (
    TenantScope,
    ensure_permission,
    scoped_assets,
    scoped_runs,
)
from govasset_api.models import Asset, Institution, Recommendation, RecommendationEvent, TriageRun
from govasset_api.schemas import (
    AssetAssessmentRead,
    AssetRead,
    InstitutionAssessmentRead,
    RecommendationEventCreate,
    RecommendationEventRead,
    RecommendationRead,
    RiskLevel,
    TriageAnalysisRead,
    TriageItem,
    TriageRunRead,
    TriageSummaryRead,
)
from govasset_api.services.institution_analysis import build_institution_assessments
from govasset_api.services.risk_engine import ENGINE_VERSION, AssetAssessment
from govasset_api.services.triage_service import (
    TriageAnalysis,
    build_triage_analysis,
    summarize,
)
from govasset_api.triage import RULE_VERSION, assess_asset

RISK_RANK = {
    RiskLevel.CRITICAL: 0,
    RiskLevel.HIGH: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.INSUFFICIENT_DATA: 3,
    RiskLevel.LOW: 4,
}

PRIORITY_RANK = {"urgent": 0, "high": 1, "medium": 2, "low": 3, "monitor": 4}


def _load_institutions(session: Session, institution_ids: set[int]) -> dict[int, tuple[str, str | None]]:
    if not institution_ids:
        return {}
    rows = session.execute(
        select(Institution.id, Institution.name, Institution.code).where(
            Institution.id.in_(institution_ids)
        )
    ).all()
    return {int(row[0]): (row[1], row[2]) for row in rows}


def _scope_name(session: Session, scope: TenantScope) -> str:
    if scope.institution_id is None:
        return "All government institutions"
    institution = session.get(Institution, scope.institution_id)
    return institution.name if institution else "All government institutions"


def _sorted_assessments(assessments: Sequence[AssetAssessment]) -> list[AssetAssessment]:
    return sorted(
        assessments,
        key=lambda item: (
            -(item.risk_score if item.risk_score is not None else -1),
            PRIORITY_RANK.get(item.maintenance_priority, 5),
            item.asset_code,
        ),
    )


def _analysis_read(
    analysis: TriageAnalysis,
    engine_version: str,
    run_id: int | None,
) -> TriageAnalysisRead:
    return TriageAnalysisRead(
        generated_on=analysis.generated_on,
        scope_name=analysis.scope_name,
        engine_version=engine_version,
        persisted_run_id=run_id,
        summary=TriageSummaryRead.model_validate(analysis.summary, from_attributes=True),
        institutions=[
            InstitutionAssessmentRead.model_validate(item, from_attributes=True)
            for item in analysis.institutions
        ],
        assets=[
            AssetAssessmentRead.model_validate(item, from_attributes=True)
            for item in _sorted_assessments(analysis.assets)
        ],
    )


def _assessment_from_recommendation(
    recommendation: Recommendation,
    institutions_by_id: dict[int, tuple[str, str | None]],
) -> AssetAssessment:
    snapshot = recommendation.asset_snapshot or {}
    institution_name = None
    if recommendation.institution_id is not None:
        institution_name = institutions_by_id.get(recommendation.institution_id, (None, None))[0]
    return AssetAssessment(
        asset_id=recommendation.asset_id,
        institution_id=recommendation.institution_id,
        institution_name=institution_name,
        asset_code=recommendation.asset_code or snapshot.get("asset_code", ""),
        asset_type=snapshot.get("asset_type", ""),
        make=snapshot.get("make"),
        model=snapshot.get("model"),
        registration_number=snapshot.get("registration_number"),
        criticality=snapshot.get("criticality", "standard"),
        condition=snapshot.get("condition", "unknown"),
        asset_age_years=recommendation.asset_age_years,
        maintenance_count=recommendation.maintenance_count or 0,
        maintenance_frequency=recommendation.maintenance_frequency,
        days_since_last_maintenance=recommendation.days_since_last_maintenance,
        recent_window_count=recommendation.recent_window_count or 0,
        recent_repeat_count=recommendation.recent_repeat_count or 0,
        unplanned_share=recommendation.unplanned_share,
        total_downtime_hours=recommendation.total_downtime_hours or 0.0,
        has_maintenance_history=bool(recommendation.has_maintenance_history),
        risk_score=recommendation.risk_score,
        risk_level=recommendation.risk_level,
        factor_scores=recommendation.factor_scores or {},
        factor_weights={},
        priority_score=recommendation.priority_score or 0,
        maintenance_priority=recommendation.maintenance_priority or "monitor",
        replacement_score=recommendation.replacement_score or 0,
        replacement_candidate=bool(recommendation.replacement_candidate),
        recommendation=recommendation.recommended_action,
        reasons=list(recommendation.reasons or []),
        evidence=list(recommendation.evidence or []),
    )


def _reconstruct_run_analysis(
    session: Session,
    run: TriageRun,
) -> TriageAnalysis:
    recommendations = session.scalars(
        select(Recommendation).where(Recommendation.run_id == run.id)
    ).all()
    institutions_by_id = _load_institutions(
        session,
        {rec.institution_id for rec in recommendations if rec.institution_id is not None},
    )
    assessments = [
        _assessment_from_recommendation(rec, institutions_by_id) for rec in recommendations
    ]
    institutions = build_institution_assessments(
        assessments, institutions_by_id, run.evaluated_on
    )
    summary = summarize(assessments, institutions)
    summary.data_quality_notes = _assessment_quality_notes(assessments)
    return TriageAnalysis(
        generated_on=run.evaluated_on,
        scope_name=_run_scope_name(session, run),
        summary=summary,
        institutions=institutions,
        assets=assessments,
    )


def _run_scope_name(session: Session, run: TriageRun) -> str:
    if run.institution_id is None:
        return "All government institutions"
    institution = session.get(Institution, run.institution_id)
    return institution.name if institution else "All government institutions"


def _assessment_quality_notes(assessments: Sequence[AssetAssessment]) -> list[str]:
    notes: list[str] = []
    without_history = sum(1 for item in assessments if not item.has_maintenance_history)
    without_age = sum(1 for item in assessments if item.asset_age_years is None)
    unknown_condition = sum(1 for item in assessments if item.condition == "unknown")
    if without_history:
        notes.append(
            f"{without_history} asset(s) had no recorded maintenance history at the time of this run."
        )
    if without_age:
        notes.append(
            f"{without_age} asset(s) were missing age data, so age-based factors were excluded."
        )
    if unknown_condition:
        notes.append(f"{unknown_condition} asset(s) had an unknown recorded condition.")
    return notes


def _run_read(session: Session, run: TriageRun) -> TriageRunRead:
    count = session.scalar(
        select(func.count(Recommendation.id)).where(Recommendation.run_id == run.id)
    )
    return TriageRunRead(
        id=run.id,
        institution_id=run.institution_id,
        evaluated_on=run.evaluated_on,
        rule_version=run.rule_version,
        created_at=run.created_at,
        recommendation_count=count or 0,
        run_name=run.run_name,
        status=run.status or "completed",
        engine_version=run.engine_version,
        total_institutions=run.total_institutions or 0,
        total_assets=run.total_assets or 0,
        high_risk_assets=run.high_risk_assets or 0,
        critical_assets=run.critical_assets or 0,
        maintenance_candidates=run.maintenance_candidates or 0,
        replacement_candidates=run.replacement_candidates or 0,
    )


def create_router(
    get_session: Callable[..., Any],
    current_scope: Callable[..., TenantScope],
) -> APIRouter:
    router = APIRouter(tags=["triage"])

    @router.get("/triage", response_model=list[TriageItem])
    def triage_queue(
        as_of: date | None = Query(default=None, description="Evaluation date; defaults to today."),
        risk_level: RiskLevel | None = None,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        evaluated_on = as_of or date.today()
        assets = session.scalars(
            scoped_assets(select(Asset), scope)
            .where(Asset.active.is_(True))
            .order_by(Asset.asset_code)
        ).all()
        items = [assess_asset(asset, evaluated_on) for asset in assets]
        if risk_level is not None:
            items = [item for item in items if item.risk_level == risk_level]
        return sorted(items, key=lambda item: (RISK_RANK[item.risk_level], item.asset.asset_code))

    @router.get("/triage/analysis", response_model=TriageAnalysisRead)
    def triage_analysis(
        as_of: date | None = Query(default=None, description="Evaluation date; defaults to today."),
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        """Preview the deterministic maintenance analysis without persisting it."""
        evaluated_on = as_of or date.today()
        assets = session.scalars(
            scoped_assets(select(Asset), scope)
            .where(Asset.active.is_(True))
            .order_by(Asset.asset_code)
        ).all()
        institutions_by_id = _load_institutions(
            session, {asset.institution_id for asset in assets if asset.institution_id is not None}
        )
        analysis = build_triage_analysis(
            session,
            assets,
            evaluated_on,
            institutions_by_id,
            scope_name=_scope_name(session, scope),
        )
        return _analysis_read(analysis, ENGINE_VERSION, None)

    @router.post(
        "/triage-runs",
        response_model=TriageRunRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_triage_run(
        as_of: date | None = Query(default=None, description="Evaluation date; defaults to today."),
        run_name: str | None = Query(default=None, max_length=200),
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        ensure_permission(scope, "triage:run")
        evaluated_on = as_of or date.today()
        assets = session.scalars(
            scoped_assets(select(Asset), scope)
            .where(Asset.active.is_(True))
            .order_by(Asset.asset_code)
        ).all()
        institutions_by_id = _load_institutions(
            session, {asset.institution_id for asset in assets if asset.institution_id is not None}
        )
        analysis = build_triage_analysis(
            session,
            assets,
            evaluated_on,
            institutions_by_id,
            scope_name=_scope_name(session, scope),
        )
        summary = analysis.summary
        run = TriageRun(
            institution_id=scope.institution_id,
            evaluated_on=evaluated_on,
            rule_version=RULE_VERSION,
            run_name=run_name or f"Maintenance triage {evaluated_on.isoformat()}",
            status="completed",
            engine_version=ENGINE_VERSION,
            total_institutions=summary.total_institutions,
            total_assets=summary.total_assets,
            high_risk_assets=summary.high_risk_assets,
            critical_assets=summary.critical_assets,
            maintenance_candidates=summary.maintenance_candidates,
            replacement_candidates=summary.replacement_candidates,
        )
        session.add(run)
        session.flush()
        assets_by_id = {asset.id: asset for asset in assets}
        for item in analysis.assets:
            asset = assets_by_id.get(item.asset_id)
            snapshot = (
                AssetRead.model_validate(asset).model_dump(mode="json")
                if asset is not None
                else {}
            )
            session.add(
                Recommendation(
                    run_id=run.id,
                    asset_id=item.asset_id,
                    institution_id=item.institution_id,
                    asset_code=item.asset_code,
                    risk_level=item.risk_level,
                    risk_score=item.risk_score,
                    factor_scores=item.factor_scores,
                    maintenance_priority=item.maintenance_priority,
                    priority_score=item.priority_score,
                    replacement_score=item.replacement_score,
                    replacement_candidate=item.replacement_candidate,
                    maintenance_count=item.maintenance_count,
                    maintenance_frequency=item.maintenance_frequency,
                    asset_age_years=item.asset_age_years,
                    days_since_last_maintenance=item.days_since_last_maintenance,
                    recent_window_count=item.recent_window_count,
                    recent_repeat_count=item.recent_repeat_count,
                    unplanned_share=item.unplanned_share,
                    total_downtime_hours=item.total_downtime_hours,
                    has_maintenance_history=item.has_maintenance_history,
                    reasons=item.reasons,
                    evidence=item.evidence,
                    recommended_action=item.recommendation,
                    rule_version=ENGINE_VERSION,
                    evaluated_on=evaluated_on,
                    asset_snapshot=snapshot,
                )
            )
        session.commit()
        session.refresh(run)
        return _run_read(session, run)

    @router.get("/triage-runs", response_model=list[TriageRunRead])
    def list_triage_runs(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        runs = session.scalars(
            scoped_runs(select(TriageRun), scope)
            .order_by(TriageRun.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [_run_read(session, run) for run in runs]

    @router.get("/triage-runs/{run_id}", response_model=TriageRunRead)
    def get_triage_run(
        run_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        run = session.scalar(scoped_runs(select(TriageRun).where(TriageRun.id == run_id), scope))
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Triage run not found.",
            )
        return _run_read(session, run)

    @router.get("/triage-runs/{run_id}/analysis", response_model=TriageAnalysisRead)
    def get_triage_run_analysis(
        run_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        """Reproduce the saved snapshot: summary, institution priorities, and assets."""
        run = session.scalar(scoped_runs(select(TriageRun).where(TriageRun.id == run_id), scope))
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Triage run not found.",
            )
        analysis = _reconstruct_run_analysis(session, run)
        return _analysis_read(analysis, run.engine_version or ENGINE_VERSION, run.id)

    @router.get(
        "/triage-runs/{run_id}/institutions",
        response_model=list[InstitutionAssessmentRead],
    )
    def get_triage_run_institutions(
        run_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        run = session.scalar(scoped_runs(select(TriageRun).where(TriageRun.id == run_id), scope))
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Triage run not found.",
            )
        analysis = _reconstruct_run_analysis(session, run)
        return [
            InstitutionAssessmentRead.model_validate(item, from_attributes=True)
            for item in analysis.institutions
        ]

    @router.get("/triage-runs/{run_id}/assets", response_model=list[AssetAssessmentRead])
    def get_triage_run_assets(
        run_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        run = session.scalar(scoped_runs(select(TriageRun).where(TriageRun.id == run_id), scope))
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Triage run not found.",
            )
        analysis = _reconstruct_run_analysis(session, run)
        return [
            AssetAssessmentRead.model_validate(item, from_attributes=True)
            for item in _sorted_assessments(analysis.assets)
        ]

    @router.get("/recommendations", response_model=list[RecommendationRead])
    def list_recommendations(
        run_id: int | None = None,
        risk_level: RiskLevel | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        query = select(Recommendation).join(Asset, Recommendation.asset_id == Asset.id)
        query = scoped_assets(query, scope).order_by(Recommendation.id.desc())
        if run_id is not None:
            query = query.where(Recommendation.run_id == run_id)
        if risk_level is not None:
            query = query.where(Recommendation.risk_level == risk_level.value)
        return session.scalars(query.offset(offset).limit(limit)).all()

    @router.get("/recommendations/{recommendation_id}", response_model=RecommendationRead)
    def get_recommendation(
        recommendation_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        recommendation = find_recommendation(session, recommendation_id, scope)
        if recommendation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found.",
            )
        return recommendation

    @router.post(
        "/recommendations/{recommendation_id}/events",
        response_model=RecommendationEventRead,
        status_code=status.HTTP_201_CREATED,
    )
    def add_recommendation_event(
        recommendation_id: int,
        payload: RecommendationEventCreate,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        permission = (
            "recommendation:review"
            if payload.event_type.value == "review"
            else "recommendation:outcome"
        )
        ensure_permission(scope, permission)
        if find_recommendation(session, recommendation_id, scope) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found.",
            )
        event = RecommendationEvent(
            recommendation_id=recommendation_id,
            **payload.model_dump(mode="python"),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event

    @router.get(
        "/recommendations/{recommendation_id}/events",
        response_model=list[RecommendationEventRead],
    )
    def list_recommendation_events(
        recommendation_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        if find_recommendation(session, recommendation_id, scope) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found.",
            )
        query = (
            select(RecommendationEvent)
            .where(RecommendationEvent.recommendation_id == recommendation_id)
            .order_by(RecommendationEvent.id)
        )
        return session.scalars(query).all()

    @router.get("/triage-runs/{run_id}/insights")
    def get_triage_run_insights(
        run_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        """Get detailed insights for a triage run including institutional analysis."""
        run = session.scalar(scoped_runs(select(TriageRun).where(TriageRun.id == run_id), scope))
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Triage run not found.",
            )

        # Get all recommendations for this run
        recommendations = session.scalars(
            select(Recommendation)
            .where(Recommendation.run_id == run_id)
        ).all()

        # Group by risk level and condition
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "insufficient_data": 0}
        condition_counts = {"critical": 0, "poor": 0, "fair": 0, "good": 0, "unknown": 0}
        assets_by_condition = {"critical": [], "poor": [], "fair": [], "good": [], "unknown": []}
        
        for rec in recommendations:
            risk_counts[rec.risk_level] = risk_counts.get(rec.risk_level, 0) + 1
            
            # Extract condition from asset_snapshot
            asset_snapshot = rec.asset_snapshot
            if isinstance(asset_snapshot, str):
                import json
                try:
                    asset = json.loads(asset_snapshot)
                except json.JSONDecodeError:
                    asset = {}
            else:
                asset = asset_snapshot or {}
            
            condition = asset.get("condition", "unknown")
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
            
            asset_code = asset.get("asset_code", "Unknown")
            if asset_code and asset_code != "Unknown":
                assets_by_condition[condition].append(asset_code)

        return {
            "run_id": run_id,
            "evaluated_on": str(run.evaluated_on),
            "total_recommendations": len(recommendations),
            "summary": {
                "risk_distribution": risk_counts,
                "condition_distribution": condition_counts,
            },
            "assets_by_condition": assets_by_condition,
        }

    return router
