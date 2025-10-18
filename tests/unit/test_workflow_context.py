"""
Unit tests for WorkflowContext.

Tests context initialization, step output management, and template
expression resolution including workflow.input and steps.X.outputs paths.
"""

import pytest
from src.workflow_engine import WorkflowContext


class TestWorkflowContext:
    """Test WorkflowContext class."""

    def test_initialization(self):
        """Test context initialization with initial input."""
        ctx = WorkflowContext({"key": "value"})
        assert ctx.workflow_input == {"key": "value"}
        assert ctx.step_outputs == {}

    def test_initialization_with_empty_input(self):
        """Test context initialization with empty input."""
        ctx = WorkflowContext({})
        assert ctx.workflow_input == {}
        assert ctx.step_outputs == {}

    def test_initialization_with_complex_input(self):
        """Test context initialization with nested input structure."""
        input_data = {
            "simple": "value",
            "nested": {"key": "nested_value"},
            "list": [1, 2, 3],
        }
        ctx = WorkflowContext(input_data)
        assert ctx.workflow_input == input_data
        assert ctx.workflow_input["nested"]["key"] == "nested_value"

    def test_set_and_retrieve_step_output(self):
        """Test setting and retrieving step output."""
        ctx = WorkflowContext({})
        ctx.set_step_output("step1", {"result": "data"})
        assert "step1" in ctx.step_outputs
        assert ctx.step_outputs["step1"]["outputs"]["result"] == "data"

    def test_set_multiple_step_outputs(self):
        """Test setting multiple step outputs."""
        ctx = WorkflowContext({})
        ctx.set_step_output("step1", {"result1": "data1"})
        ctx.set_step_output("step2", {"result2": "data2"})
        assert len(ctx.step_outputs) == 2
        assert ctx.step_outputs["step1"]["outputs"]["result1"] == "data1"
        assert ctx.step_outputs["step2"]["outputs"]["result2"] == "data2"

    def test_overwrite_step_output(self):
        """Test overwriting existing step output."""
        ctx = WorkflowContext({})
        ctx.set_step_output("step1", {"result": "old_data"})
        ctx.set_step_output("step1", {"result": "new_data"})
        assert ctx.step_outputs["step1"]["outputs"]["result"] == "new_data"

    def test_set_step_output_with_complex_data(self):
        """Test setting step output with nested data structures."""
        ctx = WorkflowContext({})
        complex_output = {
            "simple": "value",
            "nested": {"key": "nested_value"},
            "list": [1, 2, 3],
            "deep": {"level1": {"level2": {"level3": "deep_value"}}},
        }
        ctx.set_step_output("step1", complex_output)
        assert (
            ctx.step_outputs["step1"]["outputs"]["deep"]["level1"]["level2"]["level3"]
            == "deep_value"
        )  # noqa: E501


