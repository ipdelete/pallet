# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pallet is a framework for building and orchestrating AI agents using Google's A2A (Agent-to-Agent) protocol. Phase 2 implements three minimal agents (Plan, Build, Test) that communicate via FastAPI and JSON-RPC 2.0, with each agent using Claude API for AI processing.

## Common Development Commands

### Setup
```bash
# Install dependencies using uv
uv sync
```

### Bootstrap the System (Recommended)

Use the automated bootstrap script to set up everything:

```bash
bash scripts/bootstrap.sh
```

This handles all setup automatically:
- ✅ Checks dependencies (Docker, ORAS, uv, jq)
- ✅ Starts OCI registry (port 5000)
- ✅ Pushes agent cards to registry
- ✅ Starts Plan Agent (port 8001)
- ✅ Starts Build Agent (port 8002)
- ✅ Starts Test Agent (port 8003)
- ✅ Verifies all services running
- ✅ Prints ready-to-use commands

### Testing the Full Pipeline

After bootstrap completes, run the orchestrator in a new terminal:

```bash
# With default requirements:
uv run python main.py

# With custom requirements:
uv run python main.py "Create a function that validates email addresses"
```

Results are automatically saved to:
- `app/main.py` - Generated code
- `app/plan.json` - Implementation plan
- `app/review.json` - Code review
- `app/metadata.json` - Pipeline metadata

### Tear Down the System

To stop all services and clean up:

```bash
bash scripts/kill.sh              # Stop services, keep logs
bash scripts/kill.sh --clean-logs # Stop services and remove logs
```

**What it does:**
- Stops all agents (plan, build, test)
- Stops and removes the registry **container** (keeps Docker image for fast re-bootstrap)
- Clears the `app/` output folder
- Optionally clears logs (`--clean-logs` flag)

**To remove the Docker image completely:**
```bash
docker rmi registry:2
```

### Manual Agent Control (Advanced)

For manual testing, you can run agents individually in separate terminals:

```bash
# Terminal 1: Plan Agent (port 8001)
uv run python -m src.agents.plan_agent

# Terminal 2: Build Agent (port 8002)
uv run python -m src.agents.build_agent

# Terminal 3: Test Agent (port 8003)
uv run python -m src.agents.test_agent
```

But this requires manual registry setup. Use `bash scripts/bootstrap.sh` for easier setup.

### Environment Setup
```bash
# Required for Claude API access
export ANTHROPIC_API_KEY="your-api-key-here"
```

## Architecture Overview

### Core Concept
The project implements Google's A2A protocol using FastAPI. Three agents form a pipeline:
1. **Plan Agent** (port 8001) - Converts requirements to structured plans
2. **Build Agent** (port 8002) - Generates code from plans
3. **Test Agent** (port 8003) - Reviews code for quality

Each agent inherits from `BaseAgent` and implements a single skill.

### Communication Flow
- **Protocol**: JSON-RPC 2.0 over HTTP
- **Discovery**: Agents expose `/agent-card` endpoint describing capabilities
- **Execution**: Clients POST to `/execute` endpoint with JSON-RPC messages
- **Response Format**:
  ```json
  {
    "jsonrpc": "2.0",
    "result": {...},
    "id": "message-id"
  }
  ```

### Key Files & Responsibilities

#### `src/agents/base.py` - Shared Foundation
- **BaseAgent** class that all agents inherit from
- Provides FastAPI app setup and A2A endpoint handling (`/agent-card`, `/execute`)
- `execute_skill()` - Abstract method implemented by each agent
- `call_claude()` - Calls Claude via CLI subprocess (requires `claude` CLI installed)
- `call_agent_skill()` - Makes HTTP requests to other agents
- **Important**: The `call_claude()` method uses subprocess to invoke the `claude` CLI with `-p --dangerously-skip-permissions` flags. This expects the Claude CLI to be in PATH.

#### Agent Implementation Pattern
Each agent (plan, build, test) follows this structure:
```python
class AgentName(BaseAgent):
    def __init__(self):
        skills = [SkillDefinition(...)]  # Define capabilities
        super().__init__(name="...", port=PORT, skills=skills)

    async def execute_skill(self, skill_id, params):
        # Validate parameters
        # Call self.call_claude() with system_prompt and user_message
        # Parse JSON response (handles markdown code blocks)
        # Return structured result
```

### Agent Details

#### Plan Agent (`src/agents/plan_agent.py`)
- **Skill**: `create_plan`
- **Input**: `{"requirements": string}`
- **Output**: JSON with title, steps, dependencies, estimated_total_time
- **Process**: Sends requirements to Claude with planning system prompt, expects JSON response

#### Build Agent (`src/agents/build_agent.py`)
- **Skill**: `generate_code`
- **Input**: `{"plan": object}`
- **Output**: JSON with code, explanation, language, functions array
- **Process**: Converts plan to JSON string, sends to Claude for code generation

