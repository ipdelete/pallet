# File: /home/cip/src/pallet/tests/runners/util_registry.py
# How to run:
#   uv run python -m tests.runners.util_registry

from src.registry.client import Registry

class TestRegistryIsAlive:
    def test_is_alive_success_200(self):
        registry = Registry()
        result = registry.is_alive()

        assert result is True

    def test_list_all_repositories(self):
        registry = Registry()
        result = registry.list_all_repositories()

        assert result is not None
        return result
    
    def test_list_all_tags(self):
        repo = "workflows/code-generation"
        registry = Registry()
        result = registry.list_all_tags(repo)

        assert result is not None
        return result
    
    def test_get_manifest_for_repo(self):
        repo = "workflows/code-generation"
        tag = "v1"
        registry = Registry()
        result = registry.get_manifest_for_repo(repo, tag)

        assert result is not None
        return result
    
    def test_get_blob(self):
        repo = "workflows/code-generation"
        digest = "sha256:9d303fe8a26f94e09a1dc825dd509b4808a1450c5c48cb0b6056b00573206c62"
        registry = Registry()
        result = registry.get_blob(repo, digest)

        assert result is not None
        return result.decode('utf-8')


if __name__ == "__main__":
    test_class = TestRegistryIsAlive()
    test_class.test_is_alive_success_200()
    repos = test_class.test_list_all_repositories()
    print(repos)
    tags = test_class.test_list_all_tags()
    print(tags)
    manifest = test_class.test_get_manifest_for_repo()
    print(manifest)
    blob = test_class.test_get_blob()
    print(blob)
