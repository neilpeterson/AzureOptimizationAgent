"""Get findings trends for month-over-month analysis.

This endpoint is module-agnostic - it works for any detection module
(abandoned-resources, overprovisioned-vms, idle-databases, etc.)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from shared import CosmosClient


def get_findings_trends(
    module_id: str,
    months: int = 3,
    subscription_id: str | None = None,
) -> dict[str, Any]:
    """Get monthly trend data for a detection module.

    Args:
        module_id: Module ID (e.g., 'abandoned-resources', 'overprovisioned-vms')
        months: Number of months of history to include (default: 3)
        subscription_id: Optional subscription ID to filter by

    Returns:
        Trend data with monthly aggregates and change summary
    """
    client = CosmosClient()

    # Calculate date range
    today = datetime.now(timezone.utc)
    # Go back N months from start of current month
    from_date = (today.replace(day=1) - timedelta(days=months * 31)).replace(day=1)
    to_date = today

    # Query findings for the date range
    findings = client.get_findings_for_trends(
        module_id=module_id,
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%dT23:59:59Z"),
        subscription_id=subscription_id,
    )

    # Aggregate by month
    monthly_data = defaultdict(lambda: {
        "totalFindings": 0,
        "totalCost": 0.0,
        "bySeverity": defaultdict(int),
        "byResourceType": defaultdict(int),
        "subscriptions": set(),
    })

    for finding in findings:
        # Extract year-month from executionDate
        exec_date = finding.get("executionDate", "")
        if len(exec_date) >= 7:
            month_key = exec_date[:7]  # "2026-01"
        else:
            continue

        monthly_data[month_key]["totalFindings"] += 1
        monthly_data[month_key]["totalCost"] += finding.get("estimatedMonthlyCost", 0.0)
        monthly_data[month_key]["bySeverity"][finding.get("severity", "unknown")] += 1
        monthly_data[month_key]["byResourceType"][finding.get("resourceType", "unknown")] += 1
        monthly_data[month_key]["subscriptions"].add(finding.get("subscriptionId", ""))

    # Convert to sorted list (most recent first)
    sorted_months = sorted(monthly_data.keys(), reverse=True)
    trends = []
    for month in sorted_months:
        data = monthly_data[month]
        trends.append({
            "month": month,
            "totalFindings": data["totalFindings"],
            "totalCost": round(data["totalCost"], 2),
            "bySeverity": dict(data["bySeverity"]),
            "byResourceType": dict(data["byResourceType"]),
            "subscriptionsAffected": len(data["subscriptions"]),
        })

    # Calculate change summary (current vs previous month)
    summary = _calculate_change_summary(trends)

    return {
        "moduleId": module_id,
        "subscriptionId": subscription_id,
        "periodMonths": months,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "trends": trends,
        "summary": summary,
    }


def _calculate_change_summary(trends: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate month-over-month change summary.

    Args:
        trends: List of monthly trend data (most recent first)

    Returns:
        Summary with changes and trend direction
    """
    if len(trends) < 2:
        return {
            "hasComparison": False,
            "message": "Insufficient data for comparison (need at least 2 months)",
        }

    current = trends[0]
    previous = trends[1]

    findings_change = current["totalFindings"] - previous["totalFindings"]
    cost_change = current["totalCost"] - previous["totalCost"]

    # Calculate percentages (avoid division by zero)
    if previous["totalFindings"] > 0:
        findings_change_pct = (findings_change / previous["totalFindings"]) * 100
    else:
        findings_change_pct = 100.0 if current["totalFindings"] > 0 else 0.0

    if previous["totalCost"] > 0:
        cost_change_pct = (cost_change / previous["totalCost"]) * 100
    else:
        cost_change_pct = 100.0 if current["totalCost"] > 0 else 0.0

    # Determine trend direction
    if findings_change < 0:
        trend = "improving"
    elif findings_change > 0:
        trend = "worsening"
    else:
        trend = "stable"

    # Generate human-readable message
    message = _generate_trend_message(
        current_findings=current["totalFindings"],
        previous_findings=previous["totalFindings"],
        findings_change=findings_change,
        findings_change_pct=findings_change_pct,
        cost_change=cost_change,
        previous_month=previous["month"],
    )

    return {
        "hasComparison": True,
        "currentMonth": current["month"],
        "previousMonth": previous["month"],
        "findingsChange": findings_change,
        "findingsChangePercent": round(findings_change_pct, 1),
        "costChange": round(cost_change, 2),
        "costChangePercent": round(cost_change_pct, 1),
        "trend": trend,
        "message": message,
    }


def _generate_trend_message(
    current_findings: int,
    previous_findings: int,
    findings_change: int,
    findings_change_pct: float,
    cost_change: float,
    previous_month: str,
) -> str:
    """Generate a human-readable trend message.

    Args:
        Various trend metrics

    Returns:
        Human-readable message suitable for email notifications
    """
    if findings_change < 0:
        # Improvement
        return (
            f"Great progress! Findings decreased from {previous_findings} to {current_findings} "
            f"({abs(findings_change_pct):.0f}% reduction), "
            f"saving an estimated ${abs(cost_change):,.2f}/month compared to {previous_month}."
        )
    elif findings_change > 0:
        # Regression
        return (
            f"Attention needed: Findings increased from {previous_findings} to {current_findings} "
            f"({findings_change_pct:.0f}% increase), "
            f"adding ${cost_change:,.2f}/month in potential waste since {previous_month}."
        )
    else:
        # No change
        return (
            f"Findings stable at {current_findings} "
            f"(${abs(cost_change):,.2f}/month potential savings identified)."
        )
