# OCI Registry API Contract

**Version**: v2 (Docker Registry HTTP API V2)
**Source**: [OCI Image Spec](https://github.com/opencontainers/distribution-spec)
**Deployment**: Localhost on port 5000
**Purpose**: Contract for registry service deployed via Helm chart

## Base Endpoint

```
http://localhost:5000/v2/
```

## Health Check Endpoint

**Endpoint**: `GET /v2/`

**Description**: Verify OCI Registry v2 API is available and responding

**Request**:
```http
GET /v2/ HTTP/1.1
Host: localhost:5000
```

**Responses**:

### Success (Registry Ready)

```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 2

{}
```

**Status**: 200 OK
**Body**: Empty JSON object `{}`
**Meaning**: Registry is running and accepting requests

### Success (Authentication Required)

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="http://localhost:5000/auth/token",service="localhost:5000"
Content-Length: 0
```

**Status**: 401 Unauthorized
**Meaning**: Registry is running but authentication required (not expected for local dev, but acceptable)

### Failure (Registry Not Ready)

```
Connection refused
Timeout after 5 seconds
```

**Meaning**: Registry pod not yet running or port mapping failed

---

## Catalog Endpoint (Optional)

**Endpoint**: `GET /v2/_catalog`

**Description**: List all repositories in registry

**Request**:
```http
GET /v2/_catalog HTTP/1.1
Host: localhost:5000
```

**Response** (if repositories exist):
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "repositories": [
    "agents/plan",
    "agents/build",
    "agents/test"
  ]
}
```

---

## Push/Pull Operations (ORAS Client)

The registry exposes Docker Registry v2 API for ORAS push/pull operations.

**Example: Push artifact via ORAS**

```bash
oras push localhost:5000/agents/plan:v1 ./plan_agent_card.json
```

**Expected**: Success message, artifact stored in registry

**Example: Pull artifact via ORAS**

```bash
oras pull localhost:5000/agents/plan:v1 -o /tmp
```

**Expected**: Artifact extracted to `/tmp/plan_agent_card.json`

---

## Health Check Criteria

| Criterion | Threshold | Action if Failed |
|-----------|-----------|------------------|
| HTTP Status | 200 or 401 | Retry after 2 seconds (up to 30 attempts) |
| Response Time | <5 seconds | Mark unhealthy, timeout error |
| Port Accessibility | localhost:5000 | Ensure kind port mapping active |
| Endpoint Path | `/v2/` | Must be exact (case-sensitive) |

---

## Storage & Data

**Storage Location** (in pod):
- `/var/lib/registry/` (PVC mounted)

**Data Persistence**:
- Registry data persists across pod restarts
- Deleted only when PVC is explicitly removed (`kill.sh --clean-pvc`)

**Registry Config** (if customized):
- Loaded from ConfigMap (if created)
- Standard OCI Registry v2 configuration format

---

## Integration with Pallet

**Used By**:
1. **bootstrap-k8s.sh**: Calls `curl http://localhost:5000/v2/` to verify deployment
2. **Agent Discovery**: Agents query `/v2/agents/*` to find peers
3. **ORAS CLI**: Pushes agent cards to registry via Docker API v2

**Example: Agent Card Storage**

```
localhost:5000/agents/plan:v1
├── plan_agent_card.json (application/json)
└── (OCI artifact manifest)

localhost:5000/agents/build:v1
├── build_agent_card.json (application/json)

localhost:5000/agents/test:v1
├── test_agent_card.json (application/json)

localhost:5000/workflows/code-generation:v1
├── code-generation.yaml (application/x-yaml)
```

---

## Error Responses

**Invalid Repository**:
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{"errors": [{"code":"BLOB_UNKNOWN","message":"blob unknown to registry"}]}
```

**Unauthorized (if auth enabled)**:
```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer realm="...",service="..."
```

**Server Error**:
```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{"errors": [{"code":"UNSUPPORTED","message":"..."}]}
```

---

## Notes for Engineers

- **Local dev only**: Registry runs without authentication by default
- **Data is persisted**: Use `kill.sh --clean-pvc` if you need to reset registry
- **Port 5000**: Non-negotiable for `localhost:5000` access (hard-coded in agents)
- **Image tag**: Always use `registry:2.8.3+` to ensure API compatibility

---

## Troubleshooting

**Cannot reach registry**:
```bash
# Verify kind port mapping
kind get kubeconfig --name pallet-dev

# Check service
kubectl get service registry -n pallet -o wide

# Test directly
kubectl port-forward -n pallet service/registry 5000:5000
curl http://localhost:5000/v2/
```

**Registry returning 500 errors**:
```bash
# Check pod logs
kubectl logs -n pallet deployment/registry

# Check PVC status
kubectl get pvc -n pallet
```

**Images not persisting**:
```bash
# Verify PVC is bound
kubectl describe pvc registry-data -n pallet

# Check mount in pod
kubectl exec -n pallet deployment/registry -- ls -la /var/lib/registry/
```
