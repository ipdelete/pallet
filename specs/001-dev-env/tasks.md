# Tasks: Repeatable & Productive Local Development Environment

**Feature**: 001-dev-env | **Date**: 2025-10-27 | **Branch**: `001-dev-env`

**Goal**: Enable engineers to bootstrap a fully functional Pallet system with single commands using kind (Kubernetes) + Helm for registry deployment, supporting complete dev environment setup, testing, and cleanup.

---

## Overview

**User Stories** (5 total, Priority order):
1. **US1 (P1)**: Setup New Developer Environment
2. **US2 (P1)**: Tear Down & Clean Up Environment
3. **US3 (P1)**: Run Tests & Code Quality Checks
4. **US4 (P2)**: Debug Single Agent
5. **US5 (P2)**: Verify Service Health

**Phase Structure**:
- **Phase 1**: Setup & Infrastructure
- **Phase 2**: Foundational Bootstrap Components
- **Phase 3**: User Story 1 - Setup New Developer Environment
- **Phase 4**: User Story 2 - Tear Down & Clean Up Environment
- **Phase 5**: User Story 3 - Run Tests & Code Quality Checks
- **Phase 6**: User Story 4 - Debug Single Agent
- **Phase 7**: User Story 5 - Verify Service Health
- **Phase 8**: Polish & Cross-Cutting Concerns

---

## Phase 1: Setup & Infrastructure

Setup project structure, verify toolchain, establish conventions.

### Goals
- Establish directory structure for Helm charts, scripts, tests
- Verify all prerequisites and document version requirements
- Setup CI/CD integration points

### Tasks

- [ ] T001 Create project structure per plan: `charts/pallet-registry/templates/`, `scripts/`, `tests/integration/`, `tests/unit/`
- [ ] T002 [P] Create `kind-config.yaml` in repo root with port mappings (5000→5000, cluster name: pallet-dev)
- [ ] T003 [P] Create `scripts/install-kind.sh` to verify kind, helm, kubectl, docker installations with version checks
- [ ] T004 Create placeholder files: `charts/pallet-registry/Chart.yaml`, `values.yaml`, `values-dev.yaml`
- [ ] T005 [P] Update `.specify/agent-context.yaml` with active technologies: kind 0.20+, Helm 3.12+, kubectl 1.27+, OCI Registry 2.8.3+

---

## Phase 2: Foundational Bootstrap Components

Create Helm chart templates and core bootstrap logic. All other phases depend on this.

### Goals
- Helm chart fully functional and validated
- Bootstrap script (kind cluster creation + Helm install) working
- Health check infrastructure in place
- Integration tests setup for k8s bootstrap validation

### Independent Test Criteria
- `helm lint charts/pallet-registry/` passes without errors
- Kind cluster creates in <30s, Helm release deploys in <20s
- Registry health endpoint responds in <5s after bootstrap
- All chart templates render without errors

### Tasks

- [ ] T006 [P] [Story: Foundational] Write `charts/pallet-registry/Chart.yaml` with metadata (name: pallet-registry, version: 1.0.0, appVersion: 2.8.3)
- [ ] T007 [P] [Story: Foundational] Write `charts/pallet-registry/values.yaml` with full schema (image, replicaCount, service, persistence, resources, probes)
- [ ] T008 [P] [Story: Foundational] Write `charts/pallet-registry/values-dev.yaml` with dev overrides (1 replica, 1Gi PVC, IfNotPresent pull policy)
- [ ] T009 [P] [Story: Foundational] Write `charts/pallet-registry/templates/deployment.yaml` with pod spec, liveness/readiness probes, resource limits
- [ ] T010 [P] [Story: Foundational] Write `charts/pallet-registry/templates/service.yaml` (NodePort type, port 5000→5000)
- [ ] T011 [P] [Story: Foundational] Write `charts/pallet-registry/templates/pvc.yaml` (registry-data PVC, 1Gi default, ReadWriteOnce)
- [ ] T012 [P] [Story: Foundational] Write `charts/pallet-registry/templates/_helpers.tpl` with template helpers (labels, selectors, names)
- [ ] T013 [Story: Foundational] Write `charts/pallet-registry/templates/configmap.yaml` (optional, minimal registry config)
- [ ] T014 [Story: Foundational] Run `helm lint charts/pallet-registry/` and fix any validation errors
- [ ] T015 [Story: Foundational] Write unit test `tests/unit/test_health_check.py` validating health check output format (JSON + human-readable)
- [ ] T016 [Story: Foundational] Write integration test `tests/integration/test_bootstrap_k8s.py` validating kind cluster creation, Helm deploy, registry health
- [ ] T017 [Story: Foundational] Create `scripts/bootstrap-k8s.sh` stub with validation, kind cluster creation, Helm install, health check sequencing
- [ ] T018 [Story: Foundational] Create `scripts/bootstrap.sh` fallback validation (Docker-only, unmodified from existing)

