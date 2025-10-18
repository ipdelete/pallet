"""Pallet Orchestrator - Phase 5: Simple Linear Pipeline.

Chains three agents together: Plan → Build → Test
Uses dynamic discovery to find agents from registry.
No error handling, retries, or state management.
Saves results to app/ folder.
"""

import json
import os
from typing import Optional
from datetime import datetime

import httpx
from src.discovery import discover_agent


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
        plan_agent_url, "create_plan", {"requirements": requirements}
    )
    plan = plan_response["result"]

    print("✓ Plan generated:")
    print(json.dumps(plan, indent=2))
    print()

    # Step 2: Build Agent
    print("📝 Step 2: Build Agent - Generating Code")
    print("-" * 70)

    code_response = await call_agent_skill(
        build_agent_url, "generate_code", {"plan": plan}
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
        {"code": code, "language": code_result.get("language", "python")},
    )
    review = review_response["result"]

    print(f"Quality Score: {review.get('quality_score', 0)}/10")
    print(f"Approved: {'✓ Yes' if review.get('approved') else '✗ No'}")
    print(f"Summary: {review.get('summary', 'N/A')}")
    print()

    # Save results to app folder
    app_dir = ensure_app_folder()
    save_results(app_dir, plan, code_result, review, requirements)

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
