# A2A Pattern Implementation Guide

> A comprehensive guide to implementing Google's Agent-to-Agent (A2A) protocol for building interoperable AI agent systems

## Table of Contents
1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Protocol Architecture](#protocol-architecture)
4. [Implementation Pattern](#implementation-pattern)
5. [Building Your First Agent](#building-your-first-agent)
6. [Registry-Based Discovery](#registry-based-discovery)
7. [Orchestration Patterns](#orchestration-patterns)
8. [Non-Development Use Cases](#non-development-use-cases)
9. [References](#references)

## Introduction

The Agent-to-Agent (A2A) protocol, developed by Google Research, provides a standardized way for AI agents to discover, communicate, and collaborate with each other. This guide demonstrates a production-ready implementation pattern that can be adapted for any domain—from software development to healthcare, finance, education, or creative workflows.

### What Is A2A?

A2A is a protocol that enables:
- **Interoperability**: Agents from different vendors can work together
- **Discovery**: Agents can find each other based on capabilities (skills)
- **Composition**: Complex workflows can be built by chaining simple agents
- **Standards-based**: Uses JSON-RPC 2.0 and HTTP for maximum compatibility

### Why This Pattern Matters

Traditional agent systems often suffer from:
- **Tight coupling**: Hardcoded agent addresses and dependencies
- **Limited reusability**: Agents built for specific pipelines
- **Poor scalability**: Adding new agents requires code changes
- **Vendor lock-in**: Proprietary protocols prevent mixing agents

The A2A pattern solves these problems through **capability-based discovery** and **standardized communication**.

## Core Concepts

### 1. Agents
An agent is a service that exposes one or more **skills** via HTTP endpoints. Each agent:
- Has a unique identity
- Declares its capabilities (skills)
- Communicates via JSON-RPC 2.0
- Is discoverable through its agent card

### 2. Skills
A skill is a discrete capability that an agent provides. Skills have:
- **ID**: Unique identifier (e.g., `translate_text`, `analyze_sentiment`)
- **Input Schema**: JSON Schema defining expected parameters
- **Output Schema**: JSON Schema defining returned data
- **Description**: Human-readable explanation

### 3. Agent Cards
An agent card is a JSON document that describes an agent and its skills:

```json
{
  "name": "translation-agent",
  "url": "http://agent-host:8080",
  "version": "1.0.0",
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
  ]
}
```

### 4. Discovery
Discovery is the process of finding agents based on their skills. Instead of hardcoding URLs, orchestrators ask: "Who has skill X?" The discovery system returns the appropriate agent's URL.

## Protocol Architecture

### Communication Stack

```
┌──────────────────────────┐
│   Application Logic      │ ← Your agent's business logic
├──────────────────────────┤
│   A2A Protocol Layer     │ ← Skill definitions, agent cards
├──────────────────────────┤
│   JSON-RPC 2.0          │ ← Message format
├──────────────────────────┤
│   HTTP/HTTPS            │ ← Transport layer
└──────────────────────────┘
```

### Message Flow

1. **Discovery Phase**:
   ```
   Orchestrator → Registry: "Who has skill 'translate_text'?"
   Registry → Orchestrator: "translation-agent at http://host:8080"
   ```

2. **Execution Phase**:
   ```
   Orchestrator → Agent: JSON-RPC request to /execute
   Agent → LLM/Logic: Process request
   Agent → Orchestrator: JSON-RPC response
   ```

### Standard Endpoints

Every A2A agent MUST expose:

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/agent-card` | GET | Returns agent capabilities | Agent card JSON |
| `/execute` | POST | Executes a skill | JSON-RPC response |
| `/health` | GET | Health check (optional) | Status JSON |

## Implementation Pattern

### BaseAgent Class (Python/FastAPI)

Here's the core pattern for building A2A agents:

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json

class SkillDefinition(BaseModel):
    """Defines a skill's interface"""
    id: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class AgentCard(BaseModel):
    """Agent metadata and capabilities"""
    name: str
    url: str
    version: str = "1.0.0"
    skills: List[SkillDefinition]

class JSONRPCRequest(BaseModel):
    """Standard JSON-RPC 2.0 request"""
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]
    id: str

class JSONRPCResponse(BaseModel):
    """Standard JSON-RPC 2.0 response"""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: str

class BaseAgent(ABC):
    """
    Base class for all A2A agents.
    Inherit from this to create domain-specific agents.
    """

    def __init__(self, name: str, port: int, skills: List[SkillDefinition]):
        self.name = name
        self.port = port
        self.url = f"http://localhost:{port}"
        self.skills = skills
        self.app = FastAPI(title=name)
        self._setup_routes()

    def _setup_routes(self):
        """Configure A2A protocol endpoints"""

        @self.app.get("/agent-card")
        async def get_agent_card() -> AgentCard:
            """Expose agent capabilities for discovery"""
            return AgentCard(
                name=self.name,
                url=self.url,
                skills=self.skills
            )

        @self.app.post("/execute")
        async def execute(request: JSONRPCRequest) -> JSONRPCResponse:
            """Execute a skill via JSON-RPC"""
            try:
                # Extract skill_id and parameters
                skill_id = request.method
                params = request.params

                # Validate skill exists
                if not any(s.id == skill_id for s in self.skills):
                    return JSONRPCResponse(
                        id=request.id,
                        error={
                            "code": -32601,
                            "message": f"Unknown skill: {skill_id}"
                        }
                    )

                # Execute skill (implemented by subclass)
                result = await self.execute_skill(skill_id, params)

                return JSONRPCResponse(
                    id=request.id,
                    result=result
                )

            except Exception as e:
                return JSONRPCResponse(
                    id=request.id,
                    error={
                        "code": -32603,
                        "message": str(e)
                    }
                )

    @abstractmethod
    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement this method in your agent.
        This is where your domain logic lives.
        """
        pass

    async def call_agent_skill(self, agent_url: str, skill_id: str,
                              params: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to call another agent's skill"""
        async with httpx.AsyncClient() as client:
            request = JSONRPCRequest(
                method=skill_id,
                params=params,
                id=f"{self.name}-{skill_id}-call"
            )

            response = await client.post(
                f"{agent_url}/execute",
                json=request.dict()
            )

            rpc_response = JSONRPCResponse(**response.json())

            if rpc_response.error:
                raise RuntimeError(f"Agent error: {rpc_response.error}")

            return rpc_response.result

    def run(self):
        """Start the agent server"""
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)
```

## Building Your First Agent

### Example: Translation Agent

Let's build an agent for a non-development use case—language translation:

```python
from typing import Dict, Any
import asyncio

class TranslationAgent(BaseAgent):
    """
    Agent that translates text between languages.
    This example shows the pattern—replace with actual translation logic.
    """

    def __init__(self):
        skills = [
            SkillDefinition(
                id="translate_text",
                description="Translates text between languages",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "source_lang": {"type": "string"},
                        "target_lang": {"type": "string"}
                    },
                    "required": ["text", "target_lang"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "translated_text": {"type": "string"},
                        "source_lang": {"type": "string"},
                        "target_lang": {"type": "string"},
                        "confidence": {"type": "number"}
                    }
                }
            ),
            SkillDefinition(
                id="detect_language",
                description="Detects the language of input text",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "detected_lang": {"type": "string"},
                        "confidence": {"type": "number"}
                    }
                }
            )
        ]

        super().__init__(
            name="translation-agent",
            port=8001,
            skills=skills
        )

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute translation skills"""

        if skill_id == "translate_text":
            return await self._translate_text(params)
        elif skill_id == "detect_language":
            return await self._detect_language(params)
        else:
            raise ValueError(f"Unknown skill: {skill_id}")

    async def _translate_text(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Translate text implementation.
        In production, this would call a translation API or model.
        """
        text = params["text"]
        target_lang = params["target_lang"]
        source_lang = params.get("source_lang")

        # If source language not provided, detect it
        if not source_lang:
            detection = await self._detect_language({"text": text})
            source_lang = detection["detected_lang"]

        # Here you would call your translation service
        # For example: Google Translate API, DeepL, OpenAI, etc.
        # This is a mock implementation:

        translated_text = f"[Translated from {source_lang} to {target_lang}]: {text}"

        return {
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "confidence": 0.95
        }

    async def _detect_language(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect language implementation.
        In production, use a language detection library or API.
        """
        text = params["text"]

        # Mock implementation - replace with actual detection
        # Could use: langdetect, polyglot, fasttext, etc.

        # Simple heuristic for demo
        if any(c in text for c in "你好中文"):
            detected = "zh"
        elif any(c in text for c in "こんにちは日本"):
            detected = "ja"
        elif "bonjour" in text.lower():
            detected = "fr"
        else:
            detected = "en"

        return {
            "detected_lang": detected,
            "confidence": 0.85
        }

# Run the agent
if __name__ == "__main__":
    agent = TranslationAgent()
    agent.run()
```

### Testing Your Agent

Test the agent with curl:

```bash
# Get agent card
curl http://localhost:8001/agent-card

# Translate text
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "translate_text",
    "params": {
      "text": "Hello, world!",
      "target_lang": "es"
    },
    "id": "test-1"
  }'
```

## Registry-Based Discovery

### Why Use a Registry?

Without a registry, you have to hardcode agent URLs:
```python
# Bad: Tight coupling
translator_url = "http://localhost:8001"  # What if this changes?
```

With a registry, you discover agents by capability:
```python
# Good: Loose coupling
translator_url = discover_agent("translate_text")  # Find whoever can translate
```

### Setting Up an OCI Registry

The pattern uses OCI (Open Container Initiative) registries to store agent cards as artifacts:

```bash
# Start a local registry using Docker
docker run -d -p 5000:5000 --name registry registry:2

# Install ORAS CLI for pushing/pulling artifacts
# See: https://oras.land/docs/installation
brew install oras  # macOS
# or
curl -LO https://github.com/oras-project/oras/releases/download/v1.1.0/oras_1.1.0_linux_amd64.tar.gz
```

### Pushing Agent Cards to Registry

```bash
# Save your agent card as JSON
cat > translation_agent_card.json << EOF
{
  "name": "translation-agent",
  "url": "http://localhost:8001",
  "version": "1.0.0",
  "skills": [...]
}
EOF

# Push to registry as an OCI artifact
oras push localhost:5000/agents/translation:v1 \
  --artifact-type application/vnd.agent.card \
  translation_agent_card.json:application/json
```

### Discovery Implementation

```python
import json
import subprocess
import tempfile
from typing import Optional, Dict, Any
from pathlib import Path

class RegistryDiscovery:
    """
    Discovers agents from an OCI registry based on their skills.
    """

    def __init__(self, registry_url: str = "localhost:5000"):
        self.registry_url = registry_url

    def discover_agent(self, skill_id: str) -> Optional[str]:
        """
        Find an agent that provides the specified skill.
        Returns the agent's URL if found, None otherwise.
        """
        # Get list of all agent repositories
        repositories = self._list_repositories()

        # Check each agent's card for the requested skill
        for repo in repositories:
            if not repo.startswith("agents/"):
                continue

            agent_card = self._pull_agent_card(repo)
            if not agent_card:
                continue

            # Check if this agent has the requested skill
            for skill in agent_card.get("skills", []):
                if skill["id"] == skill_id:
                    return agent_card["url"]

        return None

    def _list_repositories(self) -> list:
        """List all repositories in the registry"""
        try:
            # Use registry API to list repositories
            import httpx
            response = httpx.get(f"http://{self.registry_url}/v2/_catalog")
            data = response.json()
            return data.get("repositories", [])
        except Exception as e:
            print(f"Failed to list repositories: {e}")
            return []

    def _pull_agent_card(self, repository: str) -> Optional[Dict[str, Any]]:
        """Pull and parse an agent card from the registry"""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Use ORAS to pull the artifact
                cmd = [
                    "oras", "pull",
                    f"{self.registry_url}/{repository}:v1",
                    "-o", tmpdir
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    return None

                # Find and read the agent card JSON file
                for file in Path(tmpdir).iterdir():
                    if file.suffix == ".json":
                        with open(file, "r") as f:
                            return json.load(f)

        except Exception as e:
            print(f"Failed to pull agent card for {repository}: {e}")

        return None

    def list_all_skills(self) -> Dict[str, str]:
        """
        List all available skills across all agents.
        Returns a mapping of skill_id -> agent_url
        """
        skills_map = {}
        repositories = self._list_repositories()

        for repo in repositories:
            if not repo.startswith("agents/"):
                continue

            agent_card = self._pull_agent_card(repo)
            if not agent_card:
                continue

            agent_url = agent_card["url"]
            for skill in agent_card.get("skills", []):
                skills_map[skill["id"]] = agent_url

        return skills_map
```

## Orchestration Patterns

### Sequential Pipeline

Chain agents together in sequence:

```python
class SequentialOrchestrator:
    """
    Orchestrates agents in a sequential pipeline.
    Each agent's output becomes the next agent's input.
    """

    def __init__(self, discovery: RegistryDiscovery):
        self.discovery = discovery

    async def run_pipeline(self, pipeline_config: List[Dict[str, Any]],
                          initial_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a pipeline of agent skills.

        pipeline_config format:
        [
            {"skill_id": "detect_language", "output_key": "language"},
            {"skill_id": "translate_text", "params_mapping": {...}},
            {"skill_id": "text_to_speech", "params_mapping": {...}}
        ]
        """
        current_data = initial_input
        results = []

        for step in pipeline_config:
            skill_id = step["skill_id"]

            # Discover agent for this skill
            agent_url = self.discovery.discover_agent(skill_id)
            if not agent_url:
                raise RuntimeError(f"No agent found for skill: {skill_id}")

            # Map parameters if specified
            if "params_mapping" in step:
                params = self._map_params(current_data, step["params_mapping"])
            else:
                params = current_data

            # Execute skill
            result = await self._call_agent(agent_url, skill_id, params)
            results.append(result)

            # Update current data for next step
            if "output_key" in step:
                current_data[step["output_key"]] = result
            else:
                current_data = result

        return {
            "pipeline_results": results,
            "final_output": current_data
        }

    def _map_params(self, data: Dict, mapping: Dict) -> Dict:
        """Map data fields to parameter names"""
        params = {}
        for param_name, data_path in mapping.items():
            # Support nested paths like "result.text"
            value = data
            for key in data_path.split("."):
                value = value.get(key, "")
            params[param_name] = value
        return params

    async def _call_agent(self, agent_url: str, skill_id: str,
                         params: Dict[str, Any]) -> Dict[str, Any]:
        """Call an agent's skill via JSON-RPC"""
        import httpx

        async with httpx.AsyncClient() as client:
            request = {
                "jsonrpc": "2.0",
                "method": skill_id,
                "params": params,
                "id": f"orch-{skill_id}"
            }

            response = await client.post(
                f"{agent_url}/execute",
                json=request
            )

            rpc_response = response.json()

            if "error" in rpc_response:
                raise RuntimeError(f"Agent error: {rpc_response['error']}")

            return rpc_response["result"]
```

### Parallel Execution

Run multiple agents concurrently:

```python
import asyncio

class ParallelOrchestrator:
    """
    Orchestrates agents in parallel for concurrent execution.
    """

    def __init__(self, discovery: RegistryDiscovery):
        self.discovery = discovery

    async def run_parallel(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple agent skills in parallel.

        tasks format:
        [
            {"skill_id": "analyze_sentiment", "params": {...}},
            {"skill_id": "extract_entities", "params": {...}},
            {"skill_id": "summarize_text", "params": {...}}
        ]
        """
        # Create async tasks for each skill
        async_tasks = []

        for task in tasks:
            skill_id = task["skill_id"]
            params = task["params"]

            # Discover agent
            agent_url = self.discovery.discover_agent(skill_id)
            if not agent_url:
                # Handle missing agent
                async_tasks.append(self._error_task(skill_id))
            else:
                # Create execution task
                async_tasks.append(
                    self._call_agent(agent_url, skill_id, params)
                )

        # Execute all tasks in parallel
        results = await asyncio.gather(*async_tasks, return_exceptions=True)

        # Format results
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "skill_id": tasks[i]["skill_id"],
                    "error": str(result)
                })
            else:
                formatted_results.append({
                    "skill_id": tasks[i]["skill_id"],
                    "result": result
                })

        return formatted_results

    async def _error_task(self, skill_id: str):
        """Return an error for missing agents"""
        raise RuntimeError(f"No agent found for skill: {skill_id}")

    async def _call_agent(self, agent_url: str, skill_id: str,
                         params: Dict[str, Any]) -> Dict[str, Any]:
        # Same as sequential orchestrator
        pass
```

### Conditional Routing

Route to different agents based on conditions:

```python
class ConditionalOrchestrator:
    """
    Routes to different agents based on conditions.
    """

    def __init__(self, discovery: RegistryDiscovery):
        self.discovery = discovery

    async def route_conditional(self, input_data: Dict[str, Any],
                               routing_rules: List[Dict]) -> Dict[str, Any]:
        """
        Route to agents based on conditions.

        routing_rules format:
        [
            {
                "condition": {"field": "language", "operator": "eq", "value": "en"},
                "skill_id": "english_processor",
                "params": {...}
            },
            {
                "condition": {"field": "length", "operator": "gt", "value": 1000},
                "skill_id": "long_text_processor",
                "params": {...}
            },
            {
                "default": true,
                "skill_id": "general_processor",
                "params": {...}
            }
        ]
        """
        for rule in routing_rules:
            if "default" in rule and rule["default"]:
                # Default rule - always matches
                skill_id = rule["skill_id"]
                params = rule.get("params", input_data)
            elif self._evaluate_condition(input_data, rule["condition"]):
                # Condition matches
                skill_id = rule["skill_id"]
                params = rule.get("params", input_data)
                break
        else:
            raise ValueError("No matching routing rule found")

        # Execute the selected skill
        agent_url = self.discovery.discover_agent(skill_id)
        if not agent_url:
            raise RuntimeError(f"No agent found for skill: {skill_id}")

        return await self._call_agent(agent_url, skill_id, params)

    def _evaluate_condition(self, data: Dict, condition: Dict) -> bool:
        """Evaluate a routing condition"""
        field_value = data.get(condition["field"])
        operator = condition["operator"]
        test_value = condition["value"]

        if operator == "eq":
            return field_value == test_value
        elif operator == "gt":
            return field_value > test_value
        elif operator == "lt":
            return field_value < test_value
        elif operator == "in":
            return field_value in test_value
        elif operator == "contains":
            return test_value in field_value
        else:
            return False
```

## Non-Development Use Cases

The A2A pattern works for ANY domain. Here are examples:

### Healthcare Pipeline

```python
# Agent: Medical Image Analyzer
skills = ["detect_anomalies", "measure_tumor", "classify_condition"]

# Agent: Report Generator
skills = ["generate_medical_report", "flag_critical_findings"]

# Agent: Notification Service
skills = ["notify_physician", "schedule_followup"]

# Pipeline
pipeline = [
    {"skill_id": "detect_anomalies"},     # Analyze X-ray/MRI
    {"skill_id": "classify_condition"},    # Determine condition
    {"skill_id": "generate_medical_report"}, # Create report
    {"skill_id": "notify_physician"}       # Alert if critical
]
```

### Financial Services

```python
# Agent: Risk Analyzer
skills = ["calculate_risk_score", "detect_fraud", "assess_creditworthiness"]

# Agent: Compliance Checker
skills = ["check_aml", "verify_kyc", "audit_transaction"]

# Agent: Decision Engine
skills = ["approve_loan", "set_interest_rate", "generate_contract"]

# Parallel execution for loan approval
tasks = [
    {"skill_id": "calculate_risk_score"},
    {"skill_id": "check_aml"},
    {"skill_id": "verify_kyc"}
]
# All checks run simultaneously, then decision
```

### Education Platform

```python
# Agent: Content Analyzer
skills = ["assess_difficulty", "extract_topics", "identify_prerequisites"]

# Agent: Student Profiler
skills = ["analyze_learning_style", "track_progress", "identify_gaps"]

# Agent: Curriculum Builder
skills = ["generate_lesson_plan", "recommend_resources", "create_quiz"]

# Adaptive learning pipeline
pipeline = [
    {"skill_id": "analyze_learning_style"},  # Understand student
    {"skill_id": "identify_gaps"},           # Find knowledge gaps
    {"skill_id": "generate_lesson_plan"},    # Create personalized plan
    {"skill_id": "create_quiz"}              # Generate assessment
]
```

### Content Creation

```python
# Agent: Idea Generator
skills = ["brainstorm_topics", "generate_outlines", "suggest_angles"]

# Agent: Content Writer
skills = ["write_article", "create_script", "generate_copy"]

# Agent: Editor
skills = ["check_grammar", "improve_clarity", "fact_check"]

# Agent: SEO Optimizer
skills = ["optimize_keywords", "generate_meta", "analyze_readability"]

# Content pipeline
pipeline = [
    {"skill_id": "brainstorm_topics"},    # Generate ideas
    {"skill_id": "generate_outlines"},    # Create structure
    {"skill_id": "write_article"},        # Write content
    {"skill_id": "check_grammar"},        # Edit
    {"skill_id": "optimize_keywords"}     # SEO optimize
]
```

### Customer Service

```python
# Agent: Intent Classifier
skills = ["classify_intent", "detect_sentiment", "extract_entities"]

# Agent: Knowledge Base
skills = ["search_faqs", "find_documentation", "lookup_policy"]

# Agent: Response Generator
skills = ["generate_response", "personalize_message", "suggest_actions"]

# Agent: Escalation Manager
skills = ["assess_complexity", "route_to_human", "schedule_callback"]

# Conditional routing based on intent
routing_rules = [
    {
        "condition": {"field": "intent", "operator": "eq", "value": "refund"},
        "skill_id": "process_refund"
    },
    {
        "condition": {"field": "sentiment", "operator": "lt", "value": 0.3},
        "skill_id": "route_to_human"  # Escalate negative sentiment
    },
    {
        "default": true,
        "skill_id": "generate_response"
    }
]
```

## Advanced Patterns

### Agent Composition

Agents can call other agents, creating composite services:

```python
class CompositeAgent(BaseAgent):
    """
    An agent that orchestrates other agents internally.
    Exposes a high-level skill that uses multiple lower-level skills.
    """

    def __init__(self, discovery: RegistryDiscovery):
        self.discovery = discovery

        skills = [
            SkillDefinition(
                id="analyze_document",
                description="Complete document analysis pipeline",
                input_schema={
                    "type": "object",
                    "properties": {
                        "document": {"type": "string"},
                        "analysis_type": {"type": "string"}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "entities": {"type": "array"},
                        "sentiment": {"type": "number"},
                        "key_points": {"type": "array"}
                    }
                }
            )
        ]

        super().__init__(
            name="document-analyzer",
            port=8010,
            skills=skills
        )

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if skill_id == "analyze_document":
            document = params["document"]

            # Discover and call multiple analysis agents
            tasks = []

            # Find summarization agent
            summarizer_url = self.discovery.discover_agent("summarize_text")
            if summarizer_url:
                tasks.append(
                    self.call_agent_skill(summarizer_url, "summarize_text", {"text": document})
                )

            # Find entity extraction agent
            entity_url = self.discovery.discover_agent("extract_entities")
            if entity_url:
                tasks.append(
                    self.call_agent_skill(entity_url, "extract_entities", {"text": document})
                )

            # Find sentiment analysis agent
            sentiment_url = self.discovery.discover_agent("analyze_sentiment")
            if sentiment_url:
                tasks.append(
                    self.call_agent_skill(sentiment_url, "analyze_sentiment", {"text": document})
                )

            # Execute all analyses in parallel
            results = await asyncio.gather(*tasks)

            # Combine results
            return {
                "summary": results[0].get("summary", ""),
                "entities": results[1].get("entities", []),
                "sentiment": results[2].get("sentiment_score", 0),
                "key_points": results[0].get("key_points", [])
            }
```

### Dynamic Skill Loading

Load skills dynamically based on configuration:

```python
class DynamicAgent(BaseAgent):
    """
    Agent that loads skills from configuration files.
    Allows adding new skills without code changes.
    """

    def __init__(self, config_path: str):
        # Load configuration
        with open(config_path, "r") as f:
            config = json.load(f)

        # Parse skills from config
        skills = []
        for skill_config in config["skills"]:
            skills.append(SkillDefinition(**skill_config))

        # Map skill IDs to handler functions
        self.skill_handlers = {}
        for skill_config in config["skills"]:
            handler_name = skill_config.get("handler")
            if handler_name:
                # Dynamically import handler
                module_path, func_name = handler_name.rsplit(".", 1)
                module = __import__(module_path, fromlist=[func_name])
                self.skill_handlers[skill_config["id"]] = getattr(module, func_name)

        super().__init__(
            name=config["name"],
            port=config["port"],
            skills=skills
        )

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if skill_id in self.skill_handlers:
            handler = self.skill_handlers[skill_id]
            return await handler(params)
        else:
            raise ValueError(f"No handler for skill: {skill_id}")
```

### Monitoring and Observability

Add telemetry to track agent interactions:

```python
import time
import logging
from datetime import datetime

class MonitoredAgent(BaseAgent):
    """
    Agent with built-in monitoring and metrics.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = {
            "requests": 0,
            "errors": 0,
            "total_latency": 0,
            "skill_executions": {}
        }

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        self.metrics["requests"] += 1

        try:
            # Log request
            logging.info(f"Executing skill {skill_id} with params: {params}")

            # Execute actual skill
            result = await self._execute_skill_impl(skill_id, params)

            # Track success metrics
            latency = time.time() - start_time
            self.metrics["total_latency"] += latency

            if skill_id not in self.metrics["skill_executions"]:
                self.metrics["skill_executions"][skill_id] = {
                    "count": 0,
                    "total_latency": 0,
                    "errors": 0
                }

            self.metrics["skill_executions"][skill_id]["count"] += 1
            self.metrics["skill_executions"][skill_id]["total_latency"] += latency

            # Log success
            logging.info(f"Skill {skill_id} completed in {latency:.2f}s")

            return result

        except Exception as e:
            # Track error metrics
            self.metrics["errors"] += 1
            if skill_id in self.metrics["skill_executions"]:
                self.metrics["skill_executions"][skill_id]["errors"] += 1

            # Log error
            logging.error(f"Skill {skill_id} failed: {str(e)}")
            raise

    @abstractmethod
    async def _execute_skill_impl(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Actual skill implementation"""
        pass
```

## Testing Strategies

### Unit Testing Agents

```python
import pytest
from fastapi.testclient import TestClient

class TestTranslationAgent:

    def setup_method(self):
        self.agent = TranslationAgent()
        self.client = TestClient(self.agent.app)

    def test_agent_card(self):
        """Test agent card endpoint"""
        response = self.client.get("/agent-card")
        assert response.status_code == 200

        card = response.json()
        assert card["name"] == "translation-agent"
        assert len(card["skills"]) == 2
        assert any(s["id"] == "translate_text" for s in card["skills"])

    def test_translate_skill(self):
        """Test translation skill execution"""
        request = {
            "jsonrpc": "2.0",
            "method": "translate_text",
            "params": {
                "text": "Hello",
                "target_lang": "es"
            },
            "id": "test-1"
        }

        response = self.client.post("/execute", json=request)
        assert response.status_code == 200

        result = response.json()
        assert result["jsonrpc"] == "2.0"
        assert "result" in result
        assert "translated_text" in result["result"]

    def test_unknown_skill(self):
        """Test error handling for unknown skill"""
        request = {
            "jsonrpc": "2.0",
            "method": "unknown_skill",
            "params": {},
            "id": "test-2"
        }

        response = self.client.post("/execute", json=request)
        assert response.status_code == 200

        result = response.json()
        assert "error" in result
        assert result["error"]["code"] == -32601
```

### Integration Testing Pipelines

```python
import asyncio
from unittest.mock import Mock, patch

class TestOrchestration:

    @pytest.mark.asyncio
    async def test_sequential_pipeline(self):
        """Test sequential orchestration"""
        # Mock discovery
        mock_discovery = Mock()
        mock_discovery.discover_agent = Mock(side_effect=lambda skill: f"http://localhost:800{skill[-1]}")

        orchestrator = SequentialOrchestrator(mock_discovery)

        # Mock agent calls
        with patch.object(orchestrator, '_call_agent') as mock_call:
            mock_call.side_effect = [
                {"detected_lang": "en"},
                {"translated_text": "Hola"},
                {"audio_url": "http://audio.url"}
            ]

            pipeline = [
                {"skill_id": "detect_language1"},
                {"skill_id": "translate_text2"},
                {"skill_id": "text_to_speech3"}
            ]

            result = await orchestrator.run_pipeline(
                pipeline,
                {"text": "Hello"}
            )

            assert len(result["pipeline_results"]) == 3
            assert mock_call.call_count == 3
```

## Performance Considerations

### Connection Pooling

```python
class OptimizedOrchestrator:
    """Orchestrator with connection pooling"""

    def __init__(self, discovery: RegistryDiscovery):
        self.discovery = discovery
        # Create a shared client with connection pooling
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            timeout=httpx.Timeout(30.0)
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
```

### Caching Discovery Results

```python
from functools import lru_cache
import time

class CachedDiscovery(RegistryDiscovery):
    """Discovery with caching to reduce registry queries"""

    def __init__(self, *args, cache_ttl: int = 300, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_ttl = cache_ttl
        self.cache = {}
        self.cache_times = {}

    def discover_agent(self, skill_id: str) -> Optional[str]:
        # Check cache
        if skill_id in self.cache:
            if time.time() - self.cache_times[skill_id] < self.cache_ttl:
                return self.cache[skill_id]

        # Cache miss - query registry
        agent_url = super().discover_agent(skill_id)

        # Update cache
        self.cache[skill_id] = agent_url
        self.cache_times[skill_id] = time.time()

        return agent_url
```

### Batch Processing

```python
class BatchProcessor:
    """Process multiple requests in batches for efficiency"""

    async def process_batch(self, agent_url: str, skill_id: str,
                           items: List[Dict]) -> List[Dict]:
        """
        Process multiple items through the same skill.
        Some agents may support batch processing natively.
        """
        # Check if agent supports batch processing
        agent_card = await self._get_agent_card(agent_url)
        supports_batch = any(
            s["id"] == f"{skill_id}_batch"
            for s in agent_card.get("skills", [])
        )

        if supports_batch:
            # Use batch endpoint
            return await self._call_batch(agent_url, f"{skill_id}_batch", items)
        else:
            # Process items in parallel
            tasks = [
                self._call_agent(agent_url, skill_id, item)
                for item in items
            ]
            return await asyncio.gather(*tasks)
```

## Security Considerations

### Authentication and Authorization

```python
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

class SecureAgent(BaseAgent):
    """Agent with authentication"""

    def __init__(self, *args, api_keys: List[str], **kwargs):
        super().__init__(*args, **kwargs)
        self.api_keys = set(api_keys)

    def _setup_routes(self):
        super()._setup_routes()

        # Add auth to execute endpoint
        @self.app.post("/execute")
        async def execute(
            request: JSONRPCRequest,
            credentials: HTTPAuthorizationCredentials = Security(security)
        ) -> JSONRPCResponse:
            # Verify API key
            if credentials.credentials not in self.api_keys:
                raise HTTPException(status_code=403, detail="Invalid API key")

            # Process request
            return await super().execute(request)
```

### Rate Limiting

```python
from collections import defaultdict
import time

class RateLimitedAgent(BaseAgent):
    """Agent with rate limiting"""

    def __init__(self, *args, rate_limit: int = 100, window: int = 60, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limit = rate_limit  # requests per window
        self.window = window  # seconds
        self.request_counts = defaultdict(list)

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Check rate limit
        client_id = params.get("client_id", "anonymous")
        now = time.time()

        # Clean old requests
        self.request_counts[client_id] = [
            t for t in self.request_counts[client_id]
            if now - t < self.window
        ]

        # Check limit
        if len(self.request_counts[client_id]) >= self.rate_limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # Track request
        self.request_counts[client_id].append(now)

        # Process request
        return await super().execute_skill(skill_id, params)
```

## Deployment Patterns

### Container Deployment

```dockerfile
# Dockerfile for an A2A agent
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run agent
CMD ["python", "-m", "src.agents.translation_agent"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: translation-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: translation-agent
  template:
    metadata:
      labels:
        app: translation-agent
    spec:
      containers:
      - name: agent
        image: translation-agent:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: agent-secrets
              key: api-key
---
apiVersion: v1
kind: Service
metadata:
  name: translation-agent-service
spec:
  selector:
    app: translation-agent
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Serverless Deployment

```python
# AWS Lambda handler for A2A agent
import json
from mangum import Mangum

# Create agent
agent = TranslationAgent()

# Create Lambda handler
handler = Mangum(agent.app)

# For direct Lambda invocation
def lambda_handler(event, context):
    # Route based on event type
    if "path" in event:
        # API Gateway event
        return handler(event, context)
    else:
        # Direct invocation - execute skill
        skill_id = event.get("skill_id")
        params = event.get("params", {})

        # Execute skill synchronously
        import asyncio
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            agent.execute_skill(skill_id, params)
        )

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }
```

## References

### A2A Protocol Resources
- [Google A2A Protocol Specification](https://github.com/google-research/android_world/blob/main/android_world/a2a_protocol.md) - Official protocol documentation
- [Agent-to-Agent Communication](https://arxiv.org/abs/2408.15915) - Research paper on A2A patterns
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification) - Message format specification

### OCI and Registry
- [ORAS (OCI Registry as Storage)](https://oras.land/) - Tool for working with OCI registries
- [OCI Distribution Spec](https://github.com/opencontainers/distribution-spec) - Registry API specification
- [Docker Registry API](https://docs.docker.com/registry/spec/api/) - Registry HTTP API documentation

### Python/FastAPI Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Web framework documentation
- [Pydantic](https://docs.pydantic.dev/) - Data validation library
- [httpx](https://www.python-httpx.org/) - Async HTTP client
- [asyncio](https://docs.python.org/3/library/asyncio.html) - Asynchronous programming

### Related Projects
- [LangChain](https://github.com/langchain-ai/langchain) - Framework for LLM applications
- [AutoGPT](https://github.com/Significant-Gravitas/AutoGPT) - Autonomous AI agents
- [Microsoft Semantic Kernel](https://github.com/microsoft/semantic-kernel) - AI orchestration

### Best Practices
- [Microservices Patterns](https://microservices.io/patterns/) - Applicable architectural patterns
- [The Twelve-Factor App](https://12factor.net/) - Methodology for building services
- [Cloud Native Patterns](https://www.cncf.io/) - Modern deployment practices

## Conclusion

The A2A pattern provides a powerful, flexible framework for building AI agent systems that can:
- **Scale**: Add new agents without modifying existing code
- **Interoperate**: Mix agents from different teams or vendors
- **Adapt**: Work across any domain or use case
- **Discover**: Find capabilities dynamically at runtime

By following this implementation pattern, you can build robust agent systems for any domain—from healthcare to finance, education to creative work. The key is thinking in terms of **skills** rather than specific agents, and using **discovery** rather than hardcoded dependencies.

Start with simple agents, test them individually, then compose them into powerful pipelines. The pattern scales from single agents to complex orchestrations involving dozens of specialized agents working in concert.