---

## Phase 3: User Story 1 - Setup New Developer Environment

Engineers run bootstrap and get fully functional dev environment.

### Story Goal
New engineer follows setup docs, runs one bootstrap command, gets working dev environment with all services running on first attempt.

### Independent Test Criteria
- **Acceptance Test 1**: Fresh engineer (no Pallet state) runs `bash scripts/bootstrap-k8s.sh` → all services start successfully
- **Acceptance Test 2**: After bootstrap, `uv run python main.py "test request"` completes without errors, outputs saved to `app/`
- **Acceptance Test 3**: Setup completes in <5 minutes (excluding Docker image pulls on first run)

### Tasks

- [ ] T019 [P] [US1] Complete `scripts/bootstrap-k8s.sh`: check dependencies → create kind cluster → create namespace → helm install → wait for pod ready → verify health
- [ ] T020 [US1] Add stdout logging to `bootstrap-k8s.sh` with status messages (colors: green=success, red=error, yellow=progress)
- [ ] T021 [US1] Add error handling to `bootstrap-k8s.sh` with clear messages (kind not found, Docker daemon down, port 5000 in use, Helm validation failed)
- [ ] T022 [P] [US1] Write `scripts/verify-bootstrap.sh` to check all services operational (kind cluster exists, Helm release active, registry responds, network connectivity)
- [ ] T023 [US1] Update `README.md` with prerequisites section (tool versions, installation steps for macOS/Linux)
- [ ] T024 [US1] Update `README.md` with quick start section linking to `specs/001-dev-env/quickstart.md`
- [ ] T025 [US1] Create troubleshooting section in `README.md` with common setup issues (kind not found, Docker daemon down, port conflicts, registry stuck pending)
- [ ] T026 [P] [US1] Write integration test `tests/integration/test_setup_complete.py` validating full bootstrap pipeline (cluster ready, Helm active, registry healthy, agents deployable)
- [ ] T027 [US1] Add post-bootstrap status report to `bootstrap-k8s.sh` output showing system readiness

---

## Phase 4: User Story 2 - Tear Down & Clean Up Environment

Engineers safely remove services and artifacts.

### Story Goal
Engineer runs tear-down command and verifies all services stopped, logs/artifacts cleaned, stale state prevented.

### Independent Test Criteria
- **Acceptance Test 1**: Services running → run tear-down command → all FastAPI agents and registry stop gracefully
- **Acceptance Test 2**: Check running processes → no Pallet-related services active
- **Acceptance Test 3**: Tear-down with cleanup flag → `logs/` and `app/` directories empty

### Tasks

- [ ] T028 [P] [US2] Create `scripts/kill.sh` with modes: default (stops services), `--kind` (kills kind cluster), `--clean-logs` (removes logs/ + app/), `--clean-pvc` (deletes registry data)
- [ ] T029 [P] [US2] Implement kind cluster detection in `kill.sh` (detect pallet-dev cluster, graceful delete with error handling)
- [ ] T030 [US2] Implement Docker fallback in `kill.sh` (if kind not present, use original Docker-based cleanup)
- [ ] T031 [US2] Add safety prompts to `kill.sh` for destructive operations (`--clean-pvc` requires explicit flag)
- [ ] T032 [US2] Add logging to `kill.sh` showing what's being cleaned (cluster name, release name, directories removed)
- [ ] T033 [P] [US2] Write integration test `tests/integration/test_teardown_complete.py` validating cleanup (no running processes, directories removed, k8s cluster gone)
- [ ] T034 [US2] Update `README.md` cleanup section with `kill.sh` usage examples (modes, flags, safety considerations)

