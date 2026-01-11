# Deployment Guide

## Step 1: Deploy Infrastructure

```bash
az group create --name rg-optimization-agent-cenus --location centralus
az deployment group create --resource-group rg-optimization-agent-cenus --template-file infra/main.bicep --parameters infra/main.bicepparam
```

Note the resource names from deployment output (Function App, Logic App, Cosmos DB).

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
python scripts/seed_cosmos.py
```

The script seeds both `module-registry` and `detection-targets` containers using upsert (safe to re-run).

## Step 4: Configure Logic App

The script creates the Office 365 API connection, updates the workflow definition, and outputs the HTTP trigger URL. It will also provide an OAuth consent URL - **open this in your browser to authorize the Office 365 connection**.

> **Portal alternative:** This can also be done manually in Azure Portal by navigating to the Logic App's code view to paste the workflow JSON, creating an Office 365 API connection, and authorizing it with your credentials.

```powershell
./scripts/configure_logic_app.ps1
```

## Step 5: Configure AI Agent

1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Create/select project, deploy GPT-4o model
3. Create agent with:
   - Instructions: `src/agent/system_prompt.txt`
   - Tools: each item from `src/agent/tool_definitions.json`

Test locally:
```bash
export AZURE_AI_PROJECT_CONNECTION_STRING="<connection-string>"
export FUNCTION_APP_URL="https://<function-app-name>.azurewebsites.net"
export FUNCTION_APP_KEY="<function-key>"

python src/agent/run_agent.py --dry-run
```

## Step 6: Configure RBAC

```bash
PRINCIPAL_ID=$(az functionapp identity show --name <function-app-name> --resource-group rg-optimization-agent-cenus --query principalId --output tsv)

# For single subscription
az role assignment create --assignee $PRINCIPAL_ID --role "Reader" --scope /subscriptions/<subscription-id>

# For management group (multiple subscriptions)
az role assignment create --assignee $PRINCIPAL_ID --role "Reader" --scope /providers/Microsoft.Management/managementGroups/<mg-id>
```

## Validation

| Component | Check |
|-----------|-------|
| Function App | `/api/health` returns `{"status": "healthy"}` |
| Cosmos DB | 4 containers exist |
| Detection Targets | At least one target with `ownerEmails` |
| Module Registry | `abandoned-resources` enabled |
| Logic App | Workflow enabled |
| RBAC | Function can query target subscriptions |
