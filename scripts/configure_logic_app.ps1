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
if (-not $SUBSCRIPTION_ID) {
    Write-Host "ERROR: Failed to get subscription ID. Are you logged in to Azure CLI?" -ForegroundColor Red
    exit 1
}
Write-Host "Subscription: $SUBSCRIPTION_ID"
Write-Host ""

# Step 1: Create Office 365 API connection
Write-Host "Creating Office 365 API connection..." -ForegroundColor Yellow

$connectionProperties = @{
    displayName = $ConnectionName
    api = @{
        id = "/subscriptions/$SUBSCRIPTION_ID/providers/Microsoft.Web/locations/$Location/managedApis/office365"
    }
} | ConvertTo-Json -Compress

$createResult = az resource create `
    --resource-group $ResourceGroup `
    --resource-type Microsoft.Web/connections `
    --name $ConnectionName `
    --location $Location `
    --properties $connectionProperties 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create API connection" -ForegroundColor Red
    Write-Host $createResult -ForegroundColor Red
    exit 1
}
Write-Host "  Created connection: $ConnectionName" -ForegroundColor Green
Write-Host ""

# Verify connection exists
$connectionCheck = az resource show `
    --resource-group $ResourceGroup `
    --resource-type Microsoft.Web/connections `
    --name $ConnectionName `
    --query id -o tsv 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Connection was not created successfully" -ForegroundColor Red
    Write-Host $connectionCheck -ForegroundColor Red
    exit 1
}
Write-Host "  Verified connection exists" -ForegroundColor Green
Write-Host ""

# Step 2: Update Logic App workflow
Write-Host "Updating Logic App workflow..." -ForegroundColor Yellow

# Get the script's directory and find the workflow file
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$workflowPath = Join-Path $repoRoot "src/logic-apps/send-optimization-email/workflow.json"

if (-not (Test-Path $workflowPath)) {
    Write-Host "ERROR: Workflow file not found at: $workflowPath" -ForegroundColor Red
    exit 1
}

$workflow = Get-Content -Raw $workflowPath | ConvertFrom-Json

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

$updateResult = az rest --method PUT `
    --uri "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$ResourceGroup/providers/Microsoft.Logic/workflows/$LogicAppName`?api-version=2016-06-01" `
    --body $body 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to update Logic App workflow" -ForegroundColor Red
    Write-Host $updateResult -ForegroundColor Red
    exit 1
}
Write-Host "  Workflow updated" -ForegroundColor Green
Write-Host ""

# Step 3: Get OAuth consent link
Write-Host "OAuth Authorization Required" -ForegroundColor Yellow
Write-Host ("-" * 50)

$consentLink = az rest --method POST `
    --uri "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$ResourceGroup/providers/Microsoft.Web/connections/$ConnectionName/listConsentLinks?api-version=2016-06-01" `
    --body '{"parameters": [{"parameterName": "token", "redirectUrl": "https://portal.azure.com"}]}' `
    --query "value[0].link" -o tsv 2>&1

if ($LASTEXITCODE -ne 0 -or -not $consentLink) {
    Write-Host "WARNING: Could not get consent link automatically" -ForegroundColor Yellow
    Write-Host "Please authorize the connection manually in Azure Portal:" -ForegroundColor Yellow
    Write-Host "  1. Go to: https://portal.azure.com" -ForegroundColor Cyan
    Write-Host "  2. Navigate to: Resource Groups > $ResourceGroup > $ConnectionName" -ForegroundColor Cyan
    Write-Host "  3. Click 'Edit API connection' and authorize" -ForegroundColor Cyan
} else {
    Write-Host "Open this URL in your browser to authorize Office 365:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  $consentLink"
}
Write-Host ""

# Step 4: Get trigger URL
Write-Host "Logic App Trigger URL" -ForegroundColor Yellow
Write-Host ("-" * 50)

$triggerUrl = az rest --method POST `
    --uri "https://management.azure.com/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$ResourceGroup/providers/Microsoft.Logic/workflows/$LogicAppName/triggers/When_a_HTTP_request_is_received/listCallbackUrl?api-version=2016-06-01" `
    --query value -o tsv 2>&1

if ($LASTEXITCODE -ne 0 -or -not $triggerUrl) {
    Write-Host "WARNING: Could not get trigger URL. The Logic App may need to be enabled first." -ForegroundColor Yellow
    Write-Host "Get it manually from Azure Portal > Logic App > Overview" -ForegroundColor Yellow
} else {
    Write-Host $triggerUrl -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Add this URL to Function App settings:" -ForegroundColor Yellow
    Write-Host "  az functionapp config appsettings set --name func-optimization-agent-cenus --resource-group $ResourceGroup --settings `"LOGIC_APP_URL=$triggerUrl`"" -ForegroundColor Cyan
}
Write-Host ""

Write-Host "Done! Remember to complete OAuth authorization before testing." -ForegroundColor Green
