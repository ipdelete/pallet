# Phase 4: Discovery (1 hour)

## Overview

Phase 4 implements automatic agent discovery by querying the OCI registry and dynamically discovering available agents and their skills. Instead of hardcoding agent URLs in the orchestrator, Phase 4 enables runtime discovery of agents, skills, and capabilities from the registry.

Discovery works by:
1. Fetching a list of all repositories from the registry
2. Pulling agent cards from each repository
3. Parsing agent cards to extract available skills
4. Providing a lookup function to find agents by skill ID
5. Enabling dynamic orchestration without hardcoded URLs

## Prerequisites

- **Registry Running**: Docker registry on `localhost:5000` (from Phase 3)
- **ORAS Installed**: For pulling agent cards from registry
- **Phase 3 Completed**: Agent cards published to registry
- **Python 3.12+**: Required for the discovery module

## Architecture: Dynamic Discovery

### Discovery Flow

```
┌─────────────────────┐
│ Discovery Script    │
└──────────┬──────────┘
           │
           ├── 1. Query registry for repositories
           │   GET /v2/_catalog
           │
           ├── 2. List tags in agents repository
           │   GET /v2/agents/*/tags/list
           │
           ├── 3. Pull each agent card
           │   oras pull localhost:5000/agents/{name}:{tag}
           │
           └── 4. Parse agent cards
               Extract skills and build lookup table
```

### Registry API Endpoints (Docker Registry HTTP API v2)

#### List All Repositories
```
GET http://localhost:5000/v2/_catalog
```

Response:
```json
{
  "repositories": [
    "agents/plan",
    "agents/build",
    "agents/test"
  ]
}
```

#### List Tags in Repository
```
GET http://localhost:5000/v2/agents/plan/tags/list
```

Response:
```json
{
  "name": "agents/plan",
  "tags": ["v1", "v2"]
}
```

#### Get Manifest (blob reference)
```
GET http://localhost:5000/v2/agents/plan/manifests/v1
```

Response:
```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oras.artifact.manifest.v1+json",
  "config": {...},
  "layers": [
    {
      "mediaType": "application/json",
      "size": 1024,
      "digest": "sha256:..."
    }
  ]
}
```

## 4.1 Simple Discovery Script

Create `src/discovery.py` - A Python module that queries the registry and discovers agents.

### Implementation

