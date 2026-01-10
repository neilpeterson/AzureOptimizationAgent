"""Generic confidence scoring utilities for optimization modules.

This module provides base utilities for confidence scoring. Module-specific
confidence logic (e.g., abandoned resources, overprovisioned VMs) should
be implemented within each detection module.
"""

from __future__ import annotations

from shared.models import ConfidenceLevel


def get_confidence_level(score: int) -> ConfidenceLevel:
    """Convert a numeric confidence score to a confidence level.

    Args:
        score: Confidence score from 0-100.

    Returns:
        Corresponding ConfidenceLevel enum value.

    Thresholds:
        - Certain: 95-100
        - High: 75-94
        - Medium: 50-74
        - Low: 25-49
        - Uncertain: 0-24
    """
    if score >= 95:
        return ConfidenceLevel.CERTAIN
    elif score >= 75:
        return ConfidenceLevel.HIGH
    elif score >= 50:
        return ConfidenceLevel.MEDIUM
    elif score >= 25:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.UNCERTAIN


def clamp_score(score: int, minimum: int = 0, maximum: int = 100) -> int:
    """Clamp a confidence score to valid range.

    Args:
        score: Raw confidence score.
        minimum: Minimum allowed value (default 0).
        maximum: Maximum allowed value (default 100).

    Returns:
        Score clamped to [minimum, maximum] range.
    """
    return max(minimum, min(maximum, score))


def should_report_finding(confidence_score: int, minimum_threshold: int = 25) -> bool:
    """Determine if a finding should be reported based on confidence.

    Args:
        confidence_score: The calculated confidence score.
        minimum_threshold: Minimum score required to report (default 25).

    Returns:
        True if finding should be included in report.
    """
    return confidence_score >= minimum_threshold


def get_confidence_thresholds() -> dict[str, int]:
    """Get the standard confidence level thresholds.

    Returns:
        Dictionary mapping level names to minimum scores.
    """
    return {
        "certain": 95,
        "high": 75,
        "medium": 50,
        "low": 25,
        "uncertain": 0,
    }
