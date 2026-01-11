# Configure Logic App for Azure Optimization Agent
# This script creates the Office 365 API connection, updates the workflow, and outputs the trigger URL.

param(
    [string]$ResourceGroup = "rg-optimization-agent-cenus",
    [string]$LogicAppName = "logic-optimization-agent-email-cenus",
    [string]$Location = "centralus",
    [string]$ConnectionName = "office365"
)

$ErrorActionPreference = "Stop"

Write-Host "Configuring Logic App: $LogicAppName" -ForegroundColor Cyan
Write-Host "Resource Group: $ResourceGroup"
Write-Host ""

# Get subscription ID
$SUBSCRIPTION_ID = az account show --query id -o tsv
Write-Host "Subscription: $SUBSCRIPTION_ID"
Write-Host ""

# Step 1: Create Office 365 API connection
Write-Host "Creating Office 365 API connection..." -ForegroundColor Yellow
az resource create `
    --resource-group $ResourceGroup `
    --resource-type Microsoft.Web/connections `
    --name $ConnectionName `
    --properties "{`"displayName`": `"$ConnectionName`", `"api`": {`"id`": `"/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.Web/locations/$Location/managedApis/office365`"}}" `
    --output none
Write-Host "  Created connection: $ConnectionName" -ForegroundColor Green
Write-Host ""

# Step 2: Update Logic App workflow
Write-Host "Updating Logic App workflow..." -ForegroundColor Yellow
$workflow = Get-Content -Raw src/logic-apps/send-optimization-email/workflow.json | ConvertFrom-Json

# Add $connections parameter declaration to the definition
$workflow.definition.parameters = @{
    '$connections' = @{
        defaultValue = @{}
        type = "Object"
    }
}

$body = @{
    location = $Location
    properties = @{
        definition = $workflow.definition
        parameters = @{
            '$connections' = @{
                value = @{
                    office365 = @{
                        connectionId = "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$ResourceGroup/providers/Microsoft.Web/connections/$ConnectionName"
                        connectionName = $ConnectionName
                        id = "/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.Web/locations/$Location/managedApis/office365"
                    }
                }
            }
        }
    }
} | ConvertTo-Json -Depth 20 -Compress

az rest --method PUT `
    --uri "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$ResourceGroup/providers/Microsoft.Logic/workflows/$LogicAppName`?api-version=2016-06-01" `
    --body $body `
    --output none
Write-Host "  Workflow updated" -ForegroundColor Green
Write-Host ""

# Step 3: Get OAuth consent link
Write-Host "OAuth Authorization Required" -ForegroundColor Yellow
Write-Host "-" * 50
$consentLink = az rest --method POST `
    --uri "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$ResourceGroup/providers/Microsoft.Web/connections/$ConnectionName/listConsentLinks?api-version=2016-06-01" `
    --body "{`"parameters`": [{`"parameterName`": `"token`", `"redirectUrl`": `"https://portal.azure.com`"}]}" `
    --query "value[0].link" -o tsv

Write-Host "Open this URL in your browser to authorize Office 365:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  $consentLink"
Write-Host ""

# Step 4: Get trigger URL
Write-Host "Logic App Trigger URL" -ForegroundColor Yellow
Write-Host "-" * 50
$triggerUrl = az rest --method POST `
    --uri "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$ResourceGroup/providers/Microsoft.Logic/workflows/$LogicAppName/triggers/When_a_HTTP_request_is_received/listCallbackUrl?api-version=2016-06-01" `
    --query value -o tsv

Write-Host $triggerUrl -ForegroundColor Cyan
Write-Host ""

Write-Host "Done! Remember to complete OAuth authorization before testing." -ForegroundColor Green
