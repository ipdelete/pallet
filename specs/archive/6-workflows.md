# Feature: Workflow-Based Orchestration Engine

## Feature Description

This feature introduces a declarative workflow engine that decouples workflow definitions from the orchestrator implementation. Workflows are defined in YAML files and stored in the OCI registry as versioned artifacts, enabling runtime workflow selection, reusable workflow patterns, and dynamic routing based on request analysis.

The workflow engine supports multiple execution patterns (sequential, parallel, conditional, map-reduce) and uses template expressions to pass data between steps. This makes the orchestrator generic and reusable across different use cases without code changes.

## User Story

As a **developer building AI agent systems**
I want to **define workflows declaratively in YAML files stored in a registry**
So that **I can create, version, and deploy new workflows without modifying orchestrator code, and dynamically select workflows at runtime based on request characteristics**

## Problem Statement

Currently, the orchestrator in Phase 5 has hardcoded workflow logic:
- The Plan → Build → Test pipeline is defined in Python code
- Adding new workflows requires changing the orchestrator implementation
- Workflow logic is tightly coupled to the orchestrator
- No way to version workflows independently of code
- Cannot dynamically route requests to different workflows based on content
- Difficult to test workflows in isolation
- No reusability of common workflow patterns across different use cases

This limits flexibility and makes it difficult to:
- Experiment with different agent combinations
- Deploy new workflows without redeploying the orchestrator
- Share workflows across teams or projects
- Implement sophisticated routing logic (e.g., analyze request → select appropriate workflow)

## Solution Statement

Implement a workflow engine that:

1. **Parses YAML workflow definitions** containing:
   - Metadata (id, name, version, description)
   - Steps with skill IDs, inputs (with template expressions), outputs
   - Step types (sequential, parallel, conditional, switch)
   - Error handling configuration

2. **Stores workflows in OCI registry** as versioned artifacts (like agent cards)
   - Push: `oras push localhost:5000/workflows/{id}:v1 workflow.yaml`
   - Pull: Discovery mechanism to find and load workflows

3. **Executes workflows dynamically** with:
   - Context management (passing data between steps)
   - Template expression resolution (`{{ steps.plan.outputs.result }}`)
   - Agent discovery per step (using existing discovery module)
   - Support for multiple execution patterns

4. **Enables workflow routing** where a special workflow can:
   - Analyze incoming requests
   - Select the appropriate workflow dynamically
   - Delegate execution to the selected workflow

This decouples "what to do" (workflows) from "how to do it" (orchestrator), making the system more flexible and maintainable.

## Relevant Files

### Existing Files
- **`src/orchestrator.py`** - Current hardcoded orchestration logic that will be refactored to use the workflow engine
- **`src/discovery.py`** - Agent discovery logic that will be extended to discover workflows from registry
- **`main.py`** - Entry point that will be updated to load workflows and execute them
- **`pyproject.toml`** - Will need `pyyaml` dependency added for YAML parsing
- **`src/agent_cards/*.json`** - Example artifacts in registry; workflows will follow similar pattern

### New Files

#### `src/workflow_engine.py`
Core workflow engine implementation containing:
- `WorkflowDefinition` - Pydantic model for workflow structure
- `WorkflowStep` - Represents individual workflow steps
- `WorkflowContext` - Manages execution state and template resolution
- `WorkflowEngine` - Main engine class that loads, parses, and executes workflows
- Step execution methods for sequential, parallel, conditional, and switch patterns

#### `src/workflow_registry.py`
Workflow storage and retrieval from OCI registry:
- `push_workflow()` - Push YAML workflow to registry
- `pull_workflow()` - Pull and parse workflow from registry
- `list_workflows()` - Discover available workflows
- `get_workflow_metadata()` - Read workflow metadata without pulling full file

#### `workflows/code-generation.yaml`
Example workflow for the existing Plan → Build → Test pipeline:
- Demonstrates sequential execution pattern
- Uses template expressions for data flow
- Includes timeout configuration per step
- Shows error handling configuration

