# Deployment Guide

## Prerequisites

- Azure CLI authenticated (`az login`)
- Python 3.11+
- Azure Functions Core Tools v4

## Step 1: Deploy Infrastructure

```bash
az group create --name rg-optimization-agent --location eastus

az deployment group create --resource-group rg-optimization-agent --template-file infra/main.bicep --parameters infra/main.bicepparam
```

Note the resource names from deployment output (Function App, Logic App, Cosmos DB).

## Step 2: Deploy Function App

```bash
cd src/functions

zip -r /tmp/functions-deploy.zip . -x "*.pyc" -x "__pycache__/*" -x ".venv/*" -x ".python_packages/*"

az functionapp deployment source config-zip --name <function-app-name> --resource-group rg-optimization-agent --src /tmp/functions-deploy.zip --build-remote true
```

Verify:
```bash
curl https://<function-app-name>.azurewebsites.net/api/health
```

## Step 3: Seed Cosmos DB

In Azure Portal > Cosmos DB > Data Explorer:

**Module Registry** (`optimization-db` > `module-registry` > New Item):
- Paste contents of `data/seed/module-registry.json`

**Detection Targets** (`optimization-db` > `detection-targets` > New Item):
- Add one document per target subscription/management group:

```json
{
  "id": "<subscription-id>",
  "targetId": "<subscription-id>",
  "targetType": "subscription",
  "displayName": "Production",
  "enabled": true,
  "ownerEmails": ["team@contoso.com"],
  "ownerNames": ["Team Name"]
}
```

## Step 4: Configure Logic App

1. Portal > Logic App > **Logic app code view**
2. Paste contents of `src/logic-apps/send-optimization-email/workflow.json`
3. Save

4. Portal > Logic App > **API connections** > Add connection
5. Search "Office 365 Outlook" > Create > Sign in
6. Name connection `office365`

7. Copy the HTTP trigger URL from Logic App designer

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
PRINCIPAL_ID=$(az functionapp identity show --name <function-app-name> --resource-group rg-optimization-agent --query principalId --output tsv)

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
