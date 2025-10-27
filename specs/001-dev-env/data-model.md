# Data Model: Kind Cluster + Helm Registry Deployment

**Date**: 2025-10-27
**Scope**: State transitions and entities for local K8s development environment

## Bootstrap State Machine

Engineers interact with the bootstrap process through discrete states:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Bootstrap State Transitions                    │
└─────────────────────────────────────────────────────────────────┘

[INITIAL]
   │
   ├─ Check dependencies (kind, helm, kubectl, docker)
   │
   ├─ Create kind cluster "pallet-dev"
   │  (State: CLUSTER_CREATING → CLUSTER_READY)
   │
   ├─ Create K8s namespace "pallet"
   │
   ├─ Helm install registry chart
   │  (State: RELEASE_INSTALLING → RELEASE_ACTIVE)
   │
   ├─ Wait for registry pod to be ready
   │  (State: POD_PENDING → POD_RUNNING → POD_READY)
   │
   ├─ Verify registry connectivity
   │  (State: REGISTRY_HEALTH_CHECKING → REGISTRY_HEALTHY)
   │
   └─> [READY] All systems operational
```

---

## Key Entities

### 1. Kind Cluster

**Entity**: `kind-cluster`
**Identifier**: Cluster name (e.g., `pallet-dev`)
**State Values**:
- `NOT_CREATED`: Kind cluster doesn't exist
- `CREATING`: `kind create cluster` in progress
- `READY`: Cluster running, kubectl accessible
- `DELETING`: `kind delete cluster` in progress
- `ERROR`: Creation failed

**Attributes**:
- `name`: String (default: `pallet-dev`)
- `kubeconfig`: File path (~/.kube/config updated by kind)
- `node_image`: String (kind/node:v1.27 or later)
- `port_mappings`: List (5000:5000 for registry)
- `created_at`: ISO8601 timestamp
- `control_plane_ready`: Boolean

**Transitions**:
- `NOT_CREATED` → `CREATING`: Engineer runs bootstrap-k8s.sh
- `CREATING` → `READY`: Kind cluster fully initialized (~15s)
- `READY` → `DELETING`: Engineer runs kill.sh --kind
- `DELETING` → `NOT_CREATED`: Kind cluster removed (~5s)
- Any → `ERROR`: Failure during creation/deletion

**Validation Rules**:
- Cluster name matches regex: `^[a-z0-9][a-z0-9-]*[a-z0-9]$` (K8s naming)
- Port 5000 available on localhost (or fail fast)
- Docker daemon running (prerequisite)

---

### 2. Helm Release

**Entity**: `helm-release`
**Identifier**: Release name (e.g., `registry`) + namespace (e.g., `pallet`)
**State Values**:
- `NOT_INSTALLED`: Helm release doesn't exist
- `INSTALLING`: `helm install` in progress
- `ACTIVE`: Release installed, chart running
- `UPDATING`: `helm upgrade` in progress
- `UNINSTALLING`: `helm uninstall` in progress
- `ERROR`: Installation/upgrade failed

**Attributes**:
- `name`: String (default: `registry`)
- `namespace`: String (default: `pallet`)
- `chart`: String (e.g., `./charts/pallet-registry`)
- `chart_version`: String (e.g., `1.0.0`)
- `values_file`: File path (e.g., `values-dev.yaml`)
- `installed_at`: ISO8601 timestamp
- `revision`: Integer (tracks helm release history)

**Transitions**:
- `NOT_INSTALLED` → `INSTALLING`: bootstrap-k8s.sh runs `helm install`
- `INSTALLING` → `ACTIVE`: All chart templates deployed (~10s)
- `ACTIVE` → `UPDATING`: Engineer runs `helm upgrade` (manual, not in bootstrap)
- `ACTIVE` → `UNINSTALLING`: kill.sh removes release
- `UNINSTALLING` → `NOT_INSTALLED`: Release removed (~5s)
- Any → `ERROR`: Chart validation fails or pod creation fails

**Validation Rules**:
- Chart lint passes (`helm lint`)
- All templates have required values
- Service port 5000 available on localhost

---

### 3. Kubernetes Deployment

**Entity**: `k8s-deployment`
**Identifier**: Deployment name (e.g., `registry`) in namespace `pallet`
**State Values**:
- `NOT_CREATED`: Deployment resource doesn't exist
- `CREATING`: Deployment created, pods launching
- `PROGRESSING`: Pods pending (pulling image, scheduling)
- `READY`: All replicas running and ready
- `FAILED`: Pods in CrashLoopBackOff or ImagePullBackOff
- `DELETING`: Deployment being removed

**Attributes**:
- `name`: String (default: `registry`)
- `namespace`: String (default: `pallet`)
- `image`: String (e.g., `registry:2.8.3`)
- `replicas_desired`: Integer (default: 1 for dev)
- `replicas_ready`: Integer (0–replicas_desired)
- `pod_selector`: Label selector (app: registry)

**Transitions**:
- `NOT_CREATED` → `CREATING`: helm install creates deployment
- `CREATING` → `PROGRESSING`: Pods scheduled to nodes
- `PROGRESSING` → `READY`: Pod image pulled, container started, readiness probe passes
- `READY` → `DELETING`: helm uninstall removes deployment
- `DELETING` → `NOT_CREATED`: Pod termination complete (~5s)
- `READY` → `FAILED`: Pod crash, image pull error, etc.
- `FAILED` → `READY`: Image availability restored (manual intervention or retry)

**Validation Rules**:
- Container image available (registry:2.8.3 exists on Docker Hub)
- Liveness probe: `curl http://localhost:5000/v2/` every 10s
- Readiness probe: Same as liveness (pod becomes "Ready" only if probe passes)
- Resource limits: CPU 500m, Memory 256Mi (prevents resource starvation)