#### `workflows/smart-router.yaml`
Example meta-workflow for dynamic workflow selection:
- Analyzes incoming request type
- Routes to appropriate specialized workflow
- Demonstrates switch/conditional patterns
- Includes default fallback behavior

#### `workflows/parallel-analysis.yaml`
Example parallel workflow:
- Runs multiple analysis agents simultaneously
- Demonstrates parallel execution pattern
- Shows result aggregation strategies
- Useful for content analysis, validation checks

#### `scripts/push_workflows.sh`
Bootstrap script to push sample workflows to registry:
- Creates workflow YAML files
- Pushes them to registry with ORAS
- Verifies successful push
- Lists all workflows in registry

## Implementation Plan

### Phase 1: Foundation - Workflow Data Models and YAML Parsing

**Implementation**:
- Define Pydantic models for workflows (WorkflowDefinition, WorkflowStep)
- Implement YAML loading and validation
- Create WorkflowContext for managing execution state
- Implement template expression resolution logic (`{{ variable.path }}` syntax)

**Testing** (TDD approach):
- Add `tests/unit/test_workflow_models.py` - Test Pydantic model validation
- Add `tests/unit/test_workflow_context.py` - Test context and template resolution
- Run: `uv run invoke test.unit` - All new unit tests must pass
- Coverage target: >90% for workflow models and context

### Phase 2: Core Implementation - Workflow Engine

**Implementation**:
- Implement WorkflowEngine class with step execution methods
- Add support for sequential execution (existing pattern)
- Implement parallel execution with asyncio.gather
- Add conditional execution with condition evaluation
- Implement switch/case routing pattern
- Add agent discovery integration per step
- Include timeout and basic error handling per step

**Testing**:
- Add `tests/unit/test_workflow_engine.py` - Test engine with mocked agents
- Test each execution pattern (sequential, parallel, conditional, switch)
- Test timeout handling and error cases
- Run: `uv run invoke test.unit` - All tests including existing must pass
- Coverage target: >85% for workflow engine

### Phase 3: Registry Integration - Workflow Storage

**Implementation**:
- Implement workflow_registry.py with push/pull functions
- Extend discovery.py to query workflow catalog
- Add workflow versioning support
- Create scripts/push_workflows.sh bootstrap script

**Testing**:
- Add `tests/unit/test_workflow_registry.py` - Mock subprocess/ORAS calls
- Update `tests/unit/test_discovery.py` - Add workflow discovery tests
- Add fixtures in `tests/fixtures/conftest.py` for sample workflows
- Run: `uv run invoke test.unit` - Verify no regressions
- Coverage target: >80% for registry functions

### Phase 4: Example Workflows and Integration Tests

**Implementation**:
- Create `workflows/code-generation.yaml` (existing pipeline)
- Create `workflows/smart-router.yaml` (dynamic routing)
- Create `workflows/parallel-analysis.yaml` (parallel pattern)

**Testing**:
- Add `tests/integration/test_workflow_execution.py` - End-to-end workflow tests
- Add `tests/workflows/` directory with test workflow files (valid/invalid)
- Test workflow loading, parsing, execution with mocked agents
- Test error scenarios (invalid YAML, missing skills, timeouts)
- Run: `uv run invoke test.integration` - All integration tests pass
- Run: `uv run invoke test` - All tests (unit + integration) pass
- Coverage target: >85% overall

### Phase 5: Orchestrator Refactoring and Full Validation

**Implementation**:
- Update main.py to accept workflow ID as CLI parameter
- Modify orchestrator.py to load and execute workflows
- Maintain backward compatibility with hardcoded orchestration
- Create docs/WORKFLOW_ENGINE.md documentation
- Update README.md with workflow information

**Testing**:
- Update `tests/unit/test_orchestrator.py` - Add workflow-based orchestration tests
- Update `tests/integration/test_end_to_end.py` - Test new workflow path
- Add backward compatibility tests (verify Phase 5 behavior unchanged)
- Run: `uv run invoke test.coverage` - Generate full coverage report
- Run: `uv run invoke lint.black-check` - Verify code formatting
- Run: `uv run invoke lint.flake8` - Verify style compliance
- **Final validation**: All 151+ existing tests MUST pass with zero regressions
- Coverage target: Maintain or exceed 87% overall coverage

