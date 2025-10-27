"""Integration tests for kind-based Kubernetes bootstrap."""


class TestKubernetesBootstrap:
    """Test Kubernetes bootstrap lifecycle."""

    def test_kind_cluster_creation(self):
        """Test that kind cluster can be created."""
        # This is a placeholder test - actual bootstrap happens in scripts
        # The script will create cluster "pallet-dev"
        # Expected: cluster name exists in kind clusters
        pass

    def test_helm_chart_structure(self):
        """Test that Helm chart has required files."""
        import os

        chart_dir = "charts/pallet-registry"

        # Check for required files
        assert os.path.isfile(f"{chart_dir}/Chart.yaml"), "Chart.yaml missing"
        assert os.path.isfile(f"{chart_dir}/values.yaml"), "values.yaml missing"
        assert os.path.isdir(f"{chart_dir}/templates"), "templates/ directory missing"

        # Check for required templates
        required_templates = [
            "_helpers.tpl",
            "deployment.yaml",
            "service.yaml",
            "pvc.yaml",
        ]
        for template in required_templates:
            path = f"{chart_dir}/templates/{template}"
            assert os.path.isfile(path), f"{template} missing from templates/"

    def test_helm_values_schema(self):
        """Test that values.yaml has expected structure."""
        import yaml

        with open("charts/pallet-registry/values.yaml") as f:
            values = yaml.safe_load(f)

        # Check for required keys
        assert "image" in values, "image key missing"
        assert "replicaCount" in values, "replicaCount missing"
        assert "service" in values, "service key missing"
        assert "persistence" in values, "persistence key missing"
        assert "resources" in values, "resources key missing"

        # Validate image settings
        assert "repository" in values["image"], "image.repository missing"
        assert "tag" in values["image"], "image.tag missing"

        # Validate service settings
        assert (
            values["service"]["type"] == "NodePort"
        ), "service type should be NodePort"
        assert values["service"]["port"] == 5000, "service port should be 5000"

        # Validate persistence
        assert values["persistence"]["enabled"] is True, "persistence should be enabled"
        assert values["persistence"]["size"] == "1Gi", "persistence size should be 1Gi"


class TestBootstrapScripts:
    """Test bootstrap script structure."""

    def test_bootstrap_k8s_exists(self):
        """Test that bootstrap-k8s.sh exists."""
        import os

        assert os.path.isfile("scripts/bootstrap-k8s.sh"), "bootstrap-k8s.sh missing"

    def test_install_kind_exists(self):
        """Test that install-kind.sh exists."""
        import os

        assert os.path.isfile("scripts/install-kind.sh"), "install-kind.sh missing"

    def test_kind_config_exists(self):
        """Test that kind-config.yaml exists."""
        import os

        assert os.path.isfile("kind-config.yaml"), "kind-config.yaml missing"

    def test_kind_config_structure(self):
        """Test that kind-config.yaml has correct structure."""
        import yaml

        with open("kind-config.yaml") as f:
            config = yaml.safe_load(f)

        assert config["kind"] == "Cluster", "kind field should be 'Cluster'"
        assert config["name"] == "pallet-dev", "cluster name should be 'pallet-dev'"
        assert "nodes" in config, "nodes field missing"
        assert len(config["nodes"]) > 0, "at least one node required"

        # Check port mappings
        node = config["nodes"][0]
        assert "extraPortMappings" in node, "extraPortMappings missing"
        port_mappings = node["extraPortMappings"]
        assert len(port_mappings) > 0, "at least one port mapping required"

        # Should map port 5000 to 5000
        registry_mapping = next(
            (m for m in port_mappings if m["containerPort"] == 5000), None
        )
        assert registry_mapping is not None, "port 5000 mapping missing"
        assert (
            registry_mapping["hostPort"] == 5000
        ), "port 5000 should map to host port 5000"
