# Part 4: Orchestrator Integration & Example Workflows

**Status**: 🔴 Not Started | **Depends On**: Part 1, 2, 3 | **Testing**: Integration + E2E tests

## Overview

This final part creates example workflow YAML files, integrates the workflow engine with the orchestrator, updates the CLI to accept workflow IDs, and validates the complete feature end-to-end while maintaining backward compatibility.

## Scope

### In Scope
- Create 3 example workflow YAML files (code-generation, smart-router, parallel-analysis)
- Refactor orchestrator to use workflow engine
- Update main.py CLI to accept `--workflow` flag
- Maintain backward compatibility
- Integration and E2E tests
- Documentation updates (README, new WORKFLOW_ENGINE.md)
- Full validation suite

### Out of Scope
- Advanced workflow patterns (loops, sub-workflows) - future enhancements
- Workflow visualization - future enhancement

## Prerequisites

✅ Parts 1, 2, and 3 must be completed:
- Data models and context work
- WorkflowEngine executes all patterns
- Registry push/pull/discovery works
- All previous tests pass

## Implementation Tasks

### 1. Create Example Workflow: Code Generation
**File**: `workflows/code-generation.yaml` (new file)

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

**Validation**:
```bash
python -c "import yaml; yaml.safe_load(open('workflows/code-generation.yaml'))"
python -c "from src.workflow_engine import load_workflow_from_yaml; wf = load_workflow_from_yaml('workflows/code-generation.yaml'); print(f'✓ {wf.metadata.name} - {len(wf.steps)} steps')"
```

### 2. Create Example Workflow: Smart Router
**File**: `workflows/smart-router.yaml` (new file)

```yaml
metadata:
  id: smart-router-v1
  name: Smart Request Router
  version: 1.0.0
  description: "Analyzes request type and routes to appropriate workflow"
  tags:
    - routing
    - conditional
    - meta-workflow

steps:
  - id: analyze
    skill: analyze_request
    inputs:
      request: "{{ workflow.input.requirements }}"
    outputs: request_type
    timeout: 60
    step_type: sequential

  - id: route
    skill: route_workflow
    step_type: switch
    condition: "{{ steps.analyze.outputs.request_type }}"
    branches:
      code_generation:
        - id: generate_code_workflow
          skill: execute_workflow
          inputs:
            workflow_id: code-generation-v1
            input: "{{ workflow.input }}"

      data_analysis:
        - id: analyze_data_workflow
          skill: execute_workflow
          inputs:
            workflow_id: data-analysis-v1
            input: "{{ workflow.input }}"

      default:
        - id: fallback
          skill: create_plan
          inputs:
            requirements: "{{ workflow.input.requirements }}"
```

**Note**: This workflow demonstrates the switch pattern. The `analyze_request` and `route_workflow` skills would need to be implemented in future agents.

### 3. Create Example Workflow: Parallel Analysis
**File**: `workflows/parallel-analysis.yaml` (new file)

```yaml
metadata:
  id: parallel-analysis-v1
  name: Parallel Code Analysis
  version: 1.0.0
  description: "Run multiple analysis tasks in parallel"
  tags:
    - parallel
    - analysis
    - performance

steps:
  - id: parallel_analyze
    step_type: parallel
    branches:
      steps:
        - id: analyze_quality
          skill: review_code
          inputs:
            code: "{{ workflow.input.code }}"
            language: "{{ workflow.input.language }}"
          outputs: quality_result
          timeout: 300

        - id: analyze_security
          skill: security_scan
          inputs:
            code: "{{ workflow.input.code }}"
          outputs: security_result
          timeout: 300

        - id: analyze_performance
          skill: performance_check
          inputs:
            code: "{{ workflow.input.code }}"
          outputs: performance_result
          timeout: 300

  - id: aggregate
    skill: aggregate_results
    inputs:
      quality: "{{ steps.analyze_quality.outputs.quality_result }}"
      security: "{{ steps.analyze_security.outputs.security_result }}"
      performance: "{{ steps.analyze_performance.outputs.performance_result }}"
    outputs: result
    timeout: 60
    step_type: sequential
```

