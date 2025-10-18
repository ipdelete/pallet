"""
Integration tests for workflow execution.

Tests end-to-end workflow execution with mocked agents:
- Sequential workflows
- Parallel workflows
- Conditional workflows
- Switch workflows
- Complex multi-step workflows
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from src.workflow_engine import (
    WorkflowEngine,
    load_workflow_from_yaml,
    WorkflowDefinition,
    WorkflowMetadata,
    WorkflowStep,
    StepType,
)


class TestSequentialWorkflowIntegration:
    """Integration tests for sequential workflows."""

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

        with patch(
            "src.workflow_engine.discover_agent",
            return_value="http://localhost:8001",
        ):
            with patch.object(
                engine,
                "call_agent_skill",
                AsyncMock(
                    side_effect=[
                        {"plan_data": "structured plan"},
                        {"code": "def test(): pass"},
                    ]
                ),
            ):
                context = await engine.execute_workflow(
                    workflow, {"requirements": "test requirement"}
                )

                assert "step1" in context.step_outputs
                assert "step2" in context.step_outputs
                assert (
                    context.step_outputs["step1"]["outputs"]["plan"]["plan_data"]
                    == "structured plan"
                )

    @pytest.mark.asyncio
    async def test_three_step_sequential_workflow(self):
        """Test three-step sequential workflow (Plan → Build → Test)."""
        yaml_content = """
metadata:
  id: plan-build-test
  name: Plan Build Test
  version: 1.0.0
steps:
  - id: plan
    skill: create_plan
    inputs:
      requirements: "{{ workflow.input.requirements }}"
    outputs: plan_result
  - id: build
    skill: generate_code
    inputs:
      plan: "{{ steps.plan.outputs.plan_result }}"
    outputs: code_result
  - id: test
    skill: review_code
    inputs:
      code: "{{ steps.build.outputs.code_result }}"
      language: python
    outputs: review_result
"""
        workflow = load_workflow_from_yaml(yaml_content)
        engine = WorkflowEngine()

        with patch(
            "src.workflow_engine.discover_agent",
            side_effect=[
                "http://localhost:8001",
                "http://localhost:8002",
                "http://localhost:8003",
            ],
        ):
            with patch.object(
                engine,
                "call_agent_skill",
                AsyncMock(
                    side_effect=[
                        {"steps": ["step1", "step2"]},
                        {"code": "def main(): pass"},
                        {"quality_score": 9, "approved": True},
                    ]
                ),
            ):
                context = await engine.execute_workflow(
                    workflow, {"requirements": "create a calculator"}
                )

                assert "plan" in context.step_outputs
                assert "build" in context.step_outputs
                assert "test" in context.step_outputs


class TestParallelWorkflowIntegration:
    """Integration tests for parallel workflows."""

    @pytest.mark.asyncio
    async def test_parallel_workflow_execution(self):
        """Test parallel workflow with multiple concurrent steps."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(
                id="test-parallel", name="Test Parallel", version="1.0.0"
            ),
            steps=[
                WorkflowStep(
                    id="parallel_group",
                    skill="parallel_skill",
                    step_type=StepType.PARALLEL,
                    branches={
                        "steps": [
                            {
                                "id": "fetch_data_a",
                                "skill": "fetch_skill",
                                "inputs": {"source": "a"},
                            },
                            {
                                "id": "fetch_data_b",
                                "skill": "fetch_skill",
                                "inputs": {"source": "b"},
                            },
                            {
                                "id": "fetch_data_c",
                                "skill": "fetch_skill",
                                "inputs": {"source": "c"},
                            },
                        ]
                    },
                ),
            ],
        )

        engine = WorkflowEngine()

        with patch(
            "src.workflow_engine.discover_agent",
            return_value="http://localhost:8001",
        ):
            with patch.object(
                engine,
                "call_agent_skill",
                AsyncMock(return_value={"data": "fetched"}),
            ) as mock_call:
                context = await engine.execute_workflow(workflow, {})

                # All three steps should complete
                assert "fetch_data_a" in context.step_outputs
                assert "fetch_data_b" in context.step_outputs
                assert "fetch_data_c" in context.step_outputs

                # All should be called concurrently (total 3 calls)
                assert mock_call.call_count == 3


