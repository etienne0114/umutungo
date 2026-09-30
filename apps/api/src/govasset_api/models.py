from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from govasset_api.database import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("institution_id", "asset_code", name="uq_assets_institution_code"),
        Index(
            "uq_assets_unassigned_code",
            "asset_code",
            unique=True,
            sqlite_where=text("institution_id IS NULL"),
            postgresql_where=text("institution_id IS NULL"),
        ),
        Index("ix_assets_institution_id", "institution_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True
    )
    asset_code: Mapped[str] = mapped_column(String(80))
    asset_type: Mapped[str] = mapped_column(String(80), index=True)
    make: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    acquisition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_inspected_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_service_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    condition: Mapped[str] = mapped_column(String(20), default="unknown")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", order_by="MaintenanceRecord.event_date"
    )
    inspections: Mapped[list["InspectionRecord"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="InspectionRecord.inspected_on",
    )


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    event_date: Mapped[date] = mapped_column(Date, index=True)
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    planned: Mapped[bool] = mapped_column(Boolean, default=False)
    downtime_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    asset: Mapped[Asset] = relationship(back_populates="maintenance_records")


class InspectionRecord(Base):
    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    inspected_on: Mapped[date] = mapped_column(Date, index=True)
    condition: Mapped[str] = mapped_column(String(20))
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    asset: Mapped[Asset] = relationship(back_populates="inspections")


class TriageRun(Base):
    __tablename__ = "triage_runs"
    __table_args__ = (Index("ix_triage_runs_institution_id", "institution_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True
    )
    evaluated_on: Mapped[date] = mapped_column(Date, index=True)
    rule_version: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (UniqueConstraint("run_id", "asset_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("triage_runs.id"), index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    risk_level: Mapped[str] = mapped_column(String(30), index=True)
    reasons: Mapped[list[str]] = mapped_column(JSON)
    recommended_action: Mapped[str] = mapped_column(Text)
    rule_version: Mapped[str] = mapped_column(String(80))
    evaluated_on: Mapped[date] = mapped_column(Date, index=True)
    asset_snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    run: Mapped[TriageRun] = relationship(back_populates="recommendations")
    events: Mapped[list["RecommendationEvent"]] = relationship(
        back_populates="recommendation",
        cascade="all, delete-orphan",
        order_by="RecommendationEvent.id",
    )


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(20), index=True)
    disposition: Mapped[str | None] = mapped_column(String(20), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    recommendation: Mapped[Recommendation] = relationship(back_populates="events")


class Institution(Base):
    __tablename__ = "institutions"
    __table_args__ = (
        UniqueConstraint("code", name="uq_institutions_code"),
        Index("ix_institutions_parent_id", "parent_institution_id"),
        Index("ix_institutions_active", "active"),
        CheckConstraint(
            "institution_type IN ('ministry', 'agency', 'authority', 'commission', "
            "'public_institution', 'other_government_entity', 'province', 'city', "
            "'district')",
            name="ck_institutions_type",
        ),
        CheckConstraint(
            "parent_institution_id IS NULL OR parent_institution_id != id",
            name="ck_institutions_not_own_parent",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(80))
    short_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    institution_type: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_verified_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    parent_institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), nullable=True
    )
    parent: Mapped["Institution | None"] = relationship(
        remote_side="Institution.id", back_populates="children"
    )
    children: Mapped[list["Institution"]] = relationship(back_populates="parent")


class InstitutionMembership(Base):
    __tablename__ = "institution_memberships"
    __table_args__ = (
        Index("ix_institution_memberships_institution_id", "institution_id"),
        Index("ix_institution_memberships_user_id", "user_id"),
        CheckConstraint(
            "role IN ('institution_admin', 'fleet_manager', 'maintenance_officer', "
            "'technician', 'driver', 'auditor', 'viewer')",
            name="ck_institution_membership_role",
        ),
    )

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("institutions.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(40))
    institution: Mapped[Institution] = relationship()
