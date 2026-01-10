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