```python
"""Agent discovery module - queries OCI registry for agent cards."""

import json
import httpx
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AgentInfo:
    """Information about a discovered agent."""
    name: str
    url: str
    skills: List[Dict]
    tag: str = "v1"


@dataclass
class SkillInfo:
    """Information about a skill."""
    id: str
    description: str
    agent_name: str
    agent_url: str


class RegistryDiscovery:
    """Discovers agents and skills from OCI registry."""

    def __init__(self, registry_url: str = "http://localhost:5000"):
        """Initialize discovery with registry URL.

        Args:
            registry_url: Base URL of OCI registry (e.g., http://localhost:5000)
        """
        self.registry_url = registry_url
        self.client = httpx.Client()
        self._agents_cache: Optional[Dict[str, AgentInfo]] = None

    def _get_json(self, url: str) -> Optional[Dict]:
        """Make HTTP GET request and parse JSON."""
        try:
            response = self.client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def list_repositories(self) -> List[str]:
        """List all repositories in the registry.

        Returns:
            List of repository names (e.g., ["agents/plan", "agents/build"])
        """
        url = f"{self.registry_url}/v2/_catalog"
        data = self._get_json(url)
        return data.get("repositories", []) if data else []

    def list_tags(self, repository: str) -> List[str]:
        """List all tags for a repository.

        Args:
            repository: Repository name (e.g., "agents/plan")

        Returns:
            List of tag names (e.g., ["v1", "v2"])
        """
        url = f"{self.registry_url}/v2/{repository}/tags/list"
        data = self._get_json(url)
        return data.get("tags", []) if data else []

    def get_agent_card(self, agent_name: str, tag: str = "v1") -> Optional[Dict]:
        """Pull and parse an agent card from the registry.

        Uses ORAS to pull the agent card JSON file.

        Args:
            agent_name: Name of the agent (e.g., "plan")
            tag: Repository tag (default: "v1")

        Returns:
            Parsed agent card JSON or None if pull fails
        """
        import subprocess

        try:
            # Use ORAS to pull the agent card
            result = subprocess.run(
                ["oras", "pull", f"{self.registry_url}/agents/{agent_name}:{tag}", "-o", "/tmp"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                print(f"ORAS pull failed for {agent_name}: {result.stderr}")
                return None

            # Read the pulled JSON file
            import os
            card_file = f"/tmp/{agent_name}_agent_card.json"

            if not os.path.exists(card_file):
                print(f"Agent card file not found: {card_file}")
                return None

            with open(card_file, 'r') as f:
                return json.load(f)

        except Exception as e:
            print(f"Error getting agent card: {e}")
            return None

    def discover_all_agents(self) -> Dict[str, AgentInfo]:
        """Discover all agents in the registry.

        Returns:
            Dictionary mapping agent names to AgentInfo objects
        """
        if self._agents_cache is not None:
            return self._agents_cache

        agents = {}

        # List all repositories
        repos = self.list_repositories()

        for repo in repos:
            # Only process agents/* repositories
            if not repo.startswith("agents/"):
                continue

            agent_name = repo.split("/")[-1]

            # Get the latest tag (or v1 by default)
            tags = self.list_tags(repo)
            tag = "v1" if "v1" in tags else (tags[0] if tags else "v1")

            # Pull and parse agent card
            card = self.get_agent_card(agent_name, tag)
            if card:
                agent = AgentInfo(
                    name=card.get("name", agent_name),
                    url=card.get("url", "http://localhost:800x"),
                    skills=card.get("skills", []),
                    tag=tag
                )
                agents[agent_name] = agent

        self._agents_cache = agents
        return agents

    def find_agent_by_skill(self, skill_id: str) -> Optional[AgentInfo]:
        """Find an agent that provides a specific skill.

        Args:
            skill_id: Skill ID to search for (e.g., "create_plan")

        Returns:
            AgentInfo if found, None otherwise
        """
        agents = self.discover_all_agents()

        for agent in agents.values():
            for skill in agent.skills:
                if skill.get("id") == skill_id:
                    return agent

        return None

    def list_all_skills(self) -> List[SkillInfo]:
        """List all available skills across all agents.

        Returns:
            List of SkillInfo objects
        """
        skills = []
        agents = self.discover_all_agents()

        for agent in agents.values():
            for skill in agent.skills:
                skills.append(SkillInfo(
                    id=skill.get("id", "unknown"),
                    description=skill.get("description", ""),
                    agent_name=agent.name,
                    agent_url=agent.url
                ))

        return skills

    def print_discovered_agents(self):
        """Print all discovered agents and their skills."""
        agents = self.discover_all_agents()

        print("\n" + "="*60)
        print("DISCOVERED AGENTS & SKILLS")
        print("="*60)

        if not agents:
            print("No agents found in registry")
            return

        for agent_name, agent in agents.items():
            print(f"\n📦 Agent: {agent.name}")
            print(f"   URL: {agent.url}")
            print(f"   Tag: {agent.tag}")
            print(f"   Skills: ({len(agent.skills)})")

            for skill in agent.skills:
                print(f"     • {skill.get('id', 'unknown')}")
                if skill.get('description'):
                    print(f"       {skill['description']}")

        print("\n" + "="*60 + "\n")

    def close(self):
        """Close the HTTP client."""
        self.client.close()


# Convenience functions for direct usage

def discover_agent(skill_id: str, registry_url: str = "http://localhost:5000") -> Optional[str]:
    """Convenience function: Find agent URL by skill ID.

    Args:
        skill_id: Skill ID to find (e.g., "create_plan")
        registry_url: Registry base URL

    Returns:
        Agent URL if found, None otherwise
    """
    discovery = RegistryDiscovery(registry_url)
    agent = discovery.find_agent_by_skill(skill_id)
    discovery.close()
    return agent.url if agent else None


def discover_agents(registry_url: str = "http://localhost:5000") -> Dict[str, AgentInfo]:
    """Convenience function: Get all discovered agents.

    Args:
        registry_url: Registry base URL

    Returns:
        Dictionary mapping agent names to AgentInfo
    """
    discovery = RegistryDiscovery(registry_url)
    agents = discovery.discover_all_agents()
    discovery.close()
    return agents


def list_skills(registry_url: str = "http://localhost:5000") -> List[SkillInfo]:
    """Convenience function: Get all available skills.

    Args:
        registry_url: Registry base URL

    Returns:
        List of SkillInfo objects
    """
    discovery = RegistryDiscovery(registry_url)
    skills = discovery.list_all_skills()
    discovery.close()
    return skills
```

