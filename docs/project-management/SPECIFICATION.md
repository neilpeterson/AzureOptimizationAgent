# Azure Optimization Agent

## Solution Overview

Managing Azure costs across many subscriptions is complex. Service teams often leave orphaned resources (unattached disks, unused public IPs, empty load balancers) that accumulate cost without providing value. Manual identification is time-consuming and error-prone.

The **Azure Optimization Agent** is an agentic solution that automatically identifies cost optimization opportunities, detects spending trends, and delivers personalized monthly recommendations to subscription owners.

The solution automates cost optimization through:

1. **Detection:** Modular functions scan all subscriptions for optimization opportunities
2. **Analysis:** AI agent synthesizes findings, prioritizes by impact, and identifies trends
3. **Notification:** Monthly emails to subscription owners with actionable recommendations
4. **Evolution:** Architecture supports future autonomous remediation capabilities


### Key Design Principles

| Principle | Description |
|-----------|-------------|
| **Modularity** | Plugin-based architecture allowing easy addition/removal of optimization modules |
| **Azure-Native** | Maximize use of native Azure services; minimize custom code |
| **AI-Powered** | Leverage Azure AI Foundry Agent Service for intelligent synthesis and recommendations |
| **Scalable** | Handles large fleets of subscriptions and management groups |
| **Multi-Agent Ready** | Architecture supports future evolution to autonomous optimization actions |


### Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Orchestration | Azure AI Foundry Agent Service | Central AI agent for analysis and recommendations |
| Compute | Azure Functions | Modular detection and data retrieval |
| Workflow | Azure Logic Apps | Email notifications |
| Data | Azure Cosmos DB | Module registry, findings history, owner mapping |
| Query | Azure Resource Graph | Cross-subscription resource discovery |

---

## Architecture

The architecture consists of three distinct layers, each implemented as Azure Functions or Logic Apps and orchestrated by the AI Agent:

| Layer | Purpose | Implementation |
|-------|---------|----------------|
| **Detection Layer** | Scans Azure subscriptions to identify optimization opportunities (e.g., abandoned resources, overprovisioned VMs). Each module queries Azure Resource Graph and returns standardized findings. | Azure Functions |
| **Data Layer** | Manages persistent data operations—retrieving subscription owners, storing findings history for trend analysis, and maintaining the module registry. Does not query Azure resources directly. | Azure Functions + Cosmos DB |
| **Notification Layer** | Composes and delivers personalized email reports to subscription owners with actionable recommendations. | Logic Apps |

The **Detection Layer** is externally focused—it queries Azure Resource Graph across all configured subscriptions and management groups to discover resource state. The **Data Layer** is internally focused—it manages the solution's own data (who owns what subscription, what was found previously, which modules are enabled).


```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AZURE AI FOUNDRY PROJECT                           │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                      Azure Optimization Agent                             │  │
│  │                                                                           │  │
│  │  Model: GPT-4o                                                            │  │
│  │  Role: Synthesize findings, prioritize, generate recommendations          │  │
│  │  Tools: Azure Functions (detection), Logic Apps (email)                   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
              ▼                         ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   DETECTION LAYER    │  │    DATA LAYER        │  │  NOTIFICATION LAYER  │
│   (Azure Functions)  │  │   (Azure Functions)  │  │   (Logic Apps)       │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│                      │  │                      │  │                      │
│ ┌──────────────────┐ │  │ ┌──────────────────┐ │  │ ┌──────────────────┐ │
│ │ Abandoned        │ │  │ │ GetSubscription  │ │  │ │ SendOptimization │ │
│ │ Resources Module │ │  │ │ Owners           │ │  │ │ Email            │ │
│ └──────────────────┘ │  │ └──────────────────┘ │  │ └──────────────────┘ │
│                      │  │                      │  │                      │
│ ┌──────────────────┐ │  │ ┌──────────────────┐ │  │                      │
│ │ [Future]         │ │  │ │ StoreTrendData   │ │  │                      │
│ │ Overprovisioned  │ │  │ └──────────────────┘ │  │                      │
│ │ VMs Module       │ │  │                      │  │                      │
│ └──────────────────┘ │  │ ┌──────────────────┐ │  │                      │
│                      │  │ │ GetModuleRegistry│ │  │                      │
│ ┌──────────────────┐ │  │ └──────────────────┘ │  │                      │
│ │ [Future]         │ │  │                      │  │                      │
│ │ Storage          │ │  │                      │  │                      │
│ │ Optimization     │ │  │                      │  │                      │
│ └──────────────────┘ │  │                      │  │                      │
│                      │  │                      │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
              │                         │
              ▼                         ▼
┌──────────────────────┐  ┌──────────────────────────────────────────────────┐
│  Azure Resource      │  │              Azure Cosmos DB                     │
│  Graph               │  │  ┌────────────┬────────────┬────────────┐        │
│  (Cross-subscription │  │  │ module-    │ findings-  │ subscription│       │
│   queries)           │  │  │ registry   │ history    │ -owners     │       │
└──────────────────────┘  │  └────────────┴────────────┴────────────┘        │
                          └──────────────────────────────────────────────────┘
```

