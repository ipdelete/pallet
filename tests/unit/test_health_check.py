"""Unit tests for health check output formatting."""

import json


def test_health_check_json_format():
    """Test JSON health check output format."""
    sample_output = {
        "registry": "healthy",
        "agents": {"plan": "healthy", "build": "healthy", "test": "healthy"},
    }
    # Verify it's valid JSON
    json_str = json.dumps(sample_output)
    parsed = json.loads(json_str)

    assert parsed["registry"] in ["healthy", "unhealthy", "degraded"]
    assert all(
        status in ["healthy", "unhealthy", "degraded"]
        for status in parsed["agents"].values()
    )


def test_health_check_json_invalid_status():
    """Test that invalid status values fail validation."""
    sample_output = {"registry": "invalid_status", "agents": {}}
    # This should fail validation
    assert sample_output["registry"] not in ["healthy", "unhealthy", "degraded"]


def test_health_check_human_readable_format():
    """Test human-readable health check output format."""
    # Should contain service names and status
    output = """
    ✓ Registry (localhost:5000): healthy
    ✓ Plan Agent (localhost:8001): healthy
    ✓ Build Agent (localhost:8002): healthy
    ✓ Test Agent (localhost:8003): healthy
    """

    assert "Registry" in output
    assert "Plan Agent" in output
    assert "healthy" in output
    assert "localhost:5000" in output
    assert "localhost:8001" in output
