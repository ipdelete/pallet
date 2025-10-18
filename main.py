"""Pallet Orchestrator - Workflow-Based Orchestration.

Main entry point for workflow-based orchestration.

Usage:
  python main.py "Create a function that validates email addresses"
  python main.py --workflow code-generation-v1 "Create factorial function"
  python main.py --workflow parallel-analysis-v1 --version v1 "Analyze code"
"""

import argparse
import asyncio
import json
from pathlib import Path
from src.orchestrator import execute_workflow_by_id


def save_results(results: dict, output_dir: Path = Path("app")):
    """Save workflow results to output directory."""
    output_dir.mkdir(exist_ok=True)

    # Save metadata
    metadata = {
        "workflow_id": results.get("workflow_id"),
        "workflow_name": results.get("workflow_name"),
        "workflow_version": results.get("workflow_version"),
        "initial_input": results.get("initial_input"),
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    # Save step outputs
    step_outputs = results.get("step_outputs", {})

    # Extract plan (if exists)
    if "plan" in step_outputs:
        plan_output = step_outputs["plan"].get("outputs", {}).get("result")
        if plan_output:
            (output_dir / "plan.json").write_text(json.dumps(plan_output, indent=2))

    # Extract code (if exists)
    if "build" in step_outputs:
        build_output = step_outputs["build"].get("outputs", {}).get("result")
        if build_output and isinstance(build_output, dict):
            code = build_output.get("code", "")
            if code:
                (output_dir / "main.py").write_text(code)

    # Extract review (if exists)
    if "test" in step_outputs:
        review_output = step_outputs["test"].get("outputs", {}).get("result")
        if review_output:
            (output_dir / "review.json").write_text(json.dumps(review_output, indent=2))

    print(f"\n✓ Results saved to {output_dir}/")


async def main():
    parser = argparse.ArgumentParser(
        description="Pallet A2A Agent Framework - Workflow Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default workflow with custom requirements
  python main.py "Create a function to calculate fibonacci numbers"

  # Use specific workflow by ID
  python main.py --workflow code-generation-v1 "Create a hello world function"

  # Use default requirements with default workflow
  python main.py
        """,
    )

    parser.add_argument(
        "requirements",
        nargs="?",
        default="Create a Python function that calculates the factorial of a number",
        help="Requirements for code generation (default: factorial function)",
    )

    parser.add_argument(
        "-w",
        "--workflow",
        default="code-generation-v1",
        help="Workflow ID to execute (default: code-generation-v1)",
    )

    parser.add_argument(
        "--version", default="v1", help="Workflow version (default: v1)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Pallet A2A Agent Framework")
    print("Workflow-Based Orchestration")
    print("=" * 60)

    try:
        # Execute workflow
        results = await execute_workflow_by_id(
            workflow_id=args.workflow,
            workflow_input={"requirements": args.requirements},
            version=args.version,
        )

        # Save results
        save_results(results)

        print("\n" + "=" * 60)
        print("✓ Orchestration completed successfully")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Orchestration failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
