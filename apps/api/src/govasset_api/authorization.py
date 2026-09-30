from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from govasset_api.auth import authentication_required
from govasset_api.models import Asset, Institution, InstitutionMembership, TriageRun

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "institution_admin": frozenset(
        {
            "asset:write",
            "maintenance:write",
            "inspection:write",
            "triage:run",
            "recommendation:review",
            "recommendation:outcome",
        }
    ),
    "fleet_manager": frozenset(
        {
            "asset:write",
            "maintenance:write",
            "inspection:write",
            "triage:run",
            "recommendation:review",
            "recommendation:outcome",
        }
    ),
    "maintenance_officer": frozenset(
        {
            "maintenance:write",
            "inspection:write",
            "triage:run",
            "recommendation:review",
            "recommendation:outcome",
        }
    ),
    "technician": frozenset(
        {
            "maintenance:write",
            "inspection:write",
            "recommendation:outcome",
        }
    ),
    "driver": frozenset(),
    "auditor": frozenset(),
    "viewer": frozenset(),
}


@dataclass(frozen=True)
class TenantScope:
    institution_id: int | None
    role: str | None
    global_admin: bool = False
    local_development: bool = False


def is_global_admin(claims: dict[str, Any] | None) -> bool:
    metadata = claims.get("app_metadata") if claims else None
    return isinstance(metadata, dict) and metadata.get("govasset_role") == "admin"


def resolve_tenant_scope(
    claims: dict[str, Any] | None,
    session: Session,
    institution_id: int | None = None,
) -> TenantScope:
    local = not authentication_required()
    if local:
        if institution_id is not None and session.get(Institution, institution_id) is None:
            raise HTTPException(status_code=404, detail="Institution not found.")
        return TenantScope(institution_id, None, local_development=True)

    if is_global_admin(claims):
        if institution_id is not None and session.get(Institution, institution_id) is None:
            raise HTTPException(status_code=404, detail="Institution not found.")
        return TenantScope(institution_id, None, global_admin=True)

    user_id = claims.get("sub") if claims else None
    memberships = session.scalars(
        select(InstitutionMembership)
        .join(Institution)
        .where(
            InstitutionMembership.user_id == user_id,
            Institution.active.is_(True),
        )
        .order_by(InstitutionMembership.institution_id)
    ).all()
    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your approved account has no active institution membership. "
                "Contact a system administrator."
            ),
        )
    if institution_id is None:
        if len(memberships) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Select one of your institution memberships with the "
                    "institution_id query parameter."
                ),
            )
        membership = memberships[0]
    else:
        membership = next(
            (item for item in memberships if item.institution_id == institution_id),
            None,
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to the selected institution.",
            )
    return TenantScope(membership.institution_id, membership.role)


def ensure_permission(scope: TenantScope, permission: str) -> None:
    if scope.global_admin or scope.local_development:
        return
    if permission in ROLE_PERMISSIONS.get(scope.role or "", frozenset()):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Your institution role is read-only for this action and does not grant "
            f"{permission}."
        ),
    )


def scoped_assets(statement, scope: TenantScope):
    if scope.global_admin or scope.local_development:
        if scope.institution_id is not None:
            return statement.where(Asset.institution_id == scope.institution_id)
        return statement
    return statement.where(Asset.institution_id == scope.institution_id)


def scoped_runs(statement, scope: TenantScope):
    if scope.global_admin or scope.local_development:
        if scope.institution_id is not None:
            return statement.where(TriageRun.institution_id == scope.institution_id)
        return statement
    return statement.where(TriageRun.institution_id == scope.institution_id)