class TestConditionalWorkflowIntegration:
    """Integration tests for conditional workflows."""

    @pytest.mark.asyncio
    async def test_conditional_workflow_true_branch(self):
        """Test conditional workflow executes true branch."""
        yaml_content = """
metadata:
  id: test-conditional
  name: Test Conditional
  version: 1.0.0
steps:
  - id: conditional_step
    skill: conditional_skill
    step_type: conditional
    condition: "{{ workflow.input.use_advanced }}"
    branches:
      if_true:
        - id: advanced_processing
          skill: advanced_skill
          inputs:
            data: "{{ workflow.input.data }}"
      if_false:
        - id: basic_processing
          skill: basic_skill
          inputs:
            data: "{{ workflow.input.data }}"
"""
        workflow = load_workflow_from_yaml(yaml_content)
        engine = WorkflowEngine()

        with patch(
            "src.workflow_engine.discover_agent",
            return_value="http://localhost:8001",
        ):
            with patch.object(
                engine,
                "call_agent_skill",
                AsyncMock(return_value={"result": "advanced_output"}),
            ):
                context = await engine.execute_workflow(
                    workflow, {"use_advanced": True, "data": "test"}
                )

                assert "advanced_processing" in context.step_outputs
                assert "basic_processing" not in context.step_outputs

    @pytest.mark.asyncio
    async def test_conditional_workflow_false_branch(self):
        """Test conditional workflow executes false branch."""
        yaml_content = """
metadata:
  id: test-conditional
  name: Test Conditional
  version: 1.0.0
steps:
  - id: conditional_step
    skill: conditional_skill
    step_type: conditional
    condition: "{{ workflow.input.use_advanced }}"
    branches:
      if_true:
        - id: advanced_processing
          skill: advanced_skill
      if_false:
        - id: basic_processing
          skill: basic_skill
"""
        workflow = load_workflow_from_yaml(yaml_content)
        engine = WorkflowEngine()

        with patch(
            "src.workflow_engine.discover_agent",
            return_value="http://localhost:8001",
        ):
            with patch.object(
                engine,
                "call_agent_skill",
                AsyncMock(return_value={"result": "basic_output"}),
            ):
                context = await engine.execute_workflow(
                    workflow, {"use_advanced": False}
                )

                assert "basic_processing" in context.step_outputs
                assert "advanced_processing" not in context.step_outputs


class TestSwitchWorkflowIntegration:
    """Integration tests for switch workflows."""

    @pytest.mark.asyncio
    async def test_switch_workflow_matches_case(self):
        """Test switch workflow routes to correct case."""
        yaml_content = """
metadata:
  id: test-switch
  name: Test Switch
  version: 1.0.0
steps:
  - id: switch_step
    skill: switch_skill
    step_type: switch
    condition: "{{ workflow.input.operation }}"
    branches:
      add:
        - id: add_operation
          skill: add_skill
          inputs:
            values: "{{ workflow.input.values }}"
      multiply:
        - id: multiply_operation
          skill: multiply_skill
          inputs:
            values: "{{ workflow.input.values }}"
      default:
        - id: default_operation
          skill: default_skill
"""
        workflow = load_workflow_from_yaml(yaml_content)
        engine = WorkflowEngine()

        with patch(
            "src.workflow_engine.discover_agent",
            return_value="http://localhost:8001",
        ):
            with patch.object(
                engine, "call_agent_skill", AsyncMock(return_value={"result": 15})
            ):
                context = await engine.execute_workflow(
                    workflow, {"operation": "add", "values": [5, 10]}
                )

                assert "add_operation" in context.step_outputs
                assert "multiply_operation" not in context.step_outputs
                assert "default_operation" not in context.step_outputs

    @pytest.mark.asyncio
    async def test_switch_workflow_default_case(self):
        """Test switch workflow falls back to default."""
        yaml_content = """
metadata:
  id: test-switch
  name: Test Switch
  version: 1.0.0
steps:
  - id: switch_step
    skill: switch_skill
    step_type: switch
    condition: "{{ workflow.input.operation }}"
    branches:
      add:
        - id: add_operation
          skill: add_skill
      multiply:
        - id: multiply_operation
          skill: multiply_skill
      default:
        - id: default_operation
          skill: default_skill
"""
        workflow = load_workflow_from_yaml(yaml_content)
        engine = WorkflowEngine()

        with patch(
            "src.workflow_engine.discover_agent",
            return_value="http://localhost:8001",
        ):
            with patch.object(
                engine,
                "call_agent_skill",
                AsyncMock(return_value={"result": "default"}),
            ):
                context = await engine.execute_workflow(
                    workflow, {"operation": "unknown"}
                )

                assert "default_operation" in context.step_outputs
                assert "add_operation" not in context.step_outputs


