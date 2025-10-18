---
description: Review work done against a specification file
model: claude-haiku-4-5-20251001
---

Follow the `Instructions` below to **review work done against a specification file** (specs/*.md) to ensure implemented features match requirements for the Pallet A2A Agent Framework.

## Variables

spec_file: $1

## Instructions

- Check current git branch using `git branch` to understand context (e.g., feature/workflow, feat/orchestrator)
- Run `git diff origin/master` to see all changes made in current branch. Continue even if there are no changes.
- Identify the spec file by looking for specs/*.md files that match the current branch name or feature area
- Read the identified spec file to understand requirements for workflow engine, agents, orchestration, or discovery components
- Review the implementation:
  - Check that agent implementations match the spec (Plan, Build, Test agents)
  - Verify orchestrator integration follows the spec (pipeline ordering, error handling)
  - Ensure data models and context structures match spec requirements
  - Validate JSON-RPC communication patterns are correctly implemented
  - Confirm registry discovery logic matches spec expectations
- IMPORTANT: Code Review Focus Areas:
  - Agent skills match spec input/output schemas
  - Error handling and edge cases are addressed
  - JSON response parsing is robust (handles markdown wrapping)
  - Port configuration and service discovery align with spec
  - Test coverage for new functionality
  - Documentation matches implementation

## Report

- IMPORTANT: Return results exclusively as a JSON array based on the `Output Structure` section below.
- `success` should be `true` if there are NO BLOCKING issues (implementation matches spec for all critical paths)
- `success` should be `false` ONLY if there are BLOCKING issues that prevent the work from being released
- `review_issues` can contain issues of any severity (skippable, tech_debt, or blocker)
- `screenshots` should contain paths to relevant code files or documentation (use full absolute paths)

### Output Structure

```json
{
    "success": "boolean - true if there are NO BLOCKING issues, false if there are BLOCKING issues",
    "review_summary": "string - 2-4 sentences describing what was implemented and whether it matches the spec. Written as if reporting during a standup meeting. Example: 'The workflow engine Phase 2 implementation includes dynamic agent discovery and orchestrator integration. The implementation matches all spec requirements for JSON-RPC communication, error handling, and service registry interactions. All agents correctly expose skill definitions and handle parameter validation.'",
    "review_issues": [
        {
            "review_issue_number": "number - the issue number based on the index",
            "code_location": "string - file_path:line_number where issue is found",
            "issue_description": "string - description of the issue",
            "issue_resolution": "string - description of the resolution",
            "issue_severity": "string - 'skippable', 'tech_debt', or 'blocker'"
        }
    ],
    "files_changed": "string - output of git diff --stat showing files and lines changed",
    "spec_file_reviewed": "string - path to the spec file that was reviewed"
}
```

## Issue Severity Guidelines

- `skippable` - Non-blocker issue; feature can be released but should be addressed later
- `tech_debt` - Non-blocker; creates technical debt that should be addressed in future iterations
- `blocker` - Feature cannot be released; breaks functionality or fails to meet spec requirements
