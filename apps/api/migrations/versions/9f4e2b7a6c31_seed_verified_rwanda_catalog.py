"""seed verified Rwanda government institution catalog

Revision ID: 9f4e2b7a6c31
Revises: 5c27b67a1f4d
Create Date: 2026-09-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from govasset_api.catalogs.rwanda_v2026_09_30 import (
    CATALOG_VERIFIED_ON,
    RWANDA_GOVERNMENT_INSTITUTIONS,
)


revision: str = "9f4e2b7a6c31"
down_revision: Union[str, Sequence[str], None] = "5c27b67a1f4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INSTITUTION_TYPE_CHECK = (
    "institution_type IN ('ministry', 'agency', 'authority', 'commission', "
    "'public_institution', 'other_government_entity', 'province', 'city', 'district')"
)
LEGACY_INSTITUTION_TYPE_CHECK = (
    "institution_type IN ('ministry', 'agency', 'authority', 'commission', "
    "'public_institution', 'other_government_entity')"
)


def _drop_sqlite_cycle_guard() -> None:
    op.execute("DROP TRIGGER IF EXISTS institution_cycle_insert")
    op.execute("DROP TRIGGER IF EXISTS institution_cycle_update")


def _create_sqlite_cycle_guard() -> None:
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


def _add_catalog_columns() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        _drop_sqlite_cycle_guard()
        with op.batch_alter_table("institutions") as batch:
            batch.drop_constraint("ck_institutions_type", type_="check")
            batch.add_column(sa.Column("short_name", sa.String(length=80), nullable=True))
            batch.add_column(
                sa.Column(
                    "is_official",
                    sa.Boolean(),
                    server_default=sa.false(),
                    nullable=False,
                )
            )
            batch.add_column(sa.Column("description", sa.Text(), nullable=True))
            batch.add_column(sa.Column("source_url", sa.String(length=500), nullable=True))
            batch.add_column(sa.Column("source_verified_on", sa.Date(), nullable=True))
            batch.create_check_constraint("ck_institutions_type", INSTITUTION_TYPE_CHECK)
        _create_sqlite_cycle_guard()
    else:
        schema = "govasset"
        op.drop_constraint(
            "ck_institutions_type", "institutions", type_="check", schema=schema
        )
        op.add_column(
            "institutions", sa.Column("short_name", sa.String(length=80)), schema=schema
        )
        op.add_column(
            "institutions",
            sa.Column(
                "is_official",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            ),
            schema=schema,
        )
        op.add_column("institutions", sa.Column("description", sa.Text()), schema=schema)
        op.add_column(
            "institutions", sa.Column("source_url", sa.String(length=500)), schema=schema
        )
        op.add_column(
            "institutions", sa.Column("source_verified_on", sa.Date()), schema=schema
        )
        op.create_check_constraint(
            "ck_institutions_type", "institutions", INSTITUTION_TYPE_CHECK, schema=schema
        )
    op.create_index(
        "ix_institutions_is_official",
        "institutions",
        ["is_official"],
        schema="govasset" if dialect == "postgresql" else None,
    )


def _seed_catalog() -> None:
    connection = op.get_bind()
    schema = "govasset" if connection.dialect.name == "postgresql" else None
    institutions = sa.table(
        "institutions",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("code", sa.String),
        sa.column("short_name", sa.String),
        sa.column("institution_type", sa.String),
        sa.column("active", sa.Boolean),
        sa.column("is_official", sa.Boolean),
        sa.column("description", sa.Text),
        sa.column("source_url", sa.String),
        sa.column("source_verified_on", sa.Date),
        sa.column("parent_institution_id", sa.Integer),
        schema=schema,
    )
    ids_by_code = dict(
        connection.execute(sa.select(institutions.c.code, institutions.c.id)).all()
    )
    for entry in RWANDA_GOVERNMENT_INSTITUTIONS:
        parent_id = ids_by_code.get(entry.parent_code) if entry.parent_code else None
        values = {
            "name": entry.name,
            "short_name": entry.short_name,
            "institution_type": entry.institution_type,
            "active": True,
            "is_official": True,
            "description": entry.description,
            "source_url": entry.source_url,
            "source_verified_on": CATALOG_VERIFIED_ON,
            "parent_institution_id": parent_id,
        }
        existing_id = ids_by_code.get(entry.code)
        if existing_id is not None:
            connection.execute(
                institutions.update()
                .where(institutions.c.id == existing_id)
                .values(**values)
            )
            continue

        connection.execute(
            institutions.insert().values(code=entry.code, **values)
        )
        ids_by_code[entry.code] = connection.scalar(
            sa.select(institutions.c.id).where(institutions.c.code == entry.code)
        )


def upgrade() -> None:
    _add_catalog_columns()
    _seed_catalog()


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    schema = "govasset" if dialect == "postgresql" else None
    institutions = sa.table(
        "institutions",
        sa.column("institution_type", sa.String),
        schema=schema,
    )
    op.get_bind().execute(
        institutions.update()
        .where(institutions.c.institution_type.in_(("province", "city", "district")))
        .values(institution_type="other_government_entity")
    )
    op.drop_index("ix_institutions_is_official", table_name="institutions", schema=schema)
    if dialect == "sqlite":
        _drop_sqlite_cycle_guard()
        with op.batch_alter_table("institutions") as batch:
            batch.drop_constraint("ck_institutions_type", type_="check")
            batch.create_check_constraint(
                "ck_institutions_type", LEGACY_INSTITUTION_TYPE_CHECK
            )
            batch.drop_column("source_verified_on")
            batch.drop_column("source_url")
            batch.drop_column("description")
            batch.drop_column("is_official")
            batch.drop_column("short_name")
        _create_sqlite_cycle_guard()
    else:
        op.drop_constraint(
            "ck_institutions_type", "institutions", type_="check", schema=schema
        )
        op.create_check_constraint(
            "ck_institutions_type",
            "institutions",
            LEGACY_INSTITUTION_TYPE_CHECK,
            schema=schema,
        )
        for column in (
            "source_verified_on",
            "source_url",
            "description",
            "is_official",
            "short_name",
        ):
            op.drop_column("institutions", column, schema=schema)
