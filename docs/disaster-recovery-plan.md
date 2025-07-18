# Vocare Restaurant Assistant - Disaster Recovery Plan

## Overview

This document outlines the disaster recovery procedures for the Vocare Restaurant Assistant deployed on Azure AKS. The plan covers various failure scenarios and provides step-by-step recovery procedures.

## Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO)

| Component | RTO | RPO | Priority |
|-----------|-----|-----|----------|
| Backend Service | 15 minutes | 5 minutes | Critical |
| LiveKit Server | 10 minutes | 1 minute | Critical |
| FreeSWITCH | 20 minutes | 5 minutes | High |
| Configuration Data | 30 minutes | 1 hour | Medium |
| Historical Logs | 2 hours | 24 hours | Low |

## Backup Strategy

### Automated Backups
- **Daily**: Full cluster backup using `scripts/backup/backup-cluster.sh`
- **Hourly**: Configuration snapshots
- **Real-time**: Azure Key Vault automatic backup
- **Weekly**: Complete disaster recovery test

### Backup Locations
- **Primary**: Azure Storage Account (geo-redundant)
- **Secondary**: Azure Backup vault
- **Tertiary**: Off-site storage (optional)

## Failure Scenarios and Recovery Procedures

### Scenario 1: Single Pod Failure

**Symptoms**: One or more pods in CrashLoopBackOff or Error state

**Detection**:
- Kubernetes health checks
- Azure Monitor alerts
- Application unavailability

**Recovery Steps**:
```bash
# 1. Identify failed pods
kubectl get pods -n vocare-restaurant

# 2. Check pod logs
kubectl logs <pod-name> -n vocare-restaurant

# 3. Describe pod for events
kubectl describe pod <pod-name> -n vocare-restaurant

# 4. Restart deployment if needed
kubectl rollout restart deployment/<deployment-name> -n vocare-restaurant

# 5. Verify recovery
kubectl get pods -n vocare-restaurant
```

**Expected Recovery Time**: 2-5 minutes

### Scenario 2: Node Failure

**Symptoms**: All pods on a node become unavailable

**Detection**:
- Node status shows NotReady
- Pods stuck in Pending state
- Azure Monitor node alerts

**Recovery Steps**:
```bash
# 1. Check node status
kubectl get nodes

# 2. Cordon the failed node
kubectl cordon <node-name>

# 3. Drain the node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# 4. Verify pods rescheduled
kubectl get pods -n vocare-restaurant -o wide

# 5. Replace node (if needed)
az aks nodepool scale --resource-group $RESOURCE_GROUP --cluster-name $AKS_CLUSTER_NAME --name nodepool1 --node-count 4
```

**Expected Recovery Time**: 5-10 minutes

### Scenario 3: Cluster Failure

**Symptoms**: Entire AKS cluster is unavailable

**Detection**:
- kubectl commands fail
- Azure portal shows cluster issues
- All services unreachable

**Recovery Steps**:
```bash
# 1. Check cluster status
az aks show --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER_NAME

# 2. If cluster is corrupted, create new cluster
cd azure
./setup-azure.sh

# 3. Restore from backup
cd ../scripts/backup
# Extract latest backup
tar -xzf backups/latest-backup.tar.gz

# 4. Restore Kubernetes resources
kubectl apply -f backup-*/kubernetes/

# 5. Restore secrets (manual process)
cd backup-*/azure
./restore-secrets.sh $KEYVAULT_NAME

# 6. Verify all services
kubectl get all -n vocare-restaurant
```

**Expected Recovery Time**: 30-60 minutes

### Scenario 4: Azure Region Failure

**Symptoms**: Entire Azure region is unavailable

**Detection**:
- Azure Service Health notifications
- Complete service unavailability
- DNS resolution failures

**Recovery Steps**:
```bash
# 1. Create new cluster in different region
export LOCATION="westus2"  # Different region
cd azure
./setup-azure.sh

# 2. Update DNS records to point to new region
# (Manual process via DNS provider)

# 3. Restore from geo-redundant backup
# (Backup should be available in secondary region)

# 4. Full application restore
cd ../scripts/backup
./restore-from-backup.sh <backup-location>

# 5. Update external integrations
# - SIP provider configuration
# - Webhook URLs
# - API endpoints
```

