#!/bin/bash

# Azure Setup Script for Vocare Restaurant Assistant
# This script sets up Azure resources needed for AKS deployment

set -e # Exit immediately if a command exits with a non-zero status.

# Configuration variables
RESOURCE_GROUP="vocare-restaurant-rg"
LOCATION="eastus"
AKS_CLUSTER_NAME="vocare-aks"
ACR_NAME="vocareacr"  # ACR names must be globally unique
KEYVAULT_NAME="vocare-kv"  # Key Vault names must be globally unique
STORAGE_ACCOUNT="vocarestorage"

echo "🚀 Setting up Azure resources for Vocare Restaurant Assistant..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

echo "📋 Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  AKS Cluster: $AKS_CLUSTER_NAME"
echo "  ACR Name: $ACR_NAME"
echo "  Key Vault: $KEYVAULT_NAME"
echo "  Storage Account: $STORAGE_ACCOUNT"
echo ""

read -p "Continue with this configuration? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# --- Create Resource Group ---
echo "🏗️  Checking/Creating resource group..."
if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    echo "  Resource group '$RESOURCE_GROUP' already exists. Skipping creation."
else
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
    echo "  Resource group '$RESOURCE_GROUP' created."
fi

# --- Create Azure Container Registry ---
echo "📦 Checking/Creating Azure Container Registry..."
if az acr show --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" &> /dev/null; then
    echo "  ACR '$ACR_NAME' already exists. Skipping creation."
    # Important: If it exists, ensure the SKU is correct for ACR Tasks (Standard/Premium)
    # The script created Basic, but you needed to upgrade. This ensures future runs don't downgrade.
    CURRENT_ACR_SKU=$(az acr show --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --query sku.name -o tsv)
    if [ "$CURRENT_ACR_SKU" != "Standard" ] && [ "$CURRENT_ACR_SKU" != "Premium" ]; then
        echo "  Warning: ACR '$ACR_NAME' is not in Standard or Premium SKU. Upgrading to Standard."
        az acr update --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Standard
    fi
else
    az acr create --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --sku Standard # Start with Standard directly
    echo "  ACR '$ACR_NAME' created."
fi


# --- Create AKS Cluster with ACR integration ---
echo "☸️  Checking/Creating AKS cluster (this may take 10-15 minutes if creating)..."
if az aks show --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER_NAME" &> /dev/null; then
    echo "  AKS cluster '$AKS_CLUSTER_NAME' already exists. Skipping creation."
else
    az aks create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$AKS_CLUSTER_NAME" \
        --node-count 3 \
        --node-vm-size Standard_D2s_v3 \
        --enable-addons monitoring \
        --attach-acr "$ACR_NAME" \
        --generate-ssh-keys \
        --kubernetes-version 1.33.1 \
        --tier Standard \
        --zones 3
    echo "  AKS cluster '$AKS_CLUSTER_NAME' created."
fi

# --- Get AKS credentials ---
echo "🔑 Getting AKS credentials..."
az aks get-credentials --resource-group "$RESOURCE_GROUP" --name "$AKS_CLUSTER_NAME" --overwrite-existing

# --- Create Azure Key Vault ---
echo "🔐 Checking/Creating Azure Key Vault..."
# Note: Key Vault names are globally unique.
# We also include a check for the resource group here for robustness.
if az keyvault show --name "$KEYVAULT_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "  Key Vault '$KEYVAULT_NAME' already exists. Skipping creation."
else
    az keyvault create \
        --name "$KEYVAULT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION"
    echo "  Key Vault '$KEYVAULT_NAME' created."
fi

# --- Create Storage Account for persistent volumes ---
echo "💾 Checking/Creating Storage Account..."
if az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "  Storage Account '$STORAGE_ACCOUNT' already exists. Skipping creation."
else
    az storage account create \
        --name "$STORAGE_ACCOUNT" \
        --resource-group "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --sku Standard_LRS
    echo "  Storage Account '$STORAGE_ACCOUNT' created."
fi



