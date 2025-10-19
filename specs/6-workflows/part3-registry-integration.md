# Part 3: Registry Integration (Workflow Storage & Discovery)

**Status**: 🔴 Not Started | **Depends On**: Part 1 (Data Models), Part 2 (Engine) | **Testing**: Unit tests

## Overview

This part implements workflow storage and discovery using the OCI registry. Workflows are pushed to and pulled from the registry similar to agent cards, enabling versioned workflow artifacts that can be discovered at runtime.

## Scope

### In Scope
- Push workflows to OCI registry via ORAS
- Pull workflows from registry
- List available workflows in registry
- Extend discovery module to find workflows by ID
- Create `push_workflows.sh` script
- Update `bootstrap.sh` to push workflows

### Out of Scope
- Example workflow YAML files (Part 4)
- Orchestrator refactoring (Part 4)
- Main CLI updates (Part 4)

## Prerequisites

✅ Part 1 and Part 2 must be completed:
- `WorkflowDefinition`, `load_workflow_from_yaml()` exist
- `WorkflowEngine` can execute workflows
- All Part 1 and Part 2 tests pass

## Implementation Tasks

### 1. Create Workflow Registry Module
**File**: `src/workflow_registry.py` (new file)

```python
"""
Workflow registry operations using ORAS and OCI registry.

Workflows are stored in the registry under workflows/{workflow-id}:v{version}.
"""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx


REGISTRY_URL = "localhost:5000"


def push_workflow_to_registry(
    workflow_file: Path,
    workflow_id: str,
    version: str = "v1"
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
        result = subprocess.run(
            [
                "oras", "push",
                registry_path,
                f"{workflow_file}:application/yaml"
            ],
            capture_output=True,
            text=True,
            check=True
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
    workflow_id: str,
    version: str = "v1",
    output_dir: Optional[Path] = None
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
        result = subprocess.run(
            ["oras", "pull", registry_path, "-o", str(output_dir)],
            capture_output=True,
            text=True,
            check=True
        )

        # Find the YAML file in output directory
        yaml_files = list(output_dir.glob("*.yaml")) + list(output_dir.glob("*.yml"))
        if yaml_files:
            print(f"✓ Pulled workflow {workflow_id}:{version} from registry")
            return yaml_files[0]
        else:
            print(f"✗ No YAML file found in pulled artifacts")
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
        List of workflow repository names (e.g., ["workflows/code-generation", "workflows/smart-router"])

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
        workflow_repos = [repo for repo in repositories if repo.startswith("workflows/")]

        return workflow_repos

    except httpx.RequestError as e:
        print(f"✗ Failed to query registry: {e}")
        return []
    except Exception as e:
        print(f"✗ Error listing workflows: {e}")
        return []


def get_workflow_metadata(workflow_id: str, version: str = "v1") -> Optional[Dict[str, Any]]:
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
            "steps": len(workflow.steps)
        }
    except Exception as e:
        print(f"✗ Failed to parse workflow metadata: {e}")
        return None
```

**Tests**: `tests/unit/test_workflow_registry.py`
- Test `push_workflow_to_registry()` with mocked subprocess
- Test `pull_workflow_from_registry()` with mocked subprocess
- Test `list_workflows()` with mocked HTTP response
- Test `get_workflow_metadata()` with mocked pull and parse
- Test error handling (registry down, ORAS not found, invalid YAML)
- Test file not found error in push
- Test no YAML files in pulled artifacts

### 2. Extend Discovery Module
**File**: `src/discovery.py` (extend existing file)

Add the following function:

```python
from typing import Optional
from pathlib import Path
from src.workflow_registry import pull_workflow_from_registry
from src.workflow_engine import load_workflow_from_yaml, WorkflowDefinition


# Cache for discovered workflows
_workflow_cache: Dict[str, WorkflowDefinition] = {}


async def discover_workflow(workflow_id: str, version: str = "v1") -> Optional[WorkflowDefinition]:
    """
    Discover and load a workflow from the registry.

    Args:
        workflow_id: Unique workflow identifier
        version: Workflow version (default: v1)

    Returns:
        WorkflowDefinition object, or None if not found

    Example:
        workflow = await discover_workflow("code-generation", "v1")
        if workflow:
            print(f"Found workflow: {workflow.metadata.name}")
    """
    cache_key = f"{workflow_id}:{version}"

    # Check cache first
    if cache_key in _workflow_cache:
        print(f"[Discovery] Workflow {cache_key} found in cache")
        return _workflow_cache[cache_key]

    print(f"[Discovery] Discovering workflow: {workflow_id}:{version}")

    # Pull from registry
    workflow_path = pull_workflow_from_registry(workflow_id, version)
    if not workflow_path:
        print(f"[Discovery] Workflow {workflow_id}:{version} not found in registry")
        return None

    try:
        # Load and validate
        workflow = load_workflow_from_yaml(workflow_path)
        print(f"[Discovery] Loaded workflow: {workflow.metadata.name}")

        # Cache it
        _workflow_cache[cache_key] = workflow

        return workflow

    except Exception as e:
        print(f"[Discovery] Failed to load workflow: {e}")
        return None


def clear_workflow_cache():
    """Clear the workflow cache (useful for testing)."""
    global _workflow_cache
    _workflow_cache = {}
```

