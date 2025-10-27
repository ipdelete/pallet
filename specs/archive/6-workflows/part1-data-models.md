# Part 1: Data Models & Context (Foundation)

**Status**: 🔴 Not Started | **Depends On**: None | **Testing**: Unit tests only

## Overview

This part implements the foundation layer for the workflow engine: data models, validation, and context management. This is a pure data layer with no external dependencies, making it ideal for TDD.

## Scope

### In Scope
- Pydantic models for workflows (WorkflowDefinition, WorkflowStep, StepType enum)
- WorkflowContext class for managing execution state
- Template expression resolution (`{{ variable.path }}` syntax)
- YAML loading and validation
- Input/output data flow helpers

### Out of Scope
- Agent discovery or execution (Part 2)
- Registry integration (Part 3)
- Orchestrator changes (Part 4)

## Implementation Tasks

### 1. Add Dependencies
**File**: `pyproject.toml`

Add `pyyaml` to dependencies:
```toml
dependencies = [
    ...
    "pyyaml>=6.0",
]
```

**Validation**:
```bash
uv sync
python -c "import yaml; print(f'PyYAML {yaml.__version__}')"
```

### 2. Create StepType Enum
**File**: `src/workflow_engine.py` (new file)

```python
from enum import Enum

class StepType(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    SWITCH = "switch"
```

### 3. Create WorkflowStep Model
**File**: `src/workflow_engine.py`

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

class WorkflowStep(BaseModel):
    """Represents a single step in a workflow."""
    id: str = Field(..., description="Unique step identifier")
    skill: str = Field(..., description="Skill ID to execute")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input parameters (can contain templates)")
    outputs: Optional[str] = Field(None, description="Output variable name")
    timeout: Optional[int] = Field(300, description="Timeout in seconds")
    step_type: StepType = Field(StepType.SEQUENTIAL, description="Execution pattern")
    condition: Optional[str] = Field(None, description="Condition expression for CONDITIONAL type")
    branches: Optional[Dict[str, Any]] = Field(None, description="Branches for SWITCH/CONDITIONAL types")
```

**Tests**: `tests/unit/test_workflow_models.py`
- Test required fields validation
- Test default values
- Test enum validation
- Test invalid step_type
- Test missing required fields

### 4. Create WorkflowDefinition Model
**File**: `src/workflow_engine.py`

```python
class WorkflowMetadata(BaseModel):
    """Workflow metadata."""
    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable name")
    version: str = Field(..., description="Semantic version")
    description: str = Field("", description="Workflow description")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

class WorkflowDefinition(BaseModel):
    """Complete workflow definition."""
    metadata: WorkflowMetadata = Field(..., description="Workflow metadata")
    steps: List[WorkflowStep] = Field(..., description="Workflow steps")
    error_handling: Optional[Dict[str, Any]] = Field(None, description="Error handling config")
```

**Tests**: `tests/unit/test_workflow_models.py`
- Test valid workflow creation
- Test missing metadata
- Test empty steps list
- Test workflow with multiple steps
- Test error_handling field

### 5. Implement WorkflowContext
**File**: `src/workflow_engine.py`

```python
import re
from typing import Any, Dict

