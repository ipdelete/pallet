"""
Unit tests for workflow data models.

Tests StepType, WorkflowStep, WorkflowMetadata, WorkflowDefinition,
and load_workflow_from_yaml functionality.
"""

import pytest
import tempfile
from pathlib import Path
from pydantic import ValidationError
from src.workflow_engine import (
    StepType,
    WorkflowStep,
    WorkflowMetadata,
    WorkflowDefinition,
    load_workflow_from_yaml,
)


class TestStepType:
    """Test StepType enum."""

    def test_valid_step_types(self):
        """Test all valid step type values."""
        assert StepType.SEQUENTIAL == "sequential"
        assert StepType.PARALLEL == "parallel"
        assert StepType.CONDITIONAL == "conditional"
        assert StepType.SWITCH == "switch"

    def test_step_type_is_string_enum(self):
        """Test that StepType values are strings."""
        assert isinstance(StepType.SEQUENTIAL.value, str)
        assert isinstance(StepType.PARALLEL.value, str)


class TestWorkflowStep:
    """Test WorkflowStep model."""

    def test_minimal_step(self):
        """Test creating a step with only required fields."""
        step = WorkflowStep(id="test", skill="test_skill")
        assert step.id == "test"
        assert step.skill == "test_skill"
        assert step.timeout == 300  # default
        assert step.step_type == StepType.SEQUENTIAL  # default
        assert step.inputs == {}  # default
        assert step.outputs is None
        assert step.condition is None
        assert step.branches is None

    def test_step_with_all_fields(self):
        """Test creating a step with all fields specified."""
        step = WorkflowStep(
            id="test",
            skill="test_skill",
            inputs={"key": "value"},
            outputs="result",
            timeout=600,
            step_type=StepType.PARALLEL,
            condition="x > 0",
            branches={"true": "step1", "false": "step2"},
        )
        assert step.id == "test"
        assert step.skill == "test_skill"
        assert step.inputs == {"key": "value"}
        assert step.outputs == "result"
        assert step.timeout == 600
        assert step.step_type == StepType.PARALLEL
        assert step.condition == "x > 0"
        assert step.branches == {"true": "step1", "false": "step2"}

    def test_missing_required_field_id(self):
        """Test that missing id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowStep(skill="test_skill")
        assert "id" in str(exc_info.value)

    def test_missing_required_field_skill(self):
        """Test that missing skill raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowStep(id="test")
        assert "skill" in str(exc_info.value)

    def test_invalid_step_type(self):
        """Test that invalid step_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowStep(id="test", skill="test_skill", step_type="invalid_type")
        assert "step_type" in str(exc_info.value).lower()

    def test_step_type_enum_assignment(self):
        """Test assigning StepType enum directly."""
        step = WorkflowStep(
            id="test", skill="test_skill", step_type=StepType.CONDITIONAL
        )
        assert step.step_type == StepType.CONDITIONAL

    def test_step_with_complex_inputs(self):
        """Test step with nested input structure."""
        step = WorkflowStep(
            id="test",
            skill="test_skill",
            inputs={
                "simple": "value",
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "template": "{{ workflow.input.data }}",
            },
        )
        assert step.inputs["simple"] == "value"
        assert step.inputs["nested"]["key"] == "value"
        assert step.inputs["list"] == [1, 2, 3]
        assert step.inputs["template"] == "{{ workflow.input.data }}"


class TestWorkflowMetadata:
    """Test WorkflowMetadata model."""

    def test_minimal_metadata(self):
        """Test creating metadata with only required fields."""
        metadata = WorkflowMetadata(
            id="test-workflow", name="Test Workflow", version="1.0.0"
        )
        assert metadata.id == "test-workflow"
        assert metadata.name == "Test Workflow"
        assert metadata.version == "1.0.0"
        assert metadata.description == ""  # default
        assert metadata.tags == []  # default

    def test_metadata_with_all_fields(self):
        """Test creating metadata with all fields."""
        metadata = WorkflowMetadata(
            id="test-workflow",
            name="Test Workflow",
            version="1.0.0",
            description="A test workflow",
            tags=["test", "example"],
        )
        assert metadata.id == "test-workflow"
        assert metadata.name == "Test Workflow"
        assert metadata.version == "1.0.0"
        assert metadata.description == "A test workflow"
        assert metadata.tags == ["test", "example"]

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            WorkflowMetadata(name="Test", version="1.0.0")  # missing id

        with pytest.raises(ValidationError):
            WorkflowMetadata(id="test", version="1.0.0")  # missing name

        with pytest.raises(ValidationError):
            WorkflowMetadata(id="test", name="Test")  # missing version


class TestWorkflowDefinition:
    """Test WorkflowDefinition model."""

    def test_valid_workflow(self):
        """Test creating a valid workflow definition."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test-workflow", name="Test", version="1.0.0"),
            steps=[WorkflowStep(id="step1", skill="skill1")],
        )
        assert workflow.metadata.id == "test-workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].id == "step1"
        assert workflow.error_handling is None  # default

    def test_workflow_with_multiple_steps(self):
        """Test workflow with multiple steps."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test-workflow", name="Test", version="1.0.0"),
            steps=[
                WorkflowStep(id="step1", skill="skill1"),
                WorkflowStep(id="step2", skill="skill2"),
                WorkflowStep(id="step3", skill="skill3"),
            ],
        )
        assert len(workflow.steps) == 3
        assert workflow.steps[0].id == "step1"
        assert workflow.steps[1].id == "step2"
        assert workflow.steps[2].id == "step3"

    def test_workflow_with_error_handling(self):
        """Test workflow with error handling configuration."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test-workflow", name="Test", version="1.0.0"),
            steps=[WorkflowStep(id="step1", skill="skill1")],
            error_handling={"retry_count": 3, "timeout": 600, "on_error": "rollback"},
        )
        assert workflow.error_handling is not None
        assert workflow.error_handling["retry_count"] == 3
        assert workflow.error_handling["on_error"] == "rollback"

    def test_missing_metadata(self):
        """Test that missing metadata raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowDefinition(steps=[WorkflowStep(id="step1", skill="skill1")])
        assert "metadata" in str(exc_info.value)

    def test_missing_steps(self):
        """Test that missing steps raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            WorkflowDefinition(
                metadata=WorkflowMetadata(id="test", name="Test", version="1.0.0")
            )
        assert "steps" in str(exc_info.value)

    def test_empty_steps_list(self):
        """Test that workflow can be created with empty steps list."""
        workflow = WorkflowDefinition(
            metadata=WorkflowMetadata(id="test-workflow", name="Test", version="1.0.0"),
            steps=[],
        )
        assert len(workflow.steps) == 0


