#!/bin/bash

# Vocare Restaurant Assistant - AKS Deployment Script
# This script deploys the restaurant assistant to Azure Kubernetes Service

set -e

echo "🚀 Deploying Vocare Restaurant Assistant to AKS..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Not connected to a Kubernetes cluster. Please configure kubectl."
    exit 1
fi

# Function to apply manifests with error handling
apply_manifest() {
    local file=$1
    echo "📄 Applying $file..."
    if kubectl apply -f "$file"; then
        echo "✅ Successfully applied $file"
    else
        echo "❌ Failed to apply $file"
        exit 1
    fi
}

# Create namespace first
echo "🏗️  Creating namespace..."
apply_manifest "shared/namespace.yaml"

# Apply shared resources
echo "🔧 Applying shared resources..."
apply_manifest "shared/configmap.yaml"

# Check if Azure Key Vault is set up
echo "🔐 Checking Azure Key Vault setup..."
if kubectl get secretproviderclass vocare-keyvault-secrets -n vocare-restaurant &> /dev/null; then
    echo "✅ Azure Key Vault SecretProviderClass found"
else
    echo "❌ Azure Key Vault SecretProviderClass not found!"
    echo "Please run: kubectl apply -f ../azure/keyvault/secret-provider-class.yaml"
    exit 1
fi

# Apply FreeSWITCH resources
echo "📞 Deploying FreeSWITCH..."
apply_manifest "freeswitch/configmap.yaml"
apply_manifest "freeswitch/deployment.yaml"
apply_manifest "freeswitch/service.yaml"

# Apply LiveKit resources
echo "🎥 Deploying LiveKit..."
apply_manifest "livekit/deployment.yaml"
apply_manifest "livekit/service.yaml"

# Apply Backend resources
echo "🤖 Deploying Backend..."
echo "   Using Azure Key Vault deployment"
apply_manifest "backend/deployment.yaml"
apply_manifest "backend/service.yaml"

echo "✅ Deployment completed!"
echo ""
echo "📋 Next steps:"
echo "1. Check pod status: kubectl get pods -n vocare-restaurant"
echo "2. Check services: kubectl get services -n vocare-restaurant"
echo "3. Get external IPs: kubectl get services -n vocare-restaurant -o wide"
echo "4. Check logs: kubectl logs -n vocare-restaurant -l app=vocare-backend"
echo ""
echo "🔍 Troubleshooting:"
echo "- If pods are not starting, check: kubectl describe pods -n vocare-restaurant"
echo "- For FreeSWITCH issues, you may need to enable privileged mode"
echo "- Ensure your AKS cluster has sufficient resources"

# Wait for deployments to be ready
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/backend-deployment -n vocare-restaurant
kubectl wait --for=condition=available --timeout=300s deployment/livekit-deployment -n vocare-restaurant
kubectl wait --for=condition=available --timeout=300s deployment/freeswitch-deployment -n vocare-restaurant

echo "🎉 All deployments are ready!"

# Show the status
echo ""
echo "📊 Current status:"
kubectl get all -n vocare-restaurant