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

```bash
# Use default workflow
python main.py "Create a hello world function"

# Specify workflow explicitly
python main.py --workflow code-generation-v1 "Create factorial function"
```

### List Available Workflows

```python
from src.workflow_registry import list_workflows

workflows = list_workflows()
print(f"Found {len(workflows)} workflows: {workflows}")
```

## Workflow YAML Specification

### Basic Structure

```yaml
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
```

### Template Expressions

Access workflow input and step outputs using `{{ }}` syntax:

```yaml
inputs:
  # Access workflow input
  requirements: "{{ workflow.input.requirements }}"

  # Access previous step output
  plan: "{{ steps.plan.outputs.result }}"

  # Nested paths
  code: "{{ steps.build.outputs.result.code }}"
```

### Execution Patterns

#### Sequential (default)

Execute steps one after another:

```yaml
steps:
  - id: step1
    skill: skill1
    step_type: sequential

  - id: step2
    skill: skill2
    step_type: sequential
```

#### Parallel

Execute multiple steps concurrently:

```yaml
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
```

#### Conditional

Branch based on condition:

```yaml
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
```

#### Switch

Route based on value:

```yaml
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
```

## Registry Operations

### Push Workflow

```bash
oras push localhost:5000/workflows/my-workflow:v1 my-workflow.yaml:application/yaml
```

### Pull Workflow

```python
from src.workflow_registry import pull_workflow_from_registry

workflow_path = pull_workflow_from_registry("my-workflow", "v1")
```

### List Workflows

```bash
curl -s http://localhost:5000/v2/_catalog | jq '.repositories | map(select(startswith("workflows/")))'
```

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
