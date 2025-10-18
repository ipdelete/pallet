---
description: Complete pre-flight checks and ship code changes (lint, test, secrets check, commit, push)
---

## Ship Command: Pre-flight & Deploy Workflow

Run comprehensive pre-flight checks, verify the repository is ready for deployment, and push changes.

### Step 1: Determine Current Branch & Base Branch

First, show the current branch and what it was branched from:

```bash
git branch -vv
git log --oneline --graph --all --decorate -20
```

### Step 2: Run Code Quality Checks

Run linting and tests using invoke:

```bash
uv run invoke lint.black-check
uv run invoke lint.flake8
uv run invoke test
```

### Step 3: Verify No Secrets

Scan for potential secrets (common patterns):

```bash
# Check for common secret patterns
git diff HEAD --cached | grep -E '(ANTHROPIC_API_KEY|password|secret|token|key.*=)' && echo "⚠️  WARNING: Possible secrets detected in staged changes" || echo "✅ No obvious secrets detected"

# Check for untracked files that might contain secrets
ls -la | grep -E '(\.env|credentials|secrets|\.key)' && echo "⚠️  WARNING: Potential secret files in working directory" || echo "✅ No obvious secret files detected"
```

### Step 4: Verify Git Status & .gitignore

Check if .gitignore needs updating and repo is in a good state:

```bash
git status
git check-ignore -v * 2>/dev/null | head -20 || echo "✅ .gitignore check complete"
```

### Step 5: Review Changes to Commit

Show what will be committed:

```bash
git diff HEAD
```

### Step 6: Stage All Changes

```bash
git add .
```

### Step 7: Create & Execute Commit

Review staged changes and create a descriptive commit message based on the changes. The message should follow conventional commits format (feat, fix, docs, refactor, test, chore, etc.).

After reviewing the diffs and understanding what's being committed, create a commit with an appropriate message.

### Step 8: Push to Remote

```bash
git push
```

Push the committed changes to the remote repository.

---

## Step 9: Generate Deployment Report

After all steps complete successfully, generate a comprehensive report:

```bash
echo "=== 📊 SHIP DEPLOYMENT REPORT ==="
echo ""
echo "=== Git Statistics ==="
echo "Current branch:"
git rev-parse --abbrev-ref HEAD
echo ""
echo "Commits since last tag:"
git rev-list --count $(git describe --tags --abbrev=0)..HEAD 2>/dev/null || git rev-list --count HEAD
echo ""
echo "Last 5 commits:"
git log --oneline -5
echo ""
echo "Files changed in this push:"
git diff $(git merge-base HEAD origin/$(git rev-parse --abbrev-ref HEAD))..HEAD --name-status | head -20
echo ""
echo "Lines added/deleted:"
git diff $(git merge-base HEAD origin/$(git rev-parse --abbrev-ref HEAD))..HEAD --stat | tail -1
echo ""
echo "=== Actions Completed ==="
echo "✅ Code quality checks passed (black, flake8)"
echo "✅ All tests passed"
echo "✅ No secrets detected in changes"
echo "✅ .gitignore verified"
echo "✅ Repository state verified clean"
echo "✅ Changes staged and committed"
echo "✅ Changes pushed to remote"
echo ""
echo "=== Deployment Summary ==="
git log -1 --format="Commit: %H%nAuthor: %an <%ae>%nDate: %ad%nMessage:%n%B" --date=short
echo "=== 🎉 READY TO SHIP ==="
```

---

## Pre-flight Verification Checklist

Before shipping, ensure:
- ✅ Linting passes (black-check, flake8)
- ✅ All tests pass
- ✅ No secrets in changes
- ✅ .gitignore is properly configured
- ✅ Repository is in clean state (no merge conflicts, etc.)
- ✅ Meaningful commit message
- ✅ Ready to push

If any step fails, stop and fix the issue before proceeding.
