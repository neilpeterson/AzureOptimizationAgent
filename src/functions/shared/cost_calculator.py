"""Generic cost calculation utilities for optimization modules.

This module provides base utilities for cost calculations and severity
classification. Module-specific cost estimation logic (e.g., abandoned
resource pricing, VM right-sizing savings) should be implemented within
each detection module.
"""

from typing import Any

from shared.models import Severity


def classify_severity(estimated_monthly_cost: float) -> Severity:
    """Classify severity based on monthly cost impact.

    Args:
        estimated_monthly_cost: Estimated monthly cost in USD.

    Returns:
        Severity level based on cost thresholds.

    Thresholds:
        - Critical: >$1,000/month
        - High: $100-$1,000/month
        - Medium: $10-$100/month
        - Low: $1-$10/month
        - Informational: <$1/month
    """
    if estimated_monthly_cost > 1000:
        return Severity.CRITICAL
    elif estimated_monthly_cost > 100:
        return Severity.HIGH
    elif estimated_monthly_cost > 10:
        return Severity.MEDIUM
    elif estimated_monthly_cost > 1:
        return Severity.LOW
    else:
        return Severity.INFORMATIONAL


def get_severity_thresholds() -> dict[str, float]:
    """Get the standard severity cost thresholds.

    Returns:
        Dictionary mapping severity levels to minimum cost thresholds.
    """
    return {
        "critical": 1000.0,
        "high": 100.0,
        "medium": 10.0,
        "low": 1.0,
        "informational": 0.0,
    }


def get_severity_priority(severity: Severity) -> int:
    """Get numeric priority for sorting by severity.

    Args:
        severity: Severity level.

    Returns:
        Priority number (lower = more severe).
    """
    priorities = {
        Severity.CRITICAL: 1,
        Severity.HIGH: 2,
        Severity.MEDIUM: 3,
        Severity.LOW: 4,
        Severity.INFORMATIONAL: 5,
    }
    return priorities.get(severity, 99)


def calculate_total_savings(findings: list[dict[str, Any]]) -> float:
    """Calculate total estimated monthly savings from findings.

    Args:
        findings: List of finding dictionaries with 'estimatedMonthlyCost' field.

    Returns:
        Total estimated monthly savings in USD.
    """
    return sum(f.get("estimatedMonthlyCost", 0.0) for f in findings)


def summarize_by_severity(findings: list[dict[str, Any]]) -> dict[str, int]:
    """Count findings by severity level.

    Args:
        findings: List of finding dictionaries with 'severity' field.

    Returns:
        Dictionary mapping severity to count.
    """
    counts: dict[str, int] = {}
    for finding in findings:
        severity = finding.get("severity", "informational")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def summarize_by_resource_type(findings: list[dict[str, Any]]) -> dict[str, int]:
    """Count findings by resource type.

    Args:
        findings: List of finding dictionaries with 'resourceType' field.

    Returns:
        Dictionary mapping resource type to count.
    """
    counts: dict[str, int] = {}
    for finding in findings:
        resource_type = finding.get("resourceType", "unknown")
        counts[resource_type] = counts.get(resource_type, 0) + 1
    return counts


def format_cost(amount: float, currency: str = "USD") -> str:
    """Format a cost amount for display.

    Args:
        amount: Cost amount.
        currency: Currency code (default USD).

    Returns:
        Formatted cost string.
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    return f"{amount:,.2f} {currency}"
