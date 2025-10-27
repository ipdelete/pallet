# Part 2: Core Workflow Engine (Execution Patterns)

**Status**: 🔴 Not Started | **Depends On**: Part 1 (Data Models) | **Testing**: Unit + Integration tests

## Overview

This part implements the core workflow engine that executes workflows using different patterns (sequential, parallel, conditional, switch). It integrates with the existing agent discovery system and handles step execution.

## Scope

### In Scope
- WorkflowEngine class
- Sequential execution (existing Plan → Build → Test pattern)
- Parallel execution (multiple agents simultaneously)
- Conditional execution (if/else branching)
- Switch execution (route based on value)
- Agent discovery integration per step
- Timeout handling per step
- Basic error handling

### Out of Scope
- Registry push/pull (Part 3)
- Orchestrator refactoring (Part 4)
- Example workflow YAML files (Part 4)

## Prerequisites

✅ Part 1 must be completed:
- `WorkflowDefinition`, `WorkflowStep`, `WorkflowContext` models exist
- `load_workflow_from_yaml()` function works
- Template resolution (`resolve_expression()`) works
- All Part 1 tests pass

## Implementation Tasks

### 1. Create WorkflowEngine Class
**File**: `src/workflow_engine.py` (extend existing file)

```python
import asyncio
import httpx
from typing import Dict, Any, Optional
from src.discovery import discover_agent_for_skill  # Existing function

class WorkflowEngine:
    """Executes workflows with support for multiple execution patterns."""

    def __init__(self):
        """Initialize workflow engine."""
        self.agent_cache = {}  # {skill_id: agent_url}

    async def discover_agent_for_skill(self, skill_id: str) -> str:
        """
        Discover agent URL for a skill (with caching).

        Args:
            skill_id: Skill identifier

        Returns:
            Agent URL

        Raises:
            ValueError: If skill not found
        """
        if skill_id in self.agent_cache:
            return self.agent_cache[skill_id]

        # Use existing discovery module
        agent_url = await discover_agent_for_skill(skill_id)
        if not agent_url:
            raise ValueError(f"No agent found for skill: {skill_id}")

        self.agent_cache[skill_id] = agent_url
        return agent_url

    async def call_agent_skill(
        self,
        agent_url: str,
        skill_id: str,
        params: Dict[str, Any],
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Call an agent skill via JSON-RPC.

        Args:
            agent_url: Agent URL (e.g., http://localhost:8001)
            skill_id: Skill ID to execute
            params: Skill parameters
            timeout: Timeout in seconds

        Returns:
            Skill result

        Raises:
            httpx.TimeoutException: If request times out
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{agent_url}/execute",
                json={
                    "jsonrpc": "2.0",
                    "method": skill_id,
                    "params": params,
                    "id": "1"
                }
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise RuntimeError(f"Agent error: {result['error']}")

            return result.get("result", {})
```