class WorkflowContext:
    """Manages workflow execution state and template resolution."""

    def __init__(self, initial_input: Dict[str, Any]):
        """Initialize context with initial workflow input."""
        self.workflow_input = initial_input
        self.step_outputs = {}  # {step_id: {outputs: {...}}}

    def set_step_output(self, step_id: str, output: Dict[str, Any]) -> None:
        """Store output from a completed step."""
        self.step_outputs[step_id] = {"outputs": output}

    def resolve_expression(self, expression: str) -> Any:
        """
        Resolve a template expression like {{ steps.plan.outputs.result }}.

        Supports:
        - {{ workflow.input.field }}
        - {{ steps.step_id.outputs.field }}
        - {{ steps.step_id.outputs.nested.path }}

        Returns None if path doesn't exist.
        """
        if not isinstance(expression, str):
            return expression

        # Extract {{ ... }} pattern
        match = re.match(r'{{\s*(.+?)\s*}}', expression.strip())
        if not match:
            return expression  # Not a template

        path = match.group(1).split('.')

        # Resolve path in context
        if path[0] == 'workflow' and path[1] == 'input':
            data = self.workflow_input
            path = path[2:]  # Skip 'workflow.input'
        elif path[0] == 'steps':
            step_id = path[1]
            if step_id not in self.step_outputs:
                return None
            data = self.step_outputs[step_id]
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

    def resolve_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve all template expressions in an inputs dict."""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str):
                resolved[key] = self.resolve_expression(value)
            elif isinstance(value, dict):
                resolved[key] = self.resolve_inputs(value)
            elif isinstance(value, list):
                resolved[key] = [self.resolve_expression(v) if isinstance(v, str) else v for v in value]
            else:
                resolved[key] = value
        return resolved
```

**Tests**: `tests/unit/test_workflow_context.py`
- Test initialization with initial input
- Test `set_step_output()` and retrieval
- Test `resolve_expression()` with workflow.input path
- Test `resolve_expression()` with steps.X.outputs path
- Test nested path resolution (3+ levels deep)
- Test missing keys return None
- Test non-template strings pass through
- Test `resolve_inputs()` with mixed templates and literals
- Test `resolve_inputs()` with nested dicts
- Test `resolve_inputs()` with lists

### 6. Add YAML Loading Helper
**File**: `src/workflow_engine.py`

```python
import yaml
from typing import Union
from pathlib import Path

def load_workflow_from_yaml(yaml_content: Union[str, Path]) -> WorkflowDefinition:
    """
    Load and validate a workflow from YAML content or file path.

    Args:
        yaml_content: YAML string or path to YAML file

    Returns:
        Validated WorkflowDefinition object

    Raises:
        yaml.YAMLError: If YAML is malformed
        pydantic.ValidationError: If workflow structure is invalid
    """
    if isinstance(yaml_content, Path) or (isinstance(yaml_content, str) and '\n' not in yaml_content and len(yaml_content) < 255):
        # Treat as file path
        with open(yaml_content, 'r') as f:
            data = yaml.safe_load(f)
    else:
        # Treat as YAML string
        data = yaml.safe_load(yaml_content)

    return WorkflowDefinition(**data)
```

**Tests**: `tests/unit/test_workflow_models.py`
- Test loading from YAML string
- Test loading from file path
- Test malformed YAML raises yaml.YAMLError
- Test invalid structure raises ValidationError
- Test valid workflow parses correctly

## Test Files

### `tests/unit/test_workflow_models.py`
```python
import pytest
from pydantic import ValidationError
from src.workflow_engine import (
    StepType,
    WorkflowStep,
    WorkflowMetadata,
    WorkflowDefinition,
    load_workflow_from_yaml,
)

class TestStepType:
    def test_valid_step_types(self):
        assert StepType.SEQUENTIAL == "sequential"
        assert StepType.PARALLEL == "parallel"
        # ... etc

class TestWorkflowStep:
    def test_minimal_step(self):
        step = WorkflowStep(id="test", skill="test_skill")
        assert step.id == "test"
        assert step.skill == "test_skill"
        assert step.timeout == 300  # default

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            WorkflowStep(id="test")  # missing skill

    # ... more tests

class TestWorkflowDefinition:
    def test_valid_workflow(self):
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(
                id="test-workflow",
                name="Test",
                version="1.0.0"
            ),
            steps=[
                WorkflowStep(id="step1", skill="skill1")
            ]
        )
        assert workflow.metadata.id == "test-workflow"
        assert len(workflow.steps) == 1

    # ... more tests

class TestLoadWorkflowFromYAML:
    def test_load_from_string(self):
        yaml_str = """
metadata:
  id: test
  name: Test Workflow
  version: 1.0.0
steps:
  - id: step1
    skill: test_skill
"""
        workflow = load_workflow_from_yaml(yaml_str)
        assert workflow.metadata.id == "test"

    # ... more tests
```

### `tests/unit/test_workflow_context.py`
```python
import pytest
from src.workflow_engine import WorkflowContext

class TestWorkflowContext:
    def test_initialization(self):
        ctx = WorkflowContext({"key": "value"})
        assert ctx.workflow_input == {"key": "value"}
        assert ctx.step_outputs == {}

    def test_set_and_retrieve_step_output(self):
        ctx = WorkflowContext({})
        ctx.set_step_output("step1", {"result": "data"})
        assert "step1" in ctx.step_outputs
        assert ctx.step_outputs["step1"]["outputs"]["result"] == "data"

    def test_resolve_workflow_input_expression(self):
        ctx = WorkflowContext({"requirements": "test"})
        result = ctx.resolve_expression("{{ workflow.input.requirements }}")
        assert result == "test"

    def test_resolve_step_output_expression(self):
        ctx = WorkflowContext({})
        ctx.set_step_output("plan", {"plan_data": "structured plan"})
        result = ctx.resolve_expression("{{ steps.plan.outputs.plan_data }}")
        assert result == "structured plan"

    def test_resolve_nested_path(self):
        ctx = WorkflowContext({"nested": {"deep": {"value": 42}}})
        result = ctx.resolve_expression("{{ workflow.input.nested.deep.value }}")
        assert result == 42

    def test_resolve_missing_key_returns_none(self):
        ctx = WorkflowContext({})
        result = ctx.resolve_expression("{{ workflow.input.missing }}")
        assert result is None

    def test_non_template_string_passes_through(self):
        ctx = WorkflowContext({})
        result = ctx.resolve_expression("plain string")
        assert result == "plain string"

    def test_resolve_inputs_mixed_content(self):
        ctx = WorkflowContext({"req": "test requirement"})
        ctx.set_step_output("step1", {"data": "output"})

        inputs = {
            "literal": "plain value",
            "from_workflow": "{{ workflow.input.req }}",
            "from_step": "{{ steps.step1.outputs.data }}",
            "number": 42
        }

        resolved = ctx.resolve_inputs(inputs)
        assert resolved["literal"] == "plain value"
        assert resolved["from_workflow"] == "test requirement"
        assert resolved["from_step"] == "output"
        assert resolved["number"] == 42

    # ... more tests
```

### `tests/fixtures/conftest.py` (additions)
```python
@pytest.fixture
def sample_workflow_yaml():
    """Sample valid workflow YAML."""
    return """
