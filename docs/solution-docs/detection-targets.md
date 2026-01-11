# Detection Targets

This document explains how to configure which Azure subscriptions and management groups to scan, and how owner information is managed for notifications.

## Overview

The solution uses the `detection-targets` Cosmos DB container to manage both targeting and ownership in a single, consolidated schema.

| Container | Purpose | Partition Key |
|-----------|---------|---------------|
| `detection-targets` | Define targets to scan with owner contact info | `/targetId` |

```
┌───────────────────────────────────────────────────┐
│                    detection-targets              │
│                                                   │
│  • Subscriptions and management groups to scan    │
│  • Enable/disable scanning                        │
│  • Team assignment                                │
│  • Owner emails (supports multiple recipients)    │
│  • Owner names                                    │
│  • Notification preferences                       │
│  • Cost center                                    │
│                                                   │
└───────────────────────────────────────────────────┘
                          │
                          │  Agent retrieves targets with owner info
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │              AI Agent Workflow                      │
    │                                                     │
    │  1. Get targets → 2. Run detection →                │
    │  3. Save findings → 4. Send personalized emails     │
    └─────────────────────────────────────────────────────┘
```

## Detection Target Schema

```json
{
  "id": "sub-production-001",
  "targetId": "sub-production-001",
  "targetType": "subscription",
  "displayName": "Production Subscription",
  "enabled": true,
  "teamId": "team-platform",
  "teamName": "Platform Engineering",
  "ownerEmails": ["platform-team@contoso.com", "finops@contoso.com"],
  "ownerNames": ["Platform Team DL", "FinOps Team"],
  "notificationPreferences": {
    "timezone": "America/Los_Angeles",
    "language": "en-US"
  },
  "costCenter": "CC-1001",
  "description": "Main production workloads",
  "tags": {
    "environment": "production"
  },
  "createdDate": "2026-01-11T00:00:00Z",
  "lastModifiedDate": "2026-01-11T00:00:00Z"
}
```

## Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Document ID (same as targetId) |
| `targetId` | string | Yes | Azure subscription ID or management group ID |
| `targetType` | enum | Yes | `subscription` or `managementGroup` |
| `displayName` | string | Yes | Human-readable name |
| `enabled` | boolean | Yes | Whether to include in scans |
| `teamId` | string | No | Team identifier for grouping |
| `teamName` | string | No | Team display name |
| `ownerEmails` | array | No | Email addresses for notifications (supports multiple) |
| `ownerNames` | array | No | Display names of owners (parallel to ownerEmails) |
| `notificationPreferences` | object | No | Notification settings (timezone, language) |
| `costCenter` | string | No | Cost center for reporting |
| `description` | string | No | Description of the target |
| `tags` | object | No | Custom key-value tags |
| `createdDate` | datetime | No | When the target was created |
| `lastModifiedDate` | datetime | No | When the target was last updated |

### Notification Preferences

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timezone` | string | `UTC` | Timezone for email timestamps |
| `language` | string | `en-US` | Language for email content |

## Target Types

### Subscription Target

Use for individual Azure subscriptions:

```json
{
  "id": "12345678-1234-1234-1234-123456789abc",
  "targetId": "12345678-1234-1234-1234-123456789abc",
  "targetType": "subscription",
  "displayName": "Production - East US",
  "enabled": true,
  "teamId": "team-infra",
  "teamName": "Infrastructure",
  "ownerEmails": ["infra@contoso.com"],
  "ownerNames": ["Infrastructure Team"]
}
```

### Management Group Target

Use to scan all subscriptions under a management group:

```json
{
  "id": "mg-corporate",
  "targetId": "mg-corporate",
  "targetType": "managementGroup",
  "displayName": "Corporate Management Group",
  "enabled": true,
  "teamId": "team-finops",
  "teamName": "FinOps",
  "ownerEmails": ["finops@contoso.com"],
  "ownerNames": ["FinOps Team"],
  "description": "All subscriptions under the corporate hierarchy"
}
```

## Adding Detection Targets

### Via Azure Portal (Data Explorer)

1. Navigate to your Cosmos DB account
2. Go to **Data Explorer**
3. Expand **optimization-db** > **detection-targets**
4. Click **New Item**
5. Paste your target JSON document
6. Click **Save**

### Via Azure CLI

```bash
# Get your Cosmos DB endpoint
COSMOS_ENDPOINT=$(az cosmosdb show \
  --name <cosmos-account-name> \
  --resource-group rg-optimization-agent \
  --query documentEndpoint \
  --output tsv)

