"""HTTP API composition for the Umutungo service."""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends

from govasset_api.api.dependencies import build_current_scope_dependency
from govasset_api.api.routers import administration, assets, institutions, operations, triage
from govasset_api.auth import require_authenticated_user


def create_api_router(
    get_session: Callable[..., Any],
    *,
    list_users_page: Callable[..., list[dict[str, Any]]],
    get_user: Callable[[str], dict[str, Any]],
    update_user_metadata: Callable[[str, dict[str, Any]], dict[str, Any]],
    admin_api_configured: Callable[[], bool],
) -> APIRouter:
    """Compose the versioned API from domain-focused routers."""

    router = APIRouter(
        prefix="/api/v1",
        dependencies=[Depends(require_authenticated_user)],
    )
    current_scope = build_current_scope_dependency(get_session)

    router.include_router(
        administration.create_router(
            list_users_page=list_users_page,
            get_user=get_user,
            update_user_metadata=update_user_metadata,
        )
    )
    router.include_router(
        institutions.create_router(
            get_session,
            get_user=get_user,
            admin_api_configured=admin_api_configured,
        )
    )
    router.include_router(assets.create_router(get_session, current_scope))
    router.include_router(operations.create_router(get_session, current_scope))
    router.include_router(triage.create_router(get_session, current_scope))
    return router
