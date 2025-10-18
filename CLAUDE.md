# CLAUDE.md

Guidance for Claude Code working with the Pallet A2A Agent Framework repository.

## Quick Start

**Setup:**
```bash
uv sync && uv sync --extra test
npm install -g @anthropic-ai/claude-cli
export ANTHROPIC_API_KEY="your-api-key-here"
bash scripts/bootstrap.sh
```

**Run orchestrator:**
```bash
uv run python main.py "your requirements"  # Custom
uv run python main.py                      # Default
```

**Tear down:**
```bash
bash scripts/kill.sh --clean-logs  # Stop services, clean logs
docker rmi registry:2              # Remove Docker image (optional)
```

Output saved to `app/`: code, plan, review, metadata

## Project Overview

Pallet orchestrates AI agents using Google's A2A (Agent-to-Agent) protocol. Three agents form a pipeline:
- **Plan Agent** (8001) - `create_plan` skill: requirements → structured plan
- **Build Agent** (8002) - `generate_code` skill: plan → code
- **Test Agent** (8003) - `review_code` skill: code → quality review

**Stack**: FastAPI, JSON-RPC 2.0, OCI Registry (ORAS), Claude CLI subprocess

## Architecture

### Communication
- **Protocol**: JSON-RPC 2.0 over HTTP
- **Discovery**: Registry-based via agent `/agent-card` endpoint
- **Execution**: POST to `/execute` with `{"jsonrpc": "2.0", "method": "...", "params": {...}, "id": "..."}`

### Core Components

| Component | Role |
|-----------|------|
| `src/agents/base.py` | **BaseAgent** - FastAPI setup, A2A endpoints (`/agent-card`, `/execute`), Claude CLI wrapper |
| `main.py` | CLI entry point → delegates to `src/orchestrator.py` |
| `src/orchestrator.py` | Chains agents: Plan → Build → Test, dynamic discovery, saves results |
| `src/discovery.py` | Registry queries, agent card pulls, skill-based lookup |

### Agent Pattern

Each agent (plan, build, test) inherits from `BaseAgent`:
```python
async def execute_skill(self, skill_id, params):
    # 1. Validate params
    # 2. self.call_claude(system_prompt, user_msg) → JSON response
    # 3. Parse JSON (handles markdown wrapping)
    # 4. Return result
```

**Key methods**:
- `call_claude()` - Subprocess to `claude` CLI with `-p --dangerously-skip-permissions`
- `call_agent_skill()` - HTTP POST to other agents
- `parse_json_response()` - Fallback: `\`\`\`json` → `\`\`\`` → raw

### Agent Skills

| Agent | Skill | Input | Output |
|-------|-------|-------|--------|
| Plan (8001) | `create_plan` | `requirements: str` | `{title, steps, deps, time}` |
| Build (8002) | `generate_code` | `plan: object` | `{code, explanation, language, functions}` |
| Test (8003) | `review_code` | `code: str, language: str` | `{quality_score, issues, suggestions, approved, summary}` |

## Implementation Details

### JSON Response Parsing
Agents robustly parse Claude responses:
1. Extract from `\`\`\`json...` code blocks
2. Fallback to `\`\`\`...` blocks
3. Parse raw response if no blocks found
4. Return structured error on failure

### Ports
- Plan: 8001, Build: 8002, Test: 8003
- Configurable per agent `__init__`, hardcoded in orchestrator as `localhost:PORT`

### Skill Schema
Each SkillDefinition exposes via `/agent-card`:
- `id` - Unique identifier
- `description` - Human description
- `input_schema` - JSON Schema for params
- `output_schema` - JSON Schema for result

## Project Structure

```
src/agents/          Plan/Build/Test agents, BaseAgent class
src/agent_cards/     Skill definitions (JSON)
src/orchestrator.py  Plan → Build → Test pipeline
src/discovery.py     Registry queries, agent lookup
main.py              CLI entry point
pyproject.toml       Dependencies
tests/               Unit, integration, API tests
specs/               Phase 2-5 specifications
app/                 Generated outputs (code, plan, review, metadata)
```

## Testing & Debugging

### Invoke Tasks (see [tests/README.md](tests/README.md#invoke-tasks-reference) for full docs)

**Linting:**
```bash
uv run invoke lint.black        # Format
uv run invoke lint.black-check  # Check
uv run invoke lint.flake8       # Style
```

**Testing:**
```bash
uv run invoke test              # All (excludes slow/e2e)
uv run invoke test.unit         # Unit only
uv run invoke test.integration  # Integration only
uv run invoke test.api          # API only
uv run invoke test.debug        # Drop to pdb on failure
uv run invoke test.verbose      # Verbose output
uv run invoke test.coverage     # All coverage formats
```

### Debugging Approaches

| Task | Command |
|------|---------|
| Manual agent test | `uv run python -m src.agents.plan_agent` + POST JSON-RPC to `localhost:8001/execute` |
| End-to-end test | `uv run python main.py "your requirement"` |
| Check agent card | `curl http://localhost:8001/agent-card \| jq '.skills'` |
| Verify registry | `oras pull localhost:5000/agents/plan:v1 -o /tmp/plan && cat /tmp/plan/plan_agent_card.json` |
| Debug Claude calls | Add logging to `src/agents/base.py::call_claude()` |
| View outputs | `ls -la app/` then check `main.py`, `plan.json`, `review.json`, `metadata.json` |

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Bootstrap fails | `tail -f logs/*.log` |
| Port in use | `lsof -i :8001` and free ports 8001-8003 |
| Registry down | `docker ps \| grep registry` |
| Stale state | `bash scripts/kill.sh --clean-logs` before bootstrap |
| Remove Docker image | `docker rmi registry:2` |
