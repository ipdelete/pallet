# Feature Specification: Repeatable & Productive Local Development Environment

**Feature Branch**: `001-dev-env`
**Created**: 2025-10-27
**Status**: Draft
**Input**: I want a local development environment that is repeatable, and productive for engineers

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Setup New Developer Environment (Priority: P1)

A new engineer joins the team and needs to set up their local development environment. They should be able to follow documented setup steps and have a fully functional environment where they can run the application and tests without manual configuration or debugging.

**Why this priority**: Onboarding new engineers is critical for team productivity. Every hour spent debugging setup is lost development time. This directly impacts time-to-first-contribution.

**Independent Test**: A new engineer can follow setup docs, run one bootstrap command, and have a working dev environment with all services running (agents, registry, etc.) on first attempt.

**Acceptance Scenarios**:

1. **Given** a fresh machine with required base tools (Git, Python 3.12+, Node.js, Docker), **When** engineer follows setup steps and runs bootstrap, **Then** all services start successfully and application responds to test requests
2. **Given** setup is complete, **When** engineer runs `uv run python main.py "test request"`, **Then** complete pipeline executes without errors and outputs are saved to `app/`
3. **Given** a completed setup, **When** engineer runs test suite, **Then** all tests pass without configuration changes

---

### User Story 2 - Tear Down & Clean Up Environment (Priority: P1)

After development work, engineers need a safe way to completely tear down services and clean up logs/artifacts. This ensures no stale state interferes with subsequent work and disk space remains clean.

**Why this priority**: Stale state is a common source of debugging friction ("works on my machine" problems). Quick cleanup is essential for productive iteration.

**Independent Test**: Engineer can run tear-down command and verify all services are stopped and logs/artifacts are removed without requiring manual `docker kill` or log file deletion.

**Acceptance Scenarios**:

1. **Given** services are running, **When** engineer runs tear-down command, **Then** all FastAPI agents and Docker registry stop gracefully
2. **Given** tear-down is complete, **When** engineer checks running processes, **Then** no Pallet-related services are active
3. **Given** tear-down with cleanup flag, **When** engineer checks `logs/` directory, **Then** all logs are removed

---

### User Story 3 - Run Tests & Code Quality Checks (Priority: P1)

Engineers need quick, consistent feedback on code quality and test coverage. They should be able to run linting, formatting, and tests with simple, memorable commands that follow project conventions.

**Why this priority**: Development velocity depends on fast feedback loops. Engineers need confidence that their changes are correct before committing.

**Independent Test**: Engineer can run linting and test commands from project docs and see clear pass/fail results with actionable error messages.

**Acceptance Scenarios**:

1. **Given** code changes, **When** engineer runs format check command, **Then** Black formatter validates code style and reports any violations
2. **Given** code changes, **When** engineer runs linting command, **Then** Flake8 checks for style issues and reports violations with line numbers
3. **Given** code changes, **When** engineer runs test command, **Then** all tests execute and summary shows pass count, fail count, and coverage percentage

---

### User Story 4 - Debug Single Agent (Priority: P2)

Engineers need to test individual agents in isolation when developing agent functionality. They should be able to start an agent and manually test its endpoints without running the full pipeline.

**Why this priority**: Faster feedback when developing specific agent logic. Reduces iteration time compared to running full pipeline each time.

**Independent Test**: Engineer can start a single agent (e.g., plan agent), call its endpoints directly with JSON-RPC, and see responses without full pipeline overhead.

**Acceptance Scenarios**:

1. **Given** plan agent is running on port 8001, **When** engineer POSTs JSON-RPC request to `/execute` endpoint, **Then** agent processes request and returns structured response
2. **Given** agent is running, **When** engineer calls `/agent-card` endpoint, **Then** agent returns its skill definitions in expected format

---

### User Story 5 - Verify Service Health (Priority: P2)

Engineers need quick commands to verify that services are running and accessible. This helps diagnose setup/connectivity issues without deep debugging.

**Why this priority**: Reduces time spent debugging "is it running or not" questions. Clear health checks speed up troubleshooting.

**Independent Test**: Engineer can run a health check command and see clear status (running/not running, accessible/not accessible) for each service.

**Acceptance Scenarios**:

1. **Given** services are running, **When** engineer runs health check, **Then** output shows plan agent (8001), build agent (8002), test agent (8003), and registry (5000) all accessible
2. **Given** a service is not running, **When** engineer runs health check, **Then** output clearly indicates which services are unavailable

---

### Edge Cases

- What happens when bootstrap fails partway through (e.g., Docker pull timeout)? → Should have clear error message with next steps
- How does the system handle ports already in use from previous sessions? → Should guide engineer to kill processes or use alternative ports
- What if `uv sync` or `npm install` dependencies have conflicts? → Should document how to resolve without manual intervention
- How does system behave when Docker daemon is not running? → Should provide clear error and guidance to start Docker

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Setup process MUST complete with single bootstrap command (after prerequisites are installed)
- **FR-002**: System MUST start all three agents (Plan, Build, Test) on fixed ports (8001, 8002, 8003) without manual configuration
- **FR-003**: System MUST start OCI Registry on port 5000 without manual configuration
- **FR-004**: System MUST provide tear-down command that stops all services gracefully
- **FR-005**: System MUST provide tear-down option to clean logs and artifacts from `logs/` and `app/` directories
- **FR-006**: Engineers MUST be able to run unit tests, integration tests, and API tests with simple invoke commands
- **FR-007**: Engineers MUST be able to run Black formatter, Flake8 linter with simple invoke commands
- **FR-008**: Engineers MUST be able to run code coverage analysis
- **FR-009**: System MUST support starting individual agents for manual testing
- **FR-010**: System MUST provide curl/manual testing examples in documentation
- **FR-011**: Setup documentation MUST clearly document all prerequisites (versions, tools)
- **FR-012**: Setup documentation MUST provide troubleshooting guide with common issues and solutions

### Constitutional Compliance Requirements

Per the project constitution, all features MUST include:

- **Code Quality**: All code passes Black + Flake8; type hints on public APIs; cyclomatic complexity <10
- **Testing**: TDD approach; unit tests (>80% coverage) + integration/contract tests as applicable
- **Performance**: Impact documented vs. baselines (e.g., agent latency, memory usage)
- **UX Consistency**: Response schemas match published agent cards; error messages include request IDs; help text auto-generated from cards
- **Versioning**: Breaking changes documented + migration guide if schema/API modified

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New engineer completes full setup in under 10 minutes (from fresh checkout to first successful pipeline run)
- **SC-002**: Zero manual configuration required after bootstrap (agents and registry start without environment variables or config files beyond what bootstrap provides)
- **SC-003**: All services start successfully on first bootstrap attempt 95% of the time (failing only due to external factors like Docker daemon not running)
- **SC-004**: Engineers can run tests, linting, and formatting with commands documented in project README or test docs
- **SC-005**: Tear-down process removes all services and artifacts within 30 seconds
- **SC-006**: Health check command provides clear pass/fail status for each service in under 5 seconds
- **SC-007**: Documentation is accurate enough that <5% of new engineers need to ask setup questions in team chat

## Assumptions

- Engineers have Git, Python 3.12+, Node.js 18+, and Docker installed before starting setup
- Local ports 5000, 8001, 8002, 8003 are available (or can be freed)
- Setup is targeted at macOS/Linux environments (Bash available)
- Docker daemon runs with user's credentials (no sudoer issues)
- Network access available for pulling dependencies (npm, Python packages, Docker images)