class TestComplexWorkflowIntegration:
    """Integration tests for complex multi-pattern workflows."""

    @pytest.mark.asyncio
    async def test_complex_workflow_with_multiple_patterns(self):
        """Test workflow combining sequential, parallel, and conditional steps."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(
                id="complex-workflow", name="Complex Workflow", version="1.0.0"
            ),
            steps=[
                # Step 1: Sequential preprocessing
                WorkflowStep(
                    id="preprocess",
                    skill="preprocess_skill",
                    inputs={"data": "{{ workflow.input.data }}"},
                    outputs="preprocessed",
                ),
                # Step 2: Parallel processing
                WorkflowStep(
                    id="parallel_processing",
                    skill="parallel_skill",
                    step_type=StepType.PARALLEL,
                    branches={
                        "steps": [
                            {
                                "id": "analyze_a",
                                "skill": "analyze_skill",
                                "inputs": {
                                    "data": "{{ steps.preprocess.outputs.preprocessed }}"
                                },
                            },
                            {
                                "id": "analyze_b",
                                "skill": "analyze_skill",
                                "inputs": {
                                    "data": "{{ steps.preprocess.outputs.preprocessed }}"
                                },
                            },
                        ]
                    },
                ),
                # Step 3: Conditional based on results
                WorkflowStep(
                    id="conditional_post",
                    skill="conditional_skill",
                    step_type=StepType.CONDITIONAL,
                    condition="{{ workflow.input.detailed }}",
                    branches={
                        "if_true": [{"id": "detailed_report", "skill": "report_skill"}],
                        "if_false": [
                            {"id": "summary_report", "skill": "summary_skill"}
                        ],
                    },
                ),
            ],
        )

        engine = WorkflowEngine()

        with patch(
            "src.workflow_engine.discover_agent",
            return_value="http://localhost:8001",
        ):
            with patch.object(
                engine,
                "call_agent_skill",
                AsyncMock(return_value={"result": "processed"}),
            ):
                context = await engine.execute_workflow(
                    workflow, {"data": "test_data", "detailed": True}
                )

                # Verify all steps executed
                assert "preprocess" in context.step_outputs
                assert "analyze_a" in context.step_outputs
                assert "analyze_b" in context.step_outputs
                assert "detailed_report" in context.step_outputs
                assert "summary_report" not in context.step_outputs

    @pytest.mark.asyncio
    async def test_workflow_with_template_chaining(self):
        """Test workflow with complex template expression chaining."""
        yaml_content = """
metadata:
  id: template-chaining
  name: Template Chaining
  version: 1.0.0
steps:
  - id: step1
    skill: skill1
    inputs:
      value: "{{ workflow.input.initial }}"
    outputs: result1
  - id: step2
    skill: skill2
    inputs:
      value: "{{ steps.step1.outputs.result1 }}"
    outputs: result2
  - id: step3
    skill: skill3
    inputs:
      value: "{{ steps.step2.outputs.result2 }}"
    outputs: result3
"""
        workflow = load_workflow_from_yaml(yaml_content)
        engine = WorkflowEngine()

        with patch(
            "src.workflow_engine.discover_agent",
            return_value="http://localhost:8001",
        ):
            with patch.object(
                engine,
                "call_agent_skill",
                AsyncMock(
                    side_effect=[
                        {"processed": "value1"},
                        {"processed": "value2"},
                        {"processed": "value3"},
                    ]
                ),
            ) as mock_call:
                context = await engine.execute_workflow(workflow, {"initial": "start"})

                # Verify all steps completed
                assert "step1" in context.step_outputs
                assert "step2" in context.step_outputs
                assert "step3" in context.step_outputs

                # Verify data flowed through steps
                assert mock_call.call_count == 3

                # Check that step2 received step1's output
                call_args_step2 = mock_call.call_args_list[1][1]["params"]
                assert call_args_step2["value"] == {"processed": "value1"}

                # Check that step3 received step2's output
                call_args_step3 = mock_call.call_args_list[2][1]["params"]
                assert call_args_step3["value"] == {"processed": "value2"}
