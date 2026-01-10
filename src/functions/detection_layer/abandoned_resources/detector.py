"""Main detection logic for abandoned resources module.

This module implements the module interface contract for detecting
orphaned Azure resources that incur cost but provide no value.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from shared import (
    Finding,
    FindingCategory,
    ModuleInput,
    ModuleOutput,
    ModuleSummary,
    ResourceGraphClient,
    classify_severity,
    get_confidence_level,
    should_report_finding,
)
from detection_layer.abandoned_resources.config import AbandonedResourcesConfig, parse_config
from detection_layer.abandoned_resources.confidence import (
    calculate_abandoned_confidence,
    get_recommendation_action,
)
from detection_layer.abandoned_resources.cost_calculator import estimate_abandoned_resource_cost
from detection_layer.abandoned_resources.queries import get_query_for_resource_type

logger = logging.getLogger(__name__)

MODULE_ID = "abandoned-resources"
MODULE_NAME = "Abandoned Resources"
MODULE_VERSION = "1.0.0"


def _generate_finding_id(resource_id: str, execution_id: str) -> str:
    """Generate a deterministic finding ID.

    Args:
        resource_id: Azure resource ID.
        execution_id: Current execution ID.

    Returns:
        Unique finding ID.
    """
    hash_input = f"{resource_id}:{execution_id}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def _extract_resource_name(resource_id: str) -> str:
    """Extract resource name from Azure resource ID.

    Args:
        resource_id: Full Azure resource ID.

    Returns:
        Resource name (last segment of the ID).
    """
    return resource_id.split("/")[-1] if resource_id else "unknown"


def _get_detection_rule(resource_type: str) -> str:
    """Get the detection rule description for a resource type.

    Args:
        resource_type: Azure resource type.

    Returns:
        Human-readable detection rule.
    """
    rules = {
        "microsoft.compute/disks": "Managed disk not attached to any VM",
        "microsoft.network/publicipaddresses": "Standard public IP without IP configuration",
        "microsoft.network/loadbalancers": "Load balancer with no backend pool members",
        "microsoft.network/natgateways": "NAT gateway not associated with any subnet",
        "microsoft.sql/servers/elasticpools": "SQL elastic pool with no databases",
        "microsoft.network/virtualnetworkgateways": "VNet gateway with no active connections",
        "microsoft.network/ddosprotectionplans": "DDoS plan not protecting any VNets",
        "microsoft.network/privateendpoints": "Private endpoint with no service connections",
    }
    return rules.get(resource_type.lower(), "Resource detected as potentially abandoned")


def _create_finding_from_resource(
    resource: dict[str, Any],
    resource_type: str,
    execution_id: str,
    config: AbandonedResourcesConfig,
) -> Finding | None:
    """Create a Finding from a Resource Graph query result.

    Args:
        resource: Resource data from query.
        resource_type: Azure resource type.
        execution_id: Current execution ID.
        config: Module configuration.

    Returns:
        Finding object, or None if finding should be skipped.
    """
    resource_id = resource.get("id", "")
    resource_name = resource.get("name", _extract_resource_name(resource_id))
    subscription_id = resource.get("subscriptionId", "")
    resource_group = resource.get("resourceGroup", "")
    location = resource.get("location", "")
    tags = resource.get("tags", {}) or {}

    # Extract SKU and size info for cost calculation
    sku = resource.get("sku")
    disk_size_gb = resource.get("diskSizeGB")

    # Build metadata from query-specific fields
    metadata: dict[str, Any] = {}
    for key, value in resource.items():
        if key not in ("id", "subscriptionId", "resourceGroup", "name", "location", "tags"):
            metadata[key] = value

    # Calculate confidence score
    created_date = resource.get("timeCreated")
    confidence_score = calculate_abandoned_confidence(
        resource_name=resource_name,
        created_date=created_date,
        tags=tags,
        resource_group_name=resource_group,
    )

    # Skip low confidence findings if configured
    if not should_report_finding(confidence_score, minimum_threshold=25):
        logger.debug(f"Skipping low confidence finding: {resource_id} (score={confidence_score})")
        return None

    confidence_level = get_confidence_level(confidence_score)

    # Calculate cost estimate
    estimated_cost = estimate_abandoned_resource_cost(
        resource_type=resource_type,
        sku=sku,
        size_gb=disk_size_gb,
        metadata=metadata,
    )

    # Skip zero-cost resources if not configured to include them
    if estimated_cost == 0 and not config.include_zero_cost:
        logger.debug(f"Skipping zero-cost resource: {resource_id}")
        return None

    # Classify severity based on cost
    severity = classify_severity(estimated_cost)

    # Generate description
    recommendation = get_recommendation_action(confidence_level)
    description = (
        f"Abandoned {resource_type.split('/')[-1]} detected. "
        f"Estimated monthly cost: ${estimated_cost:.2f}. "
        f"{recommendation}."
    )

    return Finding(
        findingId=_generate_finding_id(resource_id, execution_id),
        subscriptionId=subscription_id,
        resourceId=resource_id,
        resourceType=resource_type,
        resourceName=resource_name,
        resourceGroup=resource_group,
        location=location,
        category=FindingCategory.ABANDONED,
        severity=severity,
        confidenceScore=confidence_score,
        confidenceLevel=confidence_level,
        incursCost=estimated_cost > 0,
        estimatedMonthlyCost=estimated_cost,
        description=description,
        detectionRule=_get_detection_rule(resource_type),
        firstDetectedDate=datetime.now(timezone.utc),
        metadata=metadata,
    )


def _create_summary(findings: list[Finding], subscriptions_scanned: int) -> ModuleSummary:
    """Create summary statistics from findings.

    Args:
        findings: List of findings.
        subscriptions_scanned: Number of subscriptions scanned.

    Returns:
        ModuleSummary object.
    """
    total_cost = sum(f.estimated_monthly_cost for f in findings)

    # Count by severity
    by_severity: dict[str, int] = {}
    for f in findings:
        severity = f.severity.value if hasattr(f.severity, "value") else f.severity
        by_severity[severity] = by_severity.get(severity, 0) + 1

    # Count by resource type
    by_resource_type: dict[str, int] = {}
    for f in findings:
        by_resource_type[f.resource_type] = by_resource_type.get(f.resource_type, 0) + 1

    # Count unique subscriptions with findings
    subscriptions_with_findings = len(set(f.subscription_id for f in findings))

    return ModuleSummary(
        totalFindings=len(findings),
        totalEstimatedMonthlySavings=total_cost,
        findingsBySeverity=by_severity,
        findingsByResourceType=by_resource_type,
        subscriptionsWithFindings=subscriptions_with_findings,
        subscriptionsClean=subscriptions_scanned - subscriptions_with_findings,
    )


def detect(module_input: ModuleInput) -> ModuleOutput:
    """Execute abandoned resources detection.

    This is the main entry point implementing the module interface contract.

    Args:
        module_input: Module input containing execution_id, subscription_ids,
            configuration, and dry_run flag.

    Returns:
        ModuleOutput with findings and summary.
    """
    execution_id = module_input.execution_id
    subscription_ids = module_input.subscription_ids
    dry_run = module_input.dry_run

    logger.info(
        f"Starting abandoned resources detection: execution_id={execution_id}, "
        f"subscriptions={len(subscription_ids)}, dry_run={dry_run}"
    )

    # Parse configuration
    config = parse_config(module_input.configuration)
    logger.info(f"Configuration: resource_types={config.resource_types}")

    # Initialize clients
    graph_client = ResourceGraphClient()

    all_findings: list[Finding] = []
    errors: list[str] = []

    # Process each resource type
    for resource_type in config.resource_types:
        try:
            logger.info(f"Scanning for {resource_type}")

            # Get query for this resource type
            query = get_query_for_resource_type(resource_type)
            if not query:
                logger.warning(f"No query defined for resource type: {resource_type}")
                continue

            # Execute query
            if dry_run:
                logger.info(f"[DRY RUN] Would execute query for {resource_type}")
                results = []
            else:
                results = graph_client.query_batched(query, subscription_ids)

            logger.info(f"Found {len(results)} {resource_type} resources")

            # Create findings from results
            for resource in results:
                try:
                    finding = _create_finding_from_resource(
                        resource=resource,
                        resource_type=resource_type,
                        execution_id=execution_id,
                        config=config,
                    )
                    if finding:
                        all_findings.append(finding)
                except Exception as e:
                    resource_id = resource.get("id", "unknown")
                    error_msg = f"Error processing resource {resource_id}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

        except Exception as e:
            error_msg = f"Error scanning {resource_type}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Create summary
    summary = _create_summary(all_findings, len(subscription_ids))

    # Determine status
    status = "success" if not errors else "partial_success" if all_findings else "failed"

    logger.info(
        f"Detection complete: {len(all_findings)} findings, "
        f"${summary.total_estimated_monthly_savings:.2f} estimated savings, "
        f"{len(errors)} errors"
    )

    return ModuleOutput(
        moduleId=MODULE_ID,
        moduleName=MODULE_NAME,
        version=MODULE_VERSION,
        executionId=execution_id,
        executionTime=datetime.now(timezone.utc),
        status=status,
        subscriptionsScanned=len(subscription_ids),
        findings=all_findings,
        summary=summary,
        errors=errors,
    )


def detect_from_dict(input_dict: dict[str, Any]) -> dict[str, Any]:
    """Execute detection from dictionary input, returning dictionary output.

    Convenience function for Azure Functions HTTP trigger integration.

    Args:
        input_dict: Dictionary with executionId, subscriptionIds, configuration, dryRun.

    Returns:
        Dictionary representation of ModuleOutput.
    """
    module_input = ModuleInput(**input_dict)
    output = detect(module_input)
    return output.model_dump(by_alias=True)
