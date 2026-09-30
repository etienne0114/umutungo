from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetCondition(StrEnum):
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AssetCriticality(StrEnum):
    STANDARD = "standard"
    IMPORTANT = "important"
    MISSION_CRITICAL = "mission_critical"


class UsageReadingSource(StrEnum):
    MANUAL = "manual"
    IMPORT = "import"
    TELEMATICS = "telematics"
    MAINTENANCE = "maintenance"


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


class InstitutionType(StrEnum):
    MINISTRY = "ministry"
    AGENCY = "agency"
    AUTHORITY = "authority"
    COMMISSION = "commission"
    PUBLIC_INSTITUTION = "public_institution"
    OTHER_GOVERNMENT_ENTITY = "other_government_entity"
    PROVINCE = "province"
    CITY = "city"
    DISTRICT = "district"


class InstitutionRole(StrEnum):
    INSTITUTION_ADMIN = "institution_admin"
    FLEET_MANAGER = "fleet_manager"
    MAINTENANCE_OFFICER = "maintenance_officer"
    TECHNICIAN = "technician"
    DRIVER = "driver"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class InstitutionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=80)
    short_name: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    institution_type: InstitutionType
    active: bool = True
    parent_institution_id: int | None = None


class InstitutionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=80)
    short_name: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    institution_type: InstitutionType | None = None
    active: bool | None = None
    parent_institution_id: int | None = None


class InstitutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    short_name: str | None
    institution_type: InstitutionType
    active: bool
    is_official: bool
    description: str | None
    source_url: str | None
    source_verified_on: date | None
    parent_institution_id: int | None
    membership_role: InstitutionRole | None = None


class CatalogSyncRead(BaseModel):
    created: int
    updated: int
    unchanged: int
    total: int
    verified_on: date
    source_urls: list[str]


class InstitutionMembershipCreate(BaseModel):
    user_id: UUID
    institution_id: int
    role: InstitutionRole


class InstitutionMembershipUpdate(BaseModel):
    role: InstitutionRole


class InstitutionMembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    institution_id: int
    role: InstitutionRole


class AssetCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_code: str = Field(min_length=1, max_length=80)
    asset_type: str = Field(min_length=1, max_length=80)
    make: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    registration_number: str | None = Field(default=None, max_length=40)
    manufacture_year: int | None = Field(default=None, ge=1900, le=2200)
    criticality: AssetCriticality = AssetCriticality.STANDARD
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


class AssetUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_code: str | None = Field(default=None, min_length=1, max_length=80)
    asset_type: str | None = Field(default=None, min_length=1, max_length=80)
    make: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    registration_number: str | None = Field(default=None, max_length=40)
    manufacture_year: int | None = Field(default=None, ge=1900, le=2200)
    criticality: AssetCriticality | None = None
    acquisition_date: date | None = None
    last_service_date: date | None = None
    next_service_due: date | None = None
    condition: AssetCondition | None = None
    active: bool | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_id: int | None
    asset_code: str
    asset_type: str
    make: str | None
    model: str | None
    registration_number: str | None
    manufacture_year: int | None
    criticality: AssetCriticality
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
    odometer_km: float | None = Field(default=None, ge=0)
    cost_amount: float | None = Field(default=None, ge=0)
    currency: str = Field(default="RWF", pattern=r"^RWF$")
    provider_name: str | None = Field(default=None, max_length=200)
    work_order_reference: str | None = Field(default=None, max_length=100)


class MaintenanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    event_date: date
    category: str
    description: str | None
    planned: bool
    downtime_hours: float | None
    odometer_km: float | None
    cost_amount: float | None
    currency: str
    provider_name: str | None
    work_order_reference: str | None
    created_at: datetime


class UsageReadingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    recorded_on: date
    odometer_km: float = Field(ge=0)
    source: UsageReadingSource = UsageReadingSource.MANUAL
    notes: str | None = Field(default=None, max_length=1000)


class UsageReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    recorded_on: date
    odometer_km: float
    source: UsageReadingSource
    notes: str | None
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
    institution_id: int | None = None
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


