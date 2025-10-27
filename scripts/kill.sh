#!/bin/bash

#######################################################################
# Pallet Kill Script
#
# Tears down the complete Pallet agent orchestration system:
# 1. Stops all running agents
# 2. Stops the OCI registry
# 3. Clears the app folder
# 4. Optionally clears logs
#
# Usage: bash scripts/kill.sh [--clean-logs]
#######################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PALLET_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
APP_DIR="$PALLET_ROOT/app"
LOG_DIR="$PALLET_ROOT/logs"
REGISTRY_CONTAINER="local-registry"

# Flags
CLEAN_LOGS=false
CLEAN_KIND=false
CLEAN_PVC=false

#######################################################################
# Helper Functions
#######################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

#######################################################################
# Parse Arguments
#######################################################################

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --clean-logs)
                CLEAN_LOGS=true
                shift
                ;;
            --kind)
                CLEAN_KIND=true
                shift
                ;;
            --clean-pvc)
                CLEAN_PVC=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown argument: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << 'EOF'
Usage: bash scripts/kill.sh [OPTIONS]

Options:
  --kind          Delete kind cluster (pallet-dev)
  --clean-logs    Remove all agent logs and app outputs
  --clean-pvc     Delete Persistent Volume Claim data
  --help          Show this help message

Examples:
  bash scripts/kill.sh                             # Stop agents only
  bash scripts/kill.sh --kind --clean-logs         # K8s: delete cluster, clean logs
  bash scripts/kill.sh --clean-logs --clean-pvc    # Full cleanup including PVC data

EOF
}

#######################################################################
# Kill Agents
#######################################################################

kill_agents() {
    log_info "Stopping agents..."

    local killed=0
    local agents=("plan_agent" "build_agent" "test_agent")

    for agent in "${agents[@]}"; do
        # Find and kill the agent process
        if pgrep -f "src.agents.${agent}" > /dev/null; then
            pkill -f "src.agents.${agent}" || true
            log_success "Killed ${agent}"
            killed=$((killed + 1))
        fi
    done

    if [ $killed -eq 0 ]; then
        log_warning "No agents were running"
    else
        log_success "$killed agent(s) stopped"
    fi

    echo ""
}

#######################################################################
# Kill Kind Cluster
#######################################################################

kill_kind_cluster() {
    if [ "$CLEAN_KIND" = false ]; then
        return
    fi

    log_info "Cleaning up kind cluster..."

    # Check if kind is installed
    if ! command -v kind &> /dev/null; then
        log_warning "kind is not installed, skipping cluster cleanup"
        echo ""
        return
    fi

    # Check if cluster exists
    if kind get clusters 2>/dev/null | grep -q "^pallet-dev\$"; then
        log_info "Deleting kind cluster 'pallet-dev'..."

        if kind delete cluster --name pallet-dev; then
            log_success "Kind cluster deleted"
        else
            log_error "Failed to delete kind cluster"
            echo ""
            return 1
        fi

        # Optionally delete PVC data
        if [ "$CLEAN_PVC" = true ]; then
            log_info "PVC data was part of the cluster and is now removed"
        fi
    else
        log_warning "Kind cluster 'pallet-dev' not found"
    fi

    echo ""
}

#######################################################################
# Kill Registry
#
# Note: Removes the registry CONTAINER but keeps the Docker IMAGE.
# This allows for fast re-bootstrap on next run.
#######################################################################

kill_registry() {
    log_info "Stopping registry..."

    # Check if Docker is running
    if ! command -v docker &> /dev/null; then
        log_warning "Docker is not installed, skipping registry cleanup"
        echo ""
        return
    fi

    # Try to stop the container
    if docker ps --filter "name=$REGISTRY_CONTAINER" --format '{{.Names}}' | grep -q "^$REGISTRY_CONTAINER$"; then
        log_info "Stopping registry container ($REGISTRY_CONTAINER)..."
        docker stop "$REGISTRY_CONTAINER" > /dev/null 2>&1
        log_success "Registry container stopped"
    else
        log_warning "Registry container is not running"
    fi

    # Remove the container (but keep the Docker image for fast re-bootstrap)
    if docker ps -a --filter "name=$REGISTRY_CONTAINER" --format '{{.Names}}' | grep -q "^$REGISTRY_CONTAINER$"; then
        log_info "Removing registry container ($REGISTRY_CONTAINER)..."
        docker rm "$REGISTRY_CONTAINER" > /dev/null 2>&1
        log_success "Registry container removed"
        log_info "(Docker image 'registry:2' is retained for faster re-bootstrap)"
    fi

    echo ""
}

#######################################################################
# Clear App Folder
#######################################################################

clear_app_folder() {
    log_info "Clearing app folder..."

    if [ ! -d "$APP_DIR" ]; then
        log_warning "App folder does not exist: $APP_DIR"
        echo ""
        return
    fi

    # Count files before deletion
    local file_count=$(find "$APP_DIR" -type f 2>/dev/null | wc -l)

    if [ "$file_count" -gt 0 ]; then
        log_info "Removing $file_count file(s) from $APP_DIR..."
        rm -rf "$APP_DIR"/*
        log_success "App folder cleared"
    else
        log_warning "App folder is already empty"
    fi

    # Ensure directory exists
    mkdir -p "$APP_DIR"

    echo ""
}

#######################################################################
# Clear Logs (Optional)
#######################################################################

clear_logs() {
    if [ "$CLEAN_LOGS" = false ]; then
        return
    fi

    log_info "Clearing logs..."

    if [ ! -d "$LOG_DIR" ]; then
        log_warning "Log folder does not exist: $LOG_DIR"
        echo ""
        return
    fi

    local items_removed=0

    # Remove top-level .log files
    local log_files=$(find "$LOG_DIR" -maxdepth 1 -type f -name "*.log" 2>/dev/null)
    if [ -n "$log_files" ]; then
        find "$LOG_DIR" -maxdepth 1 -type f -name "*.log" -delete
        items_removed=$((items_removed + $(echo "$log_files" | wc -l)))
    fi

    # Remove agents/ directory and its contents
    if [ -d "$LOG_DIR/agents" ]; then
        rm -rf "$LOG_DIR/agents"
        log_info "Removed logs/agents/"
        items_removed=$((items_removed + 1))
    fi

    # Remove pallet/ directory and its contents
    if [ -d "$LOG_DIR/pallet" ]; then
        rm -rf "$LOG_DIR/pallet"
        log_info "Removed logs/pallet/"
        items_removed=$((items_removed + 1))
    fi

    if [ "$items_removed" -gt 0 ]; then
        log_success "Logs cleared (prompts/ preserved)"
    else
        log_warning "No logs to clear"
    fi

    echo ""
}

#######################################################################
# Main
#######################################################################

main() {
    parse_args "$@"

    cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║     Pallet Kill Script - System Teardown                       ║
╚════════════════════════════════════════════════════════════════╝

EOF

    kill_agents
    kill_kind_cluster
    kill_registry
    clear_app_folder
    clear_logs

    cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║           Pallet Shutdown Complete ✓                           ║
╚════════════════════════════════════════════════════════════════╝

All systems stopped and cleaned up.

To restart the system:
  bash scripts/bootstrap-k8s.sh  # Kubernetes-based (recommended)
  bash scripts/bootstrap.sh      # Docker-only (fallback)

EOF
}

main "$@"
