from datetime import date

from govasset_api.models import Asset
from govasset_api.schemas import RiskLevel, TriageItem

RULE_VERSION = "maintenance-triage-v1"
UPCOMING_SERVICE_DAYS = 14
OVERDUE_HIGH_DAYS = 30


def assess_asset(asset: Asset, as_of: date) -> TriageItem:
    """Apply transparent service-planning rules; this is not a failure prediction."""
    reasons: list[str] = []
    overdue_days = (
        (as_of - asset.next_service_due).days if asset.next_service_due is not None else None
    )

    if asset.condition == "critical":
        risk = RiskLevel.CRITICAL
        reasons.append("Recorded asset condition is critical.")
    elif asset.condition == "poor" or (
        overdue_days is not None and overdue_days > OVERDUE_HIGH_DAYS
    ):
        risk = RiskLevel.HIGH
        if asset.condition == "poor":
            reasons.append("Recorded asset condition is poor.")
        if overdue_days is not None and overdue_days > OVERDUE_HIGH_DAYS:
            reasons.append(f"Service is overdue by {overdue_days} days.")
    elif (
        asset.condition == "fair"
        or (overdue_days is not None and overdue_days >= 0)
        or (
            asset.next_service_due is not None
            and 0 < (asset.next_service_due - as_of).days <= UPCOMING_SERVICE_DAYS
        )
    ):
        risk = RiskLevel.MEDIUM
        if asset.condition == "fair":
            reasons.append("Recorded asset condition is fair.")
        if overdue_days is not None and overdue_days >= 0:
            if overdue_days == 0:
                reasons.append("Scheduled service is due today.")
            else:
                reasons.append(f"Service is overdue by {overdue_days} days.")
        elif asset.next_service_due is not None:
            days_until_due = (asset.next_service_due - as_of).days
            if 0 < days_until_due <= UPCOMING_SERVICE_DAYS:
                reasons.append(f"Scheduled service is due in {days_until_due} days.")
    elif asset.condition == "good" and asset.next_service_due is not None:
        risk = RiskLevel.LOW
        reasons.append("Recorded condition is good and scheduled service is not imminent.")
    else:
        risk = RiskLevel.INSUFFICIENT_DATA
        reasons.append("Condition or scheduled-service information is insufficient for triage.")

    action = {
        RiskLevel.CRITICAL: "Arrange prompt qualified inspection; follow existing safety procedures.",
        RiskLevel.HIGH: "Prioritize a maintenance officer review and schedule an inspection.",
        RiskLevel.MEDIUM: "Review the service plan and schedule work as appropriate.",
        RiskLevel.LOW: "Continue routine monitoring and scheduled maintenance.",
        RiskLevel.INSUFFICIENT_DATA: "Verify asset records and arrange manual review if needed.",
    }[risk]

    return TriageItem(
        asset=asset,
        risk_level=risk,
        reasons=reasons,
        recommended_action=action,
        rule_version=RULE_VERSION,
        evaluated_on=as_of,
    )