**Note**: This demonstrates parallel execution. The `security_scan`, `performance_check`, and `aggregate_results` skills would need to be implemented in future agents.

### 4. Create Test Workflow Directory
**Directory**: `tests/workflows/` (new directory)

Create test workflow files:

**`tests/workflows/valid_simple.yaml`**:
```yaml
metadata:
  id: test-simple
  name: Simple Test Workflow
  version: 1.0.0
steps:
  - id: step1
    skill: test_skill
    inputs:
      data: "{{ workflow.input.test }}"
```

**`tests/workflows/invalid_syntax.yaml`**:
```yaml
metadata:
  id: test-invalid
  name: Invalid YAML
  version: 1.0.0
steps:
  - id: step1
    skill: test_skill
    inputs: [invalid yaml structure here
```

**`tests/workflows/missing_required.yaml`**:
```yaml
metadata:
  id: test-missing
  version: 1.0.0
  # Missing 'name' field
steps:
  - id: step1
    skill: test_skill
```

### 5. Refactor Orchestrator
**File**: `src/orchestrator.py` (update existing file)

Add workflow-based orchestration while keeping legacy function:

```python
import asyncio
from typing import Dict, Any, Optional
from src.discovery import discover_workflow
from src.workflow_engine import WorkflowEngine


async def execute_workflow_by_id(
    workflow_id: str,
    workflow_input: Dict[str, Any],
    version: str = "v1"
) -> Dict[str, Any]:
    """
    Execute a workflow by ID from the registry.

    Args:
        workflow_id: Workflow identifier (e.g., "code-generation")
        workflow_input: Input data for workflow
        version: Workflow version (default: v1)

    Returns:
        Dict containing workflow results and metadata

    Example:
        result = await execute_workflow_by_id(
            "code-generation-v1",
            {"requirements": "Create factorial function"}
        )
    """
    print(f"\n[Orchestrator] Executing workflow: {workflow_id}:{version}")

    # Discover workflow from registry
    workflow = await discover_workflow(workflow_id, version)
    if not workflow:
        raise ValueError(f"Workflow not found: {workflow_id}:{version}")

    # Execute workflow
    engine = WorkflowEngine()
    context = await engine.execute_workflow(workflow, workflow_input)

    # Build result
    result = {
        "workflow_id": workflow.metadata.id,
        "workflow_name": workflow.metadata.name,
        "workflow_version": workflow.metadata.version,
        "initial_input": workflow_input,
        "step_outputs": context.step_outputs,
        "final_output": _extract_final_output(context)
    }

    print(f"[Orchestrator] Workflow completed successfully")
    return result


def _extract_final_output(context) -> Dict[str, Any]:
    """Extract the final output from the last step."""
    if not context.step_outputs:
        return {}

    # Get last step's output
    last_step_id = list(context.step_outputs.keys())[-1]
    return context.step_outputs[last_step_id].get("outputs", {})


# Keep existing orchestrate() function for backward compatibility
async def orchestrate(requirements: str) -> Dict[str, Any]:
    """
    Legacy orchestration function (hardcoded Plan → Build → Test).

    DEPRECATED: Use execute_workflow_by_id() with "code-generation-v1" instead.

    Args:
        requirements: User requirements string

    Returns:
        Dict with plan, code, and review results
    """
    print("\n[Orchestrator] Using legacy hardcoded orchestration (DEPRECATED)")
    print("[Orchestrator] Consider using workflow-based orchestration instead")

    # Delegate to workflow engine
    result = await execute_workflow_by_id(
        "code-generation-v1",
        {"requirements": requirements}
    )

    # Transform to legacy format for compatibility
    return {
        "plan": result["step_outputs"].get("plan", {}).get("outputs", {}).get("result"),
        "code": result["step_outputs"].get("build", {}).get("outputs", {}).get("result"),
        "review": result["step_outputs"].get("test", {}).get("outputs", {}).get("result"),
        "metadata": {
            "workflow_id": result["workflow_id"],
            "workflow_version": result["workflow_version"]
        }
    }
```

