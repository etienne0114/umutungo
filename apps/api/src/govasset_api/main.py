import os
from contextlib import asynccontextmanager
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from govasset_api.auth import require_admin_user, require_authenticated_user
from govasset_api.auth import authentication_required, supabase_url
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
    AdminAccessUpdate,
    AdminUserRead,
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
from govasset_api.supabase_admin import (
    SupabaseAdminError,
    get_supabase_user,
    list_supabase_users,
    update_supabase_user_app_metadata,
)


def create_app(engine: Engine | None = None) -> FastAPI:
    database_engine = engine or make_engine()
    session_factory = make_session_factory(database_engine)
    get_session = session_dependency(session_factory)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if authentication_required() and engine is None:
            if supabase_url() is None:
                raise RuntimeError("SUPABASE_URL is required when AUTH_REQUIRED is enabled.")
            if database_engine.dialect.name != "postgresql":
                raise RuntimeError("Hosted mode requires a persistent PostgreSQL DATABASE_URL.")
        else:
            initialize_schema(database_engine)
        yield

    app = FastAPI(
        title="Umutungo API",
        version="0.1.0",
        description=(
            "Local pilot API for asset history and transparent maintenance triage. "
            "Triage rules are advisory and are not AI predictions."
        ),
        lifespan=lifespan,
    )
    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    api = APIRouter(prefix="/api/v1", dependencies=[Depends(require_authenticated_user)])

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    @api.get(
        "/admin/users",
        response_model=list[AdminUserRead],
        tags=["administration"],
        dependencies=[Depends(require_admin_user)],
    )
    def list_users():
        try:
            users = list_supabase_users()
        except SupabaseAdminError as exc:
            detail = str(exc)
            code = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if "not configured" in detail
                else status.HTTP_502_BAD_GATEWAY
            )
            raise HTTPException(status_code=code, detail=detail) from exc

        summaries = []
        for user in users:
            metadata = user.get("app_metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            user_metadata = user.get("user_metadata")
            user_metadata = user_metadata if isinstance(user_metadata, dict) else {}
            summaries.append(
                AdminUserRead(
                    id=str(user.get("id", "")),
                    email=user.get("email"),
                    created_at=user["created_at"],
                    email_confirmed_at=user.get("email_confirmed_at"),
                    last_sign_in_at=user.get("last_sign_in_at"),
                    access=(
                        "approved"
                        if metadata.get("govasset_access") == "approved"
                        else "pending"
                    ),
                    role=(
                        "admin"
                        if metadata.get("govasset_role") == "admin"
                        else "user"
                    ),
                    full_name=(
                        user_metadata.get("full_name")
                        if isinstance(user_metadata.get("full_name"), str)
                        else None
                    ),
                    organization=(
                        user_metadata.get("organization")
                        if isinstance(user_metadata.get("organization"), str)
                        else None
                    ),
                )
            )
        return summaries

    @api.put(
        "/admin/users/{user_id}/access",
        response_model=AdminUserRead,
        tags=["administration"],
        dependencies=[Depends(require_admin_user)],
    )
    def update_user_access(
        user_id: UUID,
        payload: AdminAccessUpdate,
        admin_claims: dict = Depends(require_admin_user),
    ):
        user_id_str = str(user_id)
        if user_id_str == admin_claims.get("sub") and not payload.approved:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Administrators cannot revoke their own access.",
            )
        try:
            target_user = get_supabase_user(user_id_str)
            if payload.approved and not target_user.get("email_confirmed_at"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Users must confirm their email before approval.",
                )
            metadata = target_user.get("app_metadata")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            metadata["govasset_access"] = "approved" if payload.approved else "pending"
            updated_user = update_supabase_user_app_metadata(user_id_str, metadata)
        except SupabaseAdminError as exc:
            detail = str(exc)
            code = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if "not configured" in detail
                else status.HTTP_502_BAD_GATEWAY
            )
            raise HTTPException(status_code=code, detail=detail) from exc

        updated_metadata = updated_user.get("app_metadata")
        updated_metadata = updated_metadata if isinstance(updated_metadata, dict) else {}
        user_metadata = updated_user.get("user_metadata")
        user_metadata = user_metadata if isinstance(user_metadata, dict) else {}
        return AdminUserRead(
            id=str(updated_user.get("id", user_id_str)),
            email=updated_user.get("email"),
            created_at=updated_user["created_at"],
            email_confirmed_at=updated_user.get("email_confirmed_at"),
            last_sign_in_at=updated_user.get("last_sign_in_at"),
            access=(
                "approved"
                if updated_metadata.get("govasset_access") == "approved"
                else "pending"
            ),
            role=(
                "admin" if updated_metadata.get("govasset_role") == "admin" else "user"
            ),
            full_name=(
                user_metadata.get("full_name")
                if isinstance(user_metadata.get("full_name"), str)
                else None
            ),
            organization=(
                user_metadata.get("organization")
                if isinstance(user_metadata.get("organization"), str)
                else None
            ),
        )

    @api.post(
        "/assets",
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

    @api.get("/assets", response_model=list[AssetRead], tags=["assets"])
    def list_assets(
        active: bool | None = None,
        session: Session = Depends(get_session),
    ):
        query = select(Asset).order_by(Asset.asset_code)
        if active is not None:
            query = query.where(Asset.active.is_(active))
        return session.scalars(query).all()

    @api.get("/assets/{asset_id}", response_model=AssetRead, tags=["assets"])
    def get_asset(asset_id: int, session: Session = Depends(get_session)):
        asset = session.get(Asset, asset_id)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return asset

    @api.post(
        "/assets/{asset_id}/maintenance",
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

    @api.get(
        "/assets/{asset_id}/maintenance",
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

    @api.post(
        "/assets/{asset_id}/inspections",
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

    @api.get(
        "/assets/{asset_id}/inspections",
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

    @api.get("/triage", response_model=list[TriageItem], tags=["triage"])
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

    @api.post(
        "/triage-runs",
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

    @api.get(
        "/triage-runs",
        response_model=list[TriageRunRead],
        tags=["triage"],
    )
    def list_triage_runs(
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        session: Session = Depends(get_session),
    ):
        rows = session.execute(
            select(TriageRun, func.count(Recommendation.id))
            .outerjoin(Recommendation, Recommendation.run_id == TriageRun.id)
            .group_by(TriageRun.id)
            .order_by(TriageRun.id.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [
            TriageRunRead(
                id=run.id,
                evaluated_on=run.evaluated_on,
                rule_version=run.rule_version,
                created_at=run.created_at,
                recommendation_count=count,
            )
            for run, count in rows
        ]

    @api.get("/triage-runs/{run_id}", response_model=TriageRunRead, tags=["triage"])
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

    @api.get("/recommendations", response_model=list[RecommendationRead], tags=["triage"])
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

    @api.get(
        "/recommendations/{recommendation_id}",
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

    @api.post(
        "/recommendations/{recommendation_id}/events",
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

    @api.get(
        "/recommendations/{recommendation_id}/events",
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

    app.include_router(api)
    return app


app = create_app()
