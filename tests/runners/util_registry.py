"""
Registry utility test runner - validates registry operations with Pydantic models
How to run:
   uv run python -m tests.runners.util_registry
"""

from src.registry.client import Registry, RegistryConfig
from src.registry.models import CatalogResponse, TagsResponse, ManifestResponse
from src.registry.exceptions import (
    RegistryError,
    RegistryConnectionError,
    RegistryValidationError,
)
import sys


def test_registry_operations():
    """Test all registry operations with proper error handling"""

    # Use context manager for automatic cleanup
    with Registry() as registry:

        # Test 1: Health check
        print("=" * 50)
        print("Testing registry health...")
        if not registry.is_alive():
            print("❌ Registry is not accessible")
            sys.exit(1)
        print("✅ Registry is alive")

        # Test 2: List repositories
        print("\n" + "=" * 50)
        print("Testing repository listing...")
        try:
            catalog: CatalogResponse = registry.list_repositories()
            print(f"✅ Found {len(catalog.repositories)} repositories:")
            for repo in catalog.repositories:
                print(f"  - {repo}")

        except RegistryConnectionError as e:
            print(f"❌ Connection failed: {e}")
            sys.exit(1)
        except RegistryValidationError as e:
            print(f"❌ Invalid response format: {e}")
            sys.exit(1)

        # Test 3: List tags for each repository
        print("\n" + "=" * 50)
        print("Testing tag listing...")
        for repo in catalog.repositories:
            try:
                tags: TagsResponse = registry.list_tags(repo)
                print(f"✅ {tags.name}: {tags.tags}")
            except RegistryError as e:
                print(f"❌ Failed to get tags for {repo}: {e}")

        # Test 4: Get manifest for specific agents
        print("\n" + "=" * 50)
        print("Testing manifest retrieval...")
        test_repos = [
            ("agents/plan", "v1"),
            ("agents/build", "v1"),
            ("workflows/code-generation", "v1"),
        ]

        for repo, tag in test_repos:
            try:
                manifest: ManifestResponse = registry.get_manifest(repo, tag)
                print(f"✅ {repo}:{tag}")
                print(f"   Schema: v{manifest.schemaVersion}")
                print(f"   Layers: {len(manifest.layers)}")
                print(f"   Config digest: {manifest.config.digest[:20]}...")
            except RegistryError as e:
                print(f"❌ Failed to get manifest for {repo}:{tag}: {e}")

        # Test 5: Get blob content
        print("\n" + "=" * 50)
        print("Testing blob retrieval...")
        try:
            manifest = registry.get_manifest("agents/plan", "v1")
            if manifest.layers:
                layer = manifest.layers[0]
                blob_content = registry.get_blob("agents/plan", layer.digest)
                print(f"✅ Retrieved blob: {len(blob_content)} bytes")
                print(f"   Expected: {layer.size} bytes")

                if len(blob_content) == layer.size:
                    print("✅ Blob size matches manifest")
                else:
                    print("⚠️  Blob size mismatch!")
        except RegistryError as e:
            print(f"❌ Blob retrieval failed: {e}")

    # Context manager automatically closed session here
    print("\n" + "=" * 50)
    print("✅ All registry tests completed")


def test_custom_config():
    """Test registry with custom configuration"""
    print("\n" + "=" * 50)
    print("Testing custom configuration...")

    # Custom config with validation
    config = RegistryConfig(url="http://localhost:5000", timeout=30, max_retries=5)

    with Registry(config) as registry:
        if registry.is_alive():
            print(f"✅ Connected with custom config (timeout={config.timeout}s)")
        else:
            print("❌ Failed to connect with custom config")


def test_error_handling():
    """Test error handling for invalid scenarios"""
    print("\n" + "=" * 50)
    print("Testing error handling...")

    with Registry() as registry:
        # Test 1 - non-existent repository
        try:
            registry.list_tags("nonexistent/repo")
            print("❌ Should have raised RegistryConnectionError")
        except RegistryConnectionError as e:
            print("✅ Correctly raised error for non-existent repo")

        # Test 2: Invalid tag
        try:
            registry.get_manifest("agents/plan", "nonexistent-tag")
            print("❌ Should have raised RegistryConnectionError")
        except RegistryConnectionError:
            print("✅ Correctly raised error for invalid tag")


def test_workflow_upload():
    """Test uploading v2 of parallel-analysis workflow"""
    print("\n" + "=" * 50)
    print("Testing workflow upload (v2)...")

    workflow_path = "workflows/parallel-analysis.yaml"
    repo_name = "workflows/parallel-analysis"
    tag_v2 = "v2"

    with Registry() as registry:
        # Step 1: Read workflow file
        try:
            with open(workflow_path, "rb") as f:
                workflow_content = f.read()
            print(f"✅ Read workflow file: {len(workflow_content)} bytes")
        except FileNotFoundError:
            print(f"❌ Workflow file not found: {workflow_path}")
            sys.exit(1)

        # Step 2: Calculate digest
        blob_digest = registry._calculate_digest(workflow_content)
        print(f"✅ Calculated digest: {blob_digest[:20]}...")

        # Step 3: Upload blob
        try:
            registry.upload_blob(repo_name, workflow_content, blob_digest)
            print(f"✅ Uploaded blob to {repo_name}")
        except RegistryConnectionError as e:
            print(f"❌ Blob upload failed: {e}")
            sys.exit(1)

        # Step 4: Push manifest
        try:
            manifest_digest = registry.push_manifest(
                repo=repo_name,
                tag=tag_v2,
                filename="parallel-analysis.yaml",
                blob_digest=blob_digest,
                size=len(workflow_content),
            )
            print(f"✅ Pushed manifest as {repo_name}:{tag_v2}")
            print(f"   Manifest digest: {manifest_digest[:20]}...")
        except RegistryConnectionError as e:
            print(f"❌ Manifest push failed: {e}")
            sys.exit(1)

        # Step 5: Verify upload by retrieving manifest
        try:
            manifest = registry.get_manifest(repo_name, tag_v2)
            print(f"✅ Verified {repo_name}:{tag_v2} exists")
            print(f"   Schema version: {manifest.schemaVersion}")
            print(f"   Layers: {len(manifest.layers)}")

            # Verify blob content matches
            retrieved_blob = registry.get_blob(repo_name, blob_digest)
            if retrieved_blob == workflow_content:
                print("✅ Blob content verified - matches original")
            else:
                print("❌ Blob content mismatch!")

        except RegistryError as e:
            print(f"❌ Verification failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    try:
        test_registry_operations()
        test_custom_config()
        test_error_handling()
        test_workflow_upload()
        print("\n🎉 All tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
