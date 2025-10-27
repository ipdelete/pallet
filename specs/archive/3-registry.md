# Phase 3: Registry Operations (30 min)

## Overview

Phase 3 establishes persistent storage for agent cards using an OCI-compliant registry. Instead of agents only exposing their capabilities through HTTP endpoints, Phase 3 enables agent discovery through artifact registry storage. Each agent card is published to a Docker registry running on localhost:5000 using ORAS (OCI Registry as Storage), allowing agent cards to be versioned, pulled, and verified independently of running agent instances.

## Prerequisites

- **Registry Running**: Docker registry listening on `localhost:5000`
- **ORAS Installed**: OCI Registry as Storage CLI tool for pushing/pulling artifacts
- **Phase 2 Completed**: Three agents and their agent cards exist from Phase 2
- **Agent Cards Prepared**: JSON files available in `src/agent_cards/`

Install ORAS if needed:
```bash
# macOS
brew install oras

# Linux (using curl)
curl -L https://github.com/oras-project/oras/releases/download/v1.0.0/oras_1.0.0_linux_amd64.tar.gz | tar xz
sudo mv oras /usr/local/bin/

# Or use Go
go install oras.land/oras@latest
```

## Architecture: OCI Registry Concepts

### Registry Structure

The OCI registry uses a hierarchical namespace structure:
```
registry/
  repository-name/
    artifact:tag
```

For agent cards, the structure is:
```
localhost:5000/
  agents/
    plan:v1
    plan:v2
    build:v1
    test:v1
```

### Agent Card Artifacts

Each agent card is stored as an OCI artifact containing:
- **Media Type**: `application/json`
- **Reference Format**: `localhost:5000/agents/{agent-name}:{version}`
- **Content**: JSON describing agent capabilities, skills, and endpoints

## 3.1 Publish Agent Cards

### Step 1: Locate Existing Agent Cards

Agent cards from Phase 2 are stored in the project:
```
src/agent_cards/
├── plan_agent_card.json
├── build_agent_card.json
└── test_agent_card.json
```

Each file contains the agent's capabilities specification:
```json
{
  "name": "plan-agent",
  "url": "http://localhost:8001",
  "version": "1.0.0",
  "skills": [
    {
      "id": "create_plan",
      "description": "Creates structured implementation plans from requirements",
      "input_schema": {...},
      "output_schema": {...}
    }
  ]
}
```

### Step 2: Push Plan Agent Card

Publish the Plan Agent card to the registry:

```bash
cd src/agent_cards

oras push localhost:5000/agents/plan:v1 plan_agent_card.json
```

Expected output:
```
Uploading agent_card.json
Uploaded agent_card.json
Pushed [registry] localhost:5000/agents/plan:v1
Digest: sha256:abc123def456...
```

The registry creates:
- **Repository**: `localhost:5000/agents/plan`
- **Tag**: `v1`
- **Digest**: Content hash (e.g., `sha256:abc123def456...`)

### Step 3: Push Build Agent Card

```bash
oras push localhost:5000/agents/build:v1 build_agent_card.json
```

### Step 4: Push Test Agent Card

```bash
oras push localhost:5000/agents/test:v1 test_agent_card.json
```

### All Agents Summary

After completing all three pushes, the registry contains:

| Repository | Tag | Digest | Status |
|-----------|-----|--------|--------|
| `localhost:5000/agents/plan` | `v1` | `sha256:abc...` | Published |
| `localhost:5000/agents/build` | `v1` | `sha256:def...` | Published |
| `localhost:5000/agents/test` | `v1` | `sha256:ghi...` | Published |

## 3.2 Verify Storage

### Step 1: List Registry Contents

#### List all repositories:
```bash
oras repo list localhost:5000
```

Expected output:
```
agents/plan
agents/build
agents/test
```

#### List all tags in a specific repository:
```bash
oras repo tags localhost:5000/agents/plan
```

Expected output:
```
v1
```

#### Get detailed information about an artifact:
```bash
oras manifest fetch localhost:5000/agents/plan:v1
```

Expected output (manifest):
```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oras.artifact.manifest.v1+json",
  "config": {
    "size": 1024,
    "digest": "sha256:..."
  },
  "layers": [
    {
      "mediaType": "application/json",
      "size": 1024,
      "digest": "sha256:..."
    }
  ]
}
```

### Step 2: Pull Agent Cards Back

Pull the Plan Agent card from the registry:

```bash
mkdir -p tmp/registry-verify

oras pull localhost:5000/agents/plan:v1 -o tmp/registry-verify/
```

Expected output:
```
Downloading agent_card.json
Downloaded agent_card.json
Pulled successfully
```

Repeat for Build and Test agents:
```bash
oras pull localhost:5000/agents/build:v1 -o tmp/registry-verify/
oras pull localhost:5000/agents/test:v1 -o tmp/registry-verify/
```

### Step 3: Confirm Content Matches

#### Compare file sizes:
```bash
ls -lh src/agent_cards/*.json
ls -lh tmp/registry-verify/*.json
```

Both sets should show identical sizes.

#### Compare file contents using diff:
```bash
diff src/agent_cards/plan_agent_card.json tmp/registry-verify/plan_agent_card.json
```

No output indicates files are identical (exit code 0).

#### Validate JSON structure of pulled artifacts:
```bash
jq '.' tmp/registry-verify/plan_agent_card.json > /dev/null && echo "Valid JSON"
```

