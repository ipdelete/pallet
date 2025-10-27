#!/bin/bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
CLUSTER_NAME="pallet-dev"
NAMESPACE="pallet"
RELEASE_NAME="registry"
CHART_PATH="$REPO_ROOT/charts/pallet-registry"
KIND_CONFIG="$REPO_ROOT/kind-config.yaml"
VALUES_FILE="$CHART_PATH/values-dev.yaml"

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

log_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

log_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Cleanup on exit
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Bootstrap failed with exit code $exit_code"
    fi
    return $exit_code
}

trap cleanup EXIT

# ============================================================================
# Step 1: Check prerequisites
# ============================================================================

log_info "Checking prerequisites..."

if ! bash "$SCRIPT_DIR/install-kind.sh"; then
    log_error "Prerequisites check failed"
    exit 1
fi

log_success "All prerequisites met"

# ============================================================================
# Step 2: Check if kind cluster already exists
# ============================================================================

log_info "Checking for existing kind cluster..."

if kind get clusters 2>/dev/null | grep -q "^$CLUSTER_NAME\$"; then
    log_warning "Kind cluster '$CLUSTER_NAME' already exists"
    log_info "Deleting existing cluster..."
    kind delete cluster --name "$CLUSTER_NAME" || true
fi

# ============================================================================
# Step 3: Create kind cluster
# ============================================================================

log_info "Creating kind cluster '$CLUSTER_NAME'..."

if ! kind create cluster --config "$KIND_CONFIG"; then
    log_error "Failed to create kind cluster"
    exit 1
fi

log_success "Kind cluster created"

# ============================================================================
# Step 4: Create namespace
# ============================================================================

log_info "Creating Kubernetes namespace '$NAMESPACE'..."

if ! kubectl create namespace "$NAMESPACE" 2>/dev/null; then
    log_warning "Namespace '$NAMESPACE' already exists or creation failed"
fi

log_success "Namespace ready"

# ============================================================================
# Step 5: Validate Helm chart
# ============================================================================

log_info "Validating Helm chart..."

if ! helm lint "$CHART_PATH" > /dev/null 2>&1; then
    log_error "Helm chart validation failed"
    exit 1
fi

log_success "Helm chart validated"

# ============================================================================
# Step 6: Install Helm release
# ============================================================================

log_info "Installing Helm release '$RELEASE_NAME'..."

if ! helm install "$RELEASE_NAME" "$CHART_PATH" \
    --namespace "$NAMESPACE" \
    --values "$VALUES_FILE"; then
    log_error "Failed to install Helm release"
    exit 1
fi

log_success "Helm release installed"

# ============================================================================
# Step 7: Wait for pod to be ready
# ============================================================================

log_info "Waiting for registry pod to be ready..."

max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    pod_count=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/instance="$RELEASE_NAME" 2>/dev/null | wc -l)

    if [ $((pod_count - 1)) -gt 0 ]; then
        # Pod exists, check if it's ready
        ready=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/instance="$RELEASE_NAME" \
            -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null)

        if [ "$ready" = "True" ]; then
            log_success "Registry pod is ready"
            break
        fi
    fi

    log_info "  Waiting for pod ready... (${attempt}/${max_attempts})"
    sleep 1
    ((attempt++))
done

if [ $attempt -eq $max_attempts ]; then
    log_warning "Pod readiness check timed out"
fi

# ============================================================================
# Step 8: Verify registry connectivity
# ============================================================================

log_info "Verifying registry connectivity..."

max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s "http://localhost:5000/v2/" > /dev/null 2>&1; then
        log_success "Registry is responsive at localhost:5000"
        break
    fi

    log_info "  Testing registry health... (${attempt}/${max_attempts})"
    sleep 1
    ((attempt++))
done

if [ $attempt -eq $max_attempts ]; then
    log_error "Registry health check timed out"
    exit 1
fi

# ============================================================================
# Bootstrap complete
# ============================================================================

log_success "Bootstrap complete!"
echo ""
echo "Kubernetes Development Environment Ready:"
echo "  Cluster: $CLUSTER_NAME"
echo "  Registry: localhost:5000"
echo "  Namespace: $NAMESPACE"
echo ""
echo "Next steps:"
echo "  1. Verify bootstrap: bash scripts/verify-bootstrap.sh"
echo "  2. Run orchestrator: uv run python main.py 'your requirements'"
echo "  3. Tear down: bash scripts/kill.sh --kind --clean-logs"
echo ""
