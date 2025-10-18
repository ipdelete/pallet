# Phase 2: Three Minimal Agents (3-4 hours)

## Overview

Phase 2 implements three minimal AI agents that communicate using Google's A2A protocol over FastAPI. Each agent has a single skill and uses Claude AI to process tasks. The agents are designed to work together in a pipeline: Plan Agent → Build Agent → Test Agent.

## Architecture

### Communication Protocol: Google A2A

The implementation follows [Google's A2A (Agent-to-Agent) protocol](https://github.com/a2aproject/A2A) specifications:

- **Transport**: HTTP(S) with JSON-RPC 2.0
- **Discovery**: Agent Cards expose capabilities in JSON format
- **Messages**: JSON structures containing task inputs, outputs, and artifacts

### Shared Components

#### BaseAgent Class
Located in `src/agents/base.py`, provides:
- FastAPI application setup
- A2A message handling (JSON-RPC 2.0)
- Anthropic Claude client initialization
- Standard endpoints: `/agent-card` (GET), `/execute` (POST)
- Common error handling and logging

#### Agent Card Format
Each agent exposes an Agent Card at `/agent-card`:
```json
{
  "name": "agent-name",
  "url": "http://localhost:PORT",
  "skills": [
    {
      "id": "skill_id",
      "description": "What this skill does",
      "input_schema": {...},
      "output_schema": {...}
    }
  ]
}
```

## Three Agents

### 1. Plan Agent
**Port**: 8001
**Skill**: `create_plan`

**Input**: User requirements (text)
```json
{
  "requirements": "Create a Python function that validates email addresses"
}
```

**Process**:
- Sends requirements to Claude with planning prompt
- Claude generates structured implementation plan

**Output**: Structured plan with steps, dependencies, time estimates
```json
{
  "title": "Email Validator Implementation",
  "steps": [
    {"name": "Create validation function", "time": "15 min"},
    ...
  ],
  "dependencies": [],
  "estimated_total_time": "45 minutes"
}
```

### 2. Build Agent
**Port**: 8002
**Skill**: `generate_code`

**Input**: Plan JSON (from Plan Agent)
```json
{
  "plan": {...}
}
```

**Process**:
- Sends plan to Claude with code generation prompt
- Claude generates Python code with explanations

**Output**: Python code snippet with implementation
```json
{
  "code": "def validate_email(...): ...",
  "explanation": "This function validates email formats using regex...",
  "language": "python"
}
```

### 3. Test Agent
**Port**: 8003
**Skill**: `review_code`

**Input**: Code from Build Agent
```json
{
  "code": "def validate_email(...): ...",
  "language": "python"
}
```

**Process**:
- Sends code to Claude with review prompt
- Claude analyzes for quality, bugs, best practices

**Output**: Review comments and suggestions
```json
{
  "quality_score": 8,
  "issues": [
    {
      "type": "improvement",
      "line": 3,
      "comment": "Consider adding type hints"
    }
  ],
  "suggestions": [...],
  "approved": true
}
```

## Project Structure

```
pallet/
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py              # Shared BaseAgent class
│   │   ├── plan_agent.py        # Plan Agent (port 8001)
│   │   ├── build_agent.py       # Build Agent (port 8002)
│   │   └── test_agent.py        # Test Agent (port 8003)
│   └── agent_cards/
│       ├── plan_agent_card.json
│       ├── build_agent_card.json
│       └── test_agent_card.json
├── specs/
│   └── phase2.md                # This file
├── main.py                      # Orchestrator/test script
├── pyproject.toml              # Dependencies
└── README.md                    # Project documentation
```

## Setup & Running

### Installation
```bash
uv sync
```

### Starting Agents

In separate terminals:
```bash
# Terminal 1: Plan Agent
uv run python -m src.agents.plan_agent

# Terminal 2: Build Agent
uv run python -m src.agents.build_agent

# Terminal 3: Test Agent
uv run python -m src.agents.test_agent
```

### Testing the Pipeline

Run the orchestrator:
```bash
uv run python main.py
```

This will:
1. Send requirements to Plan Agent
2. Pass the plan to Build Agent
3. Send generated code to Test Agent
4. Display the full pipeline output

## Implementation Notes

- Each agent is ~100-120 lines of Python
- BaseAgent provides common A2A handling via inheritance
- Claude API key must be in `ANTHROPIC_API_KEY` environment variable
- Agents use async/await for non-blocking I/O
- All communication is JSON-based for A2A compliance

## Technologies

- **Framework**: FastAPI (web server)
- **AI**: Anthropic Claude API
- **Protocol**: Google A2A (JSON-RPC 2.0 over HTTP)
- **Async**: asyncio, httpx
- **Python**: 3.12+
