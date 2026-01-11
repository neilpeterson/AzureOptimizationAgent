# Deployment Guide

This guide walks through deploying the Azure Optimization Agent from the command line and Azure Portal.

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Azure subscription with Owner or Contributor access
- Python 3.11+ installed locally
- Azure Functions Core Tools (`npm install -g azure-functions-core-tools@4`)

## Step 1: Deploy Infrastructure (Bicep)

The Bicep template deploys all required Azure resources:
- Storage Account
- Cosmos DB (Serverless) with 5 containers
- Function App (Consumption plan, Python 3.11)
- Logic App (Consumption)
- Log Analytics Workspace
- Application Insights

### 1.1 Create Resource Group

```bash
az group create --name rg-optimization-agent --location eastus
```

### 1.2 Deploy Bicep Template

```bash
az deployment group create --resource-group rg-optimization-agent --template-file infra/main.bicep --parameters infra/main.bicepparam
```

### 1.4 Note Resource Names

After deployment, note the following resource names from the output or Azure Portal:

- Function App name (e.g., `func-optimization-agent-tme-two`)
- Logic App name (e.g., `logic-optimization-agent-tme-two`)
- Cosmos DB account name (e.g., `cosmos-optimization-agent-tme-two`)

## Step 2: Deploy Function App

```bash
cd src/functions
```

### 2.2 Deploy to Azure

```bash
# Create deployment package
zip -r /tmp/functions-deploy.zip . -x "*.pyc" -x "__pycache__/*" -x ".venv/*" -x ".python_packages/*"

# Deploy with remote build
az functionapp deployment source config-zip --name <function-app-name> --resource-group rg-optimization-agent --src /tmp/functions-deploy.zip --build-remote true
```
### 2.4 Get Function App URL and Key

```bash
# Get the Function App URL
az functionapp show --name func-optimization-agent-tme-two --resource-group rg-optimization-agent-tme-two --query defaultHostName --output tsv

# Get the default function key
az functionapp keys list --name <function-app-name> --resource-group rg-optimization-agent --query functionKeys.default --output tsv
```

### 2.5 Test Health Endpoint

```bash
curl https://<function-app-name>.azurewebsites.net/api/health
```

## Step 3: Seed Cosmos DB Data

### 3.1 Seed Module Registry

From the Azure Portal:

1. Navigate to your Cosmos DB account
2. Go to **Data Explorer**
3. Expand **optimization-db** > **module-registry**
4. Click **New Item**
5. Paste the contents of `data/seed/module-registry.json`
6. Click **Save**

Alternatively, use the Azure CLI:

```bash
# Get Cosmos DB endpoint
COSMOS_ENDPOINT=$(az cosmosdb show --name <cosmos-account-name> --resource-group rg-optimization-agent --query documentEndpoint --output tsv)

# Use Azure CLI extension or Data Explorer to insert the document
```

### 3.2 Seed Detection Targets

Detection targets define which subscriptions and management groups to scan.

The sample file `data/seed/detection-targets.sample.json` contains an array of example documents. Each document must be inserted individually (not the entire array).

1. Open `data/seed/detection-targets.sample.json` for reference
2. For each target you want to add:
   - Navigate to **optimization-db** > **detection-targets** in Data Explorer
   - Click **New Item**
   - Paste a single document (not the array) with your actual subscription/management group ID
   - Click **Save**

Example target document:
```json
{
  "id": "12345678-1234-1234-1234-123456789abc",
  "targetId": "12345678-1234-1234-1234-123456789abc",
  "targetType": "subscription",
  "displayName": "Production Subscription",
  "enabled": true,
  "teamName": "Platform Engineering",
  "ownerEmail": "platform@contoso.com"
}
```

For management groups, use `"targetType": "managementGroup"`.

See [Detection Targets & Owners](detection-targets.md) for detailed schema and examples.

### 3.3 Seed Subscription Owners

Subscription owners define who receives email notifications for each subscription.

The sample file `data/seed/subscription-owners.sample.json` contains an array of example documents. Each document must be inserted individually (not the entire array).

1. Open `data/seed/subscription-owners.sample.json` for reference
2. For each subscription owner:
   - Navigate to **optimization-db** > **subscription-owners** in Data Explorer
   - Click **New Item**
   - Paste a single document with your actual subscription ID and owner email
   - Click **Save**

Example owner document:
```json
{
  "id": "12345678-1234-1234-1234-123456789abc",
  "subscriptionId": "12345678-1234-1234-1234-123456789abc",
  "subscriptionName": "Production",
  "ownerEmail": "owner@contoso.com",
  "ownerName": "John Doe",
  "teamName": "Platform Engineering"
}
```

## Step 4: Deploy Logic App

The Logic App handles email notifications. Deployment requires two steps: deploying the workflow and configuring the Office 365 connection.

### 4.1 Deploy Logic App Workflow (Portal)

1. Navigate to your Logic App in the Azure Portal
2. Go to **Logic app code view** under Development Tools
3. Copy the contents of `src/logic-apps/send-optimization-email/workflow.json`
4. Paste into the code view editor
5. Click **Save**

