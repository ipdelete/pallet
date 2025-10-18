"""Tests for FastAPI endpoints across all agents."""

import pytest
from fastapi.testclient import TestClient

from src.agents.plan_agent import PlanAgent
from src.agents.build_agent import BuildAgent
from src.agents.test_agent import TestAgent


class TestCommonEndpoints:
    """Tests for common endpoints across all agents."""

    @pytest.fixture(params=[PlanAgent, BuildAgent, TestAgent])
    def agent_client(self, request):
        """Parametrized fixture for testing all agents."""
        agent = request.param()
        return TestClient(agent.app), agent

    def test_agent_card_endpoint_exists(self, agent_client):
        """Test that /agent-card endpoint exists for all agents."""
        client, _ = agent_client
        response = client.get("/agent-card")
        assert response.status_code == 200

    def test_agent_card_structure(self, agent_client):
        """Test that agent card has required fields."""
        client, _ = agent_client
        response = client.get("/agent-card")
        data = response.json()

        assert "name" in data
        assert "url" in data
        assert "skills" in data
        assert isinstance(data["skills"], list)

    def test_agent_card_skills_have_schemas(self, agent_client):
        """Test that skills in agent card have input/output schemas."""
        client, _ = agent_client
        response = client.get("/agent-card")
        data = response.json()

        for skill in data["skills"]:
            assert "id" in skill
            assert "description" in skill
            assert "input_schema" in skill
            assert "output_schema" in skill

    def test_execute_endpoint_exists(self, agent_client):
        """Test that /execute endpoint exists for all agents."""
        client, _ = agent_client
        message = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {},
            "id": "1"
        }
        # Should return 404 for unknown skill, not 405 for missing endpoint
        response = client.post("/execute", json=message)
        assert response.status_code in [200, 404]  # 200 with error or 404

    def test_execute_invalid_method(self, agent_client):
        """Test executing with invalid HTTP method."""
        client, _ = agent_client
        response = client.get("/execute")
        assert response.status_code == 405  # Method not allowed


class TestJSONRPCCompliance:
    """Tests for JSON-RPC 2.0 compliance."""

    @pytest.fixture
    def plan_client(self):
        """Client for plan agent."""
        return TestClient(PlanAgent().app)

    def test_jsonrpc_version_in_response(self, plan_client):
        """Test that responses include jsonrpc version."""
        message = {
            "jsonrpc": "2.0",
            "method": "create_plan",
            "params": {"requirements": "test"},
            "id": "123"
        }

        response = plan_client.post("/execute", json=message)
        data = response.json()

        assert "jsonrpc" in data
        assert data["jsonrpc"] == "2.0"

    def test_response_includes_id(self, plan_client):
        """Test that responses include the request ID."""
        message = {
            "jsonrpc": "2.0",
            "method": "create_plan",
            "params": {"requirements": "test"},
            "id": "custom-id"
        }

        response = plan_client.post("/execute", json=message)
        data = response.json()

        assert data["id"] == "custom-id"

    def test_response_has_result_or_error(self, plan_client):
        """Test that responses have either result or error."""
        message = {
            "jsonrpc": "2.0",
            "method": "create_plan",
            "params": {"requirements": "test"},
            "id": "1"
        }

        response = plan_client.post("/execute", json=message)
        data = response.json()

        # Must have either result or error, but not both
        has_result = "result" in data
        has_error = "error" in data

        assert has_result != has_error  # XOR: exactly one must be true

    def test_error_structure(self, plan_client):
        """Test that error responses have proper structure."""
        message = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "params": {},
            "id": "1"
        }

        response = plan_client.post("/execute", json=message)

        # BaseAgent returns 200 with error in JSON body
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "message" in data["error"]
        assert "Unknown skill" in data["error"]["message"]


class TestPlanAgentEndpoints:
    """Tests specific to Plan Agent endpoints."""

    @pytest.fixture
    def client(self):
        """Client for plan agent."""
        return TestClient(PlanAgent().app)

    def test_agent_card_name(self, client):
        """Test that plan agent has correct name."""
        response = client.get("/agent-card")
        data = response.json()
        assert data["name"] == "plan-agent"

    def test_agent_card_url(self, client):
        """Test that plan agent has correct URL."""
        response = client.get("/agent-card")
        data = response.json()
        assert "8001" in data["url"]

    def test_create_plan_skill_exists(self, client):
        """Test that create_plan skill is in agent card."""
        response = client.get("/agent-card")
        data = response.json()

        skill_ids = [skill["id"] for skill in data["skills"]]
        assert "create_plan" in skill_ids


class TestBuildAgentEndpoints:
    """Tests specific to Build Agent endpoints."""

    @pytest.fixture
    def client(self):
        """Client for build agent."""
        return TestClient(BuildAgent().app)

    def test_agent_card_name(self, client):
        """Test that build agent has correct name."""
        response = client.get("/agent-card")
        data = response.json()
        assert data["name"] == "build-agent"

    def test_agent_card_url(self, client):
        """Test that build agent has correct URL."""
        response = client.get("/agent-card")
        data = response.json()
        assert "8002" in data["url"]

    def test_generate_code_skill_exists(self, client):
        """Test that generate_code skill is in agent card."""
        response = client.get("/agent-card")
        data = response.json()

        skill_ids = [skill["id"] for skill in data["skills"]]
        assert "generate_code" in skill_ids


class TestTestAgentEndpoints:
    """Tests specific to Test Agent endpoints."""

    @pytest.fixture
    def client(self):
        """Client for test agent."""
        return TestClient(TestAgent().app)

    def test_agent_card_name(self, client):
        """Test that test agent has correct name."""
        response = client.get("/agent-card")
        data = response.json()
        assert data["name"] == "test-agent"

    def test_agent_card_url(self, client):
        """Test that test agent has correct URL."""
        response = client.get("/agent-card")
        data = response.json()
        assert "8003" in data["url"]

    def test_review_code_skill_exists(self, client):
        """Test that review_code skill is in agent card."""
        response = client.get("/agent-card")
        data = response.json()

        skill_ids = [skill["id"] for skill in data["skills"]]
        assert "review_code" in skill_ids
