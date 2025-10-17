# A2A Pattern Quick Reference

> Fast reference guide for implementing Agent-to-Agent systems

## 🚀 5-Minute Quick Start

### Step 1: Create Your First Agent

```python
# agent.py - Complete working agent in < 50 lines
from fastapi import FastAPI
from typing import Dict, Any
import uvicorn

app = FastAPI()

@app.get("/agent-card")
async def agent_card():
    return {
        "name": "my-agent",
        "url": "http://localhost:8000",
        "skills": [{
            "id": "process",
            "description": "Processes data",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"}
        }]
    }

@app.post("/execute")
async def execute(request: Dict[str, Any]):
    if request["method"] == "process":
        # Your logic here
        result = {"processed": request["params"]}
        return {"jsonrpc": "2.0", "result": result, "id": request["id"]}
    return {"jsonrpc": "2.0", "error": {"code": -32601}, "id": request["id"]}

if __name__ == "__main__":
    uvicorn.run(app, port=8000)
```

Run: `python agent.py`

### Step 2: Start a Registry

```bash
docker run -d -p 5000:5000 --name registry registry:2
```

### Step 3: Publish Agent Card

```bash
# Save agent card
cat > agent_card.json << 'EOF'
{
  "name": "my-agent",
  "url": "http://localhost:8000",
  "skills": [{
    "id": "process",
    "description": "Processes data",
    "input_schema": {"type": "object"},
    "output_schema": {"type": "object"}
  }]
}
EOF

# Push to registry
oras push localhost:5000/agents/my-agent:v1 agent_card.json:application/json
```

### Step 4: Discover and Call

```python
# discover_and_call.py
import httpx
import json

# Discover agent
def discover(skill_id):
    # In production, query registry
    return "http://localhost:8000"

# Call agent
agent_url = discover("process")
request = {
    "jsonrpc": "2.0",
    "method": "process",
    "params": {"data": "hello"},
    "id": "1"
}

response = httpx.post(f"{agent_url}/execute", json=request)
print(response.json())
```

## 📋 Command Cheat Sheet

### Docker Registry Commands

```bash
# Start registry
docker run -d -p 5000:5000 --name registry registry:2

# List repositories
curl http://localhost:5000/v2/_catalog

# List tags
curl http://localhost:5000/v2/agents/my-agent/tags/list

# Stop registry
docker stop registry && docker rm registry
```

### ORAS Commands

```bash
# Install ORAS
brew install oras                    # macOS
curl -LO https://github.com/...      # Linux (see docs)

# Push agent card
oras push localhost:5000/agents/NAME:TAG card.json:application/json

# Pull agent card
oras pull localhost:5000/agents/NAME:TAG -o output_dir

# List repositories
oras repo ls localhost:5000

# Copy between registries
oras copy SOURCE_REG/agents/NAME:TAG TARGET_REG/agents/NAME:TAG
```

### Testing Commands

```bash
# Test agent card endpoint
curl http://localhost:8000/agent-card | jq

# Test skill execution
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"SKILL_ID","params":{},"id":"1"}' | jq

# Health check
curl http://localhost:8000/health
```

## 🏗️ Pattern Templates

### Sequential Pipeline

```python
async def sequential_pipeline(agents, input_data):
    result = input_data
    for agent_url, skill_id in agents:
        result = await call_agent(agent_url, skill_id, result)
    return result

# Usage
agents = [
    ("http://agent1:8001", "extract"),
    ("http://agent2:8002", "transform"),
    ("http://agent3:8003", "load")
]
result = await sequential_pipeline(agents, data)
```

### Parallel Execution

```python
async def parallel_execution(agents, input_data):
    tasks = [
        call_agent(url, skill, input_data)
        for url, skill in agents
    ]
    return await asyncio.gather(*tasks)

# Usage
agents = [
    ("http://agent1:8001", "analyze_sentiment"),
    ("http://agent2:8002", "extract_entities"),
    ("http://agent3:8003", "summarize")
]
results = await parallel_execution(agents, text)
```

### Conditional Routing

```python
async def conditional_route(input_data, rules):
    for condition, agent_url, skill_id in rules:
        if condition(input_data):
            return await call_agent(agent_url, skill_id, input_data)
    return None

# Usage
rules = [
    (lambda x: x["lang"] == "en", "http://en-agent:8001", "process"),
    (lambda x: x["lang"] == "es", "http://es-agent:8002", "procesar"),
    (lambda x: True, "http://default:8003", "handle")  # default
]
result = await conditional_route({"lang": "en", "text": "..."}, rules)
```

### Map-Reduce

