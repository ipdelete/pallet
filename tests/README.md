# Pallet Test Suite

Comprehensive test coverage for the Pallet A2A agent orchestration framework.

## Quick Start with Invoke (Recommended)

The project uses [Invoke](https://www.pyinvoke.org/) for convenient test and linting task management:

```bash
# Install test dependencies (includes invoke)
uv sync --extra test

# List all available tasks
uv run invoke --list

# Code Quality & Linting
uv run invoke lint.black             # Format code with black
uv run invoke lint.black-check       # Check if formatting is needed
uv run invoke lint.flake8            # Run flake8 style checker

# Run all tests (default)
uv run invoke test

# Run specific test categories
uv run invoke test.unit              # Unit tests only
uv run invoke test.integration       # Integration tests only
uv run invoke test.api               # API endpoint tests only

# Coverage reports
uv run invoke test.coverage-html     # Generate HTML coverage report
uv run invoke test.coverage-term     # Show coverage in terminal
uv run invoke test.coverage-xml      # Generate XML coverage (for CI)
uv run invoke test.coverage          # All three formats

# Debugging
uv run invoke test.debug             # Drop into debugger on failure
uv run invoke test.verbose           # Verbose output
```

## Direct pytest Commands

You can also run pytest directly:

```bash
# Install test dependencies
uv sync --extra test

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test categories
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m api          # API endpoint tests only
uv run pytest -m "not e2e"    # Skip end-to-end tests (default)
uv run pytest -m "not slow"   # Skip slow tests
```

## Test Structure

```
tests/
├── unit/                           # Unit tests for individual components
│   ├── test_models.py             # Pydantic model validation tests
│   ├── test_base_agent.py         # BaseAgent class tests
│   ├── test_plan_agent.py         # Plan Agent tests
│   ├── test_build_agent.py        # Build Agent tests
│   ├── test_test_agent.py         # Test Agent (reviewer) tests
│   ├── test_discovery.py          # Discovery module tests
│   └── test_orchestrator.py       # Orchestrator logic tests
├── integration/                    # Integration tests
│   ├── test_agent_communication.py # A2A protocol tests
│   └── test_end_to_end.py         # Full pipeline tests
├── api/                           # API endpoint tests
│   └── test_endpoints.py          # FastAPI route tests
├── fixtures/                      # Shared test fixtures
│   ├── conftest.py               # Pytest fixtures
│   └── sample_data.py            # Test data constants
└── README.md                      # This file
```

## Test Categories

### Unit Tests (`-m unit`)

Test individual components in isolation with mocked dependencies.

**test_models.py**:
- Pydantic model validation (Message, SkillDefinition, AgentCard)
- Required field validation
- Type checking

**test_base_agent.py**:
- BaseAgent initialization
- FastAPI route setup
- `/agent-card` endpoint
- `/execute` endpoint
- Claude CLI integration (mocked)
- Agent-to-agent communication (mocked)
- JSON parsing robustness

**test_plan_agent.py**:
- Plan Agent initialization and configuration
- `create_plan` skill execution
- Requirements validation
- JSON response parsing
- Error handling

**test_build_agent.py**:
- Build Agent initialization and configuration
- `generate_code` skill execution
- Plan parameter handling (dict and string)
- Code generation output validation
- Error handling

**test_test_agent.py**:
- Test Agent initialization and configuration
- `review_code` skill execution
- Code quality scoring
- Multi-language support
- Review output validation

**test_discovery.py**:
- Registry catalog listing
- Agent card retrieval via ORAS
- Agent discovery by skill
- Caching behavior
- Convenience function wrappers

**test_orchestrator.py**:
- Orchestration pipeline flow
- Agent skill calls
- Data chaining (Plan → Build → Test)
- File output generation
- Metadata creation

### Integration Tests (`-m integration`)

Test component interactions with mocked external dependencies.

**test_agent_communication.py**:
- A2A protocol JSON-RPC messaging
- Agent-to-agent skill calls
- Multi-agent pipeline flow
- Error propagation
- Timeout handling

**test_end_to_end.py**:
- Full orchestration workflow
- Discovery integration
- Data flow validation
- Output file verification
- Error scenario handling

### API Tests (`-m api`)

Test FastAPI endpoints across all agents.

**test_endpoints.py**:
- Common endpoint structure
- JSON-RPC 2.0 compliance
- Agent card validation
- Skill schema verification
- Error response format

## Test Markers

Tests are marked for selective execution:

- `@pytest.mark.unit` - Unit tests (default)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.e2e` - End-to-end tests (require services)
- `@pytest.mark.slow` - Slow-running tests

## Invoke Tasks Reference

### Linting & Code Quality

| Task | Command | Purpose |
|------|---------|---------|
| Format code | `uv run invoke lint.black` | Format code with black formatter |
| Check formatting | `uv run invoke lint.black-check` | Check if code needs black formatting |
| Style check | `uv run invoke lint.flake8` | Run flake8 style checker |

### Common Test Tasks

| Task | Command | Purpose |
|------|---------|---------|
| Default (all tests) | `uv run invoke test` | Run all tests excluding slow and e2e |
| Unit tests | `uv run invoke test.unit` | Unit tests only |
| Integration tests | `uv run invoke test.integration` | Integration tests only |
| API tests | `uv run invoke test.api` | API endpoint tests only |
| Verbose output | `uv run invoke test.verbose` | Show verbose test output |
| Show prints | `uv run invoke test.show-output` | Display print statements during tests |

### Coverage Tasks

| Task | Command | Purpose |
|------|---------|---------|
| HTML coverage | `uv run invoke test.coverage-html` | Generate HTML report in `htmlcov/` |
| Terminal coverage | `uv run invoke test.coverage-term` | Show coverage with missing lines |
| XML coverage | `uv run invoke test.coverage-xml` | Generate XML for CI systems |
| All coverage | `uv run invoke test.coverage` | Generate all three formats |
| With coverage | `uv run invoke test.all-with-coverage` | Run tests with coverage display |

### Debug & Troubleshooting Tasks

| Task | Command | Purpose |
|------|---------|---------|
| Debugger mode | `uv run invoke test.debug` | Drop into pdb on test failure |
| Long traceback | `uv run invoke test.long-traceback` | Show full traceback output |
| Stop first failure | `uv run invoke test.stop-first-failure` | Stop at first failing test |
| Show locals | `uv run invoke test.show-locals` | Display local variables in traceback |
| Debug logs | `uv run invoke test.debug-logs` | Show DEBUG-level log output |

### Specialized Runs

| Task | Command | Purpose |
|------|---------|---------|
| Skip slow | `uv run invoke test.skip-slow` | Exclude slow-running tests |
| Skip e2e | `uv run invoke test.skip-e2e` | Exclude end-to-end tests |
| Unit + Integration | `uv run invoke test.unit-integration` | Run unit and integration, skip slow |
| CI mode | `uv run invoke test.ci` | Run all tests with XML coverage for CI |

### Running Specific Tests

```bash
# Run specific test file
uv run invoke test.specific --file tests/unit/test_base_agent.py

# Run specific test class
uv run invoke test.specific --file tests/unit/test_base_agent.py --name TestAgentCardEndpoint

# Run specific test function
uv run invoke test.specific --name test_get_agent_card

# Run tests matching pattern with debug logs
uv run invoke test.debug-specific --pattern test_get_agent_card
```

## Running Tests

### Basic Commands (Direct pytest)

```bash
# Run all tests (excluding slow and e2e by default)
uv run pytest

# Verbose output
uv run pytest -v

# Show print statements
uv run pytest -s

# Run specific file
uv run pytest tests/unit/test_base_agent.py

# Run specific test class
uv run pytest tests/unit/test_base_agent.py::TestAgentCardEndpoint

# Run specific test function
uv run pytest tests/unit/test_base_agent.py::TestAgentCardEndpoint::test_get_agent_card
```

### Coverage Reports

```bash
# Generate HTML coverage report
uv run pytest --cov=src --cov-report=html

# View coverage in terminal
uv run pytest --cov=src --cov-report=term-missing

# Generate XML coverage (for CI)
uv run pytest --cov=src --cov-report=xml
```

### Filtered Runs

```bash
# Only unit tests
uv run pytest -m unit

# Only integration tests
uv run pytest -m integration

# Only API tests
uv run pytest -m api

# Skip slow tests
uv run pytest -m "not slow"

# Skip end-to-end tests
uv run pytest -m "not e2e"

# Unit and integration, but not slow
uv run pytest -m "(unit or integration) and not slow"
```

## Test Fixtures

### Global Fixtures (tests/fixtures/conftest.py)

Available to all tests:

- `event_loop` - Async event loop for async tests
- `sample_skill` - Sample SkillDefinition
- `sample_requirements` - Sample user requirements
- `sample_plan` - Sample plan output
- `sample_code` - Sample code output
- `sample_code_result` - Sample code generation result
- `sample_review` - Sample code review
- `sample_agent_card` - Sample agent card
- `mock_claude_response` - Mocked Claude CLI response
- `mock_subprocess` - Mocked subprocess for Claude calls
- `mock_httpx_client` - Mocked HTTP client
- `mock_registry_response` - Mocked OCI registry response

### Sample Data (tests/fixtures/sample_data.py)

Constant test data:

- JSON-RPC messages and responses
- Agent cards for all agents
- Sample requirements, plans, code, reviews
- Claude response formats (wrapped JSON, plain JSON)

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestYourComponent:
    """Tests for YourComponent."""

    @pytest.fixture
    def component(self):
        """Create component instance."""
        return YourComponent()

    def test_initialization(self, component):
        """Test component initialization."""
        assert component.property == expected_value

    @pytest.mark.asyncio
    async def test_async_method(self, component):
        """Test async method."""
        with patch.object(component, 'dependency', new=AsyncMock()):
            result = await component.async_method()
            assert result == expected
```

### Integration Test Template

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.integration
class TestComponentIntegration:
    """Integration tests for component interactions."""

    @pytest.mark.asyncio
    async def test_integration_flow(self):
        """Test integration between components."""
        # Setup
        component_a = ComponentA()
        component_b = ComponentB()

        # Execute
        result = await component_a.call(component_b)

        # Verify
        assert result.matches_expected()
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync --extra test
      - name: Run tests
        run: uv run pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Debugging Tests

### Failed Test Debugging

```bash
# Show full traceback
uv run pytest --tb=long

# Drop into debugger on failure
uv run pytest --pdb

# Stop at first failure
uv run pytest -x

# Show local variables in traceback
uv run pytest -l
```

### Logging

```bash
# Show all log output
uv run pytest --log-cli-level=DEBUG

# Show specific logger
uv run pytest --log-cli-level=DEBUG -k test_name
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Mocking**: Mock external dependencies (Claude CLI, HTTP, subprocess)
3. **Fixtures**: Use fixtures for common setup
4. **Async**: Use `@pytest.mark.asyncio` for async tests
5. **Markers**: Mark tests appropriately (unit, integration, slow, e2e)
6. **Names**: Use descriptive test names that explain what's being tested
7. **Arrange-Act-Assert**: Follow AAA pattern in tests
8. **DRY**: Extract common patterns into fixtures or helper functions

## Coverage Goals

- **Overall**: > 80%
- **Critical paths**: > 90%
  - BaseAgent class
  - Agent skill execution
  - Orchestrator flow
  - Discovery module
- **Nice to have**: > 70%
  - CLI utilities
  - Helper functions

## Troubleshooting

### ImportError: No module named 'src'

```bash
# Ensure you're in the project root
cd /path/to/pallet

# Run pytest from project root
uv run pytest
```

### Async tests not running

```bash
# Install pytest-asyncio
uv sync --extra test

# Verify asyncio_mode in pytest.ini
cat pytest.ini | grep asyncio_mode
```

### Fixtures not found

```bash
# Ensure conftest.py is in tests/fixtures/
ls tests/fixtures/conftest.py

# Check import paths are correct
```

## Further Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-Asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
