# Runtime Workflow Loading Verification

**Date**: 2025-10-19
**Status**: ✅ VERIFIED - Runtime code only reads from registry

## Summary

The Pallet framework correctly enforces **registry-only workflow loading at runtime**. The `workflows/` directory contains example YAML files used only during bootstrap and testing, never during normal orchestration.

---

## Findings

### ✅ Runtime Code (Production)

**All runtime workflow loading goes through the registry:**

1. **`src/orchestrator.py`** (line 136)
   ```python
   workflow = await discover_workflow(workflow_id, version)
   ```
   - Uses `discover_workflow()` from discovery module
   - No direct file reads from `workflows/`

2. **`src/discovery.py`** (lines 358-408)
   ```python
   async def discover_workflow(workflow_id: str, version: str = "v1"):
       workflow_path = pull_workflow_from_registry(workflow_id, version)
       yaml_content = Path(workflow_path).read_text()
       workflow = load_workflow_from_yaml(yaml_content)
   ```
   - Calls `pull_workflow_from_registry()` - pulls from OCI registry via ORAS
   - Reads from **temporary directory** (not `workflows/`)
   - Returns: `/tmp/tmpXXXXXX/workflows/code-generation.yaml` (registry pull)

3. **`src/workflow_registry.py`** (lines 77-166)
   ```python
   def pull_workflow_from_registry(workflow_id: str, version: str = "v1"):
       output_dir = Path(tempfile.mkdtemp())  # Creates /tmp/tmpXXXXXX
       registry_path = f"{REGISTRY_URL}/workflows/{workflow_id}:{version}"
       subprocess.run(["oras", "pull", registry_path, "-o", str(output_dir)])
       yaml_files = list(output_dir.glob("**/*.yaml"))
       return yaml_files[0]  # Returns path in temp directory
   ```
   - Uses ORAS CLI to pull from `localhost:5000/workflows/{id}:v1`
   - Extracts to **temporary directory**
   - Never reads from local `workflows/` folder

4. **`src/workflow_engine.py`** (lines 148-176)
   ```python
   def load_workflow_from_yaml(yaml_content: str) -> WorkflowDefinition:
       data = yaml.safe_load(yaml_content)
       return WorkflowDefinition(**data)
   ```
   - Takes **YAML string content** as parameter (not file path)
   - Does not perform any file I/O
   - Line 171 reference to `workflows/example.yaml` is only in **docstring example**

---

### 📚 Non-Runtime Code (Bootstrap & Testing)

**The only places that read from `workflows/` directory:**

1. **`scripts/bootstrap.sh`** (line 223)
   ```bash
   if [ -d "workflows" ] && [ -n "$(ls -A workflows/*.yaml 2>/dev/null)" ]; then
       bash scripts/push_workflows.sh
   fi
   ```
   - Reads `workflows/` during initial setup
   - Pushes YAML files to registry via `push_workflows.sh`
   - Runs **once at bootstrap**, not during orchestration

2. **`scripts/push_workflows.sh`** (line 51)
   ```bash
   oras push "localhost:5000/workflows/$workflow_id:v1" \
       "workflows/$workflow_id.yaml:application/yaml"
   ```
   - Reads local `workflows/` folder
   - Pushes to OCI registry
   - Used only during setup/deployment

3. **Test Files** (`tests/integration/`, `tests/unit/`)
   ```python
   # tests/integration/test_end_to_end.py:39
   workflow_path = Path("workflows/code-generation.yaml")
   yaml_content = workflow_path.read_text()
   ```
   - Test fixtures read from `workflows/` for validation
   - **Not used in production runtime**
   - Ensures example workflows are valid YAML

4. **`src/workflow_registry.py:38`** (Docstring only)
   ```python
   Example:
       push_workflow_to_registry(
           Path("workflows/code-generation.yaml"),  # Example in docstring
           "code-generation",
           "v1"
       )
   ```
   - Reference in **documentation/example only**
   - Not executed during runtime

5. **`src/workflow_engine.py:171`** (Docstring only)
   ```python
   Example:
       yaml_str = Path("workflows/example.yaml").read_text()  # Example in docstring
       workflow = load_workflow_from_yaml(yaml_str)
   ```
   - Reference in **documentation/example only**
   - Not executed during runtime

---

## Execution Flow: Workflow Loading

### Production Runtime Flow

