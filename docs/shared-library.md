# Shared Library Architecture

This document describes the shared library (`src/functions/shared/`) and how detection modules interact with it.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                AI Agent (GPT-4o)                                │
│                         Azure AI Foundry Agent Service                          │
└───────────────────────────────────────┬─────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
        ┌───────────────────┐ ┌─────────────────┐ ┌─────────────────┐
        │  Detection Layer  │ │   Data Layer    │ │  Notification   │
        │                   │ │                 │ │     Layer       │
        │ ┌───────────────┐ │ │ get-registry    │ │                 │
        │ │   Abandoned   │ │ │ save-findings   │ │   Logic App     │
        │ │   Resources   │ │ │ get-history     │ │   (Email)       │
        │ ├───────────────┤ │ │ get-owners      │ │                 │
        │ │ Future:       │ │ │                 │ │                 │
        │ │ Overprovis-   │ │ │                 │ │                 │
        │ │ ioned VMs     │ │ │                 │ │                 │
        │ └───────────────┘ │ │                 │ │                 │
        └─────────┬─────────┘ └────────┬────────┘ └────────┬────────┘
                  │                    │                   │
                  └────────────────────┼───────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            SHARED LIBRARY                                       │
│                         (src/functions/shared/)                                 │
│                                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   models    │  │   cosmos    │  │  resource   │  │  confidence    cost     │ │
│  │             │  │   client    │  │   graph     │  │  utilities   calculator │ │
│  │  Finding    │  │             │  │   client    │  │                         │ │
│  │  ModuleIn   │  │  CRUD for   │  │             │  │ get_level()  classify() │ │
│  │  ModuleOut  │  │ 4 containers│  │  query()    │  │ clamp()      format()   │ │
│  │  Registry   │  │             │  │  batched()  │  │ threshold()  summarize()│ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└───────────┬───────────────┬───────────────┬───────────────────────┬─────────────┘
            │               │               │                       │
            ▼               ▼               ▼                       ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      ┌─────────────┐
    │  Cosmos DB  │  │  Cosmos DB  │  │    Azure    │      │   Azure     │
    │  Serverless │  │  Serverless │  │  Resource   │      │   (other)   │
    │             │  │             │  │    Graph    │      │             │
    └─────────────┘  └─────────────┘  └─────────────┘      └─────────────┘
```

## Design Principle

The shared library contains **generic, reusable components** that any detection module can use. Module-specific logic (queries, confidence scoring, cost estimation, configuration) lives within each detection module.

```
src/functions/
├── shared/                          # Generic utilities
│   ├── models.py                    # Data contracts
│   ├── cosmos_client.py             # Database operations
│   ├── resource_graph.py            # Query execution
│   ├── confidence.py                # Score utilities
│   └── cost_calculator.py           # Severity classification
│
└── detection_layer/
    └── abandoned_resources/         # Module-specific
        ├── config.py                # Configuration schema
        ├── queries.py               # KQL queries
        ├── confidence.py            # Confidence scoring logic
        ├── cost_calculator.py       # Cost estimation
        └── detector.py              # Main detection logic
```

### Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SHARED LIBRARY                                     │
│                            (Generic, Reusable)                                  │
│                                                                                 │
│   "Execute this KQL"     "Store this data"     "Score 85 = HIGH"                │
│   "Query these subs"     "Read this record"    "$150 = SEVERITY.HIGH"           │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ uses
                                      │
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DETECTION MODULES                                     │
│                          (Domain-Specific)                                      │
│                                                                                 │
│   "Query unattached disks"          "Disk orphaned 90 days = +30 points"        │
│   "Query unused public IPs"         "Name starts with 'temp-' = +15 points"     │
│   "Query empty load balancers"      "Premium_LRS disk costs $0.15/GB"           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## ResourceGraphClient

### Overview

The `ResourceGraphClient` is a thin wrapper around Azure Resource Graph that handles cross-subscription query complexity.

```python
from shared import ResourceGraphClient