class TestResolveExpression:
    """Test resolve_expression method."""

    def test_resolve_workflow_input_expression(self):
        """Test resolving workflow.input expressions."""
        ctx = WorkflowContext({"requirements": "test"})
        result = ctx.resolve_expression("{{ workflow.input.requirements }}")
        assert result == "test"

    def test_resolve_workflow_input_nested(self):
        """Test resolving nested workflow.input expressions."""
        ctx = WorkflowContext(
            {"user": {"name": "John", "email": "john@example.com"}}
        )  # noqa: E501
        result = ctx.resolve_expression("{{ workflow.input.user.name }}")
        assert result == "John"

    def test_resolve_step_output_expression(self):
        """Test resolving steps.X.outputs expressions."""
        ctx = WorkflowContext({})
        ctx.set_step_output("plan", {"plan_data": "structured plan"})
        result = ctx.resolve_expression("{{ steps.plan.outputs.plan_data }}")
        assert result == "structured plan"

    def test_resolve_step_output_nested(self):
        """Test resolving nested steps.X.outputs expressions."""
        ctx = WorkflowContext({})
        ctx.set_step_output("step1", {"result": {"nested": {"value": "deep_data"}}})
        result = ctx.resolve_expression(
            "{{ steps.step1.outputs.result.nested.value }}"
        )  # noqa: E501
        assert result == "deep_data"

    def test_resolve_nested_path_3_levels(self):
        """Test resolving 3+ level nested paths."""
        ctx = WorkflowContext({"nested": {"deep": {"value": 42}}})
        result = ctx.resolve_expression(
            "{{ workflow.input.nested.deep.value }}"
        )  # noqa: E501
        assert result == 42

    def test_resolve_nested_path_4_levels(self):
        """Test resolving 4 level nested paths."""
        ctx = WorkflowContext({})
        ctx.set_step_output(
            "step1", {"level1": {"level2": {"level3": {"level4": "value"}}}}
        )
        result = ctx.resolve_expression(
            "{{ steps.step1.outputs.level1.level2.level3.level4 }}"
        )  # noqa: E501
        assert result == "value"

    def test_resolve_missing_workflow_input_key(self):
        """Test that missing workflow.input key returns None."""
        ctx = WorkflowContext({})
        result = ctx.resolve_expression("{{ workflow.input.missing }}")
        assert result is None

    def test_resolve_missing_step_id(self):
        """Test that missing step ID returns None."""
        ctx = WorkflowContext({})
        result = ctx.resolve_expression("{{ steps.missing_step.outputs.data }}")
        assert result is None

    def test_resolve_missing_output_key(self):
        """Test that missing output key returns None."""
        ctx = WorkflowContext({})
        ctx.set_step_output("step1", {"result": "data"})
        result = ctx.resolve_expression(
            "{{ steps.step1.outputs.missing_key }}"
        )  # noqa: E501
        assert result is None

    def test_resolve_missing_nested_key(self):
        """Test that missing nested key returns None."""
        ctx = WorkflowContext({"data": {"key": "value"}})
        result = ctx.resolve_expression(
            "{{ workflow.input.data.missing.nested }}"
        )  # noqa: E501
        assert result is None

    def test_non_template_string_passes_through(self):
        """Test that non-template strings pass through unchanged."""
        ctx = WorkflowContext({})
        result = ctx.resolve_expression("plain string")
        assert result == "plain string"

    def test_string_with_partial_template_syntax(self):
        """Test that string with partial template syntax passes through."""
        ctx = WorkflowContext({})
        result = ctx.resolve_expression("text {{ incomplete")
        assert result == "text {{ incomplete"

    def test_string_with_no_spaces_in_template(self):
        """Test resolving template without spaces around expression."""
        ctx = WorkflowContext({"key": "value"})
        result = ctx.resolve_expression("{{workflow.input.key}}")
        assert result == "value"

    def test_string_with_extra_spaces_in_template(self):
        """Test resolving template with extra spaces."""
        ctx = WorkflowContext({"key": "value"})
        result = ctx.resolve_expression("{{   workflow.input.key   }}")
        assert result == "value"

    def test_non_string_input_passes_through(self):
        """Test that non-string inputs pass through unchanged."""
        ctx = WorkflowContext({})
        assert ctx.resolve_expression(42) == 42
        assert ctx.resolve_expression(3.14) == 3.14
        assert ctx.resolve_expression(True) is True
        assert ctx.resolve_expression(None) is None
        assert ctx.resolve_expression([1, 2, 3]) == [1, 2, 3]

    def test_invalid_expression_path_returns_none(self):
        """Test that invalid expression paths return None."""
        ctx = WorkflowContext({"key": "value"})
        result = ctx.resolve_expression("{{ invalid.path }}")
        assert result is None

    def test_empty_template_returns_none(self):
        """Test that empty template returns None."""
        ctx = WorkflowContext({})
        result = ctx.resolve_expression("{{  }}")
        assert result is None


