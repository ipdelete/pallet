"""Shared fixtures for tests."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from typing import Dict, Any

from src.agents.base import SkillDefinition


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_skill() -> SkillDefinition:
    """Sample skill definition for testing."""
    return SkillDefinition(
        id="test_skill",
        description="A test skill",
        input_schema={
            "type": "object",
            "properties": {"param": {"type": "string"}},
            "required": ["param"],
        },
        output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
    )


@pytest.fixture
def sample_requirements() -> str:
    """Sample requirements text for testing."""
    return "Create a Python function that validates email addresses."


@pytest.fixture
def sample_plan() -> Dict[str, Any]:
    """Sample plan output from Plan Agent."""
    return {
        "title": "Email Validator Implementation",
        "steps": [
            {
                "name": "Create regex pattern",
                "description": "Define regex for email validation",
                "time": "10 minutes",
            },
            {
                "name": "Implement validation function",
                "description": "Write the validation logic",
                "time": "15 minutes",
            },
        ],
        "dependencies": ["re"],
        "estimated_total_time": "25 minutes",
    }


@pytest.fixture
def sample_code() -> str:
    """Sample code output from Build Agent."""
    return '''import re

def validate_email(email: str) -> bool:
    """Validate an email address.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
'''


@pytest.fixture
def sample_code_result() -> Dict[str, Any]:
    """Sample code generation result from Build Agent."""
    return {
        "code": "import re\n\ndef validate_email(email: str) -> bool:\n    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$', email))",
        "explanation": "Email validation function using regex",
        "language": "python",
        "functions": ["validate_email"],
    }


@pytest.fixture
def sample_review() -> Dict[str, Any]:
    """Sample review output from Test Agent."""
    return {
        "quality_score": 8,
        "issues": [
            {
                "type": "style",
                "comment": "Consider adding more comprehensive regex pattern",
            }
        ],
        "suggestions": [
            "Add unit tests for edge cases",
            "Consider handling internationalized domain names",
        ],
        "approved": True,
        "summary": "Good implementation with room for improvement",
    }


@pytest.fixture
def sample_agent_card() -> Dict[str, Any]:
    """Sample agent card from registry."""
    return {
        "name": "test-agent",
        "url": "http://localhost:8001",
        "skills": [
            {
                "id": "test_skill",
                "description": "A test skill",
                "input_schema": {
                    "type": "object",
                    "properties": {"param": {"type": "string"}},
                    "required": ["param"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
            }
        ],
    }


@pytest.fixture
def mock_claude_response() -> str:
    """Mock response from Claude CLI."""
    return """```json
{
    "title": "Test Plan",
    "steps": [],
    "dependencies": [],
    "estimated_total_time": "10 minutes"
}
```"""


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for Claude CLI calls."""
    mock = AsyncMock()
    mock.returncode = 0
    mock.communicate = AsyncMock(return_value=(b'{"result": "test"}', b""))
    return mock


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for HTTP requests."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value={"jsonrpc": "2.0", "result": {"test": "data"}, "id": "1"}
    )
    mock_response.raise_for_status = Mock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
def mock_registry_response():
    """Mock response from OCI registry."""
    return {"repositories": ["agents/plan", "agents/build", "agents/test"]}


@pytest.fixture
def mock_oras_pull(tmp_path, sample_agent_card):
    """Mock ORAS pull operation."""
    import json

    def _mock_oras(agent_name: str):
        card_file = tmp_path / f"{agent_name}_agent_card.json"
        card_file.write_text(json.dumps(sample_agent_card))
        return 0  # Success return code

    return _mock_oras


@pytest.fixture
def sample_workflow_yaml():
    """Sample valid workflow YAML."""
    return """
metadata:
  id: test-workflow-v1
  name: Test Workflow
  version: 1.0.0
  description: A test workflow
steps:
  - id: step1
    skill: create_plan
    inputs:
      requirements: "{{ workflow.input.requirements }}"
    timeout: 300
  - id: step2
    skill: generate_code
    inputs:
      plan: "{{ steps.step1.outputs.result }}"
    timeout: 600
"""


@pytest.fixture
def sample_workflow_definition():
    """Sample WorkflowDefinition object."""
    from src.workflow_engine import WorkflowDefinition, WorkflowMetadata, WorkflowStep

    return WorkflowDefinition(
        metadata=WorkflowMetadata(
            id="test-workflow-v1", name="Test Workflow", version="1.0.0"
        ),
        steps=[
            WorkflowStep(
                id="step1",
                skill="create_plan",
                inputs={"requirements": "{{ workflow.input.requirements }}"},
            ),
            WorkflowStep(
                id="step2",
                skill="generate_code",
                inputs={"plan": "{{ steps.step1.outputs.result }}"},
            ),
        ],
    )
