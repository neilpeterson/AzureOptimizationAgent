# Detection Targets & Subscription Owners

This document explains how to configure which Azure subscriptions and management groups to scan, and how to map them to owners for notifications.

## Overview

The solution uses two Cosmos DB containers to manage targeting and ownership:

| Container | Purpose | Partition Key |
|-----------|---------|---------------|
| `detection-targets` | Define which subscriptions/management groups to scan | `/targetId` |
| `subscription-owners` | Map subscriptions to owners for email notifications | `/subscriptionId` |

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   detection-targets     │     │   subscription-owners   │
│                         │     │                         │
│  • Subscriptions        │     │  • Owner email          │
│  • Management groups    │     │  • Team name            │
│  • Enable/disable       │────►│  • Cost center          │
│  • Team assignment      │     │  • Notification prefs   │
│                         │     │                         │
└─────────────────────────┘     └─────────────────────────┘
           │                               │
           │  Agent retrieves targets      │  Agent looks up owners
           ▼                               ▼
    ┌─────────────────────────────────────────────────┐
    │              AI Agent Workflow                  │
    │                                                 │
    │  1. Get targets → 2. Run detection →            │
    │  3. Get owners → 4. Send personalized emails    │
    └─────────────────────────────────────────────────┘
```

## Detection Targets

### Schema

```json
{
  "id": "sub-production-001",
  "targetId": "sub-production-001",
  "targetType": "subscription",
  "displayName": "Production Subscription",
  "enabled": true,
  "teamId": "team-platform",
  "teamName": "Platform Engineering",
  "ownerEmail": "platform-team@contoso.com",
  "description": "Main production workloads",
  "tags": {
    "environment": "production",
    "costCenter": "CC-1001"
  },
  "createdDate": "2026-01-11T00:00:00Z",
  "lastModifiedDate": "2026-01-11T00:00:00Z"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Document ID (same as targetId) |
| `targetId` | string | Yes | Azure subscription ID or management group ID |
| `targetType` | enum | Yes | `subscription` or `managementGroup` |
| `displayName` | string | Yes | Human-readable name |
| `enabled` | boolean | Yes | Whether to include in scans |
| `teamId` | string | No | Team identifier for grouping |
| `teamName` | string | No | Team display name |
| `ownerEmail` | string | No | Primary contact email |
| `description` | string | No | Description of the target |
| `tags` | object | No | Custom key-value tags |
| `createdDate` | datetime | No | When the target was created |
| `lastModifiedDate` | datetime | No | When the target was last updated |

### Target Types

#### Subscription Target

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
  "ownerEmail": "infra@contoso.com"
}
```

#### Management Group Target

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
  "ownerEmail": "finops@contoso.com",
  "description": "All subscriptions under the corporate hierarchy"
}
```

### Adding Detection Targets

#### Via Azure Portal (Data Explorer)

1. Navigate to your Cosmos DB account
2. Go to **Data Explorer**
3. Expand **optimization-db** > **detection-targets**
4. Click **New Item**
5. Paste your target JSON document
6. Click **Save**

#### Via Azure CLI

```bash
# Get your Cosmos DB endpoint
COSMOS_ENDPOINT=$(az cosmosdb show \
  --name <cosmos-account-name> \
  --resource-group rg-optimization-agent \
  --query documentEndpoint \
  --output tsv)

# Use the REST API or Azure SDK to insert documents
```