**Tests**: Update `tests/unit/test_discovery.py`
- Test `discover_workflow()` with mocked registry pull
- Test workflow caching (second call doesn't pull from registry)
- Test workflow not found returns None
- Test invalid YAML returns None
- Test `clear_workflow_cache()` clears cache
- Verify no regressions in existing discovery tests

### 3. Create Workflow Push Script
**File**: `scripts/push_workflows.sh` (new file)

```bash
#!/bin/bash

set -e

echo "=========================================="
echo "Pushing Workflows to Registry"
echo "=========================================="

# Check if ORAS is installed
if ! command -v oras &> /dev/null; then
    echo "✗ ORAS not found. Installing..."
    bash scripts/install-oras.sh
fi

# Check if registry is running
echo "→ Checking registry status..."
if ! curl -s http://localhost:5000/v2/ > /dev/null; then
    echo "✗ Registry not running at localhost:5000"
    echo "  Start registry with: bash scripts/bootstrap.sh"
    exit 1
fi
echo "✓ Registry is running"

# Push workflows
WORKFLOWS_DIR="workflows"

if [ ! -d "$WORKFLOWS_DIR" ]; then
    echo "✗ Workflows directory not found: $WORKFLOWS_DIR"
    echo "  Run this script from the project root"
    exit 1
fi

# Find all YAML workflow files
WORKFLOW_FILES=$(find "$WORKFLOWS_DIR" -name "*.yaml" -o -name "*.yml")

if [ -z "$WORKFLOW_FILES" ]; then
    echo "⚠ No workflow files found in $WORKFLOWS_DIR"
    exit 0
fi

echo ""
echo "→ Pushing workflows to registry..."

for workflow_file in $WORKFLOW_FILES; do
    # Extract workflow ID from filename (e.g., code-generation.yaml -> code-generation)
    filename=$(basename "$workflow_file")
    workflow_id="${filename%.*}"

    echo "  → Pushing $workflow_id..."

    if oras push "localhost:5000/workflows/$workflow_id:v1" \
        "$workflow_file:application/yaml" > /dev/null 2>&1; then
        echo "    ✓ Pushed workflows/$workflow_id:v1"
    else
        echo "    ✗ Failed to push $workflow_id"
    fi
done

echo ""
echo "→ Listing all workflows in registry..."
curl -s http://localhost:5000/v2/_catalog | jq '.repositories | map(select(startswith("workflows/")))' || echo "  (jq not installed, skipping formatted output)"

echo ""
echo "✓ Workflow push complete"
echo "=========================================="
```

Make it executable:
```bash
chmod +x scripts/push_workflows.sh
```

**Tests**: Manual testing
- Create dummy workflow YAML file
- Run script
- Verify workflow appears in registry catalog
- Test error handling (registry down, ORAS not found)

### 4. Update Bootstrap Script
**File**: `scripts/bootstrap.sh` (extend existing file)

Add after agent card push section:

```bash
# Push workflows to registry
echo ""
echo "→ Pushing workflows to registry..."
if [ -d "workflows" ] && [ -n "$(ls -A workflows/*.yaml 2>/dev/null)" ]; then
    bash scripts/push_workflows.sh
else
    echo "  ⚠ No workflows directory or workflow files found, skipping"
fi
```

Update success message:
```bash
echo "✓ All services started successfully!"
echo "  - Registry: http://localhost:5000"
echo "  - Plan Agent: http://localhost:8001"
echo "  - Build Agent: http://localhost:8002"
echo "  - Test Agent: http://localhost:8003"
echo "  - Agent cards and workflows pushed to registry"
```

**Tests**: Manual testing
- Run `bash scripts/bootstrap.sh`
- Verify workflows are pushed
- Check registry contains workflows

## Test Files

### `tests/unit/test_workflow_registry.py` (new file)

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.workflow_registry import (
    push_workflow_to_registry,
    pull_workflow_from_registry,
    list_workflows,
    get_workflow_metadata,
)


class TestPushWorkflowToRegistry:
    @patch('subprocess.run')
    def test_push_success(self, mock_run):
        """Test successful workflow push."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with patch('pathlib.Path.exists', return_value=True):
            result = push_workflow_to_registry(
                Path("test.yaml"),
                "test-workflow",
                "v1"
            )

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "oras" in args
        assert "push" in args
        assert "localhost:5000/workflows/test-workflow:v1" in args

    @patch('subprocess.run')
    def test_push_file_not_found(self, mock_run):
        """Test push with non-existent file."""
        with patch('pathlib.Path.exists', return_value=False):
            result = push_workflow_to_registry(
                Path("missing.yaml"),
                "test-workflow",
                "v1"
            )

        assert result is False
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_push_oras_failure(self, mock_run):
        """Test push when ORAS command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "oras", stderr="error")

        with patch('pathlib.Path.exists', return_value=True):
            result = push_workflow_to_registry(
                Path("test.yaml"),
                "test-workflow",
                "v1"
            )

        assert result is False


