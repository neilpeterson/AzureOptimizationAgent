"""Confidence scoring logic specific to abandoned resources detection.

This module contains the abandoned-resources-specific logic for calculating
confidence scores. It uses the generic utilities from shared.confidence
and applies domain-specific rules for orphaned/abandoned resources.
"""

import re
from datetime import datetime, timezone

from shared.confidence import clamp_score, get_confidence_level
from shared.models import ConfidenceLevel


# Patterns that suggest temporary or test resources (increases confidence)
TEMPORARY_NAME_PATTERNS = [
    r"^test[-_]",
    r"[-_]test$",
    r"^temp[-_]",
    r"[-_]temp$",
    r"^tmp[-_]",
    r"[-_]tmp$",
    r"^delete[-_]",
    r"[-_]delete$",
    r"^remove[-_]",
    r"[-_]remove$",
    r"^old[-_]",
    r"[-_]old$",
    r"^deprecated[-_]",
    r"[-_]deprecated$",
    r"^backup[-_]",
    r"^bak[-_]",
    r"[-_]bak$",
    r"^copy[-_]",
    r"[-_]copy\d*$",
]

# Patterns that suggest intentional retention (decreases confidence)
RETENTION_NAME_PATTERNS = [
    r"[-_]dr$",
    r"^dr[-_]",
    r"[-_]prod",
    r"^prod[-_]",
    r"[-_]production",
    r"[-_]reserved",
    r"[-_]keep",
    r"[-_]retain",
]

# Tags that suggest intentional retention (decreases confidence)
RETENTION_TAGS = [
    "Environment:Production",
    "Environment:Prod",
    "DoNotDelete",
    "do-not-delete",
    "Retain",
    "retain",
    "Keep",
    "keep",
    "Reserved",
    "reserved",
]


def _parse_datetime(dt: datetime | str | None) -> datetime | None:
    """Parse a datetime from string or return as-is."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except ValueError:
        return None


def _calculate_duration_score(reference_date: datetime | None) -> int:
    """Calculate score adjustment based on orphan duration.

    Args:
        reference_date: When the resource became orphaned.

    Returns:
        Score adjustment (-20 to +30).
    """
    if not reference_date:
        return 0

    now = datetime.now(timezone.utc)
    if reference_date.tzinfo is None:
        reference_date = reference_date.replace(tzinfo=timezone.utc)

    days_orphaned = (now - reference_date).days

    if days_orphaned >= 90:
        return 30  # Very high confidence
    elif days_orphaned >= 30:
        return 20  # High confidence
    elif days_orphaned >= 14:
        return 10  # Moderate confidence
    elif days_orphaned >= 7:
        return 5  # Some confidence
    elif days_orphaned < 3:
        return -20  # Recently orphaned, low confidence

    return 0


def _calculate_name_pattern_score(resource_name: str) -> int:
    """Calculate score adjustment based on resource name patterns.

    Args:
        resource_name: Name of the resource.

    Returns:
        Score adjustment (-15 to +15).
    """
    name_lower = resource_name.lower()

    # Check for temporary patterns (increases confidence)
    for pattern in TEMPORARY_NAME_PATTERNS:
        if re.search(pattern, name_lower):
            return 15

    # Check for retention patterns (decreases confidence)
    for pattern in RETENTION_NAME_PATTERNS:
        if re.search(pattern, name_lower):
            return -15

    return 0


def _calculate_tag_score(tags: dict[str, str] | None) -> int:
    """Calculate score adjustment based on resource tags.

    Args:
        tags: Resource tags as key:value pairs.

    Returns:
        Score adjustment (-20 to 0).
    """
    if not tags:
        return 0

    for tag_key, tag_value in tags.items():
        tag_combined = f"{tag_key}:{tag_value}"

        # Check retention tags
        for retention_tag in RETENTION_TAGS:
            if retention_tag.lower() in tag_combined.lower():
                return -20

        # Environment production tag reduces confidence significantly
        if tag_key.lower() == "environment" and tag_value.lower() in ["prod", "production"]:
            return -20

    return 0


def _calculate_resource_group_score(resource_group_name: str | None) -> int:
    """Calculate score adjustment based on resource group name.

    Args:
        resource_group_name: Name of the resource group.

    Returns:
        Score adjustment (-10 to +10).
    """
    if not resource_group_name:
        return 0

    rg_lower = resource_group_name.lower()

    # Temporary RG patterns (increases confidence)
    if any(
        pattern in rg_lower
        for pattern in ["test", "temp", "tmp", "delete", "sandbox", "dev"]
    ):
        return 10

    # Production RG patterns (decreases confidence)
    if any(pattern in rg_lower for pattern in ["prod", "production", "prd"]):
        return -10

    return 0


def calculate_abandoned_confidence(
    resource_name: str,
    created_date: datetime | str | None = None,
    orphaned_date: datetime | str | None = None,
    tags: dict[str, str] | None = None,
    resource_group_name: str | None = None,
    base_score: int = 50,
) -> int:
    """Calculate confidence score for an abandoned resource finding.

    Confidence indicates how certain we are that a resource is truly abandoned
    and safe to delete.

    Args:
        resource_name: Name of the resource.
        created_date: When the resource was created.
        orphaned_date: When the resource became orphaned (e.g., disk unattached).
            If None, uses created_date as reference.
        tags: Resource tags as key:value pairs.
        resource_group_name: Name of the resource group.
        base_score: Starting score (default 50).

    Returns:
        Confidence score from 0-100.

    Scoring factors:
        - Duration in orphaned state: -20 to +30 points
        - Name patterns (temp, test, prod, dr): -15 to +15 points
        - Tags (DoNotDelete, Environment:Production): -20 to 0 points
        - Resource group patterns: -10 to +10 points
    """
    score = base_score

    # Parse dates
    created_dt = _parse_datetime(created_date)
    orphaned_dt = _parse_datetime(orphaned_date)

    # Use orphaned_date if available, otherwise fall back to created_date
    reference_date = orphaned_dt or created_dt

    # Apply scoring factors
    score += _calculate_duration_score(reference_date)
    score += _calculate_name_pattern_score(resource_name)
    score += _calculate_tag_score(tags)
    score += _calculate_resource_group_score(resource_group_name)

    return clamp_score(score)


def get_recommendation_action(confidence_level: ConfidenceLevel) -> str:
    """Get the recommended action for abandoned resources based on confidence.

    Args:
        confidence_level: The confidence level for the finding.

    Returns:
        Recommended action string.
    """
    actions = {
        ConfidenceLevel.CERTAIN: "Recommend immediate deletion",
        ConfidenceLevel.HIGH: "Recommend deletion after verification",
        ConfidenceLevel.MEDIUM: "Flag for review",
        ConfidenceLevel.LOW: "Informational only",
        ConfidenceLevel.UNCERTAIN: "Requires investigation",
    }
    return actions.get(confidence_level, "Unknown")
