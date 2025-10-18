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
        # Mock discovery to return agent URLs
        with patch("src.orchestrator.discover_agent") as mock_discover:
            mock_discover.side_effect = [
                "http://localhost:8001",  # Plan agent
                "http://localhost:8002",  # Build agent
                "http://localhost:8003",  # Test agent
            ]

            # Mock agent skill calls
            with patch("src.orchestrator.call_agent_skill") as mock_call:
                mock_call.side_effect = [
                    {"result": PLAN_EMAIL_VALIDATOR},
                    {"result": CODE_RESULT_EMAIL},
                    {"result": REVIEW_GOOD},
                ]

                # Mock file operations to use tmp_path
                with patch(
                    "src.orchestrator.ensure_app_folder", return_value=str(tmp_path)
                ):
                    await orchestrate(REQUIREMENTS_EMAIL_VALIDATOR)

                    # Verify all steps were executed
                    assert mock_discover.call_count == 3
                    assert mock_call.call_count == 3

                    # Verify files were created
                    assert os.path.exists(os.path.join(str(tmp_path), "main.py"))
                    assert os.path.exists(os.path.join(str(tmp_path), "plan.json"))
                    assert os.path.exists(os.path.join(str(tmp_path), "review.json"))
                    assert os.path.exists(os.path.join(str(tmp_path), "metadata.json"))

    @pytest.mark.asyncio
    async def test_orchestration_data_flow(self, tmp_path):
        """Test that data flows correctly through the pipeline."""
        with patch(
            "src.orchestrator.discover_agent", return_value="http://localhost:8000"
        ):
            with patch("src.orchestrator.call_agent_skill") as mock_call:
                # Capture calls to verify data flow
                calls = []

                def track_call(*args, **kwargs):
                    calls.append((args, kwargs))
                    # Return appropriate response based on skill
                    # args: (agent_url, skill_id, params, timeout=60.0)
                    skill_id = args[1]
                    if skill_id == "create_plan":
                        return {"result": PLAN_EMAIL_VALIDATOR}
                    elif skill_id == "generate_code":
                        return {"result": CODE_RESULT_EMAIL}
                    elif skill_id == "review_code":
                        return {"result": REVIEW_GOOD}

                mock_call.side_effect = track_call

                with patch(
                    "src.orchestrator.ensure_app_folder", return_value=str(tmp_path)
                ):
                    await orchestrate(REQUIREMENTS_EMAIL_VALIDATOR)

                    # Verify data flow
                    # Call 1: requirements → plan
                    assert (
                        calls[0][0][2]["requirements"] == REQUIREMENTS_EMAIL_VALIDATOR
                    )

                    # Call 2: plan → code
                    assert calls[1][0][2]["plan"] == PLAN_EMAIL_VALIDATOR

                    # Call 3: code → review
                    assert calls[2][0][2]["code"] == CODE_RESULT_EMAIL["code"]
                    assert calls[2][0][2]["language"] == CODE_RESULT_EMAIL["language"]

    @pytest.mark.asyncio
    async def test_output_files_content(self, tmp_path):
        """Test that output files contain correct data."""
        with patch(
            "src.orchestrator.discover_agent", return_value="http://localhost:8000"
        ):
            with patch("src.orchestrator.call_agent_skill") as mock_call:
                mock_call.side_effect = [
                    {"result": PLAN_EMAIL_VALIDATOR},
                    {"result": CODE_RESULT_EMAIL},
                    {"result": REVIEW_GOOD},
                ]

                with patch(
                    "src.orchestrator.ensure_app_folder", return_value=str(tmp_path)
                ):
                    await orchestrate(REQUIREMENTS_EMAIL_VALIDATOR)

                    # Verify main.py contains the code
                    with open(os.path.join(str(tmp_path), "main.py"), "r") as f:
                        code = f.read()
                        assert code == CODE_RESULT_EMAIL["code"]

                    # Verify plan.json
                    with open(os.path.join(str(tmp_path), "plan.json"), "r") as f:
                        plan = json.load(f)
                        assert plan["title"] == PLAN_EMAIL_VALIDATOR["title"]

                    # Verify review.json
                    with open(os.path.join(str(tmp_path), "review.json"), "r") as f:
                        review = json.load(f)
                        assert review["quality_score"] == REVIEW_GOOD["quality_score"]

                    # Verify metadata.json
                    with open(os.path.join(str(tmp_path), "metadata.json"), "r") as f:
                        metadata = json.load(f)
                        assert metadata["requirements"] == REQUIREMENTS_EMAIL_VALIDATOR
                        assert metadata["approved"] is True


@pytest.mark.e2e
@pytest.mark.slow
class TestDiscoveryIntegration:
    """Tests for discovery integration in orchestration."""

    @pytest.mark.asyncio
    async def test_orchestration_uses_discovery(self, tmp_path):
        """Test that orchestration uses discovery to find agents."""
        with patch("src.orchestrator.discover_agent") as mock_discover:
            mock_discover.side_effect = [
                "http://localhost:8001",
                "http://localhost:8002",
                "http://localhost:8003",
            ]

            with patch("src.orchestrator.call_agent_skill") as mock_call:
                mock_call.side_effect = [
                    {"result": PLAN_EMAIL_VALIDATOR},
                    {"result": CODE_RESULT_EMAIL},
                    {"result": REVIEW_GOOD},
                ]

                with patch(
                    "src.orchestrator.ensure_app_folder", return_value=str(tmp_path)
                ):
                    await orchestrate("test requirements")

                    # Verify discovery was called for each skill
                    assert mock_discover.call_count == 3

                    # Verify correct skills were requested
                    call_args = [call[0][0] for call in mock_discover.call_args_list]
                    assert "create_plan" in call_args
                    assert "generate_code" in call_args
                    assert "review_code" in call_args


@pytest.mark.e2e
@pytest.mark.slow
class TestErrorScenarios:
    """Tests for error scenarios in end-to-end flow."""

    @pytest.mark.asyncio
    async def test_orchestration_with_agent_failure(self, tmp_path):
        """Test orchestration behavior when an agent fails."""
        with patch(
            "src.orchestrator.discover_agent", return_value="http://localhost:8000"
        ):
            with patch("src.orchestrator.call_agent_skill") as mock_call:
                # First call succeeds, second fails
                mock_call.side_effect = [
                    {"result": PLAN_EMAIL_VALIDATOR},
                    Exception("Agent connection failed"),
                ]

                with patch(
                    "src.orchestrator.ensure_app_folder", return_value=str(tmp_path)
                ):
                    # Should raise exception
                    with pytest.raises(Exception, match="Agent connection failed"):
                        await orchestrate("test requirements")

    @pytest.mark.asyncio
    async def test_orchestration_with_discovery_failure(self, tmp_path):
        """Test orchestration behavior when discovery fails."""
        import httpx

        with patch("src.orchestrator.discover_agent", return_value=None):
            with patch(
                "src.orchestrator.ensure_app_folder", return_value=str(tmp_path)
            ):
                # Should raise error when trying to use None URL
                with pytest.raises(
                    (AttributeError, TypeError, httpx.UnsupportedProtocol)
                ):
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
