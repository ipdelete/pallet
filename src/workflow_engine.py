"""
Workflow Engine - Data Models and Context Management.

This module provides the foundation for the workflow engine:
- Data models for workflows (WorkflowDefinition, WorkflowStep, StepType)
- WorkflowContext for managing execution state
- Template expression resolution ({{ variable.path }} syntax)
- YAML loading and validation
- WorkflowEngine for executing workflows with various patterns
"""

import re
import yaml
import asyncio
import httpx
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from src.discovery import discover_agent
from src.logging_config import configure_module_logging

logger = configure_module_logging("workflow_engine")


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

        # Use existing discovery module (run in thread pool since it's sync)
        loop = asyncio.get_event_loop()
        agent_url = await loop.run_in_executor(None, discover_agent, skill_id)
        if not agent_url:
            raise ValueError(f"No agent found for skill: {skill_id}")

        self.agent_cache[skill_id] = agent_url
        return agent_url

    async def call_agent_skill(
        self,
        agent_url: str,
        skill_id: str,
        params: Dict[str, Any],
        timeout: int = 300,
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
                    "id": "1",
                },
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise RuntimeError(f"Agent error: {result['error']}")

            return result.get("result", {})

    async def execute_step(
        self, step: WorkflowStep, context: WorkflowContext
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
                timeout=step.timeout or 300,
            )

            print(f"[WorkflowEngine] Step {step.id} completed successfully")
            return result

        except asyncio.TimeoutError:
            raise RuntimeError(f"Step {step.id} timed out after {step.timeout}s")
        except Exception as e:
            raise RuntimeError(f"Step {step.id} failed: {str(e)}")

    async def execute_sequential_steps(
        self, steps: List[WorkflowStep], context: WorkflowContext
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

    async def execute_parallel_steps(
        self, steps: List[WorkflowStep], context: WorkflowContext
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

        print("[WorkflowEngine] All parallel steps completed")
        return context

    async def execute_conditional_step(
        self, step: WorkflowStep, context: WorkflowContext
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
            print(
                f"[WorkflowEngine] Condition true, executing if_true branch "
                f"({len(branch_steps)} steps)"
            )
        else:
            branch_steps = step.branches.get("if_false", [])
            print(
                f"[WorkflowEngine] Condition false, executing if_false branch "
                f"({len(branch_steps)} steps)"
            )

        # Execute branch
        for branch_step_data in branch_steps:
            branch_step = WorkflowStep(**branch_step_data)
            result = await self.execute_step(branch_step, context)
            context.set_step_output(branch_step.id, result)

        return context

    async def execute_switch_step(
        self, step: WorkflowStep, context: WorkflowContext
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
        branch_steps = step.branches.get(matched_case) or step.branches.get(
            "default", []
        )

        if not branch_steps:
            print(f"[WorkflowEngine] No matching case for '{switch_value}', skipping")
            return context

        print(
            f"[WorkflowEngine] Executing case '{matched_case}' "
            f"({len(branch_steps)} steps)"
        )

        # Execute matched branch
        for branch_step_data in branch_steps:
            branch_step = WorkflowStep(**branch_step_data)
            result = await self.execute_step(branch_step, context)
            context.set_step_output(branch_step.id, result)

        return context

    async def execute_workflow(
        self, workflow: WorkflowDefinition, initial_input: Dict[str, Any]
    ) -> WorkflowContext:
        """
        Execute a complete workflow.

        Args:
            workflow: WorkflowDefinition to execute
            initial_input: Initial input data

        Returns:
            Final workflow context with all step outputs
        """
        workflow_start = time.time()
        logger.info(f"Starting workflow: {workflow.metadata.name}")
        logger.info(f"Workflow ID: {workflow.metadata.id}")
        logger.info(f"Workflow version: {workflow.metadata.version}")
        logger.info(f"Number of steps: {len(workflow.steps)}")
        logger.debug(f"Workflow description: {workflow.metadata.description}")
        logger.debug(f"Initial input: {initial_input}")

        # Initialize context
        context = WorkflowContext(initial_input)

        # Execute steps
        step_times = {}
        for step in workflow.steps:
            logger.info(f"Processing step: {step.id} (type: {step.step_type})")
            logger.debug(f"Step skill: {step.skill}")
            step_start = time.time()

            try:
                if step.step_type == StepType.SEQUENTIAL:
                    result = await self.execute_step(step, context)
                    # Store output in context
                    if step.outputs:
                        context.set_step_output(step.id, {step.outputs: result})
                    else:
                        context.set_step_output(step.id, result)

                elif step.step_type == StepType.PARALLEL:
                    # For parallel, step.branches should contain list of steps
                    if not step.branches or "steps" not in step.branches:
                        raise ValueError(
                            f"Parallel step {step.id} missing 'steps' in branches"
                        )
                    parallel_steps = [WorkflowStep(**s) for s in step.branches["steps"]]
                    await self.execute_parallel_steps(parallel_steps, context)

                elif step.step_type == StepType.CONDITIONAL:
                    await self.execute_conditional_step(step, context)

                elif step.step_type == StepType.SWITCH:
                    await self.execute_switch_step(step, context)

                else:
                    raise ValueError(f"Unknown step type: {step.step_type}")

                elapsed = time.time() - step_start
                step_times[step.id] = elapsed
                logger.info(f"Step {step.id} completed in {elapsed:.2f}s")

            except Exception as e:
                elapsed = time.time() - step_start
                logger.error(
                    f"Step {step.id} failed after {elapsed:.2f}s: {e}", exc_info=True
                )
                raise

        total_elapsed = time.time() - workflow_start
        logger.info(f"Workflow completed: {workflow.metadata.name}")
        logger.info(f"Total execution time: {total_elapsed:.2f}s")
        for step_id, step_time in step_times.items():
            logger.info(f"  - {step_id}: {step_time:.2f}s")
        return context
