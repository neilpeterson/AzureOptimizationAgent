using 'main.bicep'

// =============================================================================
// Azure Optimization Agent - Parameters
// =============================================================================

// Resource names
param storageAccountName = 'stgoptimcenus'
param appInsightsName = 'appi-optimization-agent-cenus'
param cosmosDbAccountName = 'cosmos-optimization-agent-cenus'
param cosmosDbDatabaseName = 'db-optimization-agent-cenus'
param appServicePlanName = 'asp-optimization-agent-cenus'
param functionAppName = 'func-optimization-agent-cenus'
param logicAppName = 'logic-optimization-agent-email-cenus'
param logAnalyticsWorkspaceName = 'log-optimization-agent-cenus'
