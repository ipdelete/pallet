"""Invoke tasks for testing, linting, and formatting.

Run tasks with: invoke TASK_NAME

Test Examples:
    invoke test              # Run all tests
    invoke test.unit        # Run unit tests only
    invoke test.coverage    # Generate HTML coverage report
    invoke test.debug       # Run with debugger on failure
    invoke test.verbose     # Verbose output

Linting Examples:
    invoke lint.flake8      # Check code style with flake8
    invoke lint.black       # Format code with black
    invoke lint.black-check # Check if code needs formatting
"""

from invoke import Collection, task


@task(help={"verbose": "Show verbose output"})
def test(ctx, verbose=False):
    """Run all tests (default: skip slow and e2e tests)."""
    cmd = "uv run pytest"
    if verbose:
        cmd += " -v"
    ctx.run(cmd)


@task
def verbose(ctx):
    """Run all tests with verbose output."""
    ctx.run("uv run pytest -v")


@task
def show_output(ctx):
    """Run tests and show print statements."""
    ctx.run("uv run pytest -s")


@task
def unit(ctx):
    """Run unit tests only."""
    ctx.run("uv run pytest -m unit")


@task
def integration(ctx):
    """Run integration tests only."""
    ctx.run("uv run pytest -m integration")


@task
def api(ctx):
    """Run API endpoint tests only."""
    ctx.run("uv run pytest -m api")


@task
def skip_slow(ctx):
    """Run tests excluding slow tests."""
    ctx.run('uv run pytest -m "not slow"')


@task
def skip_e2e(ctx):
    """Run tests excluding end-to-end tests (default behavior)."""
    ctx.run('uv run pytest -m "not e2e"')


@task
def unit_integration(ctx):
    """Run unit and integration tests, excluding slow tests."""
    ctx.run('uv run pytest -m "(unit or integration) and not slow"')


@task(help={"file": "Specific test file to run", "name": "Test name or pattern"})
def specific(ctx, file=None, name=None):
    """Run specific test file, class, or function.

    Examples:
        invoke test.specific --file tests/unit/test_base_agent.py
        invoke test.specific --file tests/unit/test_base_agent.py --name TestAgentCardEndpoint
        invoke test.specific --name test_get_agent_card
    """
    if not file and not name:
        print("Error: Please specify --file and/or --name")
        return

    cmd = "uv run pytest"
    if file:
        cmd += f" {file}"
    if name:
        cmd += f"::{name}"

    ctx.run(cmd)


# Coverage tasks
@task
def coverage_html(ctx):
    """Generate HTML coverage report in htmlcov/ directory."""
    ctx.run("uv run pytest --cov=src --cov-report=html")
    print("\n✓ Coverage report generated in htmlcov/index.html")


@task
def coverage_term(ctx):
    """Display coverage report in terminal with missing lines."""
    ctx.run("uv run pytest --cov=src --cov-report=term-missing")


@task
def coverage_xml(ctx):
    """Generate XML coverage report (for CI)."""
    ctx.run("uv run pytest --cov=src --cov-report=xml")
    print("\n✓ Coverage report generated in coverage.xml")


@task
def coverage(ctx):
    """Generate all coverage reports (HTML, terminal, and XML)."""
    ctx.run("uv run pytest --cov=src --cov-report=html --cov-report=term-missing --cov-report=xml")
    print("\n✓ Coverage reports generated:")
    print("  - htmlcov/index.html (HTML)")
    print("  - Terminal output above")
    print("  - coverage.xml (XML for CI)")


# Debug tasks
@task
def debug(ctx):
    """Run tests with debugger (pdb) on failure."""
    ctx.run("uv run pytest --pdb")


@task
def long_traceback(ctx):
    """Run tests with long traceback output."""
    ctx.run("uv run pytest --tb=long")


@task
def stop_first_failure(ctx):
    """Stop at first test failure."""
    ctx.run("uv run pytest -x")


@task
def show_locals(ctx):
    """Run tests showing local variables in traceback."""
    ctx.run("uv run pytest -l")


# Logging tasks
@task
def debug_logs(ctx):
    """Run tests with debug-level logging."""
    ctx.run("uv run pytest --log-cli-level=DEBUG")


@task(help={"pattern": "Test name or pattern to filter"})
def debug_specific(ctx, pattern):
    """Run specific test with debug logging.

    Example:
        invoke test.debug-specific --pattern test_get_agent_card
    """
    ctx.run(f'uv run pytest --log-cli-level=DEBUG -k {pattern}')


# Combined test suites
@task
def all_with_coverage(ctx):
    """Run all tests with coverage report."""
    ctx.run("uv run pytest --cov=src --cov-report=term-missing")


@task
def ci(ctx):
    """Run all tests as if in CI (with XML coverage)."""
    ctx.run("uv run pytest --cov=src --cov-report=xml")


# Linting tasks
@task(help={"src": "Path to check (default: src)"})
def flake8(ctx, src="src"):
    """Run flake8 style checker.

    Example:
        invoke lint.flake8
        invoke lint.flake8 --src src/agents
    """
    ctx.run(f"uv run flake8 {src}")


@task(help={"check": "Check only, don't modify files"})
def black(ctx, check=False):
    """Format code with black.

    Example:
        invoke lint.black           # Format files
        invoke lint.black --check   # Check only
    """
    cmd = "uv run black src tests main.py"
    if check:
        cmd += " --check"
    ctx.run(cmd)


@task
def black_check(ctx):
    """Check if code needs black formatting."""
    ctx.run("uv run black src tests main.py --check")


# Namespace for tests
test_ns = Collection("test")
test_ns.add_task(test, default=True)
test_ns.add_task(verbose)
test_ns.add_task(show_output)
test_ns.add_task(unit)
test_ns.add_task(integration)
test_ns.add_task(api)
test_ns.add_task(skip_slow)
test_ns.add_task(skip_e2e)
test_ns.add_task(unit_integration)
test_ns.add_task(specific)
test_ns.add_task(coverage_html)
test_ns.add_task(coverage_term)
test_ns.add_task(coverage_xml)
test_ns.add_task(coverage)
test_ns.add_task(debug)
test_ns.add_task(long_traceback)
test_ns.add_task(stop_first_failure)
test_ns.add_task(show_locals)
test_ns.add_task(debug_logs)
test_ns.add_task(debug_specific)
test_ns.add_task(all_with_coverage)
test_ns.add_task(ci)

# Namespace for linting
lint_ns = Collection("lint")
lint_ns.add_task(flake8)
lint_ns.add_task(black)
lint_ns.add_task(black_check)

# Register namespaces at module level for invoke to discover
ns = Collection(test_ns, lint_ns)
