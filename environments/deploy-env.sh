#!/bin/bash

# Environment-specific deployment script for Vocare Restaurant Assistant
# Usage: ./deploy-env.sh <environment> [options]

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HELM_CHART_PATH="$PROJECT_ROOT/helm/vocare-restaurant"

# Default values
ENVIRONMENT=""
DRY_RUN=false
FORCE=false
SKIP_TESTS=false
TIMEOUT="600s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Usage function
usage() {
    cat << EOF
Usage: $0 <environment> [options]

Environments:
  dev         Deploy to development environment
  staging     Deploy to staging environment
  prod        Deploy to production environment

Options:
  --dry-run           Show what would be deployed without actually deploying
  --force             Force deployment even if validation fails
  --skip-tests        Skip pre-deployment tests
  --timeout DURATION  Timeout for deployment (default: 600s)
  -h, --help          Show this help message

Examples:
  $0 dev                    # Deploy to development
  $0 prod --dry-run         # Show what would be deployed to production
  $0 staging --timeout 900s # Deploy to staging with 15-minute timeout

EOF
}

# Parse command line arguments
parse_args() {
    if [ $# -eq 0 ]; then
        log_error "No environment specified"
        usage
        exit 1
    fi

    ENVIRONMENT="$1"
    shift

    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate environment
    case $ENVIRONMENT in
        dev|staging|prod)
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            log_error "Valid environments: dev, staging, prod"
            exit 1
            ;;
    esac
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check required tools
    local tools=("kubectl" "helm" "az")
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool is not installed or not in PATH"
            exit 1
        fi
    done

    # Check kubectl connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "kubectl is not connected to a cluster"
        exit 1
    fi

    # Check Helm chart exists
    if [ ! -d "$HELM_CHART_PATH" ]; then
        log_error "Helm chart not found at $HELM_CHART_PATH"
        exit 1
    fi

    # Check environment values file exists
    local values_file="$SCRIPT_DIR/$ENVIRONMENT/values.yaml"
    if [ ! -f "$values_file" ]; then
        log_error "Environment values file not found: $values_file"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Load environment configuration
load_environment_config() {
    log_info "Loading $ENVIRONMENT environment configuration..."

    # Set environment-specific variables
    case $ENVIRONMENT in
        dev)
            NAMESPACE="vocare-dev"
            RELEASE_NAME="vocare-dev"
            ;;
        staging)
            NAMESPACE="vocare-staging"
            RELEASE_NAME="vocare-staging"
            ;;
        prod)
            NAMESPACE="vocare-restaurant"
            RELEASE_NAME="vocare-restaurant"
            ;;
    esac

    log_info "Environment: $ENVIRONMENT"
    log_info "Namespace: $NAMESPACE"
    log_info "Release: $RELEASE_NAME"
}

# Validate environment
validate_environment() {
    if [ "$SKIP_TESTS" = true ]; then
        log_warning "Skipping environment validation"
        return
    fi

    log_info "Validating $ENVIRONMENT environment..."

    # Check if namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_warning "Namespace $NAMESPACE does not exist, it will be created"
    fi

    # Validate Helm chart
    log_info "Validating Helm chart..."
    if ! helm lint "$HELM_CHART_PATH" -f "$SCRIPT_DIR/$ENVIRONMENT/values.yaml"; then
        log_error "Helm chart validation failed"
        if [ "$FORCE" != true ]; then
            exit 1
        fi
        log_warning "Continuing due to --force flag"
    fi

    # Environment-specific validations
    case $ENVIRONMENT in
        prod)
            validate_production_environment
            ;;
        staging)
            validate_staging_environment
            ;;
        dev)
            validate_development_environment
            ;;
    esac

    log_success "Environment validation passed"
}

