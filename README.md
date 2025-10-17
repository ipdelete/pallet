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

### Quick Start

#### 1. Install Dependencies

```bash
# Install Python dependencies with uv
uv sync

# Install Claude CLI (if not already installed)
# See: https://github.com/anthropics/claude-cli
npm install -g @anthropic-ai/claude-cli

# Set up Claude API credentials
export ANTHROPIC_API_KEY="your-api-key-here"
```

#### 2. Bootstrap the System (Automated)

The `scripts/bootstrap.sh` script handles all setup automatically:

```bash
bash scripts/bootstrap.sh
```

This will:
- ✅ Check all dependencies (Docker, ORAS, uv, jq)
- ✅ Start the OCI registry (port 5000)
- ✅ Push agent cards to registry
- ✅ Start Plan Agent (port 8001)
- ✅ Start Build Agent (port 8002)
- ✅ Start Test Agent (port 8003)
- ✅ Verify all services are running
- ✅ Print ready-to-use commands

#### 3. Run the Orchestrator

After bootstrap completes, in a new terminal:

```bash
# With default requirements:
uv run python main.py

# With custom requirements:
uv run python main.py "Create a function that calculates Fibonacci numbers"
```

The orchestrator will:
- Discover all agents from the registry (by skill ID)
- Chain them together: Plan → Build → Test
- Save results to `app/` folder:
  - `app/main.py` - Generated code
  - `app/plan.json` - Implementation plan
  - `app/review.json` - Code review
  - `app/metadata.json` - Pipeline metadata

#### 4. Tear Down the System

To stop all services and clean up:

```bash
bash scripts/kill.sh              # Stop services, keep logs
bash scripts/kill.sh --clean-logs # Stop services and remove logs
```

This will:
- ✅ Stop all agents
- ✅ Stop the OCI registry **container** (removes container, keeps Docker image)
- ✅ Clear the `app/` folder
- ✅ Optionally clear logs

**Note**: The Docker image is retained for fast re-bootstrap. To remove the image:
```bash
docker rmi registry:2
```

### How Registry-based Discovery Works

The orchestrator uses a **skill-based discovery** system:

**Setup Phase** (`bash scripts/bootstrap.sh`):
1. Agent cards are **pushed** to OCI registry via `oras push`
2. Cards remain in registry for lifetime of system

**Runtime Phase** (`uv run python main.py`):
```
main.py (entry point) calls:
  src/orchestrator.py calls:
    discover_agent("create_plan")
      ↓
discovery.py queries registry:
  1. Get all repositories: registry → ["agents/plan", "agents/build", "agents/test"]
  2. For each agent, pull agent card from OCI registry using ORAS
  3. Parse agent card JSON to extract skills
  4. Search for matching skill ID in agent.skills[]
  5. Return agent URL if skill found
      ↓
src/orchestrator.py gets: "http://localhost:8001"
```

**Agent Card Format** (stored in OCI registry):
```json
{
  "name": "plan-agent",
  "url": "http://localhost:8001",
  "skills": [
    {
      "id": "create_plan",
      "description": "Creates structured implementation plans",
      "input_schema": {...},
      "output_schema": {...}
    }
  ]
}
```

**Why This Matters**:
- ✅ **No Hardcoded URLs**: Orchestrator discovers agents dynamically
- ✅ **Capability-driven**: Find agents by what they can do, not their address
- ✅ **Pluggable**: Add new agents with any skill by updating registry
- ✅ **Scalable**: Registry stores agent cards as versioned OCI artifacts

### Architecture

The agents communicate via Google's A2A protocol:
- **Transport**: HTTP with JSON-RPC 2.0
- **Discovery**: Registry-based (OCI artifact storage with ORAS)
- **Communication**: POST requests to `/execute` endpoint
- **Agent Cards**: JSON specifications stored as versioned artifacts

Each agent:
- Has one or more skills defined in its agent card
- Inherits from `BaseAgent` class
- Invokes Claude API via CLI subprocess (`claude` command)
- Exposes `/agent-card` endpoint for A2A protocol compliance

### Project Structure

```
src/
├── agents/
│   ├── base.py              # BaseAgent class (A2A protocol endpoints)
│   ├── plan_agent.py        # Plan Agent (create_plan skill)
│   ├── build_agent.py       # Build Agent (generate_code skill)
│   └── test_agent.py        # Test Agent (review_code skill)
├── agent_cards/
│   ├── plan_agent_card.json      # Plan agent skill definitions
│   ├── build_agent_card.json     # Build agent skill definitions
│   └── test_agent_card.json      # Test agent skill definitions
├── orchestrator.py          # Core orchestration logic (Phase 5)
├── discovery.py             # Registry discovery module
└── cli_discover.py          # CLI for querying registry

specs/
├── phase2.md               # Three Minimal Agents specification
├── phase3.md               # Registry Operations specification
├── phase4.md               # Discovery specification
└── phase5.md               # Orchestration specification

main.py                    # Entry point (thin wrapper)
pyproject.toml             # Dependencies
README.md                  # This file
app/                       # Generated code output folder
```

### Key Files for Discovery

| File | Purpose |
|------|---------|
| `src/discovery.py` | **RegistryDiscovery class** - queries registry, pulls agent cards, finds agents by skill ID |
| `src/orchestrator.py` | Core orchestration logic - uses `discover_agent()` to look up agents by skill ID |
| `main.py` | Entry point - delegates to `src/orchestrator.py` |
| `src/agent_cards/*.json` | Agent card definitions stored in OCI registry |
| `src/agents/base.py` | Agents expose `/agent-card` endpoint for A2A protocol compliance |

### Dependencies

- **fastapi**: Web framework for agents
- **uvicorn**: ASGI server for FastAPI
- **httpx**: Async HTTP client for agent communication
- **pydantic**: Data validation
- **oras**: OCI Registry as Storage (for pulling agent cards)
- **docker**: For running the OCI registry

### System Requirements

- **claude** CLI: Must be installed and in PATH for agents to invoke Claude API
- **ANTHROPIC_API_KEY**: Environment variable with valid Claude API key (for claude CLI)

### For More Information

- [specs/phase5.md](specs/phase5.md) - Orchestration with dynamic discovery
- [specs/phase4.md](specs/phase4.md) - Registry discovery system
- [specs/phase3.md](specs/phase3.md) - Registry operations
- [specs/phase2.md](specs/phase2.md) - Three agent architecture
