# OCI Artifact Push Guide

This guide explains how to push artifacts (like workflow YAML files) to an OCI registry using the Distribution Specification API, similar to how ORAS works. The same API is used for both container images and generic artifacts.

## Table of Contents

1. [Overview](#overview)
   - [Images vs Artifacts](#images-vs-artifacts)
2. [API Flow](#api-flow)
   - [Complete Push Sequence](#complete-push-sequence)
3. [Detailed API Reference](#detailed-api-reference)
   - [Blob Upload (Monolithic)](#1-blob-upload-monolithic)
   - [Blob Upload (Chunked)](#2-blob-upload-chunked)
   - [Manifest Upload](#3-manifest-upload)
4. [Manifest Structure](#manifest-structure)
   - [Container Image Manifest](#container-image-manifest)
   - [Generic Artifact Manifest](#generic-artifact-manifest)
   - [Key Differences](#key-differences)
5. [Python Implementation](#python-implementation)
   - [Unified Push Client](#unified-push-client-for-images-and-artifacts)
   - [Extended Example with Error Handling](#extended-example-with-error-handling)
6. [Semantic Versioning](#semantic-versioning)
   - [Tag Format](#tag-format)
   - [Versioning Strategy](#versioning-strategy)
   - [Version Resolution](#version-resolution)
7. [Usage Examples](#usage-examples)
   - [Push Artifacts vs Images](#push-artifacts-vs-images)
   - [Push Single Workflow](#push-single-workflow)
   - [Push with Version Increments](#push-with-version-increments)
   - [Push All Workflows with Versioning](#push-all-workflows-with-versioning)
   - [Push with Authentication](#push-with-authentication)
8. [Command Line Examples](#command-line-examples)
   - [Using curl](#using-curl)
   - [Using ORAS CLI](#using-oras-cli)
9. [Media Types](#media-types)
   - [Container Image Media Types](#container-image-media-types)
   - [Generic Artifact Media Types](#generic-artifact-media-types)
   - [Media Type Best Practices](#media-type-best-practices)
10. [Using Annotations and Media Types for Artifact Discovery](#using-annotations-and-media-types-for-artifact-discovery)
    - [How Media Types Help](#how-media-types-help)
    - [How Annotations Help](#how-annotations-help)
    - [Practical Examples](#practical-examples)
    - [Registry Features for Discovery](#registry-features-for-discovery)
    - [Recommended Annotation Keys](#recommended-annotation-keys)
11. [Error Handling](#error-handling)
12. [Security Considerations](#security-considerations)
13. [References](#references)

## Overview

The OCI Distribution Specification defines a standard API for pushing and pulling container images and other artifacts. The push process involves two main steps:

1. **Upload the blob** (actual file content)
2. **Upload the manifest** (metadata describing the artifact)

### Images vs Artifacts

While the API is identical, the key differences are:

| Aspect | Container Images | Generic Artifacts |
|--------|------------------|-------------------|
| **Media Type** | `application/vnd.oci.image.*` or `application/vnd.docker.*` | Custom types (e.g., `application/vnd.pallet.workflow.v1+yaml`) |
| **Config** | Runtime config (env, cmd, etc.) | Artifact metadata |
| **Layers** | Filesystem layers (tar.gz) | Any file content |
| **Tools** | docker push, buildah, podman | oras push, custom clients |
| **Use Case** | Running containers | Storing any file type |

## API Flow

The OCI Distribution API provides a standardized way to push both container images and generic artifacts to a registry. The process involves uploading content blobs first, then creating a manifest that references those blobs.

### Complete Push Sequence

```
┌─────────┐     POST /v2/<repo>/blobs/uploads/?digest=<digest>    ┌──────────┐
│ Client  │ ─────────────────────────────────────────────────────> │ Registry │
│         │ <───────────────────────────────────────────────────── │          │
│         │              201 Created                                │          │
│         │                                                         │          │
│         │     PUT /v2/<repo>/manifests/<tag>                     │          │
│         │ ─────────────────────────────────────────────────────> │          │
│         │ <───────────────────────────────────────────────────── │          │
└─────────┘              201 Created                                └──────────┘
```

## Detailed API Reference

### 1. Blob Upload (Monolithic)

**Endpoint**: `POST /v2/<name>/blobs/uploads/?digest=<digest>`

**Headers**:
```http
Content-Type: application/octet-stream
Content-Length: <size>
```

**Body**: Raw file content

**Response**: 
- `201 Created` - Blob successfully uploaded
- `Location` header with blob URL

**Example**:
```bash
curl -X POST \
  -H "Content-Type: application/octet-stream" \
  -H "Content-Length: 1234" \
  --data-binary @workflow.yaml \
  http://localhost:5000/v2/workflows/code-generation/blobs/uploads/?digest=sha256:abc123...
```

### 2. Blob Upload (Chunked)

For large files, use chunked upload:

**Step 1 - Initiate**: `POST /v2/<name>/blobs/uploads/`
```http
HTTP/1.1 202 Accepted
Location: /v2/<name>/blobs/uploads/<uuid>
```

**Step 2 - Upload chunks**: `PATCH <location>`
```http
Content-Type: application/octet-stream
Content-Range: 0-1023
Content-Length: 1024
```

**Step 3 - Complete**: `PUT <location>?digest=<digest>`

### 3. Manifest Upload

**Endpoint**: `PUT /v2/<name>/manifests/<reference>`

**Headers**:
```http
Content-Type: application/vnd.oci.image.manifest.v1+json
Content-Length: <size>
```

**Body**: JSON manifest

**Response**: 
- `201 Created` - Manifest uploaded
- `Docker-Content-Digest` header with manifest digest

## Manifest Structure

### Container Image Manifest
```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "config": {
    "mediaType": "application/vnd.oci.image.config.v1+json",
    "digest": "sha256:abc123...",
    "size": 7023
  },
  "layers": [
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "digest": "sha256:def456...",
      "size": 32654
    },
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "digest": "sha256:789012...",
      "size": 16724
    }
  ]
}
```

### Generic Artifact Manifest
```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "config": {
    "mediaType": "application/vnd.pallet.workflow.v1+yaml",
    "digest": "sha256:b5b2b2c50...",
    "size": 1470,
    "annotations": {
      "org.opencontainers.image.title": "code-generation.yaml"
    }
  },
  "layers": [
    {
      "mediaType": "application/vnd.pallet.workflow.v1+yaml",
      "digest": "sha256:b5b2b2c50...",
      "size": 1470,
      "annotations": {
        "org.opencontainers.image.title": "code-generation.yaml"
      }
    }
  ],
  "artifactType": "application/vnd.pallet.workflow.v1+yaml"
}
```

### Key Differences

1. **Config Media Type**: 
   - Images: `application/vnd.oci.image.config.v1+json` (container runtime config)
   - Artifacts: Your custom type (describes the artifact)

2. **Layer Media Types**:
   - Images: `application/vnd.oci.image.layer.v1.tar+gzip` (filesystem layers)
   - Artifacts: Your custom type (actual file content)

3. **artifactType** (optional): New field in OCI 1.1 for artifacts

## Python Implementation

The following Python examples demonstrate how to interact with the OCI Distribution API to push both container images and generic artifacts.

### Unified Push Client for Images and Artifacts

```python
import hashlib
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional

class OCIPusher:
    """Push both container images and generic artifacts to OCI registry."""
    
    def __init__(self, registry_url="http://localhost:5000"):
        self.registry_url = registry_url.rstrip('/')
        self.session = requests.Session()
    
    def push_artifact(self, repo, tag, file_path, media_type, artifact_type=None):
        """
        Push a generic artifact (non-image) to registry.
        
        Args:
            repo: Repository name
            tag: Version tag
            file_path: Path to artifact file
            media_type: Custom media type for the artifact
            artifact_type: Optional artifactType field (OCI 1.1)
        """
        content = file_path.read_bytes()
        digest = f"sha256:{hashlib.sha256(content).hexdigest()}"
        
        # Upload blob
        self._upload_blob(repo, content, digest)
        
        # Create artifact manifest
        manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "mediaType": media_type,
                "digest": digest,
                "size": len(content),
                "annotations": {
                    "org.opencontainers.image.title": file_path.name
                }
            },
            "layers": [{
                "mediaType": media_type,
                "digest": digest,
                "size": len(content)
            }]
        }
        
        # Add artifactType for OCI 1.1 compliance
        if artifact_type:
            manifest["artifactType"] = artifact_type
            
        return self._push_manifest(repo, tag, manifest)
    
    def push_image_layers(self, repo, tag, config, layers):
        """
        Push a container image with config and layers.
        
        Args:
            repo: Repository name
            tag: Version tag
            config: Dict with image configuration
            layers: List of layer tar.gz file paths
        """
        # Upload config blob
        config_json = json.dumps(config, separators=(',', ':'))
        config_digest = self._upload_json_blob(repo, config_json)
        
        # Upload layer blobs
        layer_descriptors = []
        for layer_path in layers:
            layer_content = layer_path.read_bytes()
            layer_digest = self._upload_blob(repo, layer_content)
            
            layer_descriptors.append({
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": layer_digest,
                "size": len(layer_content)
            })
        
        # Create image manifest
        manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "mediaType": "application/vnd.oci.image.config.v1+json",
                "digest": config_digest,
                "size": len(config_json.encode())
            },
            "layers": layer_descriptors
        }
        
        return self._push_manifest(repo, tag, manifest)
```

### Extended Example with Error Handling

```python
import hashlib
import json
import requests
from typing import Dict, Optional
from pathlib import Path

class RegistryPusher:
    """OCI registry push client with full error handling."""
    
    def __init__(self, registry_url: str = "http://localhost:5000"):
        self.registry_url = registry_url.rstrip('/')
        self.session = requests.Session()
        # Add retry adapter
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        retry = Retry(total=3, backoff_factor=0.3)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def push_workflow(self, workflow_path: Path) -> Dict[str, str]:
        """Push a workflow YAML file to the registry."""
        
        # Determine repository and tag from filename
        # e.g., code-generation.yaml -> workflows/code-generation:1.0.0
        repo = f"workflows/{workflow_path.stem}"
        tag = "1.0.0"  # Default semantic version
        
        content = workflow_path.read_bytes()
        digest = self._calculate_digest(content)
        
        # Step 1: Check if blob exists
        if not self._blob_exists(repo, digest):
            self._upload_blob(repo, content, digest)
        
        # Step 2: Upload manifest
        manifest_digest = self._push_manifest(
            repo, tag, workflow_path.name, digest, len(content)
        )
        
        return {
            "repository": repo,
            "tag": tag,
            "digest": manifest_digest,
            "blob_digest": digest,
            "size": len(content)
        }
    
    def _calculate_digest(self, content: bytes) -> str:
        """Calculate SHA256 digest."""
        return f"sha256:{hashlib.sha256(content).hexdigest()}"
    
    def _blob_exists(self, repo: str, digest: str) -> bool:
        """Check if blob already exists."""
        url = f"{self.registry_url}/v2/{repo}/blobs/{digest}"
        response = self.session.head(url)
        return response.status_code == 200
    
    def _upload_blob(self, repo: str, content: bytes, digest: str):
        """Upload blob using monolithic upload."""
        url = f"{self.registry_url}/v2/{repo}/blobs/uploads/?digest={digest}"
        
        response = self.session.post(
            url,
            data=content,
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(content))
            }
        )
        
        if response.status_code != 201:
            raise Exception(
                f"Blob upload failed: {response.status_code} - {response.text}"
            )
    
    def _push_manifest(
        self,
        repo: str,
        tag: str,
        filename: str,
        blob_digest: str,
        size: int
    ) -> str:
        """Create and push manifest."""
        
        # Create manifest
        manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.manifest.v1+json",
            "config": {
                "mediaType": "application/vnd.pallet.workflow.v1+yaml",
                "digest": blob_digest,
                "size": size,
                "annotations": {
                    "org.opencontainers.image.title": filename,
                    "org.pallet.workflow.type": "sequential"
                }
            },
            "layers": [{
                "mediaType": "application/vnd.pallet.workflow.v1+yaml",
                "digest": blob_digest,
                "size": size
            }],
            "annotations": {
                "org.opencontainers.image.created": 
                    datetime.utcnow().isoformat() + "Z"
            }
        }
        
        # Upload manifest
        manifest_json = json.dumps(manifest, separators=(',', ':'))
        manifest_digest = self._calculate_digest(manifest_json.encode())
        
        url = f"{self.registry_url}/v2/{repo}/manifests/{tag}"
        response = self.session.put(
            url,
            data=manifest_json,
            headers={
                "Content-Type": "application/vnd.oci.image.manifest.v1+json"
            }
        )
        
        if response.status_code != 201:
            raise Exception(
                f"Manifest upload failed: {response.status_code} - {response.text}"
            )
        
        return manifest_digest
```

## Semantic Versioning

### Tag Format

Use semantic versioning (semver) for all artifact tags:
- Format: `MAJOR.MINOR.PATCH` (e.g., `1.0.0`, `2.1.3`)
- Optional pre-release: `1.0.0-beta.1`, `2.0.0-rc.1`
- Optional build metadata: `1.0.0+20240101`

### Versioning Strategy

```python
class SemverPusher(RegistryPusher):
    """Registry pusher with semantic versioning support."""
    
    def push_workflow_version(
        self, 
        workflow_path: Path,
        version: str,
        prerelease: Optional[str] = None,
        build: Optional[str] = None
    ) -> Dict[str, str]:
        """Push workflow with semantic version."""
        
        # Construct full version tag
        tag = version
        if prerelease:
            tag += f"-{prerelease}"
        if build:
            tag += f"+{build}"
            
        repo = f"workflows/{workflow_path.stem}"
        content = workflow_path.read_bytes()
        digest = self._calculate_digest(content)
        
        # Upload blob and manifest
        if not self._blob_exists(repo, digest):
            self._upload_blob(repo, content, digest)
            
        # Add version to annotations
        manifest_digest = self._push_versioned_manifest(
            repo, tag, workflow_path.name, digest, len(content), version
        )
        
        # Also tag as 'latest' if it's a stable release
        if not prerelease:
            self._tag_as_latest(repo, manifest_digest)
            
        return {
            "repository": repo,
            "tag": tag,
            "version": version,
            "digest": manifest_digest
        }
```

### Version Resolution

```python
import re
from packaging import version

def get_latest_semver_tag(tags: List[str]) -> str:
    """Get the latest semantic version from a list of tags."""
    
    # Filter valid semver tags
    semver_pattern = re.compile(
        r'^(\d+)\.(\d+)\.(\d+)'
        r'(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?'
        r'(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'
    )
    
    valid_versions = [
        tag for tag in tags 
        if semver_pattern.match(tag)
    ]
    
    if not valid_versions:
        return "latest"
        
    # Sort by version and return latest
    return max(valid_versions, key=lambda v: version.parse(v))

def get_compatible_version(
    registry, 
    repo: str, 
    constraint: str
) -> Optional[str]:
    """Find compatible version based on constraint."""
    
    tags = registry.list_tags(repo).tags
    
    # Simple constraint examples
    if constraint.startswith("^"):  # Compatible with
        major = constraint[1:].split(".")[0]
        compatible = [
            tag for tag in tags 
            if tag.startswith(f"{major}.")
        ]
        return get_latest_semver_tag(compatible)
        
    elif constraint.startswith("~"):  # Approximately
        major_minor = ".".join(constraint[1:].split(".")[:2])
        compatible = [
            tag for tag in tags 
            if tag.startswith(major_minor)
        ]
        return get_latest_semver_tag(compatible)
        
    # Exact version
    return constraint if constraint in tags else None
```

## Usage Examples

These examples show practical usage of the OCI push API for different scenarios.

### Push Artifacts vs Images

```python
pusher = OCIPusher()

# 1. Push a workflow artifact
pusher.push_artifact(
    repo="workflows/code-generation",
    tag="1.0.0",
    file_path=Path("workflows/code-generation.yaml"),
    media_type="application/vnd.pallet.workflow.v1+yaml",
    artifact_type="application/vnd.pallet.workflow.v1+yaml"  # OCI 1.1
)

# 2. Push a Helm chart
pusher.push_artifact(
    repo="charts/myapp",
    tag="2.1.0",
    file_path=Path("myapp-2.1.0.tgz"),
    media_type="application/vnd.cncf.helm.chart.content.v1.tar+gzip",
    artifact_type="application/vnd.cncf.helm.chart.config.v1+json"
)

# 3. Push a container image
config = {
    "architecture": "amd64",
    "os": "linux",
    "config": {
        "Env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
        "Cmd": ["/bin/sh"],
        "WorkingDir": "/"
    },
    "rootfs": {"type": "layers", "diff_ids": ["sha256:..."]}
}

layers = [
    Path("layer1.tar.gz"),
    Path("layer2.tar.gz")
]

pusher.push_image_layers(
    repo="myapp/backend",
    tag="1.0.0",
    config=config,
    layers=layers
)
```

### Push Single Workflow
```python
pusher = SemverPusher()

# Push initial version
result = pusher.push_workflow_version(
    Path("workflows/code-generation.yaml"),
    version="1.0.0"
)
print(f"Pushed to {result['repository']}:{result['tag']}")
```

### Push with Version Increments
```python
# Push patch version
result = pusher.push_workflow_version(
    Path("workflows/code-generation.yaml"),
    version="1.0.1"
)

# Push minor version with new features
result = pusher.push_workflow_version(
    Path("workflows/code-generation.yaml"),
    version="1.1.0"
)

# Push major version with breaking changes
result = pusher.push_workflow_version(
    Path("workflows/code-generation.yaml"),
    version="2.0.0"
)

# Push pre-release
result = pusher.push_workflow_version(
    Path("workflows/code-generation.yaml"),
    version="2.1.0",
    prerelease="beta.1"
)
```

### Push All Workflows with Versioning
```python
from pathlib import Path

pusher = SemverPusher()
workflows_dir = Path("workflows")

# Version mapping for initial release
versions = {
    "code-generation": "1.0.0",
    "parallel-analysis": "1.0.0",
    "smart-router": "2.0.0"  # v2 due to breaking changes
}

for workflow_file in workflows_dir.glob("*.yaml"):
    try:
        version = versions.get(workflow_file.stem, "1.0.0")
        result = pusher.push_workflow_version(workflow_file, version)
        print(f"✅ Pushed {workflow_file.name} as {version}")
    except Exception as e:
        print(f"❌ Failed to push {workflow_file.name}: {e}")
```

### Push with Authentication
```python
class AuthenticatedPusher(RegistryPusher):
    def __init__(self, registry_url: str, username: str, password: str):
        super().__init__(registry_url)
        # Basic auth
        self.session.auth = (username, password)
        # Or Bearer token
        # self.session.headers['Authorization'] = f'Bearer {token}'
```

## Command Line Examples

### Using curl

```bash
# 1. Upload blob
curl -X POST \
  -H "Content-Type: application/octet-stream" \
  --data-binary @workflows/code-generation.yaml \
  "http://localhost:5000/v2/workflows/code-generation/blobs/uploads/?digest=$(sha256sum workflows/code-generation.yaml | cut -d' ' -f1)"

# 2. Create manifest.json
cat > manifest.json << EOF
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "config": {
    "mediaType": "application/vnd.pallet.workflow.v1+yaml",
    "digest": "sha256:$(sha256sum workflows/code-generation.yaml | cut -d' ' -f1)",
    "size": $(stat -f%z workflows/code-generation.yaml)
  },
  "layers": [{
    "mediaType": "application/vnd.pallet.workflow.v1+yaml",
    "digest": "sha256:$(sha256sum workflows/code-generation.yaml | cut -d' ' -f1)",
    "size": $(stat -f%z workflows/code-generation.yaml)
  }]
}
EOF

# 3. Upload manifest
curl -X PUT \
  -H "Content-Type: application/vnd.oci.image.manifest.v1+json" \
  --data-binary @manifest.json \
  "http://localhost:5000/v2/workflows/code-generation/manifests/1.0.0"
```

### Using ORAS CLI

```bash
# Push workflow with semantic versioning
oras push localhost:5000/workflows/code-generation:1.0.0 \
  --artifact-type application/vnd.pallet.workflow.v1+yaml \
  workflows/code-generation.yaml

# Push with annotations and version
oras push localhost:5000/workflows/parallel-analysis:2.1.0 \
  --artifact-type application/vnd.pallet.workflow.v1+yaml \
  --annotation "org.pallet.workflow.type=parallel" \
  --annotation "org.opencontainers.image.version=2.1.0" \
  workflows/parallel-analysis.yaml
```

## Media Types

Media types are crucial for identifying content types in an OCI registry. They follow the format `application/vnd.{vendor}.{type}.{version}+{format}` and help registries and clients understand how to handle different artifacts.

### Container Image Media Types
- **Manifest**: `application/vnd.oci.image.manifest.v1+json` or `application/vnd.docker.distribution.manifest.v2+json`
- **Config**: `application/vnd.oci.image.config.v1+json`
- **Layers**: `application/vnd.oci.image.layer.v1.tar+gzip`
- **Index** (multi-arch): `application/vnd.oci.image.index.v1+json`

### Generic Artifact Media Types

**Pallet Artifacts:**
- Workflows: `application/vnd.pallet.workflow.v1+yaml`
- Agent Cards: `application/vnd.pallet.agent-card.v1+json`
- Configurations: `application/vnd.pallet.config.v1+json`
- Schemas: `application/vnd.pallet.schema.v1+json`

**Common Artifact Types:**
- Helm Charts: `application/vnd.cncf.helm.chart.content.v1.tar+gzip`
- WASM Modules: `application/vnd.module.wasm.content.layer.v1+wasm`
- SBOMs: `application/vnd.cyclonedx+json` or `application/spdx+json`
- Signatures: `application/vnd.oci.image.config.v1+json` (Cosign)
- Generic files: `application/vnd.oci.empty.v1+json` (config) + custom layer type

### Media Type Best Practices

1. **Use standard types** when available (OCI, CNCF, etc.)
2. **Create vendor-specific types** for custom artifacts: `application/vnd.{vendor}.{type}.{version}+{format}`
3. **Include version** in media type for compatibility
4. **Use correct suffix**: `+json`, `+yaml`, `+gzip`, etc.
5. **Be consistent** across your organization's artifacts
6. **Document your custom types** for consumers

## Using Annotations and Media Types for Artifact Discovery

Annotations and media types are crucial for artifact discovery, filtering, and proper handling when accessing artifacts from the registry.

### How Media Types Help

**1. Content Identification**

```python
def identify_content_type(registry, repo, tag):
    """Identify if content is an image or artifact based on media types."""
    manifest = registry.get_manifest(repo, tag)
    config_type = manifest.config.mediaType
    
    # Check if it's a container image
    if config_type in [
        "application/vnd.oci.image.config.v1+json",
        "application/vnd.docker.container.image.v1+json"
    ]:
        return "container-image", {
            "platform": extract_platform(manifest),
            "layers": len(manifest.layers)
        }
    
    # Check for known artifact types
    elif config_type == "application/vnd.pallet.workflow.v1+yaml":
        return "workflow", {"type": "pallet-workflow"}
    
    elif config_type == "application/vnd.cncf.helm.chart.config.v1+json":
        return "helm-chart", {"type": "helm"}
    
    # Check artifactType field (OCI 1.1)
    elif hasattr(manifest, 'artifactType'):
        return "artifact", {
            "type": manifest.artifactType,
            "config_type": config_type
        }
    
    # Generic artifact
    else:
        return "artifact", {"type": config_type}

# Usage
content_type, metadata = identify_content_type(registry, "myapp/backend", "1.0.0")
if content_type == "container-image":
    print(f"Container image for {metadata['platform']}")
else:
    print(f"Artifact of type {metadata['type']}")
```

**2. Client-Side Filtering**

```python
# List only workflow artifacts
def list_workflows(registry):
    workflows = []
    for repo in registry.list_repositories().repositories:
        manifest = registry.get_manifest(repo, "latest")
        if manifest.config.mediaType == "application/vnd.pallet.workflow.v1+yaml":
            workflows.append(repo)
    return workflows
```

**3. Content Negotiation**

```python
# Request specific manifest types
headers = {
    "Accept": "application/vnd.oci.image.manifest.v1+json"
}
```

### How Annotations Help

**1. Metadata Without Downloading**

```json
{
  "config": {
    "annotations": {
      "org.pallet.workflow.type": "parallel",
      "org.pallet.workflow.timeout": "600",
      "org.pallet.workflow.dependencies": "plan,build"
    }
  }
}
```

**2. Discovery and Search**

```python
# Find all parallel workflows
def find_parallel_workflows(registry):
    parallel_workflows = []
    for repo in registry.list_repositories().repositories:
        # Get latest semver tag
        tags = registry.list_tags(repo)
        latest_tag = get_latest_semver_tag(tags.tags)
        
        manifest = registry.get_manifest(repo, latest_tag)
        annotations = manifest.config.get("annotations", {})
        if annotations.get("org.pallet.workflow.type") == "parallel":
            parallel_workflows.append({
                "repo": repo,
                "version": latest_tag,
                "timeout": annotations.get("org.pallet.workflow.timeout"),
                "deps": annotations.get("org.pallet.workflow.dependencies")
            })
    return parallel_workflows
```

**3. Version Management**

```python
# Annotations for semantic versioning
annotations = {
    "org.opencontainers.image.version": "1.2.0",
    "org.opencontainers.image.revision": "abc123",
    "org.opencontainers.image.created": "2024-01-01T00:00:00Z",
    "org.pallet.workflow.breaking-change": "true"
}
```

### Practical Examples

**1. Smart Router Selection**

```python
def select_workflow_by_capabilities(registry, required_skills):
    """Select workflow based on required capabilities."""
    candidates = []
    
    for repo in registry.list_repositories().repositories:
        if not repo.startswith("workflows/"):
            continue
            
        manifest = registry.get_manifest(repo, "latest")
        annotations = manifest.config.get("annotations", {})
        
        # Check if workflow has required skills
        workflow_skills = annotations.get("org.pallet.workflow.skills", "").split(",")
        if all(skill in workflow_skills for skill in required_skills):
            candidates.append({
                "repo": repo,
                "priority": int(annotations.get("org.pallet.workflow.priority", "0")),
                "cost": annotations.get("org.pallet.workflow.cost", "low")
            })
    
    # Return highest priority workflow
    return max(candidates, key=lambda x: x["priority"])
```

**2. Dependency Resolution**

```python
def resolve_workflow_dependencies(registry, workflow_repo):
    """Recursively resolve workflow dependencies."""
    manifest = registry.get_manifest(workflow_repo, "latest")
    annotations = manifest.config.get("annotations", {})
    
    deps = annotations.get("org.pallet.workflow.requires", "").split(",")
    resolved = set()
    
    for dep in deps:
        if dep:
            resolved.add(dep)
            # Recursively resolve
            sub_deps = resolve_workflow_dependencies(registry, f"workflows/{dep}")
            resolved.update(sub_deps)
    
    return resolved
```

**3. Runtime Selection**

```python
def get_workflow_for_context(registry, context):
    """Select workflow based on runtime context."""
    best_match = None
    best_score = 0
    
    for repo in registry.list_repositories().repositories:
        if not repo.startswith("workflows/"):
            continue
            
        manifest = registry.get_manifest(repo, "latest")
        annotations = manifest.config.get("annotations", {})
        
        score = 0
        # Match language
        if annotations.get("org.pallet.workflow.language") == context.get("language"):
            score += 10
        
        # Match environment
        if annotations.get("org.pallet.workflow.env") == context.get("env"):
            score += 5
            
        # Check resource requirements
        max_memory = annotations.get("org.pallet.workflow.max-memory", "1GB")
        if parse_memory(max_memory) <= context.get("available_memory"):
            score += 3
            
        if score > best_score:
            best_score = score
            best_match = repo
    
    return best_match
```

### Registry Features for Discovery

**1. Referrers API (OCI 1.1)**

```python
# Find all artifacts referring to a specific artifact
# GET /v2/<name>/referrers/<digest>
def find_related_artifacts(registry, artifact_digest):
    url = f"{registry.url}/v2/workflows/referrers/{artifact_digest}"
    response = requests.get(url)
    
    # Returns artifacts that reference this one
    # Useful for finding test suites, docs, configs for a workflow
    return response.json()
```

**2. Tag Filtering with Annotations**

```python
# List tags with specific patterns
def list_stable_versions(registry, repo):
    tags = registry.list_tags(repo)
    stable_tags = []
    
    for tag in tags.tags:
        # Get manifest to check annotations
        manifest = registry.get_manifest(repo, tag)
        annotations = manifest.config.get("annotations", {})
        
        if annotations.get("org.pallet.release.stable") == "true":
            stable_tags.append({
                "tag": tag,
                "date": annotations.get("org.opencontainers.image.created"),
                "notes": annotations.get("org.pallet.release.notes")
            })
    
    return stable_tags
```

### Recommended Annotation Keys

For Pallet workflows:

```json
{
  "org.pallet.workflow.type": "parallel|sequential|conditional",
  "org.pallet.workflow.skills": "create_plan,generate_code",
  "org.pallet.workflow.timeout": "600",
  "org.pallet.workflow.priority": "10",
  "org.pallet.workflow.cost": "low|medium|high",
  "org.pallet.workflow.requires": "dep1,dep2",
  "org.pallet.workflow.language": "python|javascript|go",
  "org.pallet.workflow.env": "dev|staging|prod",
  "org.pallet.workflow.max-memory": "1GB",
  "org.pallet.release.stable": "true|false",
  "org.opencontainers.image.version": "1.2.0",
  "org.opencontainers.image.created": "2024-01-01T00:00:00Z"
}
```

### Key Benefits

1. **No Download Required**: Access metadata without downloading full artifact
2. **Efficient Filtering**: Query artifacts by type, capabilities, requirements
3. **Runtime Decisions**: Select appropriate artifacts based on context
4. **Dependency Management**: Track and resolve artifact relationships
5. **Versioning**: Semantic versioning and compatibility tracking
6. **Discovery**: Find artifacts by capabilities, not just names

## Error Handling

Understanding common errors helps in building robust push clients. Here are the most frequent issues and their solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| 404 Not Found | Repository doesn't exist | Create repository or check name |
| 400 Bad Request | Invalid digest format | Ensure digest is `sha256:...` |
| 413 Payload Too Large | Blob too big | Use chunked upload |
| 401 Unauthorized | Missing auth | Add authentication headers |

## Security Considerations

When working with OCI registries in production:

1. **Authentication**: Production registries require authentication (Basic Auth, Bearer tokens, or OAuth)
2. **HTTPS**: Always use TLS for production deployments to prevent MITM attacks
3. **Digest Verification**: Always verify content matches digest after upload/download
4. **Access Control**: Implement proper RBAC for repositories
5. **Secrets Management**: Never hardcode credentials; use environment variables or secret managers
6. **Registry Scanning**: Enable vulnerability scanning for container images
7. **Audit Logging**: Track all push/pull operations for compliance

## References

- [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec)
- [ORAS Documentation](https://oras.land/docs/)
- [OCI Image Manifest Specification](https://github.com/opencontainers/image-spec/blob/main/manifest.md)
