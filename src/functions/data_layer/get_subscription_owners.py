"""Get subscription owners function.

Retrieves owner contact information for subscriptions from the
subscription-owners container in Cosmos DB.
"""

from __future__ import annotations

import logging
from typing import Any

from shared import CosmosClient

logger = logging.getLogger(__name__)


def get_subscription_owners(
    subscription_ids: list[str],
) -> dict[str, Any]:
    """Get owner information for subscriptions.

    Args:
        subscription_ids: List of Azure subscription IDs to look up.

    Returns:
        Dictionary with:
            - owners: List of subscription owner records
            - found: Number of owners found
            - notFound: List of subscription IDs with no owner mapping
    """
    logger.info(f"Getting owners for {len(subscription_ids)} subscriptions")

    client = CosmosClient()
    owners = client.get_subscription_owners(subscription_ids)

    # Identify subscriptions without owner mappings
    found_ids = {o.get("subscriptionId") for o in owners}
    not_found = [sid for sid in subscription_ids if sid not in found_ids]

    if not_found:
        logger.warning(f"No owner mapping found for {len(not_found)} subscriptions")

    logger.info(f"Found owners for {len(owners)} subscriptions")

    return {
        "owners": owners,
        "found": len(owners),
        "notFound": not_found,
    }