# --- Enable Key Vault integration with AKS (Secrets Store CSI driver) ---
echo "🔗 Setting up Key Vault integration (Secrets Store CSI driver)..."
# This command is generally idempotent.
az aks enable-addons \
    --addons azure-keyvault-secrets-provider \
    --name "$AKS_CLUSTER_NAME" \
    --resource-group "$RESOURCE_GROUP"
echo "  Key Vault integration setup completed."


# --- Grant Key Vault access to AKS using Azure RBAC (recommended) ---
echo "🔓 Granting Key Vault access to AKS via Azure RBAC..."

# Get the AKS managed identity Client ID
AKS_IDENTITY_CLIENT_ID=$(az aks show --name "$AKS_CLUSTER_NAME" --resource-group "$RESOURCE_GROUP" --query "identityProfile.kubeletidentity.clientId" -o tsv)

# Get the Key Vault's full Azure Resource ID
KEYVAULT_RESOURCE_ID=$(az keyvault show --name "$KEYVAULT_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

if [ -z "$AKS_IDENTITY_CLIENT_ID" ]; then
    echo "  Warning: Could not retrieve AKS managed identity Client ID. Key Vault access might not be set correctly."
elif [ -z "$KEYVAULT_RESOURCE_ID" ]; then
    echo "  Warning: Could not retrieve Key Vault Resource ID. Key Vault access might not be set correctly."
else
    # Check if the role assignment already exists (making it idempotent)
    # This check is a bit more complex but essential for full idempotency.
    # We look for any role assignment on the KV scope where the principal ID matches our AKS identity.
    EXISTING_ROLE_ASSIGNMENT=$(az role assignment list \
        --assignee "$AKS_IDENTITY_CLIENT_ID" \
        --scope "$KEYVAULT_RESOURCE_ID" \
        --role "Key Vault Secrets User" \
        --query "[?contains(roleDefinitionName, 'Key Vault Secrets User')].id" -o tsv)

    if [ -n "$EXISTING_ROLE_ASSIGNMENT" ]; then
        echo "  Role 'Key Vault Secrets User' already assigned to AKS identity on Key Vault. Skipping assignment."
    else
        az role assignment create \
            --assignee "$AKS_IDENTITY_CLIENT_ID" \
            --role "Key Vault Secrets User" \
            --scope "$KEYVAULT_RESOURCE_ID"
        echo "  Role 'Key Vault Secrets User' assigned to AKS identity on Key Vault."
    fi
fi

echo "✅ Azure resources checked/created successfully!"
echo ""
echo "📋 Resource Summary:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  AKS Cluster: $AKS_CLUSTER_NAME"
echo "  ACR Registry: $ACR_NAME.azurecr.io"
echo "  Key Vault: $KEYVAULT_NAME"
echo "  Storage Account: $STORAGE_ACCOUNT"
echo ""
echo "🔧 Next steps:"
echo "1. Build and push your Docker image to ACR:"
echo "   az acr build --registry $ACR_NAME --image vocare-backend:latest ."
echo ""
echo "2. Add secrets to Key Vault:"
echo "   az keyvault secret set --vault-name $KEYVAULT_NAME --name openai-api-key --value 'YOUR_OPENAI_KEY'"
echo "   az keyvault secret set --vault-name $KEYVAULT_NAME --name deepgram-api-key --value 'YOUR_DEEPGRAM_KEY'"
echo "   # ... add other secrets"
echo ""
echo "3. Update Kubernetes manifests with your ACR registry name"
echo "4. Deploy to AKS using: cd k8s && ./deploy.sh"

# Save configuration for later use
cat > azure-config.env << EOF
RESOURCE_GROUP=$RESOURCE_GROUP
LOCATION=$LOCATION
AKS_CLUSTER_NAME=$AKS_CLUSTER_NAME
ACR_NAME=$ACR_NAME
KEYVAULT_NAME=$KEYVAULT_NAME
STORAGE_ACCOUNT=$STORAGE_ACCOUNT
EOF

echo ""
echo "💾 Configuration saved to azure-config.env"