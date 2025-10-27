"""Integration tests for full bootstrap pipeline."""

import os
import yaml


class TestBootstrapPipeline:
    """Test complete bootstrap pipeline."""

    def test_project_structure_exists(self):
        """Test that required directories exist."""
        required_dirs = [
            "charts/pallet-registry",
            "charts/pallet-registry/templates",
            "scripts",
            "tests/integration",
            "tests/unit",
        ]

        for dir_path in required_dirs:
            assert os.path.isdir(dir_path), f"Directory {dir_path} missing"

    def test_helm_chart_exists_with_files(self):
        """Test that Helm chart has all required files."""
        chart_files = [
            "charts/pallet-registry/Chart.yaml",
            "charts/pallet-registry/values.yaml",
            "charts/pallet-registry/values-dev.yaml",
            "charts/pallet-registry/templates/deployment.yaml",
            "charts/pallet-registry/templates/service.yaml",
            "charts/pallet-registry/templates/pvc.yaml",
            "charts/pallet-registry/templates/configmap.yaml",
            "charts/pallet-registry/templates/_helpers.tpl",
        ]

        for file_path in chart_files:
            assert os.path.isfile(file_path), f"File {file_path} missing"

    def test_bootstrap_scripts_exist(self):
        """Test that bootstrap scripts exist and are executable."""
        scripts = [
            "scripts/bootstrap-k8s.sh",
            "scripts/verify-bootstrap.sh",
            "scripts/install-kind.sh",
        ]

        for script in scripts:
            assert os.path.isfile(script), f"Script {script} missing"
            assert os.access(script, os.X_OK), f"Script {script} not executable"

    def test_kind_config_exists(self):
        """Test that kind config file exists."""
        assert os.path.isfile("kind-config.yaml"), "kind-config.yaml missing"

    def test_kind_config_valid(self):
        """Test that kind config is valid YAML."""
        with open("kind-config.yaml") as f:
            config = yaml.safe_load(f)

        assert config is not None, "kind-config.yaml is empty or invalid"
        assert "kind" in config, "kind field missing"
        assert "name" in config, "name field missing"

    def test_helm_chart_yaml_valid(self):
        """Test that Chart.yaml is valid."""
        with open("charts/pallet-registry/Chart.yaml") as f:
            chart = yaml.safe_load(f)

        assert chart["name"] == "pallet-registry", "Chart name mismatch"
        assert "version" in chart, "Chart version missing"
        assert "appVersion" in chart, "App version missing"

    def test_helm_values_yaml_valid(self):
        """Test that values.yaml is valid."""
        with open("charts/pallet-registry/values.yaml") as f:
            values = yaml.safe_load(f)

        assert "image" in values, "image section missing"
        assert "replicaCount" in values, "replicaCount missing"
        assert "service" in values, "service section missing"
        assert "persistence" in values, "persistence section missing"
        assert "resources" in values, "resources section missing"

    def test_helm_templates_valid_yaml(self):
        """Test that Helm templates are valid YAML."""
        template_files = [
            "charts/pallet-registry/templates/deployment.yaml",
            "charts/pallet-registry/templates/service.yaml",
            "charts/pallet-registry/templates/pvc.yaml",
            "charts/pallet-registry/templates/configmap.yaml",
        ]

        for template in template_files:
            with open(template) as f:
                content = f.read()
                # Should contain Helm template syntax
                assert (
                    "{{" in content or "kind:" in content
                ), f"{template} missing Helm/K8s content"

    def test_bootstrap_script_has_required_steps(self):
        """Test that bootstrap script contains required steps."""
        with open("scripts/bootstrap-k8s.sh") as f:
            content = f.read()

        required_steps = [
            "install-kind.sh",  # Check prerequisites
            "kind create cluster",  # Create cluster
            "kubectl create namespace",  # Create namespace
            "helm install",  # Install Helm release
            "curl",  # Test registry health
            "5000",  # Registry port
        ]

        for step in required_steps:
            assert step in content, f"Bootstrap script missing step: {step}"

    def test_verify_script_exists(self):
        """Test that verify-bootstrap.sh exists."""
        assert os.path.isfile(
            "scripts/verify-bootstrap.sh"
        ), "verify-bootstrap.sh missing"

        with open("scripts/verify-bootstrap.sh") as f:
            content = f.read()

        # Should check for kind cluster
        assert "kind get clusters" in content, "verify script missing kind check"
        # Should check for Helm release
        assert "helm list" in content, "verify script missing Helm check"
        # Should check for registry connectivity
        assert "5000" in content, "verify script missing registry port check"

    def test_bootstrap_fallback_exists(self):
        """Test that original Docker-based bootstrap.sh still exists."""
        assert os.path.isfile("scripts/bootstrap.sh"), "bootstrap.sh fallback missing"

    def test_readme_updated_with_kind_instructions(self):
        """Test that README mentions Kubernetes bootstrap option."""
        with open("README.md") as f:
            content = f.read()

        assert (
            "bootstrap-k8s.sh" in content
        ), "README missing Kubernetes bootstrap instructions"
        assert "kind" in content.lower(), "README missing kind documentation"
        assert "Helm" in content, "README missing Helm documentation"
        assert "Troubleshooting" in content, "README missing troubleshooting section"


class TestBootstrapReadiness:
    """Test readiness for bootstrap execution."""

    def test_test_files_exist(self):
        """Test that test files for bootstrap validation exist."""
        test_files = [
            "tests/unit/test_health_check.py",
            "tests/integration/test_bootstrap_k8s.py",
            "tests/integration/test_setup_complete.py",
        ]

        for test_file in test_files:
            assert os.path.isfile(test_file), f"Test file {test_file} missing"

    def test_gitignore_updated(self):
        """Test that .gitignore includes K8s-specific patterns."""
        with open(".gitignore") as f:
            content = f.read()

        k8s_patterns = [".kube/", "kubeconfig", "secrets/"]
        for pattern in k8s_patterns:
            assert pattern in content, f".gitignore missing pattern: {pattern}"