**Tests**: `tests/unit/test_workflow_engine.py`
- Test `discover_agent_for_skill()` with mocked discovery
- Test agent caching (second call doesn't hit discovery)
- Test `call_agent_skill()` with mocked HTTP response
- Test timeout handling
- Test error response handling

### 2. Implement Step Execution
**File**: `src/workflow_engine.py`

```python
    async def execute_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """
        Execute a single workflow step.

        Args:
            step: WorkflowStep to execute
            context: Current workflow context

        Returns:
            Step result

        Raises:
            ValueError: If agent not found for skill
            RuntimeError: If step execution fails
        """
        print(f"[WorkflowEngine] Executing step: {step.id} (skill: {step.skill})")

        # Resolve input templates
        resolved_inputs = context.resolve_inputs(step.inputs)

        # Discover agent for skill
        agent_url = await self.discover_agent_for_skill(step.skill)

        # Call agent
        try:
            result = await self.call_agent_skill(
                agent_url=agent_url,
                skill_id=step.skill,
                params=resolved_inputs,
                timeout=step.timeout or 300
            )

            print(f"[WorkflowEngine] Step {step.id} completed successfully")
            return result

        except asyncio.TimeoutError:
            raise RuntimeError(f"Step {step.id} timed out after {step.timeout}s")
        except Exception as e:
            raise RuntimeError(f"Step {step.id} failed: {str(e)}")
```

**Tests**: `tests/unit/test_workflow_engine.py`
- Test `execute_step()` with mocked agent call
- Test input template resolution during step execution
- Test timeout raises RuntimeError
- Test agent error raises RuntimeError
- Test successful step execution flow

### 3. Implement Sequential Execution
**File**: `src/workflow_engine.py`

```python
    async def execute_sequential_steps(
        self,
        steps: List[WorkflowStep],
        context: WorkflowContext
    ) -> WorkflowContext:
        """
        Execute steps sequentially in order.

        Args:
            steps: List of steps to execute
            context: Workflow context

        Returns:
            Updated context with all step outputs
        """
        for step in steps:
            result = await self.execute_step(step, context)

            # Store output in context
            if step.outputs:
                context.set_step_output(step.id, {step.outputs: result})
            else:
                context.set_step_output(step.id, result)

        return context
```

**Tests**: `tests/unit/test_workflow_engine.py`
- Test sequential execution with 3 mocked steps
- Test data flows from step N to step N+1
- Test context is updated after each step
- Test error in step 2 stops execution

### 4. Implement Parallel Execution
**File**: `src/workflow_engine.py`

```python
    async def execute_parallel_steps(
        self,
        steps: List[WorkflowStep],
        context: WorkflowContext
    ) -> WorkflowContext:
        """
        Execute steps in parallel using asyncio.gather.

        Args:
            steps: List of steps to execute concurrently
            context: Workflow context

        Returns:
            Updated context with all step outputs
        """
        print(f"[WorkflowEngine] Executing {len(steps)} steps in parallel")

        # Execute all steps concurrently
        tasks = [self.execute_step(step, context) for step in steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Store results in context
        for step, result in zip(steps, results):
            if isinstance(result, Exception):
                raise RuntimeError(f"Step {step.id} failed: {result}")

            if step.outputs:
                context.set_step_output(step.id, {step.outputs: result})
            else:
                context.set_step_output(step.id, result)

        print(f"[WorkflowEngine] All parallel steps completed")
        return context
```

**Tests**: `tests/unit/test_workflow_engine.py`
- Test parallel execution with 3 mocked steps
- Test all steps execute concurrently (verify asyncio.gather called)
- Test all results stored in context
- Test one failure raises RuntimeError
- Test execution time is ~max(step_times), not sum

### 5. Implement Conditional Execution
**File**: `src/workflow_engine.py`

```python
    async def execute_conditional_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> WorkflowContext:
        """
        Execute conditional step (if/else branching).

        Step.branches format:
        {
            "if_true": [WorkflowStep, ...],
            "if_false": [WorkflowStep, ...]
        }

        Step.condition is evaluated as template expression.

        Args:
            step: Conditional step
            context: Workflow context

        Returns:
            Updated context
        """
        if not step.condition:
            raise ValueError(f"Conditional step {step.id} missing condition")

        if not step.branches:
            raise ValueError(f"Conditional step {step.id} missing branches")

        # Evaluate condition
        condition_result = context.resolve_expression(step.condition)

        # Determine which branch to execute
        if condition_result:
            branch_steps = step.branches.get("if_true", [])
            print(f"[WorkflowEngine] Condition true, executing if_true branch ({len(branch_steps)} steps)")
        else:
            branch_steps = step.branches.get("if_false", [])
            print(f"[WorkflowEngine] Condition false, executing if_false branch ({len(branch_steps)} steps)")

        # Execute branch
        for branch_step_data in branch_steps:
            branch_step = WorkflowStep(**branch_step_data)
            result = await self.execute_step(branch_step, context)
            context.set_step_output(branch_step.id, result)

        return context
```

**Tests**: `tests/unit/test_workflow_engine.py`
- Test conditional with true condition executes if_true branch
- Test conditional with false condition executes if_false branch
- Test missing condition raises ValueError
- Test missing branches raises ValueError
- Test branch steps are executed correctly

### 6. Implement Switch Execution
**File**: `src/workflow_engine.py`

```python
    async def execute_switch_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext
    ) -> WorkflowContext:
        """
        Execute switch step (route based on value).

        Step.condition contains the expression to evaluate.
        Step.branches format:
        {
            "case_value_1": [WorkflowStep, ...],
            "case_value_2": [WorkflowStep, ...],
            "default": [WorkflowStep, ...]
        }

        Args:
            step: Switch step
            context: Workflow context

        Returns:
            Updated context
        """
        if not step.condition:
            raise ValueError(f"Switch step {step.id} missing condition expression")

        if not step.branches:
            raise ValueError(f"Switch step {step.id} missing branches")

        # Evaluate switch expression
        switch_value = context.resolve_expression(step.condition)
        print(f"[WorkflowEngine] Switch evaluated to: {switch_value}")

        # Find matching case
        matched_case = str(switch_value)  # Convert to string for dict lookup
        branch_steps = step.branches.get(matched_case) or step.branches.get("default", [])

        if not branch_steps:
            print(f"[WorkflowEngine] No matching case for '{switch_value}', skipping")
            return context

        print(f"[WorkflowEngine] Executing case '{matched_case}' ({len(branch_steps)} steps)")

        # Execute matched branch
        for branch_step_data in branch_steps:
            branch_step = WorkflowStep(**branch_step_data)
            result = await self.execute_step(branch_step, context)
            context.set_step_output(branch_step.id, result)

        return context
```

**Tests**: `tests/unit/test_workflow_engine.py`
- Test switch matches correct case
- Test switch falls back to default case
- Test switch with no match and no default skips execution
- Test missing condition raises ValueError
- Test missing branches raises ValueError

### 7. Implement Main Workflow Execution
**File**: `src/workflow_engine.py`

```python
    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_input: Dict[str, Any]
    ) -> WorkflowContext:
        """
        Execute a complete workflow.

        Args:
            workflow: WorkflowDefinition to execute
            initial_input: Initial input data

        Returns:
            Final workflow context with all step outputs
        """
        print(f"[WorkflowEngine] Starting workflow: {workflow.metadata.name}")
        print(f"[WorkflowEngine] Workflow ID: {workflow.metadata.id}")
        print(f"[WorkflowEngine] Steps: {len(workflow.steps)}")

        # Initialize context
        context = WorkflowContext(initial_input)

        # Execute steps
        for step in workflow.steps:
            print(f"\n[WorkflowEngine] Processing step: {step.id} (type: {step.step_type})")

            if step.step_type == StepType.SEQUENTIAL:
                result = await self.execute_step(step, context)
                context.set_step_output(step.id, result)

            elif step.step_type == StepType.PARALLEL:
                # For parallel, step.branches should contain list of steps
                if not step.branches or "steps" not in step.branches:
                    raise ValueError(f"Parallel step {step.id} missing 'steps' in branches")
                parallel_steps = [WorkflowStep(**s) for s in step.branches["steps"]]
                await self.execute_parallel_steps(parallel_steps, context)

            elif step.step_type == StepType.CONDITIONAL:
                await self.execute_conditional_step(step, context)

            elif step.step_type == StepType.SWITCH:
                await self.execute_switch_step(step, context)

            else:
                raise ValueError(f"Unknown step type: {step.step_type}")

        print(f"\n[WorkflowEngine] Workflow completed: {workflow.metadata.name}")
        return context
```

**Tests**: `tests/unit/test_workflow_engine.py`
- Test `execute_workflow()` with all sequential steps
- Test workflow with mixed step types
- Test workflow initialization and completion
- Test unknown step type raises ValueError
- Test context contains all step outputs at end

## Test Files

### `tests/unit/test_workflow_engine.py`

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.workflow_engine import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowContext,
    WorkflowMetadata,
    StepType,
)

