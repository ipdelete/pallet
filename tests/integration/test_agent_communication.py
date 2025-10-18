"""Integration tests for A2A (Agent-to-Agent) protocol communication."""

import pytest
from unittest.mock import AsyncMock, patch, Mock
import json

from src.agents.plan_agent import PlanAgent
from src.agents.build_agent import BuildAgent
from src.agents.test_agent import TestAgent
from tests.fixtures.sample_data import (
    REQUIREMENTS_EMAIL_VALIDATOR,
    PLAN_EMAIL_VALIDATOR,
    CODE_RESULT_EMAIL,
    REVIEW_GOOD
)


class TestAgentToAgentCalls:
    """Tests for agent-to-agent communication."""

    @pytest.mark.asyncio
    async def test_agent_can_call_another_agent(self):
        """Test that one agent can call another agent's skill."""
        agent1 = PlanAgent()
        agent2 = BuildAgent()

        # Mock the HTTP client to simulate agent communication
        mock_response = {
            "jsonrpc": "2.0",
            "result": CODE_RESULT_EMAIL,
            "id": "1"
        }

        mock_http_response = Mock()
        mock_http_response.json = Mock(return_value=mock_response)
        mock_http_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_http_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('httpx.AsyncClient', return_value=mock_client):
            result = await agent1.call_agent_skill(
                agent_url="http://localhost:8002",
                skill_id="generate_code",
                params={"plan": PLAN_EMAIL_VALIDATOR}
            )

            assert result["jsonrpc"] == "2.0"
            assert "result" in result
            assert result["result"] == CODE_RESULT_EMAIL

    @pytest.mark.asyncio
    async def test_jsonrpc_message_format(self):
        """Test that agent-to-agent calls use proper JSON-RPC format."""
        agent = PlanAgent()

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
            await agent.call_agent_skill(
                agent_url="http://localhost:8002",
                skill_id="test_skill",
                params={"key": "value"}
            )

            # Verify the POST request was made with correct structure
            call_args = mock_client.post.call_args
            message = call_args[1]["json"]

            assert message["jsonrpc"] == "2.0"
            assert message["method"] == "test_skill"
            assert message["params"] == {"key": "value"}
            assert "id" in message


