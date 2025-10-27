#!/bin/bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Checking prerequisites for kind-based bootstrap..."

# Check kind
if ! command -v kind &> /dev/null; then
    echo -e "${RED}✗ kind not found${NC}"
    echo "  Install: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
    exit 1
fi

KIND_VERSION=$(kind version | grep -oP 'kind v\K[0-9.]+')
echo -e "${GREEN}✓ kind v${KIND_VERSION}${NC}"

# Check helm
if ! command -v helm &> /dev/null; then
    echo -e "${RED}✗ helm not found${NC}"
    echo "  Install: https://helm.sh/docs/intro/install/"
    exit 1
fi

HELM_VERSION=$(helm version --short | grep -oP 'v\K[0-9.]+')
echo -e "${GREEN}✓ helm v${HELM_VERSION}${NC}"

# Check kubectl
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}✗ kubectl not found${NC}"
    echo "  Install: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null | grep -oP 'v\K[0-9.]+')
echo -e "${GREEN}✓ kubectl v${KUBECTL_VERSION}${NC}"

# Check docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ docker not found${NC}"
    echo "  Install: https://docs.docker.com/get-docker/"
    exit 1
fi

DOCKER_VERSION=$(docker --version | grep -oP 'version \K[0-9.]+')
echo -e "${GREEN}✓ docker v${DOCKER_VERSION}${NC}"

# Check Docker daemon
if ! docker ps &> /dev/null; then
    echo -e "${RED}✗ Docker daemon not running${NC}"
    echo "  Start Docker Desktop or docker daemon"
    exit 1
fi

echo -e "${GREEN}✓ Docker daemon running${NC}"

echo -e "${GREEN}All prerequisites met!${NC}"