@pytest.fixture
def mock_agent_discovery():
    """Mock agent discovery function."""
    with patch('src.workflow_engine.discover_agent_for_skill') as mock:
        mock.return_value = "http://localhost:8001"
        yield mock

@pytest.fixture
def workflow_engine():
    """WorkflowEngine instance."""
    return WorkflowEngine()

class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_discover_agent_with_caching(self, workflow_engine, mock_agent_discovery):
        """Test agent discovery caches results."""
        url1 = await workflow_engine.discover_agent_for_skill("test_skill")
        url2 = await workflow_engine.discover_agent_for_skill("test_skill")

        assert url1 == "http://localhost:8001"
        assert url2 == "http://localhost:8001"
        mock_agent_discovery.assert_called_once()  # Only called once due to caching

    @pytest.mark.asyncio
    async def test_call_agent_skill_success(self, workflow_engine):
        """Test successful agent skill call."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"jsonrpc": "2.0", "result": {"output": "test"}, "id": "1"}
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await workflow_engine.call_agent_skill(
                "http://localhost:8001",
                "test_skill",
                {"input": "test"},
                timeout=30
            )

            assert result == {"output": "test"}

    @pytest.mark.asyncio
    async def test_execute_step_success(self, workflow_engine, mock_agent_discovery):
        """Test single step execution."""
        step = WorkflowStep(id="step1", skill="test_skill", inputs={"input": "test"})
        context = WorkflowContext({"initial": "data"})

        with patch.object(workflow_engine, 'call_agent_skill', AsyncMock(return_value={"result": "output"})):
            result = await workflow_engine.execute_step(step, context)

            assert result == {"result": "output"}

    @pytest.mark.asyncio
    async def test_execute_sequential_steps(self, workflow_engine, mock_agent_discovery):
        """Test sequential execution of multiple steps."""
        steps = [
            WorkflowStep(id="step1", skill="skill1", outputs="result1"),
            WorkflowStep(id="step2", skill="skill2", inputs={"data": "{{ steps.step1.outputs.result1 }}"}, outputs="result2"),
        ]
        context = WorkflowContext({})

        with patch.object(workflow_engine, 'call_agent_skill', AsyncMock(side_effect=[
            {"data": "step1_output"},
            {"data": "step2_output"}
        ])):
            result_context = await workflow_engine.execute_sequential_steps(steps, context)

            assert "step1" in result_context.step_outputs
            assert "step2" in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_execute_parallel_steps(self, workflow_engine, mock_agent_discovery):
        """Test parallel execution."""
        steps = [
            WorkflowStep(id="step1", skill="skill1"),
            WorkflowStep(id="step2", skill="skill2"),
            WorkflowStep(id="step3", skill="skill3"),
        ]
        context = WorkflowContext({})

        with patch.object(workflow_engine, 'call_agent_skill', AsyncMock(return_value={"result": "output"})):
            result_context = await workflow_engine.execute_parallel_steps(steps, context)

            assert len(result_context.step_outputs) == 3

    @pytest.mark.asyncio
    async def test_execute_conditional_true_branch(self, workflow_engine, mock_agent_discovery):
        """Test conditional execution (true branch)."""
        step = WorkflowStep(
            id="conditional",
            skill="conditional_skill",
            step_type=StepType.CONDITIONAL,
            condition="{{ workflow.input.flag }}",
            branches={
                "if_true": [{"id": "true_step", "skill": "true_skill"}],
                "if_false": [{"id": "false_step", "skill": "false_skill"}]
            }
        )
        context = WorkflowContext({"flag": True})

        with patch.object(workflow_engine, 'call_agent_skill', AsyncMock(return_value={"result": "true_output"})):
            result_context = await workflow_engine.execute_conditional_step(step, context)

            assert "true_step" in result_context.step_outputs
            assert "false_step" not in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_execute_switch_step(self, workflow_engine, mock_agent_discovery):
        """Test switch execution."""
        step = WorkflowStep(
            id="switch",
            skill="switch_skill",
            step_type=StepType.SWITCH,
            condition="{{ workflow.input.type }}",
            branches={
                "type_a": [{"id": "step_a", "skill": "skill_a"}],
                "type_b": [{"id": "step_b", "skill": "skill_b"}],
                "default": [{"id": "step_default", "skill": "skill_default"}]
            }
        )
        context = WorkflowContext({"type": "type_a"})

        with patch.object(workflow_engine, 'call_agent_skill', AsyncMock(return_value={"result": "output"})):
            result_context = await workflow_engine.execute_switch_step(step, context)

            assert "step_a" in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_execute_workflow_full(self, workflow_engine, mock_agent_discovery):
        """Test full workflow execution."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test", name="Test", version="1.0.0"),
            steps=[
                WorkflowStep(id="step1", skill="skill1", outputs="result1"),
                WorkflowStep(id="step2", skill="skill2", inputs={"data": "{{ steps.step1.outputs.result1 }}"})
            ]
        )

        with patch.object(workflow_engine, 'call_agent_skill', AsyncMock(side_effect=[
            {"data": "step1_output"},
            {"data": "step2_output"}
        ])):
            result_context = await workflow_engine.execute_workflow(workflow, {"initial": "input"})

            assert "step1" in result_context.step_outputs
            assert "step2" in result_context.step_outputs
