# API Reference

This document describes all HTTP endpoints exposed by the Optimization Agent Function App.

## Endpoint Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| [/get-module-registry](#get-get-module-registry) | GET | Returns all registered detection modules |
| [/save-findings](#post-save-findings) | POST | Saves detection findings to history |
| [/get-findings-history](#get-get-findings-history) | GET | Returns historical findings for a subscription |
| [/get-findings-trends](#get-get-findings-trends) | GET | Returns month-over-month findings trends |
| [/get-subscription-owners](#post-get-subscription-owners) | POST | Returns owner information for subscriptions |
| [/get-detection-targets](#get-get-detection-targets) | GET | Returns subscriptions and management groups to scan |
| [/abandoned-resources](#post-abandoned-resources) | POST | Runs abandoned resources detection module |
| [/send-optimization-email](#post-send-optimization-email) | POST | Sends optimization report email via Logic App |
| [/health](#get-health) | GET | Returns health status (no auth required) |

## Base URL

```
https://<function-app-name>.azurewebsites.net/api
```

## Authentication

All endpoints except `/health` require a function key passed as a query parameter:

```
?code=<function-key>
```

## Data Layer Endpoints

### GET /get-module-registry

Returns all registered detection modules.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| include_disabled | boolean | No | Include disabled modules (default: false) |

**Response:**

```json
[
  {
    "moduleId": "abandoned-resources",
    "displayName": "Abandoned Resources",
    "description": "Detects orphaned disks, IPs, and other unused resources",
    "enabled": true,
    "version": "1.0.0"
  }
]
```

### POST /save-findings

Saves detection findings to the findings-history container.

**Request Body:**

```json
{
  "executionId": "exec-2026-01-10-001",
  "moduleId": "abandoned-resources",
  "findings": [
    {
      "findingId": "finding-001",
      "subscriptionId": "12345678-1234-1234-1234-123456789abc",
      "resourceId": "/subscriptions/.../disks/orphaned-disk",
      "resourceType": "microsoft.compute/disks",
      "category": "abandoned",
      "severity": "medium",
      "estimatedMonthlyCost": 50.00
    }
  ]
}
```

**Response:**

```json
{
  "saved": 1,
  "executionId": "exec-2026-01-10-001"
}
```

### GET /get-findings-history

Returns historical findings for a subscription.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| subscription_id | string | Yes | Subscription ID to query |
| limit | integer | No | Maximum results (default: 100) |
| status | string | No | Filter by status: `open` or `resolved` |

**Response:**

```json
[
  {
    "findingId": "finding-001",
    "subscriptionId": "12345678-1234-1234-1234-123456789abc",
    "resourceId": "/subscriptions/.../disks/orphaned-disk",
    "detectedAt": "2026-01-10T10:00:00Z",
    "status": "open",
    "estimatedMonthlyCost": 50.00
  }
]
```

### GET /get-findings-trends

Returns month-over-month findings trends for a detection module.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| module_id | string | Yes | Module ID (e.g., `abandoned-resources`) |
| months | integer | No | Number of months to analyze (default: 3) |
| subscription_id | string | No | Filter to specific subscription |

**Response:**

```json
{
  "moduleId": "abandoned-resources",
  "trends": [
    {
      "month": "2026-01",
      "totalFindings": 22,
      "totalCost": 850.00,
      "bySeverity": {
        "critical": 2,
        "high": 5,
        "medium": 10,
        "low": 5
      }
    },
    {
      "month": "2025-12",
      "totalFindings": 50,
      "totalCost": 1920.00
    }
  ],
  "summary": {
    "hasComparison": true,
    "findingsChange": -28,
    "findingsChangePercent": -56.0,
    "trend": "improving",
    "message": "Great progress! Findings decreased from 50 to 22..."
  }
}
```

### POST /get-subscription-owners

Returns owner information for specified subscriptions.

**Request Body:**

```json
{
  "subscriptionIds": [
    "12345678-1234-1234-1234-123456789abc",
    "87654321-4321-4321-4321-cba987654321"
  ]
}
```

**Response:**

```json
[
  {
    "subscriptionId": "12345678-1234-1234-1234-123456789abc",
    "subscriptionName": "Production",
    "ownerEmail": "owner@contoso.com",
    "ownerName": "John Doe",
    "teamName": "Platform Engineering"
  }
]
```

### GET /get-detection-targets

Returns subscriptions and management groups configured for scanning.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| include_disabled | boolean | No | Include disabled targets (default: false) |
| target_type | string | No | Filter by type: `subscription` or `managementGroup` |

**Response:**

```json
{
  "targets": [
    {
      "targetId": "12345678-1234-1234-1234-123456789abc",
      "targetType": "subscription",
      "displayName": "Production Subscription",
      "enabled": true,
      "teamName": "Platform Engineering",
      "ownerEmail": "platform@contoso.com"
    },
    {
      "targetId": "mg-corp",
      "targetType": "managementGroup",
      "displayName": "Corporate",
      "enabled": true
    }
  ],
  "count": 2,
  "subscriptionCount": 1,
  "managementGroupCount": 1
}
```

## Detection Layer Endpoints

### POST /abandoned-resources

Runs the abandoned resources detection module to find orphaned disks, IPs, load balancers, and other unused resources.

**Request Body:**

```json
{
  "executionId": "exec-2026-01-10-001",
  "subscriptionIds": [
    "12345678-1234-1234-1234-123456789abc"
  ],
  "configuration": {},
  "dryRun": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| executionId | string | Yes | Unique execution identifier |
| subscriptionIds | array | Yes | List of subscription IDs to scan |
| configuration | object | No | Module-specific configuration |
| dryRun | boolean | No | If true, simulates detection without saving results |

**Response:**

```json
{
  "moduleId": "abandoned-resources",
  "executionId": "exec-2026-01-10-001",
  "status": "success",
  "findings": [
    {
      "findingId": "finding-001",
      "subscriptionId": "12345678-1234-1234-1234-123456789abc",
      "resourceId": "/subscriptions/.../disks/orphaned-disk",
      "resourceType": "microsoft.compute/disks",
      "resourceName": "orphaned-disk",
      "category": "abandoned",
      "severity": "medium",
      "confidenceScore": 85,
      "confidenceLevel": "high",
      "incursCost": true,
      "estimatedMonthlyCost": 50.00,
      "detectedAt": "2026-01-10T10:00:00Z"
    }
  ],
  "summary": {
    "totalFindings": 1,
    "totalEstimatedMonthlyCost": 50.00,
    "bySeverity": {
      "medium": 1
    },
    "byCategory": {
      "abandoned": 1
    }
  },
  "errors": []
}
```

## Notification Layer Endpoints

### POST /send-optimization-email

Sends an optimization report email to a subscription owner via Logic App.

**Request Body:**

```json
{
  "ownerEmail": "owner@contoso.com",
  "ownerName": "John Doe",
  "subscriptionId": "12345678-1234-1234-1234-123456789abc",
  "subscriptionName": "Production",
  "findings": [
    {
      "resourceName": "orphaned-disk",
      "resourceType": "microsoft.compute/disks",
      "severity": "medium",
      "estimatedMonthlyCost": 50.00
    }
  ],
  "trends": {
    "findingsChange": -10,
    "trend": "improving"
  },
  "totalEstimatedMonthlyCost": 50.00
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| ownerEmail | string | Yes | Recipient email address |
| ownerName | string | No | Recipient display name |
| subscriptionId | string | Yes | Subscription ID for the report |
| subscriptionName | string | No | Subscription display name |
| findings | array | Yes | List of findings to include |
| trends | object | No | Trend data for comparison |
| totalEstimatedMonthlyCost | number | No | Total monthly cost of findings |

**Response:**

```json
{
  "status": "sent",
  "message": "Email sent successfully"
}
```

**Error Codes:**

| Status | Description |
|--------|-------------|
| 400 | Invalid request body or missing required fields |
| 500 | Error sending email via Logic App |
| 503 | LOGIC_APP_URL environment variable not configured |

## Health Check

### GET /health

Returns the health status of the function app. This endpoint does not require authentication.

**Response:**

```json
{
  "status": "healthy",
  "service": "optimization-agent"
}
```

## Error Responses

All endpoints return errors in a consistent format:

```json
{
  "error": "Description of the error"
}
```

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Invalid input or missing required parameters |
| 500 | Internal Server Error - Unexpected error during processing |
| 503 | Service Unavailable - Required configuration missing |
