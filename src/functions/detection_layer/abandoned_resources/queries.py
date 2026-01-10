"""Azure Resource Graph KQL queries for abandoned resources detection.

This module contains all KQL queries used to detect orphaned Azure resources
that incur cost but provide no value.
"""

from __future__ import annotations


def query_unattached_disks() -> str:
    """KQL query for unattached managed disks."""
    return """
Resources
| where type =~ 'microsoft.compute/disks'
| where properties.diskState == 'Unattached'
| project
    id,
    subscriptionId,
    resourceGroup,
    name,
    location,
    sku = properties.sku.name,
    diskSizeGB = properties.diskSizeGB,
    diskState = properties.diskState,
    timeCreated = properties.timeCreated,
    tags
"""


def query_unused_public_ips() -> str:
    """KQL query for unused Standard SKU public IPs."""
    return """
Resources
| where type =~ 'microsoft.network/publicipaddresses'
| where sku.name == 'Standard'
| where isnull(properties.ipConfiguration)
| project
    id,
    subscriptionId,
    resourceGroup,
    name,
    location,
    sku = sku.name,
    allocationMethod = properties.publicIPAllocationMethod,
    ipAddress = properties.ipAddress,
    tags
"""


def query_empty_load_balancers() -> str:
    """KQL query for load balancers without backend pools."""
    return """
Resources
| where type =~ 'microsoft.network/loadbalancers'
| where sku.name == 'Standard'
| where array_length(properties.backendAddressPools) == 0
    or isnull(properties.backendAddressPools[0].properties.backendIPConfigurations)
    or array_length(properties.backendAddressPools[0].properties.backendIPConfigurations) == 0
| project
    id,
    subscriptionId,
    resourceGroup,
    name,
    location,
    sku = sku.name,
    backendPoolCount = array_length(properties.backendAddressPools),
    tags
"""


def query_orphaned_nat_gateways() -> str:
    """KQL query for NAT gateways without subnet associations."""
    return """
Resources
| where type =~ 'microsoft.network/natgateways'
| where isnull(properties.subnets) or array_length(properties.subnets) == 0
| project
    id,
    subscriptionId,
    resourceGroup,
    name,
    location,
    idleTimeoutInMinutes = properties.idleTimeoutInMinutes,
    tags
"""


def query_empty_sql_elastic_pools() -> str:
    """KQL query for SQL elastic pools without databases."""
    return """
Resources
| where type =~ 'microsoft.sql/servers/elasticpools'
| project
    id,
    subscriptionId,
    resourceGroup,
    name,
    location,
    sku = sku.name,
    tier = sku.tier,
    capacity = sku.capacity,
    maxSizeBytes = properties.maxSizeBytes,
    tags,
    serverId = tostring(split(id, '/elasticPools/')[0])
| join kind=leftouter (
    Resources
    | where type =~ 'microsoft.sql/servers/databases'
    | where properties.elasticPoolId != ''
    | summarize dbCount = count() by elasticPoolId = tolower(properties.elasticPoolId)
) on $left.id == $right.elasticPoolId
| where isnull(dbCount) or dbCount == 0
| project-away elasticPoolId, dbCount
"""


def query_unused_vnet_gateways() -> str:
    """KQL query for VNet gateways without connections."""
    return """
Resources
| where type =~ 'microsoft.network/virtualnetworkgateways'
| project
    id,
    subscriptionId,
    resourceGroup,
    name,
    location,
    gatewayType = properties.gatewayType,
    sku = properties.sku.name,
    tags
| join kind=leftouter (
    Resources
    | where type =~ 'microsoft.network/connections'
    | mv-expand gateway = pack_array(
        properties.virtualNetworkGateway1.id,
        properties.virtualNetworkGateway2.id
    )
    | where isnotnull(gateway)
    | summarize connectionCount = count() by gatewayId = tolower(tostring(gateway))
) on $left.id == $right.gatewayId
| where isnull(connectionCount) or connectionCount == 0
| project-away gatewayId, connectionCount
"""


def query_orphaned_ddos_plans() -> str:
    """KQL query for DDoS protection plans without VNets."""
    return """
Resources
| where type =~ 'microsoft.network/ddosprotectionplans'
| where isnull(properties.virtualNetworks) or array_length(properties.virtualNetworks) == 0
| project
    id,
    subscriptionId,
    resourceGroup,
    name,
    location,
    provisioningState = properties.provisioningState,
    tags
"""


def query_disconnected_private_endpoints() -> str:
    """KQL query for private endpoints not connected to resources."""
    return """
Resources
| where type =~ 'microsoft.network/privateendpoints'
| where properties.provisioningState == 'Succeeded'
| where isnull(properties.privateLinkServiceConnections)
    or array_length(properties.privateLinkServiceConnections) == 0
| where isnull(properties.manualPrivateLinkServiceConnections)
    or array_length(properties.manualPrivateLinkServiceConnections) == 0
| project
    id,
    subscriptionId,
    resourceGroup,
    name,
    location,
    provisioningState = properties.provisioningState,
    tags
"""


# Map of resource types to their query functions
ABANDONED_RESOURCE_QUERIES = {
    "microsoft.compute/disks": query_unattached_disks,
    "microsoft.network/publicipaddresses": query_unused_public_ips,
    "microsoft.network/loadbalancers": query_empty_load_balancers,
    "microsoft.network/natgateways": query_orphaned_nat_gateways,
    "microsoft.sql/servers/elasticpools": query_empty_sql_elastic_pools,
    "microsoft.network/virtualnetworkgateways": query_unused_vnet_gateways,
    "microsoft.network/ddosprotectionplans": query_orphaned_ddos_plans,
    "microsoft.network/privateendpoints": query_disconnected_private_endpoints,
}


def get_all_queries() -> dict[str, str]:
    """Get all abandoned resource queries as a dictionary.

    Returns:
        Dictionary mapping resource type to KQL query string.
    """
    return {
        resource_type: query_func()
        for resource_type, query_func in ABANDONED_RESOURCE_QUERIES.items()
    }


def get_query_for_resource_type(resource_type: str) -> str | None:
    """Get the query for a specific resource type.

    Args:
        resource_type: Azure resource type (lowercase).

    Returns:
        KQL query string, or None if resource type not supported.
    """
    query_func = ABANDONED_RESOURCE_QUERIES.get(resource_type.lower())
    return query_func() if query_func else None


def get_supported_resource_types() -> list[str]:
    """Get list of resource types with available queries.

    Returns:
        List of Azure resource type strings.
    """
    return list(ABANDONED_RESOURCE_QUERIES.keys())
