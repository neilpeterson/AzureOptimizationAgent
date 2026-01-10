"""Azure Resource Graph client wrapper.

This module provides a generic client for executing Azure Resource Graph
queries. Module-specific queries (e.g., abandoned resource KQL, VM metrics)
should be implemented within each detection module.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.mgmt.resourcegraph import ResourceGraphClient as AzureResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions

logger = logging.getLogger(__name__)


class ResourceGraphClient:
    """Wrapper for Azure Resource Graph queries across subscriptions."""

    # Maximum subscriptions per query (Azure limit is 1000)
    MAX_SUBSCRIPTIONS_PER_QUERY = 1000

    # Maximum results per page
    DEFAULT_PAGE_SIZE = 1000

    def __init__(self, credential: Any | None = None):
        """Initialize Resource Graph client.

        Args:
            credential: Azure credential. Defaults to DefaultAzureCredential.
        """
        self.credential = credential or DefaultAzureCredential()
        self._client = AzureResourceGraphClient(self.credential)

    def query(
        self,
        query: str,
        subscription_ids: list[str] | None = None,
        management_group_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Resource Graph query.

        Args:
            query: KQL query string.
            subscription_ids: List of subscription IDs to query. If None and
                management_group_id is None, queries all accessible subscriptions.
            management_group_id: Management group ID for cross-subscription queries.

        Returns:
            List of query results as dictionaries.
        """
        all_results = []
        skip_token = None

        while True:
            options = QueryRequestOptions(
                result_format="objectArray",
                skip_token=skip_token,
            )

            request = QueryRequest(
                query=query,
                subscriptions=subscription_ids,
                management_groups=[management_group_id] if management_group_id else None,
                options=options,
            )

            response = self._client.resources(request)
            all_results.extend(response.data)

            # Check for more pages
            skip_token = response.skip_token
            if not skip_token:
                break

            logger.debug(f"Fetching next page, current count: {len(all_results)}")

        return all_results

    def query_batched(
        self,
        query: str,
        subscription_ids: list[str],
    ) -> list[dict[str, Any]]:
        """Execute a query across many subscriptions in batches.

        Use this when querying more subscriptions than the per-query limit.

        Args:
            query: KQL query string.
            subscription_ids: List of subscription IDs to query.

        Returns:
            Combined results from all batches.
        """
        all_results = []

        # Split into batches
        for i in range(0, len(subscription_ids), self.MAX_SUBSCRIPTIONS_PER_QUERY):
            batch = subscription_ids[i : i + self.MAX_SUBSCRIPTIONS_PER_QUERY]
            logger.debug(f"Querying batch {i // self.MAX_SUBSCRIPTIONS_PER_QUERY + 1}")
            results = self.query(query, subscription_ids=batch)
            all_results.extend(results)

        return all_results

    def query_single(
        self,
        query: str,
        subscription_id: str,
    ) -> list[dict[str, Any]]:
        """Execute a query against a single subscription.

        Args:
            query: KQL query string.
            subscription_id: Single subscription ID to query.

        Returns:
            Query results as list of dictionaries.
        """
        return self.query(query, subscription_ids=[subscription_id])
