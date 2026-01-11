// =============================================================================
// Azure Optimization Agent - Infrastructure
// =============================================================================
// Deploys all resources for the optimization agent solution:
// - Storage Account (for Function App)
// - Cosmos DB (serverless) with 5 containers
// - App Service Plan (consumption)
// - Function App with system-assigned managed identity
// - Logic App for email notifications
// =============================================================================

// =============================================================================
// Parameters
// =============================================================================

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Storage account name')
param storageAccountName string

@description('Application Insights name')
param appInsightsName string

@description('Cosmos DB account name')
param cosmosDbAccountName string

@description('Cosmos DB database name')
param cosmosDbDatabaseName string

@description('App Service Plan name')
param appServicePlanName string

@description('Function App name')
param functionAppName string

@description('Logic App name')
param logicAppName string

@description('Log Analytics workspace name')
param logAnalyticsWorkspaceName string

@description('Network Security Perimeter name')
param networkSecurityPerimeterName string = 'nsp-optimization-agent'

// =============================================================================
// Storage Account (for Function App)
// =============================================================================

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true // Required for Flex Consumption deployment
  }
  tags: {
    application: 'optimization-agent'
  }
}

// Blob container for Flex Consumption deployment packages
resource deploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/app-package-${functionAppName}'
  properties: {
    publicAccess: 'None'
  }
}

// =============================================================================
// Log Analytics Workspace
// =============================================================================

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
  tags: {
    application: 'optimization-agent'
  }
}

// =============================================================================
// Application Insights
// =============================================================================

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Request_Source: 'rest'
    WorkspaceResourceId: logAnalyticsWorkspace.id
  }
  tags: {
    application: 'optimization-agent'
  }
}

// =============================================================================
// Cosmos DB Account (Serverless)
// =============================================================================

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: cosmosDbAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
  }
  tags: {
    application: 'optimization-agent'
  }
}

// Cosmos DB Database
resource cosmosDbDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosDbAccount
  name: cosmosDbDatabaseName
  properties: {
    resource: {
      id: cosmosDbDatabaseName
    }
  }
}

// Container: module-registry
resource containerModuleRegistry 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDbDatabase
  name: 'module-registry'
  properties: {
    resource: {
      id: 'module-registry'
      partitionKey: {
        paths: ['/moduleId']
        kind: 'Hash'
      }
    }
  }
}

// Container: findings-history (365-day TTL)
resource containerFindingsHistory 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDbDatabase
  name: 'findings-history'
  properties: {
    resource: {
      id: 'findings-history'
      partitionKey: {
        paths: ['/subscriptionId']
        kind: 'Hash'
      }
      defaultTtl: 31536000 // 365 days in seconds
    }
  }
}

// Container: subscription-owners
resource containerSubscriptionOwners 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDbDatabase
  name: 'subscription-owners'
  properties: {
    resource: {
      id: 'subscription-owners'
      partitionKey: {
        paths: ['/subscriptionId']
        kind: 'Hash'
      }
    }
  }
}

// Container: execution-logs (90-day TTL)
resource containerExecutionLogs 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDbDatabase
  name: 'execution-logs'
  properties: {
    resource: {
      id: 'execution-logs'
      partitionKey: {
        paths: ['/executionId']
        kind: 'Hash'
      }
      defaultTtl: 7776000 // 90 days in seconds
    }
  }
}

// Container: detection-targets
resource containerDetectionTargets 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDbDatabase
  name: 'detection-targets'
  properties: {
    resource: {
      id: 'detection-targets'
      partitionKey: {
        paths: ['/targetId']
        kind: 'Hash'
      }
    }
  }
}

// =============================================================================
// App Service Plan (Flex Consumption)
// =============================================================================

resource appServicePlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: appServicePlanName
  location: location
  kind: 'functionapp'
  sku: {
    tier: 'FlexConsumption'
    name: 'FC1'
  }
  properties: {
    reserved: true // Required for Linux
  }
  tags: {
    application: 'optimization-agent'
  }
}

// =============================================================================
// Function App (Flex Consumption)
// =============================================================================

// Storage account connection string for Flex Consumption
var storageConnectionString = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net'

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storageAccount.properties.primaryEndpoints.blob}app-package-${functionAppName}'
          authentication: {
            type: 'StorageAccountConnectionString'
            storageAccountConnectionStringName: 'DEPLOYMENT_STORAGE_CONNECTION_STRING'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: 100
        instanceMemoryMB: 2048
      }
      runtime: {
        name: 'python'
        version: '3.11'
      }
    }
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: storageConnectionString
        }
        {
          name: 'DEPLOYMENT_STORAGE_CONNECTION_STRING'
          value: storageConnectionString
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'COSMOS_ENDPOINT'
          value: cosmosDbAccount.properties.documentEndpoint
        }
        {
          name: 'COSMOS_DATABASE'
          value: cosmosDbDatabaseName
        }
      ]
    }
  }
  tags: {
    application: 'optimization-agent'
  }
  dependsOn: [
    deploymentContainer
  ]
}

// =============================================================================
// Logic App (Consumption)
// =============================================================================

