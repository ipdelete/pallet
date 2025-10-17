#!/bin/bash
set -e

agents=("plan" "build" "test")
registry="localhost:5000/agents"
verify_dir="tmp/registry-verify"

echo "=== Registry Verification Report ==="
echo

for agent in "${agents[@]}"; do
  echo "Verifying $agent agent..."

  # Pull
  oras pull "$registry/$agent:v1" -o "$verify_dir/" > /dev/null

  # Compare
  if diff -q "src/agent_cards/${agent}_agent_card.json" \
           "$verify_dir/${agent}_agent_card.json" > /dev/null; then
    echo "✓ $agent agent: Content verified"
  else
    echo "✗ $agent agent: Content mismatch"
    exit 1
  fi

  # Validate JSON
  if jq '.' "$verify_dir/${agent}_agent_card.json" > /dev/null 2>&1; then
    echo "✓ $agent agent: Valid JSON"
  else
    echo "✗ $agent agent: Invalid JSON"
    exit 1
  fi

  echo
done

echo "=== All agents verified successfully ==="