**Tests**: Update `tests/unit/test_orchestrator.py`
- Test `execute_workflow_by_id()` with mocked workflow discovery
- Test workflow not found raises ValueError
- Test result contains all expected fields
- Test `orchestrate()` still works (backward compatibility)
- Test `orchestrate()` delegates to workflow engine
- Verify no regressions in existing orchestrator tests

### 6. Update Main CLI
**File**: `main.py` (update existing file)

```python
import argparse
import asyncio
import json
from pathlib import Path
from src.orchestrator import execute_workflow_by_id, orchestrate


def save_results(results: dict, output_dir: Path = Path("app")):
    """Save workflow results to output directory."""
    output_dir.mkdir(exist_ok=True)

    # Save metadata
    metadata = {
        "workflow_id": results.get("workflow_id"),
        "workflow_name": results.get("workflow_name"),
        "workflow_version": results.get("workflow_version"),
        "initial_input": results.get("initial_input")
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

    # Save step outputs
    step_outputs = results.get("step_outputs", {})

    # Extract plan (if exists)
    if "plan" in step_outputs:
        plan_output = step_outputs["plan"].get("outputs", {}).get("result")
        if plan_output:
            (output_dir / "plan.json").write_text(json.dumps(plan_output, indent=2))

    # Extract code (if exists)
    if "build" in step_outputs:
        build_output = step_outputs["build"].get("outputs", {}).get("result")
        if build_output and isinstance(build_output, dict):
            code = build_output.get("code", "")
            if code:
                (output_dir / "main.py").write_text(code)

    # Extract review (if exists)
    if "test" in step_outputs:
        review_output = step_outputs["test"].get("outputs", {}).get("result")
        if review_output:
            (output_dir / "review.json").write_text(json.dumps(review_output, indent=2))

    print(f"\n✓ Results saved to {output_dir}/")


async def main():
    parser = argparse.ArgumentParser(
        description="Pallet A2A Agent Framework - Workflow Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default workflow with custom requirements
  python main.py "Create a function to calculate fibonacci numbers"

  # Use specific workflow by ID
  python main.py --workflow code-generation-v1 "Create a hello world function"

  # Use default requirements with default workflow
  python main.py
        """
    )

    parser.add_argument(
        "requirements",
        nargs="?",
        default="Create a Python function that calculates the factorial of a number",
        help="Requirements for code generation (default: factorial function)"
    )

    parser.add_argument(
        "-w", "--workflow",
        default="code-generation-v1",
        help="Workflow ID to execute (default: code-generation-v1)"
    )

    parser.add_argument(
        "--version",
        default="v1",
        help="Workflow version (default: v1)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Pallet A2A Agent Framework")
    print("Workflow-Based Orchestration")
    print("=" * 60)

    try:
        # Execute workflow
        results = await execute_workflow_by_id(
            workflow_id=args.workflow,
            workflow_input={"requirements": args.requirements},
            version=args.version
        )

        # Save results
        save_results(results)

        print("\n" + "=" * 60)
        print("✓ Orchestration completed successfully")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Orchestration failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```

**Tests**: Update `tests/integration/test_end_to_end.py`
- Test CLI with default workflow
- Test CLI with `--workflow` flag
- Test CLI with custom requirements
- Test backward compatibility (existing behavior)
- Test invalid workflow ID
- Test results are saved correctly

### 7. Create Documentation
**File**: `docs/WORKFLOW_ENGINE.md` (new file)

