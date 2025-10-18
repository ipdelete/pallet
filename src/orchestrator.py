"""Pallet Orchestrator - Phase 5: Simple Linear Pipeline.

Chains three agents together: Plan → Build → Test
Uses dynamic discovery to find agents from registry.
No error handling, retries, or state management.
Saves results to app/ folder.

Phase 6: Workflow Engine Integration
Supports workflow-based orchestration while maintaining backward compatibility.
"""

import json
import os
from typing import Optional, Dict, Any
from datetime import datetime

import httpx
from src.discovery import discover_workflow
from src.workflow_engine import WorkflowEngine


REGISTRY_URL = "http://localhost:5000"


async def call_agent_skill(
    agent_url: str, skill_id: str, params: dict, timeout: float = 60.0
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
            f"{agent_url}/execute", json=message, timeout=timeout
        )
        response.raise_for_status()
        return response.json()


def ensure_app_folder():
    """Ensure the app/ folder exists."""
    app_dir = "app"
    if not os.path.exists(app_dir):
        os.makedirs(app_dir)
    return app_dir


def save_results(
    app_dir: str, plan: dict, code_result: dict, review: dict, requirements: str
):
    """Save orchestration results to app/ folder.

    Args:
        app_dir: Path to app directory
        plan: Plan output
        code_result: Code generation output
        review: Code review output
        requirements: Original requirements
    """
    # Save generated code
    code = code_result.get("code", "")
    with open(os.path.join(app_dir, "main.py"), "w") as f:
        f.write(code)

    # Save plan
    with open(os.path.join(app_dir, "plan.json"), "w") as f:
        json.dump(plan, f, indent=2)

    # Save review
    with open(os.path.join(app_dir, "review.json"), "w") as f:
        json.dump(review, f, indent=2)

    # Save metadata
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "requirements": requirements,
        "code_language": code_result.get("language", "python"),
        "code_functions": len(code_result.get("functions", [])),
        "quality_score": review.get("quality_score", 0),
        "approved": review.get("approved", False),
    }
    with open(os.path.join(app_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Results saved to {app_dir}/")
    print("  - main.py (generated code)")
    print("  - plan.json (implementation plan)")
    print("  - review.json (code review)")
    print("  - metadata.json (pipeline metadata)")


async def execute_workflow_by_id(
    workflow_id: str, workflow_input: Dict[str, Any], version: str = "v1"
) -> Dict[str, Any]:
    """
    Execute a workflow by ID from the registry.

    Args:
        workflow_id: Workflow identifier (e.g., "code-generation-v1")
        workflow_input: Input data for workflow
        version: Workflow version (default: v1)

    Returns:
        Dict containing workflow results and metadata

    Example:
        result = await execute_workflow_by_id(
            "code-generation-v1",
            {"requirements": "Create factorial function"}
        )
    """
    print(f"\n[Orchestrator] Executing workflow: {workflow_id}:{version}")

    # Discover workflow from registry
    workflow = await discover_workflow(workflow_id, version)
    if not workflow:
        raise ValueError(f"Workflow not found: {workflow_id}:{version}")

    # Execute workflow
    engine = WorkflowEngine()
    context = await engine.execute_workflow(workflow, workflow_input)

    # Build result
    result = {
        "workflow_id": workflow.metadata.id,
        "workflow_name": workflow.metadata.name,
        "workflow_version": workflow.metadata.version,
        "initial_input": workflow_input,
        "step_outputs": context.step_outputs,
        "final_output": _extract_final_output(context),
    }

    print("[Orchestrator] Workflow completed successfully")
    return result


def _extract_final_output(context) -> Dict[str, Any]:
    """Extract the final output from the last step."""
    if not context.step_outputs:
        return {}

    # Get last step's output
    last_step_id = list(context.step_outputs.keys())[-1]
    return context.step_outputs[last_step_id].get("outputs", {})


async def orchestrate(requirements: str) -> Dict[str, Any]:
    """Run the three-agent orchestration pipeline.

    Legacy orchestration function (hardcoded Plan → Build → Test).

    DEPRECATED: Use execute_workflow_by_id() with "code-generation-v1" instead.

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

    Returns:
        Dict with plan, code, and review results
    """
    print("\n[Orchestrator] Using legacy hardcoded orchestration (DEPRECATED)")
    print("[Orchestrator] Consider using workflow-based orchestration instead\n")

    # Delegate to workflow engine
    result = await execute_workflow_by_id(
        "code-generation-v1", {"requirements": requirements}
    )

    # Transform to legacy format for compatibility
    plan_out = result["step_outputs"].get("plan", {}).get("outputs", {})
    build_out = result["step_outputs"].get("build", {}).get("outputs", {})
    test_out = result["step_outputs"].get("test", {}).get("outputs", {})

    return {
        "plan": plan_out.get("result"),
        "code": build_out.get("result"),
        "review": test_out.get("result"),
        "metadata": {
            "workflow_id": result["workflow_id"],
            "workflow_version": result["workflow_version"],
        },
    }


async def main(requirements: Optional[str] = None) -> None:
    """Entry point for orchestration.

    Args:
        requirements: User requirements text. If None, uses default.
    """
    if requirements is None:
        requirements = (
            "Create a Python function that validates email addresses. "
            "It should accept a string and return True if valid, False otherwise."
        )

    await orchestrate(requirements)
