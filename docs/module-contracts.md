# Module Interface Contracts

All detection modules implement a standard input/output contract. This enables the AI agent to discover, execute, and process any registered module without module-specific logic.

## ModuleInput

The AI agent sends this payload when invoking a detection module.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `executionId` | string | Yes | Unique identifier for this execution run |
| `subscriptionIds` | string[] | Yes | Azure subscription IDs to scan |
| `configuration` | object | No | Module-specific configuration (from registry) |
| `dryRun` | boolean | No | If true, detect but don't persist findings |

### Example

```json
{
  "executionId": "exec-2026-01-10-001",
  "subscriptionIds": [
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002"
  ],
  "configuration": {
    "resourceTypes": [
      "microsoft.compute/disks",
      "microsoft.network/publicipaddresses"
    ],
    "minimumOrphanAgeDays": 7
  },
  "dryRun": false
}
```

---

## ModuleOutput

Each module returns this structure after execution.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `moduleId` | string | Yes | Module identifier |
| `moduleName` | string | No | Human-readable module name |
| `version` | string | No | Module version |
| `executionId` | string | Yes | Matches input executionId |
| `executionTime` | datetime | Yes | When execution completed |
| `status` | string | Yes | "success", "partial", or "failed" |
| `subscriptionsScanned` | int | Yes | Number of subscriptions processed |
| `findings` | Finding[] | Yes | Array of detected findings |
| `summary` | ModuleSummary | Yes | Aggregated statistics |
| `errors` | string[] | No | Any errors encountered |

### Example

```json
{
  "moduleId": "abandoned-resources",
  "moduleName": "Abandoned Resources Detector",
  "version": "1.0.0",
  "executionId": "exec-2026-01-10-001",
  "executionTime": "2026-01-10T14:30:00Z",
  "status": "success",
  "subscriptionsScanned": 2,
  "findings": [
    {
      "findingId": "f-abc123",
      "subscriptionId": "00000000-0000-0000-0000-000000000001",
      "resourceId": "/subscriptions/.../disks/orphaned-disk-01",
      "resourceType": "microsoft.compute/disks",
      "resourceName": "orphaned-disk-01",
      "resourceGroup": "rg-sandbox",
      "location": "eastus",
      "category": "abandoned",
      "severity": "medium",
      "confidenceScore": 85,
      "confidenceLevel": "high",
      "incursCost": true,
      "estimatedMonthlyCost": 38.40,
      "currency": "USD",
      "description": "Unattached managed disk (Premium_LRS, 256 GB)",
      "detectionRule": "disk-not-attached",
      "metadata": {
        "diskSizeGB": 256,
        "sku": "Premium_LRS",
        "orphanedDays": 45
      }
    }
  ],
  "summary": {
    "totalFindings": 1,
    "totalEstimatedMonthlySavings": 38.40,
    "findingsBySeverity": {
      "medium": 1
    },
    "findingsByResourceType": {
      "microsoft.compute/disks": 1
    },
    "subscriptionsWithFindings": 1,
    "subscriptionsClean": 1
  },
  "errors": []
}
```

---

## Finding

Individual optimization finding detected by a module.

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `findingId` | string | Yes | Unique finding identifier |
| `subscriptionId` | string | Yes | Azure subscription ID |
| `subscriptionName` | string | No | Subscription display name |
| `resourceId` | string | Yes | Full Azure resource ID |
| `resourceType` | string | Yes | Azure resource type (lowercase) |
| `resourceName` | string | No | Resource display name |
| `resourceGroup` | string | No | Resource group name |
| `location` | string | No | Azure region |
| `category` | enum | Yes | Finding category (see below) |
| `severity` | enum | Yes | Severity level (see below) |
| `confidenceScore` | int | Yes | 0-100 confidence score |
| `confidenceLevel` | enum | Yes | Confidence level (see below) |
| `incursCost` | boolean | Yes | Whether resource incurs cost |
| `estimatedMonthlyCost` | float | Yes | Estimated monthly cost in USD |
| `currency` | string | No | Currency code (default: "USD") |
| `description` | string | No | Human-readable description |
| `detectionRule` | string | No | Rule that triggered finding |
| `firstDetectedDate` | datetime | No | When first detected |
| `metadata` | object | No | Module-specific additional data |