```python
async def map_reduce(items, map_agent, reduce_agent):
    # Map phase
    mapped = await asyncio.gather(*[
        call_agent(map_agent[0], map_agent[1], item)
        for item in items
    ])
    # Reduce phase
    return await call_agent(reduce_agent[0], reduce_agent[1], mapped)

# Usage
items = ["doc1", "doc2", "doc3"]
map_agent = ("http://analyzer:8001", "analyze")
reduce_agent = ("http://aggregator:8002", "aggregate")
summary = await map_reduce(items, map_agent, reduce_agent)
```

## 🔧 Common Implementations

### Agent with Multiple Skills

```python
class MultiSkillAgent(BaseAgent):
    def __init__(self):
        skills = [
            SkillDefinition(id="skill1", ...),
            SkillDefinition(id="skill2", ...),
            SkillDefinition(id="skill3", ...)
        ]
        super().__init__(name="multi", port=8000, skills=skills)

    async def execute_skill(self, skill_id, params):
        if skill_id == "skill1":
            return await self.skill1(params)
        elif skill_id == "skill2":
            return await self.skill2(params)
        elif skill_id == "skill3":
            return await self.skill3(params)
```

### Agent with External Service

```python
class ExternalServiceAgent(BaseAgent):
    async def execute_skill(self, skill_id, params):
        # Call external API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.service.com/process",
                json=params,
                headers={"Authorization": f"Bearer {API_KEY}"}
            )
            return response.json()
```

### Agent with Database

```python
class DatabaseAgent(BaseAgent):
    def __init__(self):
        super().__init__(...)
        self.db_pool = None

    async def startup(self):
        self.db_pool = await asyncpg.create_pool(DATABASE_URL)

    async def execute_skill(self, skill_id, params):
        async with self.db_pool.acquire() as conn:
            if skill_id == "query":
                rows = await conn.fetch(params["sql"])
                return [dict(r) for r in rows]
```

### Agent with Caching

```python
class CachedAgent(BaseAgent):
    def __init__(self):
        super().__init__(...)
        self.cache = {}

    async def execute_skill(self, skill_id, params):
        cache_key = f"{skill_id}:{json.dumps(params)}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        result = await self._compute_result(skill_id, params)
        self.cache[cache_key] = result
        return result
```

## 📊 Example Workflows by Domain

### Healthcare

```python
medical_pipeline = [
    ("http://image-analyzer:8001", "analyze_xray"),
    ("http://diagnosis:8002", "generate_diagnosis"),
    ("http://treatment:8003", "recommend_treatment"),
    ("http://reporter:8004", "create_report")
]
```

### Finance

```python
loan_approval = [
    ("http://credit-check:8001", "check_credit"),
    ("http://risk-assess:8002", "calculate_risk"),
    ("http://decision:8003", "approve_deny"),
    ("http://document:8004", "generate_documents")
]
```

### Education

```python
learning_path = [
    ("http://assessor:8001", "assess_knowledge"),
    ("http://recommender:8002", "recommend_content"),
    ("http://generator:8003", "create_exercises"),
    ("http://evaluator:8004", "evaluate_progress")
]
```

### E-commerce

```python
order_processing = [
    ("http://inventory:8001", "check_stock"),
    ("http://pricing:8002", "calculate_total"),
    ("http://payment:8003", "process_payment"),
    ("http://fulfillment:8004", "ship_order")
]
```

### Content Creation

```python
content_workflow = [
    ("http://researcher:8001", "research_topic"),
    ("http://writer:8002", "generate_content"),
    ("http://editor:8003", "edit_content"),
    ("http://seo:8004", "optimize_seo")
]
```

## 🐛 Debugging Tips

### Check Agent is Running

```python
import httpx

async def check_agent(url):
    try:
        response = await httpx.get(f"{url}/agent-card")
        return response.status_code == 200
    except:
        return False
```

### Test Skill Execution

```python
async def test_skill(agent_url, skill_id, test_params):
    request = {
        "jsonrpc": "2.0",
        "method": skill_id,
        "params": test_params,
        "id": "test"
    }

    response = await httpx.post(f"{agent_url}/execute", json=request)
    result = response.json()

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Success: {result['result']}")
```

### Monitor Workflow Execution

```python
class DebugOrchestrator:
    async def execute(self, workflow):
        for step in workflow:
            print(f"Executing: {step}")
            start = time.time()
            result = await call_agent(step)
            duration = time.time() - start
            print(f"  Result: {result[:100]}...")
            print(f"  Duration: {duration:.2f}s")
```

