#!/bin/bash

# Vocare Restaurant Assistant - Cluster Backup Script
# This script creates comprehensive backups of the AKS cluster and related resources

set -e

# Configuration
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
NAMESPACE="vocare-restaurant"
RETENTION_DAYS=30

# Load Azure configuration if available
if [ -f "../../azure/azure-config.env" ]; then
    source ../../azure/azure-config.env
fi

echo "🔄 Starting Vocare cluster backup..."
echo "Backup directory: $BACKUP_DIR"
echo "Namespace: $NAMESPACE"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"/{kubernetes,azure,configs,logs}

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to backup Kubernetes resources
backup_k8s_resources() {
    log "📦 Backing up Kubernetes resources..."

    # Backup all resources in the namespace
    kubectl get all -n $NAMESPACE -o yaml > "$BACKUP_DIR/kubernetes/all-resources.yaml"

    # Backup specific resource types
    for resource in deployments services configmaps secrets persistentvolumeclaims ingresses networkpolicies; do
        log "  - Backing up $resource"
        kubectl get $resource -n $NAMESPACE -o yaml > "$BACKUP_DIR/kubernetes/$resource.yaml" 2>/dev/null || true
    done

    # Backup cluster-wide resources related to Vocare
    kubectl get clusterroles,clusterrolebindings,priorityclasses -o yaml | \
        grep -A 1000 -B 5 "vocare" > "$BACKUP_DIR/kubernetes/cluster-resources.yaml" 2>/dev/null || true

    # Backup custom resource definitions (if any)
    kubectl get crd -o yaml > "$BACKUP_DIR/kubernetes/crds.yaml" 2>/dev/null || true

    log "✅ Kubernetes resources backed up"
}

# Function to backup Azure Key Vault secrets
backup_keyvault() {
    if [ -z "$KEYVAULT_NAME" ]; then
        log "⚠️  Key Vault name not found, skipping Key Vault backup"
        return
    fi

    log "🔐 Backing up Azure Key Vault secrets..."

    # Get list of secrets
    az keyvault secret list --vault-name "$KEYVAULT_NAME" --query "[].name" -o tsv > "$BACKUP_DIR/azure/secret-names.txt"

    # Backup secret metadata (not values for security)
    az keyvault secret list --vault-name "$KEYVAULT_NAME" -o json > "$BACKUP_DIR/azure/secret-metadata.json"

    # Create restore script template
    cat > "$BACKUP_DIR/azure/restore-secrets.sh" << 'EOF'
#!/bin/bash
# Key Vault Secrets Restore Script
# WARNING: You need to manually populate the secret values

KEYVAULT_NAME="$1"
if [ -z "$KEYVAULT_NAME" ]; then
    echo "Usage: $0 <keyvault-name>"
    exit 1
fi

echo "Restoring secrets to Key Vault: $KEYVAULT_NAME"
echo "You will need to provide the actual secret values..."

while IFS= read -r secret_name; do
    echo "Setting secret: $secret_name"
    read -s -p "Enter value for $secret_name: " secret_value
    echo ""
    az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "$secret_name" --value "$secret_value"
done < secret-names.txt

echo "Secrets restore completed!"
EOF
    chmod +x "$BACKUP_DIR/azure/restore-secrets.sh"

    log "✅ Key Vault backup completed"
}

# Function to backup Azure Container Registry images
backup_acr_images() {
    if [ -z "$ACR_NAME" ]; then
        log "⚠️  ACR name not found, skipping ACR backup"
        return
    fi

    log "🐳 Backing up ACR image information..."

    # List all repositories and tags
    az acr repository list --name "$ACR_NAME" -o json > "$BACKUP_DIR/azure/acr-repositories.json"

    # Get detailed image information
    for repo in $(az acr repository list --name "$ACR_NAME" -o tsv); do
        az acr repository show-tags --name "$ACR_NAME" --repository "$repo" --detail -o json > "$BACKUP_DIR/azure/acr-$repo-tags.json"
    done

    # Create image pull script
    cat > "$BACKUP_DIR/azure/pull-images.sh" << EOF
#!/bin/bash
# Script to pull all images from ACR for backup

ACR_NAME="$ACR_NAME"
echo "Pulling images from \$ACR_NAME.azurecr.io..."

az acr login --name \$ACR_NAME

EOF

    for repo in $(az acr repository list --name "$ACR_NAME" -o tsv); do
        for tag in $(az acr repository show-tags --name "$ACR_NAME" --repository "$repo" -o tsv); do
            echo "docker pull $ACR_NAME.azurecr.io/$repo:$tag" >> "$BACKUP_DIR/azure/pull-images.sh"
        done
    done

    chmod +x "$BACKUP_DIR/azure/pull-images.sh"

    log "✅ ACR backup completed"
}

