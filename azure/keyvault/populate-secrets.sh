#!/bin/bash

# Script to populate Azure Key Vault with Vocare Restaurant Assistant secrets
# Can read from .env file or prompt for manual input

set -e

# Load Azure configuration
if [ -f "../azure-config.env" ]; then
    source ../azure-config.env
else
    echo "❌ Azure configuration not found. Please run setup-azure.sh first."
    exit 1
fi

echo "🔐 Populating Azure Key Vault: $KEYVAULT_NAME"
echo ""

# Check if .env file exists
ENV_FILE="../../.env"
if [ -f "$ENV_FILE" ]; then
    echo "📄 Found .env file: $ENV_FILE"
    echo "Choose an option:"
    echo "1. Load secrets from .env file (recommended)"
    echo "2. Enter secrets manually"
    read -p "Enter choice (1 or 2): " choice
    echo ""
else
    echo "📄 No .env file found. Will prompt for secrets manually."
    choice=2
fi

# Function to set secret in Key Vault
set_keyvault_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3

    if [ -z "$secret_value" ] || [ "$secret_value" = "your-sip-username" ] || [ "$secret_value" = "your-sip-password" ] || [ "$secret_value" = "your-sip-provider.com" ]; then
        echo "⚠️  Skipping $secret_name - placeholder or empty value"
        return 0
    fi

    echo "Setting $secret_name in Key Vault..."
    if az keyvault secret set --vault-name $KEYVAULT_NAME --name $secret_name --value "$secret_value" > /dev/null; then
        echo "✅ $secret_name set successfully"
    else
        echo "❌ Failed to set $secret_name"
        return 1
    fi
}

# Function to load secrets from .env file
load_from_env() {
    echo "📖 Reading secrets from .env file..."
    echo ""

    # Read .env file and extract values
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue

        # Remove quotes from value if present
        value=$(echo "$value" | sed 's/^["'\'']//' | sed 's/["'\'']$//')

        case $key in
            "OPENAI_API_KEY")
                set_keyvault_secret "openai-api-key" "$value" "OpenAI API Key"
                ;;
            "DEEPGRAM_API_KEY")
                set_keyvault_secret "deepgram-api-key" "$value" "Deepgram API Key"
                ;;
            "CARTESIA_API_KEY")
                set_keyvault_secret "cartesia-api-key" "$value" "Cartesia API Key"
                ;;
            "LIVEKIT_API_KEY")
                set_keyvault_secret "livekit-api-key" "$value" "LiveKit API Key"
                ;;
            "LIVEKIT_API_SECRET")
                set_keyvault_secret "livekit-api-secret" "$value" "LiveKit API Secret"
                ;;
            "FREESWITCH_DEFAULT_PASSWORD")
                set_keyvault_secret "freeswitch-default-password" "$value" "FreeSWITCH Default Password"
                ;;
            "SIP_USERNAME")
                set_keyvault_secret "sip-username" "$value" "SIP Username"
                ;;
            "SIP_PASSWORD")
                set_keyvault_secret "sip-password" "$value" "SIP Password"
                ;;
            "SIP_REALM")
                set_keyvault_secret "sip-realm" "$value" "SIP Realm"
                ;;
            "SIP_PROXY")
                set_keyvault_secret "sip-proxy" "$value" "SIP Proxy"
                ;;
        esac
    done < "$ENV_FILE"

    # Handle Firebase service account file
    SERVICE_ACCOUNT_FILE="../../service.json"
    if [ -f "$SERVICE_ACCOUNT_FILE" ]; then
        echo "📄 Found Firebase service account file: $SERVICE_ACCOUNT_FILE"
        echo "Setting firebase-service-account-json in Key Vault..."
        if az keyvault secret set --vault-name $KEYVAULT_NAME --name "firebase-service-account-json" --file "$SERVICE_ACCOUNT_FILE" > /dev/null; then
            echo "✅ firebase-service-account-json set successfully"
        else
            echo "❌ Failed to set firebase-service-account-json"
        fi
    else
        echo "⚠️  Firebase service account file not found at $SERVICE_ACCOUNT_FILE"
        echo "   Please ensure service.json exists in the project root"
    fi
}

# Function to securely prompt for secrets
prompt_secret() {
    local secret_name=$1
    local description=$2
    echo "Enter $description:"
    read -s secret_value
    echo ""

    if [ -z "$secret_value" ]; then
        echo "⚠️  Warning: Empty value for $secret_name"
        return 1
    fi

    set_keyvault_secret "$secret_name" "$secret_value" "$description"
}

# Function to set secret from file
set_secret_from_file() {
    local secret_name=$1
    local file_path=$2
    local description=$3

    if [ -f "$file_path" ]; then
        echo "Setting $secret_name from $file_path..."
        az keyvault secret set --vault-name $KEYVAULT_NAME --name $secret_name --file "$file_path"
        echo "✅ $secret_name set successfully"
    else
        echo "⚠️  File not found: $file_path"
        echo "Please provide $description manually:"
        prompt_secret $secret_name "$description"
    fi
    echo ""
}

echo "📝 Please provide the following secrets:"
echo ""

# API Keys
prompt_secret "openai-api-key" "OpenAI API Key"
prompt_secret "deepgram-api-key" "Deepgram API Key"
prompt_secret "cartesia-api-key" "Cartesia API Key"

# LiveKit credentials
prompt_secret "livekit-api-key" "LiveKit API Key"
prompt_secret "livekit-api-secret" "LiveKit API Secret"

# SIP provider credentials
echo "SIP Provider Configuration:"
prompt_secret "sip-username" "SIP Username"
prompt_secret "sip-password" "SIP Password"
prompt_secret "sip-realm" "SIP Realm"
prompt_secret "sip-proxy" "SIP Proxy"

# FreeSWITCH configuration
prompt_secret "freeswitch-default-password" "FreeSWITCH Default Password"

# Firebase service account
echo "Firebase Service Account:"
echo "Looking for service.json in current directory..."
set_secret_from_file "firebase-service-account-json" "../../service.json" "Firebase Service Account JSON content"

echo "🎉 All secrets have been populated in Azure Key Vault!"
echo ""
echo "🔧 Next steps:"
echo "1. Update the SecretProviderClass with your Key Vault name and tenant ID"
echo "2. Deploy the SecretProviderClass: kubectl apply -f secret-provider-class.yaml"
echo "3. Update your Kubernetes deployments to use the Key Vault secrets"
echo ""
echo "📋 To verify secrets were set correctly:"
echo "az keyvault secret list --vault-name $KEYVAULT_NAME --output table"