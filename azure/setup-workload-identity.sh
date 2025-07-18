#!/bin/bash

# Setup Azure Workload Identity for secure Key Vault access
# This script configures Azure Workload Identity to allow pods to access Key Vault

set -e

# Load Azure configuration
if [ -f "azure-config.env" ]; then
    source azure-config.env
else
    echo "❌ Azure configuration not found. Please run setup-azure.sh first."
    exit 1
fi

# Configuration
MANAGED_IDENTITY_NAME="vocare-workload-identity"
SERVICE_ACCOUNT_NAME="vocare-workload-identity"
SERVICE_ACCOUNT_NAMESPACE="vocare-restaurant" # Ensure this namespace exists in K8s!

echo "🔐 Setting up Azure Workload Identity..."
echo "Resource Group: $RESOURCE_GROUP"
echo "AKS Cluster: $AKS_CLUSTER_NAME"
echo "Key Vault: $KEYVAULT_NAME"
echo "Managed Identity: $MANAGED_IDENTITY_NAME"
echo ""

# Get AKS OIDC issuer URL
echo "🔍 Getting AKS OIDC issuer URL..."
AKS_OIDC_ISSUER=$(az aks show --name "$AKS_CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" --query "oidcIssuerProfile.issuerUrl" -o tsv)

if [ -z "$AKS_OIDC_ISSUER" ]; then
    echo "❌ OIDC issuer not found. Enabling OIDC issuer on AKS cluster..."
    az aks update --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER_NAME" --enable-oidc-issuer --no-wait # --no-wait to make script continue faster
    echo "Waiting for OIDC issuer to be enabled. This may take a few minutes..."
    # You might want a loop here to wait for the OIDC issuer URL to appear
    for i in {1..10}; do
        sleep 30 # Wait 30 seconds
        AKS_OIDC_ISSUER=$(az aks show --name "$AKS_CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" --query "oidcIssuerProfile.issuerUrl" -o tsv 2>/dev/null)
        if [ -n "$AKS_OIDC_ISSUER" ]; then
            echo "OIDC issuer enabled: $AKS_OIDC_ISSUER"
            break
        fi
        echo "Still waiting for OIDC issuer... ($i/10)"
        if [ $i -eq 10 ]; then
            echo "Timed out waiting for OIDC issuer. Please check AKS cluster status."
            exit 1
        fi
    done
else
    echo "OIDC Issuer already enabled: $AKS_OIDC_ISSUER"
fi