client = ResourceGraphClient()
results = client.query(kql_string, subscription_ids=["sub-1", "sub-2"])
```

### Methods

| Method | Purpose |
|--------|---------|
| `query(kql, subscription_ids, management_group_id)` | Execute a query with automatic pagination |
| `query_batched(kql, subscription_ids)` | Handle >1000 subscriptions by splitting into batches |
| `query_single(kql, subscription_id)` | Convenience method for single subscription |

### Key Features

1. **Managed Identity Auth** - Uses `DefaultAzureCredential`, no secrets in code
2. **Automatic Pagination** - Fetches all pages via `skip_token`
3. **Batch Splitting** - Azure limits queries to 1000 subscriptions; automatically splits larger lists

### How Modules Use It

Each module provides its own KQL queries and passes them to the generic client:

```python
# detection_layer/abandoned_resources/detector.py
from shared import ResourceGraphClient
from detection_layer.abandoned_resources import query_unattached_disks

def detect(subscription_ids: list[str]) -> list[Finding]:
    client = ResourceGraphClient()

    # Module provides the KQL, client executes it
    orphaned_disks = client.query(
        query_unattached_disks(),  # KQL from module's queries.py
        subscription_ids=subscription_ids
    )

    # Process results into findings...
```

### Query Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Detection Module                             │
│  ┌─────────────────┐                                            │
│  │ Module-specific │──── KQL query string ────┐                 │
│  │ queries.py      │                          │                 │
│  └─────────────────┘                          ▼                 │
│                                    ┌──────────────────────┐     │
│                                    │ ResourceGraphClient  │     │
│                                    │ (shared library)     │     │
│                                    └──────────┬───────────┘     │
└───────────────────────────────────────────────┼─────────────────┘
                                                │
                                                ▼
                                    ┌──────────────────────┐
                                    │ Azure Resource Graph │
                                    │ (target subs/mgmt)   │
                                    └──────────────────────┘
```

---

## CosmosClient

### Overview

The `CosmosClient` provides CRUD operations for all four Cosmos DB containers used by the solution.

```python
from shared import CosmosClient

client = CosmosClient()  # Uses COSMOS_ENDPOINT and COSMOS_DATABASE env vars
modules = client.get_enabled_modules()
```

### Containers

| Container | Partition Key | Purpose |
|-----------|---------------|---------|
| `module-registry` | `/moduleId` | Module configuration and metadata |
| `findings-history` | `/subscriptionId` | Historical findings (365-day TTL) |
| `subscription-owners` | `/subscriptionId` | Owner contact mapping |
| `execution-logs` | `/executionId` | Audit trail (90-day TTL) |

### Key Methods

**Module Registry:**
- `get_enabled_modules()` - List all active modules
- `get_module(module_id)` - Get specific module
- `update_module_execution(module_id, date)` - Update last run time

**Findings History:**
- `save_findings(findings)` - Store findings
- `get_findings_by_subscription(subscription_id)` - For trend analysis
- `get_findings_by_execution(execution_id)` - All findings from a run

**Subscription Owners:**
- `get_subscription_owner(subscription_id)` - Single lookup
- `get_subscription_owners(subscription_ids)` - Batch lookup

**Execution Logs:**
- `create_execution_log(log)` - Start new execution
- `update_execution_log(execution_id, updates)` - Update status
- `get_recent_executions(limit)` - Recent runs

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI Agent                                       │
│                                                                             │
│  1. Get modules    2. Execute modules    3. Save results    4. Send emails  │
│        │                   │                    │                  │        │
└────────┼───────────────────┼────────────────────┼──────────────────┼────────┘
         │                   │                    │                  │
         ▼                   ▼                    ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CosmosClient                                      │
│                        (shared library)                                     │
└─────────────────────────────────────────────────────────────────────────────┘
         │                   │                    │                  │
         ▼                   ▼                    ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌──────────────────┐    ┌──────────────┐
│   module-   │    │  execution- │    │    findings-     │    │ subscription-│
│  registry   │    │    logs     │    │     history      │    │    owners    │
├─────────────┤    ├─────────────┤    ├──────────────────┤    ├──────────────┤
│ moduleId    │    │ executionId │    │ subscriptionId   │    │subscriptionId│
│ enabled     │    │ startTime   │    │ findingId        │    │ ownerEmail   │
│ config{}    │    │ status      │    │ severity         │    │ ownerName    │
│ lastExec    │    │ findings    │    │ cost             │    │ teamName     │
└─────────────┘    └─────────────┘    └──────────────────┘    └──────────────┘
     TTL: ∞           TTL: 90 days        TTL: 365 days           TTL: ∞
