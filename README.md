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

### Quick Start

**1. Setup:**
```bash
uv sync && uv sync --extra test
npm install -g @anthropic-ai/claude-cli
export ANTHROPIC_API_KEY="your-api-key-here"
```

**2. Bootstrap** (auto-configures everything):
```bash
bash scripts/bootstrap.sh
```
Starts registry (5000), agents (8001-8003), verifies services

**3. Run orchestrator:**
```bash
uv run python main.py                                          # Default
uv run python main.py "Create a function that validates email" # Custom
```
Outputs: `app/main.py`, `app/plan.json`, `app/review.json`, `app/metadata.json`

**4. Tear down:**
```bash
bash scripts/kill.sh --clean-logs  # Stop all services, clear logs
docker rmi registry:2              # Optional: remove Docker image
```

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

**Testing** (151 tests, 87% coverage):
```bash
uv run invoke test              # All (default: skips slow/e2e)
uv run invoke test.unit         # Unit only
uv run invoke test.integration  # Integration only
uv run invoke test.api          # API endpoints only
uv run invoke test.coverage     # All coverage formats (HTML, terminal, XML)
uv run invoke test.debug        # Drop to pdb on failure
```

See [tests/README.md](tests/README.md) for full invoke tasks reference.

### Learn More

- [tests/README.md](tests/README.md) - Test suite documentation
- [specs/phase5.md](specs/phase5.md) - Orchestration & discovery
- [specs/phase4.md](specs/phase4.md) - Discovery system
- [specs/phase3.md](specs/phase3.md) - Registry operations
- [specs/phase2.md](specs/phase2.md) - Three agent architecture
- [CLAUDE.md](CLAUDE.md) - Claude Code guidance
