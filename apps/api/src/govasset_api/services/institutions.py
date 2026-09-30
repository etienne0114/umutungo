"""Institution hierarchy and membership validation rules."""

from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from govasset_api.models import Institution
from govasset_api.supabase_admin import SupabaseAdminError


def validate_parent(
    session: Session,
    child_id: int | None,
    parent_id: int | None,
) -> None:
    if parent_id is None:
        return
    seen: set[int] = set()
    ancestor_id: int | None = parent_id
    while ancestor_id is not None:
        if ancestor_id == child_id:
            raise HTTPException(
                status_code=422,
                detail="An institution cannot be its own parent or an ancestor of itself.",
            )
        if ancestor_id in seen:
            raise HTTPException(
                status_code=409,
                detail="The existing institution hierarchy contains a cycle.",
            )
        seen.add(ancestor_id)
        ancestor = session.get(Institution, ancestor_id)
        if ancestor is None:
            raise HTTPException(status_code=422, detail="Parent institution does not exist.")
        ancestor_id = ancestor.parent_institution_id


def validate_membership_target(
    user_id: str,
    *,
    get_user: Callable[[str], dict[str, Any]],
    admin_api_configured: Callable[[], bool],
) -> None:
    if not admin_api_configured():
        return
    try:
        user = get_user(user_id)
    except SupabaseAdminError as exc:
        detail = str(exc)
        code = 503 if "not configured" in detail else 502
        raise HTTPException(status_code=code, detail=detail) from exc
    metadata = user.get("app_metadata")
    if user.get("id") != user_id or not isinstance(metadata, dict):
        raise HTTPException(status_code=422, detail="Supabase user could not be verified.")
    if metadata.get("govasset_access") != "approved":
        raise HTTPException(
            status_code=409,
            detail="Institution membership can only be assigned to an approved Supabase user.",
        )
