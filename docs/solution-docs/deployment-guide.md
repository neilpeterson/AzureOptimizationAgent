# Deployment Guide

## Step 1: Deploy Infrastructure

```bash
az group create --name rg-optimization-agent-cenus --location centralus
az deployment group create --resource-group rg-optimization-agent-cenus --template-file infra/main.bicep --parameters infra/main.bicepparam
```

Note the resource names from deployment output (Function App, Logic App, Cosmos DB, AI Services endpoint).

## Step 2: Deploy Function App

```bash
cd src/functions
zip -r /tmp/functions-deploy.zip . -x "*.pyc" -x "__pycache__/*" -x ".venv/*" -x ".python_packages/*"
az functionapp deployment source config-zip --name func-optimization-agent-cenus --resource-group rg-optimization-agent-cenus --src /tmp/functions-deploy.zip --build-remote true
```

Verify using the health endpoint.
```bash
curl https://func-optimization-agent-cenus.azurewebsites.net/api/health
```

## Step 3: Seed Cosmos DB

First, edit `data/seed/detection-targets.sample.json` to configure your target subscriptions and management groups.

Then run the seed script (uses your Azure CLI credentials):

```bash
pip install azure-cosmos
python3 scripts/seed_cosmos.py
```

The script seeds both `module-registry` and `detection-targets` containers using upsert (safe to re-run).

## Step 4: Configure Logic App

The script creates the Office 365 API connection, updates the workflow definition, and outputs the HTTP trigger URL. It will also provide an OAuth consent URL - **open this in your browser to authorize the Office 365 connection**.

> **Portal alternative:** This can also be done manually in Azure Portal by navigating to the Logic App's code view to paste the workflow JSON, creating an Office 365 API connection, and authorizing it with your credentials.

```powershell
./scripts/configure_logic_app.ps1
```

After the script completes, copy the HTTP trigger URL from the output and add it to the Function App settings:

```bash
az functionapp config appsettings set \
  --name func-optimization-agent-cenus \
  --resource-group rg-optimization-agent-cenus \
  --settings "LOGIC_APP_URL=<paste-trigger-url-here>"
```

## Step 5: Configure AI Agent

Configure the agent in Azure AI Foundry with an OpenAPI tool using managed identity authentication.

### Step 5a: Get AI Foundry Managed Identity IDs

1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Select your project (`optimization-agent`)
3. Click **Manage** in the top-right menu
4. Click **Manage this resource in the Azure Portal**
5. Navigate to **Resource Management** → **Identity**
6. Copy the **Object (principal) ID** under System assigned
7. In the Azure portal, search for **Microsoft Entra ID**
8. Search for the object ID you copied and open it
9. Copy the **Application (client) ID**

Save both IDs - you'll need them in the next steps.

### Step 5b: Create App Registration (No Secret)

Create an app registration without a client secret:

1. In Azure portal, go to **Microsoft Entra ID** → **App registrations**
2. Click **+ New registration**
3. Configure:
   - **Name**: `func-optimization-agent-cenus`
   - **Supported account types**: **Accounts in this organizational directory only**
   - **Redirect URI**: Leave blank
4. Click **Register**
5. Copy the **Application (client) ID** from the overview page
6. Go to **Manage** → **Expose an API**
7. Click **Add** next to Application ID URI
8. Set it to: `https://func-optimization-agent-cenus.azurewebsites.net`
9. Click **Save**

**Important**: Do NOT create a client secret.

### Step 5c: Configure Entra Authentication on Function App

1. In Azure portal, navigate to your Function App (`func-optimization-agent-cenus`)
2. Select **Settings** → **Authentication** → **Add identity provider**
3. Select **Microsoft** as the identity provider
4. Under **App registration type**: Select **Provide the details of an existing app registration**
5. Enter the **Application (client) ID** from the app registration you created in Step 5b
6. Under **Client secret**: Leave empty (no secret required)
7. Under **Issuer URL**: Enter `https://login.microsoftonline.com/<tenant-id>/v2.0` (replace `<tenant-id>` with your Entra tenant ID)
8. Under **Client application requirement**: Select **Allow requests from specific client applications**
   - Enter the **Application (client) ID** from Step 5a (the AI Foundry identity)
9. Under **Identity requirement**: Select **Allow requests from specific identities**
   - Enter the **Object (principal) ID** from Step 5a (the AI Foundry identity)
10. Under **Unauthenticated requests**: Select **HTTP 401 Unauthorized: recommended for APIs**
11. Click **Add**

### Step 5d: Create the Agent with OpenAPI Tool

1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Select your AI Services resource (`aisvc-optimization-agent-201-eaus`)
3. Navigate to **Build** → **Agents**
4. Click **+ New agent**
5. Configure the agent:
   - **Name**: `optimization-agent`
   - **Model**: Select `gpt-4o`
   - **Instructions**: Paste contents of `src/agent/system_prompt.txt`
6. Add the OpenAPI tool:
   - Click **+ Add tool** → **OpenAPI**
   - **Name**: `optimization-agent-api`
   - **Description**: `Azure Optimization Agent API for detecting cost optimization opportunities`
   - **Authentication method**: `Managed Identity`
   - **Audience**: `https://func-optimization-agent-cenus.azurewebsites.net`
   - **Spec**: Paste contents of `src/functions/openapi.json`
7. Click **Save**

## Step 6: Configure RBAC

```bash
PRINCIPAL_ID=$(az functionapp identity show --name func-optimization-agent-cenus --resource-group rg-optimization-agent-cenus --query principalId --output tsv)

# For single subscription
az role assignment create --assignee $PRINCIPAL_ID --role "Reader" --scope /subscriptions/<subscription-id>

# For management group (multiple subscriptions)
az role assignment create --assignee $PRINCIPAL_ID --role "Reader" --scope /providers/Microsoft.Management/managementGroups/<mg-id>
```