### Component Inventory

| Component | Azure Service | SKU/Tier | Purpose |
|-----------|--------------|----------|---------|
| AI Agent | Azure AI Foundry Agent Service | Standard | Orchestration and intelligence |
| AI Model | Azure OpenAI | GPT-4o | Analysis and recommendation generation |
| Detection Functions | Azure Functions | Consumption | Module execution |
| Data Functions | Azure Functions | Consumption | Data retrieval and storage |
| Module Registry | Cosmos DB | Serverless | Module metadata and configuration |
| Findings History | Cosmos DB | Serverless | Historical findings for trend analysis |
| Owner Mapping | Cosmos DB | Serverless | Subscription-to-owner mapping |
| Email Workflow | Logic Apps | Consumption | Email composition and delivery |
| Resource Queries | Azure Resource Graph | N/A (free) | Cross-subscription resource discovery |

---

## Modularity Framework

A core design principle of the Azure Optimization Agent is **modularity**. Optimization capabilities are implemented as independent, pluggable modules that can be added, removed, or modified without affecting the core system.

### Module Architecture

```json
{
  "moduleId": "abandoned-resources",
  "moduleName": "Abandoned Resources Detector",
  "version": "1.0.0",
  "enabled": true,
  "functionEndpoint": "https://func-optimization.azurewebsites.net/api/...",
  "schedule": "monthly",
  "category": "cost-optimization",
  "description": "Detects orphaned resources that incur unnecessary cost",
  "outputSchema": "v1-standard-findings",
  "configuration": {
    "resourceTypes": ["disks", "publicIPs", "loadBalancers", ...]
  }
}
```

### Module Lifecycle

| State | Description | Behavior |
|-------|-------------|----------|
| **Enabled** | Module is active and runs on schedule | Included in optimization sweep |
| **Disabled** | Module exists but does not execute | Skipped during sweep; findings retained |
| **Deprecated** | Module scheduled for removal | Warning logged; still executes if enabled |
| **Development** | Module in testing phase | Only runs in dev/test environments |

### Module Interface Contract

All modules must implement the following interface:

```json
// Input:
{
  "executionId": "exec-2026-01-08-001",
  "subscriptionIds": ["sub-1", "sub-2", ...],  // or "all"
  "configuration": { ... },  // module-specific config
  "dryRun": false
}

// Output:
{
  "moduleId": "abandoned-resources",
  "executionId": "exec-2026-01-08-001",
  "executionTime": "2026-01-08T10:30:00Z",
  "status": "success",
  "findings": [ ... ],  // standardized finding objects
  "summary": { ... },   // aggregated statistics
  "errors": [ ... ]     // any non-fatal errors encountered
}
```

### Adding a New Module

To add a new optimization module:

1. **Create Azure Function:** Implement detection logic following the module interface contract
2. **Register in Cosmos DB:** Add module metadata to the `module-registry` container
3. **Configure Agent:** Update agent system prompt to understand new finding types (if needed)
4. **Test:** Run module in `dryRun` mode against test subscriptions
5. **Enable:** Set `enabled: true` in registry

No changes to core orchestration, email templates, or other modules required.

### Planned Modules Roadmap

| Module | Description | Priority | Target Release |
|--------|-------------|----------|----------------|
| Abandoned Resources | Detect orphaned resources with cost | P0 | v1.0 |
| Overprovisioned VMs | VMs with low CPU/memory utilization | P1 | v1.1 |
| Overprovisioned Storage | Storage accounts with low utilization | P1 | v1.1 |
| Reserved Instance Opportunities | Workloads suitable for RI | P2 | v1.2 |
| Idle Resources | Resources with no activity | P2 | v1.2 |
| Right-sizing Recommendations | Azure Advisor integration | P2 | v1.3 |

---

## Module Specification: Abandoned Resources

### Overview

The Abandoned Resources module detects orphaned Azure resources that incur cost but provide no value. These resources typically result from VM deletions where associated resources (disks, NICs, IPs) were not cleaned up.

### Detection Scope

The module detects the following resource types that **incur cost when orphaned**:

| Resource Type | Detection Logic | Typical Monthly Cost | Azure Resource Graph Query |
|---------------|-----------------|---------------------|---------------------------|
| Managed Disks | `diskState == 'Unattached'` | $1.50 - $150+ | See Appendix A.1 |
| Public IP (Standard SKU) | `ipConfiguration == null` and `sku.name == 'Standard'` | ~$3.65 | See Appendix A.2 |
| Load Balancer (Standard) | No backend pool instances | ~$18 + data | See Appendix A.3 |
| NAT Gateway | No subnet associations | ~$32 + data | See Appendix A.4 |
| SQL Elastic Pool | No databases in pool | Varies by tier | See Appendix A.5 |
| VNet Gateway | No connections configured | $27 - $350+ | See Appendix A.6 |
| DDoS Protection Plan | No VNets protected | ~$2,944 | See Appendix A.7 |
| Private Endpoint | Not connected to resource | ~$7.30 | See Appendix A.8 |

