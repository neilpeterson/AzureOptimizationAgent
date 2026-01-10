# Azure Optimization Agent

The Azure Optimization Agent is an agentic solution that automatically identifies cost optimization opportunities across a large fleet of Azure subscriptions. An Azure AI Foundry Agent (GPT-4o) orchestrates the entire workflow—querying for abandoned resources, analyzing findings, and delivering personalized monthly reports to subscription owners.

### How It Works

1. **Orchestration**: An AI agent receives a monthly timer trigger and autonomously decides which detection modules to run
2. **Detection**: Azure Functions query Azure Resource Graph to find optimization opportunities (unattached disks, unused public IPs, empty load balancers, etc.)
3. **Storage**: Findings are persisted to Cosmos DB with confidence scores, cost estimates, and severity classifications
4. **Notification**: A Logic App sends personalized HTML emails to subscription owners with actionable recommendations

### Modular & Extensible

The solution uses a pluggable module architecture. Detection capabilities are registered in Cosmos DB and implement a standard interface contract. To add new optimization detection (e.g., overprovisioned VMs, idle databases):

1. Create a new detection module implementing the [`ModuleInput → ModuleOutput`](docs/module-contracts.md) contract
2. [Register the module](docs/module-registration.md) in the `module-registry` container
3. The AI agent automatically discovers and executes enabled modules

## Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                             AZURE AI FOUNDRY                                  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                         AI Agent (GPT-4o)                               │  │
│  │                                                                         │  │
│  │  "Get enabled modules" ──► "Run abandoned-resources detection" ──►      │  │
│  │  "Save findings" ──► "Get subscription owners" ──► "Send emails"        │  │
│  └───────────────────────────────────┬─────────────────────────────────────┘  │
│                                      │                                        │
│                            Tool Calls (HTTP)                                  │
└──────────────────────────────────────┼────────────────────────────────────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            AZURE FUNCTION APP                                │
│                                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐   │
│  │     Data Layer      │  │   Detection Layer   │  │       Health        │   │
│  │                     │  │                     │  │                     │   │
│  │ GET  /module-       │  │ POST /abandoned-    │  │ GET  /health        │   │
│  │      registry       │  │      resources      │  │                     │   │
│  │ POST /save-findings │  │                     │  │                     │   │
│  │ GET  /findings-     │  │ (Future modules...) │  │                     │   │
│  │      history        │  │                     │  │                     │   │
│  │ POST /subscription- │  │                     │  │                     │   │
│  │      owners         │  │                     │  │                     │   │
│  └──────────┬──────────┘  └──────────┬──────────┘  └─────────────────────┘   │
│             │                        │                                       │
│             │ Managed Identity       │ Managed Identity                      │
└─────────────┼────────────────────────┼───────────────────────────────────────┘
              │                        │
              ▼                        ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│       COSMOS DB          │  │   AZURE RESOURCE GRAPH   │
│       (Serverless)       │  │                          │
│                          │  │   Queries 200+           │
│  ┌────────────────────┐  │  │   subscriptions for:     │
│  │ module-registry    │  │  │                          │
│  │ (module configs)   │  │  │   • Unattached disks     │
│  ├────────────────────┤  │  │   • Unused public IPs    │
│  │ findings-history   │  │  │   • Empty load balancers │
│  │ (365-day TTL)      │  │  │   • Orphaned NAT GWs     │
│  ├────────────────────┤  │  │   • Empty SQL pools      │
│  │ subscription-owners│  │  │   • Unused VNet GWs      │
│  │ (email contacts)   │  │  │   • Orphaned DDoS plans  │
│  ├────────────────────┤  │  │   • Disconnected PEs     │
│  │ execution-logs     │  │  │                          │
│  │ (90-day TTL)       │  │  └──────────────────────────┘
│  └────────────────────┘  │
└──────────────────────────┘
              │
              │ Findings grouped by owner
              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                               LOGIC APP                                 │
│                                                                         │
│  Receives findings per subscription owner ──► Formats HTML email ──►    │
│  Sends via Office 365 connector                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Execution Flow

The Azure AI Foundry Agent (GPT-4o) acts as the orchestrator. On a monthly schedule, it autonomously executes a sequence of tool calls, **receives and analyzes the results**, then decides next actions.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                            AZURE AI FOUNDRY AGENT (GPT-4o)                              │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │ 1. GET MODULES                                                                  │    │
│  │    Call: GET /api/get-module-registry                                           │    │
│  │    Response: ["abandoned-resources", "overprovisioned-vms", ...]                │    │
│  │    Agent decides: "I'll run each enabled module"                                │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │ 2. RUN DETECTION                                                                │    │
│  │    Call: POST /api/abandoned-resources {subscriptionIds: [...]}                 │    │
│  │    Response: {findings: [...], summary: {totalSavings: $2,847, ...}}            │    │
│  │    Agent analyzes: "Found 47 findings, $2,847/month potential savings"          │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │ 3. SAVE FINDINGS                                                                │    │
│  │    Call: POST /api/save-findings {findings: [...]}                              │    │
│  │    Agent reasons: "Findings saved, now get historical trends for context"       │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │ 4. GET TRENDS                                                                   │    │
│  │    Call: GET /api/get-findings-trends?module_id=abandoned-resources&months=3    │    │
│  │    Response: {trends: [...], summary: {trend: "improving", message: "..."}}     │    │
│  │    Agent analyzes: "Findings down 56% from last month - great progress!"        │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │ 5. GET OWNERS                                                                   │    │
│  │    Call: POST /api/subscription-owners {subscriptionIds: ["sub-1", "sub-2"]}    │    │
│  │    Response: [{ownerEmail: "team-a@...", findings: [...]}, ...]                 │    │
│  │    Agent decides: "Send personalized report with trend context to each owner"   │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                              │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │ 6. SEND NOTIFICATIONS                                                           │    │
│  │    Call: POST /logic-app/send-email {owner: "...", findings: [...], trends: {}} │    │
│  │    Agent customizes: "Great job reducing abandoned disks from 50 to 22!"        │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Tool Call Flow

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                           AZURE AI FOUNDRY AGENT (GPT-4o)                      │
│                                                                                │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Timer   │    │   Get    │    │   Run    │    │   Save   │    │   Send   │  │
│  │ Trigger  │───►│ Modules  │───►│Detection │───►│ Findings │───►│  Email   │  │
│  │(Monthly) │    │          │    │          │    │          │    │          │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                       │               │               │               │        │
│                  Tool Call       Tool Call       Tool Call       Tool Call     │
└──────────────────────┬───────────────┬───────────────┬───────────────┬─────────┘
                       │               │               │               │
                       ▼               ▼               ▼               ▼
                  ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐
                  │ Cosmos  │    │ Resource │    │ Cosmos  │    │  Logic   │
                  │   DB    │    │  Graph   │    │   DB    │    │   App    │
                  └─────────┘    └──────────┘    └─────────┘    └──────────┘