---

## Phase 5: User Story 3 - Run Tests & Code Quality Checks

Engineers run linting, formatting, testing with simple commands.

### Story Goal
Engineer runs test/lint/format commands from docs and gets clear pass/fail results with actionable errors.

### Independent Test Criteria
- **Acceptance Test 1**: Code changes → run Black formatter check → output shows violations or pass
- **Acceptance Test 2**: Code changes → run Flake8 linter → output shows style issues with line numbers
- **Acceptance Test 3**: Code changes → run test command → output shows pass count, fail count, coverage %

### Tasks

- [ ] T035 [P] [US3] Create `tasks.md` invoke commands in `tasks/__init__.py` or `Taskfile.py`: `lint.black`, `lint.black-check`, `lint.flake8`, `test`, `test.unit`, `test.integration`, `test.api`, `test.verbose`, `test.coverage`
- [ ] T036 [P] [US3] Write invoke task `lint.black` calling Black formatter on `src/`, `tests/`, `main.py`
- [ ] T037 [P] [US3] Write invoke task `lint.black-check` calling Black in check mode
- [ ] T038 [P] [US3] Write invoke task `lint.flake8` calling Flake8 on `src/`, `tests/` with config from `.flake8`
- [ ] T039 [US3] Write invoke task `test` running all tests (unit + integration, excludes slow/e2e) with pytest
- [ ] T040 [P] [US3] Write invoke task `test.unit` running unit tests only from `tests/unit/`
- [ ] T041 [P] [US3] Write invoke task `test.integration` running integration tests only from `tests/integration/`
- [ ] T042 [US3] Write invoke task `test.api` running API tests (if separate from integration)
- [ ] T043 [US3] Write invoke task `test.debug` running tests with pdb on failure
- [ ] T044 [P] [US3] Write invoke task `test.verbose` running tests with verbose output and test names
- [ ] T045 [US3] Write invoke task `test.coverage` generating coverage reports (HTML, JSON, terminal)
- [ ] T046 [US3] Update `README.md` testing section with invoke task examples and expected output
- [ ] T047 [US3] Create `.flake8` configuration file with style rules (line length, ignored violations, exclude patterns)
- [ ] T048 [US3] Ensure all new code in previous phases passes Black + Flake8 checks
- [ ] T049 [P] [US3] Write unit test `tests/unit/test_bootstrap_validation.py` for kind/Helm availability checks
- [ ] T050 [US3] Add code coverage baseline documentation (>80% target for new code)

---

## Phase 6: User Story 4 - Debug Single Agent

Engineers start individual agents and test endpoints manually.

### Story Goal
Engineer starts single agent (e.g., plan), calls endpoints directly via JSON-RPC, sees responses without full pipeline overhead.

### Independent Test Criteria
- **Acceptance Test 1**: Plan agent running on port 8001 → POST JSON-RPC to `/execute` → agent processes request, returns structured response
- **Acceptance Test 2**: Agent running → GET `/agent-card` → returns skill definitions in expected format

### Tasks

- [ ] T051 [P] [US4] Create `scripts/start-agent.sh` to start individual agents (plan/build/test) with argument: `bash scripts/start-agent.sh plan` → starts plan agent on 8001
- [ ] T052 [P] [US4] Add environment variable support in `start-agent.sh`: `AGENT_PORT` override (default 8001/8002/8003)
- [ ] T053 [US4] Document manual testing workflow in `README.md` (start agent → use curl/Postman → POST JSON-RPC to `/execute`)
- [ ] T054 [US4] Create `examples/curl-plan-agent.sh` showing JSON-RPC request to plan agent `/execute` endpoint
- [ ] T055 [US4] Create `examples/curl-agent-card.sh` showing GET to `/agent-card` endpoint to fetch skill definitions
- [ ] T056 [P] [US4] Write integration test `tests/integration/test_single_agent_debug.py` validating agent startup, `/agent-card` response, JSON-RPC `/execute` call
- [ ] T057 [US4] Add debugging tips section to `README.md` (checking agent port, viewing agent logs, testing endpoints)

