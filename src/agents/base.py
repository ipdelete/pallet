"""Base agent class for A2A protocol implementation."""

import os
import json
import logging
import asyncio
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx


logger = logging.getLogger(__name__)


class Message(BaseModel):
    """A2A Message structure."""
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None


class SkillDefinition(BaseModel):
    """Skill definition for Agent Card."""
    id: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


class AgentCard(BaseModel):
    """Agent Card for A2A protocol."""
    name: str
    url: str
    skills: list[SkillDefinition]


class BaseAgent(ABC):
    """Base agent class implementing A2A protocol."""

    def __init__(
        self,
        name: str,
        port: int,
        skills: list[SkillDefinition],
    ):
        """Initialize base agent.

        Args:
            name: Agent name
            port: Port to run FastAPI server on
            skills: List of skills this agent provides
        """
        self.name = name
        self.port = port
        self.skills = skills
        self.app = FastAPI(title=name)

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes."""
        @self.app.get("/agent-card")
        async def get_agent_card():
            """Get the agent card with capabilities."""
            return {
                "name": self.name,
                "url": f"http://localhost:{self.port}",
                "skills": [
                    {
                        "id": skill.id,
                        "description": skill.description,
                        "input_schema": skill.input_schema,
                        "output_schema": skill.output_schema,
                    }
                    for skill in self.skills
                ]
            }

        @self.app.post("/execute")
        async def execute(message: Message):
            """Execute a skill."""
            try:
                # Validate method is a known skill
                skill_ids = [skill.id for skill in self.skills]
                if message.method not in skill_ids:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Unknown skill: {message.method}"
                    )

                # Execute the skill
                result = await self.execute_skill(message.method, message.params)

                # Return JSON-RPC 2.0 response
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": message.id,
                }
            except Exception as e:
                logger.error(f"Error executing skill: {e}")
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -1,
                        "message": str(e),
                    },
                    "id": message.id,
                }

    @abstractmethod
    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Any:
        """Execute a skill. Must be implemented by subclasses.

        Args:
            skill_id: The skill to execute
            params: Parameters for the skill

        Returns:
            Result from executing the skill
        """
        pass

    async def call_claude(self, system_prompt: str, user_message: str) -> str:
        """Call Claude using claude code CLI with system and user prompts.

        Args:
            system_prompt: System prompt for Claude
            user_message: User message

        Returns:
            Claude's response
        """
        # Combine system prompt and user message into a single prompt
        combined_prompt = f"{system_prompt}\n\n{user_message}"

        try:
            # Use asyncio to run subprocess without blocking
            process = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                "--dangerously-skip-permissions",
                combined_prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Claude code CLI failed: {error_msg}")

            return stdout.decode().strip()
        except FileNotFoundError:
            raise RuntimeError(
                "Claude code CLI not found. Make sure 'claude' is installed and in PATH."
            )
        except Exception as e:
            raise RuntimeError(f"Error calling Claude code CLI: {e}")

    async def call_agent_skill(
        self,
        agent_url: str,
        skill_id: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Call another agent's skill via A2A protocol.

        Args:
            agent_url: Base URL of the agent
            skill_id: Skill to execute
            params: Parameters for the skill

        Returns:
            Result from the agent
        """
        message = {
            "jsonrpc": "2.0",
            "method": skill_id,
            "params": params,
            "id": "1",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{agent_url}/execute",
                json=message,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    def run(self, host: str = "127.0.0.1"):
        """Run the FastAPI server.

        Args:
            host: Host to bind to
        """
        import uvicorn
        uvicorn.run(self.app, host=host, port=self.port)
