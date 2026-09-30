"""Explainable rule-based triage and recommendation history endpoints."""

from collections.abc import Callable
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
from govasset_api.models import Asset, Recommendation, RecommendationEvent, TriageRun
from govasset_api.schemas import (
    RecommendationEventCreate,
    RecommendationEventRead,
    RecommendationRead,
    RiskLevel,
    TriageItem,
    TriageRunRead,
)
from govasset_api.triage import RULE_VERSION, assess_asset

RISK_RANK = {
    RiskLevel.CRITICAL: 0,
    RiskLevel.HIGH: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.INSUFFICIENT_DATA: 3,
    RiskLevel.LOW: 4,
}


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

    @router.post(
        "/triage-runs",
        response_model=TriageRunRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_triage_run(
        as_of: date | None = Query(default=None, description="Evaluation date; defaults to today."),
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
        run = TriageRun(
            institution_id=scope.institution_id,
            evaluated_on=evaluated_on,
            rule_version=RULE_VERSION,
        )
        session.add(run)
        session.flush()
        for asset in assets:
            item = assess_asset(asset, evaluated_on)
            session.add(
                Recommendation(
                    run_id=run.id,
                    asset_id=asset.id,
                    risk_level=item.risk_level.value,
                    reasons=item.reasons,
                    recommended_action=item.recommended_action,
                    rule_version=item.rule_version,
                    evaluated_on=item.evaluated_on,
                    asset_snapshot=item.asset.model_dump(mode="json"),
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
        rows = session.execute(
            scoped_runs(select(TriageRun), scope)
            .add_columns(func.count(Recommendation.id))
            .outerjoin(Recommendation, Recommendation.run_id == TriageRun.id)
            .group_by(TriageRun.id)
            .order_by(TriageRun.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [
            TriageRunRead(
                id=run.id,
                institution_id=run.institution_id,
                evaluated_on=run.evaluated_on,
                rule_version=run.rule_version,
                created_at=run.created_at,
                recommendation_count=count,
            )
            for run, count in rows
        ]

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

    return router
