# Research: Kind + Helm for Registry Deployment

**Date**: 2025-10-27
**Scope**: Local development environment registry deployment
**Context**: Migrating from Docker-only (scripts/bootstrap.sh) to Kubernetes (kind) with Helm

## Research Tasks & Findings

### 1. Kind Setup Best Practices for macOS/Linux

**Decision**: Use `kind create cluster --name pallet-dev --config kind-config.yaml` with resource limits

**Rationale**:
- Kind v0.20+ is stable on macOS (Intel & Apple Silicon) and Linux
- Named clusters allow multiple environments
- ConfigFile enables resource configuration without CLI flags

**Alternatives Considered**:
- **minikube**: More complex setup, higher resource overhead. Kind is lighter for single-developer use.
- **k3s**: Requires manual installation. Kind leverages Docker (already required for Pallet).
- **Colima**: macOS-specific, not portable to Linux CI.

**Specifics**:
- **Minimum resources**: 2 CPU, 2GB RAM (kind default)
- **M1/M2 macs**: Native support in kind v0.20+; use `--image kindest/node:v1.27-amd64` for Colima compatibility
- **Cleanup**: `kind delete cluster --name pallet-dev` removes cluster + all persistent data
- **Config example**:
  ```yaml
  kind: Cluster
  apiVersion: kind.x-k8s.io/v1alpha4
  name: pallet-dev
  nodes:
  - role: control-plane
    extraPortMappings:
    - containerPort: 5000
      hostPort: 5000
      listenAddress: "127.0.0.1"
  ```

---

### 2. Helm Chart Structure for Registry Deployment

**Decision**: Use Helm chart with templates for Deployment, Service, PVC, ConfigMap

**Rationale**:
- Standard practice for K8s deployments
- Enables DRY config management (values.yaml for parameterization)
- Helm 3 (no Tiller) is simpler for local dev

**Alternatives Considered**:
- **Raw YAML manifests**: Less maintainable; duplicates resource definitions
- **Kustomize**: Less mature than Helm for this use case; Helm charts are more portable
- **Helm Operator**: Overkill for single OCI registry

**Specifics**:
- **Chart version**: Follow semver (Chart.yaml: `version: 1.0.0`)
- **App version**: OCI Registry v2.8.3+ (latest stable as of 2025-10-27)
- **Templates**:
  - `deployment.yaml`: Registry pod with liveness/readiness probes
  - `service.yaml`: NodePort service (5000:5000)
  - `pvc.yaml`: 1GB default (configurable in values.yaml)
  - `configmap.yaml`: Optional (for custom registry config like auth, storage backends)
- **Values separation**:
  - `values.yaml`: Production defaults (2 replicas, 10GB PVC)
  - `values-dev.yaml`: Dev overrides (1 replica, 1GB PVC, image pull policy: IfNotPresent)

---

### 3. PVC vs emptyDir Tradeoff

**Decision**: Use PVC for persistent registry data across teardowns (engineer preference)

**Rationale**:
- Developers expect `kill.sh --clean-logs` to stop services but preserve registries (workflow data)
- PVC survives pod restarts naturally in K8s
- Aligns with "repeatable but state-preserving" environment

**Alternatives Considered**:
- **emptyDir**: Data lost on pod restart; conflicts with "repeatable" requirement if engineers want state preserved
- **hostPath**: Not portable; requires specific node paths; security risk
- **NFS/Network storage**: Overkill for local dev; requires additional setup

**Specifics**:
- **Default size**: 1GB (sufficient for 100+ workflow definitions)
- **StorageClass**: Use default (local storage on host via kind)
- **Cleanup**: `kill.sh --clean-pvc` option to explicitly delete PVC data if needed
- **Backup**: Script to dump registry to local tar.gz before cleanup

---

### 4. Service Exposure Options (localhost:5000 Access)

**Decision**: Use NodePort service with port-forward or direct localhost binding

**Rationale**:
- Kind's `extraPortMappings` in cluster config enables direct localhost:5000 access
- No need for `kubectl port-forward` (simpler for scripts)
- Aligns with existing Docker setup (localhost:5000)

**Alternatives Considered**:
- **kubectl port-forward**: Requires running in background; fragile for automation
- **Ingress**: Overly complex for localhost; not needed for local dev
- **ClusterIP**: Doesn't expose to host; requires port-forward

**Specifics**:
- **kind-config.yaml**: Include `extraPortMappings` (see Task 1 above)
- **Service spec**: `type: NodePort` with `nodePort: 5000`
- **Verification**: `curl http://localhost:5000/v2/` should succeed within 5s of cluster creation

---

## Technology Versions & Compatibility

| Technology | Min Version | Recommended | Max Tested |
|------------|------------|------------|-----------|
| kind | 0.18 | 0.20+ | 0.24 |
| Helm | 3.0 | 3.12+ | 3.14 |
| kubectl | 1.24 | 1.27+ | 1.31 |
| OCI Registry | 2.6 | 2.8.3+ | 2.8.3 |
| docker | 20.10 | 24.0+ | 27.0 |

---

## Decision Rationale Matrix

| Decision | Why Chosen | Trade-offs | Fallback |
|----------|-----------|-----------|----------|
| kind for K8s | Lightweight, Docker-based, portable | Limited to local dev | Use `bootstrap.sh` (Docker-only) |
| Helm for config | Standard practice, DRY, parameterizable | Learning curve for new engineers | Raw YAML in scripts/ |
| PVC for storage | Persistence + reproducibility | Uses disk space; slower than emptyDir | Use emptyDir for ephemeral testing |
| NodePort + port-mapping | Direct localhost access, no kubectl port-forward needed | Requires kind config update | Use kubectl port-forward in bootstrap |

---

## Recommended Library Versions for Development

**Bootstrap environment (engineers)**:
```bash
kind version 0.20.0+
helm version 3.12.0+
kubectl version 1.27.0+ (auto-installed with kind)
docker version 24.0.0+
```

**CI/CD (automated testing)**:
```bash
kind version 0.20.0 (pinned for consistency)
helm version 3.12.0 (pinned for consistency)
```

---

## Next Steps (Phase 1)

1. Create `kind-config.yaml` in repo root with port-mapping config
2. Write `data-model.md` documenting bootstrap state transitions
3. Generate Helm chart skeleton in `charts/pallet-registry/`
4. Create integration test for kind cluster lifecycle

---

## References

- [kind Documentation](https://kind.sigs.k8s.io/)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
- [OCI Registry Image](https://hub.docker.com/_/registry)
- [Kubernetes Storage](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
