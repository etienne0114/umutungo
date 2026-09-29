import os

from alembic import context

from govasset_api.database import Base, make_engine
from govasset_api import models  # noqa: F401

config = context.config

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
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
    with connectable.connect() as connection:
        if schema is not None:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS govasset")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