---

### 4. Persistent Volume Claim (PVC)

**Entity**: `pvc`
**Identifier**: PVC name (e.g., `registry-data`) in namespace `pallet`
**State Values**:
- `NOT_CREATED`: PVC doesn't exist
- `PENDING`: PVC created, waiting for PV binding
- `BOUND`: PVC bound to PV, ready for mounting
- `RELEASED`: PVC unbound (after pod deletion)
- `DELETING`: PVC being removed

**Attributes**:
- `name`: String (default: `registry-data`)
- `namespace`: String (default: `pallet`)
- `size`: Quantity (e.g., `1Gi`)
- `storage_class`: String (default: local storage in kind)
- `access_modes`: List (ReadWriteOnce for single-replica setup)
- `mount_path`: String (e.g., `/var/lib/registry`)

**Transitions**:
- `NOT_CREATED` → `PENDING`: helm install creates PVC
- `PENDING` → `BOUND`: PV available and mounted to registry pod (~1s)
- `BOUND` → `DELETING`: helm uninstall removes PVC (with appropriate values)
- `DELETING` → `NOT_CREATED`: PVC resource deleted
- `RELEASED` → `BOUND`: Next pod mount uses same PV (if not deleted)

**Validation Rules**:
- Size minimum: 100Mi (absolute minimum for registry)
- Size default: 1Gi (sufficient for 100+ workflow definitions)
- StorageClass: Must exist in kind cluster (use local storage)

---

### 5. Health State

**Entity**: `health-status`
**Identifier**: Service identifier (e.g., `registry`)
**State Values**:
- `UNKNOWN`: Health status not yet checked
- `HEALTHY`: Service responding normally
- `DEGRADED`: Service responding but slow (>1s latency)
- `UNHEALTHY`: Service not responding or errors

**Attributes**:
- `service`: String (e.g., `registry`)
- `last_check`: ISO8601 timestamp
- `response_time_ms`: Integer (milliseconds)
- `status_code`: Integer (HTTP code, e.g., 200)
- `error_message`: String (if unhealthy, e.g., "Connection refused")

