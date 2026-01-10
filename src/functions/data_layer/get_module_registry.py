"""Get module registry function.

Retrieves enabled (and optionally disabled) modules from the module-registry
container in Cosmos DB.
"""

from __future__ import annotations

import logging
from typing import Any

from shared import CosmosClient

logger = logging.getLogger(__name__)


def get_module_registry(include_disabled: bool = False) -> dict[str, Any]:
    """Get modules from the registry.

    Args:
        include_disabled: If True, include disabled modules in the response.

    Returns:
        Dictionary with:
            - modules: List of module registry entries
            - count: Number of modules returned
    """
    logger.info(f"Getting module registry (include_disabled={include_disabled})")

    client = CosmosClient()

    if include_disabled:
        # Get all modules
        modules = client.get_all_modules()
    else:
        # Get only enabled modules
        modules = client.get_enabled_modules()

    logger.info(f"Found {len(modules)} modules")

    return {
        "modules": modules,
        "count": len(modules),
    }