# Create managed identity
echo "🆔 Checking for existing managed identity..."
MANAGED_IDENTITY_CLIENT_ID=$(az identity show --name "$MANAGED_IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "clientId" -o tsv 2>/dev/null)

if [ -z "$MANAGED_IDENTITY_CLIENT_ID" ]; then
    echo "Managed identity not found. Creating..."
    az identity create --name "$MANAGED_IDENTITY_NAME" --resource-group "$RESOURCE_GROUP"
    MANAGED_IDENTITY_CLIENT_ID=$(az identity show --name "$MANAGED_IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "clientId" -o tsv)
    MANAGED_IDENTITY_OBJECT_ID=$(az identity show --name "$MANAGED_IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "principalId" -o tsv)
else
    echo "Managed identity '$MANAGED_IDENTITY_NAME' already exists."
    MANAGED_IDENTITY_OBJECT_ID=$(az identity show --name "$MANAGED_IDENTITY_NAME" --resource-group "$RESOURCE_GROUP" --query "principalId" -o tsv)
fi

echo "Managed Identity Client ID: $MANAGED_IDENTITY_CLIENT_ID"
echo "Managed Identity Object ID: $MANAGED_IDENTITY_OBJECT_ID"

# Grant Key Vault access to managed identity using Azure RBAC
echo "🔑 Checking Key Vault access for managed identity..."
KEYVAULT_RESOURCE_ID=$(az keyvault show --name "$KEYVAULT_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

# Check if the role assignment already exists
# Note: Checking for specific role assignment can be tricky.
# A simpler approach for idempotency is to just try to create it.
# If it exists, 'az role assignment create' will usually error with a message
# "The role assignment already exists." which `set -e` will catch.
# For true idempotency, you'd list and check. For now, we rely on the error.
echo "Attempting to assign 'Key Vault Secrets User' role..."
if ! az role assignment create \
    --assignee "$MANAGED_IDENTITY_OBJECT_ID" \
    --role "Key Vault Secrets User" \
    --scope "$KEYVAULT_RESOURCE_ID" 2>/dev/null; then
    # Check if the error indicates it already exists
    if az role assignment list --assignee "$MANAGED_IDENTITY_OBJECT_ID" --scope "$KEYVAULT_RESOURCE_ID" --role "Key Vault Secrets User" --query "[].id" -o tsv | grep -q .; then
        echo "Role 'Key Vault Secrets User' already assigned to managed identity."
    else
        echo "❌ Failed to assign role and it doesn't appear to exist. Please check permissions."
        exit 1
    fi
else
    echo "Role 'Key Vault Secrets User' assigned to managed identity."
fi


# Create federated identity credential
FEDERATED_CREDENTIAL_NAME="vocare-federated-credential"
echo "🔗 Checking for existing federated identity credential '$FEDERATED_CREDENTIAL_NAME'..."

# Check if federated credential already exists
# This command fails if it doesn't exist, so redirect stderr to /dev/null
FEDERATED_CREDENTIAL_EXISTS=$(az identity federated-credential show \
    --name "$FEDERATED_CREDENTIAL_NAME" \
    --identity-name "$MANAGED_IDENTITY_NAME" \
    --resource-group "$RESOURCE_GROUP" 2>/dev/null || echo "")

if [ -z "$FEDERATED_CREDENTIAL_EXISTS" ]; then
    echo "Federated identity credential not found. Creating..."
    az identity federated-credential create \
        --name "$FEDERATED_CREDENTIAL_NAME" \
        --identity-name "$MANAGED_IDENTITY_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --issuer "$AKS_OIDC_ISSUER" \
        --subject "system:serviceaccount:$SERVICE_ACCOUNT_NAMESPACE:$SERVICE_ACCOUNT_NAME"
    echo "Federated identity credential created."
else
    echo "Federated identity credential '$FEDERATED_CREDENTIAL_NAME' already exists."
fi


echo "✅ Azure Workload Identity setup completed!"
echo ""
echo "📋 Configuration details:"
echo "  Managed Identity Client ID: $MANAGED_IDENTITY_CLIENT_ID"
echo "  OIDC Issuer: $AKS_OIDC_ISSUER"
echo "  Service Account: $SERVICE_ACCOUNT_NAMESPACE/$SERVICE_ACCOUNT_NAME"
echo ""
echo "🔧 Next steps:"
echo "1. Update the service account with the managed identity client ID:"
# Use realpath and check existence for sed operations
SERVICE_ACCOUNT_YAML="../k8s/shared/service-account.yaml"
if [ -f "$SERVICE_ACCOUNT_YAML" ]; then
    echo "   Updating $SERVICE_ACCOUNT_YAML..."
    sed -i "s/REPLACE_WITH_MANAGED_IDENTITY_CLIENT_ID/$MANAGED_IDENTITY_CLIENT_ID/g" "$SERVICE_ACCOUNT_YAML"
else
    echo "   ⚠️ Warning: $SERVICE_ACCOUNT_YAML not found. Skipping sed for service account."
fi

echo ""
echo "2. Update the SecretProviderClass with Key Vault and tenant details:"
SECRET_PROVIDER_CLASS_YAML="../k8s/azure/keyvault/secret-provider-class.yaml"
if [ -f "$SECRET_PROVIDER_CLASS_YAML" ]; then
    echo "   Updating $SECRET_PROVIDER_CLASS_YAML..."
    TENANT_ID=$(az account show --query tenantId -o tsv)
    sed -i "s/REPLACE_WITH_KEYVAULT_NAME/$KEYVAULT_NAME/g" "$SECRET_PROVIDER_CLASS_YAML"
    sed -i "s/REPLACE_WITH_TENANT_ID/$TENANT_ID/g" "$SECRET_PROVIDER_CLASS_YAML" # Corrected sed syntax for variables
else
    echo "   ⚠️ Warning: $SECRET_PROVIDER_CLASS_YAML not found. Skipping sed for SecretProviderClass."
fi


echo ""
echo "3. Deploy the service account and SecretProviderClass:"
echo "   kubectl apply -f ../k8s/shared/service-account.yaml"
echo "   kubectl apply -f ../k8s/azure/keyvault/secret-provider-class.yaml"

# Save the managed identity client ID for later use
echo "MANAGED_IDENTITY_CLIENT_ID=$MANAGED_IDENTITY_CLIENT_ID" >> azure-config.env
echo "AKS_OIDC_ISSUER=$AKS_OIDC_ISSUER" >> azure-config.env

echo ""
echo "💾 Configuration updated in azure-config.env"