"""Cost estimation logic specific to abandoned resources detection.

This module contains pricing data and cost estimation for orphaned Azure
resources. It uses the generic severity classification from shared.cost_calculator
and applies resource-type-specific pricing.
"""

from __future__ import annotations

from typing import Any


# Monthly cost estimates by resource type and SKU (USD)
# These are approximate costs for East US region as of 2026
ABANDONED_RESOURCE_COSTS = {
    # Managed Disks - per GB per month
    "microsoft.compute/disks": {
        "Standard_LRS": 0.05,  # ~$0.05/GB/month
        "StandardSSD_LRS": 0.075,  # ~$0.075/GB/month
        "Premium_LRS": 0.15,  # ~$0.15/GB/month (P10-P80 varies)
        "UltraSSD_LRS": 0.20,  # ~$0.20/GB/month base
        "default": 0.10,
    },
    # Public IP Addresses - flat monthly rate
    "microsoft.network/publicipaddresses": {
        "Standard": 3.65,  # ~$3.65/month for Standard SKU
        "Basic": 0.0,  # Basic is free when not associated
        "default": 3.65,
    },
    # Load Balancers - base monthly rate (excludes data processing)
    "microsoft.network/loadbalancers": {
        "Standard": 18.25,  # ~$18.25/month base
        "Basic": 0.0,  # Basic LB is free
        "Gateway": 18.25,
        "default": 18.25,
    },
    # NAT Gateways - base monthly rate (excludes data processing)
    "microsoft.network/natgateways": {
        "default": 32.85,  # ~$32.85/month + data
    },
    # SQL Elastic Pools - varies significantly by tier
    "microsoft.sql/servers/elasticpools": {
        "Basic": 15.00,  # ~$15/month for 50 eDTU
        "Standard": 75.00,  # ~$75/month for 50 eDTU
        "Premium": 465.00,  # ~$465/month for 125 eDTU
        "GeneralPurpose": 200.00,  # Approximate vCore pricing
        "BusinessCritical": 500.00,
        "default": 100.00,
    },
    # VNet Gateways - varies significantly by SKU
    "microsoft.network/virtualnetworkgateways": {
        "VpnGw1": 140.16,  # ~$140/month
        "VpnGw2": 361.35,  # ~$361/month
        "VpnGw3": 722.70,  # ~$723/month
        "VpnGw4": 1252.80,  # ~$1253/month
        "VpnGw5": 2505.60,  # ~$2506/month
        "Basic": 27.01,  # ~$27/month (deprecated)
        "ErGw1Az": 209.39,  # ExpressRoute Gateway
        "ErGw2Az": 523.61,
        "ErGw3Az": 1396.40,
        "default": 140.16,
    },
    # DDoS Protection Plans - flat monthly rate
    "microsoft.network/ddosprotectionplans": {
        "default": 2944.00,  # ~$2,944/month flat
    },
    # Private Endpoints - hourly rate converted to monthly
    "microsoft.network/privateendpoints": {
        "default": 7.30,  # ~$0.01/hour = ~$7.30/month
    },
}


def estimate_abandoned_resource_cost(
    resource_type: str,
    sku: str | None = None,
    size_gb: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> float:
    """Estimate monthly cost for an abandoned resource.

    Args:
        resource_type: Azure resource type (lowercase).
        sku: SKU name (e.g., 'Premium_LRS', 'Standard').
        size_gb: Size in GB (for disk resources).
        metadata: Additional resource metadata.

    Returns:
        Estimated monthly cost in USD.
    """
    resource_type = resource_type.lower()
    metadata = metadata or {}

    # Get cost table for this resource type
    cost_table = ABANDONED_RESOURCE_COSTS.get(resource_type, {})
    if not cost_table:
        return 0.0

    # Get per-unit cost
    sku_key = sku or "default"
    unit_cost = cost_table.get(sku_key, cost_table.get("default", 0.0))

    # For disks, multiply by size
    if resource_type == "microsoft.compute/disks":
        disk_size = size_gb or metadata.get("diskSizeGB", 0)
        return unit_cost * disk_size

    # For elastic pools, check capacity
    if resource_type == "microsoft.sql/servers/elasticpools":
        capacity = metadata.get("capacity", 1)
        # Rough scaling based on capacity
        return unit_cost * (capacity / 50) if capacity else unit_cost

    return unit_cost


def get_supported_resource_types() -> list[str]:
    """Get list of resource types supported by this cost calculator.

    Returns:
        List of Azure resource type strings.
    """
    return list(ABANDONED_RESOURCE_COSTS.keys())


def get_cost_breakdown(resource_type: str) -> dict[str, float]:
    """Get the full cost breakdown for a resource type.

    Args:
        resource_type: Azure resource type (lowercase).

    Returns:
        Dictionary mapping SKU names to costs.
    """
    resource_type = resource_type.lower()
    return ABANDONED_RESOURCE_COSTS.get(resource_type, {}).copy()