class OperationsReport(BaseModel):
    generated_on: date
    scope_institution_id: int | None
    scope_name: str
    included_institutions: int
    total_assets: int
    active_assets: int
    inactive_assets: int
    condition_recorded_assets: int
    condition_unknown_assets: int
    missing_acquisition_date: int
    missing_inspection_date: int
    missing_service_schedule: int
    inconsistent_service_dates: int
    assets_with_maintenance_history: int
    inspection_records: int
    maintenance_records: int
    service_due_assets: int
    overdue_service_assets: int
    risk_counts: dict[str, int]
    planned_maintenance_records: int
    unplanned_maintenance_records: int
    downtime_hours_recorded: float
    maintenance_records_without_downtime: int
    untracked_domains: list[str]


class InstitutionReportRow(BaseModel):
    institution: InstitutionRead
    descendant_count: int
    report: OperationsReport


class InstitutionTreeReport(BaseModel):
    generated_on: date
    root_count: int
    unassigned_assets: int
    rows: list[InstitutionReportRow]


class MaintenanceIntervalRead(BaseModel):
    sequence_number: int
    from_event_id: int
    to_event_id: int
    from_date: date
    to_date: date
    days_between: int
    from_odometer_km: float | None
    to_odometer_km: float | None
    distance_km: float | None


class HistoricalForecastRead(BaseModel):
    status: str
    method: str
    estimated_next_service_date: date | None
    estimated_interval_days: float | None
    evidence_event_count: int
    explanation: str
    limitations: list[str]


class ModelReadinessRead(BaseModel):
    status: str
    usable_for_trained_model: bool
    maintenance_event_count: int
    usage_reading_count: int
    fields_present: list[str]
    missing_requirements: list[str]


class AssetMaintenanceAnalytics(BaseModel):
    generated_on: date
    asset: AssetRead
    asset_age_days: int | None
    asset_age_years: float | None
    first_maintenance_date: date | None
    last_maintenance_date: date | None
    days_since_last_maintenance: int | None
    maintenance_event_count: int
    planned_event_count: int
    unplanned_event_count: int
    unplanned_share: float | None
    total_downtime_hours: float
    total_cost_amount: float
    cost_currency: str
    most_common_category: str | None
    most_common_category_count: int
    mean_interval_days: float | None
    median_interval_days: float | None
    shortest_interval_days: int | None
    longest_interval_days: int | None
    interval_trend: str
    intervals: list[MaintenanceIntervalRead]
    latest_odometer_km: float | None
    latest_odometer_date: date | None
    usage_reading_count: int
    distance_recorded_km: float | None
    risk_level: RiskLevel
    risk_reasons: list[str]
    recommended_action: str
    rule_version: str
    forecast: HistoricalForecastRead
    model_readiness: ModelReadinessRead


class InstitutionMaintenanceAnalytics(BaseModel):
    institution: InstitutionRead
    descendant_count: int
    asset_count: int
    active_asset_count: int
    assets_with_maintenance: int
    maintenance_history_coverage: float | None
    maintenance_event_count: int
    events_per_asset: float | None
    planned_event_count: int
    unplanned_event_count: int
    unplanned_share: float | None
    total_downtime_hours: float
    downtime_hours_per_asset: float | None
    total_cost_amount: float
    cost_currency: str
    overdue_service_assets: int
    priority_asset_count: int


class InstitutionMaintenanceComparison(BaseModel):
    generated_on: date
    scope_name: str
    methodology: str
    rows: list[InstitutionMaintenanceAnalytics]


class MaintenanceAnalyticsOverview(BaseModel):
    generated_on: date
    scope_name: str
    included_institutions: int
    asset_count: int
    assets_with_maintenance: int
    maintenance_event_count: int
    planned_event_count: int
    unplanned_event_count: int
    unplanned_share: float | None
    total_downtime_hours: float
    total_cost_amount: float
    cost_currency: str
    overdue_service_assets: int
    priority_asset_count: int
    assets_with_usage_readings: int
    model_ready_asset_count: int
    data_quality_notes: list[str]
