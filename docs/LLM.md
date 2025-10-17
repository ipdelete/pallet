# A2A Pattern: LLM Implementation Guide

> Token-efficient guide for LLMs to implement the Agent-to-Agent protocol pattern

## Core Architecture

**Pattern**: Capability-based agent discovery + JSON-RPC 2.0 communication
**Key Innovation**: Agents discovered by skill, not URL (loose coupling)

### Essential Components

1. **Agent**: HTTP service exposing skills via FastAPI
2. **Skill**: Discrete capability (ID + input/output schemas)
3. **Agent Card**: JSON describing agent capabilities
4. **Registry**: OCI artifact storage for agent cards
5. **Discovery**: Query registry by skill_id → returns agent URL
6. **Orchestrator**: Coordinates multiple agents into workflows

### Protocol Stack

```
Application Logic → A2A Protocol → JSON-RPC 2.0 → HTTP/HTTPS
```

### Standard Endpoints

- `GET /agent-card` → Returns AgentCard JSON
- `POST /execute` → JSON-RPC skill execution
- `GET /health` → Health check (optional)

## Implementation: BaseAgent

```python
from abc import ABC, abstractmethod
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import httpx

class SkillDefinition(BaseModel):
    id: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

class AgentCard(BaseModel):
    name: str
    url: str
    version: str = "1.0.0"
    skills: List[SkillDefinition]

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str  # skill_id
    params: Dict[str, Any]
    id: str

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: str

class BaseAgent(ABC):
    def __init__(self, name: str, port: int, skills: List[SkillDefinition]):
        self.name = name
        self.port = port
        self.url = f"http://localhost:{port}"
        self.skills = skills
        self.app = FastAPI(title=name)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/agent-card")
        async def get_agent_card() -> AgentCard:
            return AgentCard(name=self.name, url=self.url, skills=self.skills)

        @self.app.post("/execute")
        async def execute(request: JSONRPCRequest) -> JSONRPCResponse:
            try:
                skill_id = request.method
                if not any(s.id == skill_id for s in self.skills):
                    return JSONRPCResponse(
                        id=request.id,
                        error={"code": -32601, "message": f"Unknown skill: {skill_id}"}
                    )
                result = await self.execute_skill(skill_id, request.params)
                return JSONRPCResponse(id=request.id, result=result)
            except Exception as e:
                return JSONRPCResponse(
                    id=request.id,
                    error={"code": -32603, "message": str(e)}
                )

    @abstractmethod
    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Implement this with your domain logic"""
        pass

    async def call_agent_skill(self, agent_url: str, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            request = JSONRPCRequest(method=skill_id, params=params, id=f"{self.name}-call")
            response = await client.post(f"{agent_url}/execute", json=request.dict())
            rpc_response = JSONRPCResponse(**response.json())
            if rpc_response.error:
                raise RuntimeError(f"Agent error: {rpc_response.error}")
            return rpc_response.result

    def run(self):
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)
```

## Implementation: Registry Discovery

```python
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import httpx

class RegistryDiscovery:
    def __init__(self, registry_url: str = "localhost:5000"):
        self.registry_url = registry_url

    def discover_agent(self, skill_id: str) -> Optional[str]:
        """Find agent URL by skill_id"""
        repositories = self._list_repositories()
        for repo in repositories:
            if not repo.startswith("agents/"):
                continue
            agent_card = self._pull_agent_card(repo)
            if not agent_card:
                continue
            for skill in agent_card.get("skills", []):
                if skill["id"] == skill_id:
                    return agent_card["url"]
        return None

    def _list_repositories(self) -> list:
        try:
            response = httpx.get(f"http://{self.registry_url}/v2/_catalog")
            return response.json().get("repositories", [])
        except:
            return []

    def _pull_agent_card(self, repository: str) -> Optional[Dict[str, Any]]:
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                cmd = ["oras", "pull", f"{self.registry_url}/{repository}:v1", "-o", tmpdir]
                subprocess.run(cmd, capture_output=True, check=True)
                for file in Path(tmpdir).glob("*.json"):
                    with open(file, "r") as f:
                        return json.load(f)
            except:
                return None
```

## Implementation: Orchestrator