## Step by Step Tasks

### 1. Add Dependencies
- Add `pyyaml` to pyproject.toml
- Run `uv sync` to install dependencies
- Verify import: `python -c "import yaml; print(yaml.__version__)"`

### 2. Create Workflow Data Models (`src/workflow_engine.py` - Part 1)
- Define `StepType` enum (SEQUENTIAL, PARALLEL, CONDITIONAL, SWITCH)
- Create `WorkflowStep` dataclass with:
  - `id`, `skill`, `inputs`, `outputs`, `timeout`, `step_type`, `condition`, `branches`
- Create `WorkflowDefinition` dataclass with:
  - `metadata` (id, name, version, description, tags)
  - `steps` (list of WorkflowStep)
  - `error_handling` (optional configuration)
- Add Pydantic validation for required fields
- **Test**: Create `tests/unit/test_workflow_models.py`
  - Test WorkflowStep validation (required fields, types)
  - Test WorkflowDefinition validation
  - Test enum values
  - Run: `uv run pytest tests/unit/test_workflow_models.py -v`

### 3. Implement WorkflowContext (`src/workflow_engine.py` - Part 2)
- Create `WorkflowContext` class to manage execution state
- Implement `set_step_output()` to store step results
- Implement `resolve_expression()` to parse `{{ path }}` templates
  - Support `{{ workflow.input.field }}`
  - Support `{{ steps.step_id.outputs.field }}`
  - Support nested paths
- Implement `resolve_inputs()` to resolve all templates in a dict
- **Test**: Create `tests/unit/test_workflow_context.py`
  - Test context initialization with initial input
  - Test `set_step_output()` and retrieval
  - Test `resolve_expression()` with various patterns
  - Test nested path resolution
  - Test edge cases (missing keys, null values, invalid syntax)
  - Run: `uv run pytest tests/unit/test_workflow_context.py -v`

### 4. Create WorkflowEngine Class (`src/workflow_engine.py` - Part 3)
- Implement `load_workflow()` to parse YAML into WorkflowDefinition
- Add workflow validation (check required fields, step references)
- Implement `discover_agent_for_skill()` with caching
- Create `execute_step()` for single step execution:
  - Resolve input templates
  - Discover agent for skill
  - Call agent via JSON-RPC
  - Return result
- Add timeout handling per step
- **Test**: Create `tests/unit/test_workflow_engine.py`
  - Test `load_workflow()` with valid/invalid YAML
  - Test workflow validation errors
  - Test `execute_step()` with mocked agent calls
  - Test timeout handling
  - Test agent discovery caching
  - Add fixtures to `tests/fixtures/conftest.py` for sample workflows
  - Run: `uv run pytest tests/unit/test_workflow_engine.py -v`

### 5. Implement Execution Patterns (`src/workflow_engine.py` - Part 4)
- Implement `execute_sequential_steps()`:
  - Loop through steps in order
  - Pass output from step N to step N+1
  - Store outputs in context
- Implement `execute_parallel_steps()`:
  - Use `asyncio.gather()` for concurrent execution
  - Collect all results
  - Merge into context
- Implement `execute_conditional_step()`:
  - Evaluate condition expression
  - Execute if_true or if_false branch
  - Handle missing condition (default to true/false)
- Implement `execute_switch_step()`:
  - Evaluate switch expression
  - Match against cases
  - Execute matched workflow or default
- **Test**: Extend `tests/unit/test_workflow_engine.py`
  - Test sequential execution with mocked steps
  - Test parallel execution (verify concurrent calls)
  - Test conditional execution (both branches)
  - Test switch execution (multiple cases + default)
  - Test error propagation in each pattern
  - Run: `uv run invoke test.unit` to verify all unit tests pass

### 6. Create Main Execution Method (`src/workflow_engine.py` - Part 5)
- Implement `execute_workflow()`:
  - Initialize WorkflowContext with initial_input
  - Iterate through workflow steps
  - Dispatch to appropriate execution method based on step_type
  - Store outputs in context after each step
  - Print progress during execution
  - Return final context with all step outputs
