"""
Workflow Engine - Data Models and Context Management.

This module provides the foundation for the workflow engine:
- Data models for workflows (WorkflowDefinition, WorkflowStep, StepType)
- WorkflowContext for managing execution state
- Template expression resolution ({{ variable.path }} syntax)
- YAML loading and validation
"""

import re
import yaml
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Enumeration of workflow step execution patterns."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    SWITCH = "switch"


class WorkflowStep(BaseModel):
    """Represents a single step in a workflow."""

    id: str = Field(..., description="Unique step identifier")
    skill: str = Field(..., description="Skill ID to execute")
    inputs: Dict[str, Any] = Field(
        default_factory=dict, description="Input parameters (can contain templates)"
    )
    outputs: Optional[str] = Field(None, description="Output variable name")
    timeout: Optional[int] = Field(300, description="Timeout in seconds")
    step_type: StepType = Field(StepType.SEQUENTIAL, description="Execution pattern")
    condition: Optional[str] = Field(
        None, description="Condition expression for CONDITIONAL type"
    )
    branches: Optional[Dict[str, Any]] = Field(
        None, description="Branches for SWITCH/CONDITIONAL types"
    )


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
    error_handling: Optional[Dict[str, Any]] = Field(
        None, description="Error handling config"
    )


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
        match = re.match(r"{{\s*(.+?)\s*}}", expression.strip())
        if not match:
            return expression  # Not a template

        path = match.group(1).split(".")

        # Resolve path in context
        if path[0] == "workflow" and path[1] == "input":
            data = self.workflow_input
            path = path[2:]  # Skip 'workflow.input'
        elif path[0] == "steps":
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
                resolved[key] = [
                    self.resolve_expression(v) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                resolved[key] = value
        return resolved


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
    if isinstance(yaml_content, Path) or (
        isinstance(yaml_content, str)
        and "\n" not in yaml_content
        and len(yaml_content) < 255
    ):
        # Treat as file path
        with open(yaml_content, "r") as f:
            data = yaml.safe_load(f)
    else:
        # Treat as YAML string
        data = yaml.safe_load(yaml_content)

    return WorkflowDefinition(**data)
