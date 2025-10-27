# Quick Start: Kind + Helm Registry Setup

**For**: Engineers setting up Pallet local development environment
**Time**: ~5 minutes (after prerequisites installed)

## Prerequisites

Ensure you have:
- Docker 24.0+ (`docker --version`)
- kind 0.20+ (`kind --version`)
- Helm 3.12+ (`helm --version`)
- kubectl 1.27+ (`kubectl version --client`)
- Git (for cloning Pallet)

### Install Prerequisites (macOS)

```bash
# Install kind (Kubernetes in Docker)
brew install kind

# Install Helm
brew install helm

# Verify Docker is installed and running
docker ps  # Should show Docker daemon active
```

### Install Prerequisites (Linux)

```bash
# Install kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install kubectl (if not present)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

## Bootstrap Pallet with Kind + Helm

### Step 1: Clone & Prepare

```bash
git clone https://github.com/ipdelete/pallet.git
cd pallet
uv sync && uv sync --extra test  # Sync Python dependencies
npm install -g @anthropic-ai/claude-cli  # Install Claude CLI
```

### Step 2: Run Bootstrap

```bash
bash scripts/bootstrap-k8s.sh
```

**What this does**:
1. ✓ Checks kind, helm, kubectl available
2. ✓ Creates kind cluster named `pallet-dev`
3. ✓ Deploys registry via Helm chart (`charts/pallet-registry/`)
4. ✓ Waits for registry to be healthy
5. ✓ Verifies all services responding

**Output** (on success):
```
╔════════════════════════════════════════╗
║    Pallet Bootstrap Complete ✓         ║
╚════════════════════════════════════════╝

System Status:
  Kind Cluster: pallet-dev (running)
  Registry:     localhost:5000 ✓
  Status:       All services ready

Next Steps:
  - Deploy agents: bash scripts/bootstrap-agents.sh
  - Run tests:     uv run invoke test
  - View logs:     kubectl logs -n pallet deployment/registry
```

### Step 3: Verify Setup

```bash
# Check kind cluster
kind get clusters                    # Should show: pallet-dev

# Check Helm release
helm list -n pallet                 # Should show: registry DEPLOYED

# Check registry health
curl http://localhost:5000/v2/      # Should return: 200 OK or 401

# Check pod status
kubectl get pods -n pallet          # Should show registry pod RUNNING
```

## Common Commands

### View Registry Status

```bash
# Human-readable status
kubectl get deployment registry -n pallet -o wide

# JSON status
kubectl get deployment registry -n pallet -o json | jq '.status'

# Pod logs
kubectl logs -n pallet deployment/registry --tail=50
```

### Test Registry Connection

```bash
# Direct API test
curl -v http://localhost:5000/v2/

# Using ORAS (if testing workflow storage)
oras push localhost:5000/test/demo:v1 hello.txt
oras pull localhost:5000/test/demo:v1 -o /tmp
```

### Upgrade Registry (if needed)

```bash
# Update Helm chart values
helm upgrade registry charts/pallet-registry -n pallet -f values-dev.yaml

# Check upgrade status
helm status registry -n pallet
```

## Troubleshooting

### Issue: "kind: command not found"

**Fix**: Install kind (see Prerequisites above)

```bash
kind --version  # Verify installation
```

### Issue: "Port 5000 already in use"

**Fix**: Stop existing process or use different port

```bash
# Find what's using port 5000
lsof -i :5000

# Kill the process (replace PID)
kill -9 <PID>

# Or use different port (advanced)
# Edit kind-config.yaml before bootstrap
```

### Issue: "Registry pod stuck in Pending"

**Fix**: Check PVC and storage availability

```bash
# Check PVC status
kubectl describe pvc registry-data -n pallet

# Check node storage
kubectl describe node pallet-dev-control-plane

# Clean up and retry
bash scripts/kill.sh --kind --clean-logs
bash scripts/bootstrap-k8s.sh
```

### Issue: "Helm lint fails"

**Fix**: Validate chart templates

```bash
# Check chart syntax
helm lint charts/pallet-registry/

# Debug template rendering
helm template registry charts/pallet-registry/ -n pallet
```

### Issue: "curl localhost:5000 times out"

**Fix**: Verify kind port mapping

```bash
# Check kind cluster details
kind get kubeconfig --name pallet-dev

# Check service port mapping
kubectl get service registry -n pallet

# Verify localhost binding
netstat -an | grep 5000
```

## Cleanup

### Stop Services (Keep Data)

```bash
bash scripts/kill.sh --kind
# Registry data preserved in kind storage
```

### Full Cleanup (Delete Everything)

```bash
bash scripts/kill.sh --kind --clean-logs --clean-pvc
# - Deletes kind cluster
# - Removes logs/
# - Removes app/ outputs
# - Deletes PVC data
```

## Next Steps

Once bootstrap succeeds:

1. **Deploy agents**: Follow `Agent Deployment Guide` (Phase 3)
2. **Run tests**: `uv run invoke test`
3. **Try orchestration**: `uv run python main.py "your requirements"`
4. **View logs**: `kubectl logs -n pallet -l app=registry`

## Environment Variables (Advanced)

```bash
# Override cluster name
export KIND_CLUSTER_NAME=my-pallet

# Override registry namespace
export REGISTRY_NAMESPACE=my-registry

# Use specific Helm values file
export HELM_VALUES_FILE=values-prod.yaml

# Then run bootstrap
bash scripts/bootstrap-k8s.sh
```

## FAQ

**Q: Can I have multiple Pallet instances?**
A: Yes. Use different `KIND_CLUSTER_NAME` values (e.g., `pallet-dev-1`, `pallet-dev-2`). Each creates a separate kind cluster.

**Q: Does this work on Windows?**
A: Yes, on WSL2. Prerequisites must be installed in WSL2 Ubuntu environment.

**Q: How do I use the Docker bootstrap instead of kind?**
A: Run `bash scripts/bootstrap.sh` (original Docker-only version).

**Q: What's the resource footprint?**
A: kind uses ~1GB RAM + ~5GB disk for cluster + registry data. Total for Pallet system: <2GB RAM, <10GB disk.

**Q: Can I inspect the Helm chart?**
A: Yes. Chart templates are in `charts/pallet-registry/templates/`. Run `helm template registry charts/pallet-registry/` to see rendered YAML.

## Getting Help

- **Helm issues**: `helm lint charts/pallet-registry/`
- **Kind issues**: `kind logs --name pallet-dev`
- **Pod issues**: `kubectl describe pod <pod-name> -n pallet`
- **Full logs**: See [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md)
