"""End-to-end integration tests for the full Pallet system.

These tests verify the complete workflow from bootstrap to orchestration.
They require Docker, ORAS, and other dependencies to be installed.

Run with: pytest tests/integration/test_end_to_end.py -v
Skip with: pytest -m "not e2e"
"""

import pytest
import json
import os
from unittest.mock import patch, AsyncMock

from src.orchestrator import orchestrate, call_agent_skill, ensure_app_folder
from tests.fixtures.sample_data import (
    REQUIREMENTS_EMAIL_VALIDATOR,
    PLAN_EMAIL_VALIDATOR,
    CODE_RESULT_EMAIL,
    REVIEW_GOOD,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestFullOrchestration:
    """End-to-end tests for full orchestration pipeline.

    These tests mock the agents but test the real orchestration flow.
    """

    @pytest.mark.asyncio
    async def test_full_orchestration_workflow(self, tmp_path):
        """Test complete orchestration from requirements to review."""
        from pathlib import Path
        from src.workflow_engine import WorkflowContext, load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        # Mock workflow discovery and execution
        with patch("src.orchestrator.discover_workflow") as mock_discover:
            yaml_content = workflow_path.read_text()
            workflow = load_workflow_from_yaml(yaml_content)
            mock_discover.return_value = workflow

            # Mock context
            mock_context = WorkflowContext(
                initial_input={"requirements": REQUIREMENTS_EMAIL_VALIDATOR}
            )
            mock_context.step_outputs = {
                "plan": {"outputs": {"result": PLAN_EMAIL_VALIDATOR}},
                "build": {"outputs": {"result": CODE_RESULT_EMAIL}},
                "test": {"outputs": {"result": REVIEW_GOOD}},
            }

            with patch(
                "src.workflow_engine.discover_agent",
                return_value="http://localhost:8001",
            ):
                with patch(
                    "src.workflow_engine.WorkflowEngine.call_agent_skill",
                    AsyncMock(
                        side_effect=[
                            PLAN_EMAIL_VALIDATOR,
                            CODE_RESULT_EMAIL,
                            REVIEW_GOOD,
                        ]
                    ),
                ):
                    result = await orchestrate(REQUIREMENTS_EMAIL_VALIDATOR)

                    # Verify result structure
                    assert "plan" in result
                    assert "code" in result
                    assert "review" in result
                    assert "metadata" in result

    @pytest.mark.asyncio
    async def test_orchestration_data_flow(self, tmp_path):
        """Test that data flows correctly through the pipeline."""
        from pathlib import Path
        from src.workflow_engine import load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        # Mock workflow discovery and execution
        with patch("src.orchestrator.discover_workflow") as mock_discover:
            yaml_content = workflow_path.read_text()
            workflow = load_workflow_from_yaml(yaml_content)
            mock_discover.return_value = workflow

            with patch(
                "src.workflow_engine.discover_agent",
                return_value="http://localhost:8001",
            ):
                with patch(
                    "src.workflow_engine.WorkflowEngine.call_agent_skill",
                    AsyncMock(
                        side_effect=[
                            PLAN_EMAIL_VALIDATOR,
                            CODE_RESULT_EMAIL,
                            REVIEW_GOOD,
                        ]
                    ),
                ):
                    result = await orchestrate(REQUIREMENTS_EMAIL_VALIDATOR)

                    # Verify data flows through result
                    assert result["plan"] == PLAN_EMAIL_VALIDATOR
                    assert result["code"] == CODE_RESULT_EMAIL
                    assert result["review"] == REVIEW_GOOD

    @pytest.mark.asyncio
    async def test_output_files_content(self, tmp_path):
        """Test that output files contain correct data."""
        from pathlib import Path
        from src.workflow_engine import load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        # Mock workflow discovery and execution
        with patch("src.orchestrator.discover_workflow") as mock_discover:
            yaml_content = workflow_path.read_text()
            workflow = load_workflow_from_yaml(yaml_content)
            mock_discover.return_value = workflow

            with patch(
                "src.workflow_engine.discover_agent",
                return_value="http://localhost:8001",
            ):
                with patch(
                    "src.workflow_engine.WorkflowEngine.call_agent_skill",
                    AsyncMock(
                        side_effect=[
                            PLAN_EMAIL_VALIDATOR,
                            CODE_RESULT_EMAIL,
                            REVIEW_GOOD,
                        ]
                    ),
                ):
                    result = await orchestrate(REQUIREMENTS_EMAIL_VALIDATOR)

                    # Verify result content
                    assert result["plan"]["title"] == PLAN_EMAIL_VALIDATOR["title"]
                    assert result["code"]["code"] == CODE_RESULT_EMAIL["code"]
                    assert (
                        result["review"]["quality_score"]
                        == REVIEW_GOOD["quality_score"]
                    )


@pytest.mark.e2e
@pytest.mark.slow
class TestDiscoveryIntegration:
    """Tests for discovery integration in orchestration."""

    @pytest.mark.asyncio
    async def test_orchestration_uses_discovery(self, tmp_path):
        """Test that orchestration uses discovery to find agents."""
        from pathlib import Path
        from src.workflow_engine import load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        with patch("src.orchestrator.discover_workflow") as mock_discover_workflow:
            yaml_content = workflow_path.read_text()
            workflow = load_workflow_from_yaml(yaml_content)
            mock_discover_workflow.return_value = workflow

            with patch("src.workflow_engine.discover_agent") as mock_discover_agent:
                mock_discover_agent.return_value = "http://localhost:8001"

                with patch(
                    "src.workflow_engine.WorkflowEngine.call_agent_skill",
                    AsyncMock(
                        side_effect=[
                            PLAN_EMAIL_VALIDATOR,
                            CODE_RESULT_EMAIL,
                            REVIEW_GOOD,
                        ]
                    ),
                ):
                    result = await orchestrate("test requirements")

                    # Verify workflow discovery was called
                    mock_discover_workflow.assert_called_once()
                    # Verify agent discovery was used
                    assert mock_discover_agent.call_count >= 1


@pytest.mark.e2e
@pytest.mark.slow
class TestErrorScenarios:
    """Tests for error scenarios in end-to-end flow."""

    @pytest.mark.asyncio
    async def test_orchestration_with_agent_failure(self, tmp_path):
        """Test orchestration behavior when an agent fails."""
        from pathlib import Path
        from src.workflow_engine import load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        with patch("src.orchestrator.discover_workflow") as mock_discover:
            yaml_content = workflow_path.read_text()
            workflow = load_workflow_from_yaml(yaml_content)
            mock_discover.return_value = workflow

            with patch(
                "src.workflow_engine.discover_agent",
                return_value="http://localhost:8001",
            ):
                with patch(
                    "src.workflow_engine.WorkflowEngine.call_agent_skill",
                    AsyncMock(
                        side_effect=[
                            PLAN_EMAIL_VALIDATOR,
                            Exception("Agent connection failed"),
                        ]
                    ),
                ):
                    # Should raise exception
                    with pytest.raises(Exception, match="Agent connection failed"):
                        await orchestrate("test requirements")

    @pytest.mark.asyncio
    async def test_orchestration_with_discovery_failure(self, tmp_path):
        """Test orchestration behavior when discovery fails."""
        # Mock workflow discovery failure
        with patch("src.orchestrator.discover_workflow", return_value=None):
            # Should raise ValueError
            with pytest.raises(ValueError, match="Workflow not found"):
                await orchestrate("test requirements")


@pytest.mark.e2e
@pytest.mark.slow
class TestRealAgentsCommunication:
    """Tests that require real agents to be running.

    These tests are skipped by default and only run when agents are available.
    Run bootstrap.sh before running these tests.
    """

    @pytest.mark.skip(reason="Requires agents to be running (bootstrap.sh)")
    @pytest.mark.asyncio
    async def test_call_real_plan_agent(self):
        """Test calling real plan agent (requires agent to be running)."""
        result = await call_agent_skill(
            agent_url="http://localhost:8001",
            skill_id="create_plan",
            params={"requirements": "Create a simple hello world function"},
        )

        assert "result" in result
        assert "title" in result["result"]

    @pytest.mark.skip(reason="Requires agents to be running (bootstrap.sh)")
    @pytest.mark.asyncio
    async def test_real_end_to_end(self, tmp_path):
        """Test real end-to-end orchestration (requires all services)."""
        with patch("src.orchestrator.ensure_app_folder", return_value=str(tmp_path)):
            await orchestrate("Create a function that adds two numbers")

            # Verify output files exist
            assert os.path.exists(os.path.join(str(tmp_path), "main.py"))
            assert os.path.exists(os.path.join(str(tmp_path), "plan.json"))
            assert os.path.exists(os.path.join(str(tmp_path), "review.json"))


@pytest.mark.e2e
class TestAppFolderManagement:
    """Tests for app folder creation and management."""

    def test_ensure_app_folder_creates_directory(self, tmp_path):
        """Test that ensure_app_folder creates directory if missing."""
        app_path = os.path.join(str(tmp_path), "app")

        with patch("src.orchestrator.ensure_app_folder", wraps=ensure_app_folder):
            with patch("os.path.exists", return_value=False):
                with patch("os.makedirs") as mock_makedirs:
                    ensure_app_folder()
                    mock_makedirs.assert_called_once()

    def test_ensure_app_folder_returns_path(self):
        """Test that ensure_app_folder returns the correct path."""
        result = ensure_app_folder()
        assert result == "app"
