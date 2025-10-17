# Agent Development Guide

> Step-by-step guide to building A2A-compliant agents with real code examples

## Quick Start: Your First Agent in 5 Minutes

```python
# minimal_agent.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI()

class AgentCard(BaseModel):
    name: str = "minimal-agent"
    url: str = "http://localhost:8000"
    skills: list = [
        {
            "id": "echo",
            "description": "Echoes input back",
            "input_schema": {"type": "object", "properties": {"message": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"echo": {"type": "string"}}}
        }
    ]

@app.get("/agent-card")
async def get_agent_card() -> AgentCard:
    return AgentCard()

@app.post("/execute")
async def execute(request: Dict[str, Any]) -> Dict[str, Any]:
    if request["method"] == "echo":
        return {
            "jsonrpc": "2.0",
            "result": {"echo": request["params"]["message"]},
            "id": request["id"]
        }
    return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": request["id"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run it: `python minimal_agent.py`

Test it:
```bash
curl http://localhost:8000/agent-card
curl -X POST http://localhost:8000/execute -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"echo","params":{"message":"Hello!"},"id":"1"}'
```

## Complete Agent Template

Here's a production-ready agent template with error handling, validation, and logging:

```python
#!/usr/bin/env python3
"""
Template for building A2A-compliant agents.
Copy this file and modify for your use case.
"""

import asyncio
import json
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
import httpx
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class SkillDefinition(BaseModel):
    """Defines a single skill capability"""
    id: str = Field(..., description="Unique skill identifier")
    description: str = Field(..., description="Human-readable description")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for input")
    output_schema: Dict[str, Any] = Field(..., description="JSON Schema for output")
    examples: Optional[List[Dict[str, Any]]] = Field(None, description="Usage examples")

class AgentCard(BaseModel):
    """Agent metadata and capabilities"""
    name: str = Field(..., description="Agent name")
    url: str = Field(..., description="Agent base URL")
    version: str = Field(default="1.0.0", description="Agent version")
    description: Optional[str] = Field(None, description="Agent description")
    skills: List[SkillDefinition] = Field(..., description="Available skills")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request format"""
    jsonrpc: str = Field(default="2.0", pattern="^2\\.0$")
    method: str = Field(..., description="Skill ID to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Skill parameters")
    id: str = Field(..., description="Request ID")

class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response format"""
    jsonrpc: str = Field(default="2.0", pattern="^2\\.0$")
    result: Optional[Dict[str, Any]] = Field(None, description="Success result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details")
    id: str = Field(..., description="Request ID matching request")

# ============================================================================
# BASE AGENT CLASS
# ============================================================================

