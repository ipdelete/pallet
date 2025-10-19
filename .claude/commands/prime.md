---
description: List all tracked files and display README contents
model: claude-haiku-4-5
---

Run `git ls-files` to list all tracked files in the repository, then read and display the README file contents.
Run `uv run invoke --list` to list all tasks available for tests and lints.

## Report

After gathering information, display a structured summary with these sections:

### Tracked Files
- Count total tracked files
- Break down by category:
  - Configuration files
  - Source code (agents, orchestration, discovery)
  - Tests (unit, integration, API, fixtures)
  - Documentation (specs, guides, README)
  - Scripts and utilities

### Repository Structure
- List key directories and their purposes
- Highlight main entry points (`main.py`, `orchestrator.py`)

### Available Tasks
- **Linting & Code Quality**: black formatting, flake8 checking
- **Testing Categories**: unit, integration, API, coverage reports
- **Debug Options**: verbose, debug mode, show output

### Project Overview
- Framework name and purpose (A2A Agent Framework)
- Architecture: Plan → Build → Test pipeline
- Key technologies: FastAPI, JSON-RPC 2.0, OCI Registry
- Dynamic agent discovery mechanism

### Quick Reference
- Bootstrap command
- Run orchestrator command
- Tear down command
- Important environment variables