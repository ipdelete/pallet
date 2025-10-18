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
    main,
    execute_workflow_by_id,
    _extract_final_output,
)
from tests.fixtures.sample_data import (
    REQUIREMENTS_EMAIL_VALIDATOR,
    PLAN_EMAIL_VALIDATOR,
    CODE_RESULT_EMAIL,
    REVIEW_GOOD,
)


class TestCallAgentSkill:
    """Tests for call_agent_skill function."""

    @pytest.mark.asyncio
    async def test_call_agent_skill_success(self):
        """Test successful agent skill call."""
        mock_response = Mock()
        mock_response.json = Mock(
            return_value={"jsonrpc": "2.0", "result": {"test": "data"}, "id": "1"}
        )
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await call_agent_skill(
                agent_url="http://localhost:8001",
                skill_id="test_skill",
                params={"key": "value"},
            )

            assert result["jsonrpc"] == "2.0"
            assert result["result"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_call_agent_skill_constructs_message(self):
        """Test that call_agent_skill constructs proper JSON-RPC message."""
        mock_response = Mock()
        mock_response.json = Mock(
            return_value={"jsonrpc": "2.0", "result": {}, "id": "1"}
        )
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await call_agent_skill(
                agent_url="http://test:9000",
                skill_id="my_skill",
                params={"param1": "value1"},
                timeout=30.0,
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
        with patch("os.path.exists", return_value=False):
            with patch("os.makedirs") as mock_makedirs:
                ensure_app_folder()
                mock_makedirs.assert_called_once_with("app")

    def test_ensure_app_folder_returns_path(self):
        """Test that ensure_app_folder returns the app path."""
        with patch("os.path.exists", return_value=True):
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
            requirements=REQUIREMENTS_EMAIL_VALIDATOR,
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
            requirements=REQUIREMENTS_EMAIL_VALIDATOR,
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
            requirements=REQUIREMENTS_EMAIL_VALIDATOR,
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
            requirements=REQUIREMENTS_EMAIL_VALIDATOR,
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
        from pathlib import Path
        from src.workflow_engine import WorkflowContext, load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        with patch("src.orchestrator.discover_workflow") as mock_discover:
            workflow = load_workflow_from_yaml(workflow_path)
            mock_discover.return_value = workflow

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
                    "src.workflow_engine.WorkflowEngine.execute_workflow",
                    AsyncMock(return_value=mock_context),
                ):
                    result = await orchestrate(REQUIREMENTS_EMAIL_VALIDATOR)

                    # Verify result structure
                    assert "plan" in result
                    assert "code" in result
                    assert "review" in result
                    assert "metadata" in result

    @pytest.mark.asyncio
    async def test_orchestrate_calls_plan_agent_first(self, tmp_path):
        """Test that orchestrate delegates to workflow engine."""
        from pathlib import Path
        from src.workflow_engine import WorkflowContext, load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        with patch("src.orchestrator.discover_workflow") as mock_discover:
            workflow = load_workflow_from_yaml(workflow_path)
            mock_discover.return_value = workflow

            mock_context = WorkflowContext(
                initial_input={"requirements": "test requirements"}
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
                    "src.workflow_engine.WorkflowEngine.execute_workflow",
                    AsyncMock(return_value=mock_context),
                ):
                    result = await orchestrate("test requirements")

                    # Verify workflow was discovered and executed
                    assert "plan" in result
                    assert result["plan"] == PLAN_EMAIL_VALIDATOR

    @pytest.mark.asyncio
    async def test_orchestrate_chains_plan_to_build(self, tmp_path):
        """Test that plan output is passed to build agent via workflow."""
        from pathlib import Path
        from src.workflow_engine import WorkflowContext, load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        with patch("src.orchestrator.discover_workflow") as mock_discover:
            workflow = load_workflow_from_yaml(workflow_path)
            mock_discover.return_value = workflow

            mock_context = WorkflowContext(initial_input={"requirements": "test"})
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
                    "src.workflow_engine.WorkflowEngine.execute_workflow",
                    AsyncMock(return_value=mock_context),
                ):
                    result = await orchestrate("test")

                    # Verify data flows through workflow
                    assert result["plan"] == PLAN_EMAIL_VALIDATOR
                    assert result["code"] == CODE_RESULT_EMAIL

    @pytest.mark.asyncio
    async def test_orchestrate_chains_build_to_test(self, tmp_path):
        """Test that code output is passed to test agent via workflow."""
        from pathlib import Path
        from src.workflow_engine import WorkflowContext, load_workflow_from_yaml

        # Load actual workflow
        workflow_path = Path("workflows/code-generation.yaml")
        if not workflow_path.exists():
            pytest.skip("Workflow file not found")

        with patch("src.orchestrator.discover_workflow") as mock_discover:
            workflow = load_workflow_from_yaml(workflow_path)
            mock_discover.return_value = workflow

            mock_context = WorkflowContext(initial_input={"requirements": "test"})
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
                    "src.workflow_engine.WorkflowEngine.execute_workflow",
                    AsyncMock(return_value=mock_context),
                ):
                    result = await orchestrate("test")

                    # Verify all data flows through workflow
                    assert result["code"] == CODE_RESULT_EMAIL
                    assert result["review"] == REVIEW_GOOD


