"""Abandoned Resources detection module.

Detects orphaned Azure resources that incur cost but provide no value.
"""

from detection_layer.abandoned_resources.config import (
    AbandonedResourcesConfig,
    parse_config,
)
from detection_layer.abandoned_resources.confidence import (
    calculate_abandoned_confidence,
    get_recommendation_action,
)
from detection_layer.abandoned_resources.cost_calculator import (
    estimate_abandoned_resource_cost,
    get_supported_resource_types as get_supported_cost_types,
    get_cost_breakdown,
)
from detection_layer.abandoned_resources.queries import (
    get_all_queries,
    get_query_for_resource_type,
    get_supported_resource_types as get_supported_query_types,
    query_unattached_disks,
    query_unused_public_ips,
    query_empty_load_balancers,
    query_orphaned_nat_gateways,
    query_empty_sql_elastic_pools,
    query_unused_vnet_gateways,
    query_orphaned_ddos_plans,
    query_disconnected_private_endpoints,
)
from detection_layer.abandoned_resources.detector import (
    detect,
    detect_from_dict,
    MODULE_ID,
    MODULE_NAME,
    MODULE_VERSION,
)

__all__ = [
    # Main detection entry points
    "detect",
    "detect_from_dict",
    "MODULE_ID",
    "MODULE_NAME",
    "MODULE_VERSION",
    # Configuration
    "AbandonedResourcesConfig",
    "parse_config",
    # Confidence scoring
    "calculate_abandoned_confidence",
    "get_recommendation_action",
    # Cost estimation
    "estimate_abandoned_resource_cost",
    "get_supported_cost_types",
    "get_cost_breakdown",
    # Queries
    "get_all_queries",
    "get_query_for_resource_type",
    "get_supported_query_types",
    "query_unattached_disks",
    "query_unused_public_ips",
    "query_empty_load_balancers",
    "query_orphaned_nat_gateways",
    "query_empty_sql_elastic_pools",
    "query_unused_vnet_gateways",
    "query_orphaned_ddos_plans",
    "query_disconnected_private_endpoints",
]