**Transitions**:
- `UNKNOWN` → `HEALTHY`: First health check succeeds
- `HEALTHY` → `DEGRADED`: Latency >1000ms
- `HEALTHY` → `UNHEALTHY`: Service unresponsive
- `UNHEALTHY` → `HEALTHY`: Service recovers
- `*` → `UNKNOWN`: Health check timeout

**Validation Rules**:
- Health endpoint: `curl -s http://localhost:5000/v2/` (OCI Registry v2 API)
- Success: HTTP 200 or 401 (both indicate registry is running)
- Timeout: 5 seconds max per check
- Retry: 3 attempts before marking unhealthy

---

## State Dependency Graph

```
┌──────────────────────┐
│   kind-cluster       │
│  (control-plane)     │
└──────────┬───────────┘
           │
           │ enables
           ▼
┌──────────────────────┐
│   helm-release       │
│   (registry chart)   │
└──────────┬───────────┘
           │
           │ creates
           ▼
┌──────────────────────┐        ┌──────────────────────┐
│  k8s-deployment      │◄──────►│      pvc             │
│  (registry pod)      │        │  (registry data)     │
└──────────┬───────────┘        └──────────────────────┘
           │
           │ exposes via
           ▼
┌──────────────────────┐
│  k8s-service         │
│  (localhost:5000)    │
└──────────┬───────────┘
           │
           │ monitored by
           ▼
┌──────────────────────┐
│  health-status       │
│  (registry HEALTHY)  │
└──────────────────────┘
```

**Dependency Rules**:
1. kind-cluster must be READY before helm-release can be ACTIVE
2. helm-release must be ACTIVE before k8s-deployment is READY
3. k8s-deployment must be READY before health-status is HEALTHY
4. PVC binding must complete before Deployment can mount volume

---

## API Contracts

### Helm Chart Values Schema

**Input** (values.yaml):
```yaml
image:
  repository: registry
  tag: "2.8.3"
  pullPolicy: IfNotPresent

replicaCount: 1

service:
  type: NodePort
  port: 5000
  nodePort: 5000

persistence:
  enabled: true
  size: 1Gi
  storageClassName: null  # Use default (local storage in kind)
  mountPath: /var/lib/registry

resources:
  limits:
    cpu: 500m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

livenessProbe:
  httpGet:
    path: /v2/
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5

readinessProbe:
  httpGet:
    path: /v2/
    port: 5000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
```

**Output** (after helm install):
- Pod running at `pallet/registry-<hash>`
- Service exposed at `localhost:5000`
- PVC bound to registry pod storage

### Registry API Contract

**Endpoint**: `http://localhost:5000/v2/`
**Method**: GET
**Authentication**: None (open for local dev)
**Response**:
```
HTTP 200 OK
{}
```

**Implies**: OCI Registry v2 API is ready to accept ORAS push/pull commands

---

## Cleanup & State Reset

### Partial Cleanup (kill.sh)
- Deletes: kind cluster, all pods, deployments, services
- Preserves: Nothing (hard delete)
- PVC behavior: Deleted (can use `--keep-pvc` flag to preserve)

### Full Cleanup (kill.sh --clean-logs)
- Deletes: Everything above + logs directory + app/ outputs
- Preserves: Nothing
- Result: Clean state for fresh bootstrap

### Verification Queries

**Check cluster status**:
```bash
kind get clusters                         # List clusters
kubectl cluster-info --context kind-pallet-dev  # Cluster details
```

**Check release status**:
```bash
helm list --namespace pallet              # List releases
helm status registry --namespace pallet   # Release details
```

**Check pod status**:
```bash
kubectl get pods -n pallet                # Pod list
kubectl describe pod registry-<hash> -n pallet  # Pod details
```

**Check PVC status**:
```bash
kubectl get pvc -n pallet                 # PVC list
kubectl describe pvc registry-data -n pallet  # PVC details
```

**Check health**:
```bash
curl http://localhost:5000/v2/            # Direct API test
```
