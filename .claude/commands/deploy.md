# Deploy Azure Infrastructure

Deploy the Azure Optimization Agent infrastructure to Azure.

## Instructions

1. Ask the user for the following information using AskUserQuestion:
   - Resource group name
   - Azure location (offer common options: eastus, westus2, centralus, westeurope)

2. Check if the resource group exists. If not, create it with:
   ```
   az group create --name <resource-group-name> --location <location>
   ```

3. Deploy the Bicep template:
   ```
   az deployment group create \
     --resource-group <resource-group-name> \
     --template-file infra/main.bicep \
     --parameters infra/main.bicepparam
   ```

4. Display the deployment outputs to the user, including:
   - Function App URL
   - Cosmos DB endpoint
   - Logic App resource ID

5. Remind the user to get the Logic App trigger URL with:
   ```
   az logic workflow show --resource-group <resource-group-name> --name logic-optimization-agent-email --query "accessEndpoint"
   ```
