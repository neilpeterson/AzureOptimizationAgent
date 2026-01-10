"""Shared library for Azure Optimization Agent functions."""

from shared.models import (
    Finding,
    ModuleInput,
    ModuleOutput,
    ModuleSummary,
    ModuleRegistry,
    SubscriptionOwner,
    ExecutionLog,
    FindingCategory,
    Severity,
    ConfidenceLevel,
)
from shared.cosmos_client import CosmosClient
from shared.resource_graph import ResourceGraphClient
from shared.confidence import (
    get_confidence_level,
    clamp_score,
    should_report_finding,
    get_confidence_thresholds,
)
from shared.cost_calculator import (
    classify_severity,
    get_severity_thresholds,
    get_severity_priority,
    calculate_total_savings,
    summarize_by_severity,
    summarize_by_resource_type,
    format_cost,
)

__all__ = [
    # Models
    "Finding",
    "ModuleInput",
    "ModuleOutput",
    "ModuleSummary",
    "ModuleRegistry",
    "SubscriptionOwner",
    "ExecutionLog",
    "FindingCategory",
    "Severity",
    "ConfidenceLevel",
    # Clients
    "CosmosClient",
    "ResourceGraphClient",
    # Confidence utilities
    "get_confidence_level",
    "clamp_score",
    "should_report_finding",
    "get_confidence_thresholds",
    # Cost utilities
    "classify_severity",
    "get_severity_thresholds",
    "get_severity_priority",
    "calculate_total_savings",
    "summarize_by_severity",
    "summarize_by_resource_type",
    "format_cost",
]