```

---

## Models

### Data Contracts

All components use shared Pydantic models for consistent data structures.

| Model | Purpose |
|-------|---------|
| `Finding` | Standard finding schema all modules output |
| `ModuleInput` | What the agent sends to a module |
| `ModuleOutput` | What a module returns (findings + summary) |
| `ModuleRegistry` | Module metadata from Cosmos DB |
| `SubscriptionOwner` | Owner contact info |
| `FindingHistory` | Historical finding record |
| `ExecutionLog` | Audit log entry |

### Enums

| Enum | Values |
|------|--------|
| `FindingCategory` | abandoned, overprovisioned, idle, misconfigured, opportunity |
| `Severity` | critical, high, medium, low, informational |
| `ConfidenceLevel` | certain, high, medium, low, uncertain |
| `ModuleStatus` | active, disabled, deprecated, development |

### Data Contract Flow

```
┌──────────────┐      ┌───────────────────┐      ┌──────────────────┐
│   AI Agent   │      │  Detection Module │      │   Notification   │
│              │      │                   │      │      Layer       │
└──────┬───────┘      └─────────┬─────────┘      └────────┬─────────┘
       │                        │                         │
       │    ModuleInput         │                         │
       │  ┌─────────────────┐   │                         │
       ├─►│ executionId     │───┤                         │
       │  │ subscriptionIds │   │                         │
       │  │ configuration   │   │                         │
       │  │ dryRun          │   │                         │
       │  └─────────────────┘   │                         │
       │                        │                         │
       │                        ▼                         │
       │               ┌─────────────────┐                │
       │               │    Finding      │                │
       │               │  ┌───────────┐  │                │
       │               │  │findingId  │  │                │
       │               │  │resourceId │  │                │
       │               │  │severity   │  │                │
       │               │  │confidence │  │                │
       │               │  │cost       │  │                │
       │               │  └───────────┘  │                │
       │               └────────┬────────┘                │
       │                        │                         │
       │    ModuleOutput        │                         │
       │  ┌─────────────────┐   │                         │
       │◄─┤ moduleId        │◄──┤                         │
       │  │ findings[]      │   │                         │
       │  │ summary         │───┼────────────────────────►│
       │  │ errors          │   │   SubscriptionOwner     │
       │  └─────────────────┘   │  ┌─────────────────┐    │
       │                        │  │ ownerEmail      │───►│
       │                        │  │ subscriptionId  │    │
       │                        │  └─────────────────┘    │
       ▼                        ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Cosmos DB                               │
│  ExecutionLog    FindingHistory    ModuleRegistry    Owners     │
└─────────────────────────────────────────────────────────────────┘
```

### Module Configuration

The `ModuleRegistry.configuration` field is `dict[str, Any]` - opaque to the shared library. Each module defines its own configuration schema:

```python
# Abandoned Resources module config
class AbandonedResourcesConfig(BaseModel):
    resource_types: list[str]
    minimum_orphan_age_days: int = 7
    confidence_thresholds: ConfidenceThresholds

# Future: Overprovisioned VMs module config
class OverprovisionedVMsConfig(BaseModel):
    cpu_threshold_percent: float = 20.0
    memory_threshold_percent: float = 20.0
    observation_period_days: int = 14
```

---

## Confidence Utilities

### Generic Functions

```python
from shared import get_confidence_level, clamp_score

level = get_confidence_level(85)  # Returns ConfidenceLevel.HIGH
score = clamp_score(120)          # Returns 100 (clamped to valid range)
```

| Function | Purpose |
|----------|---------|
| `get_confidence_level(score)` | Convert 0-100 score to level enum |
| `clamp_score(score)` | Ensure score is within 0-100 |
| `should_report_finding(score, threshold)` | Check if finding meets minimum |
| `get_confidence_thresholds()` | Get threshold values |

### Thresholds

| Level | Score Range |
|-------|-------------|
| Certain | 95-100 |
| High | 75-94 |
| Medium | 50-74 |
| Low | 25-49 |
| Uncertain | 0-24 |

### Module-Specific Scoring

Each module implements its own confidence calculation logic:

```python
# Abandoned resources: based on orphan duration, name patterns, tags
from detection_layer.abandoned_resources import calculate_abandoned_confidence

