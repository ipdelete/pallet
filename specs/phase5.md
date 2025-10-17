# Phase 5: Orchestration (1 hour)

## Overview

Phase 5 implements a minimal orchestrator script that chains the three agents together in a linear workflow. The orchestrator uses dynamic discovery (from Phase 4) to find agents in the registry, then sends requirements through the pipeline: Plan Agent → Build Agent → Test Agent.

The implementation is intentionally simple with **no error handling, no retries, and no state management**. It demonstrates the basic A2A communication pattern and validates that all three agents work together end-to-end.

## Architecture: Linear Orchestration Pipeline

### Orchestration Flow

```
┌────────────────────────────────────┐
│ Orchestrator receives requirements │
└────────────────┬───────────────────┘
                 │
                 ├─── Step 0: Discover Agents
                 │    Query registry for plan, build, test agents
                 │
                 ├─── Step 1: Send to Plan Agent
                 │    POST requirements → plan_agent_url/execute
                 │    GET: structured plan
                 │
                 ├─── Step 2: Send to Build Agent
                 │    POST plan → build_agent_url/execute
                 │    GET: generated code
                 │
                 ├─── Step 3: Send to Test Agent
                 │    POST code → test_agent_url/execute
                 │    GET: code review
                 │
                 └─── Print Results
                      Display full pipeline output
```

### Communication Pattern

Each step follows the same pattern:
1. **Prepare** message with parameters for the skill
2. **POST** to agent's `/execute` endpoint with JSON-RPC message
3. **Receive** response containing `{"jsonrpc": "2.0", "result": {...}}`
4. **Extract** result and pass to next agent

### Key Design Decision: No Error Handling

This phase intentionally omits:
- Try/catch blocks for network errors
- Retry logic for failed requests
- Validation of responses
- State persistence between steps
- Fallback behaviors

This keeps the orchestrator code minimal and clear, focusing purely on the workflow.

## Prerequisites

- **Phase 4 Completed**: Discovery module and registry population
- **Three Agents Running**: Plan (8001), Build (8002), Test (8003)
- **Registry Running**: Docker registry on localhost:5000
- **ORAS Installed**: For discovery to pull agent cards
- **Python 3.12+**: Async support, type hints

## 5.1 Simple Orchestrator Script

Create or update `orchestrator.py` (or simplify `main.py`).

### Implementation

```python
"""Pallet Orchestrator - Phase 5: Simple Linear Pipeline.

Chains three agents together: Plan → Build → Test
Uses dynamic discovery to find agents from registry.
No error handling, retries, or state management.
"""

import asyncio
import json
import sys
from typing import Optional

import httpx
from src.discovery import discover_agent


REGISTRY_URL = "http://localhost:5000"


async def call_agent_skill(
    agent_url: str,
    skill_id: str,
    params: dict,
    timeout: float = 60.0
) -> dict:
    """Call an agent's skill via JSON-RPC over HTTP.

    Args:
        agent_url: Base URL of the agent (e.g., http://localhost:8001)
        skill_id: ID of the skill to call (e.g., "create_plan")
        params: Parameters to pass to the skill
        timeout: Request timeout in seconds

    Returns:
        Raw response from agent (includes jsonrpc, result, id)
    """
    message = {
        "jsonrpc": "2.0",
        "method": skill_id,
        "params": params,
        "id": "1",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{agent_url}/execute",
            json=message,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()


async def orchestrate(requirements: str) -> None:
    """Run the three-agent orchestration pipeline.

    Linear flow:
    1. Discover Plan Agent from registry
    2. Send requirements → get plan
    3. Discover Build Agent from registry
    4. Send plan → get code
    5. Discover Test Agent from registry
    6. Send code → get review
    7. Print results

    Args:
        requirements: User requirements text
    """
    print("\n" + "=" * 70)
    print("PALLET ORCHESTRATOR - Phase 5: Simple Linear Pipeline")
    print("=" * 70 + "\n")

    # Step 0: Discover agents
    print("🔍 Step 0: Discovering Agents from Registry")
    print("-" * 70)

    plan_agent_url = discover_agent("create_plan", REGISTRY_URL)
    build_agent_url = discover_agent("generate_code", REGISTRY_URL)
    test_agent_url = discover_agent("review_code", REGISTRY_URL)

    print(f"  Plan Agent:  {plan_agent_url}")
    print(f"  Build Agent: {build_agent_url}")
    print(f"  Test Agent:  {test_agent_url}")
    print()

    # Step 1: Plan Agent
    print("📋 Step 1: Plan Agent - Creating Implementation Plan")
    print("-" * 70)
    print(f"Requirements: {requirements}\n")

    plan_response = await call_agent_skill(
        plan_agent_url,
        "create_plan",
        {"requirements": requirements}
    )
    plan = plan_response["result"]

    print("✓ Plan generated:")
    print(json.dumps(plan, indent=2))
    print()

    # Step 2: Build Agent
    print("📝 Step 2: Build Agent - Generating Code")
    print("-" * 70)

    code_response = await call_agent_skill(
        build_agent_url,
        "generate_code",
        {"plan": plan}
    )
    code_result = code_response["result"]
    code = code_result.get("code", "")

    print(f"Language: {code_result.get('language', 'unknown')}")
    print(f"Functions: {code_result.get('functions', [])}")
    print("\nCode generated:")
    code_lines = code.split("\n")[:20]
    print("\n".join(code_lines))
    if len(code.split("\n")) > 20:
        print(f"... ({len(code.split(chr(10))) - 20} more lines)")
    print()

    # Step 3: Test Agent
    print("🧪 Step 3: Test Agent - Reviewing Code")
    print("-" * 70)

    review_response = await call_agent_skill(
        test_agent_url,
        "review_code",
        {
            "code": code,
            "language": code_result.get("language", "python")
        }
    )
    review = review_response["result"]

    print(f"Quality Score: {review.get('quality_score', 0)}/10")
    print(f"Approved: {'✓ Yes' if review.get('approved') else '✗ No'}")
    print(f"Summary: {review.get('summary', 'N/A')}")
    print()

    # Print final results
    print("=" * 70)
    print("ORCHESTRATION COMPLETE")
    print("=" * 70 + "\n")

    print("SUMMARY:")
    print(f"  Plan Title: {plan.get('title', 'N/A')}")
    print(f"  Plan Steps: {len(plan.get('steps', []))}")
    print(f"  Code Language: {code_result.get('language', 'unknown')}")
    print(f"  Code Functions: {len(code_result.get('functions', []))}")
    print(f"  Review Score: {review.get('quality_score', 0)}/10")
    print(f"  Code Approved: {'✓ Yes' if review.get('approved') else '✗ No'}")
    print()


async def main():
    """Entry point for the orchestrator."""
    if len(sys.argv) < 2:
        requirements = (
            "Create a Python function that validates email addresses. "
            "It should accept a string and return True if valid, False otherwise."
        )
    else:
        requirements = " ".join(sys.argv[1:])

    await orchestrate(requirements)


if __name__ == "__main__":
    asyncio.run(main())
```