### Detection Flow

```
    ┌─────────────┐
    │   START     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────┐
    │ 1. Get module configuration from    │
    │    Cosmos DB registry               │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 2. Query Azure Resource Graph       │
    │    (all target subscriptions in     │
    │     single query per resource type) │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 3. For each orphaned resource:      │
    │    • Calculate estimated cost       │
    │    • Determine confidence score     │
    │    • Build finding object           │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 4. Group findings by subscription   │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 5. Store findings in Cosmos DB      │
    │    (findings-history container)     │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 6. Return standardized output       │
    │    to orchestrator                  │
    └──────────────────-──────────────────┘
```

### Cost Calculation

Each finding includes an estimated monthly cost based on:

| Resource Type | Cost Factors | Calculation Method |
|---------------|--------------|-------------------|
| Managed Disks | Size (GB), SKU tier, Region | Azure Pricing API or lookup table |
| Public IP | SKU (Basic=free, Standard=$3.65) | Fixed rate by SKU |
| Load Balancer | SKU, Rules count, Data processed | Base rate + estimated data |
| NAT Gateway | Hours provisioned, Data processed | Base rate ($32/mo) |
| SQL Elastic Pool | DTU/vCore tier, Storage | Tier-based lookup |
| VNet Gateway | SKU tier | Fixed rate by SKU |
| DDoS Protection Plan | Flat rate | $2,944/month |

### Confidence Scoring

Each finding includes a confidence score indicating certainty that the resource is truly abandoned:

| Confidence Level | Score Range | Criteria | Agent Behavior |
|------------------|-------------|----------|----------------|
| **Certain** | 95-100% | Resource orphaned 90+ days; no activity | Recommend immediate deletion |
| **High** | 75-94% | Resource orphaned 30-90 days | Recommend deletion after verification |
| **Medium** | 50-74% | Resource orphaned 7-30 days | Flag for review |
| **Low** | 25-49% | Resource orphaned <7 days | Informational only |

**Factors that increase confidence:**
- Longer duration in orphaned state
- Resource naming suggests temporary use (e.g., `test-*`, `temp-*`, `delete-*`)
- Resource group contains other orphaned resources
- No tags indicating intentional retention

**Factors that decrease confidence:**
- Resource tagged with `Environment: Production` or similar
- Resource in a resource group with recent activity
- Resource name suggests DR/backup purpose
- Recently created resource (<7 days old)

### Module Output Example

```json
{
  "moduleId": "abandoned-resources",
  "moduleName": "Abandoned Resources Detector",
  "version": "1.0.0",
  "executionId": "exec-2026-01-08-001",
  "executionTime": "2026-01-08T10:30:00Z",
  "status": "success",
  "subscriptionsScanned": 47,
  "findings": [
    {
      "findingId": "f-abc123",
      "subscriptionId": "sub-contoso-prod-01",
      "subscriptionName": "Contoso Production 01",
      "resourceId": "/subscriptions/sub-contoso-prod-01/resourceGroups/rg-legacy/providers/Microsoft.Compute/disks/disk-orphan-01",
      "resourceType": "microsoft.compute/disks",
      "resourceName": "disk-orphan-01",
      "resourceGroup": "rg-legacy",
      "location": "eastus",
      "category": "abandoned",
      "severity": "high",
      "confidenceScore": 92,
      "confidenceLevel": "high",
      "incursCost": true,
      "estimatedMonthlyCost": 45.00,
      "currency": "USD",
      "description": "Unattached managed disk with no associated VM",
      "detectionRule": "diskState == 'Unattached'",
      "firstDetectedDate": "2025-11-15T00:00:00Z",
      "metadata": {
        "diskSizeGB": 256,
        "diskSku": "Premium_LRS",
        "diskState": "Unattached",
        "timeCreated": "2025-06-01T14:30:00Z"
      }
    }
  ],
  "summary": {
    "totalFindings": 47,
    "totalEstimatedMonthlySavings": 1250.00,
    "findingsBySeverity": {
      "high": 12,
      "medium": 25,
      "low": 10
    },
    "findingsByResourceType": {
      "microsoft.compute/disks": 28,
      "microsoft.network/publicIPAddresses": 8,
      "microsoft.network/loadBalancers": 5,
      "microsoft.network/natGateways": 3,
      "microsoft.sql/servers/elasticPools": 2,
      "microsoft.network/ddosProtectionPlans": 1
    },
    "subscriptionsWithFindings": 35,
    "subscriptionsClean": 165
  },
  "errors": []
}
```

---

## Data Contracts

### Standard Finding Schema (v1)

All modules output findings using this standardized schema:

