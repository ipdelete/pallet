"""Tests for discovery module."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.discovery import (
    RegistryDiscovery,
    AgentInfo,
    SkillInfo,
    discover_agent,
    discover_agents,
    list_skills
)
from tests.fixtures.sample_data import (
    REGISTRY_CATALOG,
    PLAN_AGENT_CARD,
    BUILD_AGENT_CARD,
    TEST_AGENT_CARD
)


@pytest.fixture
def registry_discovery():
    """Create a RegistryDiscovery instance."""
    return RegistryDiscovery(registry_url="http://localhost:5000")


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for HTTP requests."""
    mock_client = MagicMock()
    return mock_client


class TestAgentInfo:
    """Tests for AgentInfo dataclass."""

    def test_agent_info_creation(self):
        """Test creating an AgentInfo instance."""
        info = AgentInfo(
            name="test-agent",
            url="http://localhost:8001",
            skills=[{"id": "test_skill"}],
            tag="v1"
        )
        assert info.name == "test-agent"
        assert info.url == "http://localhost:8001"
        assert len(info.skills) == 1
        assert info.tag == "v1"


class TestSkillInfo:
    """Tests for SkillInfo dataclass."""

    def test_skill_info_creation(self):
        """Test creating a SkillInfo instance."""
        info = SkillInfo(
            id="test_skill",
            description="A test skill",
            agent_name="test-agent",
            agent_url="http://localhost:8001"
        )
        assert info.id == "test_skill"
        assert info.description == "A test skill"
        assert info.agent_name == "test-agent"


class TestRegistryDiscoveryInit:
    """Tests for RegistryDiscovery initialization."""

    def test_init_with_default_url(self):
        """Test initialization with default registry URL."""
        discovery = RegistryDiscovery()
        assert discovery.registry_url == "http://localhost:5000"
        assert discovery._agents_cache is None

    def test_init_with_custom_url(self):
        """Test initialization with custom registry URL."""
        discovery = RegistryDiscovery(registry_url="http://custom:9000")
        assert discovery.registry_url == "http://custom:9000"


class TestListRepositories:
    """Tests for list_repositories method."""

    def test_list_repositories_success(self, registry_discovery):
        """Test successful repository listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = REGISTRY_CATALOG
        mock_response.raise_for_status = Mock()

        with patch.object(registry_discovery.client, 'get', return_value=mock_response):
            repos = registry_discovery.list_repositories()

            assert len(repos) == 3
            assert "agents/plan" in repos
            assert "agents/build" in repos
            assert "agents/test" in repos

    def test_list_repositories_failure(self, registry_discovery):
        """Test repository listing failure."""
        with patch.object(registry_discovery.client, 'get', side_effect=Exception("Connection error")):
            repos = registry_discovery.list_repositories()

            assert repos == []


class TestListTags:
    """Tests for list_tags method."""

    def test_list_tags_success(self, registry_discovery):
        """Test successful tag listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tags": ["v1", "v2", "latest"]}
        mock_response.raise_for_status = Mock()

        with patch.object(registry_discovery.client, 'get', return_value=mock_response):
            tags = registry_discovery.list_tags("agents/plan")

            assert len(tags) == 3
            assert "v1" in tags
            assert "latest" in tags

    def test_list_tags_failure(self, registry_discovery):
        """Test tag listing failure."""
        with patch.object(registry_discovery.client, 'get', side_effect=Exception("Connection error")):
            tags = registry_discovery.list_tags("agents/plan")

            assert tags == []