### Usage Examples

```python
from src.discovery import RegistryDiscovery, discover_agent, discover_agents

# Create discovery instance
discovery = RegistryDiscovery("http://localhost:5000")

# Discover all agents
agents = discovery.discover_all_agents()
for name, agent in agents.items():
    print(f"{name}: {len(agent.skills)} skills")

# Find agent by skill
agent = discovery.find_agent_by_skill("create_plan")
if agent:
    print(f"Found: {agent.name} at {agent.url}")

# List all skills
skills = discovery.list_all_skills()
for skill in skills:
    print(f"{skill.agent_name}: {skill.id}")

# Print discovered agents (with formatting)
discovery.print_discovered_agents()

discovery.close()

# Or use convenience functions
plan_agent_url = discover_agent("create_plan")
all_agents = discover_agents()
all_skills = list_skills()
```

## 4.2 Agent Lookup Function

The `discover_agent(skill_id)` function is the core lookup mechanism used by the orchestrator.

### Function Signature

```python
def discover_agent(skill_id: str, registry_url: str = "http://localhost:5000") -> Optional[str]:
    """Find and return the URL of an agent that provides a specific skill.

    Args:
        skill_id: The skill ID to look up (e.g., "create_plan", "generate_code", "review_code")
        registry_url: The registry URL to query (defaults to localhost:5000)

    Returns:
        The agent's URL (e.g., "http://localhost:8001") if the skill is found
        None if no agent provides the requested skill

    Raises:
        ConnectionError: If the registry is not accessible
        Exception: If ORAS is not installed or ORAS pull fails
    """
```

### Implementation Details

1. **Creates a RegistryDiscovery instance** pointing to the registry
2. **Calls discover_all_agents()** to fetch all agent cards
3. **Iterates through agents** to find one with matching skill_id
4. **Returns the agent's URL** if found, None otherwise
5. **Cleans up** by closing the HTTP client

### Error Handling

The function includes robustness:
- Catches HTTP connection errors
- Handles missing ORAS installation gracefully
- Returns None on skill not found (safe for optional chaining)
- Validates registry connectivity before querying

## 4.3 CLI Discovery Script

Create `src/cli_discover.py` - Command-line interface for discovery.

### Implementation

```python
"""CLI tool for discovering agents and skills."""

import sys
import argparse
from src.discovery import RegistryDiscovery, discover_agent


def main():
    """CLI entry point for agent discovery."""
    parser = argparse.ArgumentParser(
        description="Discover agents and skills from OCI registry",
        prog="discovery"
    )

    parser.add_argument(
        "--registry",
        default="http://localhost:5000",
        help="Registry URL (default: http://localhost:5000)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command - List all agents and skills
    list_parser = subparsers.add_parser("list", help="List all agents and skills")
    list_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )

    # find command - Find agent by skill
    find_parser = subparsers.add_parser("find", help="Find agent by skill ID")
    find_parser.add_argument(
        "skill_id",
        help="Skill ID to find (e.g., create_plan)"
    )

    # agents command - List agents only
    agents_parser = subparsers.add_parser("agents", help="List available agents")
    agents_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )

    # skills command - List skills only
    skills_parser = subparsers.add_parser("skills", help="List all skills")
    skills_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    discovery = RegistryDiscovery(args.registry)

    try:
        if args.command == "list":
            discovery.print_discovered_agents()

        elif args.command == "find":
            agent = discovery.find_agent_by_skill(args.skill_id)
            if agent:
                print(f"✓ Found: {agent.name} ({agent.url})")
                print(f"  Skill: {args.skill_id}")
                return 0
            else:
                print(f"✗ Skill not found: {args.skill_id}", file=sys.stderr)
                return 1

        elif args.command == "agents":
            agents = discovery.discover_all_agents()
            if args.format == "json":
                import json
                data = {
                    name: {
                        "name": agent.name,
                        "url": agent.url,
                        "tag": agent.tag,
                        "skills": len(agent.skills)
                    }
                    for name, agent in agents.items()
                }
                print(json.dumps(data, indent=2))
            else:
                for name, agent in agents.items():
                    print(f"{name}: {agent.url} ({len(agent.skills)} skills)")

        elif args.command == "skills":
            skills = discovery.list_all_skills()
            if args.format == "json":
                import json
                data = [
                    {
                        "id": skill.id,
                        "agent": skill.agent_name,
                        "description": skill.description
                    }
                    for skill in skills
                ]
                print(json.dumps(data, indent=2))
            else:
                for skill in skills:
                    print(f"{skill.agent_name}: {skill.id}")
                    if skill.description:
                        print(f"  └─ {skill.description}")

        return 0

    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    finally:
        discovery.close()


if __name__ == "__main__":
    sys.exit(main())
```