- Add comprehensive error messages
- **Test**: Extend `tests/unit/test_workflow_engine.py`
  - Test `execute_workflow()` end-to-end with mocked agents
  - Test workflow with mixed step types
  - Test error handling and recovery
  - Test progress output
  - Run: `uv run invoke test.unit` - Verify 100% of new code passes

### 7. Implement Workflow Registry Functions (`src/workflow_registry.py`)
- Create `push_workflow_to_registry()`:
  - Use subprocess to call `oras push`
  - Tag with version
  - Return success/failure
- Create `pull_workflow_from_registry()`:
  - Use subprocess to call `oras pull`
  - Return path to downloaded YAML
  - Handle errors gracefully
- Create `list_workflows()`:
  - Query registry `/v2/_catalog`
  - Filter for `workflows/*` repositories
  - Return list of workflow IDs
- Create `get_workflow_metadata()`:
  - Pull workflow and parse metadata only
  - Don't load full workflow definition
  - Used for workflow discovery/listing
- **Test**: Create `tests/unit/test_workflow_registry.py`
  - Test `push_workflow_to_registry()` with mocked subprocess
  - Test `pull_workflow_from_registry()` with mocked ORAS
  - Test `list_workflows()` with mocked HTTP response
  - Test `get_workflow_metadata()` parsing
  - Test error handling (registry down, invalid YAML)
  - Add `mock_oras_workflow_pull` fixture to `tests/fixtures/conftest.py`
  - Run: `uv run pytest tests/unit/test_workflow_registry.py -v`

### 8. Extend Discovery Module (`src/discovery.py`)
- Add `discover_workflow()` function:
  - Query registry for workflows
  - Pull workflow by ID
  - Parse and validate YAML
  - Return WorkflowDefinition object
- Add caching for discovered workflows
- Update module docstring to mention workflow discovery
- **Test**: Update `tests/unit/test_discovery.py`
  - Add tests for `discover_workflow()` function
  - Test workflow caching behavior
  - Test integration with existing discovery functions
  - Verify no regressions in existing discovery tests
  - Run: `uv run pytest tests/unit/test_discovery.py -v`

### 9. Create Example Workflow: Code Generation (`workflows/code-generation.yaml`)
- Define metadata (id: code-generation-v1, name, version, description)
- Create sequential pipeline:
  - Step 1: create_plan skill with requirements input
  - Step 2: generate_code skill with plan from step 1
  - Step 3: review_code skill with code from step 2
- Add template expressions for data flow
- Set reasonable timeouts per step
- Include error_handling configuration
- **Test**: Create `tests/workflows/` directory with test workflows
  - Copy code-generation.yaml to `tests/workflows/valid_code_generation.yaml`
  - Create `tests/workflows/invalid_syntax.yaml` (malformed YAML)
  - Create `tests/workflows/missing_required.yaml` (missing required fields)
  - Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('workflows/code-generation.yaml'))"`

### 10. Create Example Workflow: Smart Router (`workflows/smart-router.yaml`)
- Define metadata for routing workflow
- Create analysis step to detect request type
- Implement switch step:
  - Cases: code_generation, data_analysis, content_creation
  - Each case delegates to different workflow
  - Include default case
- Add condition evaluation examples
- Validate YAML syntax

### 11. Create Example Workflow: Parallel Analysis (`workflows/parallel-analysis.yaml`)
- Define metadata for parallel processing
- Create parallel step with multiple branches:
  - analyze_sentiment
  - extract_entities
  - classify_topics
- Show aggregation strategy (merge results)
- Include timeout for overall parallel execution
- Validate YAML syntax

### 12. Create Workflow Push Script (`scripts/push_workflows.sh`)
- Check ORAS is installed
- Check registry is running (curl localhost:5000/v2/)
- For each workflow YAML:
  - Push to registry: `oras push localhost:5000/workflows/{id}:v1 workflow.yaml:application/yaml`
  - Verify push succeeded
  - Print confirmation
- List all workflows in registry at end
- Make script executable: `chmod +x scripts/push_workflows.sh`
- Test script: `bash scripts/push_workflows.sh`