class TestLoadWorkflowFromYAML:
    """Test load_workflow_from_yaml function."""

    def test_load_from_yaml_string(self):
        """Test loading workflow from YAML string."""
        yaml_str = """
metadata:
  id: test
  name: Test Workflow
  version: 1.0.0
steps:
  - id: step1
    skill: test_skill
"""
        workflow = load_workflow_from_yaml(yaml_str)
        assert workflow.metadata.id == "test"
        assert workflow.metadata.name == "Test Workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].id == "step1"

    def test_load_from_yaml_string_with_all_fields(self):
        """Test loading workflow with all fields from YAML string."""
        yaml_str = """
metadata:
  id: test-workflow-v1
  name: Test Workflow
  version: 1.0.0
  description: A test workflow
  tags:
    - test
    - example
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
error_handling:
  retry_count: 3
"""
        workflow = load_workflow_from_yaml(yaml_str)
        assert workflow.metadata.id == "test-workflow-v1"
        assert workflow.metadata.description == "A test workflow"
        assert workflow.metadata.tags == ["test", "example"]
        assert len(workflow.steps) == 2
        assert workflow.steps[0].timeout == 300
        assert workflow.steps[1].timeout == 600
        assert workflow.error_handling["retry_count"] == 3

    def test_load_from_yaml_file(self):
        """Test loading workflow from YAML file."""
        yaml_content = """
metadata:
  id: file-workflow
  name: File Workflow
  version: 1.0.0
steps:
  - id: step1
    skill: test_skill
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            workflow = load_workflow_from_yaml(temp_path)
            assert workflow.metadata.id == "file-workflow"
            assert workflow.metadata.name == "File Workflow"
        finally:
            Path(temp_path).unlink()

    def test_load_from_yaml_file_path_object(self):
        """Test loading workflow from Path object."""
        yaml_content = """
metadata:
  id: path-workflow
  name: Path Workflow
  version: 1.0.0
steps:
  - id: step1
    skill: test_skill
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            workflow = load_workflow_from_yaml(temp_path)
            assert workflow.metadata.id == "path-workflow"
        finally:
            temp_path.unlink()

    def test_malformed_yaml_raises_yaml_error(self):
        """Test that malformed YAML raises yaml.YAMLError."""
        malformed_yaml = """
metadata:
  id: test
  name: Test
  - invalid yaml structure
"""
        with pytest.raises(Exception):  # yaml.YAMLError or similar
            load_workflow_from_yaml(malformed_yaml)

    def test_invalid_structure_raises_validation_error(self):
        """Test that invalid workflow structure raises ValidationError."""
        invalid_yaml = """
metadata:
  id: test
  # missing name and version
steps:
  - id: step1
    skill: test_skill
"""
        with pytest.raises(ValidationError):
            load_workflow_from_yaml(invalid_yaml)

    def test_missing_metadata_raises_validation_error(self):
        """Test that missing metadata raises ValidationError."""
        invalid_yaml = """
steps:
  - id: step1
    skill: test_skill
"""
        with pytest.raises(ValidationError):
            load_workflow_from_yaml(invalid_yaml)

    def test_missing_steps_raises_validation_error(self):
        """Test that missing steps raises ValidationError."""
        invalid_yaml = """
metadata:
  id: test
  name: Test
  version: 1.0.0
"""
        with pytest.raises(ValidationError):
            load_workflow_from_yaml(invalid_yaml)

    def test_load_workflow_with_step_types(self):
        """Test loading workflow with different step types."""
        yaml_str = """
metadata:
  id: test
  name: Test
  version: 1.0.0
steps:
  - id: step1
    skill: skill1
    step_type: sequential
  - id: step2
    skill: skill2
    step_type: parallel
  - id: step3
    skill: skill3
    step_type: conditional
    condition: "result > 0"
"""
        workflow = load_workflow_from_yaml(yaml_str)
        assert workflow.steps[0].step_type == StepType.SEQUENTIAL
        assert workflow.steps[1].step_type == StepType.PARALLEL
        assert workflow.steps[2].step_type == StepType.CONDITIONAL
        assert workflow.steps[2].condition == "result > 0"