#### Compare JSON content ignoring formatting:
```bash
jq -S '.' src/agent_cards/plan_agent_card.json > /tmp/original.json
jq -S '.' tmp/registry-verify/plan_agent_card.json > /tmp/pulled.json
diff /tmp/original.json /tmp/pulled.json && echo "Content matches"
```

### Step 4: Verify All Agents

Create a verification script to confirm all three agents:

```bash
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
  oras pull "$registry/$agent:v1" -o "$verify_dir/"

  # Compare
  if diff -q "src/agent_cards/${agent}_agent_card.json" \
           "$verify_dir/${agent}_agent_card.json" > /dev/null; then
    echo "✓ $agent agent: Content verified"
  else
    echo "✗ $agent agent: Content mismatch"
    exit 1
  fi

  echo
done

echo "=== All agents verified successfully ==="
```

Save as `verify_registry.sh` and run:
```bash
chmod +x verify_registry.sh
./verify_registry.sh
```

## Project Structure

Updated directory structure after Phase 3:

```
pallet/
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── plan_agent.py
│   │   ├── build_agent.py
│   │   └── test_agent.py
│   └── agent_cards/
│       ├── plan_agent_card.json
│       ├── build_agent_card.json
│       └── test_agent_card.json
├── specs/
│   ├── phase2.md
│   └── phase3.md                  # This file
├── tmp/
│   └── registry-verify/           # Pulled artifacts for verification
│       ├── plan_agent_card.json
│       ├── build_agent_card.json
│       └── test_agent_card.json
├── verify_registry.sh             # Verification script
├── main.py
├── pyproject.toml
└── README.md
```

## Commands Reference

### Basic Operations

| Operation | Command |
|-----------|---------|
| Push artifact | `oras push REPO:TAG FILE` |
| Pull artifact | `oras pull REPO:TAG -o OUTDIR` |
| List repositories | `oras repo list REGISTRY` |
| List tags | `oras repo tags REGISTRY/REPO` |
| Get manifest | `oras manifest fetch REPO:TAG` |
| Get digest | `oras resolve REPO:TAG` |
| Copy artifact | `oras cp SOURCE:TAG DEST:TAG` |

### Practical Examples

```bash
# Push all agents at once (from src/agent_cards)
for agent in plan build test; do
  oras push localhost:5000/agents/$agent:v1 ${agent}_agent_card.json
done

# Pull all agents at once
for agent in plan build test; do
  oras pull localhost:5000/agents/$agent:v1 -o tmp/registry-verify/
done

# Get digest (useful for version tracking)
oras resolve localhost:5000/agents/plan:v1

# Copy to new version
oras cp localhost:5000/agents/plan:v1 localhost:5000/agents/plan:v2
```

## Troubleshooting

### Issue: Connection refused to localhost:5000

**Problem**: Registry is not running or not accessible

**Solution**:
```bash
# Verify registry is running
docker ps | grep registry

# If not running, start it
docker run -d -p 5000:5000 --name registry registry:2

# Check logs
docker logs registry
```

### Issue: ORAS command not found

**Problem**: ORAS is not installed or not in PATH

**Solution**:
```bash
# Verify installation
oras version

# If not installed, reinstall
go install oras.land/oras@latest

# Add to PATH if needed
export PATH=$PATH:$(go env GOPATH)/bin
```

### Issue: Artifact not found error

**Problem**: Tag does not exist in registry

**Solution**:
```bash
# Check what tags exist
oras repo tags localhost:5000/agents/plan

# Verify file path for push
ls -la src/agent_cards/plan_agent_card.json

# Confirm push command completed successfully
oras push localhost:5000/agents/plan:v2 src/agent_cards/plan_agent_card.json
```

### Issue: File content doesn't match after pull

**Problem**: JSON formatting differences or corruption

**Solution**:
```bash
# Check file sizes match
stat src/agent_cards/plan_agent_card.json
stat tmp/registry-verify/plan_agent_card.json

# Compare with normalized JSON (ignores formatting)
jq -S '.' src/agent_cards/plan_agent_card.json | md5sum
jq -S '.' tmp/registry-verify/plan_agent_card.json | md5sum

# If checksums differ, investigate content
jq '.' src/agent_cards/plan_agent_card.json > /tmp/original.json
jq '.' tmp/registry-verify/plan_agent_card.json > /tmp/pulled.json
diff /tmp/original.json /tmp/pulled.json
```

### Issue: Permission denied when writing to output directory

**Problem**: Output directory doesn't exist or lacks write permissions

**Solution**:
```bash
# Create output directory with proper permissions
mkdir -p tmp/registry-verify
chmod 755 tmp/registry-verify

# Or specify output to current directory
oras pull localhost:5000/agents/plan:v1 -o .
```

## Time Breakdown

- **Publishing Agent Cards**: 8 minutes (3 agents × 2-3 minutes each)
- **Verifying Storage**: 12 minutes (pulling, comparing, validating)
- **Documentation & Notes**: 10 minutes

Total: 30 minutes

## Technologies

- **ORAS**: OCI Registry as Storage - CLI tool for managing OCI artifacts
- **OCI Registry**: Open Container Initiative standard for artifact storage
- **Docker Registry**: Reference OCI registry implementation (v2 API)
- **jq**: JSON query and formatting tool (for validation)
- **JSON**: Agent card format (OCI artifact media type: `application/json`)

## What's Next?

After Phase 3 completes:

- **Phase 4** could implement registry discovery service
- **Phase 5** could add agent lifecycle management (pulling agents from registry to run)
- **Phase 6** could implement distributed agent orchestration across multiple registries