class TestResolveInputs:
    """Test resolve_inputs method."""

    def test_resolve_inputs_mixed_content(self):
        """Test resolving inputs with mixed literal and template values."""
        ctx = WorkflowContext({"req": "test requirement"})
        ctx.set_step_output("step1", {"data": "output"})

        inputs = {
            "literal": "plain value",
            "from_workflow": "{{ workflow.input.req }}",
            "from_step": "{{ steps.step1.outputs.data }}",
            "number": 42,
        }

        resolved = ctx.resolve_inputs(inputs)
        assert resolved["literal"] == "plain value"
        assert resolved["from_workflow"] == "test requirement"
        assert resolved["from_step"] == "output"
        assert resolved["number"] == 42

    def test_resolve_inputs_with_nested_dict(self):
        """Test resolving inputs with nested dictionary structures."""
        ctx = WorkflowContext({"value": "test"})

        inputs = {
            "nested": {
                "level1": "{{ workflow.input.value }}",
                "level2": {"key": "literal"},
            }
        }

        resolved = ctx.resolve_inputs(inputs)
        assert resolved["nested"]["level1"] == "test"
        assert resolved["nested"]["level2"]["key"] == "literal"

    def test_resolve_inputs_with_list(self):
        """Test resolving inputs with list values."""
        ctx = WorkflowContext({"item": "value"})

        inputs = {"list": ["{{ workflow.input.item }}", "literal", 42]}

        resolved = ctx.resolve_inputs(inputs)
        assert resolved["list"][0] == "value"
        assert resolved["list"][1] == "literal"
        assert resolved["list"][2] == 42

    def test_resolve_inputs_empty_dict(self):
        """Test resolving empty inputs dict."""
        ctx = WorkflowContext({})
        resolved = ctx.resolve_inputs({})
        assert resolved == {}

    def test_resolve_inputs_deeply_nested(self):
        """Test resolving deeply nested input structures."""
        ctx = WorkflowContext({"val": "test"})
        ctx.set_step_output("step1", {"result": "data"})

        inputs = {
            "level1": {
                "level2": {
                    "level3": {
                        "from_workflow": "{{ workflow.input.val }}",
                        "from_step": "{{ steps.step1.outputs.result }}",
                    }
                }
            }
        }

        resolved = ctx.resolve_inputs(inputs)
        assert (
            resolved["level1"]["level2"]["level3"]["from_workflow"] == "test"
        )  # noqa: E501
        assert resolved["level1"]["level2"]["level3"]["from_step"] == "data"

    def test_resolve_inputs_with_all_types(self):
        """Test resolving inputs with various data types."""
        ctx = WorkflowContext({"str_val": "string"})

        inputs = {
            "string": "{{ workflow.input.str_val }}",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"key": "value"},
        }

        resolved = ctx.resolve_inputs(inputs)
        assert resolved["string"] == "string"
        assert resolved["int"] == 42
        assert resolved["float"] == 3.14
        assert resolved["bool"] is True
        assert resolved["none"] is None
        assert resolved["list"] == [1, 2, 3]
        assert resolved["dict"] == {"key": "value"}

    def test_resolve_inputs_with_missing_values(self):
        """Test resolving inputs when template values are missing."""
        ctx = WorkflowContext({})

        inputs = {
            "missing_workflow": "{{ workflow.input.missing }}",
            "missing_step": "{{ steps.missing.outputs.data }}",
            "literal": "value",
        }

        resolved = ctx.resolve_inputs(inputs)
        assert resolved["missing_workflow"] is None
        assert resolved["missing_step"] is None
        assert resolved["literal"] == "value"

    def test_resolve_inputs_preserves_structure(self):
        """Test that resolve_inputs preserves the original structure."""
        ctx = WorkflowContext({"a": "1", "b": "2"})

        inputs = {
            "key1": "{{ workflow.input.a }}",
            "key2": {
                "nested1": "{{ workflow.input.b }}",
                "nested2": ["{{ workflow.input.a }}", "literal"],
            },
            "key3": 123,
        }

        resolved = ctx.resolve_inputs(inputs)
        assert "key1" in resolved
        assert "key2" in resolved
        assert "nested1" in resolved["key2"]
        assert "nested2" in resolved["key2"]
        assert "key3" in resolved
        assert isinstance(resolved["key2"], dict)
        assert isinstance(resolved["key2"]["nested2"], list)

    def test_resolve_inputs_with_list_of_dicts(self):
        """Test resolving list of dictionaries."""
        ctx = WorkflowContext({"val": "test"})

        inputs = {
            "items": [
                {"name": "{{ workflow.input.val }}", "id": 1},
                {"name": "literal", "id": 2},
            ]
        }

        resolved = ctx.resolve_inputs(inputs)
        # Lists are resolved element by element, but dicts in lists
        # are not recursively resolved by the current implementation
        # This test documents current behavior
        assert resolved["items"][0]["name"] == "{{ workflow.input.val }}"
        assert resolved["items"][1]["name"] == "literal"
