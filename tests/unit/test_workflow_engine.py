"""
Unit tests for WorkflowEngine execution patterns.

Tests workflow engine capabilities:
- Agent discovery with caching
- Agent skill calling
- Step execution with template resolution
- Sequential execution
- Parallel execution
- Conditional branching (if/else)
- Switch routing
- Full workflow execution
"""

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
    with patch("src.workflow_engine.discover_agent") as mock:
        mock.return_value = "http://localhost:8001"
        yield mock


@pytest.fixture
def workflow_engine():
    """WorkflowEngine instance."""
    return WorkflowEngine()


class TestWorkflowEngineDiscovery:
    """Test agent discovery and caching."""

    @pytest.mark.asyncio
    async def test_discover_agent_with_caching(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test agent discovery caches results."""
        url1 = await workflow_engine.discover_agent_for_skill("test_skill")
        url2 = await workflow_engine.discover_agent_for_skill("test_skill")

        assert url1 == "http://localhost:8001"
        assert url2 == "http://localhost:8001"
        mock_agent_discovery.assert_called_once()  # Only called once due to caching

    @pytest.mark.asyncio
    async def test_discover_agent_not_found(self, workflow_engine):
        """Test discovery raises ValueError when skill not found."""
        with patch("src.workflow_engine.discover_agent", return_value=None):
            with pytest.raises(ValueError, match="No agent found for skill"):
                await workflow_engine.discover_agent_for_skill("nonexistent_skill")

    @pytest.mark.asyncio
    async def test_discover_multiple_skills(self, workflow_engine):
        """Test discovering multiple different skills."""
        with patch("src.workflow_engine.discover_agent") as mock:
            mock.side_effect = [
                "http://localhost:8001",
                "http://localhost:8002",
            ]

            url1 = await workflow_engine.discover_agent_for_skill("skill1")
            url2 = await workflow_engine.discover_agent_for_skill("skill2")

            assert url1 == "http://localhost:8001"
            assert url2 == "http://localhost:8002"
            assert mock.call_count == 2


class TestWorkflowEngineAgentCall:
    """Test agent skill calling."""

    @pytest.mark.asyncio
    async def test_call_agent_skill_success(self, workflow_engine):
        """Test successful agent skill call."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "result": {"output": "test"},
                "id": "1",
            }
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await workflow_engine.call_agent_skill(
                "http://localhost:8001", "test_skill", {"input": "test"}, timeout=30
            )

            assert result == {"output": "test"}

    @pytest.mark.asyncio
    async def test_call_agent_skill_with_error(self, workflow_engine):
        """Test agent skill call with error response."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid request"},
                "id": "1",
            }
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(RuntimeError, match="Agent error"):
                await workflow_engine.call_agent_skill(
                    "http://localhost:8001",
                    "test_skill",
                    {"input": "test"},
                    timeout=30,
                )

    @pytest.mark.asyncio
    async def test_call_agent_skill_http_error(self, workflow_engine):
        """Test agent skill call with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("HTTP 500 Error")

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(Exception, match="HTTP 500 Error"):
                await workflow_engine.call_agent_skill(
                    "http://localhost:8001",
                    "test_skill",
                    {"input": "test"},
                    timeout=30,
                )


class TestWorkflowEngineStepExecution:
    """Test single step execution."""

    @pytest.mark.asyncio
    async def test_execute_step_success(self, workflow_engine, mock_agent_discovery):
        """Test single step execution."""
        step = WorkflowStep(id="step1", skill="test_skill", inputs={"input": "test"})
        context = WorkflowContext({"initial": "data"})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(return_value={"result": "output"}),
        ):
            result = await workflow_engine.execute_step(step, context)

            assert result == {"result": "output"}

    @pytest.mark.asyncio
    async def test_execute_step_with_template_resolution(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test step execution resolves input templates."""
        step = WorkflowStep(
            id="step2",
            skill="test_skill",
            inputs={"data": "{{ workflow.input.value }}"},
        )
        context = WorkflowContext({"value": "resolved_data"})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(return_value={"result": "output"}),
        ) as mock_call:
            await workflow_engine.execute_step(step, context)

            # Verify resolved input was passed to agent
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[1]["params"] == {"data": "resolved_data"}

    @pytest.mark.asyncio
    async def test_execute_step_timeout(self, workflow_engine, mock_agent_discovery):
        """Test step execution timeout raises RuntimeError."""
        step = WorkflowStep(
            id="step1", skill="test_skill", inputs={"input": "test"}, timeout=5
        )
        context = WorkflowContext({})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                await workflow_engine.execute_step(step, context)

    @pytest.mark.asyncio
    async def test_execute_step_agent_failure(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test step execution handles agent failures."""
        step = WorkflowStep(id="step1", skill="test_skill")
        context = WorkflowContext({})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(side_effect=Exception("Agent failed")),
        ):
            with pytest.raises(RuntimeError, match="Step step1 failed"):
                await workflow_engine.execute_step(step, context)