### Code Structure

The orchestrator contains:

1. **`call_agent_skill()`** - Generic function to invoke any agent's skill
   - Constructs JSON-RPC message
   - Makes HTTP POST request
   - Returns parsed response

2. **`orchestrate()`** - Main orchestration logic
   - Step 0: Discover agents from registry
   - Steps 1-3: Call each agent in sequence
   - Pass output from each step to the next
   - Print results at each stage

3. **`main()`** - Entry point
   - Accepts requirements as command-line argument
   - Provides default requirements if none given
   - Calls orchestrate() with requirements

### No Error Handling Rationale

This implementation **intentionally lacks**:

- **Network error handling**: If any request fails, the program crashes
- **JSON parsing**: Assumes all responses are valid JSON-RPC
- **Validation**: Doesn't verify agent discovery succeeded or response format
- **Retries**: No automatic retry logic for transient failures
- **Timeouts**: Basic timeout only, no handling when exceeded
- **State persistence**: No saving of intermediate results

This is intentional to keep the phase simple and focused on demonstrating the workflow.

## 5.2 Running the Orchestrator

### Prerequisites

Ensure all three agents and registry are running:

```bash
# Terminal 1: Registry
docker run -d -p 5000:5000 --name registry registry:2

# Terminal 2: Plan Agent (port 8001)
uv run python -m src.agents.plan_agent

# Terminal 3: Build Agent (port 8002)
uv run python -m src.agents.build_agent

# Terminal 4: Test Agent (port 8003)
uv run python -m src.agents.test_agent
```

### Using the Orchestrator

In a fifth terminal, run the orchestrator:

```bash
# With default requirements
uv run python orchestrator.py

# With custom requirements
uv run python orchestrator.py "Create a function to parse CSV files"

# Multiple word requirements
uv run python orchestrator.py "Build a REST API endpoint" "that validates user input" "and returns JSON responses"
```

### Example Output