metadata:
  id: test-workflow-v1
  name: Test Workflow
  version: 1.0.0
  description: A test workflow
steps:
  - id: step1
    skill: create_plan
    inputs:
      requirements: "{{ workflow.input.requirements }}"
    timeout: 300
  - id: step2
    skill: generate_code
    inputs:
      plan: "{{ steps.step1.outputs.result }}"
    timeout: 600
"""

@pytest.fixture
def sample_workflow_definition():
    """Sample WorkflowDefinition object."""
    from src.workflow_engine import WorkflowDefinition, WorkflowMetadata, WorkflowStep

    return WorkflowDefinition(
        metadata=WorkflowMetadata(
            id="test-workflow-v1",
            name="Test Workflow",
            version="1.0.0"
        ),
        steps=[
            WorkflowStep(id="step1", skill="create_plan", inputs={"requirements": "{{ workflow.input.requirements }}"}),
            WorkflowStep(id="step2", skill="generate_code", inputs={"plan": "{{ steps.step1.outputs.result }}"})
        ]
    )
```

## Acceptance Criteria

- [ ] `pyyaml` dependency added and installed
- [ ] `StepType` enum with all 4 types (SEQUENTIAL, PARALLEL, CONDITIONAL, SWITCH)
- [ ] `WorkflowStep` model with validation
- [ ] `WorkflowMetadata` model with validation
- [ ] `WorkflowDefinition` model with validation
- [ ] `WorkflowContext` class with state management
- [ ] `resolve_expression()` handles workflow.input paths
- [ ] `resolve_expression()` handles steps.X.outputs paths
- [ ] `resolve_expression()` handles nested paths (3+ levels)
- [ ] `resolve_expression()` returns None for missing paths
- [ ] `resolve_inputs()` recursively resolves dict/list templates
- [ ] `load_workflow_from_yaml()` loads from string and file
- [ ] All unit tests pass: `uv run pytest tests/unit/test_workflow_models.py -v`
- [ ] All context tests pass: `uv run pytest tests/unit/test_workflow_context.py -v`
- [ ] Code coverage >90% for new code: `uv run pytest tests/unit/test_workflow_*.py --cov=src.workflow_engine --cov-report=term-missing`
- [ ] No linting errors: `uv run invoke lint.black-check && uv run invoke lint.flake8`
- [ ] All existing tests still pass: `uv run invoke test`

## Validation Commands

```bash
# 1. Install dependencies
uv sync
python -c "import yaml; print(f'PyYAML {yaml.__version__}')"

# 2. Verify Python syntax
python -c "import ast; ast.parse(open('src/workflow_engine.py').read())"

# 3. Verify imports work
python -c "from src.workflow_engine import WorkflowDefinition, WorkflowStep, WorkflowContext, StepType; print('✓ All imports successful')"

# 4. Run unit tests for workflow models
uv run pytest tests/unit/test_workflow_models.py -v

# 5. Run unit tests for workflow context
uv run pytest tests/unit/test_workflow_context.py -v

# 6. Check coverage for new code
uv run pytest tests/unit/test_workflow_models.py tests/unit/test_workflow_context.py --cov=src.workflow_engine --cov-report=term-missing --cov-report=html

# 7. Verify no regressions in existing tests
uv run invoke test

# 8. Lint checks
uv run invoke lint.black-check
uv run invoke lint.flake8

# 9. Test YAML loading manually
python -c "
from src.workflow_engine import load_workflow_from_yaml
yaml_str = '''
metadata:
  id: test
  name: Test
  version: 1.0.0
steps:
  - id: step1
    skill: test_skill
'''
workflow = load_workflow_from_yaml(yaml_str)
print(f'✓ Loaded workflow: {workflow.metadata.name}')
print(f'✓ Steps: {len(workflow.steps)}')
"

# 10. Test template resolution manually
python -c "
from src.workflow_engine import WorkflowContext
ctx = WorkflowContext({'test': 'value'})
ctx.set_step_output('step1', {'result': 'data'})
resolved = ctx.resolve_expression('{{ steps.step1.outputs.result }}')
assert resolved == 'data', f'Expected data, got {resolved}'
print('✓ Template resolution works')
"
```

## Next Steps

After completing Part 1 and all tests pass:
- ✅ Proceed to **Part 2: Core Workflow Engine** (execution patterns)
- Part 2 will import and use these data models
- Part 2 will use WorkflowContext for managing execution state