# Function to backup configuration files
backup_configs() {
    log "📄 Backing up configuration files..."

    # Copy Kubernetes manifests
    cp -r ../../k8s "$BACKUP_DIR/configs/"

    # Copy Helm charts
    cp -r ../../helm "$BACKUP_DIR/configs/"

    # Copy Azure configurations
    cp -r ../../azure "$BACKUP_DIR/configs/"

    # Copy documentation
    cp -r ../../docs "$BACKUP_DIR/configs/"

    # Copy CI/CD configurations
    cp -r ../../.github "$BACKUP_DIR/configs/" 2>/dev/null || true
    cp ../../azure-pipelines.yml "$BACKUP_DIR/configs/" 2>/dev/null || true

    log "✅ Configuration files backed up"
}

# Function to collect logs
backup_logs() {
    log "📋 Collecting recent logs..."

    # Get pod logs for the last 24 hours
    for pod in $(kubectl get pods -n $NAMESPACE -o name); do
        pod_name=$(basename $pod)
        log "  - Collecting logs for $pod_name"
        kubectl logs $pod -n $NAMESPACE --since=24h > "$BACKUP_DIR/logs/$pod_name.log" 2>/dev/null || true
    done

    # Get events
    kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' > "$BACKUP_DIR/logs/events.log"

    log "✅ Logs collected"
}

# Function to create backup manifest
create_manifest() {
    log "📝 Creating backup manifest..."

    cat > "$BACKUP_DIR/backup-manifest.json" << EOF
{
    "backup_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "backup_version": "1.0",
    "cluster_info": {
        "namespace": "$NAMESPACE",
        "aks_cluster": "$AKS_CLUSTER_NAME",
        "resource_group": "$RESOURCE_GROUP",
        "acr_name": "$ACR_NAME",
        "keyvault_name": "$KEYVAULT_NAME"
    },
    "backup_contents": {
        "kubernetes_resources": true,
        "keyvault_metadata": true,
        "acr_metadata": true,
        "configuration_files": true,
        "logs": true
    },
    "restore_instructions": "See restore-instructions.md for detailed restore procedures"
}
EOF

    # Create restore instructions
    cat > "$BACKUP_DIR/restore-instructions.md" << 'EOF'
# Vocare Cluster Restore Instructions

## Prerequisites
- Azure CLI logged in with appropriate permissions
- kubectl configured for target cluster
- Helm 3.x installed

## Restore Procedure

### 1. Restore Azure Resources
```bash
# Restore Key Vault secrets (requires manual input)
cd azure
./restore-secrets.sh <target-keyvault-name>

# Pull and push ACR images to new registry
./pull-images.sh
# Then push to new ACR or import images
```

### 2. Restore Kubernetes Resources
```bash
# Apply configurations in order
kubectl apply -f kubernetes/secrets.yaml
kubectl apply -f kubernetes/configmaps.yaml
kubectl apply -f kubernetes/deployments.yaml
kubectl apply -f kubernetes/services.yaml
kubectl apply -f kubernetes/ingresses.yaml

# Or use Helm
helm install vocare-restaurant configs/helm/vocare-restaurant/
```

### 3. Verify Restoration
```bash
kubectl get all -n vocare-restaurant
kubectl logs -l app=vocare-backend -n vocare-restaurant
```

## Notes
- Secret values are not included in backups for security
- Update image references if restoring to different ACR
- Verify external dependencies (DNS, load balancers)
EOF

    log "✅ Backup manifest created"
}

# Main backup execution
main() {
    log "🚀 Starting backup process..."

    backup_k8s_resources
    backup_keyvault
    backup_acr_images
    backup_configs
    backup_logs
    create_manifest

    # Create compressed archive
    log "📦 Creating compressed backup archive..."
    tar -czf "${BACKUP_DIR}.tar.gz" -C "$(dirname $BACKUP_DIR)" "$(basename $BACKUP_DIR)"

    # Calculate backup size
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}.tar.gz" | cut -f1)

    log "✅ Backup completed successfully!"
    echo ""
    echo "📊 Backup Summary:"
    echo "  Location: ${BACKUP_DIR}.tar.gz"
    echo "  Size: $BACKUP_SIZE"
    echo "  Contents: Kubernetes resources, Azure metadata, configs, logs"
    echo ""
    echo "🔧 Next steps:"
    echo "  1. Store backup in secure location (Azure Storage, etc.)"
    echo "  2. Test restore procedure in non-production environment"
    echo "  3. Document any environment-specific restore requirements"
}

# Cleanup old backups
cleanup_old_backups() {
    log "🧹 Cleaning up backups older than $RETENTION_DAYS days..."
    find ./backups -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    find ./backups -type d -mtime +$RETENTION_DAYS -exec rm -rf {} + 2>/dev/null || true
}

# Execute main function
main
cleanup_old_backups

log "🎉 Backup process completed!"