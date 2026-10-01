"""Deterministic maintenance risk, priority, and replacement scoring.

This module is the rule/math engine of the analytics architecture. It has no
AI/LLM dependency: every score is derived from historical asset, maintenance,
inspection, and downtime records using transparent, configurable weights.

Each factor is normalised to 0-100. Factors that have no supporting data are
excluded and the remaining weights are renormalised, so missing data is never
treated as maximum risk. Assets with no scorable evidence at all are reported
as ``insufficient_data`` rather than being assigned a fabricated score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

ENGINE_VERSION = "maintenance-risk-engine-v1"

DAYS_PER_YEAR = 365.25

# Recorded condition mapped to a 0-100 factor score. ``unknown`` is intentionally
# absent so it is treated as unavailable data and its weight is redistributed.
CONDITION_FACTOR: dict[str, float] = {
    "good": 0.0,
    "fair": 35.0,
    "poor": 70.0,
    "critical": 100.0,
}

# A recorded poor/critical condition sets a minimum risk band so a single strong
# signal is not diluted by an otherwise thin history. This is a documented rule,
# not a prediction.
CONDITION_RISK_FLOOR: dict[str, int] = {
    "poor": 60,
    "critical": 80,
}

# Operational criticality shifts maintenance *priority* (urgency to act) without
# changing the underlying condition *risk*.
CRITICALITY_PRIORITY_BONUS: dict[str, int] = {
    "standard": 0,
    "important": 6,
    "mission_critical": 12,
}

OVERDUE_PRIORITY_BONUS = 10
OVERDUE_SEVERE_DAYS = 30
OVERDUE_SEVERE_PRIORITY_BONUS = 14
RECENT_REPEAT_PRIORITY_BONUS = 8

RISK_LEVEL_ORDER = ["critical", "high", "medium", "low", "insufficient_data"]


@dataclass(frozen=True)
class RiskConfig:
    """Centralised, tunable weights and thresholds for the risk engine."""

    # Risk factor weights (renormalised across the factors that have data).
    weight_maintenance_frequency: float = 0.30
    weight_age: float = 0.20
    weight_recent_maintenance: float = 0.20
    weight_condition: float = 0.20
    weight_downtime: float = 0.10

    # Normalisation caps used to scale each factor into 0-100.
    age_cap_years: float = 15.0
    frequency_cap_per_year: float = 4.0
    recent_cap_events: float = 6.0
    downtime_cap_hours: float = 200.0

    # Maintenance recency windows.
    recent_window_days: int = 180
    recent_repeat_window_days: int = 90
    recent_repeat_threshold: int = 2

    # Risk bands (lower bound inclusive).
    critical_threshold: int = 80
    high_threshold: int = 60
    medium_threshold: int = 30

    # Replacement scoring.
    replacement_weight_age: float = 0.35
    replacement_weight_frequency: float = 0.25
    replacement_weight_recent: float = 0.15
    replacement_weight_unplanned: float = 0.15
    replacement_weight_condition: float = 0.10
    replacement_age_cap_years: float = 16.0
    replacement_age_threshold_years: float = 8.0
    replacement_score_threshold: float = 60.0

    # Maintenance priority bands (lower bound inclusive).
    priority_urgent_threshold: int = 80
    priority_high_threshold: int = 60
    priority_medium_threshold: int = 40
    priority_low_threshold: int = 20


DEFAULT_CONFIG = RiskConfig()


@dataclass
class MaintenanceAggregate:
    """Per-asset maintenance history totals used as engine input."""

    maintenance_count: int = 0
    last_event_date: date | None = None
    recent_window_count: int = 0
    recent_repeat_count: int = 0
    unplanned_count: int = 0
    total_downtime_hours: float = 0.0
    downtime_records: int = 0


@dataclass
class AssetAssessment:
    """A fully explained, deterministic assessment for a single asset."""

    asset_id: int
    institution_id: int | None
    institution_name: str | None
    asset_code: str
    asset_type: str
    make: str | None
    model: str | None
    registration_number: str | None
    criticality: str
    condition: str
    asset_age_years: float | None
    maintenance_count: int
    maintenance_frequency: float | None
    days_since_last_maintenance: int | None
    recent_window_count: int
    recent_repeat_count: int
    unplanned_share: float | None
    total_downtime_hours: float
    has_maintenance_history: bool
    risk_score: int | None
    risk_level: str
    factor_scores: dict[str, float] = field(default_factory=dict)
    factor_weights: dict[str, float] = field(default_factory=dict)
    priority_score: int = 0
    maintenance_priority: str = "monitor"
    replacement_score: int = 0
    replacement_candidate: bool = False
    recommendation: str = ""
    reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


def _scaled(value: float | None, cap: float) -> float | None:
    if value is None or cap <= 0:
        return None
    return max(0.0, min(float(value) / cap, 1.0)) * 100.0


def compute_asset_age_years(asset, as_of: date) -> float | None:
    """Best-available age: acquisition date first, otherwise manufacture year."""

    if getattr(asset, "acquisition_date", None) is not None:
        days = (as_of - asset.acquisition_date).days
        return round(max(days, 0) / DAYS_PER_YEAR, 2)
    manufacture_year = getattr(asset, "manufacture_year", None)
    if manufacture_year:
        try:
            approx = date(int(manufacture_year), 7, 1)
        except ValueError:
            return None
        days = (as_of - approx).days
        if days < 0:
            return None
        return round(days / DAYS_PER_YEAR, 2)
    return None


def risk_level_for_score(score: int | None, config: RiskConfig = DEFAULT_CONFIG) -> str:
    if score is None:
        return "insufficient_data"
    if score >= config.critical_threshold:
        return "critical"
    if score >= config.high_threshold:
        return "high"
    if score >= config.medium_threshold:
        return "medium"
    return "low"


def priority_level_for_score(score: int, config: RiskConfig = DEFAULT_CONFIG) -> str:
    if score >= config.priority_urgent_threshold:
        return "urgent"
    if score >= config.priority_high_threshold:
        return "high"
    if score >= config.priority_medium_threshold:
        return "medium"
    if score >= config.priority_low_threshold:
        return "low"
    return "monitor"


def _weighted(values: dict[str, float], weights: dict[str, float]) -> int | None:
    total_weight = sum(weights[key] for key in values)
    if total_weight <= 0:
        return None
    return round(sum(values[key] * weights[key] for key in values) / total_weight)


def assess_asset(
    asset,
    aggregate: MaintenanceAggregate,
    as_of: date,
    config: RiskConfig = DEFAULT_CONFIG,
    *,
    institution_name: str | None = None,
) -> AssetAssessment:
    """Score one asset deterministically and produce explained evidence."""

    age_years = compute_asset_age_years(asset, as_of)
    count = aggregate.maintenance_count
    frequency = round(count / age_years, 3) if (age_years and age_years > 0) else None
    days_since = (
        (as_of - aggregate.last_event_date).days
        if aggregate.last_event_date is not None
        else None
    )
    unplanned_share = round(aggregate.unplanned_count / count, 3) if count else None
    has_history = count > 0

    # --- Risk factors (each normalised to 0-100, unavailable factors excluded) ---
    factors: dict[str, float] = {}
    weights: dict[str, float] = {}

    age_factor = _scaled(age_years, config.age_cap_years)
    if age_factor is not None:
        factors["age"] = age_factor
        weights["age"] = config.weight_age

    frequency_factor = _scaled(frequency, config.frequency_cap_per_year)
    if frequency_factor is not None:
        factors["maintenance_frequency"] = frequency_factor
        weights["maintenance_frequency"] = config.weight_maintenance_frequency

    if has_history:
        factors["recent_maintenance"] = _scaled(
            aggregate.recent_window_count, config.recent_cap_events
        ) or 0.0
        weights["recent_maintenance"] = config.weight_recent_maintenance

    condition = getattr(asset, "condition", "unknown")
    if condition in CONDITION_FACTOR:
        factors["condition"] = CONDITION_FACTOR[condition]
        weights["condition"] = config.weight_condition

    if aggregate.downtime_records > 0:
        factors["downtime"] = _scaled(
            aggregate.total_downtime_hours, config.downtime_cap_hours
        ) or 0.0
        weights["downtime"] = config.weight_downtime

    risk_score = _weighted(factors, weights)
    if risk_score is not None:
        floor = CONDITION_RISK_FLOOR.get(condition)
        if floor is not None:
            risk_score = max(risk_score, floor)
    risk_level = risk_level_for_score(risk_score, config)

    # --- Maintenance priority (urgency to act, distinct from risk) ---
    if risk_score is None:
        priority_score = 0
        maintenance_priority = "monitor"
    else:
        priority_score = risk_score + CRITICALITY_PRIORITY_BONUS.get(
            getattr(asset, "criticality", "standard"), 0
        )
        next_service_due = getattr(asset, "next_service_due", None)
        if next_service_due is not None and next_service_due <= as_of:
            overdue_days = (as_of - next_service_due).days
            priority_score += (
                OVERDUE_SEVERE_PRIORITY_BONUS
                if overdue_days > OVERDUE_SEVERE_DAYS
                else OVERDUE_PRIORITY_BONUS
            )
        if aggregate.recent_repeat_count >= config.recent_repeat_threshold:
            priority_score += RECENT_REPEAT_PRIORITY_BONUS
        priority_score = max(0, min(priority_score, 100))
        maintenance_priority = priority_level_for_score(priority_score, config)

    # --- Replacement consideration (combined evidence, not age alone) ---
    replacement_factors: dict[str, float] = {}
    replacement_weights: dict[str, float] = {}
    replacement_age_factor = _scaled(age_years, config.replacement_age_cap_years)
    if replacement_age_factor is not None:
        replacement_factors["age"] = replacement_age_factor
        replacement_weights["age"] = config.replacement_weight_age
    if frequency_factor is not None:
        replacement_factors["frequency"] = frequency_factor
        replacement_weights["frequency"] = config.replacement_weight_frequency
    if has_history:
        replacement_factors["recent"] = _scaled(
            aggregate.recent_window_count, config.recent_cap_events
        ) or 0.0
        replacement_weights["recent"] = config.replacement_weight_recent
        if unplanned_share is not None:
            replacement_factors["unplanned"] = unplanned_share * 100.0
            replacement_weights["unplanned"] = config.replacement_weight_unplanned
    if condition in CONDITION_FACTOR:
        replacement_factors["condition"] = CONDITION_FACTOR[condition]
        replacement_weights["condition"] = config.replacement_weight_condition

    replacement_score = _weighted(replacement_factors, replacement_weights) or 0
    replacement_candidate = replacement_score >= config.replacement_score_threshold

    recommendation = _recommendation(risk_level, replacement_candidate)
    reasons = _reasons(
        risk_score=risk_score,
        risk_level=risk_level,
        condition=condition,
        age_years=age_years,
        frequency=frequency,
        count=count,
        recent_repeat_count=aggregate.recent_repeat_count,
        replacement_score=replacement_score,
        replacement_candidate=replacement_candidate,
        recent_repeat_window_days=config.recent_repeat_window_days,
    )
    evidence = _evidence(
        age_years=age_years,
        count=count,
        frequency=frequency,
        days_since=days_since,
        recent_repeat_count=aggregate.recent_repeat_count,
        recent_repeat_window_days=config.recent_repeat_window_days,
        condition=condition,
        total_downtime_hours=aggregate.total_downtime_hours,
        downtime_records=aggregate.downtime_records,
        unplanned_share=unplanned_share,
        replacement_score=replacement_score,
    )

    return AssetAssessment(
        asset_id=asset.id,
        institution_id=getattr(asset, "institution_id", None),
        institution_name=institution_name,
        asset_code=asset.asset_code,
        asset_type=asset.asset_type,
        make=getattr(asset, "make", None),
        model=getattr(asset, "model", None),
        registration_number=getattr(asset, "registration_number", None),
        criticality=getattr(asset, "criticality", "standard"),
        condition=condition,
        asset_age_years=age_years,
        maintenance_count=count,
        maintenance_frequency=frequency,
        days_since_last_maintenance=days_since,
        recent_window_count=aggregate.recent_window_count,
        recent_repeat_count=aggregate.recent_repeat_count,
        unplanned_share=unplanned_share,
        total_downtime_hours=round(aggregate.total_downtime_hours, 2),
        has_maintenance_history=has_history,
        risk_score=risk_score,
        risk_level=risk_level,
        factor_scores={key: round(value, 1) for key, value in factors.items()},
        factor_weights={key: round(value, 3) for key, value in weights.items()},
        priority_score=priority_score,
        maintenance_priority=maintenance_priority,
        replacement_score=replacement_score,
        replacement_candidate=replacement_candidate,
        recommendation=recommendation,
        reasons=reasons,
        evidence=evidence,
    )


def _recommendation(risk_level: str, replacement_candidate: bool) -> str:
    if risk_level == "insufficient_data":
        return "Verify asset records; insufficient maintenance history for scoring."
    if replacement_candidate and risk_level in ("high", "critical"):
        return "Evaluate for replacement; prioritize technical inspection."
    if risk_level == "critical":
        return "Prioritize technical inspection and maintenance."
    if risk_level == "high":
        return "Schedule preventive inspection within the next maintenance cycle."
    if replacement_candidate:
        return "Evaluate for replacement at the next technical assessment."
    if risk_level == "medium":
        return "Review the service plan and monitor the maintenance trend."
    return "Continue normal preventive maintenance and monitoring."


def _reasons(
    *,
    risk_score: int | None,
    risk_level: str,
    condition: str,
    age_years: float | None,
    frequency: float | None,
    count: int,
    recent_repeat_count: int,
    replacement_score: int,
    replacement_candidate: bool,
    recent_repeat_window_days: int,
) -> list[str]:
    reasons: list[str] = []
    if risk_score is None:
        reasons.append(
            "No asset age, recorded condition, or maintenance history is available to score."
        )
        return reasons

    reasons.append(f"Risk score {risk_score}/100 places this asset in the {risk_level} band.")
    if condition in CONDITION_FACTOR and condition != "good":
        reasons.append(f"Recorded condition is {condition}.")
    if age_years is not None:
        reasons.append(f"Asset age is {age_years:.1f} years.")
    if frequency is not None and count:
        reasons.append(
            f"Maintenance frequency is {frequency:.2f} events/year across {count} recorded events."
        )
    elif count == 0:
        reasons.append("No maintenance history recorded for this asset.")
    if recent_repeat_count > 0:
        reasons.append(
            f"{recent_repeat_count} maintenance events in the last {recent_repeat_window_days} days."
        )
    if replacement_candidate:
        reasons.append(
            f"Replacement score {replacement_score}/100 indicates a high long-term maintenance burden."
        )
    return reasons


def _evidence(
    *,
    age_years: float | None,
    count: int,
    frequency: float | None,
    days_since: int | None,
    recent_repeat_count: int,
    recent_repeat_window_days: int,
    condition: str,
    total_downtime_hours: float,
    downtime_records: int,
    unplanned_share: float | None,
    replacement_score: int,
) -> list[str]:
    evidence: list[str] = []
    evidence.append(f"Age: {age_years:.1f} years" if age_years is not None else "Age: not recorded")
    evidence.append(f"Maintenance events: {count}")
    evidence.append(
        f"Maintenance frequency: {frequency:.2f}/year"
        if frequency is not None
        else "Maintenance frequency: not calculable (missing age or history)"
    )
    evidence.append(
        f"Last maintenance: {days_since} days ago"
        if days_since is not None
        else "Last maintenance: no history recorded"
    )
    if recent_repeat_count:
        evidence.append(
            f"Recent activity: {recent_repeat_count} events in the last {recent_repeat_window_days} days"
        )
    evidence.append(f"Recorded condition: {condition}")
    if downtime_records:
        evidence.append(f"Total downtime: {total_downtime_hours:.0f} hours")
    if unplanned_share is not None:
        evidence.append(f"Unplanned repairs: {unplanned_share * 100:.0f}% of events")
    evidence.append(f"Replacement consideration: {replacement_score}/100")
    return evidence