### Category Values

| Value | Description |
|-------|-------------|
| `abandoned` | Resource no longer in use (unattached, disconnected) |
| `overprovisioned` | Resource sized larger than needed |
| `idle` | Resource running but not being utilized |
| `misconfigured` | Configuration causing unnecessary cost |
| `opportunity` | Potential optimization (reserved instances, etc.) |

### Severity Values

Based on estimated monthly cost impact:

| Value | Monthly Cost |
|-------|--------------|
| `critical` | > $1,000 |
| `high` | $100 - $1,000 |
| `medium` | $10 - $100 |
| `low` | $1 - $10 |
| `informational` | < $1 |

### Confidence Level Values

| Value | Score Range | Criteria |
|-------|-------------|----------|
| `certain` | 95-100 | Definite issue (e.g., orphaned 90+ days) |
| `high` | 75-94 | Very likely (e.g., orphaned 30-90 days) |
| `medium` | 50-74 | Probable (e.g., orphaned 7-30 days) |
| `low` | 25-49 | Possible (e.g., orphaned < 7 days) |
| `uncertain` | 0-24 | Needs investigation |

---

## ModuleSummary

Aggregated statistics included in ModuleOutput.

### Schema

| Field | Type | Description |
|-------|------|-------------|
| `totalFindings` | int | Total number of findings |
| `totalEstimatedMonthlySavings` | float | Sum of all finding costs |
| `findingsBySeverity` | object | Count per severity level |
| `findingsByResourceType` | object | Count per resource type |
| `subscriptionsWithFindings` | int | Subscriptions with issues |
| `subscriptionsClean` | int | Subscriptions with no issues |

### Example

```json
{
  "totalFindings": 47,
  "totalEstimatedMonthlySavings": 2847.50,
  "findingsBySeverity": {
    "critical": 2,
    "high": 8,
    "medium": 25,
    "low": 12
  },
  "findingsByResourceType": {
    "microsoft.compute/disks": 18,
    "microsoft.network/publicipaddresses": 15,
    "microsoft.network/loadbalancers": 8,
    "microsoft.network/natgateways": 6
  },
  "subscriptionsWithFindings": 35,
  "subscriptionsClean": 165
}
```

---

## Python Implementation

These contracts are implemented as Pydantic models in `src/functions/shared/models.py`:

```python
from shared import ModuleInput, ModuleOutput, Finding, ModuleSummary

# Parse incoming request
input_data = ModuleInput.model_validate(request_json)

# Create findings
finding = Finding(
    findingId="f-123",
    subscriptionId="...",
    resourceId="...",
    resourceType="microsoft.compute/disks",
    category="abandoned",
    severity="medium",
    confidenceScore=85,
    confidenceLevel="high",
    incursCost=True,
    estimatedMonthlyCost=38.40
)

# Build response
output = ModuleOutput(
    moduleId="abandoned-resources",
    executionId=input_data.execution_id,
    subscriptionsScanned=len(input_data.subscription_ids),
    findings=[finding],
    summary=ModuleSummary(
        totalFindings=1,
        totalEstimatedMonthlySavings=38.40
    )
)

# Serialize to JSON (uses camelCase aliases)
return output.model_dump(by_alias=True)
```

---

## FindingsTrends

The trends endpoint provides month-over-month analysis for any detection module. This enables the AI agent to add historical context to notifications (e.g., "Great job! Abandoned disks decreased from 50 to 22").

### Request

