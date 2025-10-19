# YAML to Execution: Complete Workflow Engine Walkthrough

This document provides a detailed walkthrough of how YAML workflow definitions are converted into executable code through the workflow engine.

## Table of Contents

1. [The YAML File](#the-yaml-file)
2. [Parse YAML → Pydantic Models](#parse-yaml--pydantic-models)
3. [Discover Workflow from Registry](#discover-workflow-from-registry)
4. [Initialize Workflow Context](#initialize-workflow-context)
5. [Execute Steps](#execute-steps)
6. [Template Resolution](#template-resolution)
7. [Agent Discovery](#agent-discovery)
8. [Agent Invocation](#agent-invocation)
9. [Store Output in Context](#store-output-in-context)
10. [Next Step Uses Previous Output](#next-step-uses-previous-output)
11. [Complete Data Flow](#complete-data-flow)
12. [Key Design Patterns](#key-design-patterns)

---

## The YAML File

**Location:** `workflows/code-generation.yaml`

```yaml
metadata:
  id: code-generation-v1
  name: Code Generation Pipeline
  version: 1.0.0
  description: "Plan → Build → Test pipeline for code generation"
  tags:
    - code-generation
    - sequential
    - default

steps:
  - id: plan
    skill: create_plan
    inputs:
      requirements: "{{ workflow.input.requirements }}"
    outputs: result
    timeout: 300
    step_type: sequential

  - id: build
    skill: generate_code
    inputs:
      plan: "{{ steps.plan.outputs.result }}"
    outputs: result
    timeout: 600
    step_type: sequential

  - id: test
    skill: review_code
    inputs:
      code: "{{ steps.build.outputs.result.code }}"
      language: "{{ steps.build.outputs.result.language }}"
    outputs: result
    timeout: 300
    step_type: sequential
```

This is declarative data that defines:
- **Metadata:** Workflow identity and version
- **Steps:** Sequential execution with template expressions for data flow
- **Templates:** `{{ workflow.input.requirements }}` creates dynamic data binding

---

## Parse YAML → Pydantic Models

**Source:** `src/workflow_engine.py:148-174`

```python
def load_workflow_from_yaml(yaml_content: Union[str, Path]) -> WorkflowDefinition:
    """Load and validate a workflow from YAML content or file path."""

    if isinstance(yaml_content, Path) or (...):
        with open(yaml_content, "r") as f:
            data = yaml.safe_load(f)  # YAML → Python dict
    else:
        data = yaml.safe_load(yaml_content)

    return WorkflowDefinition(**data)  # Pydantic validation!
```

**What happens:**

1. **yaml.safe_load()** converts YAML string → Python dict
2. **Pydantic validates** the dict against model schemas:
   - `WorkflowMetadata` - validates `id`, `name`, `version`
   - `WorkflowStep` - validates each step (id, skill, inputs, outputs, etc.)
   - `WorkflowDefinition` - ensures overall structure is correct

**Result:** Type-safe Python objects instead of raw dicts

### Data Models

**StepType Enum** - Execution patterns:
```python
class StepType(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    SWITCH = "switch"
```

**WorkflowStep** - Individual step:
```python
class WorkflowStep(BaseModel):
    id: str  # Unique step identifier
    skill: str  # Skill ID to execute
    inputs: Dict[str, Any] = Field(default_factory=dict)  # Can contain templates
    outputs: Optional[str] = None  # Output variable name
    timeout: Optional[int] = 300  # Timeout in seconds
    step_type: StepType = StepType.SEQUENTIAL  # Execution pattern
    condition: Optional[str] = None  # For conditional/switch
    branches: Optional[Dict[str, Any]] = None  # For conditional/switch/parallel
```

**WorkflowMetadata** - Workflow identity:
```python
class WorkflowMetadata(BaseModel):
    id: str
    name: str
    version: str
    description: str = ""
    tags: List[str] = []
```

**WorkflowDefinition** - Complete workflow:
```python
class WorkflowDefinition(BaseModel):
    metadata: WorkflowMetadata
    steps: List[WorkflowStep]
    error_handling: Optional[Dict[str, Any]] = None
```

---

## Discover Workflow from Registry

**Source:** `src/discovery.py:358-406` and `src/orchestrator.py:134-143`

```python
# From orchestrator.py
logger.info(f"Discovering workflow: {workflow_id}:{version}")
workflow = await discover_workflow(workflow_id, version)
if not workflow:
    raise ValueError(f"Workflow not found: {workflow_id}:{version}")

logger.info(f"Loaded workflow: {workflow.metadata.name} (v{workflow.metadata.version})")
```

**Discovery process:**

1. **User requests workflow** via CLI: `python main.py --workflow code-generation-v1`
2. **Check cache** in memory for previously loaded workflows
3. **Pull from OCI registry** via ORAS if not cached:
   - `oras pull localhost:5000/workflows/code-generation:v1 -o /tmp/xyz123/`
4. **Convert YAML** from temp directory to `WorkflowDefinition` object
5. **Cache result** in memory for future use

### Discovery Function

From `src/discovery.py:358-406`:

```python
async def discover_workflow(
    workflow_id: str, version: str = "v1"
) -> Optional["WorkflowDefinition"]:
    """Discover and load a workflow from the registry."""

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
```

---

## Initialize Workflow Context

**Source:** `src/workflow_engine.py:454-476`

```python
async def execute_workflow(
    self, workflow: WorkflowDefinition, initial_input: Dict[str, Any]
) -> WorkflowContext:
    """Execute a complete workflow."""

    workflow_start = time.time()
    logger.info(f"Starting workflow: {workflow.metadata.name}")

    # Initialize context
    context = WorkflowContext(initial_input)
```

**WorkflowContext** - Execution state holder:

```python
class WorkflowContext:
    """Manages workflow execution state and template resolution."""

    def __init__(self, initial_input: Dict[str, Any]):
        self.workflow_input = initial_input  # Original input
        self.step_outputs = {}  # {step_id: {outputs: {...}}}

    def set_step_output(self, step_id: str, output: Dict[str, Any]) -> None:
        """Store output from a completed step."""
        self.step_outputs[step_id] = {"outputs": output}
```

**Example initialization:**

When calling:
```bash
python main.py "Create a factorial function"
```

Context starts with:
```python
context.workflow_input = {"requirements": "Create a factorial function"}
context.step_outputs = {}  # Empty, will be filled as steps complete
```

---

## Execute Steps

**Source:** `src/workflow_engine.py:480-521`

The orchestrator loops through each step:

```python
for step in workflow.steps:
    logger.info(f"Processing step: {step.id} (type: {step.step_type})")
    step_start = time.time()

    try:
        if step.step_type == StepType.SEQUENTIAL:
            result = await self.execute_step(step, context)
            # Store output
            context.set_step_output(step.id, {...})
        elif step.step_type == StepType.PARALLEL:
            # Execute multiple steps concurrently
            ...
        elif step.step_type == StepType.CONDITIONAL:
            # if/else branching
            ...
        elif step.step_type == StepType.SWITCH:
            # switch/case routing
            ...
```

### Execute Single Step

**Source:** `src/workflow_engine.py:250-290`

```python
async def execute_step(self, step: WorkflowStep, context: WorkflowContext):
    print(f"[WorkflowEngine] Executing step: {step.id} (skill: {step.skill})")

    # 1. RESOLVE TEMPLATES
    resolved_inputs = context.resolve_inputs(step.inputs)

    # 2. DISCOVER AGENT
    agent_url = await self.discover_agent_for_skill(step.skill)

    # 3. CALL AGENT
    result = await self.call_agent_skill(
        agent_url=agent_url,
        skill_id=step.skill,
        params=resolved_inputs,
        timeout=step.timeout or 300,
    )

    return result
```

---

## Template Resolution

**Source:** `src/workflow_engine.py:87-128` and `130-145`

This is where the magic happens. The YAML has template expressions that are resolved at execution time:

```yaml
- id: plan
  inputs:
    requirements: "{{ workflow.input.requirements }}"

- id: build
  inputs:
    plan: "{{ steps.plan.outputs.result }}"
```

### resolve_inputs Method

```python
def resolve_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve all template expressions in an inputs dict."""
    resolved = {}
    for key, value in inputs.items():
        if isinstance(value, str):
            resolved[key] = self.resolve_expression(value)  # ← Process templates
        elif isinstance(value, dict):
            resolved[key] = self.resolve_inputs(value)  # Recurse
        elif isinstance(value, list):
            resolved[key] = [
                self.resolve_expression(v) if isinstance(v, str) else v
                for v in value
            ]
        else:
            resolved[key] = value
    return resolved
```

### resolve_expression Method

```python
def resolve_expression(self, expression: str) -> Any:
    """Resolve a template expression like {{ steps.plan.outputs.result }}."""

    if not isinstance(expression, str):
        return expression

    # Extract {{ ... }} pattern
    match = re.match(r"{{\\s*(.+?)\\s*}}", expression.strip())
    if not match:
        return expression  # Not a template, return as-is

    path = match.group(1).split(".")  # "workflow.input.requirements" → ["workflow", "input", "requirements"]

    # Resolve path in context
    if path[0] == "workflow" and path[1] == "input":
        data = self.workflow_input  # Gets the initial input dict
        path = path[2:]  # Skip 'workflow.input'
    elif path[0] == "steps":
        step_id = path[1]
        if step_id not in self.step_outputs:
            return None
        data = self.step_outputs[step_id]  # Gets previous step output
        path = path[2:]  # Skip 'steps.step_id'
    else:
        return None

    # Navigate nested path
    for key in path:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None

    return data
```

### Template Resolution Examples

**Step 1 (plan) - Access workflow input:**

| Input | Processing | Result |
|-------|-----------|--------|
| Template: `"{{ workflow.input.requirements }}"` | Extract path | `["workflow", "input", "requirements"]` |
| Access `self.workflow_input` | `{"requirements": "Create a factorial function"}` | Navigate path → `"Create a factorial function"` |
| **Resolved input to agent:** | `{"requirements": "Create a factorial function"}` | Ready to send! |

**Step 2 (build) - Access previous step output:**

```yaml
- id: build
  inputs:
    plan: "{{ steps.plan.outputs.result }}"
```

| Input | Processing | Result |
|-------|-----------|--------|
| Template: `"{{ steps.plan.outputs.result }}"` | Extract path | `["steps", "plan", "outputs", "result"]` |
| Access `self.step_outputs["plan"]` | `{"outputs": {"result": {...}}}` | Navigate path → plan result object |
| **Resolved input to agent:** | `{"plan": {...plan object...}}` | Agent gets plan from previous step! |

### Template Syntax

Supported templates:
- `{{ workflow.input.field }}` - Access workflow input
- `{{ workflow.input.nested.path }}` - Access nested input
- `{{ steps.step_id.outputs.field }}` - Access step output
- `{{ steps.step_id.outputs.nested.path }}` - Access nested output

---

## Agent Discovery

**Source:** `src/workflow_engine.py:184-207`

```python
async def discover_agent_for_skill(self, skill_id: str) -> str:
    """Discover agent URL for a skill (with caching)."""

    if skill_id in self.agent_cache:
        return self.agent_cache[skill_id]

    # Use existing discovery module (run in thread pool since it's sync)
    loop = asyncio.get_event_loop()
    agent_url = await loop.run_in_executor(None, discover_agent, skill_id)
    if not agent_url:
        raise ValueError(f"No agent found for skill: {skill_id}")

    self.agent_cache[skill_id] = agent_url
    return agent_url
```

**Discovery results:**

- `skill_id = "create_plan"` → discovers → `"http://localhost:8001"`
- `skill_id = "generate_code"` → discovers → `"http://localhost:8002"`
- `skill_id = "review_code"` → discovers → `"http://localhost:8003"`

Discovery uses the registry-based lookup from `src/discovery.py` with fallback to known hardcoded ports.

---

## Agent Invocation

**Source:** `src/workflow_engine.py:209-248`

```python
async def call_agent_skill(
    self,
    agent_url: str,
    skill_id: str,
    params: Dict[str, Any],
    timeout: int = 300,
) -> Dict[str, Any]:
    """Call an agent skill via JSON-RPC."""

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{agent_url}/execute",
            json={
                "jsonrpc": "2.0",
                "method": skill_id,
                "params": params,  # ← Resolved inputs go here!
                "id": "1",
            },
        )
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise RuntimeError(f"Agent error: {result['error']}")

        return result.get("result", {})
```

### JSON-RPC Call Example

**For Step 1 (plan):**

```json
POST http://localhost:8001/execute

{
  "jsonrpc": "2.0",
  "method": "create_plan",
  "params": {
    "requirements": "Create a factorial function"
  },
  "id": "1"
}
```

**Agent responds with:**

```json
{
  "result": {
    "title": "Factorial Function Implementation",
    "steps": [...],
    "dependencies": [],
    "estimated_time": "30 minutes"
  }
}
```

---

## Store Output in Context

**Source:** `src/workflow_engine.py:487-492`

Back in `execute_workflow()`:

```python
result = await self.execute_step(step, context)

# Store output in context
if step.outputs:
    context.set_step_output(step.id, {step.outputs: result})
else:
    context.set_step_output(step.id, result)
```

**For step 1:**

```python
context.set_step_output("plan", {"result": {...agent result...}})
```

Now `context.step_outputs` looks like:

```python
{
  "plan": {
    "outputs": {
      "result": {
        "title": "Factorial Function Implementation",
        "steps": [...],
        ...
      }
    }
  }
}
```

---

## Next Step Uses Previous Output

When step 2 (build) executes, it has:

```yaml
inputs:
  plan: "{{ steps.plan.outputs.result }}"
```

**Template resolution process:**

1. **Path:** `["steps", "plan", "outputs", "result"]`
2. **Access:** `context.step_outputs["plan"]["outputs"]["result"]`
3. **Gets:** The plan object from step 1
4. **Sends to agent:** `{"plan": {...}}`

This creates an **implicit data dependency** between steps without hardcoding connections!

---

## Complete Data Flow

```
YAML File (workflows/code-generation.yaml)
    ↓
yaml.safe_load() → Python dict
    ↓
WorkflowDefinition(**data) → Pydantic validation
    ↓
discover_workflow() → Pull from registry, cache
    ↓
WorkflowEngine().execute_workflow()
    ↓
    ├─ Step 1 (plan)
    │  ├─ resolve_inputs: "{{ workflow.input.requirements }}" → "Create factorial function"
    │  ├─ discover_agent: "create_plan" → http://localhost:8001
    │  ├─ call_agent_skill: POST /execute with resolved params
    │  ├─ Agent returns: {title: "...", steps: [...]}
    │  └─ context.set_step_output("plan", {result: {...}})
    │
    ├─ Step 2 (build)
    │  ├─ resolve_inputs: "{{ steps.plan.outputs.result }}" → {title: "...", steps: [...]}
    │  ├─ discover_agent: "generate_code" → http://localhost:8002
    │  ├─ call_agent_skill: POST /execute with plan object
    │  ├─ Agent returns: {code: "def factorial...", language: "python"}
    │  └─ context.set_step_output("build", {result: {...}})
    │
    └─ Step 3 (test)
       ├─ resolve_inputs: "{{ steps.build.outputs.result.code }}" → "def factorial..."
       ├─ discover_agent: "review_code" → http://localhost:8003
       ├─ call_agent_skill: POST /execute with code
       ├─ Agent returns: {quality_score: 95, approved: true}
       └─ context.set_step_output("test", {result: {...}})
    ↓
Return final context with all step outputs
    ↓
save_results() → app/main.py, app/plan.json, app/review.json, app/metadata.json
```

---

## Key Design Patterns

### 1. Immutability & Thread Safety

- `WorkflowContext` maintains state throughout execution
- Each step gets read-only access to previous outputs
- Template expressions are stateless calculations

### 2. Async-First Architecture

- All agent calls are async via `httpx.AsyncClient`
- Parallel steps use `asyncio.gather()`
- Enables efficient resource usage

### 3. Extensibility

- New `StepType` values can be added
- New execution patterns implemented in `WorkflowEngine`
- Agent discovery is pluggable (registry vs. fallback)

### 4. Error Handling

- Step timeout → `RuntimeError`
- Missing agent → `ValueError`
- Agent error response → `RuntimeError`
- Missing template value → `None` (safe default)

### 5. Execution Patterns

#### Sequential
```python
async def execute_sequential_steps(
    self, steps: List[WorkflowStep], context: WorkflowContext
) -> WorkflowContext:
    """Execute steps sequentially in order."""

    for step in steps:
        result = await self.execute_step(step, context)
        context.set_step_output(step.id, {...})

    return context
```

#### Parallel
```python
async def execute_parallel_steps(
    self, steps: List[WorkflowStep], context: WorkflowContext
) -> WorkflowContext:
    """Execute steps in parallel using asyncio.gather."""

    # Create async tasks for all steps
    tasks = [self.execute_step(step, context) for step in steps]

    # Run all concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Store results
    for step, result in zip(steps, results):
        if isinstance(result, Exception):
            raise RuntimeError(f"Step {step.id} failed: {result}")
        context.set_step_output(step.id, result)

    return context
```

#### Conditional
```python
async def execute_conditional_step(
    self, step: WorkflowStep, context: WorkflowContext
) -> WorkflowContext:
    """Execute conditional step (if/else branching)."""

    # Evaluate condition
    condition_result = context.resolve_expression(step.condition)

    # Determine which branch to execute
    if condition_result:
        branch_steps = step.branches.get("if_true", [])
    else:
        branch_steps = step.branches.get("if_false", [])

    # Execute branch
    for branch_step_data in branch_steps:
        branch_step = WorkflowStep(**branch_step_data)
        result = await self.execute_step(branch_step, context)
        context.set_step_output(branch_step.id, result)

    return context
```

#### Switch/Routing
```python
async def execute_switch_step(
    self, step: WorkflowStep, context: WorkflowContext
) -> WorkflowContext:
    """Execute switch step (route based on value)."""

    # Evaluate switch expression
    switch_value = context.resolve_expression(step.condition)

    # Find matching case
    matched_case = str(switch_value)
    branch_steps = step.branches.get(matched_case) or step.branches.get("default", [])

    # Execute matched branch
    for branch_step_data in branch_steps:
        branch_step = WorkflowStep(**branch_step_data)
        result = await self.execute_step(branch_step, context)
        context.set_step_output(branch_step.id, result)

    return context
```

---

## Summary

The workflow engine implements a **declarative, data-driven architecture**:

1. **YAML Definition** - Workflows expressed as metadata + steps with templates
2. **Validation** - Pydantic models ensure type safety and structure correctness
3. **Discovery** - Workflows pulled from OCI registry on-demand with caching
4. **Execution** - WorkflowEngine handles sequential, parallel, conditional, and switch patterns
5. **Data Flow** - Template expressions create implicit dependencies between steps
6. **Agent Integration** - JSON-RPC calls to distributed agents with automatic discovery
7. **Results** - All step outputs stored in context for downstream access

This design decouples workflow definition (YAML) from execution logic (Python), allowing non-developers to compose complex AI agent pipelines through configuration files.
