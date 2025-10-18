"""
Workflow registry operations using ORAS and OCI registry.

Workflows are stored in the registry under workflows/{workflow-id}:v{version}.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx


REGISTRY_URL = "localhost:5000"


def push_workflow_to_registry(
    workflow_file: Path, workflow_id: str, version: str = "v1"
) -> bool:
    """
    Push a workflow YAML file to the OCI registry.

    Args:
        workflow_file: Path to workflow YAML file
        workflow_id: Unique workflow identifier
        version: Workflow version (default: v1)

    Returns:
        True if successful, False otherwise

    Example:
        push_workflow_to_registry(
            Path("workflows/code-generation.yaml"),
            "code-generation",
            "v1"
        )
    """
    if not workflow_file.exists():
        print(f"Error: Workflow file not found: {workflow_file}")
        return False

    registry_path = f"{REGISTRY_URL}/workflows/{workflow_id}:{version}"

    try:
        subprocess.run(
            ["oras", "push", registry_path, f"{workflow_file}:application/yaml"],
            capture_output=True,
            text=True,
            check=True,
        )

        print(f"✓ Pushed workflow {workflow_id}:{version} to registry")
        return True

    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to push workflow: {e.stderr}")
        return False
    except FileNotFoundError:
        print("✗ ORAS not found. Install with: bash scripts/install-oras.sh")
        return False


def pull_workflow_from_registry(
    workflow_id: str, version: str = "v1", output_dir: Optional[Path] = None
) -> Optional[Path]:
    """
    Pull a workflow YAML file from the OCI registry.

    Args:
        workflow_id: Unique workflow identifier
        version: Workflow version (default: v1)
        output_dir: Directory to save workflow (default: temp directory)

    Returns:
        Path to downloaded workflow file, or None if failed

    Example:
        workflow_path = pull_workflow_from_registry("code-generation", "v1")
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp())

    registry_path = f"{REGISTRY_URL}/workflows/{workflow_id}:{version}"

    try:
        subprocess.run(
            ["oras", "pull", registry_path, "-o", str(output_dir)],
            capture_output=True,
            text=True,
            check=True,
        )

        # Find the YAML file in output directory
        yaml_files = list(output_dir.glob("*.yaml")) + list(output_dir.glob("*.yml"))
        if yaml_files:
            print(f"✓ Pulled workflow {workflow_id}:{version} from registry")
            return yaml_files[0]
        else:
            print("✗ No YAML file found in pulled artifacts")
            return None

    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to pull workflow: {e.stderr}")
        return None
    except FileNotFoundError:
        print("✗ ORAS not found. Install with: bash scripts/install-oras.sh")
        return None


def list_workflows() -> List[str]:
    """
    List all workflows in the registry.

    Returns:
        List of workflow repository names
        (e.g., ["workflows/code-generation", "workflows/smart-router"])

    Example:
        workflows = list_workflows()
        print(f"Found {len(workflows)} workflows")
    """
    try:
        # Query registry catalog
        response = httpx.get(f"http://{REGISTRY_URL}/v2/_catalog", timeout=5.0)
        response.raise_for_status()
        catalog = response.json()

        # Filter for workflows/* repositories
        repositories = catalog.get("repositories", [])
        workflow_repos = [
            repo for repo in repositories if repo.startswith("workflows/")
        ]

        return workflow_repos

    except httpx.RequestError as e:
        print(f"✗ Failed to query registry: {e}")
        return []
    except Exception as e:
        print(f"✗ Error listing workflows: {e}")
        return []


def get_workflow_metadata(
    workflow_id: str, version: str = "v1"
) -> Optional[Dict[str, Any]]:
    """
    Get workflow metadata without pulling the full file.

    Args:
        workflow_id: Unique workflow identifier
        version: Workflow version (default: v1)

    Returns:
        Workflow metadata dict, or None if failed

    Example:
        metadata = get_workflow_metadata("code-generation", "v1")
        print(metadata["name"], metadata["description"])
    """
    workflow_path = pull_workflow_from_registry(workflow_id, version)
    if not workflow_path:
        return None

    try:
        from src.workflow_engine import load_workflow_from_yaml

        workflow = load_workflow_from_yaml(workflow_path)
        return {
            "id": workflow.metadata.id,
            "name": workflow.metadata.name,
            "version": workflow.metadata.version,
            "description": workflow.metadata.description,
            "tags": workflow.metadata.tags,
            "steps": len(workflow.steps),
        }
    except Exception as e:
        print(f"✗ Failed to parse workflow metadata: {e}")
        return None