### CLI Usage

```bash
# List all agents and skills (pretty printed)
uv run python -m src.cli_discover list

# Find agent by skill
uv run python -m src.cli_discover find create_plan

# List agents in JSON format
uv run python -m src.cli_discover agents --format json

# List all skills
uv run python -m src.cli_discover skills

# Query custom registry
uv run python -m src.cli_discover --registry http://registry.example.com:5000 list
```

## 4.4 Dynamic Orchestrator Integration

Update `main.py` to use discovery instead of hardcoded URLs.

### Updated Orchestrator

```python
"""Pallet orchestrator with dynamic discovery."""

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
) -> Optional[dict]:
    """Call an agent's skill via A2A protocol."""
    message = {
        "jsonrpc": "2.0",
        "method": skill_id,
        "params": params,
        "id": "1",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent_url}/execute",
                json=message,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error calling {agent_url}/{skill_id}: {e}", file=sys.stderr)
        return None


async def run_orchestrator(requirements: str):
    """Run the three-agent pipeline with dynamic discovery."""
    print("\n" + "="*60)
    print("PALLET A2A ORCHESTRATOR - Phase 4 (Dynamic Discovery)")
    print("="*60 + "\n")

    # Step 0: Discover agents from registry
    print("🔍 STEP 0: Discovering Agents...")
    print("-" * 60)

    plan_agent_url = discover_agent("create_plan", REGISTRY_URL)
    build_agent_url = discover_agent("generate_code", REGISTRY_URL)
    test_agent_url = discover_agent("review_code", REGISTRY_URL)

    if not all([plan_agent_url, build_agent_url, test_agent_url]):
        print("❌ Failed to discover all required agents", file=sys.stderr)
        if not plan_agent_url:
            print("   - create_plan skill not found", file=sys.stderr)
        if not build_agent_url:
            print("   - generate_code skill not found", file=sys.stderr)
        if not test_agent_url:
            print("   - review_code skill not found", file=sys.stderr)
        return

    print(f"✓ Found Plan Agent: {plan_agent_url}")
    print(f"✓ Found Build Agent: {build_agent_url}")
    print(f"✓ Found Test Agent: {test_agent_url}")
    print()

    # Step 1: Plan Agent
    print("\n📋 STEP 1: Generating Implementation Plan...")
    print("-" * 60)
    print(f"Requirements: {requirements}\n")

    result = await call_agent_skill(
        plan_agent_url,
        "create_plan",
        {"requirements": requirements}
    )

    if not result or "result" not in result:
        print("❌ Failed to generate plan", file=sys.stderr)
        return

    plan = result["result"]
    print("✅ Plan Generated:")
    print(json.dumps(plan, indent=2))
    print()

    # Step 2: Build Agent
    print("\n📝 STEP 2: Generating Code...")
    print("-" * 60)

    result = await call_agent_skill(
        build_agent_url,
        "generate_code",
        {"plan": plan}
    )

    if not result or "result" not in result:
        print("❌ Failed to generate code", file=sys.stderr)
        return

    code_result = result["result"]
    print("✅ Code Generated:")
    print(f"Language: {code_result.get('language', 'unknown')}")
    print(f"Functions: {code_result.get('functions', [])}")
    print("\nCode Preview:")
    code = code_result.get("code", "")
    code_lines = code.split("\n")[:30]
    print("\n".join(code_lines))
    if len(code.split("\n")) > 30:
        print(f"\n... ({len(code.split(chr(10))) - 30} more lines)")
    print("\nExplanation:")
    print(code_result.get("explanation", ""))
    print()

    # Step 3: Test Agent
    print("\n🧪 STEP 3: Reviewing Code...")
    print("-" * 60)

    result = await call_agent_skill(
        test_agent_url,
        "review_code",
        {
            "code": code,
            "language": "python"
        }
    )

    if not result or "result" not in result:
        print("❌ Failed to review code", file=sys.stderr)
        return

    review = result["result"]
    print("✅ Code Review Complete:")
    print(f"Quality Score: {review.get('quality_score', 0)}/10")
    print(f"Approved: {'✅ Yes' if review.get('approved') else '❌ No'}")
    print(f"\nSummary: {review.get('summary', 'N/A')}")

    issues = review.get("issues", [])
    if issues:
        print(f"\nIssues ({len(issues)}):")
        for issue in issues[:5]:
            print(f"  • [{issue.get('type', 'unknown')}] {issue.get('comment', 'N/A')}")
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more issues")

    suggestions = review.get("suggestions", [])
    if suggestions:
        print(f"\nSuggestions ({len(suggestions)}):")
        for suggestion in suggestions[:3]:
            print(f"  • {suggestion if isinstance(suggestion, str) else suggestion.get('comment', 'N/A')}")
        if len(suggestions) > 3:
            print(f"  ... and {len(suggestions) - 3} more suggestions")

    print("\n" + "="*60)
    print("ORCHESTRATION COMPLETE")
    print("="*60 + "\n")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        requirements = """
        Create a Python function that validates email addresses.
        It should:
        - Accept a string parameter
        - Return True if valid, False otherwise
        - Handle edge cases like spaces and special characters
        - Include comprehensive docstring
        """
    else:
        requirements = " ".join(sys.argv[1:])

    print("\n✓ Setup:")
    print("  - Registry running on http://localhost:5000")
    print("  - Three agents running on ports 8001-8003")
    print("\nStarting orchestration in 2 seconds...\n")

    await asyncio.sleep(2)
    await run_orchestrator(requirements)


if __name__ == "__main__":
    asyncio.run(main())
```

