#!/bin/bash

# Build and push Vocare Restaurant Assistant to Azure Container Registry
# This script builds the Docker image and pushes it to ACR

set -e

# Load Azure configuration
if [ -f "../azure-config.env" ]; then
    source ../azure-config.env
else
    echo "❌ Azure configuration not found. Please run setup-azure.sh first."
    exit 1
fi

# Configuration
IMAGE_NAME="vocare-backend"
VERSION=${1:-"latest"}
FULL_IMAGE_NAME="$ACR_NAME.azurecr.io/$IMAGE_NAME:$VERSION"

echo "🐳 Building and pushing Docker image to ACR..."
echo "Registry: $ACR_NAME.azurecr.io"
echo "Image: $IMAGE_NAME:$VERSION"
echo ""

# Check if Azure CLI is logged in
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

# Login to ACR
echo "🔑 Logging in to Azure Container Registry..."
az acr login --name $ACR_NAME

# Build and push using ACR build (recommended for production)
echo "🏗️  Building image in ACR..."
cd ../../  # Go to project root

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo "❌ Dockerfile not found in project root!"
    echo "Please ensure Dockerfile exists before building."
    exit 1
fi

echo "📄 Using existing Dockerfile from project root"

# Build using ACR build task with your existing Dockerfile
echo "🚀 Building image in Azure Container Registry..."
az acr build --registry $ACR_NAME --image $IMAGE_NAME:$VERSION --file Dockerfile .

echo "✅ Image built and pushed successfully!"
echo ""
echo "📋 Image details:"
echo "  Registry: $ACR_NAME.azurecr.io"
echo "  Image: $IMAGE_NAME:$VERSION"
echo "  Full name: $FULL_IMAGE_NAME"
echo ""
echo "🔧 Next steps:"
echo "1. Update your Kubernetes deployment to use this image:"
echo "   image: $FULL_IMAGE_NAME"
echo ""
echo "2. Deploy to AKS:"
echo "   cd ../../k8s && ./deploy.sh"
echo ""
echo "📊 To view all images in your registry:"
echo "az acr repository list --name $ACR_NAME --output table"