**Expected Recovery Time**: 2-4 hours

### Scenario 5: Data Corruption

**Symptoms**: Application data is corrupted or inconsistent

**Detection**:
- Application errors
- Data validation failures
- User reports

**Recovery Steps**:
```bash
# 1. Stop affected services
kubectl scale deployment backend-deployment --replicas=0 -n vocare-restaurant

# 2. Identify corruption scope
# Check Firebase data, configuration, etc.

# 3. Restore from point-in-time backup
# Use Firebase console or backup tools

# 4. Restore configuration from backup
kubectl apply -f backup-*/kubernetes/configmaps.yaml
kubectl apply -f backup-*/kubernetes/secrets.yaml

# 5. Restart services
kubectl scale deployment backend-deployment --replicas=2 -n vocare-restaurant

# 6. Verify data integrity
# Run application tests
```

**Expected Recovery Time**: 1-3 hours

## Emergency Contacts and Escalation

### Primary Response Team
- **DevOps Lead**: [Name] - [Phone] - [Email]
- **Application Owner**: [Name] - [Phone] - [Email]
- **Azure Administrator**: [Name] - [Phone] - [Email]

### Escalation Matrix
1. **Level 1** (0-15 min): On-call engineer
2. **Level 2** (15-30 min): Team lead + Azure support
3. **Level 3** (30+ min): Management + vendor escalation

### External Contacts
- **Azure Support**: [Support Plan Details]
- **SIP Provider**: [Provider Support Contact]
- **DNS Provider**: [Provider Support Contact]

## Recovery Procedures

### Pre-Recovery Checklist
- [ ] Assess scope of failure
- [ ] Notify stakeholders
- [ ] Activate incident response team
- [ ] Document incident start time
- [ ] Preserve logs and evidence

### Recovery Execution
1. **Immediate Response** (0-5 minutes)
   - Confirm incident
   - Activate response team
   - Begin initial assessment

2. **Assessment Phase** (5-15 minutes)
   - Determine failure scope
   - Identify root cause
   - Select recovery strategy

3. **Recovery Phase** (15+ minutes)
   - Execute recovery procedures
   - Monitor progress
   - Validate recovery

4. **Verification Phase**
   - Test all critical functions
   - Verify data integrity
   - Confirm service availability

### Post-Recovery Checklist
- [ ] All services operational
- [ ] Data integrity verified
- [ ] Performance metrics normal
- [ ] Stakeholders notified
- [ ] Incident documentation complete

## Testing and Validation

### Monthly DR Tests
- Pod failure simulation
- Node failure simulation
- Backup/restore validation
- Network partition testing

### Quarterly DR Tests
- Full cluster recovery
- Cross-region failover
- End-to-end service validation
- Communication procedures

### Annual DR Tests
- Complete disaster simulation
- Full team participation
- External vendor coordination
- Plan updates and improvements

## Monitoring and Alerting

### Critical Alerts
- Pod restart loops
- Node unavailability
- Service endpoint failures
- High error rates
- Resource exhaustion

### Alert Channels
- **Immediate**: PagerDuty/SMS
- **High**: Slack/Teams
- **Medium**: Email
- **Low**: Dashboard notifications

## Documentation Updates

This disaster recovery plan should be reviewed and updated:
- After each incident
- Quarterly during DR tests
- When infrastructure changes
- When team members change

## Appendices

### Appendix A: Emergency Scripts
Location: `scripts/emergency/`
- `emergency-scale-down.sh`
- `emergency-diagnostics.sh`
- `emergency-restore.sh`

### Appendix B: Runbooks
Location: `docs/runbooks/`
- Pod troubleshooting
- Network debugging
- Performance optimization
- Security incident response

### Appendix C: Contact Information
- Team contact list
- Vendor support contacts
- Escalation procedures
- Communication templates