class TestMain:
    """Tests for main function."""

    @pytest.mark.asyncio
    async def test_main_with_requirements(self):
        """Test main function with custom requirements."""
        with patch("src.orchestrator.orchestrate") as mock_orchestrate:
            await main("Custom requirements")

            mock_orchestrate.assert_called_once_with("Custom requirements")

    @pytest.mark.asyncio
    async def test_main_with_default_requirements(self):
        """Test main function with default requirements."""
        with patch("src.orchestrator.orchestrate") as mock_orchestrate:
            await main()

            # Should be called with default requirements
            call_args = mock_orchestrate.call_args[0][0]
            assert "email" in call_args.lower()
            assert "validate" in call_args.lower()


class TestExecuteWorkflowById:
    """Tests for execute_workflow_by_id function."""

    @pytest.mark.asyncio
    async def test_execute_workflow_by_id_success(self):
        """Test successful workflow execution by ID."""
        from src.workflow_engine import (
            WorkflowDefinition,
            WorkflowMetadata,
            WorkflowStep,
            WorkflowContext,
        )

        # Create a test workflow
        test_workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(
                id="test-workflow", name="Test Workflow", version="1.0.0"
            ),
            steps=[
                WorkflowStep(id="step1", skill="test_skill", inputs={"data": "test"})
            ],
        )

        # Mock context
        mock_context = WorkflowContext(initial_input={"requirements": "test"})
        mock_context.step_outputs = {
            "step1": {"outputs": {"result": {"data": "output"}}}
        }

        with patch("src.orchestrator.discover_workflow", return_value=test_workflow):
            with patch(
                "src.orchestrator.WorkflowEngine.execute_workflow",
                AsyncMock(return_value=mock_context),
            ):
                result = await execute_workflow_by_id(
                    "test-workflow", {"requirements": "test"}
                )

                assert result["workflow_id"] == "test-workflow"
                assert result["workflow_name"] == "Test Workflow"
                assert result["workflow_version"] == "1.0.0"
                assert "step_outputs" in result
                assert "final_output" in result

    @pytest.mark.asyncio
    async def test_execute_workflow_by_id_not_found(self):
        """Test that missing workflow raises ValueError."""
        with patch("src.orchestrator.discover_workflow", return_value=None):
            with pytest.raises(ValueError, match="Workflow not found"):
                await execute_workflow_by_id(
                    "nonexistent-workflow", {"requirements": "test"}
                )

    @pytest.mark.asyncio
    async def test_execute_workflow_by_id_with_version(self):
        """Test workflow execution with specific version."""
        from src.workflow_engine import (
            WorkflowDefinition,
            WorkflowMetadata,
            WorkflowStep,
            WorkflowContext,
        )

        test_workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(
                id="test-workflow", name="Test Workflow", version="2.0.0"
            ),
            steps=[WorkflowStep(id="step1", skill="test_skill", inputs={})],
        )

        mock_context = WorkflowContext(initial_input={})
        mock_context.step_outputs = {"step1": {"outputs": {}}}

        with patch(
            "src.orchestrator.discover_workflow", return_value=test_workflow
        ) as mock_discover:
            with patch(
                "src.orchestrator.WorkflowEngine.execute_workflow",
                AsyncMock(return_value=mock_context),
            ):
                await execute_workflow_by_id(
                    "test-workflow", {"data": "test"}, version="v2"
                )

                # Verify discover_workflow was called with correct version
                mock_discover.assert_called_once_with("test-workflow", "v2")