### 4.2 Configure Office 365 Connection

1. In the Logic App, go to **API connections** under Settings
2. Click **Add a connection**
3. Search for "Office 365 Outlook"
4. Click **Create**
5. Sign in with an account that will send the notification emails
6. Name the connection `office365` (must match the workflow reference)

### 4.3 Update Workflow with Connection

After creating the connection:

1. Go back to **Logic app designer**
2. Click on the "Send email" action
3. Verify the connection is properly linked
4. Save the workflow

### 4.4 Get Logic App Trigger URL

1. In the Logic App, go to **Overview**
2. Click **Workflow** > **send-optimization-email** (if using Standard tier)
3. Copy the **Callback URL** from the HTTP trigger

For Consumption tier:
1. Go to **Logic app designer**
2. Click on the HTTP trigger
3. Copy the **HTTP POST URL**

## Step 5: Deploy AI Agent

The AI Agent is deployed in Azure AI Foundry (formerly Azure AI Studio).

### 5.1 Create Azure AI Foundry Project

1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Create a new **Project** or select an existing one
3. Note the project's **Connection String** from Settings

### 5.2 Deploy GPT-4o Model

1. In your AI Foundry project, go to **Model catalog**
2. Select **GPT-4o**
3. Click **Deploy**
4. Note the deployment name

### 5.3 Create the Agent

1. Go to **Agents** in your AI Foundry project
2. Click **New agent**
3. Configure:
   - **Name:** optimization-agent
   - **Model:** Select your GPT-4o deployment
   - **Instructions:** Paste contents of `src/agent/system_prompt.txt`

### 5.4 Add Tool Definitions

1. In the agent configuration, go to **Tools**
2. Click **Add tool** > **Function**
3. For each tool in `src/agent/tool_definitions.json`:
   - Copy the tool definition
   - Add it to the agent
4. Save the agent

### 5.5 Configure Environment Variables

For running the agent locally, set these environment variables:

```bash
export AZURE_AI_PROJECT_CONNECTION_STRING="<your-connection-string>"
export FUNCTION_APP_URL="https://<function-app-name>.azurewebsites.net"
export FUNCTION_APP_KEY="<your-function-key>"
```

### 5.6 Test the Agent

```bash
cd src/agent

# Install dependencies
pip install azure-ai-projects azure-identity

# Run with dry-run mode
python run_agent.py --subscriptions <subscription-id> --dry-run
```

## Step 6: Configure RBAC Permissions

The Function App's managed identity needs permissions to query Azure resources across subscriptions.

### 6.1 Assign Reader Role

At the Management Group or Subscription level:

```bash
# Get the Function App's managed identity principal ID
PRINCIPAL_ID=$(az functionapp identity show --name <function-app-name> --resource-group rg-optimization-agent --query principalId --output tsv)

# Assign Reader role at subscription scope
az role assignment create --assignee $PRINCIPAL_ID --role "Reader" --scope /subscriptions/<target-subscription-id>

# Assign Cost Management Reader for cost data
az role assignment create --assignee $PRINCIPAL_ID --role "Cost Management Reader" --scope /subscriptions/<target-subscription-id>
```

### 6.2 For Multiple Subscriptions

For scanning multiple subscriptions, assign roles at the Management Group level:

```bash
az role assignment create --assignee $PRINCIPAL_ID --role "Reader" --scope /providers/Microsoft.Management/managementGroups/<management-group-id>
```

## Validation Checklist

After deployment, verify each component:

| Component | Validation |
|-----------|------------|
| Infrastructure | All resources visible in Azure Portal |
| Function App | Health endpoint returns `{"status": "healthy"}` |
| Cosmos DB | 5 containers created (detection-targets, module-registry, findings-history, subscription-owners, execution-logs) |
| Detection Targets | At least one enabled target in `detection-targets` container |
| Module Registry | `abandoned-resources` module registered and enabled |
| Subscription Owners | Owner mappings for all target subscriptions |
| Logic App | Workflow shows "Enabled" status |
| AI Agent | Test run completes with `--dry-run` |
| RBAC | Agent can query target subscriptions |

## Troubleshooting

### Function App Issues

```bash
# View function logs
az functionapp log deployment list --name <function-app-name> --resource-group rg-optimization-agent

# Stream live logs
func azure functionapp logstream <function-app-name>
```

### Cosmos DB Connection Issues

Verify the managed identity has the `Cosmos DB Built-in Data Contributor` role:

```bash
az cosmosdb sql role assignment list --account-name <cosmos-account-name> --resource-group rg-optimization-agent
```

### Logic App Connection Issues

1. Check API connection status in Azure Portal
2. Re-authorize the Office 365 connection if expired
3. Verify the connection name matches `office365` in the workflow

### Agent Tool Call Failures

1. Verify `FUNCTION_APP_URL` includes `https://` prefix
2. Verify `FUNCTION_APP_KEY` is the correct function key
3. Check Function App logs for errors during tool execution
