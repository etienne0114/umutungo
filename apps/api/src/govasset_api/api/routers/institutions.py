"""Government institution hierarchy and user membership endpoints."""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import case, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from govasset_api.auth import (
    authentication_required,
    require_admin_user,
    require_authenticated_user,
)
from govasset_api.catalogs.rwanda_v2026_09_30 import (
    CATALOG_VERIFIED_ON,
    RWANDA_GOVERNMENT_INSTITUTIONS,
)
from govasset_api.models import Institution, InstitutionMembership
from govasset_api.schemas import (
    CatalogSyncRead,
    InstitutionCreate,
    InstitutionMembershipCreate,
    InstitutionMembershipRead,
    InstitutionMembershipUpdate,
    InstitutionRead,
    InstitutionUpdate,
)
from govasset_api.services.institution_catalog import sync_rwanda_government_catalog
from govasset_api.services.institutions import (
    validate_membership_target,
    validate_parent,
)


def _institution_order():
    return (
        case(
            (Institution.institution_type == "ministry", 0),
            (Institution.institution_type == "city", 1),
            (Institution.institution_type == "province", 2),
            (Institution.institution_type == "district", 4),
            else_=3,
        ),
        Institution.name,
    )


def create_router(
    get_session: Callable[..., Any],
    *,
    get_user: Callable[[str], dict[str, Any]],
    admin_api_configured: Callable[[], bool],
) -> APIRouter:
    router = APIRouter(tags=["institutions"])

    @router.get("/institutions", response_model=list[InstitutionRead])
    def list_available_institutions(
        claims: dict | None = Depends(require_authenticated_user),
        session: Session = Depends(get_session),
    ):
        metadata = (claims or {}).get("app_metadata")
        if not authentication_required() or (
            isinstance(metadata, dict) and metadata.get("govasset_role") == "admin"
        ):
            return session.scalars(select(Institution).order_by(*_institution_order())).all()
        user_id = claims.get("sub") if claims else None
        memberships = session.execute(
            select(Institution, InstitutionMembership.role)
            .join(InstitutionMembership)
            .where(
                InstitutionMembership.user_id == user_id,
                Institution.active.is_(True),
            )
            .order_by(*_institution_order())
        ).all()
        return [
            {
                **InstitutionRead.model_validate(institution).model_dump(),
                "membership_role": role,
            }
            for institution, role in memberships
        ]

    @router.get(
        "/admin/institutions",
        response_model=list[InstitutionRead],
        dependencies=[Depends(require_admin_user)],
    )
    def list_institutions_admin(session: Session = Depends(get_session)):
        return session.scalars(select(Institution).order_by(*_institution_order())).all()

    @router.post(
        "/admin/institutions/sync-official-catalog",
        response_model=CatalogSyncRead,
        dependencies=[Depends(require_admin_user)],
    )
    def sync_official_catalog(session: Session = Depends(get_session)):
        summary = sync_rwanda_government_catalog(session)
        return CatalogSyncRead(
            created=summary.created,
            updated=summary.updated,
            unchanged=summary.unchanged,
            total=summary.total,
            verified_on=CATALOG_VERIFIED_ON,
            source_urls=sorted(
                {entry.source_url for entry in RWANDA_GOVERNMENT_INSTITUTIONS}
            ),
        )

    @router.post(
        "/admin/institutions",
        response_model=InstitutionRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_admin_user)],
    )
    def create_institution(
        payload: InstitutionCreate,
        session: Session = Depends(get_session),
    ):
        validate_parent(session, None, payload.parent_institution_id)
        institution = Institution(**payload.model_dump())
        session.add(institution)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail="An institution with this code already exists.",
            ) from exc
        session.refresh(institution)
        return institution

    @router.patch(
        "/admin/institutions/{institution_id}",
        response_model=InstitutionRead,
        dependencies=[Depends(require_admin_user)],
    )
    def update_institution(
        institution_id: int,
        payload: InstitutionUpdate,
        session: Session = Depends(get_session),
    ):
        institution = session.get(Institution, institution_id)
        if institution is None:
            raise HTTPException(status_code=404, detail="Institution not found.")
        changes = payload.model_dump(exclude_unset=True)
        for field in ("name", "code", "institution_type", "active"):
            if field in changes and changes[field] is None:
                raise HTTPException(status_code=422, detail=f"{field} cannot be null.")
        if "parent_institution_id" in changes:
            validate_parent(session, institution_id, changes["parent_institution_id"])
        for field, value in changes.items():
            setattr(institution, field, value.value if hasattr(value, "value") else value)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail="An institution with this code already exists.",
            ) from exc
        session.refresh(institution)
        return institution

    @router.get(
        "/admin/memberships",
        response_model=list[InstitutionMembershipRead],
        dependencies=[Depends(require_admin_user)],
    )
    def list_memberships(
        institution_id: int | None = None,
        session: Session = Depends(get_session),
    ):
        query = select(InstitutionMembership).order_by(
            InstitutionMembership.institution_id,
            InstitutionMembership.user_id,
        )
        if institution_id is not None:
            query = query.where(InstitutionMembership.institution_id == institution_id)
        return session.scalars(query).all()

    @router.post(
        "/admin/memberships",
        response_model=InstitutionMembershipRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_admin_user)],
    )
    def create_membership(
        payload: InstitutionMembershipCreate,
        session: Session = Depends(get_session),
    ):
        institution = session.get(Institution, payload.institution_id)
        if institution is None:
            raise HTTPException(status_code=404, detail="Institution not found.")
        if not institution.active:
            raise HTTPException(
                status_code=409,
                detail="Memberships require an active institution.",
            )
        user_id = str(payload.user_id)
        validate_membership_target(
            user_id,
            get_user=get_user,
            admin_api_configured=admin_api_configured,
        )
        membership = InstitutionMembership(
            user_id=user_id,
            institution_id=payload.institution_id,
            role=payload.role.value,
        )
        session.add(membership)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail="This user already has a membership in the institution.",
            ) from exc
        return membership

    @router.patch(
        "/admin/memberships/{user_id}/{institution_id}",
        response_model=InstitutionMembershipRead,
        dependencies=[Depends(require_admin_user)],
    )
    def update_membership(
        user_id: UUID,
        institution_id: int,
        payload: InstitutionMembershipUpdate,
        session: Session = Depends(get_session),
    ):
        membership = session.get(InstitutionMembership, (str(user_id), institution_id))
        if membership is None:
            raise HTTPException(status_code=404, detail="Institution membership not found.")
        institution = session.get(Institution, institution_id)
        if not institution or not institution.active:
            raise HTTPException(
                status_code=409,
                detail="Memberships require an active institution.",
            )
        validate_membership_target(
            str(user_id),
            get_user=get_user,
            admin_api_configured=admin_api_configured,
        )
        membership.role = payload.role.value
        session.commit()
        return membership

    @router.delete(
        "/admin/memberships/{user_id}/{institution_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(require_admin_user)],
    )
    def delete_membership(
        user_id: UUID,
        institution_id: int,
        session: Session = Depends(get_session),
    ):
        membership = session.get(InstitutionMembership, (str(user_id), institution_id))
        if membership is None:
            raise HTTPException(status_code=404, detail="Institution membership not found.")
        session.delete(membership)
        session.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
