from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import List

class CatalogResponse(BaseModel):
    """OCI registry catalog response"""
    repositories: List[str]

class TagsResponse(BaseModel):
    """OCI registry tags list response"""
    name: str
    tags: List[str]

class ManifestLayer(BaseModel):
    """OCI manifest layer"""
    mediaType: str
    digest: str
    size: int

class ManifestConfig(BaseModel):
    """OCI manifest config"""
    mediaType: str
    digest: str
    size: int

class ManifestResponse(BaseModel):
    """OCI image manifest"""
    schemaVersion: int
    mediaType: str = Field(default="application/vnd.oci.image.manifest.v1+json")
    config: ManifestConfig
    layers: List[ManifestLayer]

class RegistryConfig(BaseModel):
    """Registry client configuration"""
    url: HttpUrl = Field(default="http://localhost:5000")
    timeout: int = Field(default=10, gt=0)
    max_retries: int = Field(default=3, ge=0)

    @field_validator('url')
    @classmethod
    def strip_trailing_slash(cls, v):
        return str(v).rstrip('/')
