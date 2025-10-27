# Implementation Plan: Repeatable & Productive Local Development Environment

**Branch**: `001-dev-env` | **Date**: 2025-10-27 | **Spec**: [spec.md](spec.md)
**Input**: I want a local development environment that is repeatable, and productive for engineers

**Focus Phase**: Registry deployment via kind (Kubernetes) + Helm (user input scope)

## Summary

Establish a repeatable local development environment that enables engineers to bootstrap a fully functional Pallet system with single commands. Current phase focuses on migrating registry deployment from Docker-only (scripts/bootstrap.sh) to Kubernetes (kind) with Helm charts for configuration management. Future phases will extend to agents, testing, and documentation infrastructure.

## Technical Context

**Language/Version**: Bash 5.0+, Python 3.12+ (for orchestration)
**Primary Dependencies**: kind (Kubernetes in Docker), Helm 3.0+, docker, kubectl, oras (for registry interaction)
**Storage**: OCI Registry v2 (deployed in Kubernetes), persisted via PVC
**Testing**: pytest + pytest-mock for integration tests
**Target Platform**: macOS/Linux (Kubernetes-capable systems with Docker)
**Project Type**: Infrastructure-as-Code (Helm charts) + Bash orchestration scripts
**Performance Goals**: Registry deployment <5s, service availability check <2s
**Constraints**: Local-only (kind cluster), sub-1GB memory total, no external dependencies beyond Docker
**Scale/Scope**: Single-cluster bootstrap (3 agents, 1 registry, 1 kind cluster per dev environment)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle Alignment

- **Code Quality First**: Bash scripts will follow project conventions (check with shellcheck), Helm charts will be validated with `helm lint`. Python orchestration code will pass Black+Flake8.
- **Test-Driven Development**: Integration tests will validate kind cluster creation, Helm deployment, registry connectivity. Tests written before implementation.
- **Performance & Observability**: Structured logging for bootstrap steps. Health checks verify all services in <2s. Baseline: registry accessible within 30s of bootstrap.
- **UX Consistency & Accessibility**: Clear error messages if kind/Helm missing. Health check output follows consistent format (JSON for machine-readable, color-coded status for human).
- **Versioning & Breaking Changes**: Helm chart versioning (semver in Chart.yaml). Backward compat maintained for bootstrap.sh interface (drop-in replacement when registry migrates to k8s).

### Quality Gates

- [x] Tests will be written before implementation (integration tests for k8s bootstrap)
- [x] Bash code validated with shellcheck; Python code MUST pass Black + Flake8
- [x] Helm charts must pass `helm lint` validation
- [x] Performance baseline documented: <5s registry ready, <2s health check
- [x] Breaking change: None (kind/Helm optional; Docker fallback remains for backward compat)

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Helm charts for Kubernetes deployment
charts/
└── pallet-registry/
    ├── Chart.yaml              # Helm chart metadata + versioning
    ├── values.yaml             # Default config (image, replicas, PVC size)
    ├── values-dev.yaml         # Dev environment overrides (1 replica, 100Mi PVC)
    └── templates/
        ├── deployment.yaml      # Registry pod spec
        ├── service.yaml         # NodePort service (localhost:5000)
        ├── pvc.yaml            # PersistentVolumeClaim for registry data
        ├── configmap.yaml       # Registry config (if needed for advanced settings)
        └── _helpers.tpl         # Template helpers

# Orchestration & bootstrap
scripts/
├── bootstrap-k8s.sh             # NEW: Kind cluster + Helm deployment
├── bootstrap.sh                 # EXISTING: Docker-only fallback
├── kill.sh                      # Updated to support both modes
└── install-kind.sh              # NEW: Verify kind installation

# Tests for infrastructure
tests/
├── integration/
│   └── test_bootstrap_k8s.py    # Validates kind cluster creation, Helm deploy, registry access
└── unit/
    └── test_health_check.py     # Validates health check output format
```

**Structure Decision**: Helm chart + bash scripts. No code changes to src/agents (agents run unchanged in K8s pods). Registry storage via Kubernetes PVC instead of Docker volume. Bootstrap script auto-detects kind availability; falls back to Docker if not installed.

## Phase 0: Research & Unknowns

**Status**: Ready to execute

### Research Tasks

1. **Kind setup best practices for macOS/Linux**: How to handle M1/M2 macs, resource limits, startup/teardown patterns
2. **Helm chart structure for registry**: Standard patterns for OCI registry deployment, ConfigMap vs values.yaml
3. **PVC vs emptyDir tradeoff**: Registry data persistence strategy for local dev
4. **Service exposure options**: NodePort vs port-forward for localhost:5000 access

### Expected Outputs

- `research.md`: Best practices documented with rationale for each decision
- Helm chart template examples collected
- Decision matrix: kind versions, Helm versions, resource allocations

## Phase 1: Design & Contracts

**Prerequisites**: research.md complete

### Deliverables

1. **`data-model.md`**: State model for kind cluster + Helm release (bootstrap states, health states)
2. **`contracts/`**:
   - Helm chart schema (values.yaml contract)
   - Registry API contract (pulled from existing OCI Registry API)
3. **`quickstart.md`**: Engineers' quick reference for kind+Helm bootstrap
4. **Agent context update**: Run update-agent-context.sh to record technology choices

### Design Decisions

- **Kind cluster naming**: `pallet-dev` (single cluster per dev environment)
- **Helm release naming**: `registry` (in `pallet` namespace)
- **Registry image**: `registry:2.8+` (latest stable)
- **Storage**: PVC `registry-data` (persistent across teardowns)
- **Service**: NodePort 5000→5000 (localhost:5000 access)
- **Health check**: `curl http://localhost:5000/v2/`

## Phase 2: Implementation Plan

**Split into 2 milestones**:

### Milestone 1: Helm Chart + Bootstrap Script

**Tasks**:
1. Create `charts/pallet-registry/` directory structure
2. Write Helm chart templates (deployment, service, pvc, configmap)
3. Create `bootstrap-k8s.sh` script (kind create → helm install → verify)
4. Create `install-kind.sh` dependency checker
5. Update `kill.sh` to support both Docker and kind cleanup
6. Write integration tests for k8s bootstrap

**Tests BEFORE code**:
- Unit: Health check output validation
- Integration: Kind cluster creation, Helm deploy, registry availability

### Milestone 2: Documentation + Backward Compatibility

**Tasks**:
1. Update README with kind/Helm setup instructions
2. Create troubleshooting guide for common k8s issues
3. Update CLAUDE.md with k8s development guidance
4. Ensure `bootstrap.sh` (Docker fallback) remains functional
5. Add `--prefer-docker` flag to bootstrap for engineers who don't want k8s

**Tests**:
- E2E: Full bootstrap with both methods (kind and docker)
- Verify agent startup works identically in both deployments

### Success Criteria (Phase 2)

- Engineers can run `bash scripts/bootstrap-k8s.sh` → registry ready in <30s
- `scripts/kill.sh --kind --clean-logs` removes cluster and artifacts
- Health check: `uv run python -m src.cli_health --json` shows all services (registry + agents when deployed)
- Documentation complete and tested with fresh engineer onboarding
- All tests passing + >80% coverage for new bootstrap code
- No performance regression vs. Docker bootstrap (<100ms difference)

## Unresolved Questions

- **Windows support**: Is WSL2 in scope for this phase, or macOS/Linux only?
- **Agent deployment in k8s**: Should agents run in k8s pods (Phase 3) or remain Docker containers?
- **PVC cleanup policy**: Should `kill.sh --clean-logs` delete PVC data, or preserve it for next bootstrap?