### 13. Update Bootstrap Script (`scripts/bootstrap.sh`)
- Add workflow push step after agent card push
- Call `bash scripts/push_workflows.sh`
- Verify workflows are in registry
- Update success message to mention workflows
- Test full bootstrap with workflows

### 14. Refactor Orchestrator (`src/orchestrator.py`)
- Import WorkflowEngine
- Add `execute_workflow_by_id()` function:
  - Discover workflow from registry
  - Load with WorkflowEngine
  - Execute with provided inputs
  - Return results
- Keep existing `orchestrate()` function for backward compatibility
- Add workflow_id parameter (optional)
- Update function to use workflow engine when workflow_id provided
- Add deprecation notice for hardcoded orchestration
- **Test**: Update `tests/unit/test_orchestrator.py`
  - Add tests for `execute_workflow_by_id()`
  - Test workflow loading and execution
  - Test backward compatibility - existing `orchestrate()` still works
  - Verify no regressions in existing orchestrator tests
  - Run: `uv run pytest tests/unit/test_orchestrator.py -v`

### 15. Update Main Entry Point (`main.py`)
- Add CLI argument for workflow ID: `--workflow` or `-w`
- Default to "code-generation-v1" if not specified
- Load workflow from registry using workflow ID
- Execute workflow with WorkflowEngine
- Print results
- Update help text with workflow examples
- **Test**: Update `tests/integration/test_end_to_end.py`
  - Add test for workflow-based execution path
  - Test CLI argument parsing for --workflow flag
  - Test default workflow behavior
  - Verify backward compatibility (no --workflow flag)
  - Test: `uv run python main.py --workflow code-generation-v1 "Create hello world"`
  - Run: `uv run pytest tests/integration/test_end_to_end.py -v`

### 16. Create Workflow Engine Documentation (`docs/WORKFLOW_ENGINE.md`)
- Overview of workflow-based orchestration
- Benefits over hardcoded workflows
- YAML workflow specification reference
- Template expression syntax guide
- Execution pattern examples (sequential, parallel, conditional, switch)
- Example workflows with explanations
- How to create custom workflows
- Registry operations for workflows
- Troubleshooting guide
- Follow structure from existing docs

### 17. Update Main README (`README.md`)
- Add section on workflow-based orchestration
- Update "What It Does" to mention workflow engine
- Add example of custom workflow execution
- Update architecture diagram to show workflow engine
- Add workflow files to project structure
- Link to new WORKFLOW_ENGINE.md documentation
- Update quick start to mention workflows

### 18. Add Integration Tests and Validate All Tests Pass
- Create `tests/integration/test_workflow_execution.py`:
  - Test full workflow execution with mocked agents
  - Test workflow discovery and loading from registry
  - Test data flow between steps in real scenarios
  - Test error scenarios (timeout, missing skill, invalid input)
  - Test parallel execution performance
  - Test conditional routing with different inputs
- Add workflow fixtures to `tests/fixtures/conftest.py`:
  - `sample_workflow_definition` fixture
  - `sample_workflow_yaml` fixture
  - `mock_workflow_registry` fixture
- **Validation Commands**:
  - Run: `uv run invoke test.unit` - All unit tests pass
  - Run: `uv run invoke test.integration` - All integration tests pass
  - Run: `uv run invoke test` - All tests pass (unit + integration)
  - Run: `uv run invoke test.coverage` - Generate coverage report
  - Verify: Coverage ≥87% (maintain existing coverage)
  - Run: `uv run invoke lint.black-check` - Code is formatted
  - Run: `uv run invoke lint.flake8` - No style violations

### 19. Test End-to-End with Existing Agents
- Start all services: `bash scripts/bootstrap.sh`
- List workflows: `python -c "from src.workflow_registry import list_workflows; print(list_workflows())"`
- Execute code-generation workflow: `uv run python main.py --workflow code-generation-v1 "Create a factorial function"`
- Verify results in app/ folder
- Check workflow outputs are correct
- Test with different workflows

