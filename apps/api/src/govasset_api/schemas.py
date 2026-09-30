from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetCondition(StrEnum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class RiskLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class RecommendationEventType(StrEnum):
    REVIEW = "review"
    OUTCOME = "outcome"


class RecommendationDisposition(StrEnum):
    ACCEPTED = "accepted"
    DEFERRED = "deferred"
    REJECTED = "rejected"


class VerifiedOutcome(StrEnum):
    PLANNED_MAINTENANCE = "planned_maintenance"
    UNSCHEDULED_REPAIR = "unscheduled_repair"
    NO_MAINTENANCE_FOUND = "no_maintenance_found"
    OTHER = "other"


class AssetCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_code: str = Field(min_length=1, max_length=80)
    asset_type: str = Field(min_length=1, max_length=80)
    make: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    acquisition_date: date | None = None
    last_service_date: date | None = None
    next_service_due: date | None = None
    condition: AssetCondition = AssetCondition.UNKNOWN
    active: bool = True

    @model_validator(mode="after")
    def dates_are_ordered(self):
        if (
            self.last_service_date is not None
            and self.next_service_due is not None
            and self.next_service_due < self.last_service_date
        ):
            raise ValueError("next_service_due cannot be earlier than last_service_date")
        return self


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_code: str
    asset_type: str
    make: str | None
    model: str | None
    acquisition_date: date | None
    last_inspected_on: date | None
    last_service_date: date | None
    next_service_due: date | None
    condition: AssetCondition
    active: bool
    created_at: datetime


class MaintenanceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_date: date
    category: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=4000)
    planned: bool = False
    downtime_hours: float | None = Field(default=None, ge=0)


class MaintenanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    event_date: date
    category: str
    description: str | None
    planned: bool
    downtime_hours: float | None
    created_at: datetime


class InspectionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    inspected_on: date
    condition: AssetCondition
    observations: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_observations(self):
        if self.condition == AssetCondition.UNKNOWN:
            raise ValueError("An inspection must record an observed condition.")
        return self


class InspectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    inspected_on: date
    condition: AssetCondition
    observations: str | None
    created_at: datetime


class TriageItem(BaseModel):
    asset: AssetRead
    risk_level: RiskLevel
    reasons: list[str]
    recommended_action: str
    rule_version: str
    evaluated_on: date


class TriageRunRead(BaseModel):
    id: int
    evaluated_on: date
    rule_version: str
    created_at: datetime
    recommendation_count: int


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    asset_id: int
    risk_level: RiskLevel
    reasons: list[str]
    recommended_action: str
    rule_version: str
    evaluated_on: date
    asset_snapshot: AssetRead
    created_at: datetime


class RecommendationEventCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_type: RecommendationEventType
    disposition: RecommendationDisposition | None = None
    outcome: VerifiedOutcome | None = None
    occurred_on: date | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_event_shape(self):
        if self.event_type == RecommendationEventType.REVIEW:
            if self.disposition is None or self.outcome is not None or self.occurred_on is not None:
                raise ValueError("A review requires a disposition and cannot include an outcome.")
            if self.reason is None:
                raise ValueError("A review requires a reason.")
        elif self.outcome is None or self.occurred_on is None or self.disposition is not None:
            raise ValueError("An outcome requires an outcome type and occurred_on date.")
        return self


class RecommendationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recommendation_id: int
    event_type: RecommendationEventType
    disposition: RecommendationDisposition | None
    outcome: VerifiedOutcome | None
    occurred_on: date | None
    reason: str | None
    created_at: datetime


class AdminUserRead(BaseModel):
    id: str
    email: str | None
    created_at: datetime
    email_confirmed_at: datetime | None
    last_sign_in_at: datetime | None
    access: str
    role: str
    full_name: str | None
    organization: str | None


class AdminAccessUpdate(BaseModel):
    approved: bool
