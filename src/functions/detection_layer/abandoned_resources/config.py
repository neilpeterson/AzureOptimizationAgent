"""Configuration schema for the Abandoned Resources detection module.

This module defines the configuration structure specific to abandoned
resources detection. The configuration is stored in Cosmos DB as part
of the ModuleRegistry document and validated when the module is invoked.
"""

from pydantic import BaseModel, Field

from shared.models import ConfidenceThresholds


class AbandonedResourcesConfig(BaseModel):
    """Configuration for the Abandoned Resources detection module.

    This configuration is stored in ModuleRegistry.configuration and
    parsed by the detector when invoked.

    Example Cosmos DB document:
        {
            "moduleId": "abandoned-resources",
            "configuration": {
                "resourceTypes": ["microsoft.compute/disks", ...],
                "minimumOrphanAgeDays": 7,
                "confidenceThresholds": {"certain": 95, "high": 75, ...}
            }
        }
    """

    resource_types: list[str] = Field(
        default_factory=lambda: [
            "microsoft.compute/disks",
            "microsoft.network/publicipaddresses",
            "microsoft.network/loadbalancers",
            "microsoft.network/natgateways",
            "microsoft.sql/servers/elasticpools",
            "microsoft.network/virtualnetworkgateways",
            "microsoft.network/ddosprotectionplans",
            "microsoft.network/privateendpoints",
        ],
        alias="resourceTypes",
        description="Azure resource types to scan for abandoned resources",
    )

    minimum_orphan_age_days: int = Field(
        7,
        ge=1,
        alias="minimumOrphanAgeDays",
        description="Minimum days a resource must be orphaned to be reported",
    )

    confidence_thresholds: ConfidenceThresholds = Field(
        default_factory=ConfidenceThresholds,
        alias="confidenceThresholds",
        description="Score thresholds for confidence level classification",
    )

    include_zero_cost: bool = Field(
        False,
        alias="includeZeroCost",
        description="Include resources that don't incur cost (e.g., orphaned NICs)",
    )

    class Config:
        populate_by_name = True


def parse_config(configuration: dict) -> AbandonedResourcesConfig:
    """Parse and validate module configuration from registry.

    Args:
        configuration: Raw configuration dict from ModuleRegistry.

    Returns:
        Validated AbandonedResourcesConfig instance.

    Raises:
        ValidationError: If configuration is invalid.
    """
    return AbandonedResourcesConfig(**configuration)