```

### What the Agent Receives and Analyzes

After each detection run, the agent receives a full `ModuleOutput` containing:

```json
{
  "findings": [
    {"resourceId": "...", "severity": "high", "estimatedMonthlyCost": 150.00, ...},
    {"resourceId": "...", "severity": "medium", "estimatedMonthlyCost": 38.40, ...}
  ],
  "summary": {
    "totalFindings": 47,
    "totalEstimatedMonthlySavings": 2847.50,
    "findingsBySeverity": {"critical": 2, "high": 8, "medium": 25, "low": 12}
  }
}
```

The agent also retrieves **historical trends** for month-over-month context:

```json
{
  "moduleId": "abandoned-resources",
  "trends": [
    {"month": "2026-01", "totalFindings": 22, "totalCost": 850.00},
    {"month": "2025-12", "totalFindings": 50, "totalCost": 1920.00}
  ],
  "summary": {
    "findingsChange": -28,
    "findingsChangePercent": -56.0,
    "trend": "improving",
    "message": "Great progress! Findings decreased from 50 to 22 (56% reduction)..."
  }
}
```

The agent uses this data to:
- **Prioritize**: Focus on critical/high severity findings first
- **Group**: Organize findings by subscription owner for personalized reports
- **Recommend**: Suggest remediation actions based on resource type
- **Summarize**: Create executive summaries of optimization opportunities
- **Contextualize**: Add historical trends to show progress or highlight regressions

## Azure Resources

| Resource | SKU | Purpose |
|----------|-----|---------|
| **AI Foundry Agent** | GPT-4o | Orchestrates detection, analysis, and notification |
| **Function App** | Consumption | Hosts Data Layer + Detection Layer APIs |
| **Cosmos DB** | Serverless | Stores modules, findings, owners, logs |
| **Logic App** | Consumption | Sends personalized emails via O365 |
| **Resource Graph** | - | Cross-subscription resource queries |
| **Log Analytics** | - | Centralized logging |
| **Application Insights** | - | Function monitoring |

## Data Flow

```
      DETECTION                              STORAGE                             NOTIFICATION
          │                                     │                                     │
          ▼                                     ▼                                     ▼
┌─────────────────┐                   ┌─────────────────┐                   ┌─────────────────┐
│                 │                   │                 │                   │                 │
│  Resource Graph │────── Findings ──►│    Cosmos DB    │───── Grouped ────►│    Logic App    │
│      Query      │                   │                 │      by owner     │                 │
│                 │                   │  - findingId    │                   │  - HTML email   │
│  KQL queries    │                   │  - resourceId   │                   │  - Per owner    │
│  across 200+    │                   │  - severity     │                   │  - Monthly      │
│  subscriptions  │                   │  - cost         │                   │                 │
│                 │                   │  - confidence   │                   │                 │
└─────────────────┘                   └─────────────────┘                   └─────────────────┘
```

## Security

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                           MANAGED IDENTITY                                    │
│                                                                               │
│  Function App ────┬──── Cosmos DB Data Contributor                            │
│       │           ├──── Storage Blob Data Owner                               │
│       │           └──── Reader (Management Group scope)                       │
│       │                                                                       │
│       └───────────── No secrets in code                                       │
│                      DefaultAzureCredential                                   │
│                                                                               │
├───────────────────────────────────────────────────────────────────────────────┤
│                           NETWORK SECURITY                                    │
│                                                                               │
│  Network Security Perimeter (Preview)                                         │
│       │                                                                       │
│       ├──── Cosmos DB association                                             │
│       └──── Storage Account association                                       │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Getting Started

```bash
# 1. Deploy infrastructure
az deployment group create -g rg-optimization-agent \
  -f infra/main.bicep -p infra/main.bicepparam

# 2. Seed initial data
python scripts/test_data_layer_live.py --seed

# 3. Run detection test
python scripts/test_detector_live.py --all-types
```

## Documentation

| Document | Description |
|----------|-------------|
| [Deployment Guide](docs/deployment-guide.md) | Step-by-step deployment instructions |
| [Design Document](OptimizationAgent.md) | Full architecture and specifications |
| [Module Contracts](docs/module-contracts.md) | Input/output schemas for detection modules |
| [Module Registration](docs/module-registration.md) | How to register modules in Cosmos DB |
| [Shared Library Guide](docs/shared-library.md) | Adding new detection modules |
| [Implementation Status](STATUS.md) | Current progress |

## License

MIT
