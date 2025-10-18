# Pallet Test Suite

Comprehensive test coverage for the Pallet A2A agent orchestration framework.

## Quick Start

```bash
# Install test dependencies
uv sync --extra test

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m api          # API endpoint tests only
pytest -m "not e2e"    # Skip end-to-end tests (default)
pytest -m "not slow"   # Skip slow tests
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

## Running Tests

### Basic Commands

```bash
# Run all tests (excluding slow and e2e by default)
pytest

# Verbose output
pytest -v

# Show print statements
pytest -s

# Run specific file
pytest tests/unit/test_base_agent.py

# Run specific test class
pytest tests/unit/test_base_agent.py::TestAgentCardEndpoint

# Run specific test function
pytest tests/unit/test_base_agent.py::TestAgentCardEndpoint::test_get_agent_card
```

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage in terminal
pytest --cov=src --cov-report=term-missing

# Generate XML coverage (for CI)
pytest --cov=src --cov-report=xml
```

### Filtered Runs

```bash
# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# Only API tests
pytest -m api

# Skip slow tests
pytest -m "not slow"

# Skip end-to-end tests
pytest -m "not e2e"

# Unit and integration, but not slow
pytest -m "(unit or integration) and not slow"
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
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Debugging Tests

### Failed Test Debugging

```bash
# Show full traceback
pytest --tb=long

# Drop into debugger on failure
pytest --pdb

# Stop at first failure
pytest -x

# Show local variables in traceback
pytest -l
```

### Logging

```bash
# Show all log output
pytest --log-cli-level=DEBUG

# Show specific logger
pytest --log-cli-level=DEBUG -k test_name
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
pytest
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
