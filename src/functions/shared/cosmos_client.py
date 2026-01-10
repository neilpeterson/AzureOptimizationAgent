"""Cosmos DB client wrapper with managed identity authentication."""

from __future__ import annotations

import os
from typing import Any

from azure.cosmos import CosmosClient as AzureCosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import DefaultAzureCredential


class CosmosClient:
    """Wrapper for Azure Cosmos DB operations using managed identity."""

    # Container names
    MODULE_REGISTRY = "module-registry"
    FINDINGS_HISTORY = "findings-history"
    SUBSCRIPTION_OWNERS = "subscription-owners"
    EXECUTION_LOGS = "execution-logs"

    def __init__(
        self,
        endpoint: str | None = None,
        database_name: str | None = None,
        credential: Any | None = None,
    ):
        """Initialize Cosmos DB client.

        Args:
            endpoint: Cosmos DB endpoint URL. Defaults to COSMOS_ENDPOINT env var.
            database_name: Database name. Defaults to COSMOS_DATABASE env var.
            credential: Azure credential. Defaults to DefaultAzureCredential.
        """
        self.endpoint = endpoint or os.environ.get("COSMOS_ENDPOINT")
        self.database_name = database_name or os.environ.get("COSMOS_DATABASE", "optimization-agent")

        if not self.endpoint:
            raise ValueError("COSMOS_ENDPOINT environment variable or endpoint parameter required")

        self.credential = credential or DefaultAzureCredential()
        self._client = AzureCosmosClient(self.endpoint, credential=self.credential)
        self._database = self._client.get_database_client(self.database_name)

    def _get_container(self, container_name: str):
        """Get a container client."""
        return self._database.get_container_client(container_name)

    # Module Registry operations
    def get_enabled_modules(self) -> list[dict[str, Any]]:
        """Get all enabled modules from the registry."""
        container = self._get_container(self.MODULE_REGISTRY)
        query = "SELECT * FROM c WHERE c.enabled = true AND c.status = 'active'"
        return list(container.query_items(query, enable_cross_partition_query=True))

    def get_all_modules(self) -> list[dict[str, Any]]:
        """Get all modules from the registry (including disabled)."""
        container = self._get_container(self.MODULE_REGISTRY)
        query = "SELECT * FROM c"
        return list(container.query_items(query, enable_cross_partition_query=True))

    def get_module(self, module_id: str) -> dict[str, Any] | None:
        """Get a specific module by ID."""
        container = self._get_container(self.MODULE_REGISTRY)
        try:
            return container.read_item(item=module_id, partition_key=module_id)
        except CosmosResourceNotFoundError:
            return None

    def update_module_execution(self, module_id: str, execution_date: str) -> None:
        """Update the last execution date for a module."""
        container = self._get_container(self.MODULE_REGISTRY)
        module = container.read_item(item=module_id, partition_key=module_id)
        module["lastExecutionDate"] = execution_date
        container.replace_item(item=module_id, body=module)

    # Findings History operations
    def save_findings(self, findings: list[dict[str, Any]]) -> int:
        """Save findings to history. Returns count of saved items."""
        container = self._get_container(self.FINDINGS_HISTORY)
        saved = 0
        for finding in findings:
            container.upsert_item(finding)
            saved += 1
        return saved

    def get_findings_by_subscription(
        self, subscription_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get recent findings for a subscription."""
        container = self._get_container(self.FINDINGS_HISTORY)
        query = """
            SELECT * FROM c
            WHERE c.subscriptionId = @subscriptionId
            ORDER BY c.executionDate DESC
            OFFSET 0 LIMIT @limit
        """
        parameters = [
            {"name": "@subscriptionId", "value": subscription_id},
            {"name": "@limit", "value": limit},
        ]
        return list(
            container.query_items(
                query, parameters=parameters, partition_key=subscription_id
            )
        )

    def get_findings_by_subscription_and_status(
        self, subscription_id: str, status: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get findings for a subscription filtered by status."""
        container = self._get_container(self.FINDINGS_HISTORY)
        query = """
            SELECT * FROM c
            WHERE c.subscriptionId = @subscriptionId AND c.status = @status
            ORDER BY c.executionDate DESC
            OFFSET 0 LIMIT @limit
        """
        parameters = [
            {"name": "@subscriptionId", "value": subscription_id},
            {"name": "@status", "value": status},
            {"name": "@limit", "value": limit},
        ]
        return list(
            container.query_items(
                query, parameters=parameters, partition_key=subscription_id
            )
        )

    def get_findings_by_execution(self, execution_id: str) -> list[dict[str, Any]]:
        """Get all findings for a specific execution."""
        container = self._get_container(self.FINDINGS_HISTORY)
        query = "SELECT * FROM c WHERE c.executionId = @executionId"
        parameters = [{"name": "@executionId", "value": execution_id}]
        return list(
            container.query_items(query, parameters=parameters, enable_cross_partition_query=True)
        )

    def get_open_findings_by_resource(self, resource_id: str) -> dict[str, Any] | None:
        """Get the most recent open finding for a resource."""
        container = self._get_container(self.FINDINGS_HISTORY)
        query = """
            SELECT TOP 1 * FROM c
            WHERE c.resourceId = @resourceId AND c.status = 'open'
            ORDER BY c.executionDate DESC
        """
        parameters = [{"name": "@resourceId", "value": resource_id}]
        results = list(
            container.query_items(query, parameters=parameters, enable_cross_partition_query=True)
        )
        return results[0] if results else None

    # Subscription Owners operations
    def get_subscription_owner(self, subscription_id: str) -> dict[str, Any] | None:
        """Get owner info for a subscription."""
        container = self._get_container(self.SUBSCRIPTION_OWNERS)
        try:
            return container.read_item(item=subscription_id, partition_key=subscription_id)
        except CosmosResourceNotFoundError:
            return None

    def get_subscription_owners(self, subscription_ids: list[str]) -> list[dict[str, Any]]:
        """Get owners for multiple subscriptions."""
        container = self._get_container(self.SUBSCRIPTION_OWNERS)
        # Use IN clause for batch lookup
        placeholders = ", ".join([f"@sub{i}" for i in range(len(subscription_ids))])
        query = f"SELECT * FROM c WHERE c.subscriptionId IN ({placeholders})"
        parameters = [
            {"name": f"@sub{i}", "value": sub_id}
            for i, sub_id in enumerate(subscription_ids)
        ]
        return list(
            container.query_items(query, parameters=parameters, enable_cross_partition_query=True)
        )

    def upsert_subscription_owner(self, owner: dict[str, Any]) -> None:
        """Create or update a subscription owner mapping."""
        container = self._get_container(self.SUBSCRIPTION_OWNERS)
        container.upsert_item(owner)

    # Execution Logs operations
    def create_execution_log(self, log: dict[str, Any]) -> None:
        """Create a new execution log entry."""
        container = self._get_container(self.EXECUTION_LOGS)
        container.create_item(log)

    def update_execution_log(self, execution_id: str, updates: dict[str, Any]) -> None:
        """Update an execution log entry."""
        container = self._get_container(self.EXECUTION_LOGS)
        log = container.read_item(item=execution_id, partition_key=execution_id)
        log.update(updates)
        container.replace_item(item=execution_id, body=log)

    def get_execution_log(self, execution_id: str) -> dict[str, Any] | None:
        """Get an execution log by ID."""
        container = self._get_container(self.EXECUTION_LOGS)
        try:
            return container.read_item(item=execution_id, partition_key=execution_id)
        except CosmosResourceNotFoundError:
            return None

    def get_recent_executions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent execution logs."""
        container = self._get_container(self.EXECUTION_LOGS)
        query = """
            SELECT * FROM c
            ORDER BY c.startTime DESC
            OFFSET 0 LIMIT @limit
        """
        parameters = [{"name": "@limit", "value": limit}]
        return list(
            container.query_items(query, parameters=parameters, enable_cross_partition_query=True)
        )

    # Trends operations
    def get_findings_for_trends(
        self,
        module_id: str,
        from_date: str,
        to_date: str,
        subscription_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get findings for trend analysis within a date range.

        Args:
            module_id: Module ID to filter by (e.g., 'abandoned-resources')
            from_date: Start date (ISO format, e.g., '2025-12-01')
            to_date: End date (ISO format, e.g., '2026-01-31')
            subscription_id: Optional subscription ID to filter by

        Returns:
            List of findings with executionDate, estimatedMonthlyCost, severity, resourceType
        """
        container = self._get_container(self.FINDINGS_HISTORY)

        if subscription_id:
            query = """
                SELECT c.executionDate, c.estimatedMonthlyCost, c.severity,
                       c.resourceType, c.subscriptionId, c.findingId
                FROM c
                WHERE c.moduleId = @moduleId
                  AND c.subscriptionId = @subscriptionId
                  AND c.executionDate >= @fromDate
                  AND c.executionDate <= @toDate
            """
            parameters = [
                {"name": "@moduleId", "value": module_id},
                {"name": "@subscriptionId", "value": subscription_id},
                {"name": "@fromDate", "value": from_date},
                {"name": "@toDate", "value": to_date},
            ]
            return list(
                container.query_items(query, parameters=parameters, partition_key=subscription_id)
            )
        else:
            query = """
                SELECT c.executionDate, c.estimatedMonthlyCost, c.severity,
                       c.resourceType, c.subscriptionId, c.findingId
                FROM c
                WHERE c.moduleId = @moduleId
                  AND c.executionDate >= @fromDate
                  AND c.executionDate <= @toDate
            """
            parameters = [
                {"name": "@moduleId", "value": module_id},
                {"name": "@fromDate", "value": from_date},
                {"name": "@toDate", "value": to_date},
            ]
            return list(
                container.query_items(query, parameters=parameters, enable_cross_partition_query=True)
            )
