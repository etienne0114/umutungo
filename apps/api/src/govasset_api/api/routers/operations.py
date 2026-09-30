"""Operational reporting and bounded CSV export endpoints."""

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from govasset_api.authorization import TenantScope, scoped_assets
from govasset_api.models import Asset, InspectionRecord, Institution, MaintenanceRecord
from govasset_api.reporting import (
    bounded_export_rows,
    build_institution_tree_report,
    build_operations_report,
    render_csv,
)
from govasset_api.schemas import InstitutionTreeReport, OperationsReport
from govasset_api.services.institution_catalog import descendant_institution_ids


def _csv_response(filename: str, headers: list[str], rows: list[Any]) -> Response:
    return Response(
        render_csv(headers, [tuple(row) for row in rows]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _bounded_rows(session: Session, statement):
    try:
        return bounded_export_rows(session, statement)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc


def create_router(
    get_session: Callable[..., Any],
    current_scope: Callable[..., TenantScope],
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/reports/operations",
        response_model=OperationsReport,
        tags=["reports"],
    )
    def operations_report(
        as_of: date | None = Query(default=None, description="Report date; defaults to today."),
        include_descendants: bool = Query(
            default=False,
            description="Include the selected institution and its full reporting subtree.",
        ),
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        institution_ids: set[int] | None = None
        scope_name = "All government institutions"
        if scope.institution_id is not None:
            institution = session.get(Institution, scope.institution_id)
            if institution is None:
                raise HTTPException(status_code=404, detail="Institution not found.")
            institution_ids = {institution.id}
            scope_name = institution.name
            if include_descendants:
                if not (scope.global_admin or scope.local_development):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only system administrators can report across child institutions.",
                    )
                institution_ids = descendant_institution_ids(session, institution.id)

        return build_operations_report(
            session,
            as_of or date.today(),
            institution_ids=institution_ids,
            scope_institution_id=scope.institution_id,
            scope_name=scope_name,
        )

    @router.get(
        "/reports/institution-tree",
        response_model=InstitutionTreeReport,
        tags=["reports"],
    )
    def institution_tree_report(
        as_of: date | None = Query(default=None, description="Report date; defaults to today."),
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        if not (scope.global_admin or scope.local_development):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="National institution-tree reporting requires administrator access.",
            )
        roots = {scope.institution_id} if scope.institution_id is not None else None
        return build_institution_tree_report(session, as_of or date.today(), root_ids=roots)

    @router.get("/exports/assets.csv", tags=["exports"])
    def export_assets(
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        rows = _bounded_rows(
            session,
            scoped_assets(
                select(
                    Asset.asset_code,
                    Asset.asset_type,
                    Asset.make,
                    Asset.model,
                    Asset.acquisition_date,
                    Asset.condition,
                    Asset.active,
                    Asset.last_inspected_on,
                    Asset.last_service_date,
                    Asset.next_service_due,
                    Asset.created_at,
                ),
                scope,
            ).order_by(Asset.asset_code),
        )
        return _csv_response(
            "umutungo-assets.csv",
            [
                "asset_code",
                "asset_type",
                "make",
                "model",
                "acquisition_date",
                "condition",
                "active",
                "last_inspected_on",
                "last_service_date",
                "next_service_due",
                "created_at",
            ],
            rows,
        )

    @router.get("/exports/maintenance.csv", tags=["exports"])
    def export_maintenance(
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        statement = select(
            Asset.asset_code,
            MaintenanceRecord.event_date,
            MaintenanceRecord.category,
            MaintenanceRecord.description,
            MaintenanceRecord.planned,
            MaintenanceRecord.downtime_hours,
            MaintenanceRecord.created_at,
        ).join(Asset, MaintenanceRecord.asset_id == Asset.id)
        rows = _bounded_rows(
            session,
            scoped_assets(statement, scope).order_by(
                MaintenanceRecord.event_date,
                MaintenanceRecord.id,
            ),
        )
        return _csv_response(
            "umutungo-maintenance.csv",
            [
                "asset_code",
                "event_date",
                "category",
                "description",
                "planned",
                "downtime_hours",
                "created_at",
            ],
            rows,
        )

    @router.get("/exports/inspections.csv", tags=["exports"])
    def export_inspections(
        scope: TenantScope = Depends(current_scope),
        session: Session = Depends(get_session),
    ):
        statement = select(
            Asset.asset_code,
            InspectionRecord.inspected_on,
            InspectionRecord.condition,
            InspectionRecord.observations,
            InspectionRecord.created_at,
        ).join(Asset, InspectionRecord.asset_id == Asset.id)
        rows = _bounded_rows(
            session,
            scoped_assets(statement, scope).order_by(
                InspectionRecord.inspected_on,
                InspectionRecord.id,
            ),
        )
        return _csv_response(
            "umutungo-inspections.csv",
            ["asset_code", "inspected_on", "condition", "observations", "created_at"],
            rows,
        )

    return router