```markdown
# Workflow Engine Documentation

## Overview

The Pallet workflow engine enables declarative workflow definitions stored in YAML files and versioned in the OCI registry. This decouples workflow logic from orchestrator code, enabling runtime workflow selection and reusable patterns.

## Benefits

- **Declarative**: Define workflows in YAML, not code
- **Versioned**: Store workflows as artifacts in OCI registry
- **Dynamic**: Select workflows at runtime based on requirements
- **Reusable**: Share workflow patterns across projects
- **Testable**: Test workflows in isolation

## Quick Start

### Execute a Workflow

\`\`\`bash
# Use default workflow
python main.py "Create a hello world function"

# Specify workflow explicitly
python main.py --workflow code-generation-v1 "Create factorial function"
\`\`\`

### List Available Workflows

\`\`\`python
from src.workflow_registry import list_workflows

workflows = list_workflows()
print(f"Found {len(workflows)} workflows: {workflows}")
\`\`\`

## Workflow YAML Specification

### Basic Structure

\`\`\`yaml
metadata:
  id: my-workflow-v1          # Unique identifier
  name: My Workflow           # Human-readable name
  version: 1.0.0              # Semantic version
  description: "Description"  # Optional description
  tags:                       # Optional tags
    - tag1
    - tag2

steps:
  - id: step1                 # Unique step ID
    skill: skill_name         # Skill to execute
    inputs:                   # Input parameters
      param1: "value"
      param2: "{{ template }}"
    outputs: result           # Output variable name
    timeout: 300              # Timeout in seconds
    step_type: sequential     # Execution pattern
\`\`\`

### Template Expressions

Access workflow input and step outputs using `{{ }}` syntax:

\`\`\`yaml
inputs:
  # Access workflow input
  requirements: "{{ workflow.input.requirements }}"

  # Access previous step output
  plan: "{{ steps.plan.outputs.result }}"

  # Nested paths
  code: "{{ steps.build.outputs.result.code }}"
\`\`\`

### Execution Patterns

#### Sequential (default)

Execute steps one after another:

\`\`\`yaml
steps:
  - id: step1
    skill: skill1
    step_type: sequential

  - id: step2
    skill: skill2
    step_type: sequential
\`\`\`

#### Parallel

Execute multiple steps concurrently:

\`\`\`yaml
steps:
  - id: parallel_step
    step_type: parallel
    branches:
      steps:
        - id: task1
          skill: skill1
        - id: task2
          skill: skill2
        - id: task3
          skill: skill3
\`\`\`

#### Conditional

Branch based on condition:

\`\`\`yaml
steps:
  - id: conditional_step
    step_type: conditional
    condition: "{{ workflow.input.flag }}"
    branches:
      if_true:
        - id: true_branch
          skill: skill_true
      if_false:
        - id: false_branch
          skill: skill_false
\`\`\`

#### Switch

Route based on value:

\`\`\`yaml
steps:
  - id: switch_step
    step_type: switch
    condition: "{{ workflow.input.type }}"
    branches:
      type_a:
        - id: handle_a
          skill: skill_a
      type_b:
        - id: handle_b
          skill: skill_b
      default:
        - id: handle_default
          skill: skill_default
\`\`\`

## Registry Operations

### Push Workflow

\`\`\`bash
oras push localhost:5000/workflows/my-workflow:v1 my-workflow.yaml:application/yaml
\`\`\`

### Pull Workflow

\`\`\`python
from src.workflow_registry import pull_workflow_from_registry

workflow_path = pull_workflow_from_registry("my-workflow", "v1")
\`\`\`

### List Workflows

\`\`\`bash
curl -s http://localhost:5000/v2/_catalog | jq '.repositories | map(select(startswith("workflows/")))'
\`\`\`

## Example Workflows

See `workflows/` directory for examples:
- **code-generation.yaml**: Plan → Build → Test pipeline
- **smart-router.yaml**: Dynamic routing based on request type
- **parallel-analysis.yaml**: Parallel execution for multiple analyses

## Troubleshooting

### Workflow Not Found

- Verify workflow is in registry: `curl http://localhost:5000/v2/_catalog`
- Check workflow ID matches filename
- Ensure registry is running: `docker ps | grep registry`

### Template Resolution Errors

- Verify step IDs are correct
- Check output variable names match
- Ensure referenced steps execute before current step

