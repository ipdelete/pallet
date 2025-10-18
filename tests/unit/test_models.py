"""Tests for Pydantic models in base.py."""

import pytest
from pydantic import ValidationError

from src.agents.base import Message, SkillDefinition, AgentCard


class TestMessage:
    """Tests for Message model."""

    def test_message_creation(self):
        """Test creating a valid Message."""
        msg = Message(
            jsonrpc="2.0", method="test_method", params={"key": "value"}, id="123"
        )
        assert msg.jsonrpc == "2.0"
        assert msg.method == "test_method"
        assert msg.params == {"key": "value"}
        assert msg.id == "123"

    def test_message_default_jsonrpc(self):
        """Test that jsonrpc defaults to 2.0."""
        msg = Message(method="test", params={})
        assert msg.jsonrpc == "2.0"

    def test_message_optional_id(self):
        """Test that id is optional."""
        msg = Message(method="test", params={})
        assert msg.id is None

    def test_message_requires_method(self):
        """Test that method is required."""
        with pytest.raises(ValidationError):
            Message(params={})

    def test_message_requires_params(self):
        """Test that params is required."""
        with pytest.raises(ValidationError):
            Message(method="test")


class TestSkillDefinition:
    """Tests for SkillDefinition model."""

    def test_skill_definition_creation(self):
        """Test creating a valid SkillDefinition."""
        skill = SkillDefinition(
            id="test_skill",
            description="A test skill",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
        assert skill.id == "test_skill"
        assert skill.description == "A test skill"
        assert skill.input_schema == {"type": "object"}
        assert skill.output_schema == {"type": "object"}

    def test_skill_definition_minimal(self):
        """Test creating a SkillDefinition with minimal fields."""
        skill = SkillDefinition(id="skill", description="desc")
        assert skill.id == "skill"
        assert skill.description == "desc"
        assert skill.input_schema is None
        assert skill.output_schema is None

    def test_skill_definition_requires_id(self):
        """Test that id is required."""
        with pytest.raises(ValidationError):
            SkillDefinition(description="test")

    def test_skill_definition_requires_description(self):
        """Test that description is required."""
        with pytest.raises(ValidationError):
            SkillDefinition(id="test")


class TestAgentCard:
    """Tests for AgentCard model."""

    def test_agent_card_creation(self):
        """Test creating a valid AgentCard."""
        skill = SkillDefinition(id="skill1", description="Test skill")
        card = AgentCard(name="test-agent", url="http://localhost:8001", skills=[skill])
        assert card.name == "test-agent"
        assert card.url == "http://localhost:8001"
        assert len(card.skills) == 1
        assert card.skills[0].id == "skill1"

    def test_agent_card_empty_skills(self):
        """Test creating an AgentCard with empty skills."""
        card = AgentCard(name="test-agent", url="http://localhost:8001", skills=[])
        assert len(card.skills) == 0

    def test_agent_card_multiple_skills(self):
        """Test creating an AgentCard with multiple skills."""
        skills = [
            SkillDefinition(id="skill1", description="Skill 1"),
            SkillDefinition(id="skill2", description="Skill 2"),
            SkillDefinition(id="skill3", description="Skill 3"),
        ]
        card = AgentCard(
            name="multi-skill-agent", url="http://localhost:9000", skills=skills
        )
        assert len(card.skills) == 3
        assert card.skills[0].id == "skill1"
        assert card.skills[1].id == "skill2"
        assert card.skills[2].id == "skill3"

    def test_agent_card_requires_name(self):
        """Test that name is required."""
        with pytest.raises(ValidationError):
            AgentCard(url="http://localhost:8001", skills=[])

    def test_agent_card_requires_url(self):
        """Test that url is required."""
        with pytest.raises(ValidationError):
            AgentCard(name="test", skills=[])

    def test_agent_card_requires_skills(self):
        """Test that skills is required."""
        with pytest.raises(ValidationError):
            AgentCard(name="test", url="http://localhost:8001")
