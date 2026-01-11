"""Data Layer functions for the Optimization Agent.

This module provides HTTP-triggered functions for managing data in Cosmos DB:
- Module registry (list enabled modules)
- Findings history (store and query findings)
- Findings trends (month-over-month analysis)
- Detection targets (subscriptions/management groups with owner info)
"""

from data_layer.get_module_registry import get_module_registry
from data_layer.save_findings import save_findings
from data_layer.get_findings_history import get_findings_history
from data_layer.get_findings_trends import get_findings_trends
from data_layer.get_detection_targets import get_detection_targets

__all__ = [
    "get_module_registry",
    "save_findings",
    "get_findings_history",
    "get_findings_trends",
    "get_detection_targets",
]