# Production-specific validations
validate_production_environment() {
    log_info "Running production-specific validations..."

    # Check for production secrets
    local required_secrets=("vocare-api-secrets" "vocare-sip-secrets" "vocare-firebase-secret")
    for secret in "${required_secrets[@]}"; do
        if ! kubectl get secret "$secret" -n "$NAMESPACE" &> /dev/null; then
            log_error "Required secret '$secret' not found in namespace '$NAMESPACE'"
            if [ "$FORCE" != true ]; then
                exit 1
            fi
        fi
    done

    # Check Azure Key Vault integration
    if ! kubectl get secretproviderclass vocare-keyvault-secrets -n "$NAMESPACE" &> /dev/null; then
        log_warning "Azure Key Vault SecretProviderClass not found"
    fi

    # Check monitoring components
    if ! kubectl get prometheus -A &> /dev/null; then
        log_warning "Prometheus not found - monitoring may not work properly"
    fi
}

# Staging-specific validations
validate_staging_environment() {
    log_info "Running staging-specific validations..."
    # Add staging-specific checks here
}

# Development-specific validations
validate_development_environment() {
    log_info "Running development-specific validations..."
    # Add development-specific checks here
}

# Deploy application
deploy_application() {
    log_info "Deploying Vocare Restaurant Assistant to $ENVIRONMENT..."

    local helm_args=(
        "upgrade" "--install"
        "$RELEASE_NAME"
        "$HELM_CHART_PATH"
        "--namespace" "$NAMESPACE"
        "--create-namespace"
        "--values" "$SCRIPT_DIR/$ENVIRONMENT/values.yaml"
        "--timeout" "$TIMEOUT"
        "--wait"
    )

    if [ "$DRY_RUN" = true ]; then
        helm_args+=("--dry-run")
        log_info "DRY RUN - No actual deployment will occur"
    fi

    # Add environment-specific Helm arguments
    case $ENVIRONMENT in
        prod)
            helm_args+=("--atomic")  # Rollback on failure
            ;;
        staging)
            helm_args+=("--debug")
            ;;
        dev)
            helm_args+=("--debug")
            ;;
    esac

    log_info "Running Helm deployment..."
    if helm "${helm_args[@]}"; then
        if [ "$DRY_RUN" != true ]; then
            log_success "Deployment completed successfully"
        else
            log_success "Dry run completed successfully"
        fi
    else
        log_error "Deployment failed"
        exit 1
    fi
}

# Post-deployment verification
verify_deployment() {
    if [ "$DRY_RUN" = true ]; then
        return
    fi

    log_info "Verifying deployment..."

    # Wait for pods to be ready
    log_info "Waiting for pods to be ready..."
    if ! kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance="$RELEASE_NAME" -n "$NAMESPACE" --timeout=300s; then
        log_error "Pods failed to become ready"
        exit 1
    fi

    # Check service endpoints
    log_info "Checking service endpoints..."
    kubectl get services -n "$NAMESPACE"

    # Run health checks
    log_info "Running health checks..."
    local backend_service=$(kubectl get service -n "$NAMESPACE" -l app=vocare-backend -o jsonpath='{.items[0].metadata.name}')
    if [ -n "$backend_service" ]; then
        # Port forward and test health endpoint
        kubectl port-forward service/"$backend_service" 8080:8000 -n "$NAMESPACE" &
        local port_forward_pid=$!
        sleep 5

        if curl -f http://localhost:8080/health &> /dev/null; then
            log_success "Health check passed"
        else
            log_warning "Health check failed - service may still be starting"
        fi

        kill $port_forward_pid 2>/dev/null || true
    fi

    log_success "Deployment verification completed"
}

# Cleanup function
cleanup() {
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

# Main execution
main() {
    trap cleanup EXIT

    log_info "Starting Vocare Restaurant Assistant deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Timestamp: $(date)"

    parse_args "$@"
    check_prerequisites
    load_environment_config
    validate_environment
    deploy_application
    verify_deployment

    log_success "🎉 Deployment process completed successfully!"

    if [ "$DRY_RUN" != true ]; then
        echo ""
        log_info "📋 Next steps:"
        echo "  1. Monitor the deployment: kubectl get pods -n $NAMESPACE"
        echo "  2. Check logs: kubectl logs -l app=vocare-backend -n $NAMESPACE"
        echo "  3. Access services: kubectl get services -n $NAMESPACE"

        if [ "$ENVIRONMENT" = "prod" ]; then
            echo "  4. Verify external access and DNS"
            echo "  5. Run end-to-end tests"
            echo "  6. Monitor alerts and metrics"
        fi
    fi
}

# Execute main function with all arguments
main "$@"