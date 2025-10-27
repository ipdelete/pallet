# Pallet A2A Agent Framework Constitution

<!-- Sync Impact Report (HTML comment) -->
<!--
  VERSION CHANGE: 0.0.0 → 1.0.0 (MAJOR: Initial constitution adoption)

  MODIFIED PRINCIPLES:
  - [PRINCIPLE_1_NAME] → "Code Quality First"
  - [PRINCIPLE_2_NAME] → "Test-Driven Development (Non-Negotiable)"
  - [PRINCIPLE_3_NAME] → "Performance & Observability"
  - [PRINCIPLE_4_NAME] → "UX Consistency & Accessibility"
  - [PRINCIPLE_5_NAME] → "Versioning & Breaking Changes"

  ADDED SECTIONS:
  - Code Quality Standards (new)
  - Testing Requirements (new)
  - Performance Baselines (new)

  TEMPLATES UPDATED:
  - plan-template.md: Constitution Check section updated ✅
  - spec-template.md: Requirements section aligned to principles ✅
  - tasks-template.md: Task categorization updated for quality gates ✅

  RATIFICATION_DATE: 2025-10-27
  LAST_AMENDED_DATE: 2025-10-27
-->

## Core Principles

### I. Code Quality First

Every line committed to the repository MUST maintain or improve code quality. Code quality is measured by:
- **Adherence to style standards**: Black formatting (Python) + Flake8 compliance mandatory
- **Type safety**: Full type hints required for all functions and modules
- **Cyclomatic complexity**: Functions MUST stay below 10 branches (justified exceptions tracked in code review)
- **Duplication**: DRY principle enforced—no copy-paste code allowed without refactoring
- **Documentation**: All public APIs require docstrings (following project conventions)

**Rationale**: Maintainability compounds. Poor code quality creates technical debt that compounds exponentially and slows future development. Consistent quality enables faster iteration and fewer bugs.

---

### II. Test-Driven Development (Non-Negotiable)

TDD is mandatory for all feature work. Workflow is strict Red-Green-Refactor:

1. **RED**: Write test(s) that FAIL on current code
2. **GREEN**: Implement minimum code to make test(s) PASS
3. **REFACTOR**: Improve code quality without breaking tests

Test types required by priority:
- **Unit tests** (MUST): Test individual functions/methods in isolation (target: >80% coverage)
- **Integration tests** (MUST for APIs/services): Test component interactions
- **Contract tests** (MUST for A2A skills): Validate skill input/output schemas match agent card
- **E2E tests** (SHOULD): Test full user workflows end-to-end

Tests MUST be written BEFORE implementation. No exceptions. All PRs must include test code and evidence of red-to-green cycle.

**Rationale**: Tests serve as executable specs. They catch regressions, enable refactoring with confidence, and document expected behavior.

---

### III. Performance & Observability

Every agent service MUST be measurable and performant:

**Performance Requirements**:
- Agent `/execute` endpoint: P95 latency <1000ms (excluding Claude API calls)
- Discovery queries: <200ms response time
- Registry operations (ORAS pull): <500ms
- Memory per agent instance: <200MB baseline
- CPU usage: No spinning threads—async/await mandatory

**Observability Requirements**:
- Structured logging required for all critical paths (skill execution, discovery, agent registration)
- All errors MUST include traceable request IDs or correlation IDs
- Metrics MUST be exported (Prometheus format preferred): execution time, error rates, skill latencies
- Health check endpoints required on all agents: `/health` → `{"status": "ok", "timestamp": "ISO8601"}`

**Rationale**: Deployed systems fail silently without observability. Performance degradation compounds user experience issues. Metrics enable proactive incident response.

---

### IV. UX Consistency & Accessibility

Agent outputs and CLI interactions MUST be consistent and predictable across the framework:

**JSON Response Consistency**:
- All skill responses MUST follow their published JSON Schema (from agent card)
- Error responses MUST include: `{"error": "code", "message": "description", "request_id": "..."}`
- Markdown code block wrapping for Claude responses MUST be robust (fallback to raw JSON parsing)

**CLI Output**:
- Human-readable output MUST include progress indicators for long-running tasks
- Machine-readable output (JSON) MUST support `--json` flag on all commands
- Help text MUST be auto-generated from agent card skill definitions
- Errors MUST suggest corrective actions (not just "failed")

**Accessibility**:
- All skill descriptions MUST be plain English (no jargon)
- Required vs. optional parameters MUST be clearly marked in input schemas
- Workflow examples MUST be provided in docs for all workflows

**Rationale**: Consistency reduces cognitive load. Users (and other agents) can predict system behavior. Poor UX leads to misconfigurations and support overhead.

---

### V. Versioning & Breaking Changes

Backward compatibility MUST be preserved or deliberately broken with clear process:

**Version Scheme**: MAJOR.MINOR.PATCH (semantic versioning)
- **MAJOR**: Breaking changes (e.g., agent skill removed, schema contract changed)
- **MINOR**: New features, new agents, new skills (backward compatible)
- **PATCH**: Bug fixes, performance improvements (no API changes)