class BaseAgent(ABC):
    """
    Abstract base class for A2A agents.
    Inherit from this class and implement execute_skill().
    """

    def __init__(
        self,
        name: str,
        port: int,
        skills: List[SkillDefinition],
        description: Optional[str] = None,
        version: str = "1.0.0",
        enable_cors: bool = True,
        log_requests: bool = True
    ):
        self.name = name
        self.port = port
        self.url = f"http://localhost:{port}"
        self.version = version
        self.description = description or f"A2A-compliant {name}"
        self.skills = skills
        self.log_requests = log_requests

        # Create skill lookup map
        self.skill_map = {skill.id: skill for skill in skills}

        # Initialize FastAPI app
        self.app = FastAPI(
            title=name,
            version=version,
            description=self.description
        )

        # Add CORS if enabled
        if enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_methods=["*"],
                allow_headers=["*"]
            )

        # Setup routes
        self._setup_routes()

        # Initialize metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "skill_metrics": {skill.id: {"count": 0, "errors": 0} for skill in skills}
        }

    def _setup_routes(self):
        """Configure A2A protocol endpoints"""

        @self.app.get("/")
        async def root():
            """Root endpoint with basic info"""
            return {
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "endpoints": ["/agent-card", "/execute", "/health", "/metrics"]
            }

        @self.app.get("/agent-card", response_model=AgentCard)
        async def get_agent_card() -> AgentCard:
            """Return agent capabilities"""
            return AgentCard(
                name=self.name,
                url=self.url,
                version=self.version,
                description=self.description,
                skills=self.skills,
                metadata={
                    "created_at": datetime.utcnow().isoformat(),
                    "metrics": self.metrics
                }
            )

        @self.app.post("/execute", response_model=JSONRPCResponse)
        async def execute(request: JSONRPCRequest) -> JSONRPCResponse:
            """Execute a skill via JSON-RPC"""
            start_time = datetime.utcnow()
            skill_id = request.method

            # Log request if enabled
            if self.log_requests:
                logger.info(f"Executing skill '{skill_id}' with params: {request.params}")

            # Update metrics
            self.metrics["total_requests"] += 1

            try:
                # Validate skill exists
                if skill_id not in self.skill_map:
                    self.metrics["failed_requests"] += 1
                    return JSONRPCResponse(
                        id=request.id,
                        error={
                            "code": -32601,
                            "message": f"Method not found: {skill_id}",
                            "data": {"available_skills": list(self.skill_map.keys())}
                        }
                    )

                # Validate parameters against schema
                skill = self.skill_map[skill_id]
                if not self._validate_params(request.params, skill.input_schema):
                    self.metrics["failed_requests"] += 1
                    self.metrics["skill_metrics"][skill_id]["errors"] += 1
                    return JSONRPCResponse(
                        id=request.id,
                        error={
                            "code": -32602,
                            "message": "Invalid parameters",
                            "data": {"expected_schema": skill.input_schema}
                        }
                    )

                # Execute skill
                result = await self.execute_skill(skill_id, request.params)

                # Validate output against schema
                if not self._validate_params(result, skill.output_schema):
                    logger.warning(f"Skill '{skill_id}' returned invalid output schema")

                # Update success metrics
                self.metrics["successful_requests"] += 1
                self.metrics["skill_metrics"][skill_id]["count"] += 1

                # Log success
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Skill '{skill_id}' completed in {duration:.2f}s")

                return JSONRPCResponse(
                    id=request.id,
                    result=result
                )

            except ValidationError as e:
                self.metrics["failed_requests"] += 1
                self.metrics["skill_metrics"][skill_id]["errors"] += 1
                logger.error(f"Validation error in skill '{skill_id}': {e}")
                return JSONRPCResponse(
                    id=request.id,
                    error={
                        "code": -32602,
                        "message": "Invalid parameters",
                        "data": {"validation_errors": e.errors()}
                    }
                )

            except Exception as e:
                self.metrics["failed_requests"] += 1
                self.metrics["skill_metrics"][skill_id]["errors"] += 1
                logger.error(f"Error executing skill '{skill_id}': {e}", exc_info=True)
                return JSONRPCResponse(
                    id=request.id,
                    error={
                        "code": -32603,
                        "message": "Internal error",
                        "data": {"error": str(e)}
                    }
                )

        @self.app.get("/health")
        async def health():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "agent": self.name,
                "version": self.version
            }

        @self.app.get("/metrics")
        async def metrics():
            """Return agent metrics"""
            return self.metrics

    def _validate_params(self, params: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        Basic JSON Schema validation.
        In production, use jsonschema library for full validation.
        """
        if schema.get("type") != "object":
            return True

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        for field in required:
            if field not in params:
                return False

        # Check field types (basic validation)
        for field, value in params.items():
            if field in properties:
                expected_type = properties[field].get("type")
                if expected_type:
                    if expected_type == "string" and not isinstance(value, str):
                        return False
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        return False
                    elif expected_type == "integer" and not isinstance(value, int):
                        return False
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        return False
                    elif expected_type == "array" and not isinstance(value, list):
                        return False
                    elif expected_type == "object" and not isinstance(value, dict):
                        return False

        return True

    @abstractmethod
    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement this method to execute skills.

        Args:
            skill_id: The skill to execute
            params: Parameters for the skill

        Returns:
            Dict containing the skill execution result

        Raises:
            Exception: Any error during execution
        """
        pass

    async def call_agent_skill(
        self,
        agent_url: str,
        skill_id: str,
        params: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Helper method to call another agent's skill.

        Args:
            agent_url: Base URL of the target agent
            skill_id: Skill to execute
            params: Parameters for the skill
            timeout: Request timeout in seconds

        Returns:
            Result from the agent

        Raises:
            RuntimeError: If the agent call fails
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            request = JSONRPCRequest(
                method=skill_id,
                params=params,
                id=f"{self.name}-to-{skill_id}-{datetime.utcnow().timestamp()}"
            )

            try:
                response = await client.post(
                    f"{agent_url}/execute",
                    json=request.dict()
                )
                response.raise_for_status()
            except httpx.RequestError as e:
                raise RuntimeError(f"Failed to call agent at {agent_url}: {e}")

            rpc_response = JSONRPCResponse(**response.json())

            if rpc_response.error:
                raise RuntimeError(
                    f"Agent error from {agent_url}: {rpc_response.error}"
                )

            return rpc_response.result

    async def call_llm(
        self,
        system_prompt: str,
        user_message: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Helper method to call an LLM (replace with your LLM integration).

        This is a placeholder - implement based on your LLM provider:
        - OpenAI API
        - Anthropic Claude
        - Local models (Ollama, llama.cpp)
        - Cloud providers (Bedrock, Vertex AI)
        """
        # Example using subprocess to call claude CLI (as in original code)
        try:
            prompt = f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:"

            # This assumes claude CLI is installed
            result = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                "--dangerously-skip-permissions",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate(input=prompt.encode())

            if result.returncode != 0:
                raise RuntimeError(f"LLM call failed: {stderr.decode()}")

            return stdout.decode().strip()

        except FileNotFoundError:
            # Fallback to mock response if claude CLI not available
            logger.warning("Claude CLI not found, returning mock response")
            return f"[Mock LLM response for: {user_message}]"

    def run(self, host: str = "0.0.0.0", reload: bool = False):
        """Start the agent server"""
        logger.info(f"Starting {self.name} on port {self.port}")
        logger.info(f"Agent card available at: http://localhost:{self.port}/agent-card")

        uvicorn.run(
            self.app,
            host=host,
            port=self.port,
            reload=reload,
            log_level="info"
        )

# ============================================================================
# EXAMPLE IMPLEMENTATIONS
# ============================================================================

class ExampleTextAgent(BaseAgent):
    """
    Example agent that provides text processing skills.
    Replace with your domain-specific implementation.
    """

    def __init__(self):
        skills = [
            SkillDefinition(
                id="count_words",
                description="Counts words in text",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to analyze"}
                    },
                    "required": ["text"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "word_count": {"type": "integer"},
                        "char_count": {"type": "integer"},
                        "line_count": {"type": "integer"}
                    }
                },
                examples=[
                    {
                        "input": {"text": "Hello world"},
                        "output": {"word_count": 2, "char_count": 11, "line_count": 1}
                    }
                ]
            ),
            SkillDefinition(
                id="extract_keywords",
                description="Extracts keywords from text",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "max_keywords": {"type": "integer", "default": 5}
                    },
                    "required": ["text"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            ),
            SkillDefinition(
                id="summarize",
                description="Summarizes text content",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "max_length": {"type": "integer", "default": 100}
                    },
                    "required": ["text"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "original_length": {"type": "integer"},
                        "summary_length": {"type": "integer"}
                    }
                }
            )
        ]

        super().__init__(
            name="text-processor",
            port=8001,
            skills=skills,
            description="Agent for text analysis and processing"
        )

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute text processing skills"""

        if skill_id == "count_words":
            text = params["text"]
            return {
                "word_count": len(text.split()),
                "char_count": len(text),
                "line_count": text.count('\n') + 1
            }

        elif skill_id == "extract_keywords":
            text = params["text"]
            max_keywords = params.get("max_keywords", 5)

            # Simple keyword extraction (replace with NLP library)
            words = text.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Simple filter
                    word_freq[word] = word_freq.get(word, 0) + 1

            keywords = sorted(word_freq.keys(), key=word_freq.get, reverse=True)[:max_keywords]

            return {"keywords": keywords}

        elif skill_id == "summarize":
            text = params["text"]
            max_length = params.get("max_length", 100)

            # Use LLM for summarization
            summary = await self.call_llm(
                system_prompt="You are a text summarizer. Create concise summaries.",
                user_message=f"Summarize this text in {max_length} characters or less: {text}"
            )

            return {
                "summary": summary[:max_length],
                "original_length": len(text),
                "summary_length": len(summary)
            }

        else:
            raise ValueError(f"Unknown skill: {skill_id}")

# ============================================================================
# LLM-POWERED AGENT EXAMPLE
# ============================================================================

class LLMAgent(BaseAgent):
    """
    Example of an agent powered by an LLM for dynamic capabilities.
    """

    def __init__(self, llm_provider: str = "claude"):
        skills = [
            SkillDefinition(
                id="generate_content",
                description="Generates content based on instructions",
                input_schema={
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string"},
                        "style": {"type": "string", "enum": ["formal", "casual", "technical"]},
                        "length": {"type": "string", "enum": ["short", "medium", "long"]}
                    },
                    "required": ["instruction"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "metadata": {"type": "object"}
                    }
                }
            ),
            SkillDefinition(
                id="answer_question",
                description="Answers questions with reasoning",
                input_schema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "context": {"type": "string"}
                    },
                    "required": ["question"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "confidence": {"type": "number"},
                        "sources": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        ]

        super().__init__(
            name="llm-agent",
            port=8002,
            skills=skills,
            description="LLM-powered agent for content generation"
        )

        self.llm_provider = llm_provider

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute LLM-powered skills"""

        if skill_id == "generate_content":
            instruction = params["instruction"]
            style = params.get("style", "casual")
            length = params.get("length", "medium")

            length_map = {"short": 50, "medium": 200, "long": 500}
            word_count = length_map[length]

            system_prompt = f"""You are a content generator.
            Style: {style}
            Target length: approximately {word_count} words
            Output only the requested content, no explanations."""

            content = await self.call_llm(
                system_prompt=system_prompt,
                user_message=instruction
            )

            return {
                "content": content,
                "metadata": {
                    "style": style,
                    "requested_length": length,
                    "actual_word_count": len(content.split())
                }
            }

        elif skill_id == "answer_question":
            question = params["question"]
            context = params.get("context", "")

            system_prompt = """You are a helpful assistant that answers questions.
            Provide clear, accurate answers with reasoning.
            If you're not sure, say so."""

            user_msg = f"Question: {question}"
            if context:
                user_msg += f"\n\nContext: {context}"

            answer = await self.call_llm(
                system_prompt=system_prompt,
                user_message=user_msg
            )

            # Parse structured response (in production, enforce JSON output from LLM)
            return {
                "answer": answer,
                "confidence": 0.8,  # Would be computed based on LLM response
                "sources": []  # Would be extracted from context
            }

        else:
            raise ValueError(f"Unknown skill: {skill_id}")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import sys

    # Choose which agent to run
    if len(sys.argv) > 1:
        agent_type = sys.argv[1]
    else:
        agent_type = "example"

    if agent_type == "text":
        agent = ExampleTextAgent()
    elif agent_type == "llm":
        agent = LLMAgent()
    else:
        agent = ExampleTextAgent()

    # Run the agent
    agent.run(reload=True)  # Enable reload for development
```

## Agent Development Workflow

### 1. Define Your Skills

Start by defining what your agent can do:

```python
skills = [
    SkillDefinition(
        id="process_data",
        description="Processes input data",
        input_schema={
            "type": "object",
            "properties": {
                "data": {"type": "array"},
                "operation": {"type": "string"}
            },
            "required": ["data", "operation"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "result": {"type": "array"},
                "statistics": {"type": "object"}
            }
        }
    )
]
```

### 2. Implement Skill Logic

```python
async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if skill_id == "process_data":
        data = params["data"]
        operation = params["operation"]

        if operation == "sort":
            result = sorted(data)
        elif operation == "reverse":
            result = list(reversed(data))
        elif operation == "unique":
            result = list(set(data))
        else:
            raise ValueError(f"Unknown operation: {operation}")

        return {
            "result": result,
            "statistics": {
                "input_count": len(data),
                "output_count": len(result),
                "operation": operation
            }
        }
```

### 3. Add Error Handling

```python
async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        # Skill implementation
        result = await self._process_data(params)
        return result
    except ValueError as e:
        # Known errors - return error response
        logger.warning(f"Invalid input for {skill_id}: {e}")
        raise
    except Exception as e:
        # Unexpected errors - log and re-raise
        logger.error(f"Unexpected error in {skill_id}: {e}", exc_info=True)
        raise RuntimeError(f"Internal error processing {skill_id}")
```

### 4. Test Your Agent

```python
# test_agent.py
import pytest
import httpx
import asyncio

@pytest.fixture
async def agent_client():
    """Fixture to provide HTTP client for agent"""
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        yield client

@pytest.mark.asyncio
async def test_agent_card(agent_client):
    """Test agent card endpoint"""
    response = await agent_client.get("/agent-card")
    assert response.status_code == 200

    card = response.json()
    assert "name" in card
    assert "skills" in card
    assert len(card["skills"]) > 0

@pytest.mark.asyncio
async def test_skill_execution(agent_client):
    """Test skill execution"""
    request = {
        "jsonrpc": "2.0",
        "method": "process_data",
        "params": {
            "data": [3, 1, 4, 1, 5],
            "operation": "sort"
        },
        "id": "test-1"
    }

    response = await agent_client.post("/execute", json=request)
    assert response.status_code == 200

    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert "result" in result
    assert result["result"]["result"] == [1, 1, 3, 4, 5]

@pytest.mark.asyncio
async def test_invalid_skill(agent_client):
    """Test error handling for invalid skill"""
    request = {
        "jsonrpc": "2.0",
        "method": "invalid_skill",
        "params": {},
        "id": "test-2"
    }

    response = await agent_client.post("/execute", json=request)
    assert response.status_code == 200

    result = response.json()
    assert "error" in result
    assert result["error"]["code"] == -32601
```

### 5. Deploy Your Agent

#### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY agent.py .

# Expose port
EXPOSE 8001

# Run agent
CMD ["python", "agent.py"]
```

```bash
# Build and run
docker build -t my-agent:v1 .
docker run -d -p 8001:8001 --name my-agent my-agent:v1
```

#### Docker Compose for Multiple Agents

```yaml
# docker-compose.yml
version: '3.8'

services:
  text-agent:
    build: ./agents/text
    ports:
      - "8001:8001"
    environment:
      - AGENT_NAME=text-processor
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  llm-agent:
    build: ./agents/llm
    ports:
      - "8002:8002"
    environment:
      - AGENT_NAME=llm-agent
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - text-agent

  orchestrator:
    build: ./orchestrator
    ports:
      - "8000:8000"
    depends_on:
      - text-agent
      - llm-agent
    environment:
      - DISCOVERY_URL=http://registry:5000

  registry:
    image: registry:2
    ports:
      - "5000:5000"
```

## Best Practices

### 1. Skill Design

- **Single Responsibility**: Each skill should do one thing well
- **Clear Naming**: Use descriptive, action-oriented names (`translate_text`, not `text`)
- **Comprehensive Schemas**: Define complete input/output schemas
- **Provide Examples**: Include example inputs/outputs in skill definitions

### 2. Error Handling

- **Validate Early**: Check parameters before processing
- **Specific Errors**: Use appropriate JSON-RPC error codes
- **Log Everything**: Log requests, errors, and performance metrics
- **Graceful Degradation**: Handle partial failures when possible

### 3. Performance

- **Async Operations**: Use async/await for I/O operations
- **Connection Pooling**: Reuse HTTP connections
- **Caching**: Cache expensive computations
- **Timeouts**: Set appropriate timeouts for external calls

### 4. Security

- **Input Validation**: Always validate against schemas
- **Rate Limiting**: Implement per-client rate limits
- **Authentication**: Add API key or JWT authentication
- **Audit Logging**: Log all requests for security analysis

### 5. Testing

- **Unit Tests**: Test individual skills
- **Integration Tests**: Test agent interactions
- **Load Testing**: Verify performance under load
- **Contract Testing**: Ensure schema compliance

## Common Patterns

### Pattern 1: Stateful Agent

```python
class StatefulAgent(BaseAgent):
    """Agent that maintains state across requests"""

    def __init__(self):
        super().__init__(...)
        self.sessions = {}  # Store session state

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        session_id = params.get("session_id", "default")

        # Get or create session state
        if session_id not in self.sessions:
            self.sessions[session_id] = {"history": [], "context": {}}

        session = self.sessions[session_id]

        # Process with state
        result = await self._process_with_state(params, session)

        # Update state
        session["history"].append({"params": params, "result": result})

        return result
```

### Pattern 2: Streaming Agent

```python
from fastapi.responses import StreamingResponse
import asyncio

class StreamingAgent(BaseAgent):
    """Agent that streams responses"""

    def _setup_routes(self):
        super()._setup_routes()

        @self.app.post("/stream")
        async def stream_execute(request: JSONRPCRequest):
            """Execute skill with streaming response"""

            async def generate():
                # Stream results as they're generated
                for chunk in await self._generate_chunks(request.params):
                    yield json.dumps({"chunk": chunk}) + "\n"
                    await asyncio.sleep(0.1)  # Rate limiting

            return StreamingResponse(generate(), media_type="application/x-ndjson")
```

### Pattern 3: Batch Processing Agent

```python
class BatchAgent(BaseAgent):
    """Agent that processes multiple items efficiently"""

    def __init__(self):
        skills = [
            SkillDefinition(
                id="process_batch",
                description="Process multiple items",
                input_schema={
                    "type": "object",
                    "properties": {
                        "items": {"type": "array"},
                        "parallel": {"type": "boolean", "default": True}
                    }
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                        "failed": {"type": "array"}
                    }
                }
            )
        ]
        super().__init__(...)

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if skill_id == "process_batch":
            items = params["items"]
            parallel = params.get("parallel", True)

            if parallel:
                # Process items in parallel
                tasks = [self._process_item(item) for item in items]
                results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Process items sequentially
                results = []
                for item in items:
                    try:
                        result = await self._process_item(item)
                        results.append(result)
                    except Exception as e:
                        results.append(e)

            # Separate successful and failed results
            successful = [r for r in results if not isinstance(r, Exception)]
            failed = [{"item": items[i], "error": str(r)}
                     for i, r in enumerate(results) if isinstance(r, Exception)]

            return {
                "results": successful,
                "failed": failed
            }
```

## Troubleshooting Guide

### Agent Won't Start

```bash
# Check if port is in use
lsof -i :8001

# Check Python dependencies
pip list | grep fastapi

# Run with debug logging
python -u agent.py  # Unbuffered output
```

### Agent Card Not Found

```python
# Verify endpoint is registered
@app.get("/agent-card")  # Must be exactly this path

# Check CORS if accessing from browser
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

### Skill Execution Fails

```python
# Add debug logging
logger.debug(f"Received params: {params}")
logger.debug(f"Skill map: {self.skill_map.keys()}")

# Validate JSON-RPC format
assert request.jsonrpc == "2.0"
assert request.method in self.skill_map
```

### Performance Issues

```python
# Profile slow operations
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# ... your code ...
profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumulative')
stats.print_stats(10)

# Use async correctly
# Bad: Blocking
result = requests.get(url).json()

# Good: Non-blocking
async with httpx.AsyncClient() as client:
    result = await client.get(url)
```

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Validation](https://docs.pydantic.dev/)
- [JSON-RPC 2.0 Spec](https://www.jsonrpc.org/specification)
- [httpx Async Client](https://www.python-httpx.org/)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)