class TestWorkflowEngineSequential:
    """Test sequential step execution."""

    @pytest.mark.asyncio
    async def test_execute_sequential_steps(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test sequential execution of multiple steps."""
        steps = [
            WorkflowStep(id="step1", skill="skill1", outputs="result1"),
            WorkflowStep(
                id="step2",
                skill="skill2",
                inputs={"data": "{{ steps.step1.outputs.result1 }}"},
                outputs="result2",
            ),
        ]
        context = WorkflowContext({})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(side_effect=[{"data": "step1_output"}, {"data": "step2_output"}]),
        ):
            result_context = await workflow_engine.execute_sequential_steps(
                steps, context
            )

            assert "step1" in result_context.step_outputs
            assert "step2" in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_execute_sequential_data_flow(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test data flows from step N to step N+1."""
        steps = [
            WorkflowStep(id="step1", skill="skill1", outputs="value"),
            WorkflowStep(
                id="step2",
                skill="skill2",
                inputs={"input": "{{ steps.step1.outputs.value }}"},
            ),
        ]
        context = WorkflowContext({})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(side_effect=[{"number": 42}, {"result": "computed"}]),
        ) as mock_call:
            await workflow_engine.execute_sequential_steps(steps, context)

            # Verify second call received data from first step
            assert mock_call.call_count == 2
            second_call_params = mock_call.call_args_list[1][1]["params"]
            assert second_call_params["input"] == {"number": 42}

    @pytest.mark.asyncio
    async def test_sequential_error_stops_execution(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test error in step 2 stops execution."""
        steps = [
            WorkflowStep(id="step1", skill="skill1"),
            WorkflowStep(id="step2", skill="skill2"),
            WorkflowStep(id="step3", skill="skill3"),
        ]
        context = WorkflowContext({})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(
                side_effect=[{"ok": True}, Exception("Step 2 failed"), {"ok": True}]
            ),
        ):
            with pytest.raises(RuntimeError, match="Step step2 failed"):
                await workflow_engine.execute_sequential_steps(steps, context)

            # Verify only step1 completed
            assert "step1" in context.step_outputs
            assert "step2" not in context.step_outputs
            assert "step3" not in context.step_outputs


class TestWorkflowEngineParallel:
    """Test parallel step execution."""

    @pytest.mark.asyncio
    async def test_execute_parallel_steps(self, workflow_engine, mock_agent_discovery):
        """Test parallel execution."""
        steps = [
            WorkflowStep(id="step1", skill="skill1"),
            WorkflowStep(id="step2", skill="skill2"),
            WorkflowStep(id="step3", skill="skill3"),
        ]
        context = WorkflowContext({})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(return_value={"result": "output"}),
        ):
            result_context = await workflow_engine.execute_parallel_steps(
                steps, context
            )

            assert len(result_context.step_outputs) == 3
            assert "step1" in result_context.step_outputs
            assert "step2" in result_context.step_outputs
            assert "step3" in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_parallel_uses_asyncio_gather(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test parallel steps execute concurrently."""
        steps = [
            WorkflowStep(id="step1", skill="skill1"),
            WorkflowStep(id="step2", skill="skill2"),
        ]
        context = WorkflowContext({})

        with patch.object(
            workflow_engine, "execute_step", AsyncMock(return_value={"ok": True})
        ):
            with patch("asyncio.gather", new_callable=AsyncMock) as mock_gather:
                mock_gather.return_value = [{"ok": True}, {"ok": True}]
                await workflow_engine.execute_parallel_steps(steps, context)

                # Verify asyncio.gather was called
                mock_gather.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_one_failure_raises_error(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test one failure raises RuntimeError."""
        steps = [
            WorkflowStep(id="step1", skill="skill1"),
            WorkflowStep(id="step2", skill="skill2"),
            WorkflowStep(id="step3", skill="skill3"),
        ]
        context = WorkflowContext({})

        with patch.object(
            workflow_engine,
            "execute_step",
            AsyncMock(side_effect=[{"ok": True}, Exception("Failed"), {"ok": True}]),
        ):
            with pytest.raises(RuntimeError, match="Step step2 failed"):
                await workflow_engine.execute_parallel_steps(steps, context)


class TestWorkflowEngineConditional:
    """Test conditional step execution."""

    @pytest.mark.asyncio
    async def test_execute_conditional_true_branch(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test conditional execution (true branch)."""
        step = WorkflowStep(
            id="conditional",
            skill="conditional_skill",
            step_type=StepType.CONDITIONAL,
            condition="{{ workflow.input.flag }}",
            branches={
                "if_true": [{"id": "true_step", "skill": "true_skill"}],
                "if_false": [{"id": "false_step", "skill": "false_skill"}],
            },
        )
        context = WorkflowContext({"flag": True})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(return_value={"result": "true_output"}),
        ):
            result_context = await workflow_engine.execute_conditional_step(
                step, context
            )

            assert "true_step" in result_context.step_outputs
            assert "false_step" not in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_execute_conditional_false_branch(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test conditional execution (false branch)."""
        step = WorkflowStep(
            id="conditional",
            skill="conditional_skill",
            step_type=StepType.CONDITIONAL,
            condition="{{ workflow.input.flag }}",
            branches={
                "if_true": [{"id": "true_step", "skill": "true_skill"}],
                "if_false": [{"id": "false_step", "skill": "false_skill"}],
            },
        )
        context = WorkflowContext({"flag": False})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(return_value={"result": "false_output"}),
        ):
            result_context = await workflow_engine.execute_conditional_step(
                step, context
            )

            assert "false_step" in result_context.step_outputs
            assert "true_step" not in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_conditional_missing_condition_raises_error(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test missing condition raises ValueError."""
        step = WorkflowStep(
            id="conditional",
            skill="conditional_skill",
            step_type=StepType.CONDITIONAL,
            branches={
                "if_true": [{"id": "step1", "skill": "skill1"}],
            },
        )
        context = WorkflowContext({})

        with pytest.raises(ValueError, match="missing condition"):
            await workflow_engine.execute_conditional_step(step, context)

    @pytest.mark.asyncio
    async def test_conditional_missing_branches_raises_error(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test missing branches raises ValueError."""
        step = WorkflowStep(
            id="conditional",
            skill="conditional_skill",
            step_type=StepType.CONDITIONAL,
            condition="{{ workflow.input.flag }}",
        )
        context = WorkflowContext({"flag": True})

        with pytest.raises(ValueError, match="missing branches"):
            await workflow_engine.execute_conditional_step(step, context)

    @pytest.mark.asyncio
    async def test_conditional_branch_steps_execute_correctly(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test branch steps are executed correctly."""
        step = WorkflowStep(
            id="conditional",
            skill="conditional_skill",
            step_type=StepType.CONDITIONAL,
            condition="{{ workflow.input.execute }}",
            branches={
                "if_true": [
                    {"id": "step1", "skill": "skill1"},
                    {"id": "step2", "skill": "skill2"},
                ],
                "if_false": [],
            },
        )
        context = WorkflowContext({"execute": True})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(side_effect=[{"result": "1"}, {"result": "2"}]),
        ) as mock_call:
            await workflow_engine.execute_conditional_step(step, context)

            assert mock_call.call_count == 2
            assert "step1" in context.step_outputs
            assert "step2" in context.step_outputs


class TestWorkflowEngineSwitch:
    """Test switch step execution."""

    @pytest.mark.asyncio
    async def test_execute_switch_matches_case(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test switch matches correct case."""
        step = WorkflowStep(
            id="switch",
            skill="switch_skill",
            step_type=StepType.SWITCH,
            condition="{{ workflow.input.type }}",
            branches={
                "type_a": [{"id": "step_a", "skill": "skill_a"}],
                "type_b": [{"id": "step_b", "skill": "skill_b"}],
                "default": [{"id": "step_default", "skill": "skill_default"}],
            },
        )
        context = WorkflowContext({"type": "type_a"})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(return_value={"result": "output"}),
        ):
            result_context = await workflow_engine.execute_switch_step(step, context)

            assert "step_a" in result_context.step_outputs
            assert "step_b" not in result_context.step_outputs
            assert "step_default" not in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_execute_switch_default_case(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test switch falls back to default case."""
        step = WorkflowStep(
            id="switch",
            skill="switch_skill",
            step_type=StepType.SWITCH,
            condition="{{ workflow.input.type }}",
            branches={
                "type_a": [{"id": "step_a", "skill": "skill_a"}],
                "type_b": [{"id": "step_b", "skill": "skill_b"}],
                "default": [{"id": "step_default", "skill": "skill_default"}],
            },
        )
        context = WorkflowContext({"type": "unknown"})

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(return_value={"result": "output"}),
        ):
            result_context = await workflow_engine.execute_switch_step(step, context)

            assert "step_default" in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_switch_no_match_no_default_skips(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test switch with no match and no default skips execution."""
        step = WorkflowStep(
            id="switch",
            skill="switch_skill",
            step_type=StepType.SWITCH,
            condition="{{ workflow.input.type }}",
            branches={
                "type_a": [{"id": "step_a", "skill": "skill_a"}],
            },
        )
        context = WorkflowContext({"type": "unknown"})

        result_context = await workflow_engine.execute_switch_step(step, context)

        # No steps should have been executed
        assert len(result_context.step_outputs) == 0

    @pytest.mark.asyncio
    async def test_switch_missing_condition_raises_error(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test missing condition raises ValueError."""
        step = WorkflowStep(
            id="switch",
            skill="switch_skill",
            step_type=StepType.SWITCH,
            branches={
                "case1": [{"id": "step1", "skill": "skill1"}],
            },
        )
        context = WorkflowContext({})

        with pytest.raises(ValueError, match="missing condition expression"):
            await workflow_engine.execute_switch_step(step, context)

    @pytest.mark.asyncio
    async def test_switch_missing_branches_raises_error(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test missing branches raises ValueError."""
        step = WorkflowStep(
            id="switch",
            skill="switch_skill",
            step_type=StepType.SWITCH,
            condition="{{ workflow.input.value }}",
        )
        context = WorkflowContext({"value": "test"})

        with pytest.raises(ValueError, match="missing branches"):
            await workflow_engine.execute_switch_step(step, context)


class TestWorkflowEngineFullWorkflow:
    """Test full workflow execution."""

    @pytest.mark.asyncio
    async def test_execute_workflow_all_sequential(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test execute_workflow() with all sequential steps."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test", name="Test", version="1.0.0"),
            steps=[
                WorkflowStep(id="step1", skill="skill1", outputs="result1"),
                WorkflowStep(
                    id="step2",
                    skill="skill2",
                    inputs={"data": "{{ steps.step1.outputs.result1 }}"},
                ),
            ],
        )

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(side_effect=[{"data": "step1_output"}, {"data": "step2_output"}]),
        ):
            result_context = await workflow_engine.execute_workflow(
                workflow, {"initial": "input"}
            )

            assert "step1" in result_context.step_outputs
            assert "step2" in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_execute_workflow_mixed_types(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test workflow with mixed step types."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test", name="Test", version="1.0.0"),
            steps=[
                WorkflowStep(id="step1", skill="skill1"),
                WorkflowStep(
                    id="parallel",
                    skill="parallel_skill",
                    step_type=StepType.PARALLEL,
                    branches={
                        "steps": [
                            {"id": "p1", "skill": "skill2"},
                            {"id": "p2", "skill": "skill3"},
                        ]
                    },
                ),
            ],
        )

        with patch.object(
            workflow_engine,
            "call_agent_skill",
            AsyncMock(return_value={"result": "output"}),
        ):
            result_context = await workflow_engine.execute_workflow(workflow, {})

            assert "step1" in result_context.step_outputs
            assert "p1" in result_context.step_outputs
            assert "p2" in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_execute_workflow_unknown_step_type_raises_error(
        self, workflow_engine
    ):
        """Test unknown step type raises ValueError."""
        # Create a workflow with an invalid step type
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test", name="Test", version="1.0.0"),
            steps=[
                WorkflowStep(id="step1", skill="skill1"),
            ],
        )

        # Manually set an invalid step type after creation
        workflow.steps[0].step_type = "invalid_type"  # type: ignore

        with pytest.raises(ValueError, match="Unknown step type"):
            await workflow_engine.execute_workflow(workflow, {})

    @pytest.mark.asyncio
    async def test_workflow_context_initialization(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test workflow initialization and completion."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(
                id="test-123", name="Test Workflow", version="1.0.0"
            ),
            steps=[
                WorkflowStep(id="step1", skill="skill1"),
            ],
        )

        with patch.object(
            workflow_engine, "call_agent_skill", AsyncMock(return_value={"ok": True})
        ):
            result_context = await workflow_engine.execute_workflow(
                workflow, {"initial": "data"}
            )

            # Verify context has initial input
            assert result_context.workflow_input == {"initial": "data"}

            # Verify step outputs stored
            assert "step1" in result_context.step_outputs

    @pytest.mark.asyncio
    async def test_parallel_step_missing_steps_raises_error(
        self, workflow_engine, mock_agent_discovery
    ):
        """Test parallel step without 'steps' in branches raises error."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test", name="Test", version="1.0.0"),
            steps=[
                WorkflowStep(
                    id="parallel",
                    skill="parallel_skill",
                    step_type=StepType.PARALLEL,
                    branches={},  # Missing 'steps' key
                ),
            ],
        )

        with pytest.raises(ValueError, match="missing 'steps' in branches"):
            await workflow_engine.execute_workflow(workflow, {})