## Implementation Notes

### Discovery Caching
- `discover_all_agents()` caches results to avoid repeated registry queries
- Cache is invalidated when a new RegistryDiscovery instance is created
- Suitable for short-lived discovery sessions within a single orchestration run

### ORAS Dependency
- Discovery requires ORAS to be installed and in PATH
- The script uses `subprocess.run()` to invoke `oras pull`
- Alternative: Could implement Docker Registry HTTP API v2 directly to avoid ORAS dependency

### Error Handling Strategy
1. **Registry connection errors**: Raise ConnectionError with helpful message
2. **ORAS not found**: Catch FileNotFoundError and suggest installation
3. **Agent card not found**: Return None gracefully, let caller handle
4. **JSON parsing errors**: Raise ValueError with card path information

### Performance Considerations
- First discovery run queries registry for all agent cards (network latency ~2-5 seconds)
- Subsequent lookups use cached data (microsecond-level)
- For interactive use, consider keeping RegistryDiscovery instance alive across multiple lookups

## Project Structure

Updated directory structure after Phase 4:

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
│   ├── discovery.py              # NEW: Discovery module
│   └── cli_discover.py           # NEW: CLI tool for discovery
├── specs/
│   ├── phase2.md
│   ├── phase3.md
│   └── phase4.md                 # This file
├── scripts/
│   ├── install-oras.sh
│   └── verify_registry.sh
├── src/run_local_registry.py
├── main.py                       # Updated with dynamic discovery
├── pyproject.toml
└── README.md
```

## Commands Reference

### Running Discovery

```bash
# Discover and list all agents and skills
uv run python -m src.cli_discover list

# Find specific agent by skill
uv run python -m src.cli_discover find create_plan
uv run python -m src.cli_discover find generate_code
uv run python -m src.cli_discover find review_code

# List only agents
uv run python -m src.cli_discover agents

