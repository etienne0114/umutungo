from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from govasset_api.database import (
    initialize_schema,
    make_engine,
    make_session_factory,
    session_dependency,
)
from govasset_api.models import (
    Asset,
    InspectionRecord,
    MaintenanceRecord,
    Recommendation,
    RecommendationEvent,
    TriageRun,
)
from govasset_api.schemas import (
    AssetCreate,
    AssetRead,
    InspectionCreate,
    InspectionRead,
    MaintenanceCreate,
    MaintenanceRead,
    RecommendationEventCreate,
    RecommendationEventRead,
    RecommendationRead,
    RiskLevel,
    TriageItem,
    TriageRunRead,
)
from govasset_api.triage import RULE_VERSION, assess_asset


def create_app(engine: Engine | None = None) -> FastAPI:
    database_engine = engine or make_engine()
    session_factory = make_session_factory(database_engine)
    get_session = session_dependency(session_factory)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        initialize_schema(database_engine)
        yield

    app = FastAPI(
        title="GovAsset Insight API",
        version="0.1.0",
        description=(
            "Local pilot API for asset history and transparent maintenance triage. "
            "Triage rules are advisory and are not AI predictions."
        ),
        lifespan=lifespan,
    )

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    @app.post(
        "/api/v1/assets",
        response_model=AssetRead,
        status_code=status.HTTP_201_CREATED,
        tags=["assets"],
    )
    def create_asset(payload: AssetCreate, session: Session = Depends(get_session)):
        asset = Asset(**payload.model_dump())
        session.add(asset)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An asset with this asset_code already exists.",
            ) from exc
        session.refresh(asset)
        return asset

    @app.get("/api/v1/assets", response_model=list[AssetRead], tags=["assets"])
    def list_assets(
        active: bool | None = None,
        session: Session = Depends(get_session),
    ):
        query = select(Asset).order_by(Asset.asset_code)
        if active is not None:
            query = query.where(Asset.active.is_(active))
        return session.scalars(query).all()

    @app.get("/api/v1/assets/{asset_id}", response_model=AssetRead, tags=["assets"])
    def get_asset(asset_id: int, session: Session = Depends(get_session)):
        asset = session.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return asset

    @app.post(
        "/api/v1/assets/{asset_id}/maintenance",
        response_model=MaintenanceRead,
        status_code=status.HTTP_201_CREATED,
        tags=["maintenance"],
    )
    def create_maintenance(
        asset_id: int,
        payload: MaintenanceCreate,
        session: Session = Depends(get_session),
    ):
        if session.get(Asset, asset_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        record = MaintenanceRecord(asset_id=asset_id, **payload.model_dump())
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    @app.get(
        "/api/v1/assets/{asset_id}/maintenance",
        response_model=list[MaintenanceRead],
        tags=["maintenance"],
    )
    def list_maintenance(asset_id: int, session: Session = Depends(get_session)):
        if session.get(Asset, asset_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        query = (
            select(MaintenanceRecord)
            .where(MaintenanceRecord.asset_id == asset_id)
            .order_by(MaintenanceRecord.event_date.desc(), MaintenanceRecord.id.desc())
        )
        return session.scalars(query).all()

    @app.post(
        "/api/v1/assets/{asset_id}/inspections",
        response_model=InspectionRead,
        status_code=status.HTTP_201_CREATED,
        tags=["inspections"],
    )
    def create_inspection(
        asset_id: int,
        payload: InspectionCreate,
        session: Session = Depends(get_session),
    ):
        asset = session.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        if payload.inspected_on > date.today():
            raise HTTPException(
                status_code=422,
                detail="Inspection date cannot be in the future.",
            )
        inspection = InspectionRecord(asset_id=asset_id, **payload.model_dump())
        session.add(inspection)
        if asset.last_inspected_on is None or payload.inspected_on >= asset.last_inspected_on:
            asset.condition = payload.condition.value
            asset.last_inspected_on = payload.inspected_on
        session.commit()
        session.refresh(inspection)
        return inspection

    @app.get(
        "/api/v1/assets/{asset_id}/inspections",
        response_model=list[InspectionRead],
        tags=["inspections"],
    )
    def list_inspections(asset_id: int, session: Session = Depends(get_session)):
        if session.get(Asset, asset_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        query = (
            select(InspectionRecord)
            .where(InspectionRecord.asset_id == asset_id)
            .order_by(InspectionRecord.inspected_on.desc(), InspectionRecord.id.desc())
        )
        return session.scalars(query).all()

    @app.get("/api/v1/triage", response_model=list[TriageItem], tags=["triage"])
    def triage_queue(
        as_of: date | None = Query(default=None, description="Evaluation date; defaults to today."),
        risk_level: RiskLevel | None = None,
        session: Session = Depends(get_session),
    ):
        evaluated_on = as_of or date.today()
        assets = session.scalars(
            select(Asset).where(Asset.active.is_(True)).order_by(Asset.asset_code)
        ).all()
        items = [assess_asset(asset, evaluated_on) for asset in assets]
        if risk_level is not None:
            items = [item for item in items if item.risk_level == risk_level]
        rank = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.INSUFFICIENT_DATA: 3,
            RiskLevel.LOW: 4,
        }
        return sorted(items, key=lambda item: (rank[item.risk_level], item.asset.asset_code))

    @app.post(
        "/api/v1/triage-runs",
        response_model=TriageRunRead,
        status_code=status.HTTP_201_CREATED,
        tags=["triage"],
    )
    def create_triage_run(
        as_of: date | None = Query(default=None, description="Evaluation date; defaults to today."),
        session: Session = Depends(get_session),
    ):
        evaluated_on = as_of or date.today()
        assets = session.scalars(
            select(Asset).where(Asset.active.is_(True)).order_by(Asset.asset_code)
        ).all()
        run = TriageRun(evaluated_on=evaluated_on, rule_version=RULE_VERSION)
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
        count = session.scalar(
            select(func.count(Recommendation.id)).where(Recommendation.run_id == run.id)
        )
        return TriageRunRead(
            id=run.id,
            evaluated_on=run.evaluated_on,
            rule_version=run.rule_version,
            created_at=run.created_at,
            recommendation_count=count or 0,
        )

    @app.get("/api/v1/triage-runs/{run_id}", response_model=TriageRunRead, tags=["triage"])
    def get_triage_run(run_id: int, session: Session = Depends(get_session)):
        run = session.get(TriageRun, run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Triage run not found.")
        count = session.scalar(
            select(func.count(Recommendation.id)).where(Recommendation.run_id == run.id)
        )
        return TriageRunRead(
            id=run.id,
            evaluated_on=run.evaluated_on,
            rule_version=run.rule_version,
            created_at=run.created_at,
            recommendation_count=count or 0,
        )

    @app.get("/api/v1/recommendations", response_model=list[RecommendationRead], tags=["triage"])
    def list_recommendations(
        run_id: int | None = None,
        risk_level: RiskLevel | None = None,
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
        session: Session = Depends(get_session),
    ):
        query = select(Recommendation).order_by(Recommendation.id.desc())
        if run_id is not None:
            query = query.where(Recommendation.run_id == run_id)
        if risk_level is not None:
            query = query.where(Recommendation.risk_level == risk_level.value)
        return session.scalars(query.offset(offset).limit(limit)).all()

    @app.get(
        "/api/v1/recommendations/{recommendation_id}",
        response_model=RecommendationRead,
        tags=["triage"],
    )
    def get_recommendation(recommendation_id: int, session: Session = Depends(get_session)):
        recommendation = session.get(Recommendation, recommendation_id)
        if recommendation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found."
            )
        return recommendation

    @app.post(
        "/api/v1/recommendations/{recommendation_id}/events",
        response_model=RecommendationEventRead,
        status_code=status.HTTP_201_CREATED,
        tags=["triage"],
    )
    def add_recommendation_event(
        recommendation_id: int,
        payload: RecommendationEventCreate,
        session: Session = Depends(get_session),
    ):
        if session.get(Recommendation, recommendation_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found."
            )
        event = RecommendationEvent(
            recommendation_id=recommendation_id,
            **payload.model_dump(mode="python"),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event

    @app.get(
        "/api/v1/recommendations/{recommendation_id}/events",
        response_model=list[RecommendationEventRead],
        tags=["triage"],
    )
    def list_recommendation_events(
        recommendation_id: int,
        session: Session = Depends(get_session),
    ):
        if session.get(Recommendation, recommendation_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found."
            )
        query = (
            select(RecommendationEvent)
            .where(RecommendationEvent.recommendation_id == recommendation_id)
            .order_by(RecommendationEvent.id)
        )
        return session.scalars(query).all()

    return app


app = create_app()
