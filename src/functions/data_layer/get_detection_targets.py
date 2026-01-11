"""Get detection targets function.

Retrieves enabled (and optionally disabled) detection targets from the
detection-targets container in Cosmos DB. Targets can be subscriptions
or management groups.
"""

from __future__ import annotations

import logging
from typing import Any

from shared import CosmosClient

logger = logging.getLogger(__name__)


def get_detection_targets(
    include_disabled: bool = False,
    target_type: str | None = None,
) -> dict[str, Any]:
    """Get detection targets from the database.

    Args:
        include_disabled: If True, include disabled targets in the response.
        target_type: Optional filter by target type ('subscription' or 'managementGroup').

    Returns:
        Dictionary with:
            - targets: List of detection target entries
            - count: Number of targets returned
            - subscriptionCount: Number of subscription targets
            - managementGroupCount: Number of management group targets
    """
    logger.info(
        f"Getting detection targets (include_disabled={include_disabled}, target_type={target_type})"
    )

    client = CosmosClient()

    if target_type:
        # Filter by specific target type (always enabled only)
        targets = client.get_targets_by_type(target_type)
    elif include_disabled:
        # Get all targets including disabled
        targets = client.get_all_targets()
    else:
        # Get only enabled targets
        targets = client.get_enabled_targets()

    # Count by type
    subscription_count = sum(1 for t in targets if t.get("targetType") == "subscription")
    management_group_count = sum(1 for t in targets if t.get("targetType") == "managementGroup")

    logger.info(
        f"Found {len(targets)} targets "
        f"({subscription_count} subscriptions, {management_group_count} management groups)"
    )

    return {
        "targets": targets,
        "count": len(targets),
        "subscriptionCount": subscription_count,
        "managementGroupCount": management_group_count,
    }