```
GET /api/get-findings-trends?module_id=abandoned-resources&months=3&subscription_id=xxx
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `module_id` | string | Yes | Module ID (e.g., 'abandoned-resources', 'overprovisioned-vms') |
| `months` | int | No | Number of months to analyze (default: 3) |
| `subscription_id` | string | No | Filter to specific subscription |

### Response Schema

| Field | Type | Description |
|-------|------|-------------|
| `moduleId` | string | Module ID that was queried |
| `subscriptionId` | string | Subscription filter (if provided) |
| `periodMonths` | int | Number of months analyzed |
| `generatedAt` | datetime | When the trends were calculated |
| `trends` | MonthlyTrend[] | Array of monthly aggregates (most recent first) |
| `summary` | TrendSummary | Month-over-month change summary |

### MonthlyTrend

| Field | Type | Description |
|-------|------|-------------|
| `month` | string | Year-month (e.g., "2026-01") |
| `totalFindings` | int | Number of findings that month |
| `totalCost` | float | Total estimated monthly cost |
| `bySeverity` | object | Count per severity level |
| `byResourceType` | object | Count per resource type |
| `subscriptionsAffected` | int | Number of subscriptions with findings |

### TrendSummary

| Field | Type | Description |
|-------|------|-------------|
| `hasComparison` | boolean | Whether comparison data is available |
| `currentMonth` | string | Current month being compared |
| `previousMonth` | string | Previous month being compared |
| `findingsChange` | int | Change in finding count (negative = improvement) |
| `findingsChangePercent` | float | Percentage change |
| `costChange` | float | Change in estimated cost |
| `costChangePercent` | float | Percentage cost change |
| `trend` | string | "improving", "worsening", or "stable" |
| `message` | string | Human-readable trend message for notifications |

### Example Response

```json
{
  "moduleId": "abandoned-resources",
  "subscriptionId": null,
  "periodMonths": 3,
  "generatedAt": "2026-01-10T14:30:00Z",
  "trends": [
    {
      "month": "2026-01",
      "totalFindings": 22,
      "totalCost": 850.00,
      "bySeverity": {"high": 3, "medium": 12, "low": 7},
      "byResourceType": {"microsoft.compute/disks": 15, "microsoft.network/publicipaddresses": 7},
      "subscriptionsAffected": 18
    },
    {
      "month": "2025-12",
      "totalFindings": 50,
      "totalCost": 1920.00,
      "bySeverity": {"critical": 2, "high": 8, "medium": 25, "low": 15},
      "byResourceType": {"microsoft.compute/disks": 30, "microsoft.network/publicipaddresses": 20},
      "subscriptionsAffected": 35
    },
    {
      "month": "2025-11",
      "totalFindings": 45,
      "totalCost": 1730.00,
      "bySeverity": {"high": 5, "medium": 28, "low": 12},
      "byResourceType": {"microsoft.compute/disks": 28, "microsoft.network/publicipaddresses": 17},
      "subscriptionsAffected": 32
    }
  ],
  "summary": {
    "hasComparison": true,
    "currentMonth": "2026-01",
    "previousMonth": "2025-12",
    "findingsChange": -28,
    "findingsChangePercent": -56.0,
    "costChange": -1070.00,
    "costChangePercent": -55.7,
    "trend": "improving",
    "message": "Great progress! Findings decreased from 50 to 22 (56% reduction), saving an estimated $1,070.00/month compared to 2025-12."
  }
}
```

### Module-Agnostic Design

The trends endpoint works with any detection module. Examples:

```bash
# Abandoned resources trends
GET /api/get-findings-trends?module_id=abandoned-resources&months=6

# Overprovisioned VMs trends (when module is added)
GET /api/get-findings-trends?module_id=overprovisioned-vms&months=3

# Idle databases trends for a specific subscription
GET /api/get-findings-trends?module_id=idle-databases&subscription_id=xxx
```

---

## HTTP API

Detection modules are exposed as Azure Functions with the following endpoint pattern:

```
POST /api/{module-id}
Content-Type: application/json

{
  "executionId": "...",
  "subscriptionIds": ["..."],
  "configuration": {...},
  "dryRun": false
}
```

Response:

```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "moduleId": "...",
  "executionId": "...",
  "status": "success",
  "findings": [...],
  "summary": {...}
}
```
