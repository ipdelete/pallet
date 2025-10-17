# Orchestration Patterns

> Design patterns and strategies for composing AI agents into complex workflows

## Table of Contents
1. [Introduction](#introduction)
2. [Core Orchestration Patterns](#core-orchestration-patterns)
3. [Implementation Examples](#implementation-examples)
4. [Domain-Specific Workflows](#domain-specific-workflows)
5. [Error Handling Strategies](#error-handling-strategies)
6. [Performance Optimization](#performance-optimization)
7. [Testing and Validation](#testing-and-validation)
8. [Production Considerations](#production-considerations)

## Introduction

Orchestration is the art of coordinating multiple agents to achieve complex goals. Just as a conductor coordinates musicians in an orchestra, an orchestrator coordinates AI agents to create harmonious workflows.

### Key Principles

1. **Composition Over Complexity**: Build complex behaviors by composing simple agents
2. **Loose Coupling**: Agents should be independent and communicate through well-defined interfaces
3. **Fault Tolerance**: Workflows should handle agent failures gracefully
4. **Observability**: Track workflow execution and performance
5. **Flexibility**: Support dynamic workflow modification

## Core Orchestration Patterns

### 1. Sequential Pipeline (Chain)

Agents execute in a strict sequence, with each agent's output feeding the next agent's input.

```python
# Pattern: A → B → C → Result
class SequentialPipeline:
    """Execute agents in sequence"""

    async def execute(self, agents: List[str], initial_input: Any) -> Any:
        result = initial_input
        for agent_url in agents:
            result = await call_agent(agent_url, result)
        return result
```

**Use Cases:**
- Document processing: Parse → Extract → Transform → Store
- Translation pipeline: Detect language → Translate → Quality check
- Data ETL: Extract → Transform → Load

### 2. Parallel Execution (Fan-out/Fan-in)

Multiple agents execute simultaneously, with results combined.

```python
# Pattern:     ┌→ B →┐
#         A → ├→ C →┤ → E
#             └→ D →┘

class ParallelExecution:
    """Execute agents in parallel"""

    async def execute(self, agents: List[str], input_data: Any) -> List[Any]:
        tasks = [call_agent(agent_url, input_data) for agent_url in agents]
        results = await asyncio.gather(*tasks)
        return results
```

**Use Cases:**
- Multi-model ensemble: Run multiple ML models in parallel
- Content analysis: Sentiment + Entities + Topics simultaneously
- Multi-language translation: Translate to multiple languages at once

### 3. Conditional Routing (Switch)

Route to different agents based on conditions.

```python
# Pattern: A → [condition] → B or C or D

class ConditionalRouter:
    """Route based on conditions"""

    async def execute(self, input_data: Any, rules: List[Rule]) -> Any:
        for rule in rules:
            if evaluate_condition(input_data, rule.condition):
                return await call_agent(rule.agent_url, input_data)
        return await call_agent(default_agent, input_data)
```

**Use Cases:**
- Language-specific processing: Route based on detected language
- Expertise routing: Route medical images to specialized analyzers
- Load balancing: Route based on agent availability

### 4. Map-Reduce

Process collections by mapping operations across items, then reducing results.

```python
# Pattern: Collection → Map(process each) → Reduce(combine)

class MapReduce:
    """Map-reduce pattern for collections"""

    async def execute(self, items: List[Any], map_agent: str, reduce_agent: str) -> Any:
        # Map phase: Process each item
        mapped_tasks = [call_agent(map_agent, item) for item in items]
        mapped_results = await asyncio.gather(*mapped_tasks)

        # Reduce phase: Combine results
        return await call_agent(reduce_agent, mapped_results)
```

**Use Cases:**
- Batch document processing: Process each document, then summarize
- Distributed analysis: Analyze data shards, then aggregate
- Survey processing: Process responses, then generate statistics

### 5. Saga (Long-Running Transactions)

Coordinate long-running workflows with compensation for failures.

```python
# Pattern: A → B → C (with compensations: C' → B' → A')

class Saga:
    """Long-running transaction with compensations"""

    async def execute(self, steps: List[Step]) -> Any:
        completed = []
        try:
            for step in steps:
                result = await call_agent(step.agent, step.params)
                completed.append((step, result))
        except Exception as e:
            # Compensate in reverse order
            for step, _ in reversed(completed):
                if step.compensation:
                    await call_agent(step.compensation.agent, step.compensation.params)
            raise
        return [r for _, r in completed]
```

**Use Cases:**
- Order processing: Reserve inventory → Charge payment → Ship (with reversals)
- Multi-step workflows: Where each step must be undoable
- Distributed transactions: Across multiple services

### 6. Recursive Decomposition

Break complex tasks into subtasks recursively.

```python
# Pattern: Task → Decompose → Subtasks → Recurse → Combine

class RecursiveDecomposition:
    """Recursively decompose and solve"""

    async def execute(self, task: Any, decompose_agent: str, solve_agent: str) -> Any:
        # Check if task is simple enough to solve directly
        if await is_simple(task):
            return await call_agent(solve_agent, task)

        # Decompose into subtasks
        subtasks = await call_agent(decompose_agent, task)

        # Recursively solve subtasks
        results = []
        for subtask in subtasks:
            result = await self.execute(subtask, decompose_agent, solve_agent)
            results.append(result)

        # Combine results
        return await combine_results(results)
```

**Use Cases:**
- Complex problem solving: Break down and solve piece by piece
- Document analysis: Analyze sections recursively
- Code generation: Generate complex systems module by module

### 7. Event-Driven Choreography

Agents react to events without central coordination.

```python
# Pattern: Event → Multiple agents react independently

class EventDrivenChoreography:
    """Event-driven agent coordination"""

    def __init__(self):
        self.event_subscriptions = {}  # event_type -> [agent_urls]

    async def publish_event(self, event_type: str, data: Any):
        """Publish event to subscribed agents"""
        subscribers = self.event_subscriptions.get(event_type, [])
        tasks = [call_agent(agent, data) for agent in subscribers]
        await asyncio.gather(*tasks, return_exceptions=True)

    def subscribe(self, event_type: str, agent_url: str):
        """Subscribe agent to event type"""
        if event_type not in self.event_subscriptions:
            self.event_subscriptions[event_type] = []
        self.event_subscriptions[event_type].append(agent_url)
```

**Use Cases:**
- Real-time monitoring: Multiple agents react to sensor data
- Microservices: Decoupled event-driven architecture
- Notification systems: Multiple handlers for events

## Implementation Examples

### Complete Orchestrator Implementation

```python
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import httpx
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Data Models
# ============================================================================

class ExecutionStrategy(Enum):
    """Workflow execution strategies"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    MAP_REDUCE = "map_reduce"
    SAGA = "saga"

@dataclass
class AgentCall:
    """Represents a call to an agent"""
    agent_url: str
    skill_id: str
    params: Dict[str, Any]
    timeout: float = 30.0
    retry_count: int = 3
    compensation: Optional['AgentCall'] = None  # For saga pattern

@dataclass
class WorkflowStep:
    """A step in a workflow"""
    name: str
    agent_calls: List[AgentCall]
    strategy: ExecutionStrategy
    condition: Optional[Callable] = None
    on_error: Optional[str] = None  # "fail", "skip", "compensate"

@dataclass
class WorkflowDefinition:
    """Complete workflow definition"""
    name: str
    version: str
    description: str
    steps: List[WorkflowStep]
    metadata: Dict[str, Any] = None

# ============================================================================
# Orchestrator Implementation
# ============================================================================

class Orchestrator:
    """
    Advanced orchestrator supporting multiple patterns.
    """

    def __init__(
        self,
        discovery_url: Optional[str] = None,
        max_concurrent: int = 10,
        default_timeout: float = 30.0
    ):
        self.discovery_url = discovery_url
        self.max_concurrent = max_concurrent
        self.default_timeout = default_timeout
        self.execution_history = []
        self.metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_agent_calls": 0,
            "average_execution_time": 0
        }

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow.

        Args:
            workflow: The workflow definition
            initial_input: Initial input data

        Returns:
            Final workflow result
        """
        start_time = datetime.utcnow()
        execution_id = f"{workflow.name}-{start_time.timestamp()}"

        logger.info(f"Starting workflow execution: {execution_id}")
        self.metrics["total_executions"] += 1

        try:
            context = {
                "input": initial_input,
                "results": {},
                "execution_id": execution_id,
                "workflow": workflow.name
            }

            # Execute each step
            for step in workflow.steps:
                logger.info(f"Executing step: {step.name}")
                step_result = await self._execute_step(step, context)
                context["results"][step.name] = step_result
                context["last_result"] = step_result

            # Success
            self.metrics["successful_executions"] += 1
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_metrics(execution_time)

            result = {
                "status": "success",
                "execution_id": execution_id,
                "workflow": workflow.name,
                "results": context["results"],
                "execution_time": execution_time
            }

            self._record_execution(result)
            return result

        except Exception as e:
            # Failure
            self.metrics["failed_executions"] += 1
            logger.error(f"Workflow execution failed: {e}", exc_info=True)

            result = {
                "status": "failed",
                "execution_id": execution_id,
                "workflow": workflow.name,
                "error": str(e),
                "execution_time": (datetime.utcnow() - start_time).total_seconds()
            }

            self._record_execution(result)
            raise

    async def _execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Any:
        """Execute a single workflow step"""
        if step.strategy == ExecutionStrategy.SEQUENTIAL:
            return await self._execute_sequential(step.agent_calls, context)

        elif step.strategy == ExecutionStrategy.PARALLEL:
            return await self._execute_parallel(step.agent_calls, context)

        elif step.strategy == ExecutionStrategy.CONDITIONAL:
            return await self._execute_conditional(step, context)

        elif step.strategy == ExecutionStrategy.MAP_REDUCE:
            return await self._execute_map_reduce(step, context)

        elif step.strategy == ExecutionStrategy.SAGA:
            return await self._execute_saga(step.agent_calls, context)

        else:
            raise ValueError(f"Unknown strategy: {step.strategy}")

    async def _execute_sequential(
        self,
        calls: List[AgentCall],
        context: Dict[str, Any]
    ) -> Any:
        """Execute agent calls sequentially"""
        result = context.get("last_result", context["input"])

        for call in calls:
            params = self._resolve_params(call.params, context, result)
            result = await self._call_agent_with_retry(
                call.agent_url,
                call.skill_id,
                params,
                call.timeout,
                call.retry_count
            )

        return result

    async def _execute_parallel(
        self,
        calls: List[AgentCall],
        context: Dict[str, Any]
    ) -> List[Any]:
        """Execute agent calls in parallel"""
        tasks = []
        for call in calls:
            params = self._resolve_params(call.params, context, context.get("last_result"))
            task = self._call_agent_with_retry(
                call.agent_url,
                call.skill_id,
                params,
                call.timeout,
                call.retry_count
            )
            tasks.append(task)

        return await asyncio.gather(*tasks)

    async def _execute_conditional(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Any:
        """Execute conditional routing"""
        for call in step.agent_calls:
            if step.condition and step.condition(context):
                params = self._resolve_params(call.params, context, context.get("last_result"))
                return await self._call_agent_with_retry(
                    call.agent_url,
                    call.skill_id,
                    params,
                    call.timeout,
                    call.retry_count
                )

        # No condition matched
        return None

    async def _execute_map_reduce(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Any:
        """Execute map-reduce pattern"""
        if len(step.agent_calls) != 2:
            raise ValueError("Map-reduce requires exactly 2 agent calls (map and reduce)")

        map_call = step.agent_calls[0]
        reduce_call = step.agent_calls[1]

        # Assume input is a collection
        items = context.get("last_result", context["input"])
        if not isinstance(items, list):
            raise ValueError("Map-reduce requires list input")

        # Map phase
        map_tasks = []
        for item in items:
            params = self._resolve_params(map_call.params, context, item)
            task = self._call_agent_with_retry(
                map_call.agent_url,
                map_call.skill_id,
                params,
                map_call.timeout,
                map_call.retry_count
            )
            map_tasks.append(task)

        mapped_results = await asyncio.gather(*map_tasks)

        # Reduce phase
        reduce_params = self._resolve_params(reduce_call.params, context, mapped_results)
        return await self._call_agent_with_retry(
            reduce_call.agent_url,
            reduce_call.skill_id,
            reduce_params,
            reduce_call.timeout,
            reduce_call.retry_count
        )

    async def _execute_saga(
        self,
        calls: List[AgentCall],
        context: Dict[str, Any]
    ) -> Any:
        """Execute saga pattern with compensations"""
        completed = []
        result = context.get("last_result", context["input"])

        try:
            for call in calls:
                params = self._resolve_params(call.params, context, result)
                result = await self._call_agent_with_retry(
                    call.agent_url,
                    call.skill_id,
                    params,
                    call.timeout,
                    call.retry_count
                )
                completed.append((call, result))

            return [r for _, r in completed]

        except Exception as e:
            # Execute compensations in reverse order
            logger.warning(f"Saga failed, executing compensations: {e}")

            for call, original_result in reversed(completed):
                if call.compensation:
                    try:
                        comp_params = self._resolve_params(
                            call.compensation.params,
                            context,
                            original_result
                        )
                        await self._call_agent_with_retry(
                            call.compensation.agent_url,
                            call.compensation.skill_id,
                            comp_params,
                            call.compensation.timeout,
                            call.compensation.retry_count
                        )
                        logger.info(f"Compensation executed for {call.skill_id}")
                    except Exception as comp_error:
                        logger.error(f"Compensation failed: {comp_error}")

            raise

    async def _call_agent_with_retry(
        self,
        agent_url: str,
        skill_id: str,
        params: Dict[str, Any],
        timeout: float,
        max_retries: int
    ) -> Any:
        """Call an agent with retry logic"""
        last_error = None

        for attempt in range(max_retries):
            try:
                return await self._call_agent(agent_url, skill_id, params, timeout)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)

        raise last_error

    async def _call_agent(
        self,
        agent_url: str,
        skill_id: str,
        params: Dict[str, Any],
        timeout: float
    ) -> Any:
        """Make a single agent call"""
        self.metrics["total_agent_calls"] += 1

        async with httpx.AsyncClient(timeout=timeout) as client:
            request = {
                "jsonrpc": "2.0",
                "method": skill_id,
                "params": params,
                "id": f"orch-{skill_id}-{datetime.utcnow().timestamp()}"
            }

            logger.debug(f"Calling {agent_url} with skill {skill_id}")

            response = await client.post(
                f"{agent_url}/execute",
                json=request
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                raise RuntimeError(f"Agent error: {result['error']}")

            return result.get("result")

    def _resolve_params(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any],
        current_data: Any
    ) -> Dict[str, Any]:
        """
        Resolve parameters with context references.

        Supports:
        - Direct values: {"key": "value"}
        - Context references: {"key": "$context.results.step1"}
        - Current data: {"key": "$current"}
        """
        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$"):
                # Resolve reference
                if value == "$current":
                    resolved[key] = current_data
                elif value.startswith("$context."):
                    path = value[9:].split(".")
                    resolved[key] = self._get_nested(context, path)
                else:
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved

    def _get_nested(self, data: Dict, path: List[str]) -> Any:
        """Get nested value from dictionary"""
        current = data
        for key in path:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current

    def _update_metrics(self, execution_time: float):
        """Update metrics"""
        total = self.metrics["successful_executions"]
        current_avg = self.metrics["average_execution_time"]
        self.metrics["average_execution_time"] = \
            (current_avg * (total - 1) + execution_time) / total

    def _record_execution(self, result: Dict[str, Any]):
        """Record execution history"""
        self.execution_history.append(result)
        # Keep only last 100 executions
        if len(self.execution_history) > 100:
            self.execution_history.pop(0)
```

## Domain-Specific Workflows

### Healthcare Workflow

```python
# Medical diagnosis workflow
diagnosis_workflow = WorkflowDefinition(
    name="medical_diagnosis",
    version="1.0",
    description="Complete medical diagnosis pipeline",
    steps=[
        WorkflowStep(
            name="image_analysis",
            agent_calls=[
                AgentCall(
                    agent_url="http://xray-analyzer:8001",
                    skill_id="analyze_xray",
                    params={"image": "$current"}
                ),
                AgentCall(
                    agent_url="http://mri-analyzer:8002",
                    skill_id="analyze_mri",
                    params={"image": "$current"}
                )
            ],
            strategy=ExecutionStrategy.PARALLEL
        ),
        WorkflowStep(
            name="diagnosis",
            agent_calls=[
                AgentCall(
                    agent_url="http://diagnosis-agent:8003",
                    skill_id="generate_diagnosis",
                    params={
                        "xray_results": "$context.results.image_analysis[0]",
                        "mri_results": "$context.results.image_analysis[1]"
                    }
                )
            ],
            strategy=ExecutionStrategy.SEQUENTIAL
        ),
        WorkflowStep(
            name="treatment_plan",
            agent_calls=[
                AgentCall(
                    agent_url="http://treatment-planner:8004",
                    skill_id="create_treatment_plan",
                    params={"diagnosis": "$context.results.diagnosis"}
                )
            ],
            strategy=ExecutionStrategy.SEQUENTIAL
        )
    ]
)
```

### Financial Workflow

```python
# Loan approval workflow with saga pattern
loan_workflow = WorkflowDefinition(
    name="loan_approval",
    version="1.0",
    description="Loan approval with compensations",
    steps=[
        WorkflowStep(
            name="loan_processing",
            agent_calls=[
                AgentCall(
                    agent_url="http://credit-check:8001",
                    skill_id="check_credit",
                    params={"applicant_id": "$current.applicant_id"},
                    compensation=AgentCall(
                        agent_url="http://credit-check:8001",
                        skill_id="release_credit_check",
                        params={"check_id": "$result.check_id"}
                    )
                ),
                AgentCall(
                    agent_url="http://risk-assessment:8002",
                    skill_id="assess_risk",
                    params={"application": "$current"},
                    compensation=AgentCall(
                        agent_url="http://risk-assessment:8002",
                        skill_id="cancel_assessment",
                        params={"assessment_id": "$result.id"}
                    )
                ),
                AgentCall(
                    agent_url="http://loan-processor:8003",
                    skill_id="approve_loan",
                    params={"application": "$current", "risk": "$previous"},
                    compensation=AgentCall(
                        agent_url="http://loan-processor:8003",
                        skill_id="cancel_loan",
                        params={"loan_id": "$result.loan_id"}
                    )
                )
            ],
            strategy=ExecutionStrategy.SAGA
        )
    ]
)
```

### Content Creation Workflow

```python
# Content generation with quality control
content_workflow = WorkflowDefinition(
    name="content_creation",
    version="1.0",
    description="Create and optimize content",
    steps=[
        WorkflowStep(
            name="research",
            agent_calls=[
                AgentCall(
                    agent_url="http://research-agent:8001",
                    skill_id="research_topic",
                    params={"topic": "$current.topic"}
                )
            ],
            strategy=ExecutionStrategy.SEQUENTIAL
        ),
        WorkflowStep(
            name="content_generation",
            agent_calls=[
                AgentCall(
                    agent_url="http://writer-agent:8002",
                    skill_id="write_article",
                    params={
                        "research": "$context.results.research",
                        "style": "$current.style",
                        "length": "$current.length"
                    }
                )
            ],
            strategy=ExecutionStrategy.SEQUENTIAL
        ),
        WorkflowStep(
            name="quality_checks",
            agent_calls=[
                AgentCall(
                    agent_url="http://grammar-checker:8003",
                    skill_id="check_grammar",
                    params={"text": "$context.results.content_generation"}
                ),
                AgentCall(
                    agent_url="http://fact-checker:8004",
                    skill_id="verify_facts",
                    params={
                        "text": "$context.results.content_generation",
                        "sources": "$context.results.research.sources"
                    }
                ),
                AgentCall(
                    agent_url="http://seo-optimizer:8005",
                    skill_id="optimize_seo",
                    params={
                        "text": "$context.results.content_generation",
                        "keywords": "$current.keywords"
                    }
                )
            ],
            strategy=ExecutionStrategy.PARALLEL
        ),
        WorkflowStep(
            name="final_review",
            agent_calls=[
                AgentCall(
                    agent_url="http://editor-agent:8006",
                    skill_id="final_edit",
                    params={
                        "content": "$context.results.content_generation",
                        "grammar_report": "$context.results.quality_checks[0]",
                        "fact_report": "$context.results.quality_checks[1]",
                        "seo_report": "$context.results.quality_checks[2]"
                    }
                )
            ],
            strategy=ExecutionStrategy.SEQUENTIAL
        )
    ]
)
```

## Error Handling Strategies

### Retry with Backoff

```python
class RetryStrategy:
    """Advanced retry strategies"""

    @staticmethod
    async def exponential_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        """Retry with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                delay = min(base_delay * (2 ** attempt), max_delay)
                await asyncio.sleep(delay)

    @staticmethod
    async def circuit_breaker(
        func: Callable,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0
    ):
        """Circuit breaker pattern"""
        failures = 0
        last_failure_time = None

        while True:
            # Check if circuit should be open
            if failures >= failure_threshold:
                if last_failure_time and \
                   time.time() - last_failure_time < recovery_timeout:
                    raise RuntimeError("Circuit breaker is open")
                else:
                    # Try to recover
                    failures = 0

            try:
                result = await func()
                failures = 0  # Reset on success
                return result
            except Exception as e:
                failures += 1
                last_failure_time = time.time()
                raise
```

### Fallback Chains

```python
class FallbackChain:
    """Try multiple agents until one succeeds"""

    async def execute(
        self,
        primary_agent: str,
        fallback_agents: List[str],
        skill_id: str,
        params: Dict[str, Any]
    ) -> Any:
        """Execute with fallback chain"""
        all_agents = [primary_agent] + fallback_agents

        for i, agent_url in enumerate(all_agents):
            try:
                logger.info(f"Trying agent {i+1}/{len(all_agents)}: {agent_url}")
                return await call_agent(agent_url, skill_id, params)
            except Exception as e:
                logger.warning(f"Agent failed: {e}")
                if i == len(all_agents) - 1:
                    raise RuntimeError("All agents in fallback chain failed")
```

## Performance Optimization

### Caching Layer

```python
from functools import lru_cache
import hashlib

class CachedOrchestrator(Orchestrator):
    """Orchestrator with result caching"""

    def __init__(self, *args, cache_size: int = 128, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}
        self._cache_size = cache_size

    def _get_cache_key(self, agent_url: str, skill_id: str, params: Dict) -> str:
        """Generate cache key"""
        key_data = f"{agent_url}:{skill_id}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _call_agent(
        self,
        agent_url: str,
        skill_id: str,
        params: Dict[str, Any],
        timeout: float
    ) -> Any:
        """Call agent with caching"""
        cache_key = self._get_cache_key(agent_url, skill_id, params)

        # Check cache
        if cache_key in self._cache:
            logger.debug(f"Cache hit for {skill_id}")
            return self._cache[cache_key]

        # Cache miss
        result = await super()._call_agent(agent_url, skill_id, params, timeout)

        # Update cache
        self._cache[cache_key] = result
        if len(self._cache) > self._cache_size:
            # Evict oldest entry (simple FIFO)
            oldest = next(iter(self._cache))
            del self._cache[oldest]

        return result
```

### Connection Pooling

```python
class PooledOrchestrator(Orchestrator):
    """Orchestrator with connection pooling"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client_pool = {}

    def _get_client(self, agent_url: str) -> httpx.AsyncClient:
        """Get or create pooled client"""
        if agent_url not in self._client_pool:
            self._client_pool[agent_url] = httpx.AsyncClient(
                base_url=agent_url,
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5
                ),
                timeout=httpx.Timeout(30.0)
            )
        return self._client_pool[agent_url]

    async def cleanup(self):
        """Close all pooled connections"""
        for client in self._client_pool.values():
            await client.aclose()
```

## Testing and Validation

### Workflow Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestOrchestrator:

    @pytest.fixture
    def orchestrator(self):
        return Orchestrator()

    @pytest.fixture
    def sample_workflow(self):
        return WorkflowDefinition(
            name="test_workflow",
            version="1.0",
            description="Test workflow",
            steps=[
                WorkflowStep(
                    name="step1",
                    agent_calls=[
                        AgentCall(
                            agent_url="http://agent1:8001",
                            skill_id="process",
                            params={"data": "$current"}
                        )
                    ],
                    strategy=ExecutionStrategy.SEQUENTIAL
                )
            ]
        )

    @pytest.mark.asyncio
    async def test_sequential_execution(self, orchestrator, sample_workflow):
        """Test sequential workflow execution"""
        with patch.object(orchestrator, '_call_agent') as mock_call:
            mock_call.return_value = {"result": "processed"}

            result = await orchestrator.execute_workflow(
                sample_workflow,
                {"data": "test"}
            )

            assert result["status"] == "success"
            assert "step1" in result["results"]
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_parallel_execution(self, orchestrator):
        """Test parallel execution"""
        calls = [
            AgentCall("http://agent1:8001", "skill1", {}),
            AgentCall("http://agent2:8002", "skill2", {}),
            AgentCall("http://agent3:8003", "skill3", {})
        ]

        with patch.object(orchestrator, '_call_agent') as mock_call:
            mock_call.side_effect = [
                {"result": "r1"},
                {"result": "r2"},
                {"result": "r3"}
            ]

            results = await orchestrator._execute_parallel(calls, {})

            assert len(results) == 3
            assert mock_call.call_count == 3

    @pytest.mark.asyncio
    async def test_saga_compensation(self, orchestrator):
        """Test saga compensation on failure"""
        calls = [
            AgentCall(
                "http://agent1:8001", "step1", {},
                compensation=AgentCall("http://agent1:8001", "undo1", {})
            ),
            AgentCall(
                "http://agent2:8002", "step2", {},
                compensation=AgentCall("http://agent2:8002", "undo2", {})
            )
        ]

        with patch.object(orchestrator, '_call_agent') as mock_call:
            # First call succeeds, second fails
            mock_call.side_effect = [
                {"result": "r1"},  # step1 success
                RuntimeError("step2 failed"),  # step2 failure
                {"result": "compensation1"}  # undo1
            ]

            with pytest.raises(RuntimeError):
                await orchestrator._execute_saga(calls, {})

            # Verify compensation was called
            assert mock_call.call_count == 3
```

### Workflow Validation

```python
class WorkflowValidator:
    """Validate workflow definitions"""

    @staticmethod
    def validate(workflow: WorkflowDefinition) -> List[str]:
        """Validate workflow and return errors"""
        errors = []

        # Check workflow metadata
        if not workflow.name:
            errors.append("Workflow name is required")
        if not workflow.steps:
            errors.append("Workflow must have at least one step")

        # Check each step
        for i, step in enumerate(workflow.steps):
            if not step.name:
                errors.append(f"Step {i}: Name is required")
            if not step.agent_calls:
                errors.append(f"Step {step.name}: Must have at least one agent call")

            # Validate agent calls
            for j, call in enumerate(step.agent_calls):
                if not call.agent_url:
                    errors.append(f"Step {step.name}, Call {j}: Agent URL is required")
                if not call.skill_id:
                    errors.append(f"Step {step.name}, Call {j}: Skill ID is required")

                # Validate compensation if present
                if call.compensation:
                    if not call.compensation.agent_url:
                        errors.append(f"Step {step.name}, Call {j}: Compensation agent URL is required")
                    if not call.compensation.skill_id:
                        errors.append(f"Step {step.name}, Call {j}: Compensation skill ID is required")

        return errors
```

## Production Considerations

### Monitoring and Observability

```python
from prometheus_client import Counter, Histogram, Gauge
import opentelemetry.trace as trace

class MonitoredOrchestrator(Orchestrator):
    """Orchestrator with metrics and tracing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Prometheus metrics
        self.execution_counter = Counter(
            'workflow_executions_total',
            'Total workflow executions',
            ['workflow', 'status']
        )
        self.execution_duration = Histogram(
            'workflow_execution_duration_seconds',
            'Workflow execution duration',
            ['workflow']
        )
        self.active_executions = Gauge(
            'workflow_active_executions',
            'Currently active workflow executions'
        )

        # OpenTelemetry tracer
        self.tracer = trace.get_tracer(__name__)

    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute with monitoring"""
        with self.tracer.start_as_current_span(f"workflow.{workflow.name}") as span:
            span.set_attribute("workflow.name", workflow.name)
            span.set_attribute("workflow.version", workflow.version)

            self.active_executions.inc()

            try:
                with self.execution_duration.labels(workflow.name).time():
                    result = await super().execute_workflow(workflow, initial_input)

                self.execution_counter.labels(workflow.name, "success").inc()
                span.set_attribute("workflow.status", "success")
                return result

            except Exception as e:
                self.execution_counter.labels(workflow.name, "failure").inc()
                span.set_attribute("workflow.status", "failure")
                span.record_exception(e)
                raise

            finally:
                self.active_executions.dec()
```

### Deployment Configuration

```yaml
# kubernetes/orchestrator-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  labels:
    app: orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
    spec:
      containers:
      - name: orchestrator
        image: orchestrator:latest
        ports:
        - containerPort: 8000
        env:
        - name: DISCOVERY_URL
          value: "http://registry:5000"
        - name: MAX_CONCURRENT
          value: "20"
        - name: DEFAULT_TIMEOUT
          value: "30"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
spec:
  selector:
    app: orchestrator
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Best Practices

1. **Workflow Design**
   - Keep workflows simple and focused
   - Use composition to build complex behaviors
   - Version workflows for backward compatibility
   - Document workflow requirements and outputs

2. **Error Handling**
   - Always implement retry logic for transient failures
   - Use circuit breakers for failing services
   - Implement compensations for critical workflows
   - Log all errors with context

3. **Performance**
   - Cache results when appropriate
   - Use connection pooling
   - Implement timeouts at every level
   - Monitor and optimize bottlenecks

4. **Testing**
   - Unit test individual workflow steps
   - Integration test complete workflows
   - Load test with realistic data volumes
   - Chaos test with failure injection

5. **Observability**
   - Instrument with metrics and tracing
   - Log at appropriate levels
   - Create dashboards for key metrics
   - Set up alerting for failures

## References

- [Workflow Patterns](http://www.workflowpatterns.com/)
- [Enterprise Integration Patterns](https://www.enterpriseintegrationpatterns.com/)
- [Saga Pattern](https://microservices.io/patterns/data/saga.html)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Google A2A Protocol](https://github.com/google-research/android_world/blob/main/android_world/a2a_protocol.md)