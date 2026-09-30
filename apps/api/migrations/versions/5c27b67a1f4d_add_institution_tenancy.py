"""add institution hierarchy, memberships, and tenant ownership

Revision ID: 5c27b67a1f4d
Revises: 1ded697490a9
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5c27b67a1f4d"
down_revision: Union[str, Sequence[str], None] = "1ded697490a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_tenant_columns() -> None:
    dialect = op.get_bind().dialect.name
    schema = "govasset" if dialect == "postgresql" else None
    if dialect == "sqlite":
        with op.batch_alter_table("assets") as batch:
            batch.drop_index("ix_assets_asset_code")
            batch.add_column(sa.Column("institution_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_assets_institution_id_institutions",
                "institutions",
                ["institution_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_unique_constraint(
                "uq_assets_institution_code", ["institution_id", "asset_code"]
            )
        with op.batch_alter_table("triage_runs") as batch:
            batch.add_column(sa.Column("institution_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_triage_runs_institution_id_institutions",
                "institutions",
                ["institution_id"],
                ["id"],
                ondelete="SET NULL",
            )
    else:
        op.drop_index("ix_assets_asset_code", table_name="assets", schema=schema)
        op.add_column(
            "assets",
            sa.Column("institution_id", sa.Integer(), nullable=True),
            schema=schema,
        )
        op.create_foreign_key(
            "fk_assets_institution_id_institutions",
            "assets",
            "institutions",
            ["institution_id"],
            ["id"],
            ondelete="SET NULL",
            source_schema=schema,
            referent_schema=schema,
        )
        op.create_unique_constraint(
            "uq_assets_institution_code",
            "assets",
            ["institution_id", "asset_code"],
            schema=schema,
        )
        op.add_column(
            "triage_runs",
            sa.Column("institution_id", sa.Integer(), nullable=True),
            schema=schema,
        )
        op.create_foreign_key(
            "fk_triage_runs_institution_id_institutions",
            "triage_runs",
            "institutions",
            ["institution_id"],
            ["id"],
            ondelete="SET NULL",
            source_schema=schema,
            referent_schema=schema,
        )

    op.create_index(
        "uq_assets_unassigned_code",
        "assets",
        ["asset_code"],
        unique=True,
        postgresql_where=sa.text("institution_id IS NULL"),
        sqlite_where=sa.text("institution_id IS NULL"),
        schema=schema,
    )
    op.create_index("ix_assets_institution_id", "assets", ["institution_id"], schema=schema)
    op.create_index(
        "ix_triage_runs_institution_id", "triage_runs", ["institution_id"], schema=schema
    )


def _create_cycle_guard() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER institution_cycle_insert
            BEFORE INSERT ON institutions
            WHEN NEW.parent_institution_id IS NOT NULL
            BEGIN
                SELECT CASE WHEN EXISTS (
                    WITH RECURSIVE ancestors(id) AS (
                        SELECT NEW.parent_institution_id
                        UNION ALL
                        SELECT institution.parent_institution_id
                        FROM institutions AS institution
                        JOIN ancestors ON institution.id = ancestors.id
                        WHERE institution.parent_institution_id IS NOT NULL
                    )
                    SELECT 1 FROM ancestors WHERE id = NEW.id
                ) THEN RAISE(ABORT, 'institution hierarchy cycle') END;
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER institution_cycle_update
            BEFORE UPDATE OF parent_institution_id ON institutions
            WHEN NEW.parent_institution_id IS NOT NULL
            BEGIN
                SELECT CASE WHEN EXISTS (
                    WITH RECURSIVE ancestors(id) AS (
                        SELECT NEW.parent_institution_id
                        UNION ALL
                        SELECT institution.parent_institution_id
                        FROM institutions AS institution
                        JOIN ancestors ON institution.id = ancestors.id
                        WHERE institution.parent_institution_id IS NOT NULL
                    )
                    SELECT 1 FROM ancestors WHERE id = NEW.id
                ) THEN RAISE(ABORT, 'institution hierarchy cycle') END;
            END
            """
        )
    elif dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION govasset.reject_institution_cycle() RETURNS trigger
            LANGUAGE plpgsql AS $$
            DECLARE creates_cycle boolean;
            BEGIN
                IF NEW.parent_institution_id IS NULL THEN
                    RETURN NEW;
                END IF;
                WITH RECURSIVE ancestors(id) AS (
                    SELECT NEW.parent_institution_id
                    UNION ALL
                    SELECT institution.parent_institution_id
                    FROM govasset.institutions AS institution
                    JOIN ancestors ON institution.id = ancestors.id
                    WHERE institution.parent_institution_id IS NOT NULL
                )
                SELECT EXISTS(SELECT 1 FROM ancestors WHERE id = NEW.id)
                    INTO creates_cycle;
                IF creates_cycle THEN
                    RAISE EXCEPTION 'institution hierarchy cycle';
                END IF;
                RETURN NEW;
            END;
            $$
            """
        )
        op.execute(
            """
            CREATE TRIGGER institution_cycle_guard
            BEFORE INSERT OR UPDATE OF parent_institution_id ON govasset.institutions
            FOR EACH ROW EXECUTE FUNCTION govasset.reject_institution_cycle()
            """
        )


def upgrade() -> None:
    schema = "govasset" if op.get_bind().dialect.name == "postgresql" else None
    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("institution_type", sa.String(length=40), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("parent_institution_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "parent_institution_id IS NULL OR parent_institution_id != id",
            name="ck_institutions_not_own_parent",
        ),
        sa.CheckConstraint(
            "institution_type IN ('ministry', 'agency', 'authority', 'commission', "
            "'public_institution', 'other_government_entity')",
            name="ck_institutions_type",
        ),
        sa.ForeignKeyConstraint(
            ["parent_institution_id"],
            [f"{schema + '.' if schema else ''}institutions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_institutions_code"),
        schema=schema,
    )
    op.create_index("ix_institutions_parent_id", "institutions", ["parent_institution_id"], schema=schema)
    op.create_index("ix_institutions_active", "institutions", ["active"], schema=schema)
    op.create_table(
        "institution_memberships",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.CheckConstraint(
            "role IN ('institution_admin', 'fleet_manager', 'maintenance_officer', "
            "'technician', 'driver', 'auditor', 'viewer')",
            name="ck_institution_membership_role",
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            [f"{schema + '.' if schema else ''}institutions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "institution_id"),
        schema=schema,
    )
    op.create_index(
        "ix_institution_memberships_institution_id",
        "institution_memberships",
        ["institution_id"],
        schema=schema,
    )
    op.create_index(
        "ix_institution_memberships_user_id",
        "institution_memberships",
        ["user_id"],
        schema=schema,
    )
    _add_tenant_columns()
    _create_cycle_guard()


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    schema = "govasset" if dialect == "postgresql" else None
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS institution_cycle_insert")
        op.execute("DROP TRIGGER IF EXISTS institution_cycle_update")
    elif dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS institution_cycle_guard ON govasset.institutions")
        op.execute("DROP FUNCTION IF EXISTS govasset.reject_institution_cycle()")
    op.drop_index(
        "ix_triage_runs_institution_id", table_name="triage_runs", schema=schema
    )
    op.drop_index("ix_assets_institution_id", table_name="assets", schema=schema)
    op.drop_index("uq_assets_unassigned_code", table_name="assets", schema=schema)
    if dialect == "sqlite":
        with op.batch_alter_table("triage_runs") as batch:
            batch.drop_constraint(
                "fk_triage_runs_institution_id_institutions",
                type_="foreignkey",
            )
            batch.drop_column("institution_id")
        with op.batch_alter_table("assets") as batch:
            batch.drop_constraint("uq_assets_institution_code", type_="unique")
            batch.drop_constraint(
                "fk_assets_institution_id_institutions",
                type_="foreignkey",
            )
            batch.drop_column("institution_id")
            batch.create_index("ix_assets_asset_code", ["asset_code"], unique=True)
    else:
        op.drop_constraint(
            "fk_triage_runs_institution_id_institutions",
            "triage_runs",
            type_="foreignkey",
            schema=schema,
        )
        op.drop_column("triage_runs", "institution_id", schema=schema)
        op.drop_constraint(
            "uq_assets_institution_code",
            "assets",
            type_="unique",
            schema=schema,
        )
        op.drop_constraint(
            "fk_assets_institution_id_institutions",
            "assets",
            type_="foreignkey",
            schema=schema,
        )
        op.drop_column("assets", "institution_id", schema=schema)
        op.create_index(
            "ix_assets_asset_code",
            "assets",
            ["asset_code"],
            unique=True,
            schema=schema,
        )
    op.drop_index(
        "ix_institution_memberships_user_id",
        table_name="institution_memberships",
        schema=schema,
    )
    op.drop_index(
        "ix_institution_memberships_institution_id",
        table_name="institution_memberships",
        schema=schema,
    )
    op.drop_table("institution_memberships", schema=schema)
    op.drop_index(
        "ix_institutions_active",
        table_name="institutions",
        schema=schema,
    )
    op.drop_index(
        "ix_institutions_parent_id",
        table_name="institutions",
        schema=schema,
    )
    op.drop_table("institutions", schema=schema)
