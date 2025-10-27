# Workflow-Based Orchestration - Implementation Guide

This directory contains the breakdown of `specs/6-workflows.md` into logical, testable parts. Each part can be built and tested independently before moving to the next.

## Overview

The workflow feature adds declarative, YAML-based workflow definitions to Pallet, decoupling workflow logic from the orchestrator implementation. Workflows are stored in the OCI registry as versioned artifacts.

**Original Spec**: [../6-workflows.md](../6-workflows.md) (kept intact for reference)

## Implementation Parts

### Part 1: Data Models & Context (Foundation)
**File**: [part1-data-models.md](part1-data-models.md)
**Status**: 🔴 Not Started
**Dependencies**: None
**Testing**: Unit tests only

**Scope**:
- Pydantic models (WorkflowDefinition, WorkflowStep, StepType enum)
- WorkflowContext for managing execution state
- Template expression resolution (`{{ variable.path }}` syntax)
- YAML loading and validation

**Key Deliverables**:
- `src/workflow_engine.py` (Part 1)
- `tests/unit/test_workflow_models.py`
- `tests/unit/test_workflow_context.py`

**Acceptance**: All models validate, template resolution works, >90% coverage

---

### Part 2: Core Workflow Engine (Execution Patterns)
**File**: [part2-core-engine.md](part2-core-engine.md)
**Status**: 🔴 Not Started
**Dependencies**: Part 1 complete
**Testing**: Unit + Integration tests

**Scope**:
- WorkflowEngine class
- Sequential, parallel, conditional, switch execution patterns
- Agent discovery integration per step
- Timeout handling

**Key Deliverables**:
- `src/workflow_engine.py` (Part 2 - extends Part 1)
- `tests/unit/test_workflow_engine.py`
- `tests/integration/test_workflow_execution.py`

**Acceptance**: All execution patterns work, >85% coverage, agent calls mocked

---

### Part 3: Registry Integration (Storage & Discovery)
**File**: [part3-registry-integration.md](part3-registry-integration.md)
**Status**: 🔴 Not Started
**Dependencies**: Part 1, Part 2 complete
**Testing**: Unit tests

**Scope**:
- Push/pull workflows to/from OCI registry via ORAS
- List available workflows
- Extend discovery module for workflows
- `push_workflows.sh` script
- Update `bootstrap.sh`

**Key Deliverables**:
- `src/workflow_registry.py`
- `src/discovery.py` (extended)
- `scripts/push_workflows.sh`
- `tests/unit/test_workflow_registry.py`

**Acceptance**: Registry operations work, workflows discoverable, >80% coverage

---

### Part 4: Orchestrator Integration & Examples
**File**: [part4-orchestrator-integration.md](part4-orchestrator-integration.md)
**Status**: 🔴 Not Started
**Dependencies**: Part 1, 2, 3 complete
**Testing**: Integration + E2E tests

**Scope**:
- Example workflow YAML files (code-generation, smart-router, parallel-analysis)
- Refactor orchestrator to use workflow engine
- Update main.py CLI with `--workflow` flag
- Documentation (WORKFLOW_ENGINE.md, README updates)
- Full validation suite

**Key Deliverables**:
- `workflows/code-generation.yaml`
- `workflows/smart-router.yaml`
- `workflows/parallel-analysis.yaml`
- `src/orchestrator.py` (updated)
- `main.py` (updated)
- `docs/WORKFLOW_ENGINE.md`
- `tests/integration/test_end_to_end.py` (updated)

**Acceptance**: E2E workflows execute, backward compatibility maintained, ≥87% coverage

---

## How to Use This Guide

### Sequential Implementation

Build the feature **in order**, completing each part before moving to the next:

```bash
# Part 1: Foundation
cd /path/to/pallet
# Follow specs/6-workflows/part1-data-models.md
# Run tests: uv run pytest tests/unit/test_workflow_*.py -v
# Verify: All tests pass, >90% coverage

# Part 2: Engine
# Follow specs/6-workflows/part2-core-engine.md
# Run tests: uv run invoke test.unit
# Verify: All tests pass, >85% coverage

# Part 3: Registry
# Follow specs/6-workflows/part3-registry-integration.md
# Run tests: uv run pytest tests/unit/test_workflow_registry.py -v
# Verify: All tests pass, >80% coverage

# Part 4: Integration
# Follow specs/6-workflows/part4-orchestrator-integration.md
# Run tests: uv run invoke test
# Verify: All tests pass, ≥87% coverage, E2E works
```

### Quality Gates

Each part must meet these criteria before proceeding:

