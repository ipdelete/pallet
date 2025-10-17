# Registry and Discovery Documentation

> Complete guide to implementing dynamic agent discovery using OCI registries

## Table of Contents
1. [Overview](#overview)
2. [Why Registry-Based Discovery?](#why-registry-based-discovery)
3. [OCI Registry Fundamentals](#oci-registry-fundamentals)
4. [Setting Up a Registry](#setting-up-a-registry)
5. [Publishing Agent Cards](#publishing-agent-cards)
6. [Discovery Implementation](#discovery-implementation)
7. [Advanced Registry Patterns](#advanced-registry-patterns)
8. [Multi-Registry Federation](#multi-registry-federation)
9. [Security and Access Control](#security-and-access-control)
10. [Troubleshooting](#troubleshooting)

## Overview

Registry-based discovery enables agents to find each other dynamically based on capabilities rather than hardcoded addresses. This is the foundation of scalable, pluggable agent systems.

### The Discovery Flow

```
1. Agent starts → Publishes agent card to registry
2. Orchestrator needs skill X → Queries registry for skill X
3. Registry returns agent URL → Orchestrator calls agent
4. Agent executes skill → Returns result to orchestrator
```

## Why Registry-Based Discovery?

### Traditional Approach (Problems)

```python
# ❌ Hardcoded URLs - brittle and inflexible
AGENT_URLS = {
    "translator": "http://10.0.1.5:8001",
    "analyzer": "http://10.0.1.6:8002",
    "generator": "http://10.0.1.7:8003"
}

# What happens when:
# - IP addresses change?
# - Agents move to different hosts?
# - You want to add new agents?
# - You need load balancing?
```

### Registry Approach (Solution)

```python
# ✅ Dynamic discovery - flexible and scalable
def get_agent_for_skill(skill_id):
    return registry.discover(skill_id)

# Automatically handles:
# - Service location changes
# - Adding/removing agents
# - Load balancing
# - Version management
```

## OCI Registry Fundamentals

### What is OCI?

OCI (Open Container Initiative) defines standards for container formats and runtime. OCI registries can store any artifact type, not just container images.

### Key Concepts

- **Repository**: Collection of related artifacts (e.g., `agents/translator`)
- **Tag**: Version identifier (e.g., `v1`, `latest`, `stable`)
- **Manifest**: Metadata describing the artifact
- **Artifact**: The actual content (agent cards in our case)

### Registry API

OCI registries expose a standard HTTP API:

```bash
# List repositories
GET /v2/_catalog

# List tags for a repository
GET /v2/{name}/tags/list

# Get manifest
GET /v2/{name}/manifests/{reference}

# Get blob (artifact content)
GET /v2/{name}/blobs/{digest}
```

## Setting Up a Registry

### Option 1: Docker Registry (Recommended for Development)

```bash
# Start a local registry
docker run -d \
  -p 5000:5000 \
  --restart=always \
  --name registry \
  registry:2

# Verify it's running
curl http://localhost:5000/v2/_catalog
```

### Option 2: Cloud Registries

#### AWS ECR
```bash
# Create repository
aws ecr create-repository --repository-name agents/translator

# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URL

# Push artifact
oras push $ECR_URL/agents/translator:v1 agent_card.json
```

#### Google Artifact Registry
```bash
# Create repository
gcloud artifacts repositories create agents \
  --repository-format=docker \
  --location=us-central1

# Configure authentication
gcloud auth configure-docker us-central1-docker.pkg.dev

# Push artifact
oras push us-central1-docker.pkg.dev/$PROJECT/agents/translator:v1 agent_card.json
```

#### Azure Container Registry
```bash
# Create registry
az acr create --resource-group mygroup --name myregistry --sku Basic

# Login
az acr login --name myregistry

# Push artifact
oras push myregistry.azurecr.io/agents/translator:v1 agent_card.json
```

### Option 3: Self-Hosted Solutions

#### Harbor
```yaml
# docker-compose.yml for Harbor
version: '2'
services:
  registry:
    image: goharbor/harbor-registry:v2.8.0
    ports:
      - 5000:5000
  core:
    image: goharbor/harbor-core:v2.8.0
    environment:
      - REGISTRY_URL=http://registry:5000
  portal:
    image: goharbor/harbor-portal:v2.8.0
    ports:
      - 80:8080
```

#### Zot
```bash
# Lightweight OCI registry
docker run -d -p 5000:5000 \
  -v $(pwd)/data:/var/lib/registry \
  ghcr.io/project-zot/zot:latest
```

## Publishing Agent Cards

### Installing ORAS CLI

```bash
# macOS
brew install oras

# Linux
VERSION="1.1.0"
curl -LO "https://github.com/oras-project/oras/releases/download/v${VERSION}/oras_${VERSION}_linux_amd64.tar.gz"
tar -xzf oras_${VERSION}_linux_amd64.tar.gz
sudo mv oras /usr/local/bin/

# Windows
# Download from GitHub releases

# Verify installation
oras version
```

### Creating Agent Cards

```json
{
  "name": "translation-agent",
  "url": "http://translation-service:8001",
  "version": "1.2.0",
  "description": "Multi-language translation service",
  "maintainer": "team@example.com",
  "skills": [
    {
      "id": "translate_text",
      "description": "Translates text between languages",
      "input_schema": {
        "type": "object",
        "properties": {
          "text": {"type": "string"},
          "source_lang": {"type": "string"},
          "target_lang": {"type": "string"}
        },
        "required": ["text", "target_lang"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "translated_text": {"type": "string"},
          "confidence": {"type": "number"}
        }
      }
    }
  ],
  "metadata": {
    "labels": {
      "domain": "nlp",
      "tier": "production"
    },
    "annotations": {
      "documentation": "https://docs.example.com/translation",
      "sla": "99.9%"
    }
  }
}
```

### Publishing to Registry

```bash
# Basic push
oras push localhost:5000/agents/translator:v1 \
  agent_card.json:application/json

# With annotations
oras push localhost:5000/agents/translator:v1 \
  --artifact-type application/vnd.a2a.agent.card \
  --annotation "version=1.2.0" \
  --annotation "skills=translate_text,detect_language" \
  agent_card.json:application/json

# With multiple files
oras push localhost:5000/agents/translator:v1 \
  agent_card.json:application/json \
  README.md:text/markdown \
  schema.json:application/json
```

### Automated Publishing

```python
#!/usr/bin/env python3
"""
Automated agent card publisher
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class AgentPublisher:
    """Publishes agent cards to OCI registry"""

    def __init__(self, registry_url: str = "localhost:5000"):
        self.registry_url = registry_url

    def publish_agent_card(
        self,
        agent_name: str,
        agent_card: Dict[str, Any],
        version: str = "latest",
        annotations: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Publish an agent card to the registry.

        Args:
            agent_name: Name of the agent (e.g., "translator")
            agent_card: Agent card dictionary
            version: Version tag (default: "latest")
            annotations: Optional OCI annotations

        Returns:
            True if successful, False otherwise
        """
        # Save agent card to temp file
        temp_file = Path(f"/tmp/{agent_name}_card.json")
        with open(temp_file, "w") as f:
            json.dump(agent_card, f, indent=2)

        # Build ORAS command
        repository = f"{self.registry_url}/agents/{agent_name}:{version}"
        cmd = [
            "oras", "push", repository,
            "--artifact-type", "application/vnd.a2a.agent.card"
        ]

        # Add annotations
        if annotations:
            for key, value in annotations.items():
                cmd.extend(["--annotation", f"{key}={value}"])

        # Add the agent card file
        cmd.append(f"{temp_file}:application/json")

        # Execute push
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Published {agent_name}:{version} to {self.registry_url}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to publish {agent_name}: {e.stderr}")
            return False
        finally:
            # Clean up temp file
            temp_file.unlink(missing_ok=True)

    def publish_from_file(self, card_file: str, version: str = "latest") -> bool:
        """Publish an agent card from a JSON file"""
        path = Path(card_file)
        if not path.exists():
            print(f"❌ File not found: {card_file}")
            return False

        with open(path, "r") as f:
            agent_card = json.load(f)

        agent_name = agent_card.get("name", path.stem)

        # Extract skills for annotations
        skills = [s["id"] for s in agent_card.get("skills", [])]
        annotations = {
            "skills": ",".join(skills),
            "version": agent_card.get("version", "1.0.0")
        }

        return self.publish_agent_card(agent_name, agent_card, version, annotations)

    def bulk_publish(self, directory: str, version: str = "latest") -> Dict[str, bool]:
        """Publish all agent cards in a directory"""
        results = {}
        card_dir = Path(directory)

        if not card_dir.exists():
            print(f"❌ Directory not found: {directory}")
            return results

        for card_file in card_dir.glob("*_card.json"):
            success = self.publish_from_file(str(card_file), version)
            results[card_file.stem] = success

        return results


# CLI Usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Publish agent cards to registry")
    parser.add_argument("--registry", default="localhost:5000", help="Registry URL")
    parser.add_argument("--version", default="latest", help="Version tag")
    parser.add_argument("--file", help="Single agent card file to publish")
    parser.add_argument("--dir", help="Directory containing agent cards")

    args = parser.parse_args()

    publisher = AgentPublisher(args.registry)

    if args.file:
        success = publisher.publish_from_file(args.file, args.version)
        sys.exit(0 if success else 1)
    elif args.dir:
        results = publisher.bulk_publish(args.dir, args.version)
        print(f"\nPublished {sum(results.values())}/{len(results)} agents")
        sys.exit(0 if all(results.values()) else 1)
    else:
        print("Specify --file or --dir to publish agent cards")
        sys.exit(1)
```

## Discovery Implementation

### Basic Discovery Client

```python
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
import httpx

class RegistryDiscovery:
    """
    Discovers agents from an OCI registry.
    """

    def __init__(self, registry_url: str = "localhost:5000"):
        self.registry_url = registry_url
        self._cache = {}  # Cache discovered agents

    def discover_agent(self, skill_id: str) -> Optional[str]:
        """
        Find an agent that provides the specified skill.

        Args:
            skill_id: The skill to search for

        Returns:
            Agent URL if found, None otherwise
        """
        # Check cache first
        if skill_id in self._cache:
            return self._cache[skill_id]

        # Get all repositories
        repositories = self._list_repositories()

        for repo in repositories:
            if not repo.startswith("agents/"):
                continue

            # Pull and check agent card
            agent_card = self._pull_agent_card(repo)
            if not agent_card:
                continue

            # Check if agent has the skill
            for skill in agent_card.get("skills", []):
                if skill["id"] == skill_id:
                    agent_url = agent_card["url"]
                    self._cache[skill_id] = agent_url
                    return agent_url

        return None

    def _list_repositories(self) -> List[str]:
        """List all repositories in the registry"""
        try:
            response = httpx.get(f"http://{self.registry_url}/v2/_catalog")
            response.raise_for_status()
            data = response.json()
            return data.get("repositories", [])
        except Exception as e:
            print(f"Failed to list repositories: {e}")
            return []

    def _pull_agent_card(self, repository: str, tag: str = "latest") -> Optional[Dict[str, Any]]:
        """Pull and parse an agent card from the registry"""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Use ORAS to pull the artifact
                cmd = [
                    "oras", "pull",
                    f"{self.registry_url}/{repository}:{tag}",
                    "-o", tmpdir
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                # Find and read the JSON file
                for file in Path(tmpdir).glob("*.json"):
                    with open(file, "r") as f:
                        return json.load(f)

            except subprocess.CalledProcessError as e:
                print(f"Failed to pull {repository}: {e.stderr}")

        return None

    def list_all_skills(self) -> Dict[str, List[Dict[str, str]]]:
        """
        List all available skills across all agents.

        Returns:
            Dictionary mapping skill IDs to agent information
        """
        skills = {}
        repositories = self._list_repositories()

        for repo in repositories:
            if not repo.startswith("agents/"):
                continue

            agent_card = self._pull_agent_card(repo)
            if not agent_card:
                continue

            for skill in agent_card.get("skills", []):
                skill_id = skill["id"]
                if skill_id not in skills:
                    skills[skill_id] = []

                skills[skill_id].append({
                    "agent": agent_card["name"],
                    "url": agent_card["url"],
                    "description": skill.get("description", "")
                })

        return skills

    def get_agents_by_label(self, label_key: str, label_value: str) -> List[Dict[str, Any]]:
        """Find agents with specific labels"""
        matching_agents = []
        repositories = self._list_repositories()

        for repo in repositories:
            if not repo.startswith("agents/"):
                continue

            agent_card = self._pull_agent_card(repo)
            if not agent_card:
                continue

            # Check labels
            labels = agent_card.get("metadata", {}).get("labels", {})
            if labels.get(label_key) == label_value:
                matching_agents.append(agent_card)

        return matching_agents
```

### Advanced Discovery with Caching

```python
import time
from functools import lru_cache
from typing import Optional, Dict, Any, List
import threading

class CachedDiscovery(RegistryDiscovery):
    """
    Discovery client with intelligent caching and refresh.
    """

    def __init__(
        self,
        registry_url: str = "localhost:5000",
        cache_ttl: int = 300,  # 5 minutes
        refresh_interval: int = 60  # 1 minute
    ):
        super().__init__(registry_url)
        self.cache_ttl = cache_ttl
        self.refresh_interval = refresh_interval
        self._skill_cache = {}
        self._cache_timestamps = {}
        self._lock = threading.Lock()

        # Start background refresh thread
        self._stop_refresh = threading.Event()
        self._refresh_thread = threading.Thread(target=self._background_refresh)
        self._refresh_thread.daemon = True
        self._refresh_thread.start()

    def discover_agent(self, skill_id: str) -> Optional[str]:
        """Discover agent with caching"""
        with self._lock:
            # Check cache validity
            if skill_id in self._skill_cache:
                timestamp = self._cache_timestamps.get(skill_id, 0)
                if time.time() - timestamp < self.cache_ttl:
                    return self._skill_cache[skill_id]

        # Cache miss or expired - fetch from registry
        agent_url = super().discover_agent(skill_id)

        with self._lock:
            self._skill_cache[skill_id] = agent_url
            self._cache_timestamps[skill_id] = time.time()

        return agent_url

    def _background_refresh(self):
        """Periodically refresh the cache"""
        while not self._stop_refresh.is_set():
            time.sleep(self.refresh_interval)

            try:
                # Get all skills from registry
                all_skills = self.list_all_skills()

                with self._lock:
                    # Update cache
                    for skill_id, agents in all_skills.items():
                        if agents:
                            self._skill_cache[skill_id] = agents[0]["url"]
                            self._cache_timestamps[skill_id] = time.time()

            except Exception as e:
                print(f"Background refresh failed: {e}")

    def stop(self):
        """Stop the background refresh thread"""
        self._stop_refresh.set()
        self._refresh_thread.join()
```

### Discovery with Load Balancing

```python
import random
from typing import List, Optional, Dict, Any

class LoadBalancedDiscovery(RegistryDiscovery):
    """
    Discovery with load balancing across multiple agents.
    """

    def __init__(
        self,
        registry_url: str = "localhost:5000",
        strategy: str = "round-robin"  # or "random", "least-connections"
    ):
        super().__init__(registry_url)
        self.strategy = strategy
        self._round_robin_indexes = {}
        self._connection_counts = {}

    def discover_agents(self, skill_id: str) -> List[str]:
        """Find ALL agents that provide a skill"""
        agents = []
        repositories = self._list_repositories()

        for repo in repositories:
            if not repo.startswith("agents/"):
                continue

            agent_card = self._pull_agent_card(repo)
            if not agent_card:
                continue

            for skill in agent_card.get("skills", []):
                if skill["id"] == skill_id:
                    agents.append(agent_card["url"])
                    break

        return agents

    def select_agent(self, skill_id: str) -> Optional[str]:
        """Select an agent using load balancing strategy"""
        agents = self.discover_agents(skill_id)
        if not agents:
            return None

        if self.strategy == "random":
            return random.choice(agents)

        elif self.strategy == "round-robin":
            if skill_id not in self._round_robin_indexes:
                self._round_robin_indexes[skill_id] = 0

            index = self._round_robin_indexes[skill_id]
            agent = agents[index % len(agents)]
            self._round_robin_indexes[skill_id] = index + 1
            return agent

        elif self.strategy == "least-connections":
            # Track connection counts
            min_connections = float('inf')
            selected_agent = agents[0]

            for agent in agents:
                connections = self._connection_counts.get(agent, 0)
                if connections < min_connections:
                    min_connections = connections
                    selected_agent = agent

            # Increment connection count
            self._connection_counts[selected_agent] = \
                self._connection_counts.get(selected_agent, 0) + 1

            return selected_agent

        return agents[0]  # Default to first agent

    def release_connection(self, agent_url: str):
        """Decrement connection count after request completes"""
        if self.strategy == "least-connections":
            if agent_url in self._connection_counts:
                self._connection_counts[agent_url] -= 1
```

## Advanced Registry Patterns

### Version Management

```python
class VersionedDiscovery(RegistryDiscovery):
    """
    Discovery with semantic versioning support.
    """

    def discover_agent_version(
        self,
        skill_id: str,
        version_constraint: str = "latest"
    ) -> Optional[str]:
        """
        Find agent matching version constraint.

        Args:
            skill_id: Required skill
            version_constraint: Version spec (e.g., "~1.2.0", ">=2.0.0", "latest")
        """
        from packaging import version
        from packaging.specifiers import SpecifierSet

        best_match = None
        best_version = None

        repositories = self._list_repositories()

        for repo in repositories:
            if not repo.startswith("agents/"):
                continue

            # Get all tags for this repository
            tags = self._list_tags(repo)

            for tag in tags:
                if version_constraint == "latest" and tag == "latest":
                    agent_card = self._pull_agent_card(repo, tag)
                    if self._has_skill(agent_card, skill_id):
                        return agent_card["url"]

                # Parse semantic version tags
                try:
                    tag_version = version.parse(tag.lstrip("v"))

                    # Check version constraint
                    if version_constraint != "latest":
                        spec = SpecifierSet(version_constraint)
                        if tag_version not in spec:
                            continue

                    agent_card = self._pull_agent_card(repo, tag)
                    if self._has_skill(agent_card, skill_id):
                        if best_version is None or tag_version > best_version:
                            best_match = agent_card["url"]
                            best_version = tag_version

                except version.InvalidVersion:
                    continue

        return best_match

    def _list_tags(self, repository: str) -> List[str]:
        """List all tags for a repository"""
        try:
            response = httpx.get(f"http://{self.registry_url}/v2/{repository}/tags/list")
            response.raise_for_status()
            data = response.json()
            return data.get("tags", [])
        except Exception:
            return []

    def _has_skill(self, agent_card: Optional[Dict], skill_id: str) -> bool:
        """Check if agent card contains a skill"""
        if not agent_card:
            return False
        return any(s["id"] == skill_id for s in agent_card.get("skills", []))
```

### Health-Aware Discovery

```python
import asyncio
import httpx
from typing import Optional, Dict, Any

class HealthAwareDiscovery(RegistryDiscovery):
    """
    Discovery that checks agent health before returning.
    """

    def __init__(
        self,
        registry_url: str = "localhost:5000",
        health_check_timeout: float = 5.0
    ):
        super().__init__(registry_url)
        self.health_check_timeout = health_check_timeout
        self._health_cache = {}
        self._health_cache_ttl = 30  # seconds

    async def discover_healthy_agent(self, skill_id: str) -> Optional[str]:
        """Find a healthy agent with the required skill"""
        agents = self.discover_agents(skill_id)

        for agent_url in agents:
            if await self._is_healthy(agent_url):
                return agent_url

        return None

    async def _is_healthy(self, agent_url: str) -> bool:
        """Check if an agent is healthy"""
        # Check cache
        cache_key = agent_url
        if cache_key in self._health_cache:
            cached_time, is_healthy = self._health_cache[cache_key]
            if time.time() - cached_time < self._health_cache_ttl:
                return is_healthy

        # Perform health check
        try:
            async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
                response = await client.get(f"{agent_url}/health")
                is_healthy = response.status_code == 200

                # Cache result
                self._health_cache[cache_key] = (time.time(), is_healthy)
                return is_healthy

        except Exception:
            # Cache negative result
            self._health_cache[cache_key] = (time.time(), False)
            return False
```

## Multi-Registry Federation

### Federated Discovery

```python
class FederatedDiscovery:
    """
    Discover agents across multiple registries.
    """

    def __init__(self, registries: List[str]):
        self.registries = [RegistryDiscovery(r) for r in registries]

    def discover_agent(self, skill_id: str) -> Optional[str]:
        """Search all registries for an agent"""
        for registry in self.registries:
            agent_url = registry.discover_agent(skill_id)
            if agent_url:
                return agent_url
        return None

    def discover_all_agents(self, skill_id: str) -> List[str]:
        """Find all agents across all registries"""
        all_agents = []
        for registry in self.registries:
            agents = registry.discover_agents(skill_id)
            all_agents.extend(agents)
        return all_agents
```

### Registry Mirroring

```python
class RegistryMirror:
    """
    Mirror agent cards between registries.
    """

    def __init__(self, source_registry: str, target_registry: str):
        self.source = source_registry
        self.target = target_registry

    def mirror_repository(self, repository: str, tag: str = "latest") -> bool:
        """Mirror a repository from source to target"""
        try:
            # Pull from source
            cmd = [
                "oras", "copy",
                f"{self.source}/{repository}:{tag}",
                f"{self.target}/{repository}:{tag}"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def sync_all(self) -> Dict[str, bool]:
        """Sync all agent repositories"""
        source_discovery = RegistryDiscovery(self.source)
        repositories = source_discovery._list_repositories()

        results = {}
        for repo in repositories:
            if repo.startswith("agents/"):
                success = self.mirror_repository(repo)
                results[repo] = success

        return results
```

## Security and Access Control

### Authenticated Registry Access

```python
import base64

class SecureDiscovery(RegistryDiscovery):
    """
    Discovery with authentication support.
    """

    def __init__(
        self,
        registry_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None
    ):
        super().__init__(registry_url)
        self.auth_headers = {}

        if username and password:
            # Basic auth
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            self.auth_headers["Authorization"] = f"Basic {credentials}"
        elif token:
            # Bearer token
            self.auth_headers["Authorization"] = f"Bearer {token}"

    def _list_repositories(self) -> List[str]:
        """List repositories with authentication"""
        try:
            response = httpx.get(
                f"http://{self.registry_url}/v2/_catalog",
                headers=self.auth_headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get("repositories", [])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("Authentication failed")
            return []
        except Exception as e:
            print(f"Failed to list repositories: {e}")
            return []

    def _pull_agent_card(self, repository: str, tag: str = "latest") -> Optional[Dict[str, Any]]:
        """Pull with authentication"""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Login to registry first if credentials provided
                if "Authorization" in self.auth_headers:
                    # For ORAS, you typically need to login first
                    # This is registry-specific
                    pass

                cmd = [
                    "oras", "pull",
                    f"{self.registry_url}/{repository}:{tag}",
                    "-o", tmpdir
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                for file in Path(tmpdir).glob("*.json"):
                    with open(file, "r") as f:
                        return json.load(f)

            except subprocess.CalledProcessError:
                return None

        return None
```

### Registry Access Policies

```yaml
# Example: Harbor robot account with limited access
apiVersion: v1
kind: ConfigMap
metadata:
  name: registry-robot-account
data:
  username: "robot$discovery"
  permissions: |
    - resource: /project/agents/repository
      action: pull
    - resource: /project/agents/artifact
      action: read
```

## Troubleshooting

### Common Issues and Solutions

#### Registry Not Accessible

```bash
# Check registry is running
curl http://localhost:5000/v2/

# Check network connectivity
nc -zv localhost 5000

# Check Docker logs
docker logs registry
```

#### ORAS Commands Failing

```bash
# Verify ORAS installation
oras version

# Enable debug mode
export ORAS_DEBUG=true
oras pull localhost:5000/agents/test:latest

# Check registry compatibility
oras repo ls localhost:5000
```

#### Agent Cards Not Found

```python
# Debug discovery
discovery = RegistryDiscovery("localhost:5000")

# List all repositories
repos = discovery._list_repositories()
print(f"Found repositories: {repos}")

# Check specific repository
card = discovery._pull_agent_card("agents/translator")
if card:
    print(f"Agent card: {json.dumps(card, indent=2)}")
else:
    print("Failed to pull agent card")
```

#### Performance Issues

```python
# Use caching
discovery = CachedDiscovery(
    registry_url="localhost:5000",
    cache_ttl=600,  # 10 minutes
    refresh_interval=120  # 2 minutes
)

# Use connection pooling
client = httpx.Client(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
)
```

### Registry Diagnostics

```python
class RegistryDiagnostics:
    """Tools for diagnosing registry issues"""

    def __init__(self, registry_url: str):
        self.registry_url = registry_url

    def check_health(self) -> Dict[str, Any]:
        """Comprehensive registry health check"""
        results = {
            "registry_url": self.registry_url,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }

        # Check basic connectivity
        try:
            response = httpx.get(f"http://{self.registry_url}/v2/")
            results["checks"]["connectivity"] = {
                "status": "pass",
                "status_code": response.status_code
            }
        except Exception as e:
            results["checks"]["connectivity"] = {
                "status": "fail",
                "error": str(e)
            }
            return results

        # Check catalog endpoint
        try:
            response = httpx.get(f"http://{self.registry_url}/v2/_catalog")
            repos = response.json().get("repositories", [])
            results["checks"]["catalog"] = {
                "status": "pass",
                "repository_count": len(repos)
            }
        except Exception as e:
            results["checks"]["catalog"] = {
                "status": "fail",
                "error": str(e)
            }

        # Check ORAS compatibility
        try:
            cmd = ["oras", "repo", "ls", self.registry_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            results["checks"]["oras"] = {
                "status": "pass" if result.returncode == 0 else "fail",
                "output": result.stdout or result.stderr
            }
        except Exception as e:
            results["checks"]["oras"] = {
                "status": "fail",
                "error": str(e)
            }

        return results

    def validate_agent_cards(self) -> Dict[str, Any]:
        """Validate all agent cards in registry"""
        discovery = RegistryDiscovery(self.registry_url)
        repositories = discovery._list_repositories()

        validation_results = {}

        for repo in repositories:
            if not repo.startswith("agents/"):
                continue

            card = discovery._pull_agent_card(repo)
            if not card:
                validation_results[repo] = {"status": "missing"}
                continue

            # Validate required fields
            errors = []
            if "name" not in card:
                errors.append("Missing 'name' field")
            if "url" not in card:
                errors.append("Missing 'url' field")
            if "skills" not in card or not card["skills"]:
                errors.append("Missing or empty 'skills' field")

            # Validate each skill
            for i, skill in enumerate(card.get("skills", [])):
                if "id" not in skill:
                    errors.append(f"Skill {i}: Missing 'id'")
                if "input_schema" not in skill:
                    errors.append(f"Skill {i}: Missing 'input_schema'")
                if "output_schema" not in skill:
                    errors.append(f"Skill {i}: Missing 'output_schema'")

            validation_results[repo] = {
                "status": "valid" if not errors else "invalid",
                "errors": errors
            }

        return validation_results
```

## Best Practices

### 1. Agent Card Design
- **Versioning**: Always include version in agent cards
- **Metadata**: Add labels for filtering and discovery
- **Documentation**: Include links to documentation
- **Examples**: Provide example inputs/outputs in skill definitions

### 2. Registry Organization
- **Naming Convention**: Use consistent naming (e.g., `agents/{domain}/{name}`)
- **Tagging Strategy**: Use semantic versioning and environment tags
- **Cleanup Policy**: Implement retention policies for old versions

### 3. Discovery Optimization
- **Caching**: Cache discovery results with appropriate TTLs
- **Parallel Queries**: Query multiple registries concurrently
- **Fallbacks**: Have fallback registries for high availability

### 4. Security
- **Authentication**: Use robot accounts with minimal permissions
- **TLS**: Always use HTTPS in production
- **Scanning**: Scan agent cards for security issues
- **Audit Logging**: Log all registry access

### 5. Monitoring
- **Metrics**: Track discovery latency and cache hit rates
- **Alerts**: Alert on registry unavailability
- **Health Checks**: Regular health checks of registry and agents

## References

- [OCI Distribution Spec](https://github.com/opencontainers/distribution-spec)
- [ORAS Documentation](https://oras.land/docs/)
- [Docker Registry API](https://docs.docker.com/registry/spec/api/)
- [Harbor Registry](https://goharbor.io/)
- [Zot Registry](https://zotregistry.io/)