#### Test Agent (`src/agents/test_agent.py`)
- **Skill**: `review_code`
- **Input**: `{"code": string, "language": string}`
- **Output**: JSON with quality_score (1-10), issues, suggestions, approved (boolean), summary
- **Process**: Sends code to Claude with review prompt

### Orchestrator Architecture

**Entry Point** (`main.py`):
- Thin wrapper that parses CLI arguments
- Delegates to core orchestration logic in `src/orchestrator.py`
- Usage: `uv run python main.py [requirements]`

**Core Logic** (`src/orchestrator.py`):
- Chains the three agents sequentially: Plan → Build → Test
- Uses dynamic discovery to find agents by skill ID
- Makes A2A calls via HTTP with JSON-RPC 2.0
- Saves results to `app/` folder (code, plan, review, metadata)
- Default requirements if none provided; accepts custom requirements
- Formats and displays results from each agent

## Important Implementation Details

### JSON Parsing Robustness
All agents include fallback JSON parsing that:
1. Checks for `\`\`\`json` code blocks and extracts content
2. Falls back to `\`\`\`` code blocks
3. Treats raw response as JSON if no code blocks
4. Returns structured error response on JSON parse failure

This handles cases where Claude wraps JSON in markdown.

### Claude CLI Integration
The `BaseAgent.call_claude()` method:
- Uses subprocess to call the `claude` CLI tool
- Combines system_prompt and user_message into one prompt
- Requires `claude` to be installed and in PATH
- Uses async subprocess for non-blocking execution
- Raises RuntimeError if CLI not found or subprocess fails

### Port Assignment
- Plan Agent: 8001
- Build Agent: 8002
- Test Agent: 8003
- Hardcoded in orchestrator as `localhost:PORT`
- Can be changed in individual agent `__init__` if needed

## Skill Schema Structure

Each SkillDefinition includes:
- `id` - Unique skill identifier
- `description` - Human-readable description
- `input_schema` - JSON Schema describing expected parameters
- `output_schema` - JSON Schema describing returned data

These are exposed in the `/agent-card` response for agent discovery.

## File Organization

```
src/
├── agents/
│   ├── base.py              # BaseAgent class & A2A protocol
│   ├── plan_agent.py        # Plan Agent (create_plan skill)
│   ├── build_agent.py       # Build Agent (generate_code skill)
│   └── test_agent.py        # Test Agent (review_code skill)
├── agent_cards/
│   ├── plan_agent_card.json      # Plan agent skill definitions
│   ├── build_agent_card.json     # Build agent skill definitions
│   └── test_agent_card.json      # Test agent skill definitions
├── orchestrator.py          # Core orchestration logic (Phase 5)
└── discovery.py             # Registry discovery module

specs/
├── phase2.md         # Three Minimal Agents specification
├── phase3.md         # Registry Operations specification
├── phase4.md         # Discovery specification
└── phase5.md         # Orchestration specification

main.py              # Entry point (thin wrapper)
pyproject.toml       # Dependencies & project config
README.md            # User-facing documentation
app/                 # Generated code output folder
```

## Testing Tips

### Quick Setup & Testing Loop

```bash
# Bootstrap everything (5-10 seconds)
bash scripts/bootstrap.sh

# Test multiple runs with different requirements
uv run python main.py "Create a function that validates email addresses"
uv run python main.py "Build a TODO list manager"
uv run python main.py "Create a Fibonacci calculator"

# Check results in app/ folder
ls -la app/
cat app/review.json | jq '.quality_score, .approved, .summary'

# Tear down when done
bash scripts/kill.sh --clean-logs
```

### Individual Tests

- **Single agent test**: Run one agent manually (`uv run python -m src.agents.plan_agent`) and POST JSON-RPC messages to `localhost:PORT/execute`
- **Full pipeline**: Use `main.py` with various requirements to test end-to-end
- **Registry discovery**: Verify agent cards are in registry:
  ```bash
  oras pull localhost:5000/agents/plan:v1 -o /tmp/plan
  cat /tmp/plan/plan_agent_card.json | jq '.skills[].id'
  ```
- **Debug Claude calls**: Add logging to `src/agents/base.py::call_claude()` to see raw prompts
- **Agent availability**: GET `localhost:PORT/agent-card` to verify skill definitions:
  ```bash
  curl http://localhost:8001/agent-card | jq '.skills'
  ```
- **Check results**: Look in `app/` folder after orchestration:
  - `app/main.py` - Generated code (execute with `python app/main.py`)
  - `app/metadata.json` - Pipeline run metadata
  - `app/review.json` - Detailed code review with scores

### Troubleshooting

- **Bootstrap fails**: Check logs with `tail -f logs/*.log`
- **Agent not starting**: Ensure port (8001-8003) isn't in use: `lsof -i :8001`
- **Registry issues**: Verify with `docker ps | grep registry`
- **Clean restart**: Run `bash scripts/kill.sh --clean-logs` before bootstrap
- **Complete clean** (remove Docker image too):
  ```bash
  bash scripts/kill.sh --clean-logs
  docker rmi registry:2
  bash scripts/bootstrap.sh  # Next bootstrap will pull fresh image
  ```