class TestPipelineCommunication:
    """Tests for multi-agent pipeline communication."""

    @pytest.mark.asyncio
    async def test_plan_to_build_communication(self):
        """Test communication from Plan Agent to Build Agent."""
        plan_agent = PlanAgent()

        # Mock Plan Agent's Claude call
        plan_json = json.dumps(PLAN_EMAIL_VALIDATOR)
        with patch.object(plan_agent, 'call_claude', new=AsyncMock(return_value=plan_json)):
            # Execute Plan Agent
            plan = await plan_agent.execute_skill(
                "create_plan",
                {"requirements": REQUIREMENTS_EMAIL_VALIDATOR}
            )

            # Verify plan can be passed to Build Agent
            assert "title" in plan
            assert "steps" in plan

            # Mock Build Agent receiving this plan
            build_agent = BuildAgent()
            code_json = json.dumps(CODE_RESULT_EMAIL)

            with patch.object(build_agent, 'call_claude', new=AsyncMock(return_value=code_json)):
                code_result = await build_agent.execute_skill(
                    "generate_code",
                    {"plan": plan}  # Plan output becomes Build input
                )

                assert "code" in code_result
                assert "language" in code_result

    @pytest.mark.asyncio
    async def test_build_to_test_communication(self):
        """Test communication from Build Agent to Test Agent."""
        build_agent = BuildAgent()

        # Mock Build Agent's Claude call
        code_json = json.dumps(CODE_RESULT_EMAIL)
        with patch.object(build_agent, 'call_claude', new=AsyncMock(return_value=code_json)):
            # Execute Build Agent
            code_result = await build_agent.execute_skill(
                "generate_code",
                {"plan": PLAN_EMAIL_VALIDATOR}
            )

            # Verify code can be passed to Test Agent
            assert "code" in code_result
            assert "language" in code_result

            # Mock Test Agent receiving this code
            test_agent = TestAgent()
            review_json = json.dumps(REVIEW_GOOD)

            with patch.object(test_agent, 'call_claude', new=AsyncMock(return_value=review_json)):
                review = await test_agent.execute_skill(
                    "review_code",
                    {
                        "code": code_result["code"],  # Build output becomes Test input
                        "language": code_result["language"]
                    }
                )

                assert "quality_score" in review
                assert "approved" in review

    @pytest.mark.asyncio
    async def test_full_three_agent_pipeline(self):
        """Test full Plan → Build → Test pipeline."""
        # Step 1: Plan Agent
        plan_agent = PlanAgent()
        plan_json = json.dumps(PLAN_EMAIL_VALIDATOR)

        with patch.object(plan_agent, 'call_claude', new=AsyncMock(return_value=plan_json)):
            plan = await plan_agent.execute_skill(
                "create_plan",
                {"requirements": REQUIREMENTS_EMAIL_VALIDATOR}
            )

        # Step 2: Build Agent (receives plan)
        build_agent = BuildAgent()
        code_json = json.dumps(CODE_RESULT_EMAIL)

        with patch.object(build_agent, 'call_claude', new=AsyncMock(return_value=code_json)):
            code_result = await build_agent.execute_skill(
                "generate_code",
                {"plan": plan}
            )

        # Step 3: Test Agent (receives code)
        test_agent = TestAgent()
        review_json = json.dumps(REVIEW_GOOD)

        with patch.object(test_agent, 'call_claude', new=AsyncMock(return_value=review_json)):
            review = await test_agent.execute_skill(
                "review_code",
                {
                    "code": code_result["code"],
                    "language": code_result["language"]
                }
            )

        # Verify end-to-end data flow
        assert plan["title"] == PLAN_EMAIL_VALIDATOR["title"]
        assert "validate_email" in code_result["functions"]
        assert review["quality_score"] == REVIEW_GOOD["quality_score"]
        assert review["approved"] is True


class TestErrorHandling:
    """Tests for error handling in agent communication."""

    @pytest.mark.asyncio
    async def test_http_error_propagation(self):
        """Test that HTTP errors are properly propagated."""
        agent = PlanAgent()

        async def raise_error(*args, **kwargs):
            raise Exception("Connection refused")

        mock_client = Mock()
        mock_client.post = AsyncMock(side_effect=raise_error)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(Exception, match="Connection refused"):
                await agent.call_agent_skill(
                    agent_url="http://localhost:9999",
                    skill_id="test_skill",
                    params={}
                )

    @pytest.mark.asyncio
    async def test_invalid_response_handling(self):
        """Test handling of invalid JSON responses."""
        agent = PlanAgent()

        mock_response = Mock()
        # Invalid JSON structure (missing jsonrpc field)
        mock_response.json = Mock(return_value={"invalid": "response"})
        mock_response.raise_for_status = Mock()

        mock_client = Mock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch('httpx.AsyncClient', return_value=mock_client):
            # Should still return the response even if format is unexpected
            result = await agent.call_agent_skill(
                agent_url="http://localhost:8002",
                skill_id="test_skill",
                params={}
            )

            # Response is returned as-is
            assert result == {"invalid": "response"}


class TestTimeout:
    """Tests for timeout handling in agent communication."""

    @pytest.mark.asyncio
    async def test_custom_timeout(self):
        """Test that custom timeout is respected."""
        agent = PlanAgent()

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
            await agent.call_agent_skill(
                agent_url="http://localhost:8002",
                skill_id="test_skill",
                params={}
            )

            # Verify timeout was passed (default 30.0)
            call_args = mock_client.post.call_args
            assert call_args[1]["timeout"] == 30.0