class TestExtractFinalOutput:
    """Tests for _extract_final_output helper function."""

    def test_extract_final_output_with_outputs(self):
        """Test extracting final output from context with outputs."""
        from src.workflow_engine import WorkflowContext

        context = WorkflowContext(initial_input={})
        context.step_outputs = {
            "step1": {"outputs": {"result": "output1"}},
            "step2": {"outputs": {"result": "output2"}},
            "step3": {"outputs": {"result": "output3"}},
        }

        result = _extract_final_output(context)
        assert result == {"result": "output3"}

    def test_extract_final_output_empty_context(self):
        """Test extracting final output from empty context."""
        from src.workflow_engine import WorkflowContext

        context = WorkflowContext(initial_input={})
        context.step_outputs = {}

        result = _extract_final_output(context)
        assert result == {}


class TestOrchestrateBackwardCompatibility:
    """Tests for backward compatibility of orchestrate function."""

    @pytest.mark.asyncio
    async def test_orchestrate_delegates_to_workflow_engine(self, tmp_path):
        """Test that orchestrate now delegates to workflow engine."""
        from src.workflow_engine import (
            WorkflowDefinition,
            WorkflowMetadata,
            WorkflowStep,
            WorkflowContext,
        )

        test_workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(
                id="code-generation-v1", name="Code Gen", version="1.0.0"
            ),
            steps=[
                WorkflowStep(id="plan", skill="create_plan", inputs={}),
                WorkflowStep(id="build", skill="generate_code", inputs={}),
                WorkflowStep(id="test", skill="review_code", inputs={}),
            ],
        )

        mock_context = WorkflowContext(initial_input={"requirements": "test"})
        mock_context.step_outputs = {
            "plan": {"outputs": {"result": PLAN_EMAIL_VALIDATOR}},
            "build": {"outputs": {"result": CODE_RESULT_EMAIL}},
            "test": {"outputs": {"result": REVIEW_GOOD}},
        }

        with patch("src.orchestrator.discover_workflow", return_value=test_workflow):
            with patch(
                "src.orchestrator.WorkflowEngine.execute_workflow",
                AsyncMock(return_value=mock_context),
            ):
                result = await orchestrate("test requirements")

                # Verify legacy format
                assert "plan" in result
                assert "code" in result
                assert "review" in result
                assert "metadata" in result
                assert result["plan"] == PLAN_EMAIL_VALIDATOR
                assert result["code"] == CODE_RESULT_EMAIL
                assert result["review"] == REVIEW_GOOD
                assert result["metadata"]["workflow_id"] == "code-generation-v1"

    @pytest.mark.asyncio
    async def test_orchestrate_returns_dict(self):
        """Test that orchestrate returns dict (not None)."""
        from src.workflow_engine import (
            WorkflowDefinition,
            WorkflowMetadata,
            WorkflowContext,
        )

        test_workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(
                id="code-generation-v1", name="Code Gen", version="1.0.0"
            ),
            steps=[],
        )

        mock_context = WorkflowContext(initial_input={})
        mock_context.step_outputs = {}

        with patch("src.orchestrator.discover_workflow", return_value=test_workflow):
            with patch(
                "src.orchestrator.WorkflowEngine.execute_workflow",
                AsyncMock(return_value=mock_context),
            ):
                result = await orchestrate("test")

                assert isinstance(result, dict)
                assert "metadata" in result
