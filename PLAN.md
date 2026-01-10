# Azure Optimization Agent - Implementation Plan

## Overview

Implement a three-layer agentic solution that identifies cost optimization opportunities across Azure subscriptions and delivers personalized monthly recommendations to subscription owners.

**Architecture:** Detection Layer → Data Layer → Notification Layer (orchestrated by Azure AI Foundry Agent with GPT-4o)

---

## Directory Structure

```
OptimizationAgent/
├── infra/                          # Bicep infrastructure
│   ├── main.bicep                  # All resources in single file
│   └── main.bicepparam             # Parameters file
├── src/
│   ├── functions/                  # Azure Functions (Python)
│   │   ├── function_app.py
│   │   ├── requirements.txt
│   │   ├── shared/
│   │   │   ├── models.py           # Pydantic data contracts
│   │   │   ├── cosmos_client.py    # Cosmos DB wrapper
│   │   │   ├── resource_graph.py   # Resource Graph helper
│   │   │   ├── confidence.py       # Confidence scoring
│   │   │   └── cost_calculator.py  # Cost estimation
│   │   ├── data_layer/
│   │   │   ├── get_module_registry.py
│   │   │   ├── save_findings.py
│   │   │   ├── get_findings_history.py
│   │   │   ├── get_findings_trends.py
│   │   │   └── get_subscription_owners.py
│   │   └── detection_layer/
│   │       └── abandoned_resources/
│   │           ├── detector.py     # Main detection logic
│   │           ├── queries.py      # KQL queries
│   │           ├── config.py       # Module configuration
│   │           ├── confidence.py   # Module-specific confidence
│   │           └── cost_calculator.py
│   ├── agent/
│   │   ├── system_prompt.txt
│   │   ├── tool_definitions.json
│   │   └── run_agent.py
│   └── logic-apps/
│       └── send-optimization-email/
├── tests/
│   ├── unit/
│   └── integration/
└── data/
    └── seed/                       # Initial Cosmos DB data
```

---

## Implementation Phases

### Phase 1: Infrastructure (First)

| File | Purpose |
|------|---------|
| `infra/main.bicep` | All infrastructure resources (Storage, Log Analytics, App Insights, Cosmos DB, Function App, Logic App, RBAC, NSP) |
| `infra/main.bicepparam` | Deployment parameters (environment, location, naming) |

**Resources in main.bicep:**
- Storage Account (for Function App, shared key access disabled)
- Log Analytics Workspace (30-day retention)
- Application Insights (connected to Log Analytics)
- Cosmos DB Account (serverless) with 4 containers
- App Service Plan (consumption, Linux)
- Function App with system-assigned managed identity (Python 3.11)
- Logic App for email notifications (with HTTP trigger schema)
- RBAC assignments:
  - Function App → Cosmos DB Data Contributor
  - Function App → Storage Blob Data Owner
  - Function App → Storage Account Contributor
  - Function App → Storage Queue Data Contributor
- Network Security Perimeter with Storage and Cosmos DB associations (Learning mode)

**Cosmos DB Containers:**
- `module-registry` (partition: `/moduleId`)
- `findings-history` (partition: `/subscriptionId`, TTL: 365 days)
- `subscription-owners` (partition: `/subscriptionId`)
- `execution-logs` (partition: `/executionId`, TTL: 90 days)

### Phase 2: Shared Library

| File | Purpose |
|------|---------|
| `src/functions/shared/models.py` | Pydantic models: `Finding`, `ModuleInput`, `ModuleOutput`, `ModuleRegistry` |
| `src/functions/shared/cosmos_client.py` | Cosmos DB client with managed identity auth |
| `src/functions/shared/resource_graph.py` | Azure Resource Graph query helper |
| `src/functions/shared/confidence.py` | Confidence scoring (duration, naming patterns, tags) |
| `src/functions/shared/cost_calculator.py` | Cost estimation and severity classification |

### Phase 3: Data Layer Functions

| File | Endpoint | Purpose |
|------|----------|---------|
| `data_layer/get_module_registry.py` | `GET /api/get-module-registry` | List enabled modules |
| `data_layer/save_findings.py` | `POST /api/save-findings` | Store findings |
| `data_layer/get_findings_history.py` | `GET /api/get-findings-history` | Query historical findings |
| `data_layer/get_findings_trends.py` | `GET /api/get-findings-trends` | Month-over-month trends |
| `data_layer/get_subscription_owners.py` | `POST /api/get-subscription-owners` | Owner lookup |

### Phase 4: Detection Layer

