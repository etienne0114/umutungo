import csv
import io
from collections import defaultdict, deque
from datetime import date
from typing import Any, Iterable, Sequence

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from govasset_api.models import Asset, InspectionRecord, Institution, MaintenanceRecord
from govasset_api.schemas import (
    InstitutionReportRow,
    InstitutionTreeReport,
    OperationsReport,
    RiskLevel,
)
from govasset_api.triage import assess_asset

MAX_EXPORT_ROWS = 10_000
MaintenanceTotals = Sequence[int | float | None]


def _scope_assets(statement, institution_ids: set[int] | None):
    if institution_ids is None:
        return statement
    return statement.where(Asset.institution_id.in_(institution_ids))


def _assemble_operations_report(
    as_of: date,
    *,
    assets: Sequence[Asset],
    maintenance_totals: MaintenanceTotals,
    inspection_count: int,
    scope_institution_id: int | None,
    scope_name: str,
    included_institutions: int,
) -> OperationsReport:
    active_assets = [asset for asset in assets if asset.active]
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
        scope_institution_id=scope_institution_id,
        scope_name=scope_name,
        included_institutions=included_institutions,
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
        assets_with_maintenance_history=int(maintenance_totals[5] or 0),
        inspection_records=inspection_count,
        maintenance_records=int(maintenance_totals[0] or 0),
        service_due_assets=len(due_assets),
        overdue_service_assets=sum(asset.next_service_due < as_of for asset in due_assets),
        risk_counts=risk_counts,
        planned_maintenance_records=int(maintenance_totals[1] or 0),
        unplanned_maintenance_records=int(maintenance_totals[2] or 0),
        downtime_hours_recorded=round(float(maintenance_totals[3] or 0), 2),
        maintenance_records_without_downtime=int(maintenance_totals[4] or 0),
        untracked_domains=[
            "parts used",
            "work-order status",
            "source-system lineage and import freshness",
            "recommendation actor identity",
            "driver assignments and trip history",
            "route, load, weather, and component fault telemetry",
        ],
    )


def _maintenance_statement():
    return select(
        func.count(MaintenanceRecord.id),
        func.sum(case((MaintenanceRecord.planned.is_(True), 1), else_=0)),
        func.sum(case((MaintenanceRecord.planned.is_(False), 1), else_=0)),
        func.sum(func.coalesce(MaintenanceRecord.downtime_hours, 0)),
        func.sum(case((MaintenanceRecord.downtime_hours.is_(None), 1), else_=0)),
        func.count(func.distinct(MaintenanceRecord.asset_id)),
    )


def build_operations_report(
    session: Session,
    as_of: date,
    *,
    institution_ids: set[int] | None = None,
    scope_institution_id: int | None = None,
    scope_name: str = "All government institutions",
) -> OperationsReport:
    """Build a descriptive report for one institution tree or the national view."""

    assets = session.scalars(_scope_assets(select(Asset), institution_ids)).all()
    maintenance_query = _maintenance_statement()
    inspection_query = select(func.count(InspectionRecord.id))
    if institution_ids is not None:
        maintenance_query = _scope_assets(
            maintenance_query.join(Asset, MaintenanceRecord.asset_id == Asset.id),
            institution_ids,
        )
        inspection_query = _scope_assets(
            inspection_query.join(Asset, InspectionRecord.asset_id == Asset.id),
            institution_ids,
        )
    maintenance_totals = session.execute(maintenance_query).one()
    inspection_count = session.scalar(inspection_query) or 0
    included_institutions = (
        len(institution_ids)
        if institution_ids is not None
        else session.scalar(select(func.count(Institution.id))) or 0
    )
    return _assemble_operations_report(
        as_of,
        assets=assets,
        maintenance_totals=maintenance_totals,
        inspection_count=inspection_count,
        scope_institution_id=scope_institution_id,
        scope_name=scope_name,
        included_institutions=included_institutions,
    )


