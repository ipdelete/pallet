#!/bin/bash

set -e

echo "=========================================="
echo "Pushing Workflows to Registry"
echo "=========================================="

# Check if ORAS is installed
if ! command -v oras &> /dev/null; then
    echo "✗ ORAS not found. Installing..."
    bash scripts/install-oras.sh
fi

# Check if registry is running
echo "→ Checking registry status..."
if ! curl -s http://localhost:5000/v2/ > /dev/null; then
    echo "✗ Registry not running at localhost:5000"
    echo "  Start registry with: bash scripts/bootstrap.sh"
    exit 1
fi
echo "✓ Registry is running"

# Push workflows
WORKFLOWS_DIR="workflows"

if [ ! -d "$WORKFLOWS_DIR" ]; then
    echo "✗ Workflows directory not found: $WORKFLOWS_DIR"
    echo "  Run this script from the project root"
    exit 1
fi

# Find all YAML workflow files
WORKFLOW_FILES=$(find "$WORKFLOWS_DIR" -name "*.yaml" -o -name "*.yml")

if [ -z "$WORKFLOW_FILES" ]; then
    echo "⚠ No workflow files found in $WORKFLOWS_DIR"
    exit 0
fi

echo ""
echo "→ Pushing workflows to registry..."

for workflow_file in $WORKFLOW_FILES; do
    # Extract workflow ID from filename (e.g., code-generation.yaml -> code-generation)
    filename=$(basename "$workflow_file")
    workflow_id="${filename%.*}"

    echo "  → Pushing $workflow_id..."

    if oras push "localhost:5000/workflows/$workflow_id:v1" \
        "$workflow_file:application/yaml" > /dev/null 2>&1; then
        echo "    ✓ Pushed workflows/$workflow_id:v1"
    else
        echo "    ✗ Failed to push $workflow_id"
    fi
done

echo ""
echo "→ Listing all workflows in registry..."
curl -s http://localhost:5000/v2/_catalog | jq '.repositories | map(select(startswith("workflows/")))' || echo "  (jq not installed, skipping formatted output)"

echo ""
echo "✓ Workflow push complete"
echo "=========================================="