| File | Purpose |
|------|---------|
| `detection_layer/abandoned_resources/detector.py` | Main module implementing interface contract |
| `detection_layer/abandoned_resources/queries.py` | KQL queries for 8 resource types |
| `detection_layer/abandoned_resources/config.py` | Module configuration schema |
| `detection_layer/abandoned_resources/confidence.py` | Module-specific confidence scoring |
| `detection_layer/abandoned_resources/cost_calculator.py` | Module-specific cost estimation |

**Supported Resource Types:**
- Unattached managed disks
- Unused public IPs (Standard SKU)
- Empty load balancers
- Orphaned NAT gateways
- Empty SQL elastic pools
- Unused VNet gateways
- Orphaned DDoS plans
- Disconnected private endpoints

**Module Interface Contract:**
```python
# Input
{"executionId": "...", "subscriptionIds": ["sub-1"] or ["all"], "dryRun": false}

# Output
{"moduleId": "abandoned-resources", "status": "success", "findings": [...], "summary": {...}}
```

### Phase 5: AI Agent Configuration

| File | Purpose |
|------|---------|
| `src/agent/system_prompt.txt` | Agent instructions for analysis and recommendations |
| `src/agent/tool_definitions.json` | Tool schemas for Function and Logic App endpoints |
| `src/agent/run_agent.py` | Orchestration script (can be timer-triggered) |

### Phase 6: Notification Layer

| File | Purpose |
|------|---------|
| `src/logic-apps/send-optimization-email/workflow.json` | Logic App workflow definition |
| `src/logic-apps/templates/email-template.html` | HTML email template |

---

## Critical Files

1. **`infra/main.bicep`** - All infrastructure resources in single deployment
2. **`infra/main.bicepparam`** - Deployment parameters
3. **`src/functions/shared/models.py`** - Data contracts used by every component
4. **`src/functions/detection_layer/abandoned_resources.py`** - Core detection logic
5. **`src/functions/shared/cosmos_client.py`** - Database access layer
6. **`src/agent/system_prompt.txt`** - AI agent behavior definition

---

## Key Implementation Details

### Confidence Scoring
| Level | Score | Criteria |
|-------|-------|----------|
| Certain | 95-100% | Orphaned 90+ days |
| High | 75-94% | Orphaned 30-90 days |
| Medium | 50-74% | Orphaned 7-30 days |
| Low | 25-49% | Orphaned <7 days |

### Severity Classification
| Severity | Monthly Cost |
|----------|--------------|
| Critical | >$1,000 |
| High | $100-$1,000 |
| Medium | $10-$100 |
| Low | $1-$10 |

### Security
- System-Assigned Managed Identity for Function App and Logic App
- Storage Account with shared key access disabled (managed identity only)
- Network Security Perimeter protecting Storage and Cosmos DB (Learning mode initially)
- RBAC assignments deployed via Bicep:
  - Function App → Cosmos DB Data Contributor
  - Function App → Storage Blob Data Owner, Account Contributor, Queue Data Contributor
- Cross-subscription access via Management Group RBAC (Reader + Cost Management Reader)
- No secrets in code - DefaultAzureCredential for auth

---

## Verification Plan

### Unit Tests
```bash
pytest tests/unit/test_confidence_scoring.py
pytest tests/unit/test_cost_calculator.py
pytest tests/unit/test_models.py
```

### Integration Tests
```bash
# Deploy infrastructure
az deployment group create -g rg-optimization-agent -f infra/main.bicep -p infra/main.bicepparam

# Seed test data
python infra/scripts/seed-data.py

# Test function endpoints
pytest tests/integration/test_function_endpoints.py
```

### End-to-End Test
1. Deploy all infrastructure to test environment
2. Seed `module-registry` and `subscription-owners` with test data
3. Run agent with `dryRun: true` to validate detection
4. Run agent against test subscriptions (2-3 with known orphaned resources)
5. Verify:
   - Findings stored in `findings-history`
   - Email received at test address
   - Summary statistics match expected counts

### Manual Verification
```bash
# Check Cosmos DB data
az cosmosdb sql container list --account-name <account> --database-name optimization-agent

# Check Function App logs
az webapp log tail --name <function-app> --resource-group <rg>

# Trigger test run
curl -X POST https://<function-app>.azurewebsites.net/api/abandoned-resources \
  -H "Content-Type: application/json" \
  -d '{"executionId": "test-001", "subscriptionIds": ["<test-sub>"], "dryRun": true}'
```

---

## Dependencies

```
# src/functions/requirements.txt
azure-functions>=1.17.0
azure-cosmos>=4.5.0
azure-identity>=1.15.0
azure-mgmt-resourcegraph>=8.0.0
pydantic>=2.5.0
```
