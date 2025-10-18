"""Tests for Plan Agent."""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.agents.plan_agent import PlanAgent
from tests.fixtures.sample_data import (
    REQUIREMENTS_EMAIL_VALIDATOR,
    PLAN_EMAIL_VALIDATOR,
    CLAUDE_JSON_WRAPPED,
    CLAUDE_INVALID_JSON
)


@pytest.fixture
def plan_agent():
    """Create a PlanAgent instance."""
    return PlanAgent()


@pytest.fixture
def test_client(plan_agent):
    """Create a test client for PlanAgent."""
    return TestClient(plan_agent.app)


class TestPlanAgentInitialization:
    """Tests for PlanAgent initialization."""

    def test_agent_name_and_port(self, plan_agent):
        """Test that PlanAgent has correct name and port."""
        assert plan_agent.name == "plan-agent"
        assert plan_agent.port == 8001

    def test_agent_has_create_plan_skill(self, plan_agent):
        """Test that PlanAgent has create_plan skill."""
        assert len(plan_agent.skills) == 1
        skill = plan_agent.skills[0]
        assert skill.id == "create_plan"
        assert skill.description is not None

    def test_create_plan_skill_schema(self, plan_agent):
        """Test that create_plan skill has proper schemas."""
        skill = plan_agent.skills[0]

        # Check input schema
        assert skill.input_schema is not None
        assert skill.input_schema["type"] == "object"
        assert "requirements" in skill.input_schema["properties"]
        assert "requirements" in skill.input_schema["required"]

        # Check output schema
        assert skill.output_schema is not None
        assert skill.output_schema["type"] == "object"
        assert "title" in skill.output_schema["properties"]
        assert "steps" in skill.output_schema["properties"]


class TestPlanAgentEndpoints:
    """Tests for PlanAgent endpoints."""

    def test_agent_card(self, test_client):
        """Test that agent card endpoint works."""
        response = test_client.get("/agent-card")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "plan-agent"
        assert data["url"] == "http://localhost:8001"
        assert len(data["skills"]) == 1
        assert data["skills"][0]["id"] == "create_plan"


class TestExecuteSkill:
    """Tests for execute_skill method."""

    @pytest.mark.asyncio
    async def test_execute_create_plan_success(self, plan_agent):
        """Test successful plan creation."""
        # Mock the call_claude method
        plan_json = json.dumps(PLAN_EMAIL_VALIDATOR)
        with patch.object(plan_agent, 'call_claude', new=AsyncMock(return_value=plan_json)):
            result = await plan_agent.execute_skill(
                "create_plan",
                {"requirements": REQUIREMENTS_EMAIL_VALIDATOR}
            )

            assert "title" in result
            assert "steps" in result
            assert "dependencies" in result
            assert "estimated_total_time" in result

    @pytest.mark.asyncio
    async def test_execute_create_plan_with_wrapped_json(self, plan_agent):
        """Test plan creation with JSON wrapped in markdown."""
        with patch.object(plan_agent, 'call_claude', new=AsyncMock(return_value=CLAUDE_JSON_WRAPPED)):
            result = await plan_agent.execute_skill(
                "create_plan",
                {"requirements": "test requirement"}
            )

            # Should successfully parse the wrapped JSON
            assert "title" in result
            assert result["title"] == "Test Plan"

    @pytest.mark.asyncio
    async def test_execute_create_plan_invalid_json(self, plan_agent):
        """Test plan creation with invalid JSON response."""
        with patch.object(plan_agent, 'call_claude', new=AsyncMock(return_value=CLAUDE_INVALID_JSON)):
            result = await plan_agent.execute_skill(
                "create_plan",
                {"requirements": "test"}
            )

            # Should return error structure
            assert "error" in result
            assert "raw_response" in result

    @pytest.mark.asyncio
    async def test_execute_unknown_skill(self, plan_agent):
        """Test executing unknown skill raises error."""
        with pytest.raises(ValueError, match="Unknown skill"):
            await plan_agent.execute_skill("unknown_skill", {})

    @pytest.mark.asyncio
    async def test_execute_missing_requirements(self, plan_agent):
        """Test executing without requirements raises error."""
        with pytest.raises(ValueError, match="requirements parameter is required"):
            await plan_agent.execute_skill("create_plan", {})

    @pytest.mark.asyncio
    async def test_execute_empty_requirements(self, plan_agent):
        """Test executing with empty requirements raises error."""
        with pytest.raises(ValueError, match="requirements parameter is required"):
            await plan_agent.execute_skill("create_plan", {"requirements": ""})


class TestCLaudeIntegration:
    """Tests for Claude CLI integration."""

    @pytest.mark.asyncio
    async def test_calls_claude_with_correct_prompts(self, plan_agent):
        """Test that execute_skill calls Claude with proper prompts."""
        mock_claude = AsyncMock(return_value='{"title": "test", "steps": [], "dependencies": [], "estimated_total_time": "1 min"}')

        with patch.object(plan_agent, 'call_claude', mock_claude):
            await plan_agent.execute_skill(
                "create_plan",
                {"requirements": "Test requirement"}
            )

            # Verify Claude was called
            mock_claude.assert_called_once()

            # Check the arguments
            call_args = mock_claude.call_args[0]
            system_prompt = call_args[0]
            user_message = call_args[1]

            # System prompt should mention planning
            assert "plan" in system_prompt.lower()
            assert "json" in system_prompt.lower()

            # User message should include the requirements
            assert "Test requirement" in user_message


class TestEndToEndExecution:
    """End-to-end tests via HTTP."""

    def test_execute_create_plan_via_http(self, test_client, plan_agent):
        """Test creating a plan via HTTP POST."""
        mock_response = json.dumps({
            "title": "Test Implementation",
            "steps": [{"name": "Step 1", "description": "Do something", "time": "5 min"}],
            "dependencies": [],
            "estimated_total_time": "5 minutes"
        })

        with patch.object(plan_agent, 'call_claude', new=AsyncMock(return_value=mock_response)):
            message = {
                "jsonrpc": "2.0",
                "method": "create_plan",
                "params": {"requirements": "Create a test function"},
                "id": "test-123"
            }

            response = test_client.post("/execute", json=message)
            assert response.status_code == 200

            data = response.json()
            assert data["jsonrpc"] == "2.0"
            assert data["id"] == "test-123"
            assert "result" in data
            assert data["result"]["title"] == "Test Implementation"

    def test_execute_with_missing_params(self, test_client):
        """Test execution with missing requirements parameter."""
        message = {
            "jsonrpc": "2.0",
            "method": "create_plan",
            "params": {},
            "id": "test-456"
        }

        response = test_client.post("/execute", json=message)
        assert response.status_code == 200

        data = response.json()
        assert "error" in data
        assert "requirements" in data["error"]["message"].lower()
