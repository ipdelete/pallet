"""Tests for Test Agent (code reviewer)."""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.agents.test_agent import TestAgent
from tests.fixtures.sample_data import (
    CODE_EMAIL_VALIDATOR,
    CODE_FIBONACCI,
    REVIEW_GOOD,
    REVIEW_POOR,
)


@pytest.fixture
def test_agent():
    """Create a TestAgent instance."""
    return TestAgent()


@pytest.fixture
def test_client(test_agent):
    """Create a test client for TestAgent."""
    return TestClient(test_agent.app)


class TestTestAgentInitialization:
    """Tests for TestAgent initialization."""

    def test_agent_name_and_port(self, test_agent):
        """Test that TestAgent has correct name and port."""
        assert test_agent.name == "test-agent"
        assert test_agent.port == 8003

    def test_agent_has_review_code_skill(self, test_agent):
        """Test that TestAgent has review_code skill."""
        assert len(test_agent.skills) == 1
        skill = test_agent.skills[0]
        assert skill.id == "review_code"
        assert skill.description is not None

    def test_review_code_skill_schema(self, test_agent):
        """Test that review_code skill has proper schemas."""
        skill = test_agent.skills[0]

        # Check input schema
        assert skill.input_schema is not None
        assert skill.input_schema["type"] == "object"
        assert "code" in skill.input_schema["properties"]
        assert "code" in skill.input_schema["required"]
        assert "language" in skill.input_schema["properties"]

        # Check output schema
        assert skill.output_schema is not None
        assert skill.output_schema["type"] == "object"
        assert "quality_score" in skill.output_schema["properties"]
        assert "approved" in skill.output_schema["properties"]
        assert "issues" in skill.output_schema["properties"]


class TestTestAgentEndpoints:
    """Tests for TestAgent endpoints."""

    def test_agent_card(self, test_client):
        """Test that agent card endpoint works."""
        response = test_client.get("/agent-card")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "test-agent"
        assert data["url"] == "http://localhost:8003"
        assert len(data["skills"]) == 1
        assert data["skills"][0]["id"] == "review_code"


class TestExecuteSkill:
    """Tests for execute_skill method."""

    @pytest.mark.asyncio
    async def test_execute_review_code_success(self, test_agent):
        """Test successful code review."""
        review_json = json.dumps(REVIEW_GOOD)
        with patch.object(
            test_agent, "call_claude", new=AsyncMock(return_value=review_json)
        ):
            result = await test_agent.execute_skill(
                "review_code", {"code": CODE_EMAIL_VALIDATOR, "language": "python"}
            )

            assert "quality_score" in result
            assert "issues" in result
            assert "suggestions" in result
            assert "approved" in result
            assert "summary" in result

    @pytest.mark.asyncio
    async def test_execute_review_code_default_language(self, test_agent):
        """Test code review with default language (python)."""
        review_json = json.dumps(REVIEW_GOOD)
        with patch.object(
            test_agent, "call_claude", new=AsyncMock(return_value=review_json)
        ):
            result = await test_agent.execute_skill(
                "review_code", {"code": CODE_EMAIL_VALIDATOR}
            )

            assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_execute_review_poor_code(self, test_agent):
        """Test review of poor quality code."""
        review_json = json.dumps(REVIEW_POOR)
        with patch.object(
            test_agent, "call_claude", new=AsyncMock(return_value=review_json)
        ):
            result = await test_agent.execute_skill(
                "review_code", {"code": "bad code", "language": "python"}
            )

            assert result["quality_score"] == 4
            assert result["approved"] is False
            assert len(result["issues"]) > 0

    @pytest.mark.asyncio
    async def test_execute_unknown_skill(self, test_agent):
        """Test executing unknown skill raises error."""
        with pytest.raises(ValueError, match="Unknown skill"):
            await test_agent.execute_skill("unknown_skill", {})

    @pytest.mark.asyncio
    async def test_execute_missing_code(self, test_agent):
        """Test executing without code raises error."""
        with pytest.raises(ValueError, match="code parameter is required"):
            await test_agent.execute_skill("review_code", {})

    @pytest.mark.asyncio
    async def test_execute_with_invalid_json_response(self, test_agent):
        """Test code review with invalid JSON response."""
        with patch.object(
            test_agent, "call_claude", new=AsyncMock(return_value="Not valid JSON")
        ):
            result = await test_agent.execute_skill(
                "review_code", {"code": CODE_EMAIL_VALIDATOR}
            )

            # Should return fallback structure
            assert "quality_score" in result
            assert result["quality_score"] == 0
            assert result["approved"] is False
            assert "error" in result


class TestClaudeIntegration:
    """Tests for Claude CLI integration."""

    @pytest.mark.asyncio
    async def test_calls_claude_with_code(self, test_agent):
        """Test that execute_skill calls Claude with the code."""
        mock_claude = AsyncMock(return_value=json.dumps(REVIEW_GOOD))

        with patch.object(test_agent, "call_claude", mock_claude):
            await test_agent.execute_skill(
                "review_code", {"code": CODE_EMAIL_VALIDATOR, "language": "python"}
            )

            # Verify Claude was called
            mock_claude.assert_called_once()

            # Check the arguments
            call_args = mock_claude.call_args[0]
            system_prompt = call_args[0]
            user_message = call_args[1]

            # System prompt should mention code review
            assert "review" in system_prompt.lower()
            assert "python" in system_prompt.lower()

            # User message should include the code
            assert (
                CODE_EMAIL_VALIDATOR in user_message or "review" in user_message.lower()
            )

    @pytest.mark.asyncio
    async def test_supports_multiple_languages(self, test_agent):
        """Test that review supports different languages."""
        mock_claude = AsyncMock(return_value=json.dumps(REVIEW_GOOD))

        with patch.object(test_agent, "call_claude", mock_claude):
            # Test with JavaScript
            await test_agent.execute_skill(
                "review_code", {"code": "function test() {}", "language": "javascript"}
            )

            call_args = mock_claude.call_args[0]
            system_prompt = call_args[0]
            assert "javascript" in system_prompt.lower()


class TestEndToEndExecution:
    """End-to-end tests via HTTP."""

    def test_execute_review_code_via_http(self, test_client, test_agent):
        """Test reviewing code via HTTP POST."""
        mock_response = json.dumps(REVIEW_GOOD)

        with patch.object(
            test_agent, "call_claude", new=AsyncMock(return_value=mock_response)
        ):
            message = {
                "jsonrpc": "2.0",
                "method": "review_code",
                "params": {"code": CODE_EMAIL_VALIDATOR, "language": "python"},
                "id": "test-123",
            }

            response = test_client.post("/execute", json=message)
            assert response.status_code == 200

            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "test-123"
            assert "result" in data
            assert data["result"]["quality_score"] == 9
            assert data["result"]["approved"] is True

    def test_execute_with_missing_params(self, test_client):
        """Test execution with missing code parameter."""
        message = {
            "jsonrpc": "2.0",
            "method": "review_code",
            "params": {},
            "id": "test-456",
        }

        response = test_client.post("/execute", json=message)
        assert response.status_code == 200

        data = response.json()
        assert "error" in data
        assert "code" in data["error"]["message"].lower()