## 🚨 Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Agent not running | Start agent, check port |
| `Method not found` | Wrong skill ID | Check agent card for correct ID |
| `Invalid parameters` | Schema mismatch | Verify input against schema |
| `Timeout` | Slow processing | Increase timeout, optimize agent |
| `Registry not found` | Registry down | Start registry, check URL |
| `ORAS command failed` | ORAS not installed | Install ORAS CLI |
| `Agent card not found` | Not published | Push agent card to registry |
| `Circuit breaker open` | Too many failures | Fix underlying issue, wait for reset |

## 🎯 Production Checklist

### Agent Checklist
- [ ] Health endpoint implemented
- [ ] Metrics endpoint implemented
- [ ] Error handling comprehensive
- [ ] Logging configured
- [ ] Input validation strict
- [ ] Timeouts configured
- [ ] Rate limiting implemented
- [ ] Authentication added
- [ ] Tests written
- [ ] Documentation complete

### Registry Checklist
- [ ] Registry running with persistence
- [ ] Backup strategy defined
- [ ] Access control configured
- [ ] TLS/SSL enabled
- [ ] Monitoring setup
- [ ] Retention policy defined

### Orchestrator Checklist
- [ ] Discovery caching enabled
- [ ] Retry logic implemented
- [ ] Circuit breakers configured
- [ ] Metrics collection active
- [ ] Tracing enabled
- [ ] Error recovery defined
- [ ] Load testing completed
- [ ] Scaling configured

## 📚 Essential Code Snippets

### Complete Agent Call Function

```python
async def call_agent(url, skill_id, params, timeout=30):
    """Complete agent call with error handling"""
    async with httpx.AsyncClient(timeout=timeout) as client:
        request = {
            "jsonrpc": "2.0",
            "method": skill_id,
            "params": params,
            "id": str(uuid.uuid4())
        }

        try:
            response = await client.post(f"{url}/execute", json=request)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise RuntimeError(f"Agent error: {result['error']}")

            return result.get("result")

        except httpx.TimeoutException:
            raise TimeoutError(f"Agent {url} timed out")
        except httpx.RequestError as e:
            raise ConnectionError(f"Failed to reach {url}: {e}")
```

### Registry Discovery Function

```python
def discover_agent(skill_id, registry_url="localhost:5000"):
    """Discover agent by skill ID"""
    import subprocess
    import json
    import tempfile

    # Get all repositories
    response = httpx.get(f"http://{registry_url}/v2/_catalog")
    repos = response.json().get("repositories", [])

    for repo in repos:
        if not repo.startswith("agents/"):
            continue

        # Pull agent card
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = ["oras", "pull", f"{registry_url}/{repo}:latest", "-o", tmpdir]
            subprocess.run(cmd, capture_output=True, check=True)

            # Read agent card
            for file in Path(tmpdir).glob("*.json"):
                with open(file) as f:
                    card = json.load(f)

                # Check skills
                for skill in card.get("skills", []):
                    if skill["id"] == skill_id:
                        return card["url"]

    return None
```

### Workflow Executor

```python
async def execute_workflow(steps):
    """Execute workflow steps"""
    context = {}

    for step in steps:
        try:
            if step["type"] == "sequential":
                result = await sequential_execution(step["agents"], context)
            elif step["type"] == "parallel":
                result = await parallel_execution(step["agents"], context)
            elif step["type"] == "conditional":
                result = await conditional_execution(step["rules"], context)

            context[step["name"]] = result

        except Exception as e:
            print(f"Step {step['name']} failed: {e}")
            if step.get("required", True):
                raise

    return context
```

## 🔗 Useful Links

- [Google A2A Protocol](https://github.com/google-research/android_world/blob/main/android_world/a2a_protocol.md)
- [ORAS Documentation](https://oras.land/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Registry](https://docs.docker.com/registry/)
- [JSON-RPC 2.0 Spec](https://www.jsonrpc.org/specification)

## 💡 Pro Tips

1. **Start Simple**: Begin with one agent, one skill, then expand
2. **Use Docker Compose**: Manage multi-agent systems easily
3. **Cache Discovery**: Don't query registry on every request
4. **Version Everything**: Agent cards, workflows, and schemas
5. **Monitor Early**: Add metrics from the start
6. **Test in Isolation**: Test agents individually before orchestrating
7. **Document Skills**: Clear descriptions help discovery and usage
8. **Plan for Failure**: Every agent call can fail - handle it
9. **Use Types**: Type hints and schemas prevent errors
10. **Keep Agents Stateless**: Easier to scale and replace

---

**Remember**: The A2A pattern is about **composition**, not complexity. Build simple agents that do one thing well, then orchestrate them into powerful workflows!