### 20. Final Test Suite Validation and Quality Gates
- **Quality Gate 1: All Tests Pass**
  - Run: `uv run invoke test` - Must pass 100% of tests
  - Run: `uv run invoke test.verbose` - Review any warnings
  - Verify: All 151+ existing tests still pass (zero regressions)
  - Verify: All new workflow tests pass
- **Quality Gate 2: Code Coverage**
  - Run: `uv run invoke test.coverage-term` - Review coverage
  - Run: `uv run invoke test.coverage-html` - Generate HTML report
  - Verify: Overall coverage ≥87% (maintain or exceed existing)
  - Verify: New workflow code has ≥85% coverage
- **Quality Gate 3: Code Quality**
  - Run: `uv run invoke lint.black-check` - No formatting issues
  - Run: `uv run invoke lint.flake8` - No style violations
  - Fix any issues found
- **Quality Gate 4: Integration Validation**
  - Run: `bash scripts/bootstrap.sh` - All services start
  - Run: `uv run python main.py "Create factorial function"` - Works
  - Run: `uv run python main.py --workflow code-generation-v1 "..."` - Works
  - Run: `bash scripts/kill.sh` - Clean shutdown
- **Quality Gate 5: Backward Compatibility**
  - Verify Phase 5 behavior unchanged when --workflow not specified
  - Run existing integration tests - all pass
  - Verify existing orchestrator functions still work
- Execute all validation commands listed below
- Mark feature complete only when ALL quality gates pass

## Testing Strategy

### Manual Testing

1. **Workflow Creation and Push**
   - Create a new workflow YAML file
   - Validate YAML syntax
   - Push to registry with ORAS
   - Verify it appears in catalog

2. **Workflow Execution**
   - Execute code-generation workflow with sample requirements
   - Verify Plan → Build → Test pipeline works
   - Check outputs are saved correctly
   - Inspect logs for proper step execution

3. **Parallel Execution**
   - Execute parallel-analysis workflow
   - Verify all branches run simultaneously
   - Check results are properly merged
   - Measure execution time (should be faster than sequential)

4. **Conditional Routing**
   - Execute smart-router workflow with different input types
   - Verify correct workflow is selected based on request type
   - Test default fallback case
   - Check condition evaluation logic

5. **Template Resolution**
   - Inspect workflow context at each step
   - Verify data flows correctly between steps
   - Test nested template expressions
   - Check edge cases (missing keys, null values)

6. **Error Handling**
   - Test with invalid workflow YAML
   - Test with missing skills
   - Test with agent timeout
   - Verify error messages are helpful

### Edge Cases

- **Empty Workflow**: Workflow with no steps - should handle gracefully
- **Circular References**: Template referencing non-existent step - should error clearly
- **Invalid Skill ID**: Step requests skill that doesn't exist - discovery should fail with clear message
- **Missing Template Variables**: Expression refers to missing data - should return null or error
- **Agent Timeout**: Step takes longer than timeout - should cancel and report error
- **Registry Down**: Cannot connect to registry - should fail with connection error
- **Invalid YAML**: Malformed workflow file - should fail at parse time with line number
- **Version Conflicts**: Multiple versions of same workflow - should select correct version
- **Parallel Failures**: One branch fails in parallel execution - should handle partial results
- **Nested Workflows**: Workflow calling another workflow - should support or explicitly not support

## Acceptance Criteria

### Functionality
- [ ] WorkflowEngine can load and parse YAML workflow definitions
- [ ] Template expressions (`{{ steps.X.outputs.Y }}`) are resolved correctly
- [ ] Sequential execution pattern works (current Plan → Build → Test pipeline)
- [ ] Parallel execution pattern works (multiple agents execute simultaneously)
- [ ] Conditional execution pattern works (if/else branching)
- [ ] Switch execution pattern works (route based on value)
- [ ] Workflows can be pushed to and pulled from OCI registry
- [ ] Workflow discovery works (list available workflows)
- [ ] Orchestrator can execute workflows by ID
- [ ] Main entry point accepts workflow ID as CLI argument
- [ ] Example workflows (code-generation, smart-router, parallel-analysis) execute successfully
- [ ] Bootstrap script pushes workflows to registry
- [ ] Documentation explains workflow engine and YAML specification
- [ ] README updated with workflow-based orchestration information
- [ ] Backward compatibility maintained (existing orchestrator still works)