```python
import asyncio
from typing import List, Dict, Any
from enum import Enum

class ExecutionStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    MAP_REDUCE = "map_reduce"

class Orchestrator:
    def __init__(self, discovery: RegistryDiscovery):
        self.discovery = discovery

    async def sequential(self, skills: List[str], initial_input: Any) -> Any:
        """A → B → C"""
        result = initial_input
        for skill_id in skills:
            agent_url = self.discovery.discover_agent(skill_id)
            result = await self._call_agent(agent_url, skill_id, result)
        return result

    async def parallel(self, skills: List[str], input_data: Any) -> List[Any]:
        """A,B,C simultaneously"""
        tasks = []
        for skill_id in skills:
            agent_url = self.discovery.discover_agent(skill_id)
            tasks.append(self._call_agent(agent_url, skill_id, input_data))
        return await asyncio.gather(*tasks)

    async def conditional(self, rules: List[Dict], input_data: Any) -> Any:
        """Route based on condition"""
        for rule in rules:
            if rule.get("default") or self._evaluate_condition(input_data, rule.get("condition")):
                skill_id = rule["skill_id"]
                agent_url = self.discovery.discover_agent(skill_id)
                return await self._call_agent(agent_url, skill_id, input_data)

    async def map_reduce(self, items: List[Any], map_skill: str, reduce_skill: str) -> Any:
        """Map over collection, reduce results"""
        map_url = self.discovery.discover_agent(map_skill)
        mapped = await asyncio.gather(*[self._call_agent(map_url, map_skill, item) for item in items])
        reduce_url = self.discovery.discover_agent(reduce_skill)
        return await self._call_agent(reduce_url, reduce_skill, mapped)

    async def _call_agent(self, agent_url: str, skill_id: str, params: Any) -> Any:
        async with httpx.AsyncClient(timeout=30) as client:
            request = {"jsonrpc": "2.0", "method": skill_id, "params": params, "id": "orch"}
            response = await client.post(f"{agent_url}/execute", json=request)
            result = response.json()
            if "error" in result:
                raise RuntimeError(f"Agent error: {result['error']}")
            return result.get("result")

    def _evaluate_condition(self, data: Dict, condition: Dict) -> bool:
        if not condition:
            return False
        field_value = data.get(condition["field"])
        operator = condition["operator"]
        test_value = condition["value"]
        return {
            "eq": lambda: field_value == test_value,
            "gt": lambda: field_value > test_value,
            "lt": lambda: field_value < test_value,
            "in": lambda: field_value in test_value,
            "contains": lambda: test_value in field_value
        }.get(operator, lambda: False)()
```

## Example: Concrete Agent

```python
class ProcessingAgent(BaseAgent):
    def __init__(self):
        skills = [
            SkillDefinition(
                id="process_data",
                description="Processes input data",
                input_schema={
                    "type": "object",
                    "properties": {"data": {"type": "string"}},
                    "required": ["data"]
                },
                output_schema={
                    "type": "object",
                    "properties": {"result": {"type": "string"}}
                }
            )
        ]
        super().__init__(name="processor", port=8001, skills=skills)

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if skill_id == "process_data":
            # Your logic here
            return {"result": f"Processed: {params['data']}"}
        raise ValueError(f"Unknown skill: {skill_id}")

# Run
if __name__ == "__main__":
    ProcessingAgent().run()
```

## Registry Setup

```bash
# Start OCI registry
docker run -d -p 5000:5000 --name registry registry:2

# Create agent card JSON
cat > agent_card.json << 'EOF'
{
  "name": "processor",
  "url": "http://localhost:8001",
  "version": "1.0.0",
  "skills": [{"id": "process_data", "description": "...", "input_schema": {...}, "output_schema": {...}}]
}
EOF

# Push to registry (requires ORAS CLI)
oras push localhost:5000/agents/processor:v1 agent_card.json:application/json
```

## Orchestration Patterns

### Sequential Pipeline
```python
# Healthcare: Image → Analyze → Diagnose → Report
pipeline = ["analyze_xray", "generate_diagnosis", "create_report"]
result = await orchestrator.sequential(pipeline, xray_data)
```

### Parallel Execution
```python
# Finance: Run checks simultaneously
checks = ["calculate_risk", "verify_kyc", "check_aml"]
results = await orchestrator.parallel(checks, application_data)
```

### Conditional Routing
```python
# Customer service: Route by intent
rules = [
    {"condition": {"field": "intent", "operator": "eq", "value": "refund"}, "skill_id": "process_refund"},
    {"condition": {"field": "sentiment", "operator": "lt", "value": 0.3}, "skill_id": "escalate_human"},
    {"default": True, "skill_id": "auto_respond"}
]
result = await orchestrator.conditional(rules, customer_request)
```

### Map-Reduce
```python
# Batch processing: Analyze documents → Aggregate
documents = ["doc1", "doc2", "doc3"]
summary = await orchestrator.map_reduce(documents, "analyze_doc", "aggregate_results")
```

