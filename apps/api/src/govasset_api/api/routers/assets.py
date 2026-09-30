"""Asset register, usage, maintenance history, and inspection endpoints."""

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from govasset_api.api.dependencies import find_asset
from govasset_api.authorization import TenantScope, ensure_permission, scoped_assets
from govasset_api.models import (
    Asset,
    AssetUsageReading,
    InspectionRecord,
    MaintenanceRecord,
)
from govasset_api.schemas import (
    AssetCreate,
    AssetRead,
    AssetUpdate,
    InspectionCreate,
    InspectionRead,
    MaintenanceCreate,
    MaintenanceRead,
    UsageReadingCreate,
    UsageReadingRead,
)


def _validate_odometer_sequence(
    session: Session,
    asset_id: int,
    recorded_on: date,
    odometer_km: float,
) -> AssetUsageReading | None:
    same_day = session.scalar(
        select(AssetUsageReading).where(
            AssetUsageReading.asset_id == asset_id,
            AssetUsageReading.recorded_on == recorded_on,
        )
    )
    if same_day is not None:
        if abs(same_day.odometer_km - odometer_km) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A different odometer reading is already recorded for this date.",
            )
        return same_day

    previous = session.scalar(
        select(AssetUsageReading)
        .where(
            AssetUsageReading.asset_id == asset_id,
            AssetUsageReading.recorded_on < recorded_on,
        )
        .order_by(AssetUsageReading.recorded_on.desc(), AssetUsageReading.id.desc())
        .limit(1)
    )
    following = session.scalar(
        select(AssetUsageReading)
        .where(
            AssetUsageReading.asset_id == asset_id,
            AssetUsageReading.recorded_on > recorded_on,
        )
        .order_by(AssetUsageReading.recorded_on, AssetUsageReading.id)
        .limit(1)
    )
    if previous is not None and odometer_km < previous.odometer_km:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Odometer cannot be below the earlier reading of "
                f"{previous.odometer_km:g} km on {previous.recorded_on.isoformat()}."
            ),
        )
    if following is not None and odometer_km > following.odometer_km:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Odometer cannot exceed the later reading of "
                f"{following.odometer_km:g} km on {following.recorded_on.isoformat()}."
            ),
        )
    return None


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
        if scope.institution_id is None and not scope.local_development:
            raise HTTPException(
                status_code=422,
                detail="Select an institution before registering an asset.",
            )
        if (
            payload.manufacture_year is not None
            and payload.acquisition_date is not None
            and payload.manufacture_year > payload.acquisition_date.year
        ):
            raise HTTPException(
                status_code=422,
                detail="manufacture_year cannot be later than the acquisition year.",
            )
        asset = Asset(**payload.model_dump(), institution_id=scope.institution_id)
        session.add(asset)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An asset with this code or registration number already exists "
                    "in the selected institution."
                ),
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
        for field in ("asset_code", "asset_type", "condition", "criticality", "active"):
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
        manufacture_year = changes.get("manufacture_year", asset.manufacture_year)
        acquisition_date = changes.get("acquisition_date", asset.acquisition_date)
        if (
            manufacture_year is not None
            and acquisition_date is not None
            and manufacture_year > acquisition_date.year
        ):
            raise HTTPException(
                status_code=422,
                detail="manufacture_year cannot be later than the acquisition year.",
            )
        for field, value in changes.items():
            setattr(asset, field, value.value if hasattr(value, "value") else value)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An asset with this code or registration number already exists "
                    "in the selected institution."
                ),
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
        asset = find_asset(session, asset_id, scope)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        if payload.event_date > date.today():
            raise HTTPException(status_code=422, detail="Maintenance date cannot be in the future.")
        if asset.acquisition_date is not None and payload.event_date < asset.acquisition_date:
            raise HTTPException(
                status_code=422,
                detail="Maintenance date cannot be earlier than the asset acquisition date.",
            )

        existing_reading = None
        if payload.odometer_km is not None:
            existing_reading = _validate_odometer_sequence(
                session,
                asset_id,
                payload.event_date,
                payload.odometer_km,
            )

        record = MaintenanceRecord(asset_id=asset_id, **payload.model_dump())
        session.add(record)
        if payload.odometer_km is not None and existing_reading is None:
            session.add(
                AssetUsageReading(
                    asset_id=asset_id,
                    recorded_on=payload.event_date,
                    odometer_km=payload.odometer_km,
                    source="maintenance",
                    notes="Captured with a maintenance record.",
                )
            )
        if asset.last_service_date is None or payload.event_date >= asset.last_service_date:
            asset.last_service_date = payload.event_date
            if asset.next_service_due is not None and asset.next_service_due <= payload.event_date:
                asset.next_service_due = None
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This maintenance or odometer record conflicts with existing history.",
            ) from exc
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
        "/assets/{asset_id}/usage-readings",
        response_model=UsageReadingRead,
        status_code=status.HTTP_201_CREATED,
        tags=["usage"],
    )
    def create_usage_reading(
        asset_id: int,
        payload: UsageReadingCreate,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        ensure_permission(scope, "maintenance:write")
        asset = find_asset(session, asset_id, scope)
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        if payload.recorded_on > date.today():
            raise HTTPException(status_code=422, detail="Usage reading date cannot be in the future.")
        if asset.acquisition_date is not None and payload.recorded_on < asset.acquisition_date:
            raise HTTPException(
                status_code=422,
                detail="Usage reading cannot be earlier than the asset acquisition date.",
            )
        if (
            _validate_odometer_sequence(
                session,
                asset_id,
                payload.recorded_on,
                payload.odometer_km,
            )
            is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An odometer reading is already recorded for this date.",
            )
        reading = AssetUsageReading(asset_id=asset_id, **payload.model_dump())
        session.add(reading)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An odometer reading is already recorded for this date.",
            ) from exc
        session.refresh(reading)
        return reading

    @router.get(
        "/assets/{asset_id}/usage-readings",
        response_model=list[UsageReadingRead],
        tags=["usage"],
    )
    def list_usage_readings(
        asset_id: int,
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        if find_asset(session, asset_id, scope) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
        query = (
            select(AssetUsageReading)
            .where(AssetUsageReading.asset_id == asset_id)
            .order_by(AssetUsageReading.recorded_on.desc(), AssetUsageReading.id.desc())
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
        if asset.acquisition_date is not None and payload.inspected_on < asset.acquisition_date:
            raise HTTPException(
                status_code=422,
                detail="Inspection date cannot be earlier than the asset acquisition date.",
            )
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