### Testing & Quality (CRITICAL)
- [ ] **All 151+ existing tests pass with zero regressions**
- [ ] Unit tests added for all new modules:
  - [ ] `tests/unit/test_workflow_models.py` (>90% coverage)
  - [ ] `tests/unit/test_workflow_context.py` (>90% coverage)
  - [ ] `tests/unit/test_workflow_engine.py` (>85% coverage)
  - [ ] `tests/unit/test_workflow_registry.py` (>80% coverage)
  - [ ] `tests/unit/test_discovery.py` updated (no regressions)
  - [ ] `tests/unit/test_orchestrator.py` updated (no regressions)
- [ ] Integration tests added:
  - [ ] `tests/integration/test_workflow_execution.py` (full workflow scenarios)
  - [ ] `tests/integration/test_end_to_end.py` updated (workflow path + backward compat)
- [ ] Test fixtures added to `tests/fixtures/conftest.py`:
  - [ ] `sample_workflow_definition`
  - [ ] `sample_workflow_yaml`
  - [ ] `mock_oras_workflow_pull`
  - [ ] `mock_workflow_registry`
- [ ] Test workflows in `tests/workflows/`:
  - [ ] Valid workflow examples
  - [ ] Invalid YAML examples
  - [ ] Edge case workflows
- [ ] **Overall test coverage ≥87% (maintain or exceed existing)**
- [ ] **New workflow code coverage ≥85%**
- [ ] `uv run invoke test` passes 100%
- [ ] `uv run invoke lint.black-check` passes
- [ ] `uv run invoke lint.flake8` passes with zero violations
- [ ] All validation commands (section below) execute successfully

## Validation Commands

Execute every command to validate the feature works correctly with zero regressions.

```bash
# 1. Verify Python syntax for all new files
python -c "import ast; ast.parse(open('src/workflow_engine.py').read())"
python -c "import ast; ast.parse(open('src/workflow_registry.py').read())"

# 2. Verify YAML syntax for workflow files
python -c "import yaml; yaml.safe_load(open('workflows/code-generation.yaml'))"
python -c "import yaml; yaml.safe_load(open('workflows/smart-router.yaml'))"
python -c "import yaml; yaml.safe_load(open('workflows/parallel-analysis.yaml'))"

# 3. Verify dependencies installed
uv sync
python -c "import yaml; print(f'PyYAML {yaml.__version__}')"

# 4. Start all services (includes workflow push)
bash scripts/bootstrap.sh

# 5. Verify workflows are in registry
curl -s http://localhost:5000/v2/_catalog | jq '.repositories' | grep workflows

# 6. List workflows programmatically
python -c "from src.workflow_registry import list_workflows; workflows = list_workflows(); print(f'Found {len(workflows)} workflows'); print(workflows)"

# 7. Execute code-generation workflow (default)
uv run python main.py "Create a function to calculate prime numbers"

# 8. Execute workflow by explicit ID
uv run python main.py --workflow code-generation-v1 "Create a hello world function"

# 9. Verify outputs created
ls -lh app/
cat app/metadata.json | jq '.workflow_id'

# 10. Test workflow engine directly
python -c "
import asyncio
from src.workflow_engine import WorkflowEngine

async def test():
    engine = WorkflowEngine()
    yaml_content = open('workflows/code-generation.yaml').read()
    workflow = engine.load_workflow(yaml_content)
    print(f'Loaded: {workflow.metadata[\"name\"]}')
    print(f'Steps: {len(workflow.steps)}')
    
asyncio.run(test())
"

# 11. Test template resolution
python -c "
from src.workflow_engine import WorkflowContext

ctx = WorkflowContext({'test': 'value'})
ctx.set_step_output('step1', {'result': 'data'})
resolved = ctx.resolve_expression('{{ steps.step1.outputs.result }}')
assert resolved == 'data', f'Expected data, got {resolved}'
print('✓ Template resolution works')
"

# 12. Run unit tests (if implemented)
uv run pytest tests/ -v

# 13. Verify backward compatibility - existing orchestration still works
python -c "
from src.orchestrator import orchestrate
print('✓ Backward compatible orchestrate function exists')
"

# 14. Test workflow push script
bash scripts/push_workflows.sh

# 15. Verify all services are running
curl -s http://localhost:8001/agent-card | jq '.name'
curl -s http://localhost:8002/agent-card | jq '.name'
curl -s http://localhost:8003/agent-card | jq '.name'
curl -s http://localhost:5000/v2/_catalog | jq '.repositories | length'

# 16. Verify no Python import errors
python -c "from src.workflow_engine import WorkflowEngine, WorkflowContext, WorkflowDefinition, WorkflowStep; print('✓ All imports successful')"
python -c "from src.workflow_registry import push_workflow_to_registry, pull_workflow_from_registry, list_workflows; print('✓ Registry functions import successfully')"

# 17. Stop all services
bash scripts/kill.sh
```

