"""Tests for BaseAgent class."""

import pytest
import json
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient

from src.agents.base import BaseAgent, SkillDefinition, Message
from tests.fixtures.sample_data import CLAUDE_JSON_WRAPPED, CLAUDE_JSON_PLAIN, CLAUDE_INVALID_JSON


class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    async def execute_skill(self, skill_id: str, params: dict) -> dict:
        """Simple test implementation."""
        if skill_id == "test_skill":
            return {"result": params.get("param", "default")}
        raise ValueError(f"Unknown skill: {skill_id}")


@pytest.fixture
def test_agent(sample_skill):
    """Create a test agent instance."""
    return ConcreteAgent(
        name="test-agent",
        port=9999,
        skills=[sample_skill]
    )


@pytest.fixture
def test_client(test_agent):
    """Create a test client for the agent."""
    return TestClient(test_agent.app)


class TestBaseAgentInitialization:
    """Tests for BaseAgent initialization."""

    def test_agent_initialization(self, test_agent, sample_skill):
        """Test that BaseAgent initializes correctly."""
        assert test_agent.name == "test-agent"
        assert test_agent.port == 9999
        assert len(test_agent.skills) == 1
        assert test_agent.skills[0].id == sample_skill.id
        assert test_agent.app is not None

    def test_agent_multiple_skills(self):
        """Test agent with multiple skills."""
        skills = [
            SkillDefinition(id="skill1", description="Skill 1"),
            SkillDefinition(id="skill2", description="Skill 2")
        ]
        agent = ConcreteAgent(name="multi", port=8888, skills=skills)
        assert len(agent.skills) == 2


class TestAgentCardEndpoint:
    """Tests for /agent-card endpoint."""

    def test_get_agent_card(self, test_client, sample_skill):
        """Test GET /agent-card returns correct structure."""
        response = test_client.get("/agent-card")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "test-agent"
        assert data["url"] == "http://localhost:9999"
        assert len(data["skills"]) == 1
        assert data["skills"][0]["id"] == sample_skill.id
        assert data["skills"][0]["description"] == sample_skill.description

    def test_agent_card_includes_schemas(self, test_client, sample_skill):
        """Test that agent card includes input/output schemas."""
        response = test_client.get("/agent-card")
        data = response.json()

        skill = data["skills"][0]
        assert "input_schema" in skill
        assert "output_schema" in skill
        assert skill["input_schema"] == sample_skill.input_schema
        assert skill["output_schema"] == sample_skill.output_schema


class TestExecuteEndpoint:
    """Tests for /execute endpoint."""

    def test_execute_valid_skill(self, test_client):
        """Test executing a valid skill."""
        message = {
            "jsonrpc": "2.0",
            "method": "test_skill",
            "params": {"param": "test_value"},
            "id": "123"
        }
        response = test_client.post("/execute", json=message)
        assert response.status_code == 200

        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "123"
        assert "result" in data
        assert data["result"]["result"] == "test_value"

    def test_execute_unknown_skill(self, test_client):
        """Test executing an unknown skill returns error."""
        message = {
            "jsonrpc": "2.0",
            "method": "unknown_skill",
            "params": {},
            "id": "456"
        }
        response = test_client.post("/execute", json=message)
        # Returns 200 with error in JSON body (caught by general exception handler)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Unknown skill" in data["error"]["message"]

    def test_execute_returns_error_on_exception(self, test_client):
        """Test that exceptions in execute_skill are handled."""
        # This will trigger the ValueError in execute_skill
        message = {
            "jsonrpc": "2.0",
            "method": "invalid",
            "params": {},
            "id": "789"
        }
        response = test_client.post("/execute", json=message)

        # Returns 200 with error in JSON body
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Unknown skill" in data["error"]["message"]

    def test_execute_jsonrpc_format(self, test_client):
        """Test that response follows JSON-RPC 2.0 format."""
        message = {
            "jsonrpc": "2.0",
            "method": "test_skill",
            "params": {"param": "value"},
            "id": "abc"
        }
        response = test_client.post("/execute", json=message)
        data = response.json()

        assert "jsonrpc" in data
        assert data["jsonrpc"] == "2.0"
        assert "result" in data or "error" in data
        assert data["id"] == "abc"


class TestCallClaude:
    """Tests for call_claude method."""

    @pytest.mark.asyncio
    async def test_call_claude_success(self, test_agent):
        """Test successful Claude CLI call."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(
            return_value=(b'{"result": "test"}', b'')
        )

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            result = await test_agent.call_claude(
                "system prompt",
                "user message"
            )
            assert result == '{"result": "test"}'

    @pytest.mark.asyncio
    async def test_call_claude_combines_prompts(self, test_agent):
        """Test that call_claude combines system and user prompts."""
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b'test', b''))

        with patch('asyncio.create_subprocess_exec', return_value=mock_process) as mock_exec:
            await test_agent.call_claude("system", "user")

            # Verify the command includes the combined prompt
            args = mock_exec.call_args[0]
            assert args[0] == "claude"
            assert args[1] == "-p"
            assert args[2] == "--dangerously-skip-permissions"
            assert "system" in args[3]
            assert "user" in args[3]

    @pytest.mark.asyncio
    async def test_call_claude_failure(self, test_agent):
        """Test Claude CLI call failure."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b'', b'Error message')
        )

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(RuntimeError, match="Claude code CLI failed"):
                await test_agent.call_claude("system", "user")

    @pytest.mark.asyncio
    async def test_call_claude_not_found(self, test_agent):
        """Test Claude CLI not found."""
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError, match="Claude code CLI not found"):
                await test_agent.call_claude("system", "user")


class TestCallAgentSkill:
    """Tests for call_agent_skill method."""

    @pytest.mark.asyncio
    async def test_call_agent_skill_success(self, test_agent):
        """Test successful agent-to-agent skill call."""
        mock_response = Mock()
        mock_response.json = Mock(return_value={
            "jsonrpc": "2.0",
            "result": {"data": "test"},
            "id": "1"
        })
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await test_agent.call_agent_skill(
                agent_url="http://localhost:8001",
                skill_id="test_skill",
                params={"key": "value"}
            )

            assert result["jsonrpc"] == "2.0"
            assert result["result"]["data"] == "test"

    @pytest.mark.asyncio
    async def test_call_agent_skill_constructs_message(self, test_agent):
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

        with patch('httpx.AsyncClient', return_value=mock_client) as mock:
            await test_agent.call_agent_skill(
                agent_url="http://test:8000",
                skill_id="my_skill",
                params={"param1": "value1"}
            )

            # Verify the POST was called with correct structure
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "http://test:8000/execute"

            message = call_args[1]["json"]
            assert message["jsonrpc"] == "2.0"
            assert message["method"] == "my_skill"
            assert message["params"] == {"param1": "value1"}
            assert message["id"] == "1"


class TestJSONParsing:
    """Tests for JSON parsing robustness in agents."""

    def test_parse_json_wrapped(self):
        """Test parsing JSON wrapped in markdown code blocks."""
        # This test uses the pattern from plan_agent.py
        response = CLAUDE_JSON_WRAPPED

        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        data = json.loads(json_str)
        assert "title" in data
        assert data["title"] == "Test Plan"

    def test_parse_json_plain(self):
        """Test parsing plain JSON."""
        response = CLAUDE_JSON_PLAIN
        json_str = response.strip()
        data = json.loads(json_str)
        assert "title" in data

    def test_parse_invalid_json_handling(self):
        """Test handling of invalid JSON."""
        response = CLAUDE_INVALID_JSON

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            json.loads(json_str)
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            # Expected behavior
            pass
