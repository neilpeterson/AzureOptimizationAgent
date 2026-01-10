"""Pydantic models for Azure Optimization Agent data contracts."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FindingCategory(str, Enum):
    """Category of optimization finding."""

    ABANDONED = "abandoned"
    OVERPROVISIONED = "overprovisioned"
    IDLE = "idle"
    MISCONFIGURED = "misconfigured"
    OPPORTUNITY = "opportunity"


class Severity(str, Enum):
    """Severity based on monthly cost impact."""

    CRITICAL = "critical"  # >$1,000/month
    HIGH = "high"  # $100-$1,000/month
    MEDIUM = "medium"  # $10-$100/month
    LOW = "low"  # $1-$10/month
    INFORMATIONAL = "informational"  # $0/month


class ConfidenceLevel(str, Enum):
    """Confidence level for finding accuracy."""

    CERTAIN = "certain"  # 95-100%
    HIGH = "high"  # 75-94%
    MEDIUM = "medium"  # 50-74%
    LOW = "low"  # 25-49%
    UNCERTAIN = "uncertain"  # <25%


class ModuleStatus(str, Enum):
    """Module lifecycle status."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    DEVELOPMENT = "development"


class Finding(BaseModel):
    """Standard finding schema (v1) for all optimization modules."""

    finding_id: str = Field(..., alias="findingId")
    subscription_id: str = Field(..., alias="subscriptionId")
    subscription_name: str | None = Field(None, alias="subscriptionName")
    resource_id: str = Field(..., alias="resourceId")
    resource_type: str = Field(..., alias="resourceType")
    resource_name: str | None = Field(None, alias="resourceName")
    resource_group: str | None = Field(None, alias="resourceGroup")
    location: str | None = None
    category: FindingCategory
    severity: Severity
    confidence_score: int = Field(..., ge=0, le=100, alias="confidenceScore")
    confidence_level: ConfidenceLevel = Field(..., alias="confidenceLevel")
    incurs_cost: bool = Field(..., alias="incursCost")
    estimated_monthly_cost: float = Field(0.0, ge=0, alias="estimatedMonthlyCost")
    currency: str = "USD"
    description: str | None = None
    detection_rule: str | None = Field(None, alias="detectionRule")
    first_detected_date: datetime | None = Field(None, alias="firstDetectedDate")
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        use_enum_values = True


class ModuleInput(BaseModel):
    """Input contract for optimization modules."""

    execution_id: str = Field(..., alias="executionId")
    subscription_ids: list[str] = Field(..., alias="subscriptionIds")
    configuration: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = Field(False, alias="dryRun")

    class Config:
        populate_by_name = True


class ModuleSummary(BaseModel):
    """Summary statistics for module execution."""

    total_findings: int = Field(0, alias="totalFindings")
    total_estimated_monthly_savings: float = Field(0.0, alias="totalEstimatedMonthlySavings")
    findings_by_severity: dict[str, int] = Field(default_factory=dict, alias="findingsBySeverity")
    findings_by_resource_type: dict[str, int] = Field(
        default_factory=dict, alias="findingsByResourceType"
    )
    subscriptions_with_findings: int = Field(0, alias="subscriptionsWithFindings")
    subscriptions_clean: int = Field(0, alias="subscriptionsClean")

    class Config:
        populate_by_name = True