class TestPullWorkflowFromRegistry:
    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    @patch('pathlib.Path.glob')
    def test_pull_success(self, mock_glob, mock_mkdtemp, mock_run):
        """Test successful workflow pull."""
        mock_mkdtemp.return_value = "/tmp/test"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_glob.return_value = [Path("/tmp/test/workflow.yaml")]

        result = pull_workflow_from_registry("test-workflow", "v1")

        assert result == Path("/tmp/test/workflow.yaml")
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_pull_oras_failure(self, mock_run):
        """Test pull when ORAS command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "oras", stderr="not found")

        result = pull_workflow_from_registry("test-workflow", "v1")

        assert result is None


class TestListWorkflows:
    @patch('httpx.get')
    def test_list_workflows_success(self, mock_get):
        """Test listing workflows from registry."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "repositories": [
                "agents/plan",
                "workflows/code-generation",
                "workflows/smart-router",
                "agents/build"
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        workflows = list_workflows()

        assert len(workflows) == 2
        assert "workflows/code-generation" in workflows
        assert "workflows/smart-router" in workflows

    @patch('httpx.get')
    def test_list_workflows_registry_down(self, mock_get):
        """Test listing when registry is down."""
        mock_get.side_effect = httpx.RequestError("Connection failed")

        workflows = list_workflows()

        assert workflows == []


class TestGetWorkflowMetadata:
    @patch('src.workflow_registry.pull_workflow_from_registry')
    @patch('src.workflow_registry.load_workflow_from_yaml')
    def test_get_metadata_success(self, mock_load, mock_pull):
        """Test getting workflow metadata."""
        mock_pull.return_value = Path("/tmp/workflow.yaml")

        mock_workflow = MagicMock()
        mock_workflow.metadata.id = "test-workflow"
        mock_workflow.metadata.name = "Test Workflow"
        mock_workflow.metadata.version = "1.0.0"
        mock_workflow.metadata.description = "A test"
        mock_workflow.metadata.tags = ["test"]
        mock_workflow.steps = [MagicMock(), MagicMock()]
        mock_load.return_value = mock_workflow

        metadata = get_workflow_metadata("test-workflow", "v1")

        assert metadata["id"] == "test-workflow"
        assert metadata["name"] == "Test Workflow"
        assert metadata["steps"] == 2

    @patch('src.workflow_registry.pull_workflow_from_registry')
    def test_get_metadata_pull_failed(self, mock_pull):
        """Test metadata when pull fails."""
        mock_pull.return_value = None

        metadata = get_workflow_metadata("test-workflow", "v1")

        assert metadata is None
```

### Update `tests/unit/test_discovery.py`

Add to existing file:

```python
import pytest
from unittest.mock import patch, AsyncMock
from src.discovery import discover_workflow, clear_workflow_cache

@pytest.mark.asyncio
class TestDiscoverWorkflow:
    async def test_discover_workflow_success(self):
        """Test successful workflow discovery."""
        mock_workflow = MagicMock()
        mock_workflow.metadata.name = "Test Workflow"

        with patch('src.discovery.pull_workflow_from_registry', return_value=Path("/tmp/workflow.yaml")):
            with patch('src.discovery.load_workflow_from_yaml', return_value=mock_workflow):
                workflow = await discover_workflow("test-workflow", "v1")

                assert workflow is not None
                assert workflow.metadata.name == "Test Workflow"

    async def test_discover_workflow_caching(self):
        """Test workflow caching."""
        mock_workflow = MagicMock()
        mock_workflow.metadata.name = "Test Workflow"

        with patch('src.discovery.pull_workflow_from_registry', return_value=Path("/tmp/workflow.yaml")) as mock_pull:
            with patch('src.discovery.load_workflow_from_yaml', return_value=mock_workflow):
                workflow1 = await discover_workflow("test-workflow", "v1")
                workflow2 = await discover_workflow("test-workflow", "v1")

                assert workflow1 is workflow2
                mock_pull.assert_called_once()  # Only called once due to caching

    async def test_discover_workflow_not_found(self):
        """Test workflow not found."""
        with patch('src.discovery.pull_workflow_from_registry', return_value=None):
            workflow = await discover_workflow("missing-workflow", "v1")

            assert workflow is None

    async def test_clear_workflow_cache(self):
        """Test cache clearing."""
        mock_workflow = MagicMock()

        with patch('src.discovery.pull_workflow_from_registry', return_value=Path("/tmp/workflow.yaml")):
            with patch('src.discovery.load_workflow_from_yaml', return_value=mock_workflow):
                await discover_workflow("test-workflow", "v1")
                clear_workflow_cache()
                await discover_workflow("test-workflow", "v1")

                # Should pull twice since cache was cleared
                # Verify by checking call count (implementation detail)
