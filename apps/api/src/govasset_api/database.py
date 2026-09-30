import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from govasset_api.config import load_local_environment

load_local_environment()


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None):
    url = database_url or os.getenv("DATABASE_URL", "sqlite:///./govasset.db")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
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
    if "last_inspected_on" not in asset_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE govasset.assets ADD COLUMN last_inspected_on DATE")
                if schema is not None
                else text("ALTER TABLE assets ADD COLUMN last_inspected_on DATE")
            )


def session_dependency(factory: sessionmaker[Session]):
    def get_session() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    return get_session
