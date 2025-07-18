# Vocare Restaurant Assistant - Azure AKS Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Vocare Restaurant Assistant to Azure Kubernetes Service (AKS). The deployment includes:

- **Backend Service**: Python-based AI assistant using LiveKit Agents
- **LiveKit Server**: Real-time communication server
- **FreeSWITCH**: SIP telephony server for phone call handling
- **Azure Integration**: Container Registry, Key Vault, Monitoring

## Prerequisites

### Required Tools
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) (latest version)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) (latest version)
- [Helm 3.x](https://helm.sh/docs/intro/install/)
- [Docker](https://docs.docker.com/get-docker/) (for local builds)

### Required Accounts and Services
- Azure subscription with sufficient permissions
- OpenAI API account and key
- Deepgram API account and key
- Cartesia API account and key
- Firebase project with service account
- SIP provider account (optional, for phone integration)

### Azure Permissions Required
Your Azure account needs the following permissions:
- Contributor role on the subscription or resource group
- Ability to create and manage:
  - Resource Groups
  - AKS clusters
  - Container Registries
  - Key Vaults
  - Storage Accounts
  - Managed Identities

## Step 1: Initial Setup

### 1.1 Clone and Prepare Repository
```bash
git clone <your-repository-url>
cd vocare
```

### 1.2 Login to Azure
```bash
az login
az account set --subscription "your-subscription-id"
```

### 1.3 Verify Prerequisites
```bash
# Check Azure CLI
az --version

# Check kubectl
kubectl version --client

# Check Helm
helm version

# Check Docker
docker --version
```

## Step 2: Azure Infrastructure Setup

### 2.1 Run Azure Setup Script
```bash
cd azure
chmod +x setup-azure.sh
./setup-azure.sh
```

This script will create:
- Resource Group
- AKS Cluster (3 nodes, Standard_D2s_v3)
- Azure Container Registry
- Azure Key Vault
- Storage Account
- Necessary integrations

**Expected Duration**: 10-15 minutes

### 2.2 Verify Infrastructure
```bash
# Check resource group
az group show --name vocare-restaurant-rg

# Check AKS cluster
az aks show --resource-group vocare-restaurant-rg --name vocare-aks

# Check ACR
az acr list --resource-group vocare-restaurant-rg

# Test kubectl connection
kubectl get nodes
```

## Step 3: Secrets Management

### 3.1 Prepare API Keys and Credentials
Gather the following information:
- OpenAI API Key
- Deepgram API Key
- Cartesia API Key
- LiveKit API Key and Secret
- SIP provider credentials (if using)
- Firebase service account JSON file

### 3.2 Populate Azure Key Vault
```bash
cd azure/keyvault
chmod +x populate-secrets.sh
./populate-secrets.sh
```

Follow the prompts to enter your API keys and credentials securely.

### 3.3 Set up Workload Identity
```bash
cd azure
chmod +x setup-workload-identity.sh
./setup-workload-identity.sh
```

This enables secure access to Key Vault from AKS pods without storing credentials.

## Step 4: Build and Push Application

### 4.1 Build Docker Image
```bash
cd azure/acr
chmod +x build-and-push.sh
./build-and-push.sh
```

This will:
- Create a production-optimized Dockerfile
- Build the image in Azure Container Registry
- Tag and push the image

### 4.2 Verify Image
```bash
# List images in ACR
az acr repository list --name your-acr-name --output table

# Show image tags
az acr repository show-tags --name your-acr-name --repository vocare-backend --output table
```

## Step 5: Deploy to AKS

### 5.1 Update Configuration
Before deploying, update the following files with your specific values:

**k8s/backend/deployment.yaml**:
```yaml
image: "your-acr-name.azurecr.io/vocare-backend:latest"
```

**azure/keyvault/secret-provider-class.yaml**:
```yaml
keyvaultName: "your-keyvault-name"
tenantId: "your-tenant-id"
```

### 5.2 Deploy Using Scripts
```bash
cd k8s
chmod +x deploy.sh
./deploy.sh
```

### 5.3 Alternative: Deploy Using Helm
```bash
# Update values in helm/vocare-restaurant/values.yaml
helm upgrade --install vocare-restaurant ./helm/vocare-restaurant \
  --namespace vocare-restaurant \
  --create-namespace \
  --set global.imageRegistry=your-acr-name.azurecr.io \
  --set azure.keyVaultName=your-keyvault-name \
  --wait --timeout=10m
```

## Step 6: Verify Deployment

### 6.1 Check Pod Status
```bash
kubectl get pods -n vocare-restaurant
kubectl get services -n vocare-restaurant
```

### 6.2 Check Logs
```bash
# Backend logs
kubectl logs -n vocare-restaurant -l app=vocare-backend

# LiveKit logs
kubectl logs -n vocare-restaurant -l app=livekit-server

# FreeSWITCH logs
kubectl logs -n vocare-restaurant -l app=freeswitch-server
```

### 6.3 Test Connectivity
```bash
# Get external IPs
kubectl get services -n vocare-restaurant -o wide

# Test backend health (replace with actual IP)
curl http://EXTERNAL_IP:8000/health

# Test LiveKit WebSocket (replace with actual IP)
curl http://EXTERNAL_IP:7880/
```

## Step 7: Configure Networking and DNS

### 7.1 Set up Domain Names
Update your DNS records to point to the external IPs:
```bash
# Get external IPs
kubectl get services -n vocare-restaurant

# Update DNS records:
# vocare.yourdomain.com -> Backend LoadBalancer IP
# livekit.yourdomain.com -> LiveKit LoadBalancer IP
# sip.yourdomain.com -> FreeSWITCH LoadBalancer IP
```

### 7.2 Configure SSL/TLS (Optional)
```bash
# Install cert-manager for automatic SSL certificates
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Apply ingress with TLS
kubectl apply -f k8s/networking/ingress.yaml
```

## Step 8: Set up Monitoring

### 8.1 Enable Azure Monitor
```bash
# Enable monitoring add-on
az aks enable-addons \
  --addons monitoring \
  --name vocare-aks \
  --resource-group vocare-restaurant-rg

# Apply monitoring configuration
kubectl apply -f k8s/monitoring/azure-monitor.yaml
```

### 8.2 Configure Application Insights
1. Create Application Insights resource in Azure Portal
2. Get the connection string
3. Update the ConfigMap in `k8s/monitoring/azure-monitor.yaml`
4. Redeploy the monitoring configuration

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. Pods Not Starting

**Symptoms**: Pods stuck in `Pending` or `CrashLoopBackOff` state

**Diagnosis**:
```bash
kubectl describe pod POD_NAME -n vocare-restaurant
kubectl logs POD_NAME -n vocare-restaurant
```

**Common Causes**:
- Insufficient cluster resources
- Image pull errors
- Missing secrets
- Configuration errors

**Solutions**:
```bash
# Check cluster resources
kubectl top nodes
kubectl describe nodes

# Check image pull secrets
kubectl get secrets -n vocare-restaurant

# Verify ACR integration
az aks check-acr --name vocare-aks --resource-group vocare-restaurant-rg --acr your-acr-name
```

#### 2. FreeSWITCH Networking Issues

**Symptoms**: SIP calls not connecting, RTP audio issues

**Diagnosis**:
```bash
# Check FreeSWITCH logs
kubectl logs -n vocare-restaurant -l app=freeswitch-server

# Check service endpoints
kubectl get endpoints -n vocare-restaurant
```

**Solutions**:
- Ensure UDP ports are properly exposed
- Check Azure Load Balancer configuration
- Consider using host networking for FreeSWITCH
- Verify SIP provider configuration

#### 3. Key Vault Access Issues

**Symptoms**: Secrets not loading, authentication errors

**Diagnosis**:
```bash
# Check workload identity
kubectl describe pod POD_NAME -n vocare-restaurant

# Check secret provider class
kubectl describe secretproviderclass vocare-keyvault-secrets -n vocare-restaurant
```

**Solutions**:
```bash
# Verify workload identity setup
az identity show --name vocare-workload-identity --resource-group vocare-restaurant-rg

# Check Key Vault permissions
az keyvault show --name your-keyvault-name
```

#### 4. LiveKit Connection Issues

**Symptoms**: WebSocket connections failing, media not flowing

**Diagnosis**:
```bash
# Check LiveKit logs
kubectl logs -n vocare-restaurant -l app=livekit-server

# Test WebSocket connection
curl -I http://LIVEKIT_IP:7880/
```

**Solutions**:
- Verify external IP configuration
- Check firewall rules
- Ensure proper port forwarding
- Validate LiveKit configuration

### Performance Optimization

#### 1. Resource Allocation
```bash
# Monitor resource usage
kubectl top pods -n vocare-restaurant
kubectl top nodes

# Adjust resource requests/limits in deployments
```

#### 2. Scaling
```bash
# Manual scaling
kubectl scale deployment backend-deployment --replicas=3 -n vocare-restaurant

# Enable horizontal pod autoscaling
kubectl autoscale deployment backend-deployment \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n vocare-restaurant
```

#### 3. Node Optimization
```bash
# Add dedicated node pool for telephony workloads
az aks nodepool add \
  --resource-group vocare-restaurant-rg \
  --cluster-name vocare-aks \
  --name telephony \
  --node-count 2 \
  --node-vm-size Standard_D4s_v3 \
  --node-taints vocare.com/freeswitch=true:NoSchedule
```

## Maintenance and Operations

### Regular Tasks

#### 1. Update Images
```bash
# Build new image
cd azure/acr
./build-and-push.sh v1.1.0

# Update deployment
kubectl set image deployment/backend-deployment \
  vocare-backend=your-acr-name.azurecr.io/vocare-backend:v1.1.0 \
  -n vocare-restaurant

# Monitor rollout
kubectl rollout status deployment/backend-deployment -n vocare-restaurant
```

#### 2. Backup and Recovery
```bash
# Backup Kubernetes resources
kubectl get all -n vocare-restaurant -o yaml > backup-$(date +%Y%m%d).yaml

# Backup Key Vault secrets
az keyvault secret list --vault-name your-keyvault-name --query "[].name" -o tsv | \
  xargs -I {} az keyvault secret show --vault-name your-keyvault-name --name {} > keyvault-backup-$(date +%Y%m%d).json
```

#### 3. Security Updates
```bash
# Update AKS cluster
az aks upgrade --resource-group vocare-restaurant-rg --name vocare-aks --kubernetes-version 1.28.0

# Update node pools
az aks nodepool upgrade --resource-group vocare-restaurant-rg --cluster-name vocare-aks --name nodepool1 --kubernetes-version 1.28.0
```

## Support and Resources

### Useful Commands
```bash
# Get cluster info
kubectl cluster-info

# Check all resources
kubectl get all -n vocare-restaurant

# Describe problematic resources
kubectl describe deployment/backend-deployment -n vocare-restaurant

# Port forward for local testing
kubectl port-forward service/backend-service 8000:8000 -n vocare-restaurant

# Execute commands in pods
kubectl exec -it POD_NAME -n vocare-restaurant -- /bin/bash
```

### Log Locations
- **Application Logs**: `kubectl logs -n vocare-restaurant`
- **Azure Monitor**: Azure Portal > Monitor > Logs
- **AKS Diagnostics**: Azure Portal > AKS Cluster > Monitoring

### Documentation Links
- [Azure AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [LiveKit Documentation](https://docs.livekit.io/)
- [FreeSWITCH Documentation](https://freeswitch.org/confluence/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

---

**Need Help?**
- Check the troubleshooting section above
- Review logs using the commands provided
- Consult the Azure AKS documentation
- Open an issue in the project repository
```