"""add vehicle usage and maintenance analytics fields

Revision ID: c7a2d4e8f901
Revises: 9f4e2b7a6c31
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7a2d4e8f901"
down_revision: Union[str, Sequence[str], None] = "9f4e2b7a6c31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_asset_columns(schema: str | None, dialect: str) -> None:
    columns = (
        sa.Column("registration_number", sa.String(length=40), nullable=True),
        sa.Column("manufacture_year", sa.Integer(), nullable=True),
        sa.Column(
            "criticality",
            sa.String(length=20),
            server_default="standard",
            nullable=False,
        ),
    )
    if dialect == "sqlite":
        with op.batch_alter_table("assets") as batch:
            for column in columns:
                batch.add_column(column)
            batch.create_unique_constraint(
                "uq_assets_institution_registration_number",
                ["institution_id", "registration_number"],
            )
            batch.create_check_constraint(
                "ck_assets_manufacture_year",
                "manufacture_year IS NULL OR manufacture_year BETWEEN 1900 AND 2200",
            )
            batch.create_check_constraint(
                "ck_assets_criticality",
                "criticality IN ('standard', 'important', 'mission_critical')",
            )
        return

    for column in columns:
        op.add_column("assets", column, schema=schema)
    op.create_unique_constraint(
        "uq_assets_institution_registration_number",
        "assets",
        ["institution_id", "registration_number"],
        schema=schema,
    )
    op.create_check_constraint(
        "ck_assets_manufacture_year",
        "assets",
        "manufacture_year IS NULL OR manufacture_year BETWEEN 1900 AND 2200",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_assets_criticality",
        "assets",
        "criticality IN ('standard', 'important', 'mission_critical')",
        schema=schema,
    )


def _add_maintenance_columns(schema: str | None, dialect: str) -> None:
    columns = (
        sa.Column("odometer_km", sa.Float(), nullable=True),
        sa.Column("cost_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column(
            "currency",
            sa.String(length=3),
            server_default="RWF",
            nullable=False,
        ),
        sa.Column("provider_name", sa.String(length=200), nullable=True),
        sa.Column("work_order_reference", sa.String(length=100), nullable=True),
    )
    if dialect == "sqlite":
        with op.batch_alter_table("maintenance_records") as batch:
            for column in columns:
                batch.add_column(column)
            batch.create_check_constraint(
                "ck_maintenance_downtime_nonnegative",
                "downtime_hours IS NULL OR downtime_hours >= 0",
            )
            batch.create_check_constraint(
                "ck_maintenance_odometer_nonnegative",
                "odometer_km IS NULL OR odometer_km >= 0",
            )
            batch.create_check_constraint(
                "ck_maintenance_cost_nonnegative",
                "cost_amount IS NULL OR cost_amount >= 0",
            )
            batch.create_check_constraint(
                "ck_maintenance_currency",
                "currency = 'RWF'",
            )
        op.drop_index(
            "ix_maintenance_records_asset_id",
            table_name="maintenance_records",
        )
        op.create_index(
            "ix_maintenance_records_asset_event",
            "maintenance_records",
            ["asset_id", "event_date"],
        )
        return

    for column in columns:
        op.add_column("maintenance_records", column, schema=schema)
    op.create_check_constraint(
        "ck_maintenance_downtime_nonnegative",
        "maintenance_records",
        "downtime_hours IS NULL OR downtime_hours >= 0",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_maintenance_odometer_nonnegative",
        "maintenance_records",
        "odometer_km IS NULL OR odometer_km >= 0",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_maintenance_cost_nonnegative",
        "maintenance_records",
        "cost_amount IS NULL OR cost_amount >= 0",
        schema=schema,
    )
    op.create_check_constraint(
        "ck_maintenance_currency",
        "maintenance_records",
        "currency = 'RWF'",
        schema=schema,
    )
    op.drop_index(
        "ix_maintenance_records_asset_id",
        table_name="maintenance_records",
        schema=schema,
    )
    op.create_index(
        "ix_maintenance_records_asset_event",
        "maintenance_records",
        ["asset_id", "event_date"],
        schema=schema,
    )


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    schema = "govasset" if dialect == "postgresql" else None
    _add_asset_columns(schema, dialect)
    _add_maintenance_columns(schema, dialect)

    op.create_table(
        "asset_usage_readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        sa.Column("odometer_km", sa.Float(), nullable=False),
        sa.Column(
            "source",
            sa.String(length=40),
            server_default="manual",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "odometer_km >= 0",
            name="ck_usage_odometer_nonnegative",
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'maintenance', 'import')",
            name="ck_usage_source",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            [f"{schema + '.' if schema else ''}assets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id",
            "recorded_on",
            name="uq_usage_asset_recorded_on",
        ),
        schema=schema,
    )
    op.create_index(
        "ix_usage_asset_recorded",
        "asset_usage_readings",
        ["asset_id", "recorded_on"],
        schema=schema,
    )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    schema = "govasset" if dialect == "postgresql" else None
    op.drop_index(
        "ix_usage_asset_recorded",
        table_name="asset_usage_readings",
        schema=schema,
    )
    op.drop_table("asset_usage_readings", schema=schema)

    op.drop_index(
        "ix_maintenance_records_asset_event",
        table_name="maintenance_records",
        schema=schema,
    )
    op.create_index(
        "ix_maintenance_records_asset_id",
        "maintenance_records",
        ["asset_id"],
        schema=schema,
    )
    if dialect == "sqlite":
        with op.batch_alter_table("maintenance_records") as batch:
            batch.drop_constraint(
                "ck_maintenance_currency",
                type_="check",
            )
            batch.drop_constraint(
                "ck_maintenance_cost_nonnegative",
                type_="check",
            )
            batch.drop_constraint(
                "ck_maintenance_odometer_nonnegative",
                type_="check",
            )
            batch.drop_constraint(
                "ck_maintenance_downtime_nonnegative",
                type_="check",
            )
            for column in (
                "work_order_reference",
                "provider_name",
                "currency",
                "cost_amount",
                "odometer_km",
            ):
                batch.drop_column(column)
        with op.batch_alter_table("assets") as batch:
            batch.drop_constraint(
                "ck_assets_criticality",
                type_="check",
            )
            batch.drop_constraint(
                "ck_assets_manufacture_year",
                type_="check",
            )
            batch.drop_constraint(
                "uq_assets_institution_registration_number",
                type_="unique",
            )
            for column in ("criticality", "manufacture_year", "registration_number"):
                batch.drop_column(column)
        return

    for constraint in (
        "ck_maintenance_currency",
        "ck_maintenance_cost_nonnegative",
        "ck_maintenance_odometer_nonnegative",
        "ck_maintenance_downtime_nonnegative",
    ):
        op.drop_constraint(
            constraint,
            "maintenance_records",
            type_="check",
            schema=schema,
        )
    for column in (
        "work_order_reference",
        "provider_name",
        "currency",
        "cost_amount",
        "odometer_km",
    ):
        op.drop_column("maintenance_records", column, schema=schema)

    op.drop_constraint(
        "ck_assets_criticality",
        "assets",
        type_="check",
        schema=schema,
    )
    op.drop_constraint(
        "ck_assets_manufacture_year",
        "assets",
        type_="check",
        schema=schema,
    )
    op.drop_constraint(
        "uq_assets_institution_registration_number",
        "assets",
        type_="unique",
        schema=schema,
    )
    for column in ("criticality", "manufacture_year", "registration_number"):
        op.drop_column("assets", column, schema=schema)