---

## Phase 7: User Story 5 - Verify Service Health

Engineers check service status quickly with health check commands.

### Story Goal
Engineer runs health check and sees clear status (running/not running, accessible/not accessible) for each service.

### Independent Test Criteria
- **Acceptance Test 1**: Services running → run health check → output shows plan agent (8001), build agent (8002), test agent (8003), registry (5000) all accessible
- **Acceptance Test 2**: Service not running → health check → output clearly indicates which services unavailable
- **Acceptance Test 3**: Health check completes in <5 seconds

### Tasks

- [ ] T058 [P] [US5] Create `src/cli_health.py` implementing health check (calls `/agent-card` on each agent, `GET /v2/` on registry)
- [ ] T059 [P] [US5] Implement JSON output mode in `src/cli_health.py` (machine-readable: `{"registry": "healthy", "agents": {"plan": "healthy", "build": "down", ...}}`)
- [ ] T060 [P] [US5] Implement human-readable output mode in `src/cli_health.py` (colored status: green=healthy, red=down, yellow=degraded)
- [ ] T061 [US5] Add retry logic to health checks (3 attempts per service, 2s backoff) to handle transient failures
- [ ] T062 [US5] Add timeout configuration to health checks (default 5s per service, configurable via env var)
- [ ] T063 [US5] Create wrapper command `scripts/health-check.sh` calling `uv run python -m src.cli_health` with optional `--json` flag
- [ ] T064 [P] [US5] Write unit test `tests/unit/test_health_check_format.py` validating JSON + human output formatting
- [ ] T065 [US5] Write integration test `tests/integration/test_health_check_accuracy.py` validating correct service detection (running/not running)
- [ ] T066 [US5] Update `README.md` with health check usage examples and output explanations

---

## Phase 8: Polish & Cross-Cutting Concerns

Documentation, final validation, performance baseline, backward compatibility.

### Goals
- All documentation complete and accurate
- Performance baselines established
- Backward compatibility verified (Docker fallback works)
- Code quality gates passed

### Tasks

- [ ] T067 Create `TROUBLESHOOTING.md` documenting common issues: kind not found, Docker down, port conflicts, Helm validation failures, registry pending, PVC issues
- [ ] T068 [P] Add troubleshooting solutions with commands to diagnose and fix
- [ ] T069 Create `docs/ARCHITECTURE.md` documenting bootstrap architecture (kind + Helm + health checks, state transitions, dependency graph)
- [ ] T070 [P] Create `docs/BOOTSTRAP_INTERNALS.md` with technical details for maintainers (Helm chart structure, environment variables, configuration options)
- [ ] T071 Run final linting: `uv run invoke lint.black-check && uv run invoke lint.flake8` on all new code
- [ ] T072 [P] Run test coverage: `uv run invoke test.coverage` and verify >80% coverage for new modules
- [ ] T073 [P] Execute E2E bootstrap test: fresh `kill.sh --clean-logs`, then `bootstrap-k8s.sh`, verify all services operational
- [ ] T074 [P] Execute E2E teardown test: run `kill.sh --kind --clean-logs --clean-pvc`, verify clean state
- [ ] T075 Test Docker fallback: `bash scripts/bootstrap.sh` (original), verify registry starts without kind
- [ ] T076 [P] Test backward compatibility: both `bootstrap-k8s.sh` and `bootstrap.sh` work independently
- [ ] T077 Create performance baseline: document bootstrap times (kind cluster <30s, Helm install <20s, health check <5s)
- [ ] T078 [P] Verify no port conflicts: test with ports 5000, 8001, 8002, 8003 available and allocated correctly
- [ ] T079 Update `CLAUDE.md` with kind/Helm development guidance and quick start
- [ ] T080 Update `CLAUDE.md` with troubleshooting section for developers
- [ ] T081 [P] Run full test suite: `uv run invoke test --all` (all tests including slow/e2e, must pass)
- [ ] T082 Final code review: check all new files for Python type hints, docstrings, error handling
- [ ] T083 [P] Validate all Helm templates: `helm template registry charts/pallet-registry/ -f values-dev.yaml | kubectl apply --dry-run=client -f -`
- [ ] T084 Update project README with link to quickstart guide
- [ ] T085 [P] Verify documentation accuracy: one team member follows quickstart from scratch, report any gaps

