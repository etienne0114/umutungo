"""Synchronization and traversal for the verified Rwanda institution catalog."""

from collections import defaultdict, deque
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from govasset_api.catalogs.rwanda_v2026_09_30 import (
    CATALOG_VERIFIED_ON,
    RWANDA_GOVERNMENT_INSTITUTIONS,
)
from govasset_api.models import Institution


@dataclass(frozen=True)
class CatalogSyncSummary:
    created: int
    updated: int
    unchanged: int

    @property
    def total(self) -> int:
        return self.created + self.updated + self.unchanged


def sync_rwanda_government_catalog(session: Session) -> CatalogSyncSummary:
    """Idempotently insert/update the immutable 2026-09-30 official snapshot."""

    existing = {
        institution.code: institution
        for institution in session.scalars(select(Institution)).all()
    }
    created = 0
    updated = 0
    unchanged = 0

    for entry in RWANDA_GOVERNMENT_INSTITUTIONS:
        parent = existing.get(entry.parent_code) if entry.parent_code else None
        values = {
            "name": entry.name,
            "short_name": entry.short_name,
            "institution_type": entry.institution_type,
            "active": True,
            "parent_institution_id": parent.id if parent else None,
            "is_official": True,
            "source_url": entry.source_url,
            "source_verified_on": CATALOG_VERIFIED_ON,
            "description": entry.description,
        }
        institution = existing.get(entry.code)
        if institution is None:
            institution = Institution(code=entry.code, **values)
            session.add(institution)
            session.flush()
            existing[entry.code] = institution
            created += 1
            continue

        changed = False
        for field, value in values.items():
            if getattr(institution, field) != value:
                setattr(institution, field, value)
                changed = True
        if changed:
            updated += 1
        else:
            unchanged += 1

    session.commit()
    return CatalogSyncSummary(created=created, updated=updated, unchanged=unchanged)


def descendant_institution_ids(session: Session, root_id: int) -> set[int]:
    """Return a root and every descendant without relying on dialect-specific SQL."""

    rows = session.execute(
        select(Institution.id, Institution.parent_institution_id)
    ).all()
    children: dict[int, list[int]] = defaultdict(list)
    all_ids: set[int] = set()
    for institution_id, parent_id in rows:
        all_ids.add(institution_id)
        if parent_id is not None:
            children[parent_id].append(institution_id)
    if root_id not in all_ids:
        return set()

    result: set[int] = set()
    queue: deque[int] = deque([root_id])
    while queue:
        institution_id = queue.popleft()
        if institution_id in result:
            continue
        result.add(institution_id)
        queue.extend(children.get(institution_id, ()))
    return result
