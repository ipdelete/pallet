"""Agent discovery module - queries OCI registry for agent cards."""

import json
import httpx
import subprocess
import os
from typing import Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass

from src.logging_config import configure_module_logging

logger = configure_module_logging("discovery")

if TYPE_CHECKING:
    from src.workflow_engine import WorkflowDefinition


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
        try:
            # Extract host:port from registry URL (remove http:// or https://)
            registry_ref = self.registry_url.replace("http://", "").replace(
                "https://", ""
            )

            # Create a temp directory for this pull to avoid conflicts
            import tempfile

            pull_dir = tempfile.mkdtemp()

            # Use ORAS to pull the agent card
            result = subprocess.run(
                [
                    "oras",
                    "pull",
                    f"{registry_ref}/agents/{agent_name}:{tag}",
                    "-o",
                    pull_dir,
                    "--allow-path-traversal",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print(f"ORAS pull failed for {agent_name}: {result.stderr}")
                return None

            # Find the JSON file (ORAS may create subdirectories)
            json_files = []
            for root, dirs, files in os.walk(pull_dir):
                for file in files:
                    if file.endswith("_agent_card.json"):
                        json_files.append(os.path.join(root, file))

            if not json_files:
                print(f"Agent card file not found for {agent_name}")
                return None

            # Read the first JSON file found
            with open(json_files[0], "r") as f:
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
                    tag=tag,
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
                skills.append(
                    SkillInfo(
                        id=skill.get("id", "unknown"),
                        description=skill.get("description", ""),
                        agent_name=agent.name,
                        agent_url=agent.url,
                    )
                )

        return skills

    def print_discovered_agents(self):
        """Print all discovered agents and their skills."""
        agents = self.discover_all_agents()

        print("\n" + "=" * 60)
        print("DISCOVERED AGENTS & SKILLS")
        print("=" * 60)

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
                if skill.get("description"):
                    print(f"       {skill['description']}")

        print("\n" + "=" * 60 + "\n")

    def close(self):
        """Close the HTTP client."""
        self.client.close()


# Convenience functions for direct usage

# Known skill to agent port mappings (for fallback discovery)
KNOWN_AGENT_PORTS = {
    "create_plan": 8001,
    "generate_code": 8002,
    "review_code": 8003,
}


def discover_agent(
    skill_id: str, registry_url: str = "http://localhost:5000"
) -> Optional[str]:
    """Convenience function: Find agent URL by skill ID.

    Tries registry first, then falls back to known hardcoded ports.

    Args:
        skill_id: Skill ID to find (e.g., "create_plan")
        registry_url: Registry base URL

    Returns:
        Agent URL if found, None otherwise
    """
    logger.debug(f"Discovering agent for skill: {skill_id}")

    # Try registry discovery first
    try:
        logger.debug(f"Attempting registry discovery at {registry_url}")
        discovery = RegistryDiscovery(registry_url)
        agent = discovery.find_agent_by_skill(skill_id)
        discovery.close()
        if agent:
            logger.info(f"Found agent for {skill_id} via registry: {agent.url}")
            return agent.url
        logger.debug(f"No agent found in registry for {skill_id}")
    except Exception as e:
        logger.warning(f"Registry discovery failed for {skill_id}: {e}", exc_info=True)

    # Fallback to known agent ports
    if skill_id in KNOWN_AGENT_PORTS:
        port = KNOWN_AGENT_PORTS[skill_id]
        agent_url = f"http://localhost:{port}"
        logger.debug(f"Trying fallback discovery for {skill_id} at {agent_url}")

        try:
            # Verify agent is running
            response = httpx.get(f"{agent_url}/agent-card", timeout=5.0)
            if response.status_code == 200:
                logger.info(
                    f"Found agent for {skill_id} via fallback port {port}: {agent_url}"
                )
                return agent_url
            logger.debug(f"Agent at {agent_url} returned status {response.status_code}")
        except httpx.RequestError as e:
            logger.debug(
                f"Fallback discovery failed for {skill_id} at {agent_url}: {e}"
            )
    else:
        logger.warning(f"No known port mapping for skill: {skill_id}")

    logger.error(f"Could not discover agent for skill: {skill_id}")
    return None


def discover_agents(
    registry_url: str = "http://localhost:5000",
) -> Dict[str, AgentInfo]:
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


# Workflow discovery functions


# Cache for discovered workflows
_workflow_cache: Dict[str, "WorkflowDefinition"] = {}


async def discover_workflow(
    workflow_id: str, version: str = "v1"
) -> Optional["WorkflowDefinition"]:
    """
    Discover and load a workflow from the registry.

    Args:
        workflow_id: Unique workflow identifier
        version: Workflow version (default: v1)

    Returns:
        WorkflowDefinition object, or None if not found

    Example:
        workflow = await discover_workflow("code-generation", "v1")
        if workflow:
            print(f"Found workflow: {workflow.metadata.name}")
    """
    from src.workflow_registry import pull_workflow_from_registry
    from src.workflow_engine import load_workflow_from_yaml

    cache_key = f"{workflow_id}:{version}"

    # Check cache first
    if cache_key in _workflow_cache:
        print(f"[Discovery] Workflow {cache_key} found in cache")
        return _workflow_cache[cache_key]

    print(f"[Discovery] Discovering workflow: {workflow_id}:{version}")

    # Pull from registry
    workflow_path = pull_workflow_from_registry(workflow_id, version)
    if not workflow_path:
        print(f"[Discovery] Workflow {workflow_id}:{version} not found in registry")
        return None

    try:
        # Load and validate
        workflow = load_workflow_from_yaml(workflow_path)
        print(f"[Discovery] Loaded workflow: {workflow.metadata.name}")

        # Cache it
        _workflow_cache[cache_key] = workflow

        return workflow

    except Exception as e:
        print(f"[Discovery] Failed to load workflow: {e}")
        return None


def clear_workflow_cache():
    """Clear the workflow cache (useful for testing)."""
    global _workflow_cache
    _workflow_cache = {}