class ModuleOutput(BaseModel):
    """Output contract for optimization modules."""

    module_id: str = Field(..., alias="moduleId")
    module_name: str | None = Field(None, alias="moduleName")
    version: str | None = None
    execution_id: str = Field(..., alias="executionId")
    execution_time: datetime = Field(default_factory=datetime.utcnow, alias="executionTime")
    status: str = "success"
    subscriptions_scanned: int = Field(0, alias="subscriptionsScanned")
    findings: list[Finding] = Field(default_factory=list)
    summary: ModuleSummary = Field(default_factory=ModuleSummary)
    errors: list[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class ConfidenceThresholds(BaseModel):
    """Thresholds for confidence level classification.

    This is a generic model used by all modules for consistent
    confidence level boundaries.
    """

    certain: int = 95
    high: int = 75
    medium: int = 50
    low: int = 25


class ModuleRegistry(BaseModel):
    """Module metadata stored in Cosmos DB module-registry container.

    Note: The `configuration` field is module-specific and opaque to the
    shared library. Each detection module defines its own configuration
    schema and validates it when invoked.
    """

    id: str
    module_id: str = Field(..., alias="moduleId")
    module_name: str = Field(..., alias="moduleName")
    version: str = "1.0.0"
    enabled: bool = True
    status: ModuleStatus = ModuleStatus.ACTIVE
    category: str = "cost-optimization"
    description: str | None = None
    function_app: str | None = Field(None, alias="functionApp")
    function_name: str | None = Field(None, alias="functionName")
    schedule: str = "monthly"
    output_schema: str = Field("v1-standard-findings", alias="outputSchema")
    configuration: dict[str, Any] = Field(default_factory=dict)
    created_date: datetime | None = Field(None, alias="createdDate")
    last_modified_date: datetime | None = Field(None, alias="lastModifiedDate")
    last_execution_date: datetime | None = Field(None, alias="lastExecutionDate")

    class Config:
        populate_by_name = True
        use_enum_values = True


class NotificationPreferences(BaseModel):
    """User notification preferences."""

    timezone: str = "America/Los_Angeles"
    language: str = "en-US"


class SubscriptionOwner(BaseModel):
    """Subscription-to-owner mapping stored in Cosmos DB."""

    id: str
    subscription_id: str = Field(..., alias="subscriptionId")
    subscription_name: str | None = Field(None, alias="subscriptionName")
    owner_email: str = Field(..., alias="ownerEmail")
    owner_name: str | None = Field(None, alias="ownerName")
    team_name: str | None = Field(None, alias="teamName")
    cost_center: str | None = Field(None, alias="costCenter")
    notification_preferences: NotificationPreferences = Field(
        default_factory=NotificationPreferences, alias="notificationPreferences"
    )
    last_updated: datetime | None = Field(None, alias="lastUpdated")
    data_source: str = Field("manual", alias="dataSource")

    class Config:
        populate_by_name = True


class FindingHistory(BaseModel):
    """Historical finding record stored in Cosmos DB findings-history container."""

    id: str
    finding_id: str = Field(..., alias="findingId")
    execution_id: str = Field(..., alias="executionId")
    execution_date: datetime = Field(..., alias="executionDate")
    subscription_id: str = Field(..., alias="subscriptionId")
    module_id: str = Field(..., alias="moduleId")
    resource_id: str = Field(..., alias="resourceId")
    resource_type: str = Field(..., alias="resourceType")
    category: FindingCategory
    severity: Severity
    confidence_score: int = Field(..., ge=0, le=100, alias="confidenceScore")
    estimated_monthly_cost: float = Field(0.0, alias="estimatedMonthlyCost")
    status: str = "open"
    first_detected_date: datetime | None = Field(None, alias="firstDetectedDate")
    resolved_date: datetime | None = Field(None, alias="resolvedDate")
    ttl: int = 31536000  # 365 days in seconds

    class Config:
        populate_by_name = True
        use_enum_values = True


class ExecutionLog(BaseModel):
    """Execution audit log stored in Cosmos DB execution-logs container."""

    id: str
    execution_id: str = Field(..., alias="executionId")
    start_time: datetime = Field(..., alias="startTime")
    end_time: datetime | None = Field(None, alias="endTime")
    status: str = "running"
    modules_executed: list[str] = Field(default_factory=list, alias="modulesExecuted")
    total_findings: int = Field(0, alias="totalFindings")
    total_subscriptions: int = Field(0, alias="totalSubscriptions")
    emails_sent: int = Field(0, alias="emailsSent")
    errors: list[str] = Field(default_factory=list)
    ttl: int = 7776000  # 90 days in seconds

    class Config:
        populate_by_name = True
