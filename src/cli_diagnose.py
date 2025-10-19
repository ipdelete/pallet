"""Diagnostic CLI for Pallet framework.

Provides commands for debugging and inspecting system state.

Usage:
    python -m src.cli_diagnose health
    python -m src.cli_diagnose registry-contents
    python -m src.cli_diagnose lookup-workflow code-generation-v1 v1
    python -m src.cli_diagnose lookup-skill create_plan
"""

import argparse
import sys
import httpx

from src.logging_config import configure_module_logging
from src.discovery import RegistryDiscovery, KNOWN_AGENT_PORTS
from src.workflow_registry import pull_workflow_from_registry, list_workflows
from src.workflow_engine import load_workflow_from_yaml

logger = configure_module_logging("cli_diagnose")


def check_registry_health(registry_url: str = "http://localhost:5000") -> bool:
    """Check if registry is reachable."""
    try:
        response = httpx.get(f"{registry_url}/v2/_catalog", timeout=5.0)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Registry health check failed: {e}")
        return False


def check_agent_health(port: int, agent_name: str) -> bool:
    """Check if agent is running and responding."""
    try:
        response = httpx.get(f"http://localhost:{port}/agent-card", timeout=5.0)
        return response.status_code == 200
    except Exception as e:
        logger.debug(f"Agent {agent_name} health check failed: {e}")
        return False


def cmd_health():
    """Check system health."""
    print("\n" + "=" * 70)
    print("PALLET SYSTEM HEALTH CHECK")
    print("=" * 70)

    # Check registry
    print("\n[Registry]")
    registry_ok = check_registry_health()
    status = "✓ HEALTHY" if registry_ok else "✗ UNREACHABLE"
    print(f"  localhost:5000: {status}")

    # Check agents
    print("\n[Agents]")
    agents = {
        "plan": 8001,
        "build": 8002,
        "test": 8003,
    }

    all_agents_ok = True
    for agent_name, port in agents.items():
        agent_ok = check_agent_health(port, agent_name)
        all_agents_ok = all_agents_ok and agent_ok
        status = "✓ RESPONDING" if agent_ok else "✗ NOT RESPONDING"
        print(f"  {agent_name} (:{port}): {status}")

    # Check workflows in registry
    print("\n[Workflows in Registry]")
    try:
        workflows = list_workflows()
        if workflows:
            for wf in workflows:
                print(f"  - {wf}")
        else:
            print("  (none found)")
    except Exception as e:
        logger.debug(f"Failed to list workflows: {e}")
        print(f"  (error: {e})")

    # Summary
    print("\n" + "=" * 70)
    if registry_ok and all_agents_ok and workflows:
        print("✓ System is READY for orchestration")
        print("=" * 70 + "\n")
        return 0
    else:
        print("✗ System has issues. See details above.")
        print("=" * 70 + "\n")
        return 1


def cmd_registry_contents():
    """List registry contents (workflows and agents)."""
    print("\n" + "=" * 70)
    print("REGISTRY CONTENTS")
    print("=" * 70)

    registry_url = "http://localhost:5000"

    try:
        response = httpx.get(f"{registry_url}/v2/_catalog", timeout=5.0)
        response.raise_for_status()
        catalog = response.json()
        repos = catalog.get("repositories", [])

        print("\n[Workflows]")
        workflow_repos = [r for r in repos if r.startswith("workflows/")]
        if workflow_repos:
            for repo in workflow_repos:
                print(f"  - {repo}")
        else:
            print("  (none found)")

        print("\n[Agents]")
        agent_repos = [r for r in repos if r.startswith("agents/")]
        if agent_repos:
            for repo in agent_repos:
                print(f"  - {repo}")
        else:
            print("  (none found)")

        print(f"\n[Total Repositories: {len(repos)}]")
        print("=" * 70 + "\n")
        return 0

    except Exception as e:
        print(f"\n✗ Error querying registry: {e}")
        print("=" * 70 + "\n")
        return 1


