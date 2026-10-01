import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from govasset_api.config import load_local_environment

load_local_environment()


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None):
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required. Configure the Supabase PostgreSQL connection URL."
        )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine_options = {}
    if os.getenv("VERCEL") and url.startswith("postgresql+psycopg://"):
        # A warm function reuses one connection through Supavisor transaction pooling.
        connect_args = {
            "prepare_threshold": None,
            "sslmode": "require",
            "connect_timeout": 10,
        }
        engine_options = {"pool_size": 1, "max_overflow": 0, "pool_pre_ping": True}
    engine = create_engine(url, connect_args=connect_args, **engine_options)
    if engine.dialect.name == "postgresql":
        return engine.execution_options(schema_translate_map={None: "govasset"})
    return engine


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def initialize_schema(engine: Engine) -> None:
    schema = "govasset" if engine.dialect.name == "postgresql" else None
    if schema is not None:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS govasset")
    Base.metadata.create_all(engine)
    asset_columns = {
        column["name"] for column in inspect(engine).get_columns("assets", schema=schema)
    }
    column_definitions = {"last_inspected_on": "last_inspected_on DATE"}
    if engine.dialect.name == "sqlite":
        column_definitions.update(
            {
                "registration_number": "registration_number VARCHAR(40)",
                "manufacture_year": "manufacture_year INTEGER",
                "criticality": (
                    "criticality VARCHAR(20) NOT NULL DEFAULT 'standard'"
                ),
            }
        )
    missing_definitions = [
        definition
        for name, definition in column_definitions.items()
        if name not in asset_columns
    ]
    if missing_definitions:
        table_name = "govasset.assets" if schema is not None else "assets"
        with engine.begin() as connection:
            for definition in missing_definitions:
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {definition}"))


    from govasset_api.services.institution_catalog import sync_rwanda_government_catalog

    with Session(engine) as session:
        sync_rwanda_government_catalog(session)


def session_dependency(factory: sessionmaker[Session]):
    def get_session() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    return get_session
