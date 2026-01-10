"""Get findings history function.

Retrieves historical findings for a subscription from the findings-history
container in Cosmos DB. Used for trend analysis and tracking resolved issues.
"""

from __future__ import annotations

import logging
from typing import Any

from shared import CosmosClient

logger = logging.getLogger(__name__)


def get_findings_history(
    subscription_id: str,
    limit: int = 100,
    status: str | None = None,
) -> dict[str, Any]:
    """Get findings history for a subscription.

    Args:
        subscription_id: Azure subscription ID to query.
        limit: Maximum number of findings to return (default 100).
        status: Optional filter by status ('open' or 'resolved').

    Returns:
        Dictionary with:
            - findings: List of historical finding records
            - count: Number of findings returned
            - subscriptionId: The queried subscription ID
    """
    logger.info(
        f"Getting findings history for subscription={subscription_id}, "
        f"limit={limit}, status={status}"
    )

    client = CosmosClient()

    if status:
        findings = client.get_findings_by_subscription_and_status(
            subscription_id=subscription_id,
            status=status,
            limit=limit,
        )
    else:
        findings = client.get_findings_by_subscription(
            subscription_id=subscription_id,
            limit=limit,
        )

    logger.info(f"Found {len(findings)} findings for subscription {subscription_id}")

    return {
        "findings": findings,
        "count": len(findings),
        "subscriptionId": subscription_id,
    }