```
main.py
  ↓
orchestrator.py::execute_workflow_by_id("code-generation-v1")
  ↓
discovery.py::discover_workflow("code-generation-v1", "v1")
  ↓
workflow_registry.py::pull_workflow_from_registry("code-generation-v1", "v1")
  ├─→ Creates: /tmp/tmp_abc123/  (temporary directory)
  ├─→ Executes: oras pull localhost:5000/workflows/code-generation:v1 -o /tmp/tmp_abc123/
  ├─→ Registry extracts: /tmp/tmp_abc123/workflows/code-generation.yaml
  └─→ Returns: Path("/tmp/tmp_abc123/workflows/code-generation.yaml")
  ↓
discovery.py reads: /tmp/tmp_abc123/workflows/code-generation.yaml
  ↓
workflow_engine.py::load_workflow_from_yaml(yaml_content)
  ↓
WorkflowDefinition object returned
```

**Key Points:**
- ✅ All reads happen from **temporary directories** created by ORAS
- ✅ Registry path `localhost:5000/workflows/{id}:v1` is queried
- ✅ Local `workflows/` folder is **never accessed**

---

## Code Analysis Summary

| File | Line | Type | Runtime? | Purpose |
|------|------|------|----------|---------|
| `src/orchestrator.py` | 136 | Registry call | ✅ Yes | Discovers workflow from registry |
| `src/discovery.py` | 389 | Registry call | ✅ Yes | Pulls from registry via ORAS |
| `src/workflow_registry.py` | 121 | Registry call | ✅ Yes | ORAS pull to temp dir |
| `src/workflow_engine.py` | 171 | Docstring | ❌ No | Example in documentation |
| `src/workflow_registry.py` | 38 | Docstring | ❌ No | Example in documentation |
| `scripts/bootstrap.sh` | 223 | Local read | ❌ No | Initial setup only |
| `scripts/push_workflows.sh` | 51 | Local read | ❌ No | Push to registry once |
| `tests/*` | Various | Local read | ❌ No | Test fixtures only |

---

## Verification Commands

### 1. Check Runtime Workflow Discovery

```bash
# Start with empty workflows/ directory
rm -rf workflows/
mkdir workflows/

# Bootstrap (pushes workflows to registry)
bash scripts/bootstrap.sh

# Run orchestrator - should work because it reads from registry
uv run python main.py "Create hello world"
```

**Expected Result**: ✅ Works - pulls workflow from registry, not local files

### 2. Check Registry Contents

```bash
# List workflows in registry
curl -s http://localhost:5000/v2/_catalog | jq '.repositories | map(select(startswith("workflows/")))'

# Expected output:
# [
#   "workflows/code-generation",
#   "workflows/parallel-analysis",
#   "workflows/smart-router"
# ]
```

### 3. Verify ORAS Pull Path

```bash
# Pull workflow manually to see where it goes
oras pull localhost:5000/workflows/code-generation:v1 -o /tmp/test_pull

# Check extracted path
ls -la /tmp/test_pull/
# Should show: workflows/code-generation.yaml (in temp dir, not local workflows/)
```

---

## Purpose of `workflows/` Directory

The `workflows/` directory serves as:

1. **Example Templates** - Reference implementations for users
2. **Bootstrap Source** - Initial workflow definitions pushed to registry
3. **Test Fixtures** - Validate workflow engine with known-good YAML
4. **Documentation** - Living examples of workflow syntax

**It is NOT used during runtime orchestration.**

---

## Compliance Check

### ✅ Requirements Met

- [x] Runtime code **never reads** from local `workflows/` directory
- [x] All workflow loading goes through **OCI registry** via ORAS
- [x] Workflows pulled to **temporary directories** only
- [x] `load_workflow_from_yaml()` accepts **string content**, not file paths
- [x] Discovery module uses `pull_workflow_from_registry()` exclusively
- [x] Orchestrator uses `discover_workflow()` exclusively
- [x] Local `workflows/` used only for bootstrap and testing

### ❌ Violations

**None found.**

---

## Conclusion

**The Pallet framework correctly enforces registry-only workflow loading at runtime.**

- ✅ Production code reads workflows from OCI registry via ORAS
- ✅ Temporary directories used for pulled artifacts
- ✅ Local `workflows/` folder used only during setup and testing
- ✅ No direct file reads from `workflows/` in runtime paths
- ✅ All references to `workflows/` in source code are:
  - Documentation examples (docstrings)
  - Bootstrap scripts (setup phase)
  - Test fixtures (validation)

**Verification Status**: ✅ **PASSED**

---

## Related Files

- `src/orchestrator.py` - Workflow execution entry point
- `src/discovery.py` - Workflow discovery from registry
- `src/workflow_registry.py` - ORAS pull/push operations
- `src/workflow_engine.py` - YAML parsing (string input only)
- `scripts/bootstrap.sh` - Initial setup (pushes to registry)
- `scripts/push_workflows.sh` - Registry upload utility
- `workflows/` - Example templates (not used at runtime)