def _descendants_by_root(institutions: Iterable[Institution]) -> dict[int, set[int]]:
    institution_list = list(institutions)
    children: dict[int, list[int]] = defaultdict(list)
    for institution in institution_list:
        if institution.parent_institution_id is not None:
            children[institution.parent_institution_id].append(institution.id)
    result: dict[int, set[int]] = {}
    for root in institution_list:
        descendants: set[int] = set()
        queue: deque[int] = deque([root.id])
        while queue:
            institution_id = queue.popleft()
            if institution_id in descendants:
                continue
            descendants.add(institution_id)
            queue.extend(children.get(institution_id, ()))
        result[root.id] = descendants
    return result


def _sum_totals(
    institution_ids: set[int],
    totals_by_institution: dict[int, tuple[int | float, ...]],
) -> tuple[int | float, ...]:
    return tuple(
        sum(
            float(totals_by_institution.get(institution_id, (0,) * 6)[index] or 0)
            for institution_id in institution_ids
        )
        for index in range(6)
    )


def build_institution_tree_report(
    session: Session,
    as_of: date,
    *,
    root_ids: set[int] | None = None,
) -> InstitutionTreeReport:
    """Aggregate every reporting root with four bulk database queries."""

    institutions = session.scalars(select(Institution)).all()
    descendants = _descendants_by_root(institutions)
    roots = [
        institution
        for institution in institutions
        if institution.active
        and (
            (root_ids is None and institution.parent_institution_id is None)
            or (root_ids is not None and institution.id in root_ids)
        )
    ]
    type_order = {"ministry": 0, "city": 1, "province": 2}
    roots.sort(key=lambda item: (type_order.get(item.institution_type, 3), item.name))

    assets = session.scalars(select(Asset)).all()
    assets_by_institution: dict[int, list[Asset]] = defaultdict(list)
    unassigned_assets = 0
    for asset in assets:
        if asset.institution_id is None:
            unassigned_assets += 1
        else:
            assets_by_institution[asset.institution_id].append(asset)

    maintenance_rows = session.execute(
        select(Asset.institution_id, *_maintenance_statement().selected_columns)
        .join(MaintenanceRecord, MaintenanceRecord.asset_id == Asset.id)
        .where(Asset.institution_id.is_not(None))
        .group_by(Asset.institution_id)
    ).all()
    maintenance_by_institution = {
        int(row[0]): tuple(row[1:]) for row in maintenance_rows if row[0] is not None
    }
    inspection_by_institution = {
        int(institution_id): int(count)
        for institution_id, count in session.execute(
            select(Asset.institution_id, func.count(InspectionRecord.id))
            .join(InspectionRecord, InspectionRecord.asset_id == Asset.id)
            .where(Asset.institution_id.is_not(None))
            .group_by(Asset.institution_id)
        ).all()
        if institution_id is not None
    }

    rows: list[InstitutionReportRow] = []
    for root in roots:
        institution_ids = descendants.get(root.id, {root.id})
        root_assets = [
            asset
            for institution_id in institution_ids
            for asset in assets_by_institution.get(institution_id, ())
        ]
        rows.append(
            InstitutionReportRow(
                institution=root,
                descendant_count=max(len(institution_ids) - 1, 0),
                report=_assemble_operations_report(
                    as_of,
                    assets=root_assets,
                    maintenance_totals=_sum_totals(
                        institution_ids, maintenance_by_institution
                    ),
                    inspection_count=sum(
                        inspection_by_institution.get(institution_id, 0)
                        for institution_id in institution_ids
                    ),
                    scope_institution_id=root.id,
                    scope_name=root.name,
                    included_institutions=len(institution_ids),
                ),
            )
        )

    return InstitutionTreeReport(
        generated_on=as_of,
        root_count=len(rows),
        unassigned_assets=unassigned_assets,
        rows=rows,
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
