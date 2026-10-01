"""Institution-level aggregation and normalised maintenance priority scoring.

Institutions are compared using *normalised* indicators (ratios and per-asset
frequency) rather than raw totals, so a large fleet is not automatically ranked
above a small one. Metric weights are renormalised when a metric is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

HIGH_RISK_LEVELS = ("high", "critical")
ATTENTION_PRIORITIES = ("urgent", "high", "medium")


@dataclass(frozen=True)
class InstitutionPriorityConfig:
    weight_high_risk_ratio: float = 0.40
    weight_critical_ratio: float = 0.25
    weight_maintenance_frequency: float = 0.20
    weight_replacement_ratio: float = 0.15
    frequency_cap_per_year: float = 4.0
    urgent_threshold: int = 80
    high_threshold: int = 60
    medium_threshold: int = 35


DEFAULT_INSTITUTION_CONFIG = InstitutionPriorityConfig()


@dataclass
class InstitutionAssessment:
    institution_id: int | None
    institution_name: str
    institution_code: str | None
    total_assets: int
    high_risk_assets: int
    critical_assets: int
    medium_risk_assets: int
    low_risk_assets: int
    insufficient_data_assets: int
    maintenance_candidates: int
    replacement_candidates: int
    maintenance_events: int
    average_age_years: float | None
    events_per_asset: float | None
    maintenance_frequency: float | None
    high_risk_ratio: float
    critical_ratio: float
    replacement_ratio: float | None
    priority_score: int
    priority_level: str
    reasons: list[str] = field(default_factory=list)


def priority_level_for_score(score: int, config: InstitutionPriorityConfig) -> str:
    if score >= config.urgent_threshold:
        return "urgent"
    if score >= config.high_threshold:
        return "high"
    if score >= config.medium_threshold:
        return "medium"
    return "low"


def _per_asset_frequency(maintenance_count: int, asset_age_years: float | None) -> float | None:
    if asset_age_years and asset_age_years > 0:
        return maintenance_count / asset_age_years
    return None


def build_institution_assessments(
    items,
    institutions_by_id: dict[int, tuple[str, str | None]],
    as_of: date,
    config: InstitutionPriorityConfig = DEFAULT_INSTITUTION_CONFIG,
) -> list[InstitutionAssessment]:
    """Aggregate per-asset assessments into institution maintenance priorities.

    ``items`` may be live :class:`AssetAssessment` objects or persisted
    ``Recommendation`` rows; both expose the attributes read here.
    """

    grouped: dict[int | None, list] = {}
    for item in items:
        grouped.setdefault(item.institution_id, []).append(item)

    assessments: list[InstitutionAssessment] = []
    for institution_id, rows in grouped.items():
        name, code = institutions_by_id.get(
            institution_id, ("Unassigned assets", None)
        ) if institution_id is not None else ("Unassigned assets", None)

        total = len(rows)
        critical = sum(1 for row in rows if row.risk_level == "critical")
        high = sum(1 for row in rows if row.risk_level == "high")
        medium = sum(1 for row in rows if row.risk_level == "medium")
        low = sum(1 for row in rows if row.risk_level == "low")
        insufficient = sum(1 for row in rows if row.risk_level == "insufficient_data")
        maintenance_candidates = sum(
            1 for row in rows if row.maintenance_priority in ATTENTION_PRIORITIES
        )
        replacement_candidates = sum(1 for row in rows if row.replacement_candidate)
        maintenance_events = sum(int(row.maintenance_count or 0) for row in rows)

        ages = [row.asset_age_years for row in rows if row.asset_age_years is not None]
        average_age = round(sum(ages) / len(ages), 2) if ages else None

        frequencies = [
            freq
            for freq in (
                _per_asset_frequency(int(row.maintenance_count or 0), row.asset_age_years)
                for row in rows
            )
            if freq is not None
        ]
        maintenance_frequency = (
            round(sum(frequencies) / len(frequencies), 3) if frequencies else None
        )

        high_risk = high + critical
        high_risk_ratio = round(high_risk / total, 4) if total else 0.0
        critical_ratio = round(critical / total, 4) if total else 0.0
        replacement_ratio = round(replacement_candidates / total, 4) if total else None
        events_per_asset = round(maintenance_events / total, 2) if total else None

        assessments.append(
            InstitutionAssessment(
                institution_id=institution_id,
                institution_name=name,
                institution_code=code,
                total_assets=total,
                high_risk_assets=high_risk,
                critical_assets=critical,
                medium_risk_assets=medium,
                low_risk_assets=low,
                insufficient_data_assets=insufficient,
                maintenance_candidates=maintenance_candidates,
                replacement_candidates=replacement_candidates,
                maintenance_events=maintenance_events,
                average_age_years=average_age,
                events_per_asset=events_per_asset,
                maintenance_frequency=maintenance_frequency,
                high_risk_ratio=high_risk_ratio,
                critical_ratio=critical_ratio,
                replacement_ratio=replacement_ratio,
                priority_score=0,
                priority_level="low",
            )
        )

    _score_institutions(assessments, config)
    assessments.sort(key=lambda item: (-item.priority_score, item.institution_name))
    return assessments


def _score_institutions(
    assessments: list[InstitutionAssessment],
    config: InstitutionPriorityConfig,
) -> None:
    frequencies = [item.maintenance_frequency for item in assessments if item.maintenance_frequency]
    system_average_frequency = (
        sum(frequencies) / len(frequencies) if frequencies else None
    )

    for item in assessments:
        factors: dict[str, float] = {}
        weights: dict[str, float] = {}

        factors["high_risk_ratio"] = item.high_risk_ratio * 100.0
        weights["high_risk_ratio"] = config.weight_high_risk_ratio

        factors["critical_ratio"] = item.critical_ratio * 100.0
        weights["critical_ratio"] = config.weight_critical_ratio

        if item.maintenance_frequency is not None:
            factors["maintenance_frequency"] = min(
                item.maintenance_frequency / config.frequency_cap_per_year, 1.0
            ) * 100.0
            weights["maintenance_frequency"] = config.weight_maintenance_frequency

        if item.replacement_ratio is not None:
            factors["replacement_ratio"] = item.replacement_ratio * 100.0
            weights["replacement_ratio"] = config.weight_replacement_ratio

        total_weight = sum(weights.values())
        score = (
            round(sum(factors[key] * weights[key] for key in factors) / total_weight)
            if total_weight
            else 0
        )
        item.priority_score = max(0, min(score, 100))
        item.priority_level = priority_level_for_score(item.priority_score, config)
        item.reasons = _institution_reasons(item, system_average_frequency)


def _institution_reasons(
    item: InstitutionAssessment,
    system_average_frequency: float | None,
) -> list[str]:
    reasons: list[str] = []
    high_pct = round(item.high_risk_ratio * 100)
    critical_pct = round(item.critical_ratio * 100)

    if high_pct:
        reasons.append(f"{high_pct}% of assets are high or critical risk.")
    else:
        reasons.append("No assets are currently in the high or critical risk bands.")
    if critical_pct:
        reasons.append(f"{critical_pct}% of assets are critical risk.")

    if item.maintenance_frequency is not None and system_average_frequency:
        if item.maintenance_frequency >= system_average_frequency:
            reasons.append(
                f"Maintenance frequency ({item.maintenance_frequency:.2f}/year) is above the system average."
            )
        else:
            reasons.append(
                f"Maintenance frequency ({item.maintenance_frequency:.2f}/year) is below the system average."
            )

    if item.replacement_candidates:
        reasons.append(
            f"{item.replacement_candidates} asset(s) are replacement candidates."
        )
    if item.average_age_years is not None:
        reasons.append(f"Average asset age is {item.average_age_years:.1f} years.")
    return reasons
