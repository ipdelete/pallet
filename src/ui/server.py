"""Simple FastAPI server for registry UI"""

import logging
import sys
from pathlib import Path
from typing import List

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.registry.client import Registry
from src.registry.exceptions import RegistryConnectionError, RegistryValidationError
from src.registry.models import RegistryConfig

logger = logging.getLogger(__name__)

app = FastAPI(title="Registry UI API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RepositoryListResponse(BaseModel):
    repositories: List[str]


@app.get("/api/repositories", response_model=RepositoryListResponse)
async def list_repositories():
    """List all repositories in the registry"""
    try:
        config = RegistryConfig(url="http://localhost:5000")
        with Registry(config) as client:
            if not client.is_alive():
                raise HTTPException(status_code=503, detail="Registry is not available")

            response = client.list_repositories()
            return RepositoryListResponse(repositories=response.repositories)

    except (RegistryConnectionError, RegistryValidationError) as e:
        logger.error(f"Registry error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