```
======================================================================
PALLET ORCHESTRATOR - Phase 5: Simple Linear Pipeline
======================================================================

🔍 Step 0: Discovering Agents from Registry
----------------------------------------------------------------------
  Plan Agent:  http://localhost:8001
  Build Agent: http://localhost:8002
  Test Agent:  http://localhost:8003

📋 Step 1: Plan Agent - Creating Implementation Plan
----------------------------------------------------------------------
Requirements: Create a Python function that validates email addresses...

✓ Plan generated:
{
  "title": "Email Validation Function Implementation",
  "steps": [
    {
      "name": "Define email validation regex pattern",
      "time": "5 min"
    },
    {
      "name": "Create validate_email function",
      "time": "10 min"
    },
    {
      "name": "Add error handling and edge cases",
      "time": "15 min"
    }
  ],
  "dependencies": [],
  "estimated_total_time": "30 minutes"
}

📝 Step 2: Build Agent - Generating Code
----------------------------------------------------------------------
Language: python
Functions: ["validate_email"]

Code generated:
import re

def validate_email(email: str) -> bool:
    """Validate email address format.

    Args:
        email: Email address string to validate

    Returns:
        True if valid email format, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
... (5 more lines)

🧪 Step 3: Test Agent - Reviewing Code
----------------------------------------------------------------------
Quality Score: 8/10
Approved: ✓ Yes
Summary: Code is well-structured with good documentation and proper input validation...

======================================================================
ORCHESTRATION COMPLETE
======================================================================

SUMMARY:
  Plan Title: Email Validation Function Implementation
  Plan Steps: 3
  Code Language: python
  Code Functions: 1
  Review Score: 8/10
  Code Approved: ✓ Yes

```

## Project Structure

Updated after Phase 5:

```
pallet/
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── plan_agent.py
│   │   ├── build_agent.py
│   │   └── test_agent.py
│   ├── agent_cards/
│   │   ├── plan_agent_card.json
│   │   ├── build_agent_card.json
│   │   └── test_agent_card.json
│   ├── discovery.py
│   └── cli_discover.py
├── specs/
│   ├── phase2.md
│   ├── phase3.md
│   ├── phase4.md
│   └── phase5.md                # This file
├── scripts/
│   ├── install-oras.sh
│   └── verify_registry.sh
├── orchestrator.py              # NEW: Simple orchestrator (this phase)
├── main.py                      # (May be updated to use orchestrator)
├── pyproject.toml
└── README.md
```

## Workflow Summary

| Step | Agent | Input | Output | Status |
|------|-------|-------|--------|--------|
| 0 | Registry | skill IDs | Agent URLs | Discover |
| 1 | Plan | Requirements | Structured Plan | ✓ Complete |
| 2 | Build | Plan JSON | Code + Explanation | ✓ Complete |
| 3 | Test | Code + Language | Review + Score | ✓ Complete |
| - | Orchestrator | - | Summary Output | ✓ Display |

## Implementation Notes

### Discovery Call Format

Each discovery call queries the registry:
```python
discover_agent("create_plan", REGISTRY_URL)  # Returns: http://localhost:8001
discover_agent("generate_code", REGISTRY_URL)  # Returns: http://localhost:8002
discover_agent("review_code", REGISTRY_URL)  # Returns: http://localhost:8003
```

### JSON-RPC Message Format

All agent calls use JSON-RPC 2.0:
```json
{
  "jsonrpc": "2.0",
  "method": "skill_id",
  "params": {...},
  "id": "1"
}
```

Agent responds with:
```json
{
  "jsonrpc": "2.0",
  "result": {...},
  "id": "1"
}
```

### Data Flow Through Pipeline

```
Requirements (string)
    ↓
[Plan Agent] → Plan (JSON object)
    ↓
[Build Agent] → Code (string) + Language (string) + Functions (array)
    ↓
[Test Agent] → Review (JSON object with quality_score, issues, suggestions)
    ↓
Results → Print to stdout
```

## Time Breakdown

- **Orchestrator Implementation**: 20 minutes
  - Main `orchestrate()` function: 12 minutes
  - `call_agent_skill()` helper: 5 minutes
  - Output formatting: 3 minutes

- **Testing & Documentation**: 40 minutes
  - Start all agents: 5 minutes
  - Test discovery: 3 minutes
  - Run orchestrator with various inputs: 10 minutes
  - Verify each step completes: 7 minutes
  - Document workflow: 15 minutes

Total: 60 minutes (1 hour)

## Technologies

- **httpx**: Async HTTP client for agent communication
- **asyncio**: Async/await for concurrent operations
- **JSON-RPC 2.0**: Standard message protocol for agent calls
- **Discovery Module**: From Phase 4 (ORAS + Registry API)
- **Python 3.12+**: Type hints, async support

## What's Next?

After Phase 5 completes:

- **Phase 6** could add error handling and retry logic for robustness
- **Phase 7** could add state management (save intermediate results, resume from failures)
- **Phase 8** could add support for parallel agent execution (map/reduce patterns)
- **Phase 9** could add support for custom agent chains and branching logic
- **Phase 10** could implement a full workflow engine with conditional logic and loops

## Testing Checklist

- [ ] Registry running on localhost:5000
- [ ] All three agents started on ports 8001-8003
- [ ] Discovery successfully finds all three agents
- [ ] Plan Agent receives requirements and returns plan
- [ ] Build Agent receives plan and returns code
- [ ] Test Agent receives code and returns review
- [ ] Orchestrator completes full pipeline without errors
- [ ] Output displays summary with plan, code, and review information
