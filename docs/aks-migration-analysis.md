# Azure AKS Migration Analysis

## Current Architecture Overview

### Services Architecture
The current system consists of three main services orchestrated via Docker Compose:

1. **Backend Service** (Restaurant AI Assistant)
   - Python 3.11 application using LiveKit Agents
   - Ports: 8000 (FreeSWITCH socket), 8081 (LiveKit agent)
   - Dependencies: Firebase, OpenAI, Deepgram, Cartesia APIs
   - Main entry point: `main.py`

2. **LiveKit Server**
   - Real-time communication server for audio/video
   - Ports: 7880 (WebSocket), 7881 (WebSocket TLS), 7882/udp (TURN), 16384-16394/udp (RTP)
   - Configuration: `livekit-config.yaml`

3. **FreeSWITCH**
   - SIP telephony server for phone call handling
   - Ports: 5060/udp, 5080/udp (SIP), 8021 (Event Socket), 30000-30010/udp (RTP)
   - Configuration: `freeswitch-config/`
   - Requires privileged mode and SYS_NICE capability

### Networking Requirements

#### Internal Communication
- Backend ↔ LiveKit: HTTP webhooks (backend:8000/webhook)
- Backend ↔ FreeSWITCH: Event Socket (freeswitch:8021)
- LiveKit ↔ FreeSWITCH: SIP integration

#### External Access Requirements
- **SIP Traffic**: UDP 5060, 5080 for SIP signaling
- **RTP Media**: UDP 30000-30010 (FreeSWITCH), UDP 16384-16394 (LiveKit)
- **WebSocket**: TCP 7880, 7881 for web clients
- **API Access**: TCP 8081 for LiveKit agent connections

### Data Dependencies

#### Persistent Storage
- Firebase service account JSON (`service.json`)
- FreeSWITCH configuration files
- LiveKit configuration

#### Environment Variables
**Required Secrets:**
- `OPENAI_API_KEY`
- `DEEPGRAM_API_KEY`
- `CARTESIA_API_KEY`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- SIP provider credentials

**Configuration:**
- Model settings, voice IDs
- Firebase paths
- SIP trunk configurations

## AKS Migration Challenges

### 1. Networking Complexity
- **UDP Port Ranges**: Large UDP port ranges for RTP traffic
- **External IP Requirements**: LiveKit needs external IP for WebRTC
- **SIP NAT Traversal**: FreeSWITCH requires proper NAT configuration

### 2. Privileged Containers
- FreeSWITCH requires privileged mode and SYS_NICE capability
- Need to evaluate security implications in AKS

### 3. Real-time Performance
- Low-latency requirements for voice communication
- Need proper resource allocation and QoS

### 4. Service Discovery
- Internal service communication needs to be reconfigured
- Webhook URLs need to be updated for Kubernetes services

## Recommended AKS Architecture

### Pod Structure
1. **Backend Pod**: Single container for the Python application
2. **LiveKit Pod**: Single container for LiveKit server
3. **FreeSWITCH Pod**: Single container with security context for capabilities

### Service Types
- **Backend**: ClusterIP (internal only)
- **LiveKit**: LoadBalancer (external WebSocket access)
- **FreeSWITCH**: LoadBalancer (external SIP/RTP access)

### Storage Strategy
- **ConfigMaps**: Non-sensitive configuration
- **Secrets**: API keys and credentials
- **Azure Key Vault**: Integration for enhanced secret management
- **Persistent Volumes**: For any file-based storage needs

### Networking Strategy
- **Azure Load Balancer**: For external SIP and WebSocket traffic
- **Network Policies**: For internal service communication
- **Ingress Controller**: For HTTP/HTTPS traffic (if needed)

## Implementation Status ✅

All major components have been implemented:

1. ✅ **Kubernetes Manifests**: Complete manifests for all services
2. ✅ **Azure Integration**: ACR, Key Vault, Storage, Workload Identity
3. ✅ **Networking**: Load balancers, ingress, network policies
4. ✅ **Secrets Management**: Azure Key Vault integration
5. ✅ **Monitoring**: Azure Monitor and Application Insights
6. ✅ **CI/CD**: GitHub Actions and Azure DevOps pipelines
7. ✅ **Helm Charts**: For easier deployment management

## Quick Start Deployment

### Prerequisites
- Azure CLI installed and logged in
- kubectl installed
- Helm 3.x installed
- Docker installed (for local builds)

### Step 1: Set up Azure Resources
```bash
cd azure
./setup-azure.sh
```

### Step 2: Configure Secrets
```bash
cd azure/keyvault
./populate-secrets.sh
```

### Step 3: Set up Workload Identity
```bash
cd azure
./setup-workload-identity.sh
```

### Step 4: Build and Push Image
```bash
cd azure/acr
./build-and-push.sh
```

### Step 5: Deploy to AKS
```bash
cd k8s
./deploy.sh
```

## File Structure
```
├── azure/                          # Azure-specific configurations
│   ├── setup-azure.sh             # Main Azure setup script
│   ├── setup-workload-identity.sh # Workload Identity setup
│   ├── acr/                        # Container Registry
│   ├── keyvault/                   # Key Vault integration
│   └── storage/                    # Storage configurations
├── k8s/                            # Kubernetes manifests
│   ├── deploy.sh                   # Main deployment script
│   ├── shared/                     # Shared resources
│   ├── backend/                    # Backend service
│   ├── livekit/                    # LiveKit server
│   ├── freeswitch/                 # FreeSWITCH server
│   ├── networking/                 # Network policies, ingress
│   └── monitoring/                 # Monitoring configurations
├── helm/                           # Helm charts
│   └── vocare-restaurant/          # Main Helm chart
├── .github/workflows/              # GitHub Actions
└── docs/                           # Documentation
```