```

### `tests/integration/test_workflow_execution.py` (new file)

```python
import pytest
import asyncio
from src.workflow_engine import WorkflowEngine, load_workflow_from_yaml
from unittest.mock import AsyncMock, patch

class TestWorkflowIntegration:
    @pytest.mark.asyncio
    async def test_sequential_workflow_with_mocked_agents(self):
        """Test sequential workflow with mocked agent calls."""
        yaml_content = """
metadata:
  id: test-sequential
  name: Test Sequential
  version: 1.0.0
steps:
  - id: step1
    skill: create_plan
    inputs:
      requirements: "{{ workflow.input.requirements }}"
    outputs: plan
  - id: step2
    skill: generate_code
    inputs:
      plan: "{{ steps.step1.outputs.plan }}"
    outputs: code
"""
        workflow = load_workflow_from_yaml(yaml_content)
        engine = WorkflowEngine()

        with patch('src.workflow_engine.discover_agent_for_skill', return_value="http://localhost:8001"):
            with patch.object(engine, 'call_agent_skill', AsyncMock(side_effect=[
                {"plan_data": "structured plan"},
                {"code": "def test(): pass"}
            ])):
                context = await engine.execute_workflow(workflow, {"requirements": "test requirement"})

                assert "step1" in context.step_outputs
                assert "step2" in context.step_outputs
                assert context.step_outputs["step1"]["outputs"]["plan"]["plan_data"] == "structured plan"

    # More integration tests...