## Production Enhancements

### Retry Logic
```python
async def call_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Caching
```python
class CachedDiscovery(RegistryDiscovery):
    def __init__(self, *args, cache_ttl=300, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
        self.cache_times = {}

    def discover_agent(self, skill_id: str):
        import time
        if skill_id in self.cache:
            if time.time() - self.cache_times[skill_id] < self.cache_ttl:
                return self.cache[skill_id]
        agent_url = super().discover_agent(skill_id)
        self.cache[skill_id] = agent_url
        self.cache_times[skill_id] = time.time()
        return agent_url
```

### Monitoring
```python
class MonitoredAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = {"requests": 0, "errors": 0, "latency": []}

    async def execute_skill(self, skill_id, params):
        import time
        start = time.time()
        self.metrics["requests"] += 1
        try:
            result = await self._execute_impl(skill_id, params)
            self.metrics["latency"].append(time.time() - start)
            return result
        except Exception as e:
            self.metrics["errors"] += 1
            raise
```

## Domain Examples

### Healthcare
```python
# Agents: image_analyzer, diagnosis_generator, treatment_planner
workflow = ["analyze_medical_image", "generate_diagnosis", "recommend_treatment"]
```

### Finance
```python
# Agents: risk_assessor, compliance_checker, loan_processor
checks = ["assess_credit_risk", "verify_kyc", "check_aml"]
```

### Education
```python
# Agents: content_analyzer, student_profiler, curriculum_builder
pipeline = ["analyze_learning_style", "identify_knowledge_gaps", "generate_lesson_plan"]
```

### Content Creation
```python
# Agents: researcher, writer, editor, seo_optimizer
pipeline = ["research_topic", "write_article", "check_grammar", "optimize_seo"]
```

## Key Design Principles

1. **Stateless Agents**: Each call independent (enables scaling)
2. **Single Responsibility**: One skill = one well-defined task
3. **Schema Validation**: Strict input/output schemas
4. **Error Handling**: Fail gracefully, return structured errors
5. **Loose Coupling**: Discover by capability, not hardcoded URLs

## Implementation Checklist

- [ ] Define skills (ID, description, schemas)
- [ ] Implement BaseAgent subclass with execute_skill()
- [ ] Create agent card JSON
- [ ] Start OCI registry (Docker)
- [ ] Push agent card with ORAS
- [ ] Implement RegistryDiscovery
- [ ] Test: agent-card endpoint + execute endpoint
- [ ] Build orchestrator for your workflow pattern
- [ ] Add retry + caching + monitoring
- [ ] Deploy (Docker/K8s/Serverless)

## Testing

```python
# Unit test agent
from fastapi.testclient import TestClient

def test_agent():
    agent = ProcessingAgent()
    client = TestClient(agent.app)

    # Test agent card
    response = client.get("/agent-card")
    assert response.status_code == 200

    # Test skill execution
    response = client.post("/execute", json={
        "jsonrpc": "2.0",
        "method": "process_data",
        "params": {"data": "test"},
        "id": "1"
    })
    assert response.status_code == 200
    assert "result" in response.json()
```

## Quick Reference

### Agent Card Format
```json
{
  "name": "agent-name",
  "url": "http://host:port",
  "version": "1.0.0",
  "skills": [
    {
      "id": "skill_id",
      "description": "What it does",
      "input_schema": {"type": "object", "properties": {...}, "required": [...]},
      "output_schema": {"type": "object", "properties": {...}}
    }
  ]
}
```

### JSON-RPC Request
```json
{
  "jsonrpc": "2.0",
  "method": "skill_id",
  "params": {"key": "value"},
  "id": "unique-id"
}
```

### JSON-RPC Response
```json
{
  "jsonrpc": "2.0",
  "result": {"key": "value"},
  "id": "unique-id"
}
```

### Error Response
```json
{
  "jsonrpc": "2.0",
  "error": {"code": -32601, "message": "Method not found"},
  "id": "unique-id"
}
```

## References

- Google A2A Protocol: https://github.com/google-research/android_world/blob/main/android_world/a2a_protocol.md
- JSON-RPC 2.0: https://www.jsonrpc.org/specification
- ORAS: https://oras.land/docs/
- FastAPI: https://fastapi.tiangolo.com/

---

**Pattern Summary**: Build simple agents with focused skills → Store cards in OCI registry → Discover by capability → Orchestrate into workflows. Domain-agnostic, scalable, interoperable.