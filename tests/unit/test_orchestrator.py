"""Tests for orchestrator module."""

import pytest
import json
import os
from unittest.mock import AsyncMock, patch, Mock
from src.orchestrator import (
    call_agent_skill,
    ensure_app_folder,
    save_results,
    orchestrate,
    main
)
from tests.fixtures.sample_data import (
    REQUIREMENTS_EMAIL_VALIDATOR,
    PLAN_EMAIL_VALIDATOR,
    CODE_RESULT_EMAIL,
    REVIEW_GOOD
)


class TestCallAgentSkill:
    """Tests for call_agent_skill function."""

    @pytest.mark.asyncio
    async def test_call_agent_skill_success(self):
        """Test successful agent skill call."""
        mock_response = Mock()
        mock_response.json = Mock(return_value={
            "jsonrpc": "2.0",
            "result": {"test": "data"},
            "id": "1"
        })
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await call_agent_skill(
                agent_url="http://localhost:8001",
                skill_id="test_skill",
                params={"key": "value"}
            )

            assert result["jsonrpc"] == "2.0"
            assert result["result"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_call_agent_skill_constructs_message(self):
        """Test that call_agent_skill constructs proper JSON-RPC message."""
        mock_response = Mock()
        mock_response.json = Mock(return_value={
            "jsonrpc": "2.0",
            "result": {},
            "id": "1"
        })
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('httpx.AsyncClient', return_value=mock_client):
            await call_agent_skill(
                agent_url="http://test:9000",
                skill_id="my_skill",
                params={"param1": "value1"},
                timeout=30.0
            )

            # Verify POST was called correctly
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://test:9000/execute"

            message = call_args[1]["json"]
            assert message["jsonrpc"] == "2.0"
            assert message["method"] == "my_skill"
            assert message["params"] == {"param1": "value1"}
            assert message["id"] == "1"


class TestEnsureAppFolder:
    """Tests for ensure_app_folder function."""

    def test_ensure_app_folder_creates_folder(self, tmp_path):
        """Test that ensure_app_folder creates the app directory."""
        with patch('os.path.exists', return_value=False):
            with patch('os.makedirs') as mock_makedirs:
                ensure_app_folder()
                mock_makedirs.assert_called_once_with("app")

    def test_ensure_app_folder_returns_path(self):
        """Test that ensure_app_folder returns the app path."""
        with patch('os.path.exists', return_value=True):
            result = ensure_app_folder()
            assert result == "app"


class TestSaveResults:
    """Tests for save_results function."""

    def test_save_results_creates_files(self, tmp_path):
        """Test that save_results creates all required files."""
        app_dir = str(tmp_path)

        save_results(
            app_dir=app_dir,
            plan=PLAN_EMAIL_VALIDATOR,
            code_result=CODE_RESULT_EMAIL,
            review=REVIEW_GOOD,
            requirements=REQUIREMENTS_EMAIL_VALIDATOR
        )

        # Check that files were created
        assert os.path.exists(os.path.join(app_dir, "main.py"))
        assert os.path.exists(os.path.join(app_dir, "plan.json"))
        assert os.path.exists(os.path.join(app_dir, "review.json"))
        assert os.path.exists(os.path.join(app_dir, "metadata.json"))

    def test_save_results_code_content(self, tmp_path):
        """Test that code is saved correctly."""
        app_dir = str(tmp_path)

        save_results(
            app_dir=app_dir,
            plan=PLAN_EMAIL_VALIDATOR,
            code_result=CODE_RESULT_EMAIL,
            review=REVIEW_GOOD,
            requirements=REQUIREMENTS_EMAIL_VALIDATOR
        )

        # Read and verify code file
        with open(os.path.join(app_dir, "main.py"), "r") as f:
            code = f.read()
            assert code == CODE_RESULT_EMAIL["code"]

    def test_save_results_plan_content(self, tmp_path):
        """Test that plan is saved correctly."""
        app_dir = str(tmp_path)

        save_results(
            app_dir=app_dir,
            plan=PLAN_EMAIL_VALIDATOR,
            code_result=CODE_RESULT_EMAIL,
            review=REVIEW_GOOD,
            requirements=REQUIREMENTS_EMAIL_VALIDATOR
        )

        # Read and verify plan file
        with open(os.path.join(app_dir, "plan.json"), "r") as f:
            plan = json.load(f)
            assert plan["title"] == PLAN_EMAIL_VALIDATOR["title"]

    def test_save_results_metadata(self, tmp_path):
        """Test that metadata is saved correctly."""
        app_dir = str(tmp_path)

        save_results(
            app_dir=app_dir,
            plan=PLAN_EMAIL_VALIDATOR,
            code_result=CODE_RESULT_EMAIL,
            review=REVIEW_GOOD,
            requirements=REQUIREMENTS_EMAIL_VALIDATOR
        )

        # Read and verify metadata
        with open(os.path.join(app_dir, "metadata.json"), "r") as f:
            metadata = json.load(f)
            assert metadata["requirements"] == REQUIREMENTS_EMAIL_VALIDATOR
            assert metadata["code_language"] == "python"
            assert metadata["quality_score"] == 9
            assert metadata["approved"] is True


class TestOrchestrate:
    """Tests for orchestrate function."""

    @pytest.mark.asyncio
    async def test_orchestrate_full_pipeline(self, tmp_path):
        """Test full orchestration pipeline."""
        # Mock discovery
        with patch('src.orchestrator.discover_agent') as mock_discover:
            mock_discover.side_effect = [
                "http://localhost:8001",  # Plan agent
                "http://localhost:8002",  # Build agent
                "http://localhost:8003"   # Test agent
            ]

            # Mock agent skill calls
            with patch('src.orchestrator.call_agent_skill') as mock_call:
                mock_call.side_effect = [
                    {"result": PLAN_EMAIL_VALIDATOR},  # Plan response
                    {"result": CODE_RESULT_EMAIL},  # Build response
                    {"result": REVIEW_GOOD}  # Test response
                ]

                # Mock file operations
                with patch('src.orchestrator.ensure_app_folder', return_value=str(tmp_path)):
                    with patch('src.orchestrator.save_results') as mock_save:
                        await orchestrate(REQUIREMENTS_EMAIL_VALIDATOR)

                        # Verify discovery was called for all agents
                        assert mock_discover.call_count == 3

                        # Verify all agents were called
                        assert mock_call.call_count == 3

                        # Verify results were saved
                        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_orchestrate_calls_plan_agent_first(self, tmp_path):
        """Test that orchestrate calls plan agent first."""
        with patch('src.orchestrator.discover_agent', return_value="http://localhost:8001"):
            with patch('src.orchestrator.call_agent_skill') as mock_call:
                mock_call.side_effect = [
                    {"result": PLAN_EMAIL_VALIDATOR},
                    {"result": CODE_RESULT_EMAIL},
                    {"result": REVIEW_GOOD}
                ]

                with patch('src.orchestrator.ensure_app_folder', return_value=str(tmp_path)):
                    with patch('src.orchestrator.save_results'):
                        await orchestrate("test requirements")

                        # First call should be to create_plan
                        first_call = mock_call.call_args_list[0]
                        # call_agent_skill(agent_url, skill_id, params, timeout=...)
                        assert first_call[0][1] == "create_plan"  # skill_id is 2nd positional arg
                        assert first_call[0][2]["requirements"] == "test requirements"  # params is 3rd positional arg

    @pytest.mark.asyncio
    async def test_orchestrate_chains_plan_to_build(self, tmp_path):
        """Test that plan output is passed to build agent."""
        with patch('src.orchestrator.discover_agent', return_value="http://localhost:8000"):
            with patch('src.orchestrator.call_agent_skill') as mock_call:
                mock_call.side_effect = [
                    {"result": PLAN_EMAIL_VALIDATOR},
                    {"result": CODE_RESULT_EMAIL},
                    {"result": REVIEW_GOOD}
                ]

                with patch('src.orchestrator.ensure_app_folder', return_value=str(tmp_path)):
                    with patch('src.orchestrator.save_results'):
                        await orchestrate("test")

                        # Second call should pass plan to generate_code
                        second_call = mock_call.call_args_list[1]
                        assert second_call[0][1] == "generate_code"
                        assert second_call[0][2]["plan"] == PLAN_EMAIL_VALIDATOR

    @pytest.mark.asyncio
    async def test_orchestrate_chains_build_to_test(self, tmp_path):
        """Test that code output is passed to test agent."""
        with patch('src.orchestrator.discover_agent', return_value="http://localhost:8000"):
            with patch('src.orchestrator.call_agent_skill') as mock_call:
                mock_call.side_effect = [
                    {"result": PLAN_EMAIL_VALIDATOR},
                    {"result": CODE_RESULT_EMAIL},
                    {"result": REVIEW_GOOD}
                ]

                with patch('src.orchestrator.ensure_app_folder', return_value=str(tmp_path)):
                    with patch('src.orchestrator.save_results'):
                        await orchestrate("test")

                        # Third call should pass code to review_code
                        third_call = mock_call.call_args_list[2]
                        assert third_call[0][1] == "review_code"
                        assert third_call[0][2]["code"] == CODE_RESULT_EMAIL["code"]
                        assert third_call[0][2]["language"] == "python"


class TestMain:
    """Tests for main function."""

    @pytest.mark.asyncio
    async def test_main_with_requirements(self):
        """Test main function with custom requirements."""
        with patch('src.orchestrator.orchestrate') as mock_orchestrate:
            await main("Custom requirements")

            mock_orchestrate.assert_called_once_with("Custom requirements")

    @pytest.mark.asyncio
    async def test_main_with_default_requirements(self):
        """Test main function with default requirements."""
        with patch('src.orchestrator.orchestrate') as mock_orchestrate:
            await main()

            # Should be called with default requirements
            call_args = mock_orchestrate.call_args[0][0]
            assert "email" in call_args.lower()
            assert "validate" in call_args.lower()