**Breaking Change Process**:
1. MUST be documented in CHANGELOG before merge
2. MUST include migration guide for users
3. MUST be announced in release notes with deprecation timeline
4. Agent cards MUST include version (e.g., `plan_agent_v2`)
5. Workflows MUST support multiple versions during transition (e.g., `code-generation-v1` and `code-generation-v2` both available)

**Skill Schema Contract**:
- Input schemas are IMMUTABLE once published. New parameters are ADDITIONS ONLY.
- Output schemas are IMMUTABLE once published. New fields are ADDITIONS ONLY.
- Changing existing field type = MAJOR version bump

**Rationale**: Agents (and orchestrators) rely on published contracts. Breaking changes without notice cascade into production failures. Clear versioning enables graceful deprecation.

---

## Code Quality Standards

### Linting & Formatting

- **Black** (Python): Code MUST pass `uv run invoke lint.black-check`
- **Flake8**: Code MUST pass style checks—no E501 (line length) overrides without justification
- **Type hints**: `mypy` or equivalent strongly encouraged; all public APIs require hints
- Pre-commit hooks MUST enforce these before commit (no `--no-verify` bypasses)

### Test Coverage

- **Minimum**: 80% code coverage for src/ (measured by pytest-cov or similar)
- **Exceptions**: Require explicit justification and approval in code review
- **Coverage reports**: Generated in CI/CD; tracked per PR
- Integration and E2E tests MUST be included in coverage (not skipped)

### Code Review Requirements

- Minimum 1 approval required before merge (code owner or designated reviewer)
- Checklist items MUST include:
  - [ ] Tests present and comprehensive?
  - [ ] Code quality standards met (Black, Flake8, type hints)?
  - [ ] Documentation/docstrings updated?
  - [ ] Breaking changes? (If yes, version bump + migration guide required)
  - [ ] Performance impact assessed?

---

## Testing Requirements

### Test Organization

```
tests/
├── unit/           # Isolated function tests (no network/I/O)
├── integration/    # Component interaction tests
├── contract/       # A2A skill contract validation tests
├── api/            # HTTP endpoint tests
└── e2e/            # Full workflow tests (orchestrator → agents → results)
```

### Test Timing

- **Unit**: MUST run in <100ms per test
- **Integration**: MUST run in <500ms per test
- **Contract**: MUST run in <200ms per test (schema validation only)
- **E2E**: MAY exceed 5s per test; marked with `@pytest.mark.slow`

### Test Independence

- No test MAY depend on another test
- Each test MUST be runnable in isolation: `pytest tests/unit/test_X.py::test_foo`
- No shared mutable state between tests
- Fixtures MUST clean up after themselves (temp files, docker containers, etc.)

---

## Performance Baselines

### Agent Services

| Metric | Baseline | SLA |
|--------|----------|-----|
| Skill execution (P95) | <1000ms | Excluding Claude API call time |
| Agent startup | <2s | Cold start, all ports ready |
| Discovery query | <200ms | Registry available |
| Agent health check | <50ms | Should always be instant |

### Data Flow

| Operation | Baseline | Justification |
|-----------|----------|---|
| ORAS pull agent card | <500ms | Small JSON file, local network |
| Workflow YAML load | <100ms | Should be in-memory cached |
| JSON schema validation | <50ms | Schema validation is lightweight |

### Memory

| Component | Baseline | Trigger |
|-----------|----------|---------|
| Plan agent instance | <200MB | Investigate if exceeded |
| Build agent instance | <200MB | Investigate if exceeded |
| Test agent instance | <200MB | Investigate if exceeded |
| Registry container | <500MB | If exceeded, review workflow storage |

Baseline violations MUST be investigated in PRs. Document findings in commit message.

---

## Governance

### Constitution Authority

This constitution supersedes all other guidance and standards. When conflicts arise, constitution principles take precedence. All team members agree to uphold these principles.

### Amendment Process

1. **Propose**: Issue or PR with `[CONSTITUTION]` label includes proposed change + rationale
2. **Discuss**: Minimum 3-day discussion period for feedback
3. **Document**: Amendment includes migration plan (if affects existing work)
4. **Ratify**: Merged by repository maintainer with version bump (MAJOR/MINOR/PATCH per change)
5. **Communicate**: Release notes explain impact + any required actions

### Compliance Review

- **Per PR**: Code review includes constitution check (linting, tests, performance impact)
- **Per Release**: Changelog MUST link any broken principles to justifications + approval
- **Quarterly**: Team review of coverage metrics + identify systemic improvements

### Guidance References

- Runtime development guidance: See [CLAUDE.md](../../CLAUDE.md)
- Testing patterns: See [tests/README.md](../../tests/README.md)
- Workflow specifications: See [docs/WORKFLOW_ENGINE.md](../../docs/WORKFLOW_ENGINE.md)
- Agent patterns: See [src/agents/base.py](../../src/agents/base.py)

---

**Version**: 1.0.0 | **Ratified**: 2025-10-27 | **Last Amended**: 2025-10-27
