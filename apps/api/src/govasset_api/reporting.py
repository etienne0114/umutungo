import csv
import io
from datetime import date
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from govasset_api.models import Asset, InspectionRecord, MaintenanceRecord
from govasset_api.schemas import OperationsReport, RiskLevel
from govasset_api.triage import assess_asset

MAX_EXPORT_ROWS = 10_000


def build_operations_report(session: Session, as_of: date) -> OperationsReport:
    assets = session.scalars(select(Asset)).all()
    active_assets = [asset for asset in assets if asset.active]
    maintenance_totals = session.execute(
        select(
            func.count(MaintenanceRecord.id),
            func.sum(case((MaintenanceRecord.planned.is_(True), 1), else_=0)),
            func.sum(case((MaintenanceRecord.planned.is_(False), 1), else_=0)),
            func.sum(func.coalesce(MaintenanceRecord.downtime_hours, 0)),
            func.sum(case((MaintenanceRecord.downtime_hours.is_(None), 1), else_=0)),
            func.count(func.distinct(MaintenanceRecord.asset_id)),
        )
    ).one()
    inspection_count = session.scalar(select(func.count(InspectionRecord.id))) or 0

    risk_counts = {risk.value: 0 for risk in RiskLevel}
    for asset in active_assets:
        risk_counts[assess_asset(asset, as_of).risk_level.value] += 1

    due_assets = [
        asset
        for asset in active_assets
        if asset.next_service_due is not None and asset.next_service_due <= as_of
    ]
    return OperationsReport(
        generated_on=as_of,
        total_assets=len(assets),
        active_assets=len(active_assets),
        inactive_assets=len(assets) - len(active_assets),
        condition_recorded_assets=sum(asset.condition != "unknown" for asset in assets),
        condition_unknown_assets=sum(asset.condition == "unknown" for asset in assets),
        missing_acquisition_date=sum(asset.acquisition_date is None for asset in assets),
        missing_inspection_date=sum(asset.last_inspected_on is None for asset in assets),
        missing_service_schedule=sum(asset.next_service_due is None for asset in assets),
        inconsistent_service_dates=sum(
            asset.last_service_date is not None
            and asset.next_service_due is not None
            and asset.next_service_due < asset.last_service_date
            for asset in assets
        ),
        assets_with_maintenance_history=maintenance_totals[5] or 0,
        inspection_records=inspection_count,
        maintenance_records=maintenance_totals[0] or 0,
        service_due_assets=len(due_assets),
        overdue_service_assets=sum(asset.next_service_due < as_of for asset in due_assets),
        risk_counts=risk_counts,
        planned_maintenance_records=maintenance_totals[1] or 0,
        unplanned_maintenance_records=maintenance_totals[2] or 0,
        downtime_hours_recorded=round(float(maintenance_totals[3] or 0), 2),
        maintenance_records_without_downtime=maintenance_totals[4] or 0,
        untracked_domains=[
            "usage readings",
            "parts used",
            "maintenance costs",
            "work-order status",
            "source-system lineage and import freshness",
            "recommendation actor identity",
            "institution-level access boundaries",
        ],
    )


def _safe_csv_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def render_csv(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(tuple(_safe_csv_value(value) for value in row) for row in rows)
    return output.getvalue()


def bounded_export_rows(session: Session, statement) -> list[Any]:
    rows = session.execute(statement.limit(MAX_EXPORT_ROWS + 1)).all()
    if len(rows) > MAX_EXPORT_ROWS:
        raise ValueError(
            f"Export exceeds {MAX_EXPORT_ROWS} rows. Narrow the dataset before exporting."
        )
    return rows