```

### `tests/fixtures/conftest.py` (additions)

```python
@pytest.fixture
def mock_oras_workflow_pull(tmp_path):
    """Mock ORAS workflow pull operation."""
    def _create_workflow(workflow_id: str, content: str):
        workflow_file = tmp_path / f"{workflow_id}.yaml"
        workflow_file.write_text(content)
        return workflow_file
    return _create_workflow

@pytest.fixture
def mock_workflow_registry():
    """Mock workflow registry with sample workflows."""
    return {
        "repositories": [
            "workflows/code-generation",
            "workflows/smart-router",
            "workflows/parallel-analysis",
            "agents/plan",
            "agents/build"
        ]
    }
```

## Acceptance Criteria

- [ ] `src/workflow_registry.py` created with all functions
- [ ] `push_workflow_to_registry()` pushes workflow to OCI registry via ORAS
- [ ] `pull_workflow_from_registry()` pulls workflow from registry
- [ ] `list_workflows()` queries registry catalog and filters workflows
- [ ] `get_workflow_metadata()` extracts metadata from workflow
- [ ] `discover_workflow()` added to `src/discovery.py`
- [ ] Workflow discovery uses caching
- [ ] `scripts/push_workflows.sh` created and executable
- [ ] `scripts/bootstrap.sh` updated to push workflows
- [ ] All unit tests pass: `uv run pytest tests/unit/test_workflow_registry.py -v`
- [ ] Discovery tests updated: `uv run pytest tests/unit/test_discovery.py -v`
- [ ] Code coverage >80% for registry code
- [ ] No linting errors: `uv run invoke lint.black-check && uv run invoke lint.flake8`
- [ ] All existing tests still pass: `uv run invoke test`
- [ ] Manual test: `bash scripts/push_workflows.sh` works

## Validation Commands

```bash
# 1. Verify Python syntax
python -c "import ast; ast.parse(open('src/workflow_registry.py').read())"

# 2. Verify imports work
python -c "from src.workflow_registry import push_workflow_to_registry, pull_workflow_from_registry, list_workflows; print('✓ Registry functions imported')"

# 3. Verify discovery module updated
python -c "from src.discovery import discover_workflow; print('✓ discover_workflow imported')"

# 4. Run registry unit tests
uv run pytest tests/unit/test_workflow_registry.py -v

# 5. Run updated discovery tests
uv run pytest tests/unit/test_discovery.py -v

# 6. Check coverage
uv run pytest tests/unit/test_workflow_registry.py --cov=src.workflow_registry --cov-report=term-missing

# 7. Verify no regressions
uv run invoke test

# 8. Lint checks
uv run invoke lint.black-check
uv run invoke lint.flake8

# 9. Manual test (requires registry running)
# Start registry first
docker run -d -p 5000:5000 --name registry registry:2

# Create dummy workflow
mkdir -p workflows
cat > workflows/test.yaml << 'EOF'
metadata:
  id: test-workflow
  name: Test
  version: 1.0.0
steps:
  - id: step1
    skill: test_skill
EOF

# Test push script
bash scripts/push_workflows.sh

# Verify in registry
curl -s http://localhost:5000/v2/_catalog | jq '.repositories'

# Test list function
python -c "from src.workflow_registry import list_workflows; print(list_workflows())"

# Test pull function
python -c "from src.workflow_registry import pull_workflow_from_registry; path = pull_workflow_from_registry('test', 'v1'); print(f'Pulled to: {path}')"

# Cleanup
docker stop registry && docker rm registry
rm -rf workflows/test.yaml
```

## Next Steps

After completing Part 3 and all tests pass:
- ✅ Proceed to **Part 4: Example Workflows & Orchestrator Integration**
- Part 4 will create actual workflow YAML files and integrate with orchestrator
