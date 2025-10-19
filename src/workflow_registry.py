"""
Workflow registry operations using ORAS and OCI registry.

Workflows are stored in the registry under workflows/{workflow-id}:v{version}.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx

from src.logging_config import configure_module_logging

logger = configure_module_logging("workflow_registry")

REGISTRY_URL = "localhost:5000"
ORAS_VERBOSE = os.getenv("PALLET_ORAS_VERBOSE", "0") == "1"


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
    logger.info(f"Pushing workflow to registry: {workflow_id}:{version}")
    logger.debug(f"Workflow file: {workflow_file}")

    if not workflow_file.exists():
        logger.error(f"Workflow file not found: {workflow_file}")
        return False

    registry_path = f"{REGISTRY_URL}/workflows/{workflow_id}:{version}"
    logger.debug(f"Registry path: {registry_path}")

    try:
        cmd = ["oras", "push", registry_path, f"{workflow_file}:application/yaml"]
        logger.debug(f"Executing: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info(f"Successfully pushed workflow {workflow_id}:{version} to registry")
        if ORAS_VERBOSE and result.stdout:
            logger.debug(f"ORAS output: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to push workflow: {e.stderr}", exc_info=True)
        return False
    except FileNotFoundError:
        logger.error("ORAS not found. Install with: bash scripts/install-oras.sh")
        return False


def pull_workflow_from_registry(
    workflow_id: str, version: str = "v1", output_dir: Optional[Path] = None
) -> Optional[Path]:
    """
    Pull a workflow YAML file from the OCI registry.

    Args:
        workflow_id: Unique workflow identifier
            (may include version suffix like "code-generation-v1")
        version: Workflow version (default: v1)
        output_dir: Directory to save workflow (default: temp directory)

    Returns:
        Path to downloaded workflow file, or None if failed

    Example:
        workflow_path = pull_workflow_from_registry("code-generation", "v1")
        # Also works with version suffix:
        workflow_path = pull_workflow_from_registry("code-generation-v1", "v1")
    """
    logger.info(f"Pulling workflow from registry: {workflow_id}:{version}")
    logger.debug(f"Input workflow_id: {workflow_id}")

    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp())
    logger.debug(f"Output directory: {output_dir}")

    # Strip version suffix from workflow_id if present
    # (e.g., "code-generation-v1" -> "code-generation")
    # This handles the case where workflow metadata ID includes version info
    base_workflow_id = workflow_id
    if (
        workflow_id.endswith("-v1")
        or workflow_id.endswith("-v2")
        or workflow_id.endswith("-v3")
    ):
        # Extract base name by removing -vN suffix
        import re

        match = re.match(r"^(.+?)-v\d+$", workflow_id)
        if match:
            base_workflow_id = match.group(1)
            logger.debug(f"Stripped version suffix: {workflow_id} → {base_workflow_id}")

    registry_path = f"{REGISTRY_URL}/workflows/{base_workflow_id}:{version}"
    logger.debug(f"Registry path: {registry_path}")

    try:
        cmd = ["oras", "pull", registry_path, "-o", str(output_dir)]
        logger.debug(f"Executing: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        if ORAS_VERBOSE and result.stdout:
            logger.debug(f"ORAS output: {result.stdout}")

        # Find the YAML file in output directory (ORAS may create subdirectories)
        logger.debug("Searching for YAML files in output directory")
        yaml_files = list(output_dir.glob("*.yaml")) + list(output_dir.glob("*.yml"))

        if not yaml_files:
            logger.debug("No YAML files in root, searching subdirectories")
            # Look in subdirectories (ORAS may preserve directory structure)
            yaml_files = list(output_dir.glob("**/*.yaml")) + list(
                output_dir.glob("**/*.yml")
            )

        if yaml_files:
            selected_file = yaml_files[0]
            logger.info(f"Successfully pulled workflow {workflow_id}:{version}")
            logger.debug(f"Selected workflow file: {selected_file}")
            return selected_file
        else:
            found_files = list(output_dir.rglob("*"))
            logger.error("No YAML file found in pulled artifacts")
            logger.debug(f"Directory contents: {found_files}")
            return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to pull workflow: {e.stderr}", exc_info=True)
        return None
    except FileNotFoundError:
        logger.error("ORAS not found. Install with: bash scripts/install-oras.sh")
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

        yaml_content = Path(workflow_path).read_text()
        workflow = load_workflow_from_yaml(yaml_content)
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