score = calculate_abandoned_confidence(
    resource_name="temp-disk-01",
    orphaned_date=datetime(2025, 10, 1),
    tags={"Environment": "Dev"},
    resource_group_name="rg-sandbox"
)  # Returns ~85 (high confidence)
```

### Confidence Scoring Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                     Module-Specific Scoring                                │
│                (detection_layer/abandoned_resources/confidence.py)         │
│                                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Resource   │  │   Orphan    │  │    Name     │  │    Tags     │        │
│  │   Info      │  │  Duration   │  │  Patterns   │  │   Check     │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│         │   base=50      │  +30 (>90d)    │  +15 (temp-)   │  -20 (prod)   │
│         │                │  +20 (30-90d)  │  -15 (prod-)   │  -20 (keep)   │
│         │                │  +10 (14-30d)  │                │               │
│         │                │  -20 (<3d)     │                │               │
│         │                │                │                │               │
│         └────────────────┴────────────────┴────────────────┘               │
│                                    │                                       │
│                                    ▼                                       │
│                          ┌─────────────────┐                               │
│                          │  Raw Score: 85  │                               │
│                          └────────┬────────┘                               │
└───────────────────────────────────┼────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Generic Utilities                                    │
│                     (shared/confidence.py)                                  │
│                                                                             │
│    ┌────────────────┐         ┌─────────────────────────────────────┐       │
│    │ clamp_score()  │────────►│  Score: 85  (clamped to 0-100)      │       │
│    └────────────────┘         └─────────────────┬───────────────────┘       │
│                                                 │                           │
│    ┌─────────────────────┐                      ▼                           │
│    │ get_confidence_     │    ┌─────────────────────────────────────┐       │
│    │ level()             │───►│  Level: HIGH  (75-94 range)         │       │
│    └─────────────────────┘    └─────────────────────────────────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Calculator Utilities

### Generic Functions

```python
from shared import classify_severity, format_cost, calculate_total_savings

severity = classify_severity(150.0)  # Returns Severity.HIGH
formatted = format_cost(1234.56)     # Returns "$1,234.56"
total = calculate_total_savings(findings)  # Sums estimatedMonthlyCost
```

| Function | Purpose |
|----------|---------|
| `classify_severity(cost)` | Map cost to severity level |
| `get_severity_thresholds()` | Get threshold values |
| `get_severity_priority(severity)` | For sorting (1=critical, 5=info) |
| `calculate_total_savings(findings)` | Sum all finding costs |
| `summarize_by_severity(findings)` | Count by severity |
| `summarize_by_resource_type(findings)` | Count by type |
| `format_cost(amount, currency)` | Format for display |

### Severity Thresholds

| Severity | Monthly Cost |
|----------|--------------|
| Critical | >$1,000 |
| High | $100-$1,000 |
| Medium | $10-$100 |
| Low | $1-$10 |
| Informational | <$1 |

### Module-Specific Estimation

Each module implements its own cost estimation logic:

```python
# Abandoned resources: lookup table by resource type and SKU
from detection_layer.abandoned_resources import estimate_abandoned_resource_cost

