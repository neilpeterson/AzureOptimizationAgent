"""Save findings function.

Stores findings from a detection module execution into the findings-history
container in Cosmos DB.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from shared import CosmosClient

logger = logging.getLogger(__name__)


def save_findings(
    execution_id: str,
    module_id: str,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Save findings to the findings-history container.

    Args:
        execution_id: Unique identifier for this execution run.
        module_id: ID of the module that generated the findings.
        findings: List of finding dictionaries to save.

    Returns:
        Dictionary with:
            - saved: Number of findings saved
            - executionId: The execution ID
            - moduleId: The module ID
    """
    logger.info(
        f"Saving {len(findings)} findings for execution={execution_id}, module={module_id}"
    )

    if not findings:
        logger.info("No findings to save")
        return {
            "saved": 0,
            "executionId": execution_id,
            "moduleId": module_id,
        }

    client = CosmosClient()
    execution_date = datetime.now(timezone.utc)

    # Transform findings to history records
    history_records = []
    for finding in findings:
        record = {
            "id": str(uuid.uuid4()),
            "findingId": finding.get("findingId"),
            "executionId": execution_id,
            "executionDate": execution_date.isoformat(),
            "subscriptionId": finding.get("subscriptionId"),
            "moduleId": module_id,
            "resourceId": finding.get("resourceId"),
            "resourceType": finding.get("resourceType"),
            "resourceName": finding.get("resourceName"),
            "category": finding.get("category"),
            "severity": finding.get("severity"),
            "confidenceScore": finding.get("confidenceScore"),
            "confidenceLevel": finding.get("confidenceLevel"),
            "estimatedMonthlyCost": finding.get("estimatedMonthlyCost", 0.0),
            "description": finding.get("description"),
            "status": "open",
            "firstDetectedDate": finding.get("firstDetectedDate", execution_date.isoformat()),
            "ttl": 31536000,  # 365 days
        }
        history_records.append(record)

    # Save to Cosmos DB
    saved_count = client.save_findings(history_records)

    logger.info(f"Saved {saved_count} findings to history")

    return {
        "saved": saved_count,
        "executionId": execution_id,
        "moduleId": module_id,
    }