class TestGetAgentCard:
    """Tests for get_agent_card method."""

    def test_get_agent_card_success(self, registry_discovery, tmp_path):
        """Test successful agent card retrieval."""
        # Create a temporary agent card file
        card_file = tmp_path / "plan_agent_card.json"
        card_file.write_text(json.dumps(PLAN_AGENT_CARD))

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            with patch('os.path.exists', return_value=True):
                with patch('builtins.open', create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(PLAN_AGENT_CARD)
                    with patch('json.load', return_value=PLAN_AGENT_CARD):
                        card = registry_discovery.get_agent_card("plan")

                        assert card is not None
                        assert card["name"] == "plan-agent"
                        assert len(card["skills"]) == 1

    def test_get_agent_card_oras_failure(self, registry_discovery):
        """Test agent card retrieval with ORAS failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "ORAS pull failed"

        with patch('subprocess.run', return_value=mock_result):
            card = registry_discovery.get_agent_card("plan")

            assert card is None

    def test_get_agent_card_file_not_found(self, registry_discovery):
        """Test agent card retrieval when file doesn't exist."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result):
            with patch('os.path.exists', return_value=False):
                card = registry_discovery.get_agent_card("plan")

                assert card is None


class TestDiscoverAllAgents:
    """Tests for discover_all_agents method."""

    def test_discover_all_agents_success(self, registry_discovery):
        """Test successful discovery of all agents."""
        with patch.object(registry_discovery, 'list_repositories', return_value=["agents/plan", "agents/build"]):
            with patch.object(registry_discovery, 'list_tags', return_value=["v1"]):
                with patch.object(registry_discovery, 'get_agent_card', side_effect=[PLAN_AGENT_CARD, BUILD_AGENT_CARD]):
                    agents = registry_discovery.discover_all_agents()

                    assert len(agents) == 2
                    assert "plan" in agents
                    assert "build" in agents
                    assert agents["plan"].name == "plan-agent"
                    assert agents["build"].url == "http://localhost:8002"

    def test_discover_all_agents_uses_cache(self, registry_discovery):
        """Test that discover_all_agents uses cache."""
        # First call
        with patch.object(registry_discovery, 'list_repositories', return_value=["agents/plan"]) as mock_list:
            with patch.object(registry_discovery, 'get_agent_card', return_value=PLAN_AGENT_CARD):
                agents1 = registry_discovery.discover_all_agents()

                # Second call should use cache
                agents2 = registry_discovery.discover_all_agents()

                # list_repositories should only be called once
                assert mock_list.call_count == 1
                assert agents1 == agents2

    def test_discover_all_agents_skips_non_agent_repos(self, registry_discovery):
        """Test that non-agent repositories are skipped."""
        with patch.object(registry_discovery, 'list_repositories', return_value=["other/repo", "agents/plan"]):
            with patch.object(registry_discovery, 'list_tags', return_value=["v1"]):
                with patch.object(registry_discovery, 'get_agent_card', return_value=PLAN_AGENT_CARD):
                    agents = registry_discovery.discover_all_agents()

                    # Should only have plan agent, not "other/repo"
                    assert len(agents) == 1
                    assert "plan" in agents


class TestFindAgentBySkill:
    """Tests for find_agent_by_skill method."""

    def test_find_agent_by_skill_success(self, registry_discovery):
        """Test finding an agent by skill ID."""
        mock_agents = {
            "plan": AgentInfo(
                name="plan-agent",
                url="http://localhost:8001",
                skills=[{"id": "create_plan", "description": "Creates plans"}],
                tag="v1"
            )
        }

        with patch.object(registry_discovery, 'discover_all_agents', return_value=mock_agents):
            agent = registry_discovery.find_agent_by_skill("create_plan")

            assert agent is not None
            assert agent.name == "plan-agent"
            assert agent.url == "http://localhost:8001"

    def test_find_agent_by_skill_not_found(self, registry_discovery):
        """Test finding a non-existent skill."""
        mock_agents = {
            "plan": AgentInfo(
                name="plan-agent",
                url="http://localhost:8001",
                skills=[{"id": "create_plan"}],
                tag="v1"
            )
        }

        with patch.object(registry_discovery, 'discover_all_agents', return_value=mock_agents):
            agent = registry_discovery.find_agent_by_skill("nonexistent_skill")

            assert agent is None


class TestListAllSkills:
    """Tests for list_all_skills method."""

    def test_list_all_skills(self, registry_discovery):
        """Test listing all skills across agents."""
        mock_agents = {
            "plan": AgentInfo(
                name="plan-agent",
                url="http://localhost:8001",
                skills=[
                    {"id": "create_plan", "description": "Creates plans"}
                ],
                tag="v1"
            ),
            "build": AgentInfo(
                name="build-agent",
                url="http://localhost:8002",
                skills=[
                    {"id": "generate_code", "description": "Generates code"}
                ],
                tag="v1"
            )
        }

        with patch.object(registry_discovery, 'discover_all_agents', return_value=mock_agents):
            skills = registry_discovery.list_all_skills()

            assert len(skills) == 2
            assert skills[0].id == "create_plan"
            assert skills[1].id == "generate_code"
            assert skills[0].agent_name == "plan-agent"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_discover_agent_function(self):
        """Test discover_agent convenience function."""
        mock_agent = AgentInfo(
            name="plan-agent",
            url="http://localhost:8001",
            skills=[{"id": "create_plan"}],
            tag="v1"
        )

        with patch.object(RegistryDiscovery, 'find_agent_by_skill', return_value=mock_agent):
            with patch.object(RegistryDiscovery, 'close'):
                url = discover_agent("create_plan", "http://localhost:5000")

                assert url == "http://localhost:8001"

    def test_discover_agent_not_found(self):
        """Test discover_agent when skill not found."""
        with patch.object(RegistryDiscovery, 'find_agent_by_skill', return_value=None):
            with patch.object(RegistryDiscovery, 'close'):
                url = discover_agent("nonexistent", "http://localhost:5000")

                assert url is None

    def test_discover_agents_function(self):
        """Test discover_agents convenience function."""
        mock_agents = {
            "plan": AgentInfo(name="plan-agent", url="http://localhost:8001", skills=[], tag="v1")
        }

        with patch.object(RegistryDiscovery, 'discover_all_agents', return_value=mock_agents):
            with patch.object(RegistryDiscovery, 'close'):
                agents = discover_agents("http://localhost:5000")

                assert len(agents) == 1
                assert "plan" in agents

    def test_list_skills_function(self):
        """Test list_skills convenience function."""
        mock_skills = [
            SkillInfo(id="skill1", description="Skill 1", agent_name="agent1", agent_url="url1")
        ]

        with patch.object(RegistryDiscovery, 'list_all_skills', return_value=mock_skills):
            with patch.object(RegistryDiscovery, 'close'):
                skills = list_skills("http://localhost:5000")

                assert len(skills) == 1
                assert skills[0].id == "skill1"