### Timeout Errors

- Increase step timeout in YAML
- Check agent is responding: `curl http://localhost:8001/agent-card`
\`\`\`

**Update**: `README.md`

Add section after "What It Does":

```markdown
### Workflow-Based Orchestration

Pallet uses a **declarative workflow engine** that separates workflow definitions from code:

- **Workflows are YAML files** stored in the OCI registry
- **Runtime workflow selection** based on requirements
- **Multiple execution patterns**: sequential, parallel, conditional, switch
- **Template expressions** for data flow between steps

Example workflows:
- `code-generation-v1`: Plan → Build → Test (default)
- `smart-router-v1`: Analyze request type → route to appropriate workflow
- `parallel-analysis-v1`: Run multiple analyses concurrently

See [docs/WORKFLOW_ENGINE.md](docs/WORKFLOW_ENGINE.md) for full documentation.
```

Update project structure:
```
workflows/            Example workflow definitions (YAML)
docs/WORKFLOW_ENGINE.md  Workflow engine documentation
```

### 8. Integration Tests
**File**: `tests/integration/test_workflow_execution.py` (extend if exists)

Add comprehensive integration tests:

```python
import pytest
import asyncio
from pathlib import Path
from src.workflow_engine import WorkflowEngine, load_workflow_from_yaml
from src.orchestrator import execute_workflow_by_id
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class TestWorkflowExecutionIntegration:
    async def test_code_generation_workflow_full(self):
        """Test full code generation workflow with mocked agents."""
        workflow_file = Path("workflows/code-generation.yaml")
        if not workflow_file.exists():
            pytest.skip("Workflow file not found")

        workflow = load_workflow_from_yaml(workflow_file)
        engine = WorkflowEngine()

        mock_responses = [
            {"title": "Factorial Function", "steps": ["Define function", "Implement logic"]},  # plan
            {"code": "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)", "language": "python"},  # build
            {"quality_score": 85, "approved": True, "summary": "Good code"}  # test
        ]

        with patch('src.workflow_engine.discover_agent_for_skill', return_value="http://localhost:8001"):
            with patch.object(engine, 'call_agent_skill', AsyncMock(side_effect=mock_responses)):
                context = await engine.execute_workflow(
                    workflow,
                    {"requirements": "Create a factorial function"}
                )

                assert "plan" in context.step_outputs
                assert "build" in context.step_outputs
                assert "test" in context.step_outputs

    async def test_execute_workflow_by_id_integration(self):
        """Test orchestrator workflow execution."""
        with patch('src.orchestrator.discover_workflow') as mock_discover:
            # Mock workflow discovery
            workflow = load_workflow_from_yaml("workflows/code-generation.yaml")
            mock_discover.return_value = workflow

            with patch('src.workflow_engine.discover_agent_for_skill', return_value="http://localhost:8001"):
                with patch('src.workflow_engine.WorkflowEngine.call_agent_skill', AsyncMock(return_value={"result": "test"})):
                    result = await execute_workflow_by_id(
                        "code-generation-v1",
                        {"requirements": "test"}
                    )

                    assert result["workflow_id"] == "code-generation-v1"
                    assert "step_outputs" in result
                    assert "final_output" in result
```

### 9. Final Validation Suite

Create validation checklist:

```bash
# Full test suite
uv run invoke test

# Coverage report
uv run invoke test.coverage

# Linting
uv run invoke lint.black-check
uv run invoke lint.flake8