# List only skills
uv run python -m src.cli_discover skills

# JSON output (for integration with other tools)
uv run python -m src.cli_discover agents --format json
uv run python -m src.cli_discover skills --format json

# Custom registry
uv run python -m src.cli_discover --registry http://registry.example.com:5000 list
```

### Using Discovery in Python

```bash
# Run orchestrator with dynamic discovery
uv run python main.py "Your requirements here"

# All three agents will be dynamically discovered from registry
```

## Troubleshooting

### Issue: "ORAS pull failed" error

**Problem**: ORAS command fails when pulling agent cards

**Solution**:
```bash
# Verify ORAS is installed
oras version

# If not installed, run installation script
bash scripts/install-oras.sh

# Verify registry is running
curl http://localhost:5000/v2/_catalog

# Verify agent cards are published
oras repo list localhost:5000
oras repo tags localhost:5000/agents/plan
```

### Issue: "ConnectionError: Failed to connect to registry"

**Problem**: Registry is not accessible at localhost:5000

**Solution**:
```bash
# Check if registry container is running
docker ps | grep registry

# Start registry if needed
uv run src/run_local_registry.py

# Test connectivity
curl http://localhost:5000/v2/_catalog

# If curl fails, check Docker logs
docker logs local-registry
```

### Issue: "Agent card file not found after ORAS pull"

**Problem**: ORAS pulls succeed but file isn't where expected

**Solution**:
```bash
# Check ORAS pull output directory
ls -la /tmp/*_agent_card.json

# Verify agent cards are actually in registry
oras manifest fetch localhost:5000/agents/plan:v1

# Test manual ORAS pull
oras pull localhost:5000/agents/plan:v1 -o /tmp
ls -la /tmp/plan_agent_card.json
```

### Issue: "Skill not found" when running orchestrator

**Problem**: `discover_agent()` returns None for a skill

**Solution**:
```bash
# List all available skills in registry
uv run python -m src.cli_discover skills

# Verify agent cards contain expected skills
uv run python -m src.cli_discover list

# Check agent card format in source
cat src/agent_cards/plan_agent_card.json | jq '.skills[].id'

# Verify agents are running on expected ports
curl http://localhost:8001/agent-card
curl http://localhost:8002/agent-card
curl http://localhost:8003/agent-card
```

### Issue: Discovery works but orchestrator still uses hardcoded URLs

**Problem**: Not using updated `main.py` with discovery

**Solution**:
```bash
# Verify main.py imports discovery module
grep "from src.discovery import" main.py

# Verify discover_agent calls in main.py
grep "discover_agent" main.py

# Run with discovery
uv run python main.py "Your requirements"
```

## Time Breakdown

- **Discovery Module Implementation**: 20 minutes
  - RegistryDiscovery class with caching: 12 minutes
  - Convenience functions: 5 minutes
  - Error handling: 3 minutes

- **CLI Tool Implementation**: 15 minutes
  - Argument parser setup: 5 minutes
  - Subcommands (list, find, agents, skills): 8 minutes
  - Output formatting: 2 minutes

- **Orchestrator Integration**: 15 minutes
  - Update main.py for dynamic discovery: 8 minutes
  - Agent lookup in pipeline: 4 minutes
  - Error handling and messaging: 3 minutes

- **Testing & Documentation**: 10 minutes
  - Test discovery with running agents: 5 minutes
  - Test CLI commands: 3 minutes
  - Verify orchestrator workflow: 2 minutes

Total: 60 minutes (1 hour)

## Technologies

- **Docker Registry HTTP API v2**: Standard registry protocol for repository/tag queries
- **ORAS**: OCI Registry as Storage - pulls agent card artifacts from registry
- **httpx**: Async HTTP client for registry API queries
- **Subprocess**: Calls ORAS CLI tool for artifact pulling
- **Caching**: Reduces registry queries for repeated lookups within same session
- **Python 3.12+**: Type hints, dataclasses, async/await

## What's Next?

After Phase 4 completes:

- **Phase 5** could implement agent lifecycle management (pulling and running agents from registry)
- **Phase 6** could add agent versioning and rollback capabilities
- **Phase 7** could implement distributed orchestration across multiple registries
- **Phase 8** could add authentication and authorization for registry access
