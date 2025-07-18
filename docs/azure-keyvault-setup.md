# Azure Key Vault Setup for Vocare Restaurant Assistant

## Quick Setup Guide

Since you want to use Azure Key Vault (recommended for production), follow these steps:

### Step 1: Run Azure Infrastructure Setup
```bash
cd azure
./setup-azure.sh
```
This creates:
- Azure Key Vault
- AKS cluster
- Container Registry
- All necessary Azure resources

### Step 2: Set up Workload Identity (for secure Key Vault access)
```bash
./setup-workload-identity.sh
```
This configures:
- Managed Identity for AKS
- Federated credentials
- Key Vault access permissions

### Step 3: Populate Key Vault with Your Secrets
```bash
cd keyvault
./populate-secrets.sh
```
This script will prompt you for:
- OpenAI API Key
- Deepgram API Key
- Cartesia API Key
- LiveKit API Key & Secret
- SIP provider credentials
- Firebase service account JSON

### Step 4: Deploy the SecretProviderClass
```bash
# Update the Key Vault name and tenant ID first
kubectl apply -f azure/keyvault/secret-provider-class.yaml
```

### Step 5: Deploy the Application
```bash
cd ../k8s
./deploy.sh
```
The script will automatically detect Azure Key Vault and use the secure deployment.

## What This Gives You

✅ **No manual base64 encoding** - Azure handles it automatically
✅ **Secure secret storage** - Encrypted at rest in Azure
✅ **Automatic rotation** - Can be configured for API keys
✅ **Audit logging** - Track who accesses secrets
✅ **No secrets in Git** - Secrets never stored in your repository

## Verification

After setup, verify Key Vault integration:
```bash
# Check if SecretProviderClass exists
kubectl get secretproviderclass vocare-keyvault-secrets -n vocare-restaurant

# Check if secrets are mounted in pods
kubectl describe pod -l app=vocare-backend -n vocare-restaurant

# Look for the Key Vault mount
kubectl exec -it <backend-pod> -n vocare-restaurant -- ls /mnt/secrets-store
```

## Troubleshooting

### Common Issues:

1. **"SecretProviderClass not found"**
   - Run: `kubectl apply -f azure/keyvault/secret-provider-class.yaml`

2. **"Failed to get secret from Key Vault"**
   - Check workload identity: `./azure/setup-workload-identity.sh`
   - Verify Key Vault permissions

3. **"Pod can't access secrets"**
   - Ensure the pod uses the correct service account
   - Check the SecretProviderClass configuration

### Debug Commands:
```bash
# Check workload identity
kubectl describe pod <backend-pod> -n vocare-restaurant

# Check Key Vault access
az keyvault secret list --vault-name <your-keyvault-name>

# Check service account
kubectl get serviceaccount vocare-workload-identity -n vocare-restaurant -o yaml
```

## Next Steps

Once Key Vault is set up:
1. Deploy to development: `cd environments && ./deploy-env.sh dev`
2. Deploy to production: `./deploy-env.sh prod`
3. Monitor the deployment: `kubectl get pods -n vocare-restaurant`

The Key Vault approach is much cleaner and more secure than manual secrets! 🔐