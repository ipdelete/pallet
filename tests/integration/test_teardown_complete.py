"""Integration tests for complete teardown and cleanup."""

import os


class TestTeardownScripts:
    """Test teardown script functionality."""

    def test_kill_script_exists(self):
        """Test that kill script exists and is executable."""
        assert os.path.isfile("scripts/kill.sh"), "kill.sh missing"
        assert os.access("scripts/kill.sh", os.X_OK), "kill.sh not executable"

    def test_kill_script_has_help(self):
        """Test that kill script has help option."""
        with open("scripts/kill.sh") as f:
            content = f.read()

        assert "--help" in content, "kill.sh missing --help option"
        assert "show_help" in content, "kill.sh missing show_help function"

    def test_kill_script_supports_kind_flag(self):
        """Test that kill script supports --kind flag."""
        with open("scripts/kill.sh") as f:
            content = f.read()

        assert "--kind" in content, "kill.sh missing --kind flag"
        assert "kind delete cluster" in content, "kill.sh missing kind cluster deletion"

    def test_kill_script_supports_clean_logs_flag(self):
        """Test that kill script supports --clean-logs flag."""
        with open("scripts/kill.sh") as f:
            content = f.read()

        assert "--clean-logs" in content, "kill.sh missing --clean-logs flag"
        assert "CLEAN_LOGS" in content, "kill.sh missing CLEAN_LOGS variable"

    def test_kill_script_supports_clean_pvc_flag(self):
        """Test that kill script supports --clean-pvc flag."""
        with open("scripts/kill.sh") as f:
            content = f.read()

        assert "--clean-pvc" in content, "kill.sh missing --clean-pvc flag"
        assert "CLEAN_PVC" in content, "kill.sh missing CLEAN_PVC variable"

    def test_kill_script_has_cleanup_functions(self):
        """Test that kill script has required cleanup functions."""
        with open("scripts/kill.sh") as f:
            content = f.read()

        required_functions = [
            "kill_agents",
            "kill_kind_cluster",
            "kill_registry",
            "clear_app_folder",
            "clear_logs",
        ]

        for func in required_functions:
            assert f"{func}()" in content, f"kill.sh missing {func} function"

    def test_kill_script_has_error_handling(self):
        """Test that kill script has error handling."""
        with open("scripts/kill.sh") as f:
            content = f.read()

        assert (
            "set -e" in content or "trap" in content
        ), "kill.sh missing error handling"
        assert "log_error" in content, "kill.sh missing error logging"

    def test_readme_cleanup_documented(self):
        """Test that README documents teardown process."""
        with open("README.md") as f:
            content = f.read()

        assert "kill.sh" in content, "README missing kill.sh documentation"
        assert "--kind" in content, "README missing --kind flag documentation"
        assert "--clean-logs" in content, "README missing --clean-logs documentation"


class TestCleanupReadiness:
    """Test readiness for cleanup operations."""

    def test_app_directory_referenced(self):
        """Test that cleanup scripts reference app directory."""
        with open("scripts/kill.sh") as f:
            content = f.read()

        assert (
            "APP_DIR" in content or "app" in content
        ), "kill.sh missing app directory cleanup"

    def test_logs_directory_referenced(self):
        """Test that cleanup scripts reference logs directory."""
        with open("scripts/kill.sh") as f:
            content = f.read()

        assert "logs/" in content, "kill.sh missing logs/ directory cleanup"

    def test_docker_fallback_preserved(self):
        """Test that original Docker fallback is preserved."""
        assert os.path.isfile("scripts/bootstrap.sh"), "bootstrap.sh fallback missing"

        with open("scripts/kill.sh") as f:
            content = f.read()

        # Should mention both bootstrap options
        assert "bootstrap" in content, "kill.sh should reference bootstrap scripts"
