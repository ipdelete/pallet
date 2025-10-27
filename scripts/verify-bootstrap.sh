#!/bin/bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

log_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

log_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

echo "Verifying bootstrap status..."
echo ""

# Check kind cluster
log_info "Checking kind cluster..."
if kind get clusters 2>/dev/null | grep -q "^pallet-dev\$"; then
    log_success "Kind cluster 'pallet-dev' exists"
else
    log_error "Kind cluster 'pallet-dev' not found"
    exit 1
fi

# Check Helm release
log_info "Checking Helm release..."
if helm list --namespace pallet 2>/dev/null | grep -q "registry"; then
    log_success "Helm release 'registry' is active"
else
    log_error "Helm release 'registry' not found"
    exit 1
fi

# Check registry pod
log_info "Checking registry pod..."
if kubectl get pods -n pallet -l app.kubernetes.io/instance="registry" &>/dev/null; then
    pod_name=$(kubectl get pods -n pallet -l app.kubernetes.io/instance="registry" -o jsonpath='{.items[0].metadata.name}')
    log_success "Registry pod '$pod_name' exists"
else
    log_error "Registry pod not found"
    exit 1
fi

# Check registry connectivity
log_info "Checking registry connectivity..."
if curl -s "http://localhost:5000/v2/" > /dev/null 2>&1; then
    log_success "Registry is accessible at localhost:5000"
else
    log_error "Registry is not responding at localhost:5000"
    exit 1
fi

# Optional: Check agents (if running)
log_info "Checking optional services..."
for port in 8001 8002 8003; do
    if curl -s "http://localhost:${port}/agent-card" > /dev/null 2>&1; then
        agent_name="unknown"
        case $port in
            8001) agent_name="Plan" ;;
            8002) agent_name="Build" ;;
            8003) agent_name="Test" ;;
        esac
        log_success "$agent_name Agent is accessible at localhost:${port}"
    else
        log_warning "Agent at localhost:${port} not responding (may not be running)"
    fi
done

echo ""
log_success "Bootstrap verification complete!"
echo ""
echo "System Status:"
echo "  ✓ Kind cluster: pallet-dev"
echo "  ✓ Helm release: registry"
echo "  ✓ Registry: localhost:5000"
echo "  ? Agents: check above"
echo ""
