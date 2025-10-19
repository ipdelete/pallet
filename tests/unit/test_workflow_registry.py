import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.workflow_registry import (
    push_workflow_to_registry,
    pull_workflow_from_registry,
    list_workflows,
    get_workflow_metadata,
)


class TestPushWorkflowToRegistry:
    @patch("subprocess.run")
    def test_push_success(self, mock_run):
        """Test successful workflow push."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch("pathlib.Path.exists", return_value=True):
            result = push_workflow_to_registry(Path("test.yaml"), "test-workflow", "v1")

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "oras" in args
        assert "push" in args
        assert "localhost:5000/workflows/test-workflow:v1" in args

    @patch("subprocess.run")
    def test_push_file_not_found(self, mock_run):
        """Test push with non-existent file."""
        with patch("pathlib.Path.exists", return_value=False):
            result = push_workflow_to_registry(
                Path("missing.yaml"), "test-workflow", "v1"
            )

        assert result is False
        mock_run.assert_not_called()

    @patch("subprocess.run")
    def test_push_oras_failure(self, mock_run):
        """Test push when ORAS command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "oras", stderr="error")

        with patch("pathlib.Path.exists", return_value=True):
            result = push_workflow_to_registry(Path("test.yaml"), "test-workflow", "v1")

        assert result is False

    @patch("subprocess.run")
    def test_push_oras_not_found(self, mock_run):
        """Test push when ORAS is not installed."""
        mock_run.side_effect = FileNotFoundError("oras not found")

        with patch("pathlib.Path.exists", return_value=True):
            result = push_workflow_to_registry(Path("test.yaml"), "test-workflow", "v1")

        assert result is False


class TestPullWorkflowFromRegistry:
    @patch("subprocess.run")
    @patch("tempfile.mkdtemp")
    def test_pull_success(self, mock_mkdtemp, mock_run):
        """Test successful workflow pull."""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch("pathlib.Path.glob", return_value=[Path("/tmp/test/workflow.yaml")]):
            result = pull_workflow_from_registry("test-workflow", "v1")

        assert result == Path("/tmp/test/workflow.yaml")
        mock_run.assert_called_once()

    @patch("subprocess.run")
    @patch("tempfile.mkdtemp")
    def test_pull_no_yaml_files(self, mock_mkdtemp, mock_run):
        """Test pull when no YAML files found in artifacts."""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch("pathlib.Path.glob", return_value=[]):
            result = pull_workflow_from_registry("test-workflow", "v1")

        assert result is None

    @patch("subprocess.run")
    def test_pull_oras_failure(self, mock_run):
        """Test pull when ORAS command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "oras", stderr="not found"
        )

        result = pull_workflow_from_registry("test-workflow", "v1")

        assert result is None

    @patch("subprocess.run")
    def test_pull_oras_not_found(self, mock_run):
        """Test pull when ORAS is not installed."""
        mock_run.side_effect = FileNotFoundError("oras not found")

        result = pull_workflow_from_registry("test-workflow", "v1")

        assert result is None

    @patch("subprocess.run")
    @patch("tempfile.mkdtemp")
    def test_pull_with_custom_output_dir(self, mock_mkdtemp, mock_run):
        """Test pull with custom output directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        output_dir = Path("/custom/output")

        with patch(
            "pathlib.Path.glob", return_value=[Path("/custom/output/workflow.yaml")]
        ):
            result = pull_workflow_from_registry("test-workflow", "v1", output_dir)

        assert result == Path("/custom/output/workflow.yaml")
        # Verify mkdtemp was not called since we provided output_dir
        mock_mkdtemp.assert_not_called()


class TestListWorkflows:
    @patch("httpx.get")
    def test_list_workflows_success(self, mock_get):
        """Test listing workflows from registry."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "repositories": [
                "agents/plan",
                "workflows/code-generation",
                "workflows/smart-router",
                "agents/build",
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        workflows = list_workflows()

        assert len(workflows) == 2
        assert "workflows/code-generation" in workflows
        assert "workflows/smart-router" in workflows

    @patch("httpx.get")
    def test_list_workflows_empty_registry(self, mock_get):
        """Test listing when no workflows exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "repositories": ["agents/plan", "agents/build"]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        workflows = list_workflows()

        assert workflows == []

    @patch("httpx.get")
    def test_list_workflows_registry_down(self, mock_get):
        """Test listing when registry is down."""
        import httpx

        mock_get.side_effect = httpx.RequestError("Connection failed")

        workflows = list_workflows()

        assert workflows == []

    @patch("httpx.get")
    def test_list_workflows_http_error(self, mock_get):
        """Test listing when registry returns HTTP error."""
        import httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error", request=MagicMock(), response=MagicMock()
        )
        mock_get.return_value = mock_response

        workflows = list_workflows()

        assert workflows == []


class TestGetWorkflowMetadata:
    @patch("src.workflow_registry.pull_workflow_from_registry")
    @patch("src.workflow_engine.load_workflow_from_yaml")
    def test_get_metadata_success(self, mock_load, mock_pull):
        """Test getting workflow metadata."""
        mock_pull.return_value = Path("/tmp/workflow.yaml")

        mock_workflow = MagicMock()
        mock_workflow.metadata.id = "test-workflow"
        mock_workflow.metadata.name = "Test Workflow"
        mock_workflow.metadata.version = "1.0.0"
        mock_workflow.metadata.description = "A test"
        mock_workflow.metadata.tags = ["test"]
        mock_workflow.steps = [MagicMock(), MagicMock()]
        mock_load.return_value = mock_workflow

        metadata = get_workflow_metadata("test-workflow", "v1")

        assert metadata["id"] == "test-workflow"
        assert metadata["name"] == "Test Workflow"
        assert metadata["version"] == "1.0.0"
        assert metadata["description"] == "A test"
        assert metadata["tags"] == ["test"]
        assert metadata["steps"] == 2

    @patch("src.workflow_registry.pull_workflow_from_registry")
    def test_get_metadata_pull_failed(self, mock_pull):
        """Test metadata when pull fails."""
        mock_pull.return_value = None

        metadata = get_workflow_metadata("test-workflow", "v1")

        assert metadata is None

    @patch("src.workflow_registry.pull_workflow_from_registry")
    @patch("src.workflow_engine.load_workflow_from_yaml")
    def test_get_metadata_parse_failed(self, mock_load, mock_pull):
        """Test metadata when workflow parsing fails."""
        mock_pull.return_value = Path("/tmp/workflow.yaml")
        mock_load.side_effect = Exception("Invalid YAML")

        metadata = get_workflow_metadata("test-workflow", "v1")

        assert metadata is None
