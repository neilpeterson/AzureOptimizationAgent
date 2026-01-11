# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

The **Azure Optimization Agent** is an agentic solution that automatically identifies cost optimization opportunities across Azure subscriptions, detects spending trends, and delivers personalized monthly recommendations to subscription owners.

## Architecture

Three-layer architecture orchestrated by an Azure AI Foundry Agent (GPT-4o):

| Layer | Purpose | Implementation |
|-------|---------|----------------|
| **Detection Layer** | Scans Azure subscriptions via Resource Graph for optimization opportunities | Azure Functions |
| **Data Layer** | Manages module registry, findings history, subscription-owner mapping | Azure Functions + Cosmos DB |
| **Notification Layer** | Sends personalized email reports to subscription owners | Logic Apps |

**Key distinction:** Detection Layer queries Azure resources externally; Data Layer manages internal solution data.

## Tech Stack

- **Orchestration:** Azure AI Foundry Agent Service
- **Model:** GPT-4o
- **Compute:** Azure Functions (Consumption)
- **Data:** Azure Cosmos DB (Serverless, SQL API)
- **Workflow:** Azure Logic Apps
- **Query:** Azure Resource Graph

## Module System

Optimization capabilities are pluggable modules registered in Cosmos DB's `module-registry` container.

### Module Interface Contract

```json
// Input
{
  "executionId": "exec-2026-01-08-001",
  "subscriptionIds": ["sub-1", "sub-2"],
  "managementGroupIds": ["mg-corp"],
  "configuration": { },
  "dryRun": false
}

// Output
{
  "moduleId": "abandoned-resources",
  "executionId": "exec-2026-01-08-001",
  "status": "success",
  "findings": [ /* standardized finding objects */ ],
  "summary": { },
  "errors": [ ]
}
```

### Adding a New Module

1. Create Azure Function implementing the module interface contract
2. Register module metadata in `module-registry` Cosmos container
3. Update agent system prompt if new finding types require special handling
4. Test with `dryRun: true` against test subscriptions
5. Set `enabled: true` in registry

## Data Contracts

### Standard Finding Schema

All modules output findings with these required fields:
- `findingId`, `subscriptionId`, `resourceId`, `resourceType`
- `category`: abandoned | overprovisioned | idle | misconfigured | opportunity
- `severity`: critical | high | medium | low | informational
- `confidenceScore` (0-100), `confidenceLevel`
- `incursCost`, `estimatedMonthlyCost`

### Severity Classification

| Severity | Monthly Cost Impact |
|----------|---------------------|
| Critical | >$1,000 |
| High | $100 - $1,000 |
| Medium | $10 - $100 |
| Low | $1 - $10 |
| Informational | $0 |

### Confidence Scoring

| Level | Score | Criteria |
|-------|-------|----------|
| Certain | 95-100% | Orphaned 90+ days, no activity |
| High | 75-94% | Orphaned 30-90 days |
| Medium | 50-74% | Orphaned 7-30 days |
| Low | 25-49% | Orphaned <7 days |

## Cosmos DB Containers

| Container | Partition Key | Purpose |
|-----------|--------------|---------|
| `detection-targets` | `/targetId` | Subscriptions and management groups to scan |
| `module-registry` | `/moduleId` | Module configuration |
| `findings-history` | `/subscriptionId` | Historical findings (365-day TTL) |
| `subscription-owners` | `/subscriptionId` | Owner mapping (manual, interim) |
| `execution-logs` | `/executionId` | Audit trail (90-day TTL) |

## Detection Targets

Detection targets define which subscriptions and management groups to scan. Targets are stored in the `detection-targets` container.

### Detection Target Schema

```json
{
  "id": "sub-prod-001",
  "targetId": "sub-prod-001",
  "targetType": "subscription",  // or "managementGroup"
  "displayName": "Production Subscription",
  "enabled": true,
  "teamId": "team-platform",
  "teamName": "Platform Engineering",
  "ownerEmail": "platform@contoso.com"
}
```

### Target Types

- **subscription**: Individual Azure subscription ID
- **managementGroup**: Management group ID (scans all child subscriptions)

Mixed targeting is supported - you can combine specific subscriptions with management groups.

## Security

- All resources use System-Assigned Managed Identity
- Cross-subscription access via Management Group scope with Reader + Cost Management Reader roles
- No PII stored; subscription IDs only

## Related Documentation

- [Implementation Status](./docs/project-management/STATUS.md) - Current implementation progress
- [Implementation Plan](./docs/project-management/PLAN.md) - Detailed implementation roadmap
- [Specification](./docs/project-management/SPECIFICATION.md) - Full project specification
