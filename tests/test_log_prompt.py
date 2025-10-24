"""Test for log_prompt.py hook script."""

import json
import subprocess
from pathlib import Path
import pytest
from datetime import datetime


@pytest.fixture
def temp_logs_dir(tmp_path, monkeypatch):
    """Temporarily override logs directory."""
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    # Change to temp directory so script writes there
    monkeypatch.chdir(tmp_path)
    return logs_dir


def test_log_prompt_creates_file(temp_logs_dir):
    """Test that log_prompt.py creates a timestamped log file."""
    # Prepare hook input
    hook_input = {
        "session_id": "test-session-123",
        "user_prompt": "This is a test prompt",
        "cwd": str(Path.cwd()),
        "hook_event_name": "UserPromptSubmit",
    }

    # Run the script
    script_path = Path(__file__).parent.parent / "scripts" / "log_prompt.py"
    result = subprocess.run(
        ["uv", "run", str(script_path)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
    )

    # Check success
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    # Find the created log file
    log_files = list(temp_logs_dir.glob("prompt_*.txt"))
    assert len(log_files) == 1, f"Expected 1 log file, found {len(log_files)}"

    # Verify content
    log_content = log_files[0].read_text()
    assert "Timestamp:" in log_content
    assert "Session: test-session-123" in log_content
    assert "This is a test prompt" in log_content


def test_log_prompt_filename_format(temp_logs_dir):
    """Test that log file has correct timestamp format."""
    hook_input = {
        "session_id": "test-session-456",
        "user_prompt": "Another test",
    }

    script_path = Path(__file__).parent.parent / "scripts" / "log_prompt.py"
    subprocess.run(
        ["uv", "run", str(script_path)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
    )

    # Check filename format: prompt_YYYYMMDD_HHMMSS.txt
    log_files = list(temp_logs_dir.glob("prompt_*.txt"))
    assert len(log_files) == 1

    filename = log_files[0].name
    assert filename.startswith("prompt_")
    assert filename.endswith(".txt")

    # Extract timestamp part
    timestamp_part = filename[7:-4]  # Remove "prompt_" and ".txt"
    assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS
    assert timestamp_part[8] == "_"

    # Verify it's a valid date format
    datetime.strptime(timestamp_part, "%Y%m%d_%H%M%S")


def test_log_prompt_handles_empty_prompt(temp_logs_dir):
    """Test that script handles empty prompt gracefully."""
    hook_input = {
        "session_id": "test-session-789",
        "user_prompt": "",
    }

    script_path = Path(__file__).parent.parent / "scripts" / "log_prompt.py"
    result = subprocess.run(
        ["uv", "run", str(script_path)],
        input=json.dumps(hook_input),
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    log_files = list(temp_logs_dir.glob("prompt_*.txt"))
    assert len(log_files) == 1

    log_content = log_files[0].read_text()
    assert "Session: test-session-789" in log_content
    assert "Prompt:\n\n" in log_content  # Empty prompt section
