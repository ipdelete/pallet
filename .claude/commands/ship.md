---
description: Complete pre-flight checks and ship code changes (lint, test, secrets check, commit, push)
---

## Ship Command: Pre-flight & Deploy Workflow

Run comprehensive pre-flight checks, verify the repository is ready for deployment, and push changes.

## Workflow Steps

### Step 1: Verify Git Status

Execute these git commands to understand current state:
- `git branch -vv` - Show current branch and tracking status
- `git log --oneline --graph --all --decorate -20` - Show recent commit history

### Step 2: Run Code Quality Checks

Execute invoke tasks for code quality:
- `uv run invoke lint.black-check` - Verify black formatting
- `uv run invoke lint.flake8` - Run flake8 style checks
- `uv run invoke test` - Run all tests

### Step 3: Verify No Secrets

Scan for potential secrets in staged changes and working directory:
- Check for common secret patterns: `ANTHROPIC_API_KEY`, `password`, `secret`, `token`, `key=`
- Check for untracked secret files: `.env`, `credentials`, `secrets`, `.key`

### Step 4: Review Changes

Show all changes that will be committed:
- Execute `git diff HEAD` to see all modifications
- Ensure changes align with intended scope

### Step 5: Stage Changes

- Execute `git add .` to stage all changes

### Step 6: Create Commit

Review staged changes and create a descriptive commit message following conventional commits format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `refactor:` for code refactoring
- `test:` for test additions/changes
- `chore:` for maintenance tasks

### Step 7: Push to Remote

- Execute `git push` to push committed changes

---

## Deployment Report

After all steps complete successfully, display a comprehensive report with these sections:

### Git Statistics
- Current branch name
- Commits since last tag
- Last 5 commits (oneline format)
- Files changed in this push
- Lines added/deleted summary

### Actions Completed
- ✅ Code quality checks passed (black, flake8)
- ✅ All tests passed
- ✅ No secrets detected in changes
- ✅ .gitignore verified
- ✅ Repository state verified clean
- ✅ Changes staged and committed
- ✅ Changes pushed to remote

### Deployment Summary
- Full commit hash
- Author name and email
- Commit date
- Full commit message

---

## Pre-flight Verification Checklist

Before shipping, ensure:
- ✅ Linting passes (black-check, flake8)
- ✅ All tests pass
- ✅ No secrets detected in changes
- ✅ .gitignore is properly configured
- ✅ Repository is in clean state (no merge conflicts, etc.)
- ✅ Meaningful commit message
- ✅ Ready to push

If any step fails, stop and fix the issue before proceeding.
