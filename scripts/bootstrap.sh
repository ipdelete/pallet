#!/bin/bash

#######################################################################
# Pallet Bootstrap Script
#
# Sets up the complete Pallet agent orchestration system:
# 1. Checks dependencies
# 2. Starts the OCI registry
# 3. Publishes agent cards to registry
# 4. Starts all three agents (Plan, Build, Test)
# 5. Verifies the setup
# 6. Provides instructions for running orchestration
#
# Usage: bash scripts/bootstrap.sh
#######################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGISTRY_URL="localhost:5000"
REGISTRY_NAMESPACE="agents"
PALLET_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_CARDS_DIR="$PALLET_ROOT/src/agent_cards"
SCRIPTS_DIR="$PALLET_ROOT/scripts"
LOG_DIR="$PALLET_ROOT/logs"

# Agents configuration
declare -A AGENTS=(
    ["plan"]="8001"
    ["build"]="8002"
    ["test"]="8003"
)

mkdir -p "$LOG_DIR"

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

wait_for_port() {
    local port=$1
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        # Try nc first, fall back to bash TCP check or sleep
        if command -v nc &> /dev/null; then
            if nc -z localhost "$port" 2>/dev/null; then
                return 0
            fi
        elif timeout 1 bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 0.5
    done

    return 1
}

#######################################################################
# Step 1: Check Dependencies
#######################################################################

check_dependencies() {
    log_info "Checking dependencies..."

    local missing_deps=0

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker."
        missing_deps=1
    else
        log_success "Docker found: $(docker --version)"
    fi

    # Check ORAS
    if ! command -v oras &> /dev/null; then
        log_warning "ORAS CLI not found. Installing..."
        bash "$SCRIPTS_DIR/install-oras.sh"
    else
        log_success "ORAS found"
    fi

    # Check uv
    if ! command -v uv &> /dev/null; then
        log_error "uv is not installed. Please install uv or run 'pip install uv'."
        missing_deps=1
    else
        log_success "uv found"
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install jq."
        missing_deps=1
    else
        log_success "jq found"
    fi

    # Check nc (netcat) - optional, will use bash TCP checks as fallback
    if command -v nc &> /dev/null; then
        log_success "netcat found"
    else
        log_warning "netcat (nc) not found. Will use bash TCP checks as fallback."
    fi

    if [ $missing_deps -eq 1 ]; then
        log_error "Please install missing dependencies and try again."
        exit 1
    fi

    echo ""
}

#######################################################################
# Step 2: Start Registry
#######################################################################

start_registry() {
    log_info "Starting OCI registry..."

    local registry_name="local-registry"
    local registry_port="5000"
    local registry_image="registry:2"

    # Check if container is already running
    if docker ps --filter "name=$registry_name" --format "{{.Names}}" | grep -q "$registry_name"; then
        log_success "Registry container is already running"
    else
        # Remove stopped container if it exists
        if docker ps -a --filter "name=$registry_name" --format "{{.Names}}" | grep -q "$registry_name"; then
            log_info "Removing stopped registry container..."
            docker rm "$registry_name" > /dev/null 2>&1 || true
        fi

        # Start new registry container
        log_info "Starting registry container..."
        docker run -d -p "$registry_port:5000" --name "$registry_name" "$registry_image" > /dev/null 2>&1
        sleep 1
    fi

    # Wait for registry to be ready
    log_info "Waiting for registry to be ready..."
    if wait_for_port 5000; then
        log_success "Registry is ready"
    else
        log_error "Registry failed to start on port 5000"
        exit 1
    fi

    echo ""
}

#######################################################################
# Step 3: Publish Agent Cards to Registry
#######################################################################

publish_agent_cards() {
    log_info "Publishing agent cards to registry..."

    cd "$PALLET_ROOT"

    for agent in "${!AGENTS[@]}"; do
        local card_file="$AGENT_CARDS_DIR/${agent}_agent_card.json"
        local registry_path="$REGISTRY_URL/$REGISTRY_NAMESPACE/$agent:v1"

        if [ ! -f "$card_file" ]; then
            log_error "Agent card not found: $card_file"
            exit 1
        fi

        log_info "Publishing ${agent} agent card..."

        # Push agent card to registry using ORAS
        if oras push "$registry_path" "$card_file" --disable-path-validation > /tmp/oras_push.log 2>&1; then
            log_success "${agent} agent card published"
        else
            log_error "Failed to publish ${agent} agent card"
            cat /tmp/oras_push.log
            exit 1
        fi
    done

    log_success "All agent cards published"
    echo ""
}