# Use the REST API or Azure SDK to insert documents
```

## API Endpoint

```
GET /api/get-detection-targets
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_disabled` | boolean | `false` | Include disabled targets |
| `target_type` | string | - | Filter by type (`subscription` or `managementGroup`) |

**Example Response:**

```json
{
  "targets": [
    {
      "targetId": "sub-prod-001",
      "targetType": "subscription",
      "displayName": "Production",
      "enabled": true,
      "teamName": "Platform",
      "ownerEmails": ["platform@contoso.com", "finops@contoso.com"],
      "ownerNames": ["Platform Team", "FinOps Team"]
    },
    {
      "targetId": "mg-development",
      "targetType": "managementGroup",
      "displayName": "Development Group",
      "enabled": true,
      "teamName": "DevOps",
      "ownerEmails": ["devops@contoso.com"],
      "ownerNames": ["DevOps Team"]
    }
  ],
  "count": 2,
  "subscriptionCount": 1,
  "managementGroupCount": 1
}
```

## Common Scenarios

### Scenario 1: Single Team, Multiple Subscriptions

A platform team owns 5 subscriptions. All notifications go to the team distribution list:

```json
[
  {
    "targetId": "sub-1",
    "targetType": "subscription",
    "displayName": "Prod East",
    "enabled": true,
    "teamId": "platform",
    "teamName": "Platform",
    "ownerEmails": ["platform@contoso.com"],
    "ownerNames": ["Platform Team"]
  },
  {
    "targetId": "sub-2",
    "targetType": "subscription",
    "displayName": "Prod West",
    "enabled": true,
    "teamId": "platform",
    "teamName": "Platform",
    "ownerEmails": ["platform@contoso.com"],
    "ownerNames": ["Platform Team"]
  }
]
```

### Scenario 2: Multiple Recipients per Subscription

A subscription has both a technical owner and a FinOps contact:

```json
{
  "targetId": "sub-critical-app",
  "targetType": "subscription",
  "displayName": "Critical Application",
  "enabled": true,
  "ownerEmails": ["app-team@contoso.com", "finops@contoso.com", "manager@contoso.com"],
  "ownerNames": ["App Team", "FinOps", "Engineering Manager"]
}
```

All three recipients will receive the optimization report email.

### Scenario 3: Management Group with Centralized Notifications

A corporate management group where all findings go to FinOps:

```json
{
  "targetId": "mg-corporate",
  "targetType": "managementGroup",
  "displayName": "Corporate",
  "enabled": true,
  "teamId": "finops",
  "teamName": "FinOps",
  "ownerEmails": ["finops@contoso.com"],
  "ownerNames": ["FinOps Team"]
}
```

### Scenario 4: Temporarily Disable a Target

To skip a subscription during the next scan, set `enabled: false`:

```json
{
  "targetId": "sub-sandbox",
  "targetType": "subscription",
  "displayName": "Sandbox (disabled)",
  "enabled": false,
  "description": "Skipped during cost optimization - sandbox environment"
}
```

### Scenario 5: Mixed Targeting

Combine individual subscriptions with management groups:

```json
[
  {"targetId": "mg-production", "targetType": "managementGroup", "enabled": true, "ownerEmails": ["prod-ops@contoso.com"]},
  {"targetId": "sub-special-project", "targetType": "subscription", "enabled": true, "ownerEmails": ["special-project@contoso.com"]},
  {"targetId": "sub-legacy-app", "targetType": "subscription", "enabled": true, "ownerEmails": ["legacy-support@contoso.com"]}
]
```

## Seed Data

Sample seed data is available in `data/seed/detection-targets.sample.json`.

Copy and modify this file for your environment, then import via Data Explorer.

## Best Practices

1. **Use consistent IDs**: Set `id` equal to `targetId` for simplicity
2. **Add descriptions**: Document why targets are included/excluded
3. **Use tags**: Add metadata for filtering and reporting
4. **Keep owners updated**: Regularly verify email addresses are current
5. **Use distribution lists**: For team-owned subscriptions, use DLs instead of individual emails
6. **Start small**: Begin with a few subscriptions, then expand
7. **Disable vs. delete**: Use `enabled: false` rather than deleting to preserve history
8. **Multiple recipients**: Add both technical owners and FinOps contacts for visibility