```json
{
  "$schema": "https://schemas.internal/finding-v1.json",
  "type": "object",
  "required": ["findingId", "subscriptionId", "resourceId", "resourceType", "category", "severity", "incursCost"],
  "properties": {
    "findingId": {
      "type": "string",
      "description": "Unique identifier for this finding"
    },
    "subscriptionId": {
      "type": "string",
      "description": "Azure subscription ID"
    },
    "subscriptionName": {
      "type": "string",
      "description": "Human-readable subscription name"
    },
    "resourceId": {
      "type": "string",
      "description": "Full Azure resource ID"
    },
    "resourceType": {
      "type": "string",
      "description": "Azure resource type (lowercase)"
    },
    "resourceName": {
      "type": "string",
      "description": "Resource name"
    },
    "resourceGroup": {
      "type": "string",
      "description": "Resource group name"
    },
    "location": {
      "type": "string",
      "description": "Azure region"
    },
    "category": {
      "type": "string",
      "enum": ["abandoned", "overprovisioned", "idle", "misconfigured", "opportunity"],
      "description": "Finding category"
    },
    "severity": {
      "type": "string",
      "enum": ["critical", "high", "medium", "low", "informational"],
      "description": "Finding severity based on cost impact"
    },
    "confidenceScore": {
      "type": "integer",
      "minimum": 0,
      "maximum": 100,
      "description": "Confidence that finding is accurate (0-100)"
    },
    "confidenceLevel": {
      "type": "string",
      "enum": ["certain", "high", "medium", "low", "uncertain"],
      "description": "Human-readable confidence level"
    },
    "incursCost": {
      "type": "boolean",
      "description": "Whether this resource incurs cost in current state"
    },
    "estimatedMonthlyCost": {
      "type": "number",
      "description": "Estimated monthly cost in specified currency"
    },
    "currency": {
      "type": "string",
      "default": "USD",
      "description": "Currency code for cost estimates"
    },
    "description": {
      "type": "string",
      "description": "Human-readable description of the finding"
    },
    "detectionRule": {
      "type": "string",
      "description": "Rule or query that detected this finding"
    },
    "firstDetectedDate": {
      "type": "string",
      "format": "date-time",
      "description": "When this finding was first detected"
    },
    "metadata": {
      "type": "object",
      "description": "Resource-type-specific additional data"
    }
  }
}
```

### Severity Classification

| Severity | Monthly Cost Impact | Examples |
|----------|--------------------| ---------|
| **Critical** | >$1,000 | Orphaned DDoS Protection Plan, unused VNet Gateway (VpnGw3) |
| **High** | $100 - $1,000 | Large orphaned Premium disks, unused SQL Elastic Pool |
| **Medium** | $10 - $100 | Standard orphaned disks, unused Standard Load Balancer |
| **Low** | $1 - $10 | Single orphaned Standard Public IP |
| **Informational** | $0 | Orphaned NIC (no cost, but housekeeping) |

---

## AI Agent Design

### Agent Configuration

| Property | Value |
|----------|-------|
| **Platform** | Azure AI Foundry Agent Service |
| **Model** | GPT-4o |
| **Agent Type** | Single agent with tool connections |
| **Memory** | Thread-based conversation state |

### Agent Tools

The agent connects to the following tools:

| Tool | Type | Purpose |
|------|------|---------|
| GetModuleRegistry | Azure Function | Retrieve enabled modules |
| ExecuteModule | Azure Function | Trigger module execution |
| GetSubscriptionOwners | Azure Function | Retrieve owner contact info |
| GetHistoricalFindings | Azure Function | Retrieve past findings for trends |
| SendOptimizationEmail | Logic App | Send formatted email |

### System Prompt

```
You are the Azure Optimization Agent, an expert in Azure cost optimization. Your role is to:

1. ANALYZE findings from optimization modules across all configured Azure subscriptions and management groups
2. PRIORITIZE findings by cost impact and confidence level
3. IDENTIFY TRENDS by comparing current findings to historical data
4. GENERATE actionable recommendations for subscription owners
5. COMPOSE clear, professional monthly reports

When processing findings:
- Focus on high-confidence, high-cost findings first
- Group related findings (e.g., multiple orphaned disks in same resource group)
- Distinguish between "immediate action" (high confidence) and "review recommended" (medium confidence)
- Note resources that are free but should be cleaned for hygiene
- Identify month-over-month trends (new findings, resolved findings, recurring patterns)

When generating recommendations:
- Be specific about the action needed (delete, resize, review)
- Include estimated savings in dollars
- Provide Azure Portal deep links where possible
- For medium-confidence findings, explain why verification is recommended
- Suggest process improvements if patterns indicate systemic issues

Tone: Professional, helpful, focused on enabling teams to save money without creating alert fatigue.
```

### Agent Processing Flow

