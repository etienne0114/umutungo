import os

from alembic import context
from sqlalchemy import MetaData

from govasset_api.database import Base, make_engine
from govasset_api import models  # noqa: F401

config = context.config

target_metadata = Base.metadata


def metadata_for_schema(schema: str | None):
    if schema is None:
        return target_metadata
    translated = MetaData()
    for table in target_metadata.sorted_tables:
        table.to_metadata(translated, schema=schema)
    for table in translated.tables.values():
        for index in table.indexes:
            if index.name and index.name.startswith("ix_govasset_"):
                index.name = "ix_" + index.name.removeprefix("ix_govasset_")
    return translated


def include_schema_name(name, type_, _parent_names):
    return type_ != "schema" or name == "govasset"


def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for Alembic migrations.")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = make_engine(os.getenv("DATABASE_URL"))
    schema = "govasset" if connectable.dialect.name == "postgresql" else None
    if schema is not None:
        with connectable.begin() as schema_connection:
            schema_connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS govasset")

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=metadata_for_schema(schema),
            include_schemas=schema is not None,
            include_name=include_schema_name if schema is not None else None,
            version_table_schema=schema,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