✅ **All tests pass** (including existing tests - zero regressions)
✅ **Coverage targets met** (stated in each part's acceptance criteria)
✅ **Linting passes** (`uv run invoke lint.black-check && uv run invoke lint.flake8`)
✅ **Validation commands execute successfully** (listed at end of each part)

### Testing Strategy

- **Part 1**: Pure unit tests (no mocking needed, data layer only)
- **Part 2**: Unit tests with mocked agents, integration tests
- **Part 3**: Unit tests with mocked subprocess/HTTP calls
- **Part 4**: Integration tests + E2E manual testing

### Context Window Management

Each part is designed to fit in Claude Code's context window:

- **Part 1**: ~150 lines of code, ~200 lines of tests
- **Part 2**: ~300 lines of code, ~400 lines of tests
- **Part 3**: ~200 lines of code, ~300 lines of tests
- **Part 4**: ~300 lines of code + YAML files, ~200 lines of tests

Total implementation: ~1000 lines of production code, ~1100 lines of tests

## File Structure

After completing all parts, the project will have:

```
specs/
  6-workflows.md                      # Original spec (intact)
  6-workflows/                        # Breakdown (this directory)
    README.md                         # This file
    part1-data-models.md              # Foundation
    part2-core-engine.md              # Execution
    part3-registry-integration.md     # Storage
    part4-orchestrator-integration.md # Integration

src/
  workflow_engine.py                  # Parts 1 & 2
  workflow_registry.py                # Part 3
  orchestrator.py                     # Part 4 (updated)
  discovery.py                        # Part 3 (updated)

workflows/
  code-generation.yaml                # Part 4
  smart-router.yaml                   # Part 4
  parallel-analysis.yaml              # Part 4

tests/
  unit/
    test_workflow_models.py           # Part 1
    test_workflow_context.py          # Part 1
    test_workflow_engine.py           # Part 2
    test_workflow_registry.py         # Part 3
    test_discovery.py                 # Part 3 (updated)
    test_orchestrator.py              # Part 4 (updated)
  integration/
    test_workflow_execution.py        # Part 2 & 4
    test_end_to_end.py                # Part 4 (updated)
  workflows/                          # Part 4
    valid_simple.yaml
    invalid_syntax.yaml
    missing_required.yaml

scripts/
  push_workflows.sh                   # Part 3
  bootstrap.sh                        # Part 3 (updated)

docs/
  WORKFLOW_ENGINE.md                  # Part 4

main.py                               # Part 4 (updated)
README.md                             # Part 4 (updated)
```

## Dependencies

### External Dependencies
- `pyyaml>=6.0` (Part 1)
- Existing: `pydantic`, `httpx`, `fastapi`, `oras`

### Internal Dependencies
- Part 2 depends on Part 1 models
- Part 3 depends on Part 1 (models) and Part 2 (engine)
- Part 4 depends on all previous parts

## Validation Checkpoints

### After Part 1
```bash
uv run pytest tests/unit/test_workflow_models.py tests/unit/test_workflow_context.py -v --cov=src.workflow_engine --cov-report=term-missing
# Expected: All pass, >90% coverage
```

### After Part 2
```bash
uv run pytest tests/unit/test_workflow_engine.py tests/integration/test_workflow_execution.py -v --cov=src.workflow_engine
# Expected: All pass, >85% coverage
```

### After Part 3
```bash
uv run pytest tests/unit/test_workflow_registry.py tests/unit/test_discovery.py -v
bash scripts/push_workflows.sh  # Manual test
# Expected: All pass, registry operations work
```

### After Part 4 (Final)
```bash
uv run invoke test                    # All tests
uv run invoke test.coverage           # Coverage report
uv run invoke lint.black-check        # Formatting
uv run invoke lint.flake8             # Style

bash scripts/bootstrap.sh             # Start services
uv run python main.py "test"          # E2E test
bash scripts/kill.sh --clean-logs     # Cleanup

# Expected: 100% tests pass, ≥87% coverage, E2E works
```

## Backward Compatibility

The feature maintains backward compatibility with Phase 5:

- ✅ Existing `orchestrate()` function still works (delegates to workflow engine)
- ✅ Existing tests pass without modification
- ✅ Default workflow (`code-generation-v1`) replicates Phase 5 behavior
- ✅ CLI works without `--workflow` flag (uses default)
- ✅ Agent discovery unchanged
- ✅ Registry operations extend existing pattern

## Success Criteria

The feature is complete when **ALL** of the following are true:

### Functionality
- [ ] All 4 parts implemented
- [ ] All example workflows created and valid
- [ ] Orchestrator uses workflow engine
- [ ] CLI accepts workflow IDs
- [ ] Results saved correctly
- [ ] Documentation complete

### Testing
- [ ] **All 151+ existing tests pass (zero regressions)**
- [ ] All new unit tests pass
- [ ] All integration tests pass
- [ ] Overall coverage ≥87%
- [ ] Workflow code coverage ≥85%

### Quality
- [ ] No linting errors
- [ ] No type errors
- [ ] All validation commands pass

### E2E
- [ ] Bootstrap starts services + pushes workflows
- [ ] Default workflow executes successfully
- [ ] Custom workflow executes successfully
- [ ] Backward compatibility verified
- [ ] Clean shutdown works

## Troubleshooting

### Part 1 Issues
- **Import errors**: Verify `pyyaml` installed with `uv sync`
- **Template resolution fails**: Check regex pattern in `resolve_expression()`
- **Validation errors**: Review Pydantic model field requirements

### Part 2 Issues
- **Async errors**: Ensure using `@pytest.mark.asyncio` decorator
- **Agent discovery fails**: Check mocking in tests
- **Timeout not working**: Verify `asyncio.TimeoutError` handling

### Part 3 Issues
- **ORAS not found**: Run `bash scripts/install-oras.sh`
- **Registry connection fails**: Check `docker ps | grep registry`
- **Subprocess errors**: Mock with `patch('subprocess.run')`

### Part 4 Issues
- **E2E test fails**: Ensure all agents running with `bash scripts/bootstrap.sh`
- **CLI not working**: Check argparse configuration
- **Results not saved**: Verify `app/` directory creation

## References

- Original spec: [specs/6-workflows.md](../6-workflows.md)
- Project README: [README.md](../../README.md)
- Claude guidance: [CLAUDE.md](../../CLAUDE.md)
- Test documentation: [tests/README.md](../../tests/README.md)

---

**Implementation Status**: ⏸️ Planning Complete - Ready to BUILD Part 1

Start with [Part 1: Data Models & Context](part1-data-models.md)