---

## Task Summary

**Total Tasks**: 85

**By Phase**:
- Phase 1 (Setup): 5 tasks
- Phase 2 (Foundational): 13 tasks
- Phase 3 (US1 - Setup): 9 tasks
- Phase 4 (US2 - Teardown): 7 tasks
- Phase 5 (US3 - Tests): 16 tasks
- Phase 6 (US4 - Single Agent): 7 tasks
- Phase 7 (US5 - Health Check): 9 tasks
- Phase 8 (Polish): 19 tasks

**By User Story**:
- US1 (Setup New Dev Env): 9 tasks
- US2 (Teardown & Cleanup): 7 tasks
- US3 (Run Tests & Checks): 16 tasks
- US4 (Debug Single Agent): 7 tasks
- US5 (Verify Health): 9 tasks

**Parallelizable Tasks**: 42 [P] marked tasks can run in parallel (file isolation, no inter-dependencies until phase boundaries)

---

## Dependencies & Execution Order

### Critical Path
1. **Phase 1**: Setup (sequential, 5 tasks, ~5min)
2. **Phase 2**: Foundational (parallel within phase, 13 tasks, ~20min)
3. **Phase 3+**: User stories (parallel within story, sequential between stories, ~60-90min total)

### Parallel Execution Examples

**Phase 2 (Foundational) - Parallel Grouping**:
```
Group 1 (Helm templates): T006, T007, T008, T009, T010, T011, T012
Group 2 (Testing infrastructure): T015, T016
Group 3 (Scripts): T017, T018
→ Sequential: T013 (configmap), T014 (helm lint)
```

**Phase 3 (US1) - Parallel Grouping**:
```
Group 1 (Bootstrap script): T019, T021
Group 2 (Documentation): T023, T024, T025
Group 3 (Testing): T026, T027
→ Sequential: T020 (logging), T022 (verify script)
```

---

## Implementation Strategy

### MVP Scope (Phase 1-2)
**Goal**: Working kind + Helm registry deployment
- Tasks: T001-T018
- **Deliverables**:
  - Functional Helm chart (validated with `helm lint`)
  - Working `bootstrap-k8s.sh` (creates cluster, deploys registry, verifies health)
  - Integration tests for Helm + bootstrap
- **Estimated Time**: 25-30 minutes

### Incremental Delivery
- **Sprint 1**: MVP (Phase 1-2) → merge to `001-dev-env`
- **Sprint 2**: US1 (Phase 3) → bootstrap working, engineers can setup
- **Sprint 3**: US2 + US3 (Phase 4-5) → teardown + testing infrastructure
- **Sprint 4**: US4 + US5 (Phase 6-7) → debugging + health checks
- **Sprint 5**: Polish (Phase 8) → docs, performance, backward compat

### Quality Gates
- All new code passes Black + Flake8
- All Helm templates pass `helm lint`
- Integration tests pass (bootstrap lifecycle, health checks)
- >80% code coverage for new modules

---

## Unresolved Questions & Blockers

**None** - All design decisions documented in spec.md, plan.md, data-model.md, research.md

---

## References

- [spec.md](spec.md) - Feature specification & acceptance criteria
- [plan.md](plan.md) - Technical implementation plan
- [data-model.md](data-model.md) - Bootstrap state transitions & entities
- [research.md](research.md) - Decision rationale & technology choices
- [quickstart.md](quickstart.md) - Engineer quick reference guide
- [contracts/](contracts/) - Helm values schema & OCI Registry API
