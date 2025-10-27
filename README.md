```
    ____        _ _      _
   |  _ \ __ _| | | ___| |_
   | |_) / _` | | |/ _ \ __|
   |  __/ (_| | | |  __/ |_
   |_|   \__,_|_|_|\___|\__|

   AI Agent Framework
   Google A2A Protocol • Dynamic Discovery
   JSON-RPC 2.0 • FastAPI
```

# Pallet - A2A Agent Framework

A framework for building and orchestrating AI agents using Google's A2A (Agent-to-Agent) protocol.

## Phase 5: Registry-based Orchestration

The Pallet framework implements **dynamic agent discovery** using an OCI registry. Agents are discovered at runtime based on their capabilities (skills) rather than hardcoded URLs.

### What It Does

The orchestrator (`orchestrator.py`) implements a simple 3-step pipeline:

```
Requirements (text)
    ↓
[Plan Agent] → Structured Plan (JSON)
    ↓
[Build Agent] → Generated Code (Python)
    ↓
[Test Agent] → Code Review (Score & Feedback)
    ↓
Results (saved to app/ folder)
```

**Key Innovation**: Agents are discovered **by their skill IDs**, not hardcoded URLs:

- Orchestrator asks: "Who has the `create_plan` skill?" → Gets Plan Agent URL
- Orchestrator asks: "Who has the `generate_code` skill?" → Gets Build Agent URL
- Orchestrator asks: "Who has the `review_code` skill?" → Gets Test Agent URL

This means you can add/replace agents without modifying the orchestrator—just update the registry!

### Workflow-Based Orchestration

Pallet uses a **declarative workflow engine** that separates workflow definitions from code:

- **Workflows are YAML files** stored in the OCI registry
- **Runtime workflow selection** based on requirements
- **Multiple execution patterns**: sequential, parallel, conditional, switch
- **Template expressions** for data flow between steps

Example workflows:
- `code-generation-v1`: Plan → Build → Test (default)
- `smart-router-v1`: Analyze request type → route to appropriate workflow
- `parallel-analysis-v1`: Run multiple analyses concurrently

See [docs/WORKFLOW_ENGINE.md](docs/WORKFLOW_ENGINE.md) for full documentation.

### Prerequisites

**Required (all platforms)**:
- Python 3.12+
- Docker Desktop or Docker daemon running
- `claude` CLI: `npm install -g @anthropic-ai/claude-cli`
- `ANTHROPIC_API_KEY` environment variable

**Optional (for Kubernetes-based setup)**:
- kind 0.20+
- Helm 3.12+
- kubectl 1.27+

**Installation** (macOS):
```bash
# Using Homebrew
brew install kind helm kubectl
```

See [specs/001-dev-env/quickstart.md](specs/001-dev-env/quickstart.md) for full setup guide.

### Quick Start

**1. Setup:**
```bash
uv sync && uv sync --extra test
npm install -g @anthropic-ai/claude-cli
export ANTHROPIC_API_KEY="your-api-key-here"
```

**2. Bootstrap** (choose one):

**Option A: Kubernetes-based (recommended)** - Requires kind/Helm:
```bash
bash scripts/bootstrap-k8s.sh    # Creates kind cluster + Helm registry deployment
bash scripts/verify-bootstrap.sh # Verify all services operational
```

**Option B: Docker-only (fallback)** - No additional tools needed:
```bash
bash scripts/bootstrap.sh        # Original Docker container setup
```

**3. Run orchestrator:**
```bash
uv run python main.py                                          # Default
uv run python main.py "Create a function that validates email" # Custom
```
Outputs: `app/main.py`, `app/plan.json`, `app/review.json`, `app/metadata.json`

**4. Tear down:**

For Kubernetes-based setup:
```bash
bash scripts/kill.sh --kind --clean-logs          # Delete cluster, clean logs/artifacts
bash scripts/kill.sh --kind --clean-logs --clean-pvc  # Also delete PVC data
```

For Docker-based setup:
```bash
bash scripts/kill.sh --clean-logs                 # Stop containers, clean logs
docker rmi registry:2                             # Optional: remove Docker image
```

**Cleanup options**:
- `--kind`: Delete kind cluster (pallet-dev) - use with K8s-based bootstrap
- `--clean-logs`: Remove logs/ and app/ directories
- `--clean-pvc`: Delete Persistent Volume Claim data (K8s only)

### How Discovery Works

**Setup**: `bash scripts/bootstrap.sh` → agent cards pushed to OCI registry via ORAS

**Runtime**: `uv run python main.py`
1. Orchestrator asks: "Who has `create_plan` skill?"
2. Discovery queries registry: get repos → pull agent cards → find matching skill
3. Returns agent URL (e.g., `http://localhost:8001`)
4. Repeats for `generate_code` and `review_code` skills

**Key Benefits**: No hardcoded URLs • Capability-driven • Pluggable • Scalable

**Agent Card Format**:
```json
{
  "name": "plan-agent",
  "url": "http://localhost:8001",
  "skills": [{"id": "create_plan", "description": "...", "input_schema": {...}, "output_schema": {...}}]
}
```

### Architecture

**Protocol**: HTTP + JSON-RPC 2.0 | **Discovery**: OCI Registry (ORAS) | **Communication**: `/execute` endpoint

**Each agent**:
- Inherits from `BaseAgent` (provides `/agent-card` and `/execute` endpoints)
- Implements single skill in `execute_skill()` method
- Calls Claude API via CLI subprocess: `claude ... -p --dangerously-skip-permissions`
- Exposes skill definition: id, description, input_schema, output_schema

### Project Structure

```
src/agents/           Plan, Build, Test agents + BaseAgent class
src/agent_cards/      Skill definitions (JSON)
src/orchestrator.py   Workflow-based orchestration + legacy pipeline
src/discovery.py      Registry queries, agent & workflow lookup
src/workflow_engine/  Workflow execution engine (data models, execution, registry)
workflows/            Example workflow definitions (YAML)
docs/WORKFLOW_ENGINE.md  Workflow engine documentation
main.py               CLI entry point (with --workflow flag)
tests/                Unit, integration, API tests (151+ tests, 87% coverage)
specs/                Phase 2-6 specifications
app/                  Output: main.py, plan.json, review.json, metadata.json
```

### Key Components

| Component | Role |
|-----------|------|
| `src/agents/base.py` | **BaseAgent**: FastAPI setup, `/agent-card` and `/execute` endpoints, Claude CLI wrapper |
| `src/orchestrator.py` | Chains agents, discovers by skill ID, saves outputs |
| `src/discovery.py` | Queries registry, pulls agent cards, finds agents by skill |
| `main.py` | Delegates to orchestrator |

### Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi`, `uvicorn` | Agent web servers (A2A endpoints) |
| `httpx` | Async HTTP for agent-to-agent calls |
| `pydantic` | Data validation |
| `oras` | Pull agent cards from OCI registry |
| `docker` | Run OCI registry container |

### Requirements

- `claude` CLI (in PATH): `npm install -g @anthropic-ai/claude-cli`
- `ANTHROPIC_API_KEY` environment variable

### Testing & Linting

**Linting:**
```bash
uv run invoke lint.black        # Format code
uv run invoke lint.black-check  # Check formatting
uv run invoke lint.flake8       # Style check
```

**Testing**:
```bash
uv run invoke test                      # All tests (default: skips slow/e2e)
uv run invoke test.unit                 # Unit tests only
uv run invoke test.integration          # Integration tests only
uv run invoke test.api                  # API endpoint tests only
uv run invoke test.verbose              # All tests with verbose output
uv run invoke test.coverage             # All coverage formats (HTML, terminal, XML)
uv run invoke test.debug                # Drop to pdb on test failure
```

**Code Quality**:
```bash
uv run invoke lint.black                # Format code with Black
uv run invoke lint.black-check          # Check if formatting is needed
uv run invoke lint.flake8               # Check code style with Flake8
```

See [tests/README.md](tests/README.md) for full invoke tasks reference.

### Troubleshooting

**Setup Issues**:

| Issue | Solution |
|-------|----------|
| `kind: command not found` | Install kind: `brew install kind` (macOS) or see https://kind.sigs.k8s.io/docs/user/quick-start/ |
| `helm: command not found` | Install helm: `brew install helm` (macOS) or see https://helm.sh/docs/intro/install/ |
| `Docker daemon not running` | Start Docker Desktop or `dockerd` |
| `Port 5000 already in use` | Run `lsof -i :5000` to find process, then `kill <PID>` or choose different port |
| `kind cluster not deleting` | Run `kind delete cluster --name pallet-dev` manually |

**Runtime Issues**:

| Issue | Solution |
|-------|----------|
| `Registry not responding` | Check: `curl http://localhost:5000/v2/` Should return `200 OK` or `401 Unauthorized` |
| `Agent not responding` | Check: `curl http://localhost:8001/agent-card` for plan agent (ports 8001/8002/8003) |
| `Helm release stuck` | Check: `helm list --namespace pallet` and `kubectl describe pod -n pallet` |
| `PVC not binding` | Check: `kubectl describe pvc -n pallet` for storage issues |

**Debugging**:

```bash
# Check cluster status
kind get clusters                                 # List clusters
kubectl cluster-info --context kind-pallet-dev   # Cluster details

# Check Helm deployment
helm list --namespace pallet                      # List releases
helm status registry --namespace pallet           # Release status

# Check pods
kubectl get pods -n pallet                        # Pod list
kubectl logs -n pallet <pod-name>                 # Pod logs
kubectl describe pod -n pallet <pod-name>         # Pod details

# Test registry
curl -v http://localhost:5000/v2/                 # Direct API test

# Clean up everything
bash scripts/kill.sh --kind --clean-logs --clean-pvc
```

### Learn More

- [tests/README.md](tests/README.md) - Test suite documentation
- [specs/phase5.md](specs/phase5.md) - Orchestration & discovery
- [specs/phase4.md](specs/phase4.md) - Discovery system
- [specs/phase3.md](specs/phase3.md) - Registry operations
- [specs/phase2.md](specs/phase2.md) - Three agent architecture
- [CLAUDE.md](CLAUDE.md) - Claude Code guidance