def cmd_lookup_workflow(workflow_id: str, version: str = "v1"):
    """Debug workflow lookup."""
    print("\n" + "=" * 70)
    print(f"WORKFLOW LOOKUP: {workflow_id}:{version}")
    print("=" * 70)

    print(f"\nInput workflow_id: {workflow_id}")
    print(f"Version: {version}")

    try:
        print("\n[Attempting to pull from registry...]")
        workflow_path = pull_workflow_from_registry(workflow_id, version)

        if not workflow_path:
            print("\n✗ Failed to pull workflow from registry")
            print("=" * 70 + "\n")
            return 1

        print("✓ Successfully pulled workflow")
        print(f"  File: {workflow_path}")

        print("\n[Loading workflow definition...]")
        from pathlib import Path
        yaml_content = Path(workflow_path).read_text()
        workflow = load_workflow_from_yaml(yaml_content)

        print("✓ Successfully loaded workflow")
        print(f"  ID: {workflow.metadata.id}")
        print(f"  Name: {workflow.metadata.name}")
        print(f"  Version: {workflow.metadata.version}")
        print(f"  Description: {workflow.metadata.description}")
        print(f"  Steps: {len(workflow.steps)}")
        print(f"    {', '.join([s.id for s in workflow.steps])}")

        print("\n" + "=" * 70 + "\n")
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.error(f"Workflow lookup failed: {e}", exc_info=True)
        print("=" * 70 + "\n")
        return 1


def cmd_lookup_skill(skill_id: str):
    """Debug skill lookup."""
    print("\n" + "=" * 70)
    print(f"SKILL LOOKUP: {skill_id}")
    print("=" * 70)

    print(f"\nSearching for skill: {skill_id}")

    # Try registry discovery
    print("\n[Attempting registry discovery...]")
    try:
        discovery = RegistryDiscovery()
        agent = discovery.find_agent_by_skill(skill_id)
        discovery.close()

        if agent:
            print("✓ Found in registry")
            print(f"  Agent: {agent.name}")
            print(f"  URL: {agent.url}")
            print("=" * 70 + "\n")
            return 0
    except Exception as e:
        print(f"✗ Registry discovery failed: {e}")

    # Try fallback
    print("\n[Attempting fallback discovery...]")
    if skill_id in KNOWN_AGENT_PORTS:
        port = KNOWN_AGENT_PORTS[skill_id]
        agent_url = f"http://localhost:{port}"
        print(f"Known port: {port}")

        try:
            response = httpx.get(f"{agent_url}/agent-card", timeout=5.0)
            if response.status_code == 200:
                print("✓ Found via fallback")
                print(f"  URL: {agent_url}")
                print("=" * 70 + "\n")
                return 0
            else:
                print(f"✗ Agent returned status {response.status_code}")
        except Exception as e:
            print(f"✗ Agent not responding: {e}")
    else:
        print(f"✗ No known port mapping for {skill_id}")

    print("\n✗ Skill not found via any discovery method")
    print("=" * 70 + "\n")
    return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Pallet Diagnostics - Debug and inspect system state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.cli_diagnose health
  python -m src.cli_diagnose registry-contents
  python -m src.cli_diagnose lookup-workflow code-generation-v1 v1
  python -m src.cli_diagnose lookup-skill create_plan
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Diagnostic command")

    # Health check command
    subparsers.add_parser("health", help="Check system health and readiness")

    # Registry contents command
    subparsers.add_parser(
        "registry-contents", help="List workflows and agents in registry"
    )

    # Lookup workflow command
    lookup_wf = subparsers.add_parser("lookup-workflow", help="Debug workflow lookup")
    lookup_wf.add_argument("workflow_id", help="Workflow ID to lookup")
    lookup_wf.add_argument(
        "--version", default="v1", help="Workflow version (default: v1)"
    )

    # Lookup skill command
    lookup_skill = subparsers.add_parser("lookup-skill", help="Debug skill lookup")
    lookup_skill.add_argument("skill_id", help="Skill ID to lookup")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "health":
        return cmd_health()
    elif args.command == "registry-contents":
        return cmd_registry_contents()
    elif args.command == "lookup-workflow":
        return cmd_lookup_workflow(args.workflow_id, args.version)
    elif args.command == "lookup-skill":
        return cmd_lookup_skill(args.skill_id)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
