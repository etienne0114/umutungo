"""Asset register, maintenance history, and inspection endpoints."""

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from govasset_api.api.dependencies import find_asset
from govasset_api.authorization import TenantScope, ensure_permission, scoped_assets
from govasset_api.models import Asset, InspectionRecord, MaintenanceRecord
from govasset_api.schemas import (
    AssetCreate,
    AssetRead,
    AssetUpdate,
    InspectionCreate,
    InspectionRead,
    MaintenanceCreate,
    MaintenanceRead,
)


def create_router(
    get_session: Callable[..., Any],
    current_scope: Callable[..., TenantScope],
) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/assets",
        response_model=AssetRead,
        status_code=status.HTTP_201_CREATED,
        tags=["assets"],
    )
    def create_asset(
        payload: AssetCreate,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        ensure_permission(scope, "asset:write")
        asset = Asset(**payload.model_dump(), institution_id=scope.institution_id)
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

    @router.get("/assets", response_model=list[AssetRead], tags=["assets"])
    def list_assets(
        active: bool | None = None,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        query = scoped_assets(select(Asset), scope).order_by(Asset.asset_code)
        if active is not None:
            query = query.where(Asset.active.is_(active))
        return session.scalars(query).all()

    @router.get("/assets/{asset_id}", response_model=AssetRead, tags=["assets"])
    def get_asset(
        asset_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        asset = find_asset(session, asset_id, scope)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        return asset

    @router.patch("/assets/{asset_id}", response_model=AssetRead, tags=["assets"])
    def update_asset(
        asset_id: int,
        payload: AssetUpdate,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        ensure_permission(scope, "asset:write")
        asset = find_asset(session, asset_id, scope)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

        changes = payload.model_dump(exclude_unset=True)
        for field in ("asset_code", "asset_type", "condition", "active"):
            if field in changes and changes[field] is None:
                raise HTTPException(status_code=422, detail=f"{field} cannot be null.")
        last_service_date = changes.get("last_service_date", asset.last_service_date)
        next_service_due = changes.get("next_service_due", asset.next_service_due)
        if (
            last_service_date is not None
            and next_service_due is not None
            and next_service_due < last_service_date
        ):
            raise HTTPException(
                status_code=422,
                detail="next_service_due cannot be earlier than last_service_date.",
            )
        for field, value in changes.items():
            setattr(asset, field, value.value if hasattr(value, "value") else value)
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

    @router.post(
        "/assets/{asset_id}/maintenance",
        response_model=MaintenanceRead,
        status_code=status.HTTP_201_CREATED,
        tags=["maintenance"],
    )
    def create_maintenance(
        asset_id: int,
        payload: MaintenanceCreate,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        ensure_permission(scope, "maintenance:write")
        if find_asset(session, asset_id, scope) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        record = MaintenanceRecord(asset_id=asset_id, **payload.model_dump())
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    @router.get(
        "/assets/{asset_id}/maintenance",
        response_model=list[MaintenanceRead],
        tags=["maintenance"],
    )
    def list_maintenance(
        asset_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        if find_asset(session, asset_id, scope) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        query = (
            select(MaintenanceRecord)
            .where(MaintenanceRecord.asset_id == asset_id)
            .order_by(MaintenanceRecord.event_date.desc(), MaintenanceRecord.id.desc())
        )
        return session.scalars(query).all()

    @router.post(
        "/assets/{asset_id}/inspections",
        response_model=InspectionRead,
        status_code=status.HTTP_201_CREATED,
        tags=["inspections"],
    )
    def create_inspection(
        asset_id: int,
        payload: InspectionCreate,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        ensure_permission(scope, "inspection:write")
        asset = find_asset(session, asset_id, scope)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        if payload.inspected_on > date.today():
            raise HTTPException(status_code=422, detail="Inspection date cannot be in the future.")
        inspection = InspectionRecord(asset_id=asset_id, **payload.model_dump())
        session.add(inspection)
        if asset.last_inspected_on is None or payload.inspected_on >= asset.last_inspected_on:
            asset.condition = payload.condition.value
            asset.last_inspected_on = payload.inspected_on
        session.commit()
        session.refresh(inspection)
        return inspection

    @router.get(
        "/assets/{asset_id}/inspections",
        response_model=list[InspectionRead],
        tags=["inspections"],
    )
    def list_inspections(
        asset_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        if find_asset(session, asset_id, scope) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        query = (
            select(InspectionRecord)
            .where(InspectionRecord.asset_id == asset_id)
            .order_by(InspectionRecord.inspected_on.desc(), InspectionRecord.id.desc())
        )
        return session.scalars(query).all()

    return router
