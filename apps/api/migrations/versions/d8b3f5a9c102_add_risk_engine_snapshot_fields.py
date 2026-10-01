"""add risk engine snapshot fields to triage runs and recommendations

Revision ID: d8b3f5a9c102
Revises: c7a2d4e8f901
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d8b3f5a9c102"
down_revision: Union[str, Sequence[str], None] = "c7a2d4e8f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TRIAGE_RUN_COLUMNS = (
    sa.Column("run_name", sa.String(length=200), nullable=True),
    sa.Column("status", sa.String(length=20), server_default="completed", nullable=False),
    sa.Column("engine_version", sa.String(length=80), nullable=True),
    sa.Column("total_institutions", sa.Integer(), server_default="0", nullable=False),
    sa.Column("total_assets", sa.Integer(), server_default="0", nullable=False),
    sa.Column("high_risk_assets", sa.Integer(), server_default="0", nullable=False),
    sa.Column("critical_assets", sa.Integer(), server_default="0", nullable=False),
    sa.Column("maintenance_candidates", sa.Integer(), server_default="0", nullable=False),
    sa.Column("replacement_candidates", sa.Integer(), server_default="0", nullable=False),
)

RECOMMENDATION_COLUMNS = (
    sa.Column("institution_id", sa.Integer(), nullable=True),
    sa.Column("asset_code", sa.String(length=80), nullable=True),
    sa.Column("risk_score", sa.Integer(), nullable=True),
    sa.Column("factor_scores", sa.JSON(), nullable=True),
    sa.Column("maintenance_priority", sa.String(length=20), nullable=True),
    sa.Column("priority_score", sa.Integer(), nullable=True),
    sa.Column("replacement_score", sa.Integer(), nullable=True),
    sa.Column(
        "replacement_candidate", sa.Boolean(), server_default=sa.false(), nullable=False
    ),
    sa.Column("maintenance_count", sa.Integer(), server_default="0", nullable=False),
    sa.Column("maintenance_frequency", sa.Float(), nullable=True),
    sa.Column("asset_age_years", sa.Float(), nullable=True),
    sa.Column("days_since_last_maintenance", sa.Integer(), nullable=True),
    sa.Column("recent_window_count", sa.Integer(), server_default="0", nullable=False),
    sa.Column("recent_repeat_count", sa.Integer(), server_default="0", nullable=False),
    sa.Column("unplanned_share", sa.Float(), nullable=True),
    sa.Column(
        "total_downtime_hours", sa.Float(), server_default="0", nullable=False
    ),
    sa.Column(
        "has_maintenance_history", sa.Boolean(), server_default=sa.false(), nullable=False
    ),
    sa.Column("evidence", sa.JSON(), nullable=True),
)


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    schema = "govasset" if dialect == "postgresql" else None

    if dialect == "sqlite":
        with op.batch_alter_table("triage_runs", schema=schema) as batch:
            for column in TRIAGE_RUN_COLUMNS:
                batch.add_column(column)
        with op.batch_alter_table("recommendations", schema=schema) as batch:
            for column in RECOMMENDATION_COLUMNS:
                batch.add_column(column)
        op.create_index(
            "ix_recommendations_institution_id",
            "recommendations",
            ["institution_id"],
            schema=schema,
        )
        op.create_index(
            "ix_recommendations_maintenance_priority",
            "recommendations",
            ["maintenance_priority"],
            schema=schema,
        )
        return

    for column in TRIAGE_RUN_COLUMNS:
        op.add_column("triage_runs", column, schema=schema)
    for column in RECOMMENDATION_COLUMNS:
        op.add_column("recommendations", column, schema=schema)
    op.create_index(
        "ix_recommendations_institution_id",
        "recommendations",
        ["institution_id"],
        schema=schema,
    )
    op.create_index(
        "ix_recommendations_maintenance_priority",
        "recommendations",
        ["maintenance_priority"],
        schema=schema,
    )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    schema = "govasset" if dialect == "postgresql" else None

    op.drop_index(
        "ix_recommendations_maintenance_priority", table_name="recommendations", schema=schema
    )
    op.drop_index(
        "ix_recommendations_institution_id", table_name="recommendations", schema=schema
    )

    recommendation_names = [column.name for column in RECOMMENDATION_COLUMNS]
    triage_run_names = [column.name for column in TRIAGE_RUN_COLUMNS]

    if dialect == "sqlite":
        with op.batch_alter_table("recommendations", schema=schema) as batch:
            for name in recommendation_names:
                batch.drop_column(name)
        with op.batch_alter_table("triage_runs", schema=schema) as batch:
            for name in triage_run_names:
                batch.drop_column(name)
        return

    for name in recommendation_names:
        op.drop_column("recommendations", name, schema=schema)
    for name in triage_run_names:
        op.drop_column("triage_runs", name, schema=schema)