```
    ┌─────────────┐
    │  Scheduled  │
    │  Trigger    │
    │  (Monthly)  │
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────┐
    │ 1. Get enabled modules from         │
    │    registry                         │
    │    → Tool: GetModuleRegistry        │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 2. Execute each enabled module      │
    │    → Tool: ExecuteModule            │
    │    (Abandoned Resources, etc.)      │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 3. Aggregate findings by            │
    │    subscription                     │
    │    (Agent reasoning)                │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 4. Get historical findings for      │
    │    trend analysis                   │
    │    → Tool: GetHistoricalFindings    │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 5. For each subscription with       │
    │    findings:                        │
    │    • Prioritize by impact           │
    │    • Identify trends                │
    │    • Generate recommendations       │
    │    (Agent reasoning)                │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 6. Get subscription owner           │
    │    → Tool: GetSubscriptionOwners    │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ 7. Send personalized email          │
    │    → Tool: SendOptimizationEmail    │
    │    (To owner + FinOps team CC)      │
    └─────────────────────────────────────┘
```

### Findings to Recommendations Transformation

The agent transforms raw module findings into actionable recommendations:

**Input (from module):**
```json
{
  "resourceType": "microsoft.compute/disks",
  "resourceName": "disk-orphan-01",
  "resourceGroup": "rg-legacy-migration",
  "estimatedMonthlyCost": 45.00,
  "confidenceLevel": "high",
  "metadata": { "diskSizeGB": 256, "diskSku": "Premium_LRS" }
}
```

**Output (from agent):**

