"""System-administrator account access endpoints."""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from govasset_api.auth import require_admin_user
from govasset_api.schemas import AdminAccessUpdate, AdminUserRead
from govasset_api.supabase_admin import SupabaseAdminError


def _service_error(exc: SupabaseAdminError) -> HTTPException:
    detail = str(exc)
    code = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if "not configured" in detail
        else status.HTTP_502_BAD_GATEWAY
    )
    return HTTPException(status_code=code, detail=detail)


def _user_summary(user: dict[str, Any], fallback_id: str = "") -> AdminUserRead:
    metadata = user.get("app_metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    user_metadata = user.get("user_metadata")
    user_metadata = user_metadata if isinstance(user_metadata, dict) else {}
    return AdminUserRead(
        id=str(user.get("id", fallback_id)),
        email=user.get("email"),
        created_at=user["created_at"],
        email_confirmed_at=user.get("email_confirmed_at"),
        last_sign_in_at=user.get("last_sign_in_at"),
        access="approved" if metadata.get("govasset_access") == "approved" else "pending",
        role="admin" if metadata.get("govasset_role") == "admin" else "user",
        full_name=(
            user_metadata.get("full_name")
            if isinstance(user_metadata.get("full_name"), str)
            else None
        ),
        organization=(
            user_metadata.get("organization")
            if isinstance(user_metadata.get("organization"), str)
            else None
        ),
    )


def create_router(
    *,
    list_users_page: Callable[..., list[dict[str, Any]]],
    get_user: Callable[[str], dict[str, Any]],
    update_user_metadata: Callable[[str, dict[str, Any]], dict[str, Any]],
) -> APIRouter:
    router = APIRouter(
        prefix="/admin/users",
        tags=["administration"],
        dependencies=[Depends(require_admin_user)],
    )

    @router.get("", response_model=list[AdminUserRead])
    def list_users(
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=100, ge=1, le=100),
    ):
        try:
            users = list_users_page(page=page, per_page=per_page)
        except SupabaseAdminError as exc:
            raise _service_error(exc) from exc
        return [_user_summary(user) for user in users]

    @router.put("/{user_id}/access", response_model=AdminUserRead)
    def update_user_access(
        user_id: UUID,
        payload: AdminAccessUpdate,
        admin_claims: dict = Depends(require_admin_user),
    ):
        user_id_str = str(user_id)
        if user_id_str == admin_claims.get("sub") and not payload.approved:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Administrators cannot revoke their own access.",
            )
        try:
            target_user = get_user(user_id_str)
            if payload.approved and not target_user.get("email_confirmed_at"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Users must confirm their email before approval.",
                )
            metadata = target_user.get("app_metadata")
            metadata = dict(metadata) if isinstance(metadata, dict) else {}
            expected_access = "approved" if payload.approved else "pending"
            metadata["govasset_access"] = expected_access
            updated_user = update_user_metadata(user_id_str, metadata)
            updated_metadata = updated_user.get("app_metadata")
            if (
                updated_user.get("id") != user_id_str
                or not isinstance(updated_metadata, dict)
                or updated_metadata.get("govasset_access") != expected_access
            ):
                raise SupabaseAdminError(
                    "Supabase did not confirm the requested account access change."
                )
        except SupabaseAdminError as exc:
            raise _service_error(exc) from exc
        return _user_summary(updated_user, user_id_str)

    return router