# Manual E2E test
bash scripts/bootstrap.sh
uv run python main.py "Create factorial function"
ls -la app/
bash scripts/kill.sh --clean-logs
```

## Acceptance Criteria

### Functionality
- [ ] `workflows/code-generation.yaml` created and valid
- [ ] `workflows/smart-router.yaml` created and valid
- [ ] `workflows/parallel-analysis.yaml` created and valid
- [ ] `tests/workflows/` directory with test workflows
- [ ] `execute_workflow_by_id()` added to orchestrator
- [ ] `orchestrate()` maintains backward compatibility
- [ ] `main.py` accepts `--workflow` flag
- [ ] `main.py` defaults to code-generation-v1
- [ ] Results saved to app/ directory
- [ ] `docs/WORKFLOW_ENGINE.md` created
- [ ] `README.md` updated with workflow information

### Testing (CRITICAL)
- [ ] All 151+ existing tests pass (zero regressions)
- [ ] `tests/unit/test_orchestrator.py` updated with workflow tests
- [ ] `tests/integration/test_end_to_end.py` updated
- [ ] `tests/integration/test_workflow_execution.py` created
- [ ] Overall coverage ≥87% (maintain existing)
- [ ] Workflow code coverage ≥85%
- [ ] `uv run invoke test` passes 100%
- [ ] `uv run invoke lint.black-check` passes
- [ ] `uv run invoke lint.flake8` passes

### Validation
- [ ] `bash scripts/bootstrap.sh` starts all services + pushes workflows
- [ ] `python main.py "test"` works (default workflow)
- [ ] `python main.py --workflow code-generation-v1 "test"` works
- [ ] Results saved to app/ directory
- [ ] Backward compatibility verified
- [ ] All validation commands (below) execute successfully

## Validation Commands

```bash
# 1. Validate workflow YAML files
python -c "import yaml; yaml.safe_load(open('workflows/code-generation.yaml'))"
python -c "import yaml; yaml.safe_load(open('workflows/smart-router.yaml'))"
python -c "import yaml; yaml.safe_load(open('workflows/parallel-analysis.yaml'))"

# 2. Load workflows with engine
python -c "from src.workflow_engine import load_workflow_from_yaml; wf = load_workflow_from_yaml('workflows/code-generation.yaml'); print(f'✓ {wf.metadata.name}')"

# 3. Test orchestrator imports
python -c "from src.orchestrator import execute_workflow_by_id, orchestrate; print('✓ Orchestrator functions imported')"

# 4. Test main.py imports
python -c "import main; print('✓ main.py imports successfully')"

# 5. Run all tests
uv run invoke test

# 6. Run integration tests
uv run invoke test.integration

# 7. Generate coverage report
uv run invoke test.coverage

# 8. Lint checks
uv run invoke lint.black-check
uv run invoke lint.flake8

# 9. Start services and test E2E
bash scripts/bootstrap.sh

# 10. List workflows in registry
curl -s http://localhost:5000/v2/_catalog | jq '.repositories | map(select(startswith("workflows/")))'

# 11. Execute default workflow
uv run python main.py "Create a function to calculate prime numbers"

# 12. Execute specific workflow
uv run python main.py --workflow code-generation-v1 "Create hello world"

# 13. Verify outputs created
ls -lh app/
cat app/metadata.json | jq '.'

# 14. Test backward compatibility
python -c "
import asyncio
from src.orchestrator import orchestrate

async def test():
    # This should still work (legacy function)
    result = await orchestrate('test requirement')
    print('✓ Legacy orchestrate() still works')

asyncio.run(test())
"

# 15. Clean up
bash scripts/kill.sh --clean-logs
```

## Success Criteria

All of the following must be true before marking Part 4 complete:

1. ✅ All 3 example workflows created and valid
2. ✅ Orchestrator refactored with workflow support
3. ✅ Main CLI accepts --workflow flag
4. ✅ Backward compatibility maintained
5. ✅ Documentation complete (WORKFLOW_ENGINE.md + README updates)
6. ✅ All 151+ existing tests pass with zero regressions
7. ✅ New tests added and passing
8. ✅ Coverage ≥87% maintained
9. ✅ All linting passes
10. ✅ E2E manual testing successful
11. ✅ All validation commands execute successfully

## Next Steps

After completing Part 4:
- ✅ Feature is **COMPLETE**
- Review specs/6-workflows.md acceptance criteria
- Mark all items as completed
- Consider future enhancements (sub-workflows, loops, monitoring)
