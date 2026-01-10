# Module Registration

Detection modules must be registered in the Cosmos DB `module-registry` container before the AI agent can discover and execute them.

## Registry Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Document ID (same as moduleId) |
| `moduleId` | string | Yes | Unique module identifier |
| `moduleName` | string | Yes | Human-readable display name |
| `version` | string | No | Semantic version (default: "1.0.0") |
| `enabled` | boolean | Yes | Whether agent should execute this module |
| `status` | enum | No | Lifecycle status (see below) |
| `category` | string | No | Module category (default: "cost-optimization") |
| `description` | string | No | What the module detects |
| `functionApp` | string | No | Azure Function App name |
| `functionName` | string | No | Function name within the app |
| `schedule` | string | No | Execution frequency (default: "monthly") |
| `outputSchema` | string | No | Output format version |
| `configuration` | object | No | Module-specific settings |
| `createdDate` | datetime | No | When module was registered |
| `lastModifiedDate` | datetime | No | Last configuration change |
| `lastExecutionDate` | datetime | No | Last successful run |

### Status Values

| Status | Description |
|--------|-------------|
| `active` | Module is production-ready |
| `development` | Module is being developed/tested |
| `disabled` | Temporarily disabled |
| `deprecated` | Scheduled for removal |

---

## Registering a New Module

### Option 1: Seed Data File

Add to `data/seed/module-registry.json`:

```json
{
  "id": "overprovisioned-vms",
  "moduleId": "overprovisioned-vms",
  "moduleName": "Overprovisioned VMs Detector",
  "version": "1.0.0",
  "enabled": true,
  "status": "active",
  "category": "cost-optimization",
  "description": "Detects VMs with consistently low CPU and memory utilization that could be rightsized.",
  "functionApp": "func-optimization-agent",
  "functionName": "overprovisioned-vms",
  "schedule": "monthly",
  "outputSchema": "v1-standard-findings",
  "configuration": {
    "cpuThresholdPercent": 20.0,
    "memoryThresholdPercent": 20.0,
    "observationPeriodDays": 14,
    "excludedVmSizes": ["Standard_B1s", "Standard_B1ms"]
  },
  "createdDate": "2026-01-10T00:00:00Z",
  "lastModifiedDate": "2026-01-10T00:00:00Z",
  "lastExecutionDate": null
}
```

Then run the seed script:

```bash
python scripts/test_data_layer_live.py --seed
```

### Option 2: Direct Cosmos DB Insert

Using Azure CLI:

```bash
az cosmosdb sql container item create \
  --account-name <cosmos-account> \
  --database-name optimization-agent \
  --container-name module-registry \
  --partition-key-path "/moduleId" \
  --body '{
    "id": "overprovisioned-vms",
    "moduleId": "overprovisioned-vms",
    "moduleName": "Overprovisioned VMs Detector",
    "enabled": true,
    "status": "active",
    "configuration": {}
  }'
```

### Option 3: Python Script

```python
from shared import CosmosClient

client = CosmosClient()
container = client._get_container("module-registry")

module = {
    "id": "overprovisioned-vms",
    "moduleId": "overprovisioned-vms",
    "moduleName": "Overprovisioned VMs Detector",
    "enabled": True,
    "status": "active",
    "configuration": {
        "cpuThresholdPercent": 20.0,
        "memoryThresholdPercent": 20.0
    }
}

container.upsert_item(module)
```

---

## Configuration Examples

### Abandoned Resources Module

```json
{
  "configuration": {
    "resourceTypes": [
      "microsoft.compute/disks",
      "microsoft.network/publicipaddresses",
      "microsoft.network/loadbalancers",
      "microsoft.network/natgateways",
      "microsoft.sql/servers/elasticpools",
      "microsoft.network/virtualnetworkgateways",
      "microsoft.network/ddosprotectionplans",
      "microsoft.network/privateendpoints"
    ],
    "minimumOrphanAgeDays": 7,
    "includeZeroCost": false,
    "confidenceThresholds": {
      "certain": 95,
      "high": 75,
      "medium": 50,
      "low": 25
    }
  }
}
```

### Overprovisioned VMs Module (Example)

```json
{
  "configuration": {
    "cpuThresholdPercent": 20.0,
    "memoryThresholdPercent": 20.0,
    "observationPeriodDays": 14,
    "excludedVmSizes": ["Standard_B1s", "Standard_B1ms"],
    "excludedResourceGroups": ["rg-build-agents", "rg-ephemeral"],
    "minimumRunningHours": 168
  }
}
```

### Idle Databases Module (Example)

```json
{
  "configuration": {
    "connectionThresholdDays": 30,
    "dtuThresholdPercent": 5.0,
    "excludedDatabases": ["master", "tempdb"],
    "includePaasOnly": true
  }
}
```

---

## Enabling/Disabling Modules

To temporarily disable a module without removing it:

```python
from shared import CosmosClient

client = CosmosClient()
container = client._get_container("module-registry")

# Disable
container.upsert_item({
    "id": "abandoned-resources",
    "moduleId": "abandoned-resources",
    "enabled": False,
    # ... other fields
})
```

The AI agent only executes modules where `enabled: true`.

---

## Verifying Registration

Query the registry to confirm your module is registered:

```bash
# Using the data layer API
curl -X GET "https://<function-app>.azurewebsites.net/api/get-module-registry?includeDisabled=true"
```

Or via the test script:

```bash
python scripts/test_data_layer_live.py
```

Expected output:

```
TEST: get_module_registry
------------------------------------------------------------
Enabled modules: 2
  - abandoned-resources: Abandoned Resources Detector
  - overprovisioned-vms: Overprovisioned VMs Detector
All modules: 2
```

---

## Module Discovery Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AI Agent (GPT-4o)                                │
│                                                                             │
│  1. "Get enabled modules"                                                   │
│         │                                                                   │
└─────────┼───────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GET /api/get-module-registry                             │
│                                                                             │
│  SELECT * FROM c WHERE c.enabled = true AND c.status = 'active'             │
│                                                                             │
└─────────┬───────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Cosmos DB Response                                  │
│                                                                             │
│  {                                                                          │
│    "modules": [                                                             │
│      { "moduleId": "abandoned-resources", "functionName": "..." },          │
│      { "moduleId": "overprovisioned-vms", "functionName": "..." }           │
│    ]                                                                        │
│  }                                                                          │
└─────────┬───────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AI Agent (GPT-4o)                                │
│                                                                             │
│  2. For each module: "Run {moduleId} detection"                             │
│         │                                                                   │
│         ├──► POST /api/abandoned-resources                                  │
│         └──► POST /api/overprovisioned-vms                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