resource logicApp 'Microsoft.Logic/workflows@2019-05-01' = {
  name: logicAppName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    state: 'Enabled'
    definition: {
      '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#'
      contentVersion: '1.0.0.0'
      parameters: {}
      triggers: {
        manual: {
          type: 'Request'
          kind: 'Http'
          inputs: {
            schema: {
              type: 'object'
              properties: {
                recipientEmail: {
                  type: 'string'
                }
                ccEmails: {
                  type: 'array'
                  items: {
                    type: 'string'
                  }
                }
                subscriptionName: {
                  type: 'string'
                }
                recommendations: {
                  type: 'string'
                }
                summary: {
                  type: 'object'
                }
              }
              required: [
                'recipientEmail'
                'subscriptionName'
                'recommendations'
              ]
            }
          }
        }
      }
      actions: {
        Response: {
          type: 'Response'
          kind: 'Http'
          inputs: {
            statusCode: 200
            body: {
              status: 'Email workflow triggered'
              message: 'Configure Office 365 or SendGrid connector to complete email delivery'
            }
          }
          runAfter: {}
        }
      }
      outputs: {}
    }
  }
  tags: {
    application: 'optimization-agent'
  }
}

// =============================================================================
// RBAC: Function App -> Cosmos DB Data Contributor
// =============================================================================

@description('Cosmos DB Built-in Data Contributor role ID')
var cosmosDbDataContributorRoleId = '00000000-0000-0000-0000-000000000002'

resource cosmosDbRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-11-15' = {
  parent: cosmosDbAccount
  name: guid(cosmosDbAccount.id, functionApp.id, cosmosDbDataContributorRoleId)
  properties: {
    roleDefinitionId: '${cosmosDbAccount.id}/sqlRoleDefinitions/${cosmosDbDataContributorRoleId}'
    principalId: functionApp.identity.principalId
    scope: cosmosDbAccount.id
  }
}

// =============================================================================
// RBAC: Function App -> Storage Account (for managed identity access)
// =============================================================================

@description('Storage Blob Data Owner role ID')
var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'

@description('Storage Account Contributor role ID')
var storageAccountContributorRoleId = '17d1049b-9a84-46fb-8f53-869881c3d3ab'

@description('Storage Queue Data Contributor role ID')
var storageQueueDataContributorRoleId = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'

resource storageBlobDataOwnerAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, storageBlobDataOwnerRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleId)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageAccountContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, storageAccountContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageAccountContributorRoleId)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageQueueDataContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, functionApp.id, storageQueueDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRoleId)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// =============================================================================
// Network Security Perimeter
// =============================================================================

resource networkSecurityPerimeter 'Microsoft.Network/networkSecurityPerimeters@2023-08-01-preview' = {
  name: networkSecurityPerimeterName
  location: location
  tags: {
    application: 'optimization-agent'
  }
}

resource nspProfile 'Microsoft.Network/networkSecurityPerimeters/profiles@2023-08-01-preview' = {
  parent: networkSecurityPerimeter
  name: 'default-profile'
  location: location
  properties: {}
}

// Associate Storage Account with NSP in Learning (transient) mode
resource storageNspAssociation 'Microsoft.Network/networkSecurityPerimeters/resourceAssociations@2023-08-01-preview' = {
  parent: networkSecurityPerimeter
  name: 'storage-association'
  location: location
  properties: {
    privateLinkResource: {
      id: storageAccount.id
    }
    profile: {
      id: nspProfile.id
    }
    accessMode: 'Learning'
  }
}

// Associate Cosmos DB with NSP in Learning (transient) mode
resource cosmosDbNspAssociation 'Microsoft.Network/networkSecurityPerimeters/resourceAssociations@2023-08-01-preview' = {
  parent: networkSecurityPerimeter
  name: 'cosmosdb-association'
  location: location
  properties: {
    privateLinkResource: {
      id: cosmosDbAccount.id
    }
    profile: {
      id: nspProfile.id
    }
    accessMode: 'Learning'
  }
}

// =============================================================================
// Outputs
// =============================================================================

@description('Function App name')
output functionAppNameOutput string = functionApp.name

@description('Function App URL')
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'

@description('Function App principal ID (for RBAC assignments)')
output functionAppPrincipalId string = functionApp.identity.principalId

@description('Cosmos DB account name')
output cosmosDbAccountNameOutput string = cosmosDbAccount.name

@description('Cosmos DB endpoint')
output cosmosDbEndpoint string = cosmosDbAccount.properties.documentEndpoint

@description('Logic App name')
output logicAppNameOutput string = logicApp.name

@description('Logic App resource ID (use Azure CLI to get trigger URL)')
output logicAppResourceId string = logicApp.id

@description('Application Insights name')
output appInsightsNameOutput string = appInsights.name

@description('Storage account name')
output storageAccountNameOutput string = storageAccount.name

@description('Log Analytics workspace name')
output logAnalyticsWorkspaceNameOutput string = logAnalyticsWorkspace.name

@description('Log Analytics workspace ID')
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id

@description('Network Security Perimeter name')
output networkSecurityPerimeterNameOutput string = networkSecurityPerimeter.name

@description('Network Security Perimeter ID')
output networkSecurityPerimeterId string = networkSecurityPerimeter.id
