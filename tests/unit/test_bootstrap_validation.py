"""Unit tests for bootstrap dependency validation."""

import os


class TestBootstrapDependencies:
    """Test bootstrap dependency checking."""

    def test_install_kind_script_exists(self):
        """Test that install-kind.sh exists and is executable."""
        assert os.path.isfile("scripts/install-kind.sh"), "install-kind.sh missing"
        assert os.access(
            "scripts/install-kind.sh", os.X_OK
        ), "install-kind.sh not executable"

    def test_install_kind_script_checks_prerequisites(self):
        """Test that install-kind.sh checks for required tools."""
        with open("scripts/install-kind.sh") as f:
            content = f.read()

        # Should check for required tools
        required_checks = ["kind", "helm", "kubectl", "docker"]
        for tool in required_checks:
            assert tool in content, f"install-kind.sh missing check for {tool}"

    def test_install_kind_script_validates_docker_daemon(self):
        """Test that install-kind.sh validates Docker daemon is running."""
        with open("scripts/install-kind.sh") as f:
            content = f.read()

        assert "docker ps" in content, "install-kind.sh should test Docker daemon"

    def test_kind_config_has_valid_port_mapping(self):
        """Test that kind-config.yaml has port 5000 mapping."""
        import yaml

        with open("kind-config.yaml") as f:
            config = yaml.safe_load(f)

        # Find port mapping for 5000
        nodes = config.get("nodes", [])
        assert len(nodes) > 0, "kind config should have at least one node"

        node = nodes[0]
        port_mappings = node.get("extraPortMappings", [])
        assert len(port_mappings) > 0, "node should have port mappings"

        # Find registry port mapping
        registry_mapping = next(
            (m for m in port_mappings if m.get("containerPort") == 5000), None
        )
        assert registry_mapping is not None, "port 5000 mapping missing"
        assert (
            registry_mapping.get("hostPort") == 5000
        ), "container port 5000 should map to host port 5000"

    def test_helm_chart_has_resource_limits(self):
        """Test that Helm chart specifies resource limits."""
        import yaml

        with open("charts/pallet-registry/values.yaml") as f:
            values = yaml.safe_load(f)

        resources = values.get("resources", {})
        assert "limits" in resources, "resources.limits missing"
        assert "requests" in resources, "resources.requests missing"

        # Check for reasonable limits
        limits = resources["limits"]
        assert "cpu" in limits, "CPU limit missing"
        assert "memory" in limits, "Memory limit missing"

    def test_helm_chart_has_health_probes(self):
        """Test that Helm chart specifies health probes."""
        import yaml

        with open("charts/pallet-registry/values.yaml") as f:
            values = yaml.safe_load(f)

        assert "livenessProbe" in values, "livenessProbe missing"
        assert "readinessProbe" in values, "readinessProbe missing"

        # Check probe configuration
        liveness = values["livenessProbe"]
        assert "httpGet" in liveness, "livenessProbe missing httpGet"
        assert (
            liveness["httpGet"]["path"] == "/v2/"
        ), "liveness probe path should be /v2/"

    def test_helm_chart_persistence_configured(self):
        """Test that Helm chart has persistence configuration."""
        import yaml

        with open("charts/pallet-registry/values.yaml") as f:
            values = yaml.safe_load(f)

        persistence = values.get("persistence", {})
        assert persistence.get("enabled") is True, "persistence should be enabled"
        assert "size" in persistence, "PVC size missing"
        assert "mountPath" in persistence, "mount path missing"


class TestBootstrapScriptValidation:
    """Test bootstrap script validation logic."""

    def test_bootstrap_k8s_validates_prerequisites(self):
        """Test that bootstrap-k8s.sh calls install-kind.sh."""
        with open("scripts/bootstrap-k8s.sh") as f:
            content = f.read()

        assert "install-kind.sh" in content, "bootstrap should call install-kind.sh"

    def test_bootstrap_k8s_creates_cluster(self):
        """Test that bootstrap-k8s.sh creates kind cluster."""
        with open("scripts/bootstrap-k8s.sh") as f:
            content = f.read()

        assert "kind create cluster" in content, "bootstrap should create kind cluster"
        assert "pallet-dev" in content, "cluster name should be pallet-dev"

    def test_bootstrap_k8s_creates_namespace(self):
        """Test that bootstrap-k8s.sh creates Kubernetes namespace."""
        with open("scripts/bootstrap-k8s.sh") as f:
            content = f.read()

        assert (
            "kubectl create namespace" in content
        ), "bootstrap should create namespace"
        assert "pallet" in content, "namespace should be named pallet"

    def test_bootstrap_k8s_installs_helm_release(self):
        """Test that bootstrap-k8s.sh installs Helm release."""
        with open("scripts/bootstrap-k8s.sh") as f:
            content = f.read()

        assert "helm install" in content, "bootstrap should install Helm release"
        assert "registry" in content, "release name should be registry"

    def test_bootstrap_k8s_verifies_health(self):
        """Test that bootstrap-k8s.sh verifies registry health."""
        with open("scripts/bootstrap-k8s.sh") as f:
            content = f.read()

        assert "5000" in content, "should test registry on port 5000"
        assert "curl" in content, "should use curl for health checks"

    def test_bootstrap_script_fallback_exists(self):
        """Test that Docker fallback bootstrap.sh is preserved."""
        with open("scripts/bootstrap.sh") as f:
            content = f.read()

        # Should have original Docker-based logic
        assert "docker" in content.lower(), "fallback should use Docker"
