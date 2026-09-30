"""Shared dependencies and tenant-scoped entity lookups."""

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from govasset_api.auth import require_authenticated_user
from govasset_api.authorization import TenantScope, resolve_tenant_scope, scoped_assets
from govasset_api.models import Asset, Recommendation


def build_current_scope_dependency(get_session: Callable[..., Any]):
    def current_scope(
        claims: dict | None = Depends(require_authenticated_user),
        session: Session = Depends(get_session),
        institution_id: int | None = Query(default=None),
    ) -> TenantScope:
        return resolve_tenant_scope(claims, session, institution_id)

    return current_scope


def find_asset(session: Session, asset_id: int, scope: TenantScope) -> Asset | None:
    return session.scalar(scoped_assets(select(Asset).where(Asset.id == asset_id), scope))


def find_recommendation(
    session: Session,
    recommendation_id: int,
    scope: TenantScope,
) -> Recommendation | None:
    query = (
        select(Recommendation)
        .join(Asset, Recommendation.asset_id == Asset.id)
        .where(Recommendation.id == recommendation_id)
    )
    return session.scalar(scoped_assets(query, scope))
