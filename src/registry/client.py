import requests
from requests.exceptions import RequestException
from typing import Optional
from pydantic import ValidationError
from .models import ManifestResponse, RegistryConfig, CatalogResponse, TagsResponse
from .exceptions import RegistryConnectionError, RegistryValidationError
import logging
import json
import hashlib
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Registry:
    """OCI compliant registry client with Pydantic validation"""

    def __init__(self, config: Optional[RegistryConfig] = None):
        self.config = config or RegistryConfig()
        self.url = str(self.config.url)
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create configured requests session"""
        session = requests.session()
        session.headers.update({"User-Agent": "pallet-registry-client/0.1.0"})
        return session

    def is_alive(self) -> bool:
        """Check if registry is alive"""
        try:
            response = self._session.get(f"{self.url}/v2/", timeout=self.config.timeout)
            return response.status_code in (200, 401)
        except RequestException as e:
            logger.debug(f"Registry health check failed: {e}")
            return False

    def list_repositories(self) -> Optional[CatalogResponse]:
        """
        List all repositories in the catalog

        Returns:
            CatalogResponse with repository list, or None on failure

        Raises:
            RegistryConnectionError: If request fails
            RegistryValidationError: If response doesn't match schema
        """
        try:
            response = self._session.get(
                f"{self.url}/v2/_catalog/", timeout=self.config.timeout
            )
            response.raise_for_status()

            return CatalogResponse.model_validate(response.json())

        except RequestException as e:
            logger.error(f"Failed to list repositories: {e}")
            raise RegistryConnectionError(f"Repository listing failed: {e}")
        except ValidationError as e:
            logger.error(f"Invalid catalog response: {e}")
            raise RegistryValidationError(f"Invalid catalog format: {e}")

    def list_tags(self, repo: str) -> Optional[TagsResponse]:
        """
        List all tags for a repository

        Args:
            repo: Repository name (e.g., "agents/plan")

        Returns:
            TagsResponse with tag list, or None on failure
        """
        try:
            url = f"{self.url}/v2/{repo}/tags/list"
            logger.debug(f"Fetching tags from: {url}")

            response = self._session.get(url, timeout=self.config.timeout)
            response.raise_for_status()

            return TagsResponse.model_validate(response.json())

        except RequestException as e:
            logger.error(f"Failed to list tags for {repo}: {e}")
            raise RegistryConnectionError(f"Tag listing failed: {e}")
        except ValidationError as e:
            logger.error(f"Invalid tags response for {repo}: {e}")
            raise RegistryValidationError(f"Invalid tags format: {e}")

    def get_manifest(self, repo: str, tag: str) -> Optional[ManifestResponse]:
        """
        Get OCI manifest for a specific tag

        Args:
            repo: Repository name
            tag: Tag/version identifier

        Returns:
            ManifestResponse with manifest details
        """
        try:
            headers = {"Accept": "application/vnd.oci.image.manifest.v1+json"}
            response = self._session.get(
                f"{self.url}/v2/{repo}/manifests/{tag}",
                headers=headers,
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            return ManifestResponse.model_validate(response.json())

        except RequestException as e:
            logger.error(f"Failed to get manifest {repo}:{tag}: {e}")
            raise RegistryConnectionError(f"Manifest fetch failed: {e}")
        except ValidationError as e:
            logger.error(f"Invalid manifest response for {repo}:{tag}: {e}")
            raise RegistryValidationError(f"Invalid manifest format: {e}")

    def get_blob(self, repo: str, digest: str) -> Optional[bytes]:
        """
        Get blob content by digest

        Args:
            repo: Repository name
            digest: Content digest (e.g., "sha256:abc123...")

        Returns:
            Raw blob content as bytes
        """
        try:
            response = self._session.get(
                f"{self.url}/v2/{repo}/blobs/{digest}", timeout=self.config.timeout
            )
            response.raise_for_status()
            return response.content

        except RequestException as e:
            logger.error(f"Failed to get blob {digest}: {e}")
            raise RegistryConnectionError(f"Blob fetch failed: {e}")

    def upload_blob(self, repo: str, content: bytes, digest: str):
        """Upload blob using monolithic upload. Should be less than 4mb"""
        # Step 1: Initiate upload
        initiate_url = f"{self.url}/v2/{repo}/blobs/uploads/"

        try:
            # Initiate the upload
            initiate_response = self._session.post(initiate_url)

            if initiate_response.status_code != 202:
                raise RequestException(
                    f"Blob upload initiation failed: {initiate_response.status_code} - {initiate_response.text}"
                )

            # Get the upload location from the response
            upload_location = initiate_response.headers.get("Location")
            if not upload_location:
                raise RequestException(
                    "No Location header in upload initiation response"
                )

            # Make location absolute if it's relative
            if upload_location.startswith("/"):
                upload_location = f"{self.url}{upload_location}"

            # Step 2: Complete the monolithic upload with digest
            upload_url = f"{upload_location}&digest={digest}"
            upload_response = self._session.put(
                upload_url,
                data=content,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(len(content)),
                },
            )

            if upload_response.status_code != 201:
                raise RequestException(
                    f"Blob upload failed: {upload_response.status_code} - {upload_response.text}"
                )

        except RequestException as e:
            logger.error(f"Failed to upload blob {digest}: {e}")
            raise RegistryConnectionError(f"Blob upload failed: {e}")

    def _calculate_digest(self, content: bytes) -> str:
        """Calculate SHA256 digest for content"""
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def push_manifest(
        self, repo: str, tag: str, filename: str, blob_digest: str, size: int
    ) -> str:
        """
        Create and push OCI manifest

        Args:
            repo: Repository name
            tag: Tag/version identifier
            filename: Original filename for annotations
            blob_digest: Digest of the blob content
            size: Size of the blob in bytes

        Returns:
            Manifest digest string
        """
        try:
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
                        "org.pallet.workflow.type": "sequential",
                    },
                },
                "layers": [
                    {
                        "mediaType": "application/vnd.pallet.workflow.v1+yaml",
                        "digest": blob_digest,
                        "size": size,
                    }
                ],
                "annotations": {
                    "org.opencontainers.image.created": datetime.now(
                        timezone.utc
                    ).isoformat()
                    + "Z"
                },
            }

            # Upload manifest
            manifest_json = json.dumps(manifest, separators=(",", ":"))
            manifest_digest = self._calculate_digest(manifest_json.encode())

            url = f"{self.url}/v2/{repo}/manifests/{tag}"
            logger.debug(f"Pushing manifest to: {url}")

            response = self._session.put(
                url,
                data=manifest_json,
                headers={"Content-Type": "application/vnd.oci.image.manifest.v1+json"},
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            return manifest_digest

        except RequestException as e:
            logger.error(f"Failed to push manifest {repo}:{tag}: {e}")
            raise RegistryConnectionError(f"Manifest upload failed: {e}")

    def close(self):
        """Close the underlying session"""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exec_type, exec_val, exec_tb):
        self.close()