## Notes

### Design Decisions

**YAML vs JSON**: YAML chosen for workflows because:
- More human-readable for complex nested structures
- Native support for comments
- Less verbose than JSON for configuration files
- Widely used in workflow systems (GitHub Actions, Kubernetes, etc.)

**Template Syntax**: Using `{{ variable.path }}` syntax because:
- Familiar to users of Jinja2, Ansible, GitHub Actions
- Clear distinction from regular strings
- Easy to parse with regex
- Supports nested paths with dot notation

**Registry Storage**: Storing workflows in OCI registry because:
- Consistent with agent cards (same infrastructure)
- Built-in versioning (tags)
- Can use existing ORAS tooling
- Centralized storage
- Enables workflow sharing across systems

**Execution Patterns**: Supporting multiple patterns because:
- Sequential: Most common, existing pattern
- Parallel: Performance optimization for independent tasks
- Conditional: Decision trees, error handling
- Switch: Dynamic routing based on content
- These cover 95% of orchestration use cases

### Future Enhancements

Not included in this phase but could be added later:
- **Workflow composition**: Workflows calling other workflows (sub-workflows)
- **Loop patterns**: Map-reduce, for-each over collections
- **Advanced error handling**: Retry with exponential backoff, circuit breakers
- **Workflow scheduling**: Cron-style execution, event triggers
- **Workflow visualization**: Generate diagrams from YAML
- **Workflow validation**: Lint workflows for common mistakes
- **Workflow testing**: Unit test framework for workflows
- **Performance optimizations**: Parallel discovery, connection pooling
- **Monitoring**: Metrics, tracing, logging integration
- **State persistence**: Save workflow state between steps
- **Human-in-the-loop**: Pause for approval, input during execution

### Migration Path from Phase 5

Existing code continues to work:
1. Keep `src/orchestrator.py` with hardcoded workflow as fallback
2. `main.py` defaults to code-generation-v1 workflow if no --workflow specified
3. Old function signatures remain available (deprecated but functional)
4. Bootstrap script works with or without workflows

Users can migrate gradually:
1. Phase 5 → Phase 6: No code changes needed, existing behavior preserved
2. Opt-in to workflows: Pass --workflow flag to use new engine
3. Create custom workflows: Add YAML files and push to registry
4. Eventually deprecate hardcoded orchestration in future phase

### Security Considerations

- **YAML Injection**: Use `yaml.safe_load()` to prevent arbitrary code execution
- **Template Injection**: Limited expression syntax, no arbitrary Python eval
- **Registry Access**: No authentication in Phase 6, add in production
- **Agent Trust**: Assume agents are trusted (same as Phase 5)
- **Input Validation**: Validate workflow structure before execution
- **Resource Limits**: Enforce timeouts to prevent infinite loops

---

**Implementation Status**: ⏸️ Planning Complete - Ready for BUILD stage

This specification provides a complete, actionable plan for implementing workflow-based orchestration in the Pallet framework. The feature builds on existing Phase 5 infrastructure while maintaining backward compatibility and adding powerful new capabilities for declarative workflow management.