> **🔴 High Priority: Orphaned Premium SSD Disk**
> 
> **Resource:** disk-orphan-01 (256 GB Premium SSD)  
> **Location:** rg-legacy-migration  
> **Estimated Savings:** $45.00/month
> 
> This disk has been unattached for 54 days. The resource group name suggests it may be from a completed migration project.
> 
> **Recommendation:** Verify the migration is complete, then delete this disk.
> 
> [View in Azure Portal →](https://portal.azure.com/#resource/...)

---

## Notification System

### Email Workflow

The notification system uses Azure Logic Apps to send monthly optimization reports.

```
    ┌─────────────────────────────────────┐
    │ Trigger: HTTP Request               │
    │ (Called by AI Agent)                │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ Parse JSON payload                  │
    │ • recipientEmail                    │
    │ • ccEmails (FinOps team)            │
    │ • subscriptionName                  │
    │ • recommendations (from agent)      │
    │ • summary statistics                │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ Compose HTML email from template    │
    │ • Header with subscription name     │
    │ • Summary statistics                │
    │ • Prioritized recommendations       │
    │ • Trend insights                    │
    │ • Footer with support links         │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ Send email via Office 365           │
    │ connector (or SendGrid)             │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ Log delivery status to              │
    │ Cosmos DB                           │
    └──────────────────┬──────────────────┘
                       │
                       ▼
    ┌─────────────────────────────────────┐
    │ Return HTTP 200 OK                  │
    └─────────────────────────────────────┘
```

### Email Template Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  [Logo]                                                                     │
│                                                                             │
│  AZURE COST OPTIMIZATION REPORT                                             │
│  Subscription: Contoso Production 01                                        │
│  Report Date: January 2026                                                  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SUMMARY                                                                    │
│  ─────────────────────────────────────────────                              │
│  Total findings: 12                                                         │
│  Estimated monthly savings: $342.50                                         │
│  Trend: ↑ 3 new findings since last month                                   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🔴 HIGH PRIORITY (Act Now)                                                 │
│  ─────────────────────────────────────────────                              │
│                                                                             │
│  • 3 Orphaned Premium SSD Disks — $135/month                                │
│    Resources: disk-orphan-01, disk-orphan-02, disk-orphan-03                │
│    [View in Portal]                                                         │
│    Recommendation: Delete after verifying no data recovery needed           │
│                                                                             │
│  • 1 Unused DDoS Protection Plan — $2,944/month                             │
│    Resource: ddos-plan-legacy                                               │
│    [View in Portal]                                                         │
│    Recommendation: Delete immediately (no VNets protected)                  │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  🟡 REVIEW RECOMMENDED                                                      │
│  ─────────────────────────────────────────────                              │
│                                                                             │
│  • 2 Unattached Standard Public IPs — $7.30/month                           │
│    These may be reserved for DR. Verify with team before deletion.          │
│    [View in Portal]                                                         │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📈 TREND INSIGHT                                                           │
│  ─────────────────────────────────────────────                              │
│                                                                             │
│  This subscription has generated 3+ new orphaned disks each month           │
│  for the past 3 months. Consider enabling "Delete disks with VM"            │
│  in your deployment templates to prevent future orphaned resources.         │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Questions? Contact the FinOps team at finops@contoso.com                   │
│                                                                             │
│  [Unsubscribe] — Note: This is a mandatory compliance report.               │
│                  Contact FinOps to discuss frequency changes.               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Security and Identity

### Managed Identity Architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│ Azure Functions     │     │ AI Foundry Agent    │     │ Logic Apps          │
│ (Detection/Data)    │     │ Service             │     │ (Email)             │
├─────────────────────┤     ├─────────────────────┤     ├─────────────────────┤
│ System-Assigned     │     │ Project Managed     │     │ System-Assigned     │
│ Managed Identity    │     │ Identity            │     │ Managed Identity    │
└──────────┬──────────┘     └──────────┬──────────┘     └──────────┬──────────┘
           │                           │                           │
           │                           │                           │
           ▼                           ▼                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RBAC ASSIGNMENTS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Azure Functions Identity:                                                  │
│  ├── Reader (Management Group scope - all target subscriptions)             │
│  ├── Cost Management Reader (Management Group scope)                        │
│  └── Cosmos DB Data Contributor (Cosmos DB account)                         │
│                                                                             │
│  AI Foundry Project Identity:                                               │
│  └── Cognitive Services User (AI Foundry resource)                          │
│                                                                             │
│  Logic Apps Identity:                                                       │
│  └── Mail.Send (Microsoft Graph API - via app registration)                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```


### Cross-Subscription Access

To query all target subscriptions efficiently:

**Recommended Approach: Management Group Scope**

1. Create or identify a Management Group containing your target subscriptions
2. Assign `Reader` and `Cost Management Reader` roles at Management Group level
3. Azure Resource Graph queries automatically span all child subscriptions

```
Management Group: "All-Subscriptions"
├── Subscription: Contoso-Prod-01
├── Subscription: Contoso-Prod-02
├── Subscription: Contoso-Dev-01
├── ...
└── Subscription: Contoso-Test-99
```

### Data Security

| Control | Implementation |
|---------|---------------|
| Encryption at rest | Azure-managed keys (default) |
| Encryption in transit | TLS 1.2+ enforced |
| Network isolation | Cosmos DB VNet integration (optional) |
| Data residency | All resources in same Azure region |
| Access logging | Azure Monitor diagnostic logs |
| PII handling | No PII stored; subscription IDs only |

---

## Data Storage

### Cosmos DB Design

**Account Configuration:**

| Property | Value |
|----------|-------|
| API | Core (SQL) |
| Capacity Mode | Serverless (recommended for this workload) |
| Consistency | Session |
| Multi-region | No (single region sufficient) |

**Container Design:**

| Container | Partition Key | Purpose | TTL |
|-----------|--------------|---------|-----|
| `module-registry` | `/moduleId` | Module configuration and metadata | None |
| `findings-history` | `/subscriptionId` | Historical findings for trend analysis | 365 days |
| `subscription-owners` | `/subscriptionId` | Subscription-to-owner mapping | None |
| `execution-logs` | `/executionId` | Audit trail of agent runs | 90 days |

### Module Registry Schema

```json
{
  "id": "abandoned-resources",
  "moduleId": "abandoned-resources",
  "moduleName": "Abandoned Resources Detector",
  "version": "1.0.0",
  "enabled": true,
  "status": "active",
  "category": "cost-optimization",
  "description": "Detects orphaned Azure resources that incur unnecessary cost",
  "functionApp": "func-optimization",
  "functionName": "DetectAbandonedResources",
  "schedule": "monthly",
  "outputSchema": "v1-standard-findings",
  "configuration": {
    "resourceTypes": [
      "microsoft.compute/disks",
      "microsoft.network/publicIPAddresses",
      "microsoft.network/loadBalancers",
      "microsoft.network/natGateways",
      "microsoft.sql/servers/elasticPools",
      "microsoft.network/virtualNetworkGateways",
      "microsoft.network/ddosProtectionPlans",
      "microsoft.network/privateEndpoints"
    ],
    "minimumOrphanAgeDays": 7,
    "confidenceThresholds": {
      "certain": 95,
      "high": 75,
      "medium": 50,
      "low": 25
    }
  },
  "createdDate": "2026-01-15T00:00:00Z",
  "lastModifiedDate": "2026-01-15T00:00:00Z",
  "lastExecutionDate": null
}
```

### Subscription Owners Schema

> **Note:** This is an interim solution for development. The subscription-to-owner mapping is maintained manually in Cosmos DB while we research integration options with Azure Data Explorer and other authoritative data sources.

```json
{
  "id": "sub-contoso-prod-01",
  "subscriptionId": "sub-contoso-prod-01",
  "subscriptionName": "Contoso Production 01",
  "ownerEmail": "jane.smith@contoso.com",
  "ownerName": "Jane Smith",
  "teamName": "Platform Engineering",
  "costCenter": "CC-12345",
  "notificationPreferences": {
    "timezone": "America/Los_Angeles",
    "language": "en-US"
  },
  "lastUpdated": "2026-01-10T00:00:00Z",
  "dataSource": "manual"
}
```

**Future Enhancement:** Replace manual mapping with automated sync from Azure Data Explorer or integration with Azure Resource Manager tags/Azure Active Directory.

### Findings History Schema

```json
{
  "id": "f-abc123-2026-01-08",
  "findingId": "f-abc123",
  "executionId": "exec-2026-01-08-001",
  "executionDate": "2026-01-08T10:30:00Z",
  "subscriptionId": "sub-contoso-prod-01",
  "moduleId": "abandoned-resources",
  "resourceId": "/subscriptions/.../disks/disk-orphan-01",
  "resourceType": "microsoft.compute/disks",
  "category": "abandoned",
  "severity": "high",
  "confidenceScore": 92,
  "estimatedMonthlyCost": 45.00,
  "status": "open",
  "firstDetectedDate": "2025-11-15T00:00:00Z",
  "resolvedDate": null,
  "ttl": 31536000
}
```

---

## API Integration Details

For detailed Azure Resource Graph queries and API integration patterns, see [Optimization Agent Queries](optimization-agent-queries.md).

---

## Cost Estimate

### Monthly Cost Breakdown

| Service | Configuration | Estimated Monthly Cost |
|---------|--------------|----------------------|
| Azure AI Foundry Agent Service | Standard | $0 (service fee) |
| Azure OpenAI (GPT-4o) | ~100K tokens/month | $50 - $100 |
| Azure Functions | Consumption, ~1000 executions | $5 - $15 |
| Azure Cosmos DB | Serverless, ~1GB storage | $25 - $50 |
| Azure Logic Apps | Consumption | $10 - $20 |
| Azure Resource Graph | Free | $0 |
| Azure Monitor (Logging) | Basic logs | $10 - $20 |
| **Total** | | **$100 - $205/month** |

### Cost Optimization Notes

- Cosmos DB Serverless is ideal for this workload (spiky, monthly execution)
- Function Consumption plan is sufficient; no need for Premium
- Token usage scales with number of subscriptions with findings

---

## Project Plan

### Phase 1: Foundation (Weeks 1-2)

#### Milestone 1.1: Infrastructure Setup (Week 1)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Create resource group and naming convention | Platform Team | 0.5 days | - |
| Deploy Azure AI Foundry project | Platform Team | 1 day | Resource group |
| Deploy Azure Cosmos DB (Serverless) | Platform Team | 0.5 days | Resource group |
| Create Cosmos DB containers (4) | Platform Team | 0.5 days | Cosmos DB |
| Deploy Azure Function App | Platform Team | 0.5 days | Resource group |
| Create Logic App (empty) | Platform Team | 0.5 days | Resource group |
| Configure Managed Identities | Security Team | 1 day | All resources |
| Assign RBAC at Management Group scope | Security Team | 1 day | Identities configured |
| Validate cross-subscription access | Platform Team | 0.5 days | RBAC assigned |

**Deliverables:**
- All infrastructure resources deployed
- Managed identities configured
- Cross-subscription Reader access validated

#### Milestone 1.2: Data Layer Development (Week 1-2)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Implement GetModuleRegistry function | Dev Team | 0.5 days | Function App |
| Implement GetSubscriptionOwners function | Dev Team | 0.5 days | Function App, Cosmos DB |
| Populate initial subscription-owner mapping | Dev Team | 1 day | Container created |
| Implement StoreFindingsHistory function | Dev Team | 0.5 days | Function App, Cosmos DB |
| Implement GetHistoricalFindings function | Dev Team | 0.5 days | Function App, Cosmos DB |
| Unit test all data functions | Dev Team | 1 day | Functions complete |

**Deliverables:**
- Data access layer complete
- Initial owner mapping populated (manual)
- Functions tested and deployed

#### Milestone 1.3: Abandoned Resources Module (Week 2)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Implement Resource Graph queries (8 types) | Dev Team | 1.5 days | RBAC configured |
| Implement cost calculation logic | Dev Team | 1 day | Queries working |
| Implement confidence scoring | Dev Team | 1 day | Queries working |
| Implement module output formatting | Dev Team | 0.5 days | All logic complete |
| Register module in Cosmos DB | Dev Team | 0.25 days | Module complete |
| Test module against 10 subscriptions | QA Team | 1 day | Module deployed |
| Validate findings accuracy | QA Team | 1 day | Test complete |

**Deliverables:**
- Abandoned Resources module deployed
- Module registered in registry
- Accuracy validated on test subscriptions

### Phase 2: Agent & Integration (Week 3)

#### Milestone 2.1: AI Agent Configuration (Week 3)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Deploy GPT-4o model in Foundry | AI Team | 0.5 days | Foundry project |
| Design and test system prompt | AI Team | 1.5 days | Model deployed |
| Connect agent to Function tools | AI Team | 1 day | Functions ready |
| Test agent reasoning with sample data | AI Team | 1 day | Tools connected |
| Iterate on prompt based on output quality | AI Team | 1 day | Initial test |

**Deliverables:**
- Agent deployed and configured
- System prompt finalized
- Tool integrations validated

#### Milestone 2.2: Email Workflow (Week 3)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Design HTML email template | UX Team | 1 day | Requirements approved |
| Implement Logic App workflow | Dev Team | 1 day | Template ready |
| Configure Office 365 connector | Dev Team | 0.5 days | Admin consent |
| Connect agent to Logic App | AI Team | 0.5 days | Workflow ready |
| Test email delivery (5 test recipients) | QA Team | 1 day | Integration complete |

**Deliverables:**
- Email workflow operational
- Template approved
- End-to-end test passed

#### Milestone 2.3: End-to-End Integration (Week 3)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Full pipeline integration test | Dev Team | 1 day | All components ready |
| Performance testing | QA Team | 1 day | Integration test passed |
| Error handling and retry logic | Dev Team | 1 day | Testing complete |
| Monitoring and alerting setup | Platform Team | 0.5 days | Pipeline stable |

**Deliverables:**
- Complete pipeline functional
- Performance validated at scale
- Monitoring in place

### Phase 3: Pilot & Rollout (Weeks 4-5)

#### Milestone 3.1: Pilot Program (Week 4)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Select 20 pilot subscriptions | Project Lead | 0.5 days | Stakeholder approval |
| Brief pilot subscription owners | Project Lead | 1 day | Selection complete |
| Execute first monthly run (pilot) | Dev Team | 0.5 days | Briefing complete |
| Collect feedback from pilot users | Project Lead | 2.5 days | First run complete |
| Iterate based on feedback | Dev Team | 1.5 days | Feedback collected |

**Deliverables:**
- Pilot executed successfully
- Feedback incorporated
- Go/no-go decision for full rollout

#### Milestone 3.2: Communication & Training (Week 4-5)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Create announcement communication | Project Lead | 1 day | Pilot approved |
| Develop FAQ document | Project Lead | 1 day | Announcement draft |
| Send organization-wide announcement | Project Lead | 0.5 days | Materials ready |
| Host Q&A session for service teams | Project Lead | 0.5 days | Announcement sent |

**Deliverables:**
- All subscription owners informed
- FAQ published
- Questions addressed

#### Milestone 3.3: Full Rollout (Week 5)

| Task | Owner | Duration | Dependencies |
|------|-------|----------|--------------|
| Enable for all target subscriptions | Dev Team | 0.5 days | Communication complete |
| Execute first full monthly run | Dev Team | 0.5 days | All subscriptions enabled |
| Monitor for issues | Platform Team | 2.5 days | First run complete |
| Address any delivery failures | Dev Team | Ongoing | Monitoring active |
| Post-launch retrospective | Project Lead | 0.5 days | First run stabilized |

**Deliverables:**
- All target subscriptions receiving reports
- First full month complete
- Lessons learned documented

---

## Future Considerations

### Multi-Agent Evolution

The Azure Optimization Agent is designed as the foundation for a multi-agent system. Future agents may include:

| Agent | Purpose | Interaction |
|-------|---------|-------------|
| **Remediation Agent** | Execute approved optimization actions | Receives approved recommendations from Optimization Agent |
| **Approval Agent** | Route high-risk actions for human approval | Integrates with Teams/ServiceNow for approval workflows |
| **Monitoring Agent** | Track implementation of recommendations | Verifies actions were taken; follows up on unresolved findings |

### Autonomous Actions (Phase 2+)

The architecture supports progressive automation:

**Phase 2: Recommendations with Approval**
- Agent generates remediation scripts (ARM templates, CLI commands)
- Logic Apps routes to owner for approval via Teams Adaptive Card
- Approved actions executed via Azure Automation Runbook

**Phase 3: Low-Risk Autonomous Actions**
- Pre-approved action types (e.g., delete resources orphaned 90+ days with high confidence)
- Agent executes directly via Azure Automation
- Full audit trail in Cosmos DB
- Rollback capability (e.g., disk snapshots before deletion)

**Governance Controls:**
- Action classification (low/medium/high risk)
- Approval workflows by risk level
- Spending impact thresholds
- Emergency stop capability

### Subscription Owner Data Source

Current implementation uses a manual mapping in Cosmos DB. Future options to explore:

| Option | Description | Effort |
|--------|-------------|--------|
| Azure Data Explorer sync | Automated sync from existing Kusto database | Medium |
| Azure Resource Manager tags | Read owner from subscription tags | Low |
| Azure AD Group membership | Map subscriptions to AAD groups | Medium |
| ServiceNow CMDB integration | Pull from IT service management system | High |

### Additional Modules

| Module | Detection Method | Target Release |
|--------|-----------------|----------------|
| Overprovisioned VMs | Azure Monitor CPU/memory metrics <20% avg | v1.1 |
| Overprovisioned Storage | Storage account utilization <30% | v1.1 |
| Reserved Instance Opportunities | Consistent VM usage patterns | v1.2 |
| Idle App Services | Zero requests for 30+ days | v1.2 |
| Unused Azure Kubernetes Clusters | No workloads scheduled | v1.3 |