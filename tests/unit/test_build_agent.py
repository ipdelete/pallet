"""Tests for Build Agent."""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.agents.build_agent import BuildAgent
from tests.fixtures.sample_data import (
    PLAN_EMAIL_VALIDATOR,
    CODE_EMAIL_VALIDATOR,
    CODE_RESULT_EMAIL,
)


@pytest.fixture
def build_agent():
    """Create a BuildAgent instance."""
    return BuildAgent()


@pytest.fixture
def test_client(build_agent):
    """Create a test client for BuildAgent."""
    return TestClient(build_agent.app)


class TestBuildAgentInitialization:
    """Tests for BuildAgent initialization."""

    def test_agent_name_and_port(self, build_agent):
        """Test that BuildAgent has correct name and port."""
        assert build_agent.name == "build-agent"
        assert build_agent.port == 8002

    def test_agent_has_generate_code_skill(self, build_agent):
        """Test that BuildAgent has generate_code skill."""
        assert len(build_agent.skills) == 1
        skill = build_agent.skills[0]
        assert skill.id == "generate_code"
        assert skill.description is not None

    def test_generate_code_skill_schema(self, build_agent):
        """Test that generate_code skill has proper schemas."""
        skill = build_agent.skills[0]

        # Check input schema
        assert skill.input_schema is not None
        assert skill.input_schema["type"] == "object"
        assert "plan" in skill.input_schema["properties"]
        assert "plan" in skill.input_schema["required"]

        # Check output schema
        assert skill.output_schema is not None
        assert skill.output_schema["type"] == "object"
        assert "code" in skill.output_schema["properties"]
        assert "language" in skill.output_schema["properties"]


class TestBuildAgentEndpoints:
    """Tests for BuildAgent endpoints."""

    def test_agent_card(self, test_client):
        """Test that agent card endpoint works."""
        response = test_client.get("/agent-card")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "build-agent"
        assert data["url"] == "http://localhost:8002"
        assert len(data["skills"]) == 1
        assert data["skills"][0]["id"] == "generate_code"


class TestExecuteSkill:
    """Tests for execute_skill method."""

    @pytest.mark.asyncio
    async def test_execute_generate_code_success(self, build_agent):
        """Test successful code generation."""
        code_result_json = json.dumps(CODE_RESULT_EMAIL)
        with patch.object(
            build_agent, "call_claude", new=AsyncMock(return_value=code_result_json)
        ):
            result = await build_agent.execute_skill(
                "generate_code", {"plan": PLAN_EMAIL_VALIDATOR}
            )

            assert "code" in result
            assert "explanation" in result
            assert "language" in result
            assert "functions" in result

    @pytest.mark.asyncio
    async def test_execute_with_dict_plan(self, build_agent):
        """Test code generation with dict plan (converts to JSON string)."""
        code_result_json = json.dumps(CODE_RESULT_EMAIL)
        with patch.object(
            build_agent, "call_claude", new=AsyncMock(return_value=code_result_json)
        ):
            result = await build_agent.execute_skill(
                "generate_code", {"plan": PLAN_EMAIL_VALIDATOR}
            )

            assert "code" in result

    @pytest.mark.asyncio
    async def test_execute_with_string_plan(self, build_agent):
        """Test code generation with string plan."""
        code_result_json = json.dumps(CODE_RESULT_EMAIL)
        with patch.object(
            build_agent, "call_claude", new=AsyncMock(return_value=code_result_json)
        ):
            result = await build_agent.execute_skill(
                "generate_code", {"plan": "Simple plan as string"}
            )

            assert "code" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_skill(self, build_agent):
        """Test executing unknown skill raises error."""
        with pytest.raises(ValueError, match="Unknown skill"):
            await build_agent.execute_skill("unknown_skill", {})

    @pytest.mark.asyncio
    async def test_execute_missing_plan(self, build_agent):
        """Test executing without plan raises error."""
        with pytest.raises(ValueError, match="plan parameter is required"):
            await build_agent.execute_skill("generate_code", {})

    @pytest.mark.asyncio
    async def test_execute_with_invalid_json_response(self, build_agent):
        """Test code generation with invalid JSON response."""
        with patch.object(
            build_agent, "call_claude", new=AsyncMock(return_value="Not valid JSON")
        ):
            result = await build_agent.execute_skill(
                "generate_code", {"plan": PLAN_EMAIL_VALIDATOR}
            )

            # Should return fallback structure
            assert "code" in result
            assert "error" in result


class TestClaudeIntegration:
    """Tests for Claude CLI integration."""

    @pytest.mark.asyncio
    async def test_calls_claude_with_plan(self, build_agent):
        """Test that execute_skill calls Claude with the plan."""
        mock_claude = AsyncMock(return_value=json.dumps(CODE_RESULT_EMAIL))

        with patch.object(build_agent, "call_claude", mock_claude):
            await build_agent.execute_skill(
                "generate_code", {"plan": PLAN_EMAIL_VALIDATOR}
            )

            # Verify Claude was called
            mock_claude.assert_called_once()

            # Check the arguments
            call_args = mock_claude.call_args[0]
            system_prompt = call_args[0]
            user_message = call_args[1]

            # System prompt should mention code generation
            assert "code" in system_prompt.lower()
            assert "python" in system_prompt.lower()

            # User message should include plan content
            assert "Email Validator" in user_message or "plan" in user_message.lower()


class TestEndToEndExecution:
    """End-to-end tests via HTTP."""

    def test_execute_generate_code_via_http(self, test_client, build_agent):
        """Test generating code via HTTP POST."""
        mock_response = json.dumps(CODE_RESULT_EMAIL)

        with patch.object(
            build_agent, "call_claude", new=AsyncMock(return_value=mock_response)
        ):
            message = {
                "jsonrpc": "2.0",
                "method": "generate_code",
                "params": {"plan": PLAN_EMAIL_VALIDATOR},
                "id": "build-123",
            }

            response = test_client.post("/execute", json=message)
            assert response.status_code == 200

            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "build-123"
            assert "result" in data
            assert data["result"]["language"] == "python"

    def test_execute_with_missing_params(self, test_client):
        """Test execution with missing plan parameter."""
        message = {
            "jsonrpc": "2.0",
            "method": "generate_code",
            "params": {},
            "id": "build-456",
        }

        response = test_client.post("/execute", json=message)
        assert response.status_code == 200

        data = response.json()
        assert "error" in data
        assert "plan" in data["error"]["message"].lower()