cost = estimate_abandoned_resource_cost(
    resource_type="microsoft.compute/disks",
    sku="Premium_LRS",
    size_gb=256
)  # Returns 38.40 (256 * $0.15/GB)
```

### Cost Calculation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Module-Specific Estimation                              │
│              (detection_layer/abandoned_resources/cost_calculator.py)       │
│                                                                             │
│   Resource Graph Result                                                     │
│   ┌─────────────────────────────────────────────────┐                       │
│   │ type: microsoft.compute/disks                   │                       │
│   │ sku: Premium_LRS                                │                       │
│   │ diskSizeGB: 256                                 │                       │
│   └──────────────────────┬──────────────────────────┘                       │
│                          │                                                  │
│                          ▼                                                  │
│   ┌─────────────────────────────────────────────────┐                       │
│   │        ABANDONED_RESOURCE_COSTS                 │                       │
│   │  ┌────────────────────────────────────────┐    │                        │
│   │  │ microsoft.compute/disks:               │    │                        │
│   │  │   Premium_LRS: $0.15/GB/month          │◄───┤                        │
│   │  │   Standard_LRS: $0.05/GB/month         │    │                        │
│   │  │   StandardSSD_LRS: $0.075/GB/month     │    │                        │
│   │  └────────────────────────────────────────┘    │                        │
│   └──────────────────────┬──────────────────────────┘                       │
│                          │                                                  │
│                          ▼                                                  │
│            ┌──────────────────────────┐                                     │
│            │  $0.15 × 256 = $38.40    │                                     │
│            └────────────┬─────────────┘                                     │
└─────────────────────────┼───────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Generic Utilities                                    │
│                    (shared/cost_calculator.py)                              │
│                                                                             │
│    ┌───────────────────┐      ┌──────────────────────────────────────┐      │
│    │ classify_severity │─────►│  $38.40 → MEDIUM ($10-$100 range)    │      │
│    └───────────────────┘      └──────────────────────────────────────┘      │
│                                                                             │
│    ┌───────────────────┐      ┌──────────────────────────────────────┐      │
│    │ format_cost       │─────►│  "$38.40"                            │      │
│    └───────────────────┘      └──────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

                              Multiple Findings
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        Aggregation Utilities                               │
│                                                                            │
│  ┌──────────────────────────┐    ┌───────────────────────────────────────┐ │
│  │ calculate_total_savings  │───►│ Sum: $2,847.50/month                  │ │
│  └──────────────────────────┘    └───────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────┐    ┌───────────────────────────────────────┐ │
│  │ summarize_by_severity    │───►│ {critical: 2, high: 5, medium: 12}    │ │
│  └──────────────────────────┘    └───────────────────────────────────────┘ │
│                                                                            │
│  ┌──────────────────────────┐    ┌───────────────────────────────────────┐ │
│  │ summarize_by_resource_   │───►│ {disks: 8, publicIPs: 6, LBs: 3}      │ │
│  │ type                     │    └───────────────────────────────────────┘ │
│  └──────────────────────────┘                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Adding a New Module

To add a new detection module (e.g., "Overprovisioned VMs"):

### 1. Create Module Structure

```
detection_layer/
└── overprovisioned_vms/
    ├── __init__.py
    ├── config.py           # OverprovisionedVMsConfig
    ├── queries.py          # KQL for VMs with metrics
    ├── confidence.py       # Based on utilization patterns
    ├── cost_calculator.py  # Current vs recommended SKU cost
    └── detector.py         # Main detection logic
```

### 2. Define Configuration

```python
# config.py
class OverprovisionedVMsConfig(BaseModel):
    cpu_threshold_percent: float = 20.0
    memory_threshold_percent: float = 20.0
    observation_period_days: int = 14
```

### 3. Implement Queries

```python
# queries.py
def query_all_vms() -> str:
    return """
    Resources
    | where type =~ 'microsoft.compute/virtualmachines'
    | project id, name, subscriptionId, vmSize = properties.hardwareProfile.vmSize
    """
```

### 4. Implement Confidence Scoring

```python
# confidence.py
def calculate_overprovisioned_confidence(
    avg_cpu: float,
    avg_memory: float,
    observation_days: int
) -> int:
    # Different logic than abandoned resources
    ...
```

### 5. Implement Cost Estimation

```python
# cost_calculator.py
VM_SKU_COSTS = {
    "Standard_D2s_v3": 70.08,
    "Standard_D4s_v3": 140.16,
    ...
}

def estimate_rightsizing_savings(current_sku: str, recommended_sku: str) -> float:
    return VM_SKU_COSTS[current_sku] - VM_SKU_COSTS[recommended_sku]
```

### 6. Use Shared Library

```python
# detector.py
from shared import ResourceGraphClient, Finding, classify_severity
from detection_layer.overprovisioned_vms import (
    query_all_vms,
    calculate_overprovisioned_confidence,
    estimate_rightsizing_savings,
)

def detect(subscription_ids: list[str]) -> list[Finding]:
    client = ResourceGraphClient()  # Generic client
    vms = client.query(query_all_vms(), subscription_ids)

    # Module-specific processing...
```

### 7. Register in Cosmos DB

```json
{
  "id": "overprovisioned-vms",
  "moduleId": "overprovisioned-vms",
  "moduleName": "Overprovisioned VMs Detector",
  "enabled": true,
  "configuration": {
    "cpuThresholdPercent": 20.0,
    "memoryThresholdPercent": 20.0,
    "observationPeriodDays": 14
  }
}
```
