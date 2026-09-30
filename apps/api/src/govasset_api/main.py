"""Umutungo FastAPI application factory.

Domain endpoints live under ``govasset_api.api.routers``. This module only
owns process-level concerns: configuration, lifespan, middleware, and router
composition.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from govasset_api.api import create_api_router
from govasset_api.auth import authentication_required, supabase_url
from govasset_api.database import (
    initialize_schema,
    make_engine,
    make_session_factory,
    session_dependency,
)
from govasset_api.supabase_admin import (
    get_supabase_user,
    list_supabase_users_page,
    supabase_admin_configured,
    update_supabase_user_app_metadata,
)


def _cors_origins() -> list[str]:
    configured = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


def create_app(engine: Engine | None = None) -> FastAPI:
    database_engine = engine or make_engine()
    get_session = session_dependency(make_session_factory(database_engine))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if authentication_required() and engine is None:
            if supabase_url() is None:
                raise RuntimeError("SUPABASE_URL is required when AUTH_REQUIRED is enabled.")
            if database_engine.dialect.name != "postgresql":
                raise RuntimeError("Hosted mode requires a persistent PostgreSQL DATABASE_URL.")
        else:
            initialize_schema(database_engine)
        yield

    app = FastAPI(
        title="Umutungo API",
        version="0.1.0",
        description=(
            "Asset history and transparent maintenance decision support. "
            "Current triage rules are advisory and are not AI predictions."
        ),
        lifespan=lifespan,
    )
    cors_origin_regex = os.getenv(
        "CORS_ORIGIN_REGEX",
        r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|https://umutungo-[a-z0-9-]+-etienne0114s-projects\.vercel\.app)$",
    ).strip() or None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_origin_regex=cors_origin_regex,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    # Delegates resolve module globals at request time. Tests can replace the
    # external transport without coupling route modules to a concrete client.
    app.include_router(
        create_api_router(
            get_session,
            list_users_page=lambda **kwargs: list_supabase_users_page(**kwargs),
            get_user=lambda user_id: get_supabase_user(user_id),
            update_user_metadata=lambda user_id, metadata: update_supabase_user_app_metadata(
                user_id, metadata
            ),
            admin_api_configured=lambda: supabase_admin_configured(),
        )
    )
    return app


app = create_app()