#######################################################################
# Step 4: Start Agents
#######################################################################

start_agents() {
    log_info "Starting agents..."

    cd "$PALLET_ROOT"

    for agent in "${!AGENTS[@]}"; do
        local port=${AGENTS[$agent]}
        local log_file="$LOG_DIR/${agent}_agent.log"

        log_info "Starting ${agent} agent (port $port)..."

        # Start agent in background
        uv run python -m src.agents.${agent}_agent > "$log_file" 2>&1 &
        local pid=$!

        # Wait for agent to be ready
        if wait_for_port "$port"; then
            log_success "${agent} agent started (PID: $pid, port: $port)"
        else
            log_error "${agent} agent failed to start on port $port"
            cat "$log_file"
            exit 1
        fi

        sleep 1
    done

    echo ""
}

#######################################################################
# Step 5: Verify Setup
#######################################################################

verify_setup() {
    log_info "Verifying setup..."

    cd "$PALLET_ROOT"

    # Helper function for checking port
    check_port() {
        local port=$1
        if command -v nc &> /dev/null; then
            nc -z localhost "$port" 2>/dev/null
        else
            timeout 1 bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null
        fi
    }

    # Check registry
    if ! check_port 5000; then
        log_error "Registry is not responding on port 5000"
        exit 1
    fi
    log_success "Registry is running"

    # Check agents
    for agent in "${!AGENTS[@]}"; do
        local port=${AGENTS[$agent]}

        if ! check_port "$port"; then
            log_error "${agent} agent is not responding on port $port"
            exit 1
        fi
        log_success "${agent} agent is running on port $port"
    done

    # Run registry verification script
    log_info "Running registry verification..."
    bash "$SCRIPTS_DIR/verify_registry.sh" > /dev/null 2>&1 && \
        log_success "Registry verification passed" || \
        log_warning "Registry verification had issues (agents may still be publishing)"

    echo ""
}

#######################################################################
# Step 6: Print Instructions
#######################################################################

print_instructions() {
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║           Pallet Bootstrap Complete ✓                          ║
╚════════════════════════════════════════════════════════════════╝

System Status:
  Registry:     localhost:5000
  Plan Agent:   localhost:8001
  Build Agent:  localhost:8002
  Test Agent:   localhost:8003

Running Services:
  - OCI Registry (storing agent cards)
  - Plan Agent (creates structured plans)
  - Build Agent (generates code from plans)
  - Test Agent (reviews generated code)

═══════════════════════════════════════════════════════════════════

NEXT STEPS - Run the Orchestrator:

  1. In a new terminal, run the orchestrator:

     uv run python orchestrator.py "Your requirements here"

     Or use the default requirements:

     uv run python orchestrator.py

  2. The orchestrator will:
     - Discover agents from the registry
     - Send requirements to the Plan Agent
     - Pass the plan to the Build Agent
     - Pass the code to the Test Agent
     - Display results

═══════════════════════════════════════════════════════════════════

AVAILABLE COMMANDS:

  List all available skills:
    uv run python -m src.cli_discover skills

  Find a specific agent by skill:
    uv run python -m src.cli_discover find create_plan
    uv run python -m src.cli_discover find generate_code
    uv run python -m src.cli_discover find review_code

  List all agents:
    uv run python -m src.cli_discover agents

═══════════════════════════════════════════════════════════════════

LOGS & DEBUGGING:

  View agent logs:
    tail -f logs/plan_agent.log
    tail -f logs/build_agent.log
    tail -f logs/test_agent.log

  Check registry contents:
    oras pull localhost:5000/agents/plan:v1 -o /tmp/plan
    cat /tmp/plan/plan_agent_card.json | jq '.'

═══════════════════════════════════════════════════════════════════

STOPPING THE SYSTEM:

  Stop all services and clean up:
    bash scripts/kill.sh              # Keep logs for debugging
    bash scripts/kill.sh --clean-logs # Also remove logs

  For more options, see:
    bash scripts/kill.sh --help

═══════════════════════════════════════════════════════════════════

EOF
}

#######################################################################
# Main
#######################################################################

main() {
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║     Pallet Bootstrap - Agent Orchestration System              ║
║                                                                ║
║  Setting up: Registry → Agents → Orchestration                ║
╚════════════════════════════════════════════════════════════════╝

EOF

    check_dependencies
    start_registry
    publish_agent_cards
    start_agents
    verify_setup
    print_instructions

    log_success "Bootstrap complete! Ready for orchestration."
}

main