### API Endpoint

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
      "teamName": "Platform"
    },
    {
      "targetId": "mg-development",
      "targetType": "managementGroup",
      "displayName": "Development Group",
      "enabled": true,
      "teamName": "DevOps"
    }
  ],
  "count": 2,
  "subscriptionCount": 1,
  "managementGroupCount": 1
}
```

## Subscription Owners

The `subscription-owners` container maps individual subscriptions to owners who should receive notification emails.

### Schema

```json
{
  "id": "12345678-1234-1234-1234-123456789abc",
  "subscriptionId": "12345678-1234-1234-1234-123456789abc",
  "subscriptionName": "Production - East US",
  "ownerEmail": "john.doe@contoso.com",
  "ownerName": "John Doe",
  "teamName": "Platform Engineering",
  "costCenter": "CC-1001",
  "notificationPreferences": {
    "timezone": "America/Los_Angeles",
    "language": "en-US"
  },
  "lastUpdated": "2026-01-11T00:00:00Z",
  "dataSource": "manual"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Document ID (same as subscriptionId) |
| `subscriptionId` | string | Yes | Azure subscription ID |
| `subscriptionName` | string | No | Human-readable subscription name |
| `ownerEmail` | string | Yes | Email address for notifications |
| `ownerName` | string | No | Owner's display name |
| `teamName` | string | No | Team or department name |
| `costCenter` | string | No | Cost center for reporting |
| `notificationPreferences` | object | No | Email preferences (timezone, language) |
| `lastUpdated` | datetime | No | When the record was last updated |
| `dataSource` | string | No | How the data was populated (`manual`, `api`, etc.) |

### Adding Subscription Owners

#### Via Azure Portal (Data Explorer)

1. Navigate to your Cosmos DB account
2. Go to **Data Explorer**
3. Expand **optimization-db** > **subscription-owners**
4. Click **New Item**
5. Paste your owner mapping JSON
6. Click **Save**

#### Example: Multiple Subscriptions, Same Owner

If one person owns multiple subscriptions, create a document for each:

```json
// Document 1
{
  "id": "sub-prod-001",
  "subscriptionId": "sub-prod-001",
  "subscriptionName": "Production",
  "ownerEmail": "alice@contoso.com",
  "ownerName": "Alice Smith",
  "teamName": "Platform"
}

// Document 2
{
  "id": "sub-staging-001",
  "subscriptionId": "sub-staging-001",
  "subscriptionName": "Staging",
  "ownerEmail": "alice@contoso.com",
  "ownerName": "Alice Smith",
  "teamName": "Platform"
}
```

Alice will receive separate emails for each subscription's findings.

### API Endpoint

```
POST /api/get-subscription-owners
```

**Request Body:**

```json
{
  "subscriptionIds": ["sub-prod-001", "sub-staging-001"]
}
```

**Response:**

```json
{
  "owners": [
    {
      "subscriptionId": "sub-prod-001",
      "subscriptionName": "Production",
      "ownerEmail": "alice@contoso.com",
      "ownerName": "Alice Smith"
    },
    {
      "subscriptionId": "sub-staging-001",
      "subscriptionName": "Staging",
      "ownerEmail": "alice@contoso.com",
      "ownerName": "Alice Smith"
    }
  ],
  "count": 2,
  "notFound": []
}
```

## Common Scenarios

### Scenario 1: Single Team, Multiple Subscriptions

A platform team owns 5 subscriptions. Configure detection targets and owners:

**Detection Targets:**
```json
[
  {"targetId": "sub-1", "targetType": "subscription", "teamId": "platform", "enabled": true},
  {"targetId": "sub-2", "targetType": "subscription", "teamId": "platform", "enabled": true},
  {"targetId": "sub-3", "targetType": "subscription", "teamId": "platform", "enabled": true},
  {"targetId": "sub-4", "targetType": "subscription", "teamId": "platform", "enabled": true},
  {"targetId": "sub-5", "targetType": "subscription", "teamId": "platform", "enabled": true}
]
```

**Subscription Owners:**
```json
[
  {"subscriptionId": "sub-1", "ownerEmail": "platform@contoso.com"},
  {"subscriptionId": "sub-2", "ownerEmail": "platform@contoso.com"},
  {"subscriptionId": "sub-3", "ownerEmail": "platform@contoso.com"},
  {"subscriptionId": "sub-4", "ownerEmail": "platform@contoso.com"},
  {"subscriptionId": "sub-5", "ownerEmail": "platform@contoso.com"}
]
```

### Scenario 2: Management Group with Multiple Teams

A corporate management group contains subscriptions owned by different teams:

**Detection Target:**
```json
{
  "targetId": "mg-corporate",
  "targetType": "managementGroup",
  "displayName": "Corporate",
  "enabled": true,
  "teamId": "finops",
  "ownerEmail": "finops@contoso.com"
}
```

**Subscription Owners** (findings route to the right team):
```json
[
  {"subscriptionId": "sub-sales", "ownerEmail": "sales-ops@contoso.com", "teamName": "Sales"},
  {"subscriptionId": "sub-hr", "ownerEmail": "hr-tech@contoso.com", "teamName": "HR"},
  {"subscriptionId": "sub-finance", "ownerEmail": "finance-it@contoso.com", "teamName": "Finance"}
]
```

### Scenario 3: Temporarily Disable a Target

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

### Scenario 4: Mixed Targeting

Combine individual subscriptions with management groups:

```json
[
  {"targetId": "mg-production", "targetType": "managementGroup", "enabled": true},
  {"targetId": "sub-special-project", "targetType": "subscription", "enabled": true},
  {"targetId": "sub-legacy-app", "targetType": "subscription", "enabled": true}
]
```

## Seed Data

Sample seed data is available in `data/seed/`:

- `detection-targets.sample.json` - Example targets
- `subscription-owners.sample.json` - Example owner mappings

Copy and modify these files for your environment, then import via Data Explorer.

## Best Practices

1. **Use consistent IDs**: Set `id` equal to `targetId` or `subscriptionId` for simplicity
2. **Add descriptions**: Document why targets are included/excluded
3. **Use tags**: Add metadata for filtering and reporting
4. **Keep owners updated**: Regularly verify email addresses are current
5. **Start small**: Begin with a few subscriptions, then expand
6. **Disable vs. delete**: Use `enabled: false` rather than deleting to preserve history