```

## Acceptance Criteria

- [ ] `WorkflowEngine` class implemented with agent discovery caching
- [ ] `execute_step()` resolves templates and calls agents
- [ ] `execute_sequential_steps()` runs steps in order
- [ ] `execute_parallel_steps()` runs steps concurrently with asyncio.gather
- [ ] `execute_conditional_step()` evaluates conditions and executes correct branch
- [ ] `execute_switch_step()` routes to correct case based on value
- [ ] `execute_workflow()` dispatches to correct execution method based on step type
- [ ] Timeout handling works per step
- [ ] Agent discovery is cached
- [ ] All unit tests pass: `uv run pytest tests/unit/test_workflow_engine.py -v`
- [ ] Integration tests pass: `uv run pytest tests/integration/test_workflow_execution.py -v`
- [ ] Code coverage >85% for engine code: `uv run pytest tests/unit/test_workflow_engine.py --cov=src.workflow_engine --cov-report=term-missing`
- [ ] No linting errors: `uv run invoke lint.black-check && uv run invoke lint.flake8`
- [ ] All existing tests still pass: `uv run invoke test`

## Validation Commands

```bash
# 1. Verify Python syntax
python -c "import ast; ast.parse(open('src/workflow_engine.py').read())"

# 2. Verify imports work
python -c "from src.workflow_engine import WorkflowEngine; print('✓ WorkflowEngine imported')"

# 3. Run unit tests for workflow engine
uv run pytest tests/unit/test_workflow_engine.py -v

# 4. Run integration tests
uv run pytest tests/integration/test_workflow_execution.py -v

# 5. Check coverage
uv run pytest tests/unit/test_workflow_engine.py tests/integration/test_workflow_execution.py --cov=src.workflow_engine --cov-report=term-missing --cov-report=html

# 6. Verify no regressions
uv run invoke test

# 7. Lint checks
uv run invoke lint.black-check
uv run invoke lint.flake8

# 8. Manual test of engine (after agents are running)
python -c "
import asyncio
from src.workflow_engine import WorkflowEngine, load_workflow_from_yaml

async def test():
    # Create simple workflow
    yaml_str = '''
metadata:
  id: test
  name: Test
  version: 1.0.0
steps:
  - id: step1
    skill: create_plan
    inputs:
      requirements: \"{{ workflow.input.requirements }}\"
'''
    workflow = load_workflow_from_yaml(yaml_str)
    engine = WorkflowEngine()
    print(f'✓ Engine created, workflow loaded')
    print(f'✓ Workflow: {workflow.metadata.name}')
    print(f'✓ Steps: {len(workflow.steps)}')

asyncio.run(test())
"
```

## Next Steps

After completing Part 2 and all tests pass:
- ✅ Proceed to **Part 3: Registry Integration** (workflow storage/discovery)
- Part 3 will use WorkflowEngine to load and execute workflows from registry
