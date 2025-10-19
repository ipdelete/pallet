# Workflow Execution Walkthrough

A detailed step-by-step guide to understanding how workflows execute in the Pallet framework, including call stacks and execution flow for each step type.

## Table of Contents

1. [Overview](#overview)
2. [Execution Entry Point](#execution-entry-point)
3. [Sequential Step Execution](#sequential-step-execution)
4. [Parallel Step Execution](#parallel-step-execution)
5. [Conditional Step Execution](#conditional-step-execution)
6. [Switch Step Execution](#switch-step-execution)
7. [Complete Execution Examples](#complete-execution-examples)

---

## Overview

The workflow engine (`src/workflow_engine.py`) orchestrates AI agents using declarative YAML workflows. Each workflow consists of:

- **Metadata**: ID, name, version, description, tags
- **Steps**: Ordered list of operations with execution patterns
- **Context**: Manages state and template resolution across steps

**Key Components:**

```
WorkflowEngine
├── WorkflowContext (state management)
├── Agent Discovery (skill → agent URL mapping)
├── Template Resolution ({{ variable.path }} syntax)
└── Step Execution (sequential, parallel, conditional, switch)
```

---

## Execution Entry Point

### Main Entry: `WorkflowEngine.execute_workflow()`

**Call Stack:**
```
main.py
  └─→ orchestrator.py::run_orchestrator()
      └─→ WorkflowEngine.execute_workflow(workflow, initial_input)
```

**Step-by-Step:**

```python
# File: src/workflow_engine.py:455-529

async def execute_workflow(workflow, initial_input):
    """
    1. Log workflow metadata
    2. Initialize WorkflowContext with initial_input
    3. Iterate through workflow.steps
    4. Route each step to appropriate handler based on step_type
    5. Track timing for each step
    6. Return final context with all outputs
    """
```

**Detailed Execution Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INITIALIZATION (lines 468-477)                          │
├─────────────────────────────────────────────────────────────┤
│ - Log: workflow name, ID, version, step count              │
│ - Create WorkflowContext(initial_input)                     │
│   • workflow_input = initial_input                          │
│   • step_outputs = {}                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. STEP ITERATION (lines 481-522)                          │
├─────────────────────────────────────────────────────────────┤
│ For each step in workflow.steps:                            │
│   ├─→ Log: step ID, step type, skill                       │
│   ├─→ Start timer                                           │
│   ├─→ Route to handler:                                     │
│   │    • SEQUENTIAL → execute_step()                        │
│   │    • PARALLEL → execute_parallel_steps()                │
│   │    • CONDITIONAL → execute_conditional_step()           │
│   │    • SWITCH → execute_switch_step()                     │
│   ├─→ Store result in context                               │
│   └─→ Log: completion time                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. FINALIZATION (lines 524-529)                            │
├─────────────────────────────────────────────────────────────┤
│ - Log: total execution time                                 │
│ - Log: individual step timings                              │
│ - Return: final WorkflowContext                             │
└─────────────────────────────────────────────────────────────┘
```

**Context State Management:**

```python
# Initial state
context = WorkflowContext({
    "requirements": "Create a hello world function"
})

# After first step (plan)
context.step_outputs = {
    "plan": {
        "outputs": {
            "result": {
                "title": "Hello World Function",
                "steps": [...],
                ...
            }
        }
    }
}

# Template resolution for next step
# Input: "{{ steps.plan.outputs.result }}"
# Resolves to: {...plan object...}
```

---

## Sequential Step Execution

### Handler: `WorkflowEngine.execute_step()`

**Call Stack:**
```
execute_workflow()
  └─→ execute_step(step, context)
      ├─→ context.resolve_inputs(step.inputs)
      │   └─→ context.resolve_expression("{{ ... }}")
      ├─→ discover_agent_for_skill(step.skill)
      │   └─→ discover_agent(skill_id)  # From discovery.py
      └─→ call_agent_skill(agent_url, skill_id, params, timeout)
          └─→ HTTP POST to {agent_url}/execute
```

**Step-by-Step Execution:**

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Input Resolution (lines 268-271)                   │
├─────────────────────────────────────────────────────────────┤
│ Input: step.inputs = {"requirements": "{{ workflow.input.requirements }}"}
│                                                              │
│ context.resolve_inputs(step.inputs):                        │
│   For each key, value in inputs:                            │
│     ├─→ Is value a string?                                  │
│     │   └─→ YES: resolve_expression(value)                  │
│     │       ├─→ Match {{ ... }} pattern                     │
│     │       ├─→ Parse path: ["workflow", "input", "requirements"]
│     │       ├─→ Navigate context data                       │
│     │       └─→ Return: "Create a hello world function"     │
│     ├─→ Is value a dict?                                    │
│     │   └─→ YES: Recursively resolve nested dict            │
│     └─→ Is value a list?                                    │
│         └─→ YES: Resolve each list item                     │
│                                                              │
│ Output: resolved_inputs = {"requirements": "Create a hello world function"}
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Agent Discovery (lines 273-274)                    │
├─────────────────────────────────────────────────────────────┤
│ discover_agent_for_skill("create_plan"):                    │
│   ├─→ Check agent_cache for "create_plan"                  │
│   │   └─→ HIT: Return cached URL                            │
│   │   └─→ MISS: Continue to discovery                       │
│   ├─→ Call discover_agent("create_plan")                   │
│   │   ├─→ Query OCI registry for agent cards                │
│   │   ├─→ Pull agent cards via ORAS                         │
│   │   ├─→ Find agent with skill "create_plan"               │
│   │   └─→ Return: "http://localhost:8001"                   │
│   ├─→ Cache result: agent_cache["create_plan"] = url       │
│   └─→ Return: "http://localhost:8001"                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Agent Skill Call (lines 276-291)                   │
├─────────────────────────────────────────────────────────────┤
│ call_agent_skill(agent_url, skill_id, params, timeout):    │
│                                                              │
│   1. Create AsyncClient with timeout                        │
│                                                              │
│   2. POST to http://localhost:8001/execute                  │
│      Body: {                                                 │
│        "jsonrpc": "2.0",                                     │
│        "method": "create_plan",                              │
│        "params": {"requirements": "Create hello world..."},  │
│        "id": "1"                                             │
│      }                                                       │
│                                                              │
│   3. Agent processes request:                               │
│      ├─→ BaseAgent.execute() receives request               │
│      ├─→ Routes to PlanAgent.execute_skill()                │
│      ├─→ Validates params against input_schema              │
│      ├─→ Calls Claude CLI: claude -p --dangerously...       │
│      ├─→ Parses JSON response                               │
│      └─→ Returns: {                                          │
│            "title": "Hello World Function",                  │
│            "steps": [...],                                   │
│            "dependencies": [],                               │
│            "estimated_time": "5 minutes"                     │
│          }                                                   │
│                                                              │
│   4. Check for errors in response                           │
│                                                              │
│   5. Return result["result"]                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Store Output (lines 310-313 in execute_workflow)   │
├─────────────────────────────────────────────────────────────┤
│ If step.outputs specified:                                  │
│   context.set_step_output(step.id, {step.outputs: result}) │
│                                                              │
│ Otherwise:                                                   │
│   context.set_step_output(step.id, result)                 │
│                                                              │
│ Example:                                                     │
│   step.id = "plan"                                          │
│   step.outputs = "result"                                   │
│   result = {...plan data...}                                │
│                                                              │
│   context.step_outputs["plan"] = {                          │
│     "outputs": {                                             │
│       "result": {...plan data...}                           │
│     }                                                        │
│   }                                                          │
└─────────────────────────────────────────────────────────────┘
```

**Example: Code Generation Workflow (Sequential)**

```yaml
# workflows/code-generation.yaml
steps:
  - id: plan
    skill: create_plan
    inputs:
      requirements: "{{ workflow.input.requirements }}"
    outputs: result
```

**Execution Trace:**

```
1. execute_workflow() starts
   initial_input = {"requirements": "Create hello world"}

2. Process step: plan
   ├─→ resolve_inputs({"requirements": "{{ workflow.input.requirements }}"})
   │   └─→ Returns: {"requirements": "Create hello world"}
   │
   ├─→ discover_agent_for_skill("create_plan")
   │   └─→ Returns: "http://localhost:8001"
   │
   ├─→ call_agent_skill(
   │     agent_url="http://localhost:8001",
   │     skill_id="create_plan",
   │     params={"requirements": "Create hello world"}
   │   )
   │   ├─→ POST http://localhost:8001/execute
   │   ├─→ Agent executes skill
   │   └─→ Returns: {"title": "...", "steps": [...], ...}
   │
   └─→ context.set_step_output("plan", {
         "result": {"title": "...", "steps": [...], ...}
       })

3. Context state after step:
   context.step_outputs = {
     "plan": {
       "outputs": {
         "result": {...plan data...}
       }
     }
   }
```

---

## Parallel Step Execution

### Handler: `WorkflowEngine.execute_parallel_steps()`

**Call Stack:**
```
execute_workflow()
  └─→ execute_parallel_steps(steps, context)
      ├─→ [execute_step(step1, context), execute_step(step2, context), ...]
      │   └─→ asyncio.gather(*tasks)
      └─→ Store all results in context
```

**Step-by-Step Execution:**

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Parallel Task Creation (lines 332-334)             │
├─────────────────────────────────────────────────────────────┤
│ Input: steps = [step1, step2, step3]                        │
│                                                              │
│ Create coroutine tasks:                                     │
│   tasks = [                                                  │
│     execute_step(step1, context),  # analyze_quality        │
│     execute_step(step2, context),  # analyze_security       │
│     execute_step(step3, context)   # analyze_performance    │
│   ]                                                          │
│                                                              │
│ All tasks share the SAME context object                     │
│ (Template resolution happens at task start, not creation)   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Concurrent Execution (line 334)                    │
├─────────────────────────────────────────────────────────────┤
│ results = await asyncio.gather(*tasks, return_exceptions=True)
│                                                              │
│ Execution Timeline:                                         │
│ ═══════════════════════════════════════════════════════════│
│                                                              │
│ T=0s   ┌─→ Task 1: analyze_quality                          │
│        ├─→ Task 2: analyze_security                         │
│        └─→ Task 3: analyze_performance                      │
│                                                              │
│ T=1s   │   All tasks: resolve inputs                        │
│        │   All tasks: discover agents (cached after first)  │
│                                                              │
│ T=2s   │   All tasks: POST to agent /execute               │
│        │   (HTTP requests run concurrently)                 │
│                                                              │
│ T=10s  ├─✓ Task 1 completes                                 │
│ T=12s  ├─✓ Task 3 completes                                 │
│ T=15s  └─✓ Task 2 completes                                 │
│                                                              │
│ gather() waits for ALL tasks to complete                    │
│ Returns: [result1, result2, result3] in original order      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Result Processing (lines 337-344)                  │
├─────────────────────────────────────────────────────────────┤
│ For each (step, result) pair:                               │
│   ├─→ Check if result is Exception                          │
│   │   └─→ YES: Raise RuntimeError (fail entire workflow)    │
│   │                                                          │
│   ├─→ Store in context:                                     │
│   │   If step.outputs:                                       │
│   │     context.set_step_output(step.id, {step.outputs: result})
│   │   Else:                                                  │
│   │     context.set_step_output(step.id, result)           │
│   │                                                          │
│   └─→ Next step can access via template:                    │
│       "{{ steps.analyze_quality.outputs.quality_result }}"  │
└─────────────────────────────────────────────────────────────┘
```

**Example: Parallel Analysis Workflow**

```yaml
# workflows/parallel-analysis.yaml
steps:
  - id: parallel_analyze
    step_type: parallel
    branches:
      steps:
        - id: analyze_quality
          skill: review_code
          inputs:
            code: "{{ workflow.input.code }}"
          outputs: quality_result

        - id: analyze_security
          skill: security_scan
          inputs:
            code: "{{ workflow.input.code }}"
          outputs: security_result

        - id: analyze_performance
          skill: performance_check
          inputs:
            code: "{{ workflow.input.code }}"
          outputs: performance_result
```

**Execution Trace:**

```
1. execute_workflow() processes "parallel_analyze" step
   ├─→ Detects step_type: parallel
   ├─→ Extracts parallel steps from step.branches["steps"]
   └─→ Calls execute_parallel_steps([step1, step2, step3], context)

2. execute_parallel_steps() starts
   ├─→ Log: "Executing 3 steps in parallel"
   │
   ├─→ Create tasks:
   │   ├─→ Task A: execute_step(analyze_quality, context)
   │   ├─→ Task B: execute_step(analyze_security, context)
   │   └─→ Task C: execute_step(analyze_performance, context)
   │
   └─→ await asyncio.gather(A, B, C)

3. Concurrent execution:

   Task A (analyze_quality):
   ├─→ resolve_inputs({"code": "{{ workflow.input.code }}"})
   ├─→ discover_agent("review_code") → localhost:8003
   ├─→ POST localhost:8003/execute
   └─→ Returns: {"quality_score": 8.5, ...}

   Task B (analyze_security):  [running concurrently]
   ├─→ resolve_inputs({"code": "{{ workflow.input.code }}"})
   ├─→ discover_agent("security_scan") → localhost:8004
   ├─→ POST localhost:8004/execute
   └─→ Returns: {"vulnerabilities": [], ...}

   Task C (analyze_performance):  [running concurrently]
   ├─→ resolve_inputs({"code": "{{ workflow.input.code }}"})
   ├─→ discover_agent("performance_check") → localhost:8005
   ├─→ POST localhost:8005/execute
   └─→ Returns: {"complexity": "O(n)", ...}

4. All tasks complete, gather returns results

5. Store outputs:
   context.step_outputs["analyze_quality"] = {
     "outputs": {"quality_result": {...}}
   }
   context.step_outputs["analyze_security"] = {
     "outputs": {"security_result": {...}}
   }
   context.step_outputs["analyze_performance"] = {
     "outputs": {"performance_result": {...}}
   }

6. Next sequential step can access all results via templates
```

**Key Differences from Sequential:**

| Aspect | Sequential | Parallel |
|--------|-----------|----------|
| Execution | One step at a time | All steps concurrently |
| Timing | Sum of all step times | Max of any single step time |
| Failure | Stop at failed step | All tasks continue, check at end |
| Context Access | Each step sees previous outputs | All steps see same initial context |

---

## Conditional Step Execution

### Handler: `WorkflowEngine.execute_conditional_step()`

**Call Stack:**
```
execute_workflow()
  └─→ execute_conditional_step(step, context)
      ├─→ context.resolve_expression(step.condition)
      ├─→ Evaluate condition → true/false
      ├─→ Select branch: if_true or if_false
      └─→ For each branch_step:
          ├─→ execute_step(branch_step, context)
          └─→ Store result in context
```

**Step-by-Step Execution:**

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Condition Evaluation (lines 370-377)               │
├─────────────────────────────────────────────────────────────┤
│ Input:                                                       │
│   step.condition = "{{ steps.analyze.outputs.has_errors }}" │
│   step.branches = {                                          │
│     "if_true": [...steps to run if true...],                │
│     "if_false": [...steps to run if false...]               │
│   }                                                          │
│                                                              │
│ Validate:                                                    │
│   ├─→ Check step.condition exists                           │
│   │   └─→ MISSING: Raise ValueError                         │
│   └─→ Check step.branches exists                            │
│       └─→ MISSING: Raise ValueError                         │
│                                                              │
│ Resolve condition:                                           │
│   context.resolve_expression("{{ steps.analyze.outputs.has_errors }}")
│   ├─→ Match {{ ... }} pattern                               │
│   ├─→ Parse path: ["steps", "analyze", "outputs", "has_errors"]
│   ├─→ Navigate context:                                     │
│   │   context.step_outputs["analyze"]["outputs"]["has_errors"]
│   └─→ Returns: True or False                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Branch Selection (lines 379-391)                   │
├─────────────────────────────────────────────────────────────┤
│ If condition_result == True:                                │
│   ├─→ branch_steps = step.branches["if_true"]              │
│   └─→ Log: "Condition true, executing if_true branch"       │
│                                                              │
│ Else (condition_result == False):                           │
│   ├─→ branch_steps = step.branches["if_false"]             │
│   └─→ Log: "Condition false, executing if_false branch"     │
│                                                              │
│ Extract steps:                                               │
│   branch_steps = [                                           │
│     {                                                        │
│       "id": "fix_errors",                                    │
│       "skill": "fix_code",                                   │
│       "inputs": {...},                                       │
│       ...                                                    │
│     },                                                       │
│     ...                                                      │
│   ]                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Branch Execution (lines 394-398)                   │
├─────────────────────────────────────────────────────────────┤
│ For each branch_step_data in branch_steps:                  │
│   ├─→ Construct WorkflowStep from dict                      │
│   │   branch_step = WorkflowStep(**branch_step_data)        │
│   │                                                          │
│   ├─→ Execute step                                           │
│   │   result = await execute_step(branch_step, context)     │
│   │   (Same execution flow as sequential step)              │
│   │                                                          │
│   └─→ Store in context                                       │
│       context.set_step_output(branch_step.id, result)       │
│                                                              │
│ Return updated context                                       │
└─────────────────────────────────────────────────────────────┘
```

**Example: Conditional Workflow**

```yaml
steps:
  - id: analyze
    skill: analyze_code
    inputs:
      code: "{{ workflow.input.code }}"
    outputs: analysis

  - id: conditional_fix
    step_type: conditional
    condition: "{{ steps.analyze.outputs.analysis.has_errors }}"
    branches:
      if_true:
        - id: fix_errors
          skill: fix_code
          inputs:
            code: "{{ workflow.input.code }}"
            errors: "{{ steps.analyze.outputs.analysis.errors }}"
          outputs: fixed_code

        - id: verify_fix
          skill: verify_code
          inputs:
            code: "{{ steps.fix_errors.outputs.fixed_code }}"
          outputs: verification

      if_false:
        - id: optimize
          skill: optimize_code
          inputs:
            code: "{{ workflow.input.code }}"
          outputs: optimized_code
```

**Execution Trace (Condition = True):**

```
1. execute_workflow() processes "conditional_fix" step
   ├─→ Detects step_type: conditional
   └─→ Calls execute_conditional_step(step, context)

2. execute_conditional_step() starts

   ├─→ Validate:
   │   ├─→ step.condition exists? YES
   │   └─→ step.branches exists? YES
   │
   ├─→ Evaluate condition:
   │   resolve_expression("{{ steps.analyze.outputs.analysis.has_errors }}")
   │   ├─→ Path: ["steps", "analyze", "outputs", "analysis", "has_errors"]
   │   ├─→ Navigate: context.step_outputs["analyze"]["outputs"]["analysis"]["has_errors"]
   │   └─→ Returns: True
   │
   ├─→ Select branch:
   │   condition_result = True
   │   branch_steps = step.branches["if_true"]
   │   Log: "Condition true, executing if_true branch (2 steps)"
   │
   └─→ Execute branch steps sequentially:

3. Execute fix_errors step:
   ├─→ WorkflowStep(**branch_step_data[0])
   ├─→ resolve_inputs({
   │     "code": "{{ workflow.input.code }}",
   │     "errors": "{{ steps.analyze.outputs.analysis.errors }}"
   │   })
   │   Returns: {
   │     "code": "def foo():\n  x = 1/0",
   │     "errors": ["ZeroDivisionError at line 2"]
   │   }
   ├─→ discover_agent("fix_code") → localhost:8006
   ├─→ call_agent_skill(...)
   └─→ context.set_step_output("fix_errors", {
         "fixed_code": "def foo():\n  x = 1/1"
       })

4. Execute verify_fix step:
   ├─→ WorkflowStep(**branch_step_data[1])
   ├─→ resolve_inputs({
   │     "code": "{{ steps.fix_errors.outputs.fixed_code }}"
   │   })
   │   Returns: {"code": "def foo():\n  x = 1/1"}
   ├─→ discover_agent("verify_code") → localhost:8007
   ├─→ call_agent_skill(...)
   └─→ context.set_step_output("verify_fix", {
         "verification": {"passed": true, "issues": []}
       })

5. Return updated context

6. Context state:
   context.step_outputs = {
     "analyze": {...},
     "fix_errors": {"outputs": {"fixed_code": "..."}},
     "verify_fix": {"outputs": {"verification": {...}}}
   }

   Note: "optimize" step was NOT executed (if_false branch)
```

**Execution Trace (Condition = False):**

```
1. Same setup as above

2. execute_conditional_step():
   ├─→ Evaluate condition:
   │   resolve_expression("{{ steps.analyze.outputs.analysis.has_errors }}")
   │   └─→ Returns: False
   │
   ├─→ Select branch:
   │   condition_result = False
   │   branch_steps = step.branches["if_false"]
   │   Log: "Condition false, executing if_false branch (1 steps)"
   │
   └─→ Execute branch steps:

3. Execute optimize step:
   └─→ context.set_step_output("optimize", {
         "optimized_code": "..."
       })

4. Context state:
   context.step_outputs = {
     "analyze": {...},
     "optimize": {"outputs": {"optimized_code": "..."}}
   }

   Note: "fix_errors" and "verify_fix" were NOT executed
```

---

## Switch Step Execution

### Handler: `WorkflowEngine.execute_switch_step()`

**Call Stack:**
```
execute_workflow()
  └─→ execute_switch_step(step, context)
      ├─→ context.resolve_expression(step.condition)
      ├─→ Convert result to string for case matching
      ├─→ Find matching case in step.branches
      ├─→ Fallback to "default" if no match
      └─→ For each branch_step:
          ├─→ execute_step(branch_step, context)
          └─→ Store result in context
```

**Step-by-Step Execution:**

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Switch Expression Evaluation (lines 422-430)       │
├─────────────────────────────────────────────────────────────┤
│ Input:                                                       │
│   step.condition = "{{ steps.analyze.outputs.request_type }}"│
│   step.branches = {                                          │
│     "code_generation": [...],                                │
│     "data_analysis": [...],                                  │
│     "text_processing": [...],                                │
│     "default": [...]                                         │
│   }                                                          │
│                                                              │
│ Validate:                                                    │
│   ├─→ Check step.condition exists                           │
│   │   └─→ MISSING: Raise ValueError                         │
│   └─→ Check step.branches exists                            │
│       └─→ MISSING: Raise ValueError                         │
│                                                              │
│ Resolve switch expression:                                  │
│   context.resolve_expression("{{ steps.analyze.outputs.request_type }}")
│   ├─→ Match {{ ... }} pattern                               │
│   ├─→ Parse path: ["steps", "analyze", "outputs", "request_type"]
│   ├─→ Navigate context                                      │
│   └─→ Returns: "code_generation" (or other value)           │
│                                                              │
│ Log: "Switch evaluated to: code_generation"                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Case Matching (lines 432-440)                      │
├─────────────────────────────────────────────────────────────┤
│ Convert switch value to string:                             │
│   matched_case = str(switch_value)                          │
│   # "code_generation" → "code_generation"                   │
│   # 123 → "123"                                              │
│   # True → "True"                                            │
│                                                              │
│ Find matching branch:                                        │
│   branch_steps = step.branches.get(matched_case)            │
│                                                              │
│   ├─→ FOUND: Use matched case steps                         │
│   │   Log: "Executing case 'code_generation' (3 steps)"     │
│   │                                                          │
│   └─→ NOT FOUND: Try default                                │
│       branch_steps = step.branches.get("default", [])       │
│       ├─→ Default exists: Use default steps                 │
│       │   Log: "No match, executing default (1 steps)"      │
│       └─→ No default: Empty list                            │
│           Log: "No matching case, skipping"                 │
│           Return context unchanged                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Case Execution (lines 448-452)                     │
├─────────────────────────────────────────────────────────────┤
│ For each branch_step_data in branch_steps:                  │
│   ├─→ Construct WorkflowStep from dict                      │
│   │   branch_step = WorkflowStep(**branch_step_data)        │
│   │                                                          │
│   ├─→ Execute step                                           │
│   │   result = await execute_step(branch_step, context)     │
│   │   (Same execution flow as sequential step)              │
│   │                                                          │
│   └─→ Store in context                                       │
│       context.set_step_output(branch_step.id, result)       │
│                                                              │
│ Return updated context                                       │
└─────────────────────────────────────────────────────────────┘
```

**Example: Smart Router Workflow**

```yaml
# workflows/smart-router.yaml
steps:
  - id: analyze
    skill: analyze_request
    inputs:
      request: "{{ workflow.input.requirements }}"
    outputs: request_type

  - id: route
    step_type: switch
    condition: "{{ steps.analyze.outputs.request_type }}"
    branches:
      code_generation:
        - id: generate_code_workflow
          skill: execute_workflow
          inputs:
            workflow_id: code-generation-v1
            input: "{{ workflow.input }}"

      data_analysis:
        - id: analyze_data_workflow
          skill: execute_workflow
          inputs:
            workflow_id: data-analysis-v1
            input: "{{ workflow.input }}"

      text_processing:
        - id: process_text_workflow
          skill: execute_workflow
          inputs:
            workflow_id: text-processing-v1
            input: "{{ workflow.input }}"

      default:
        - id: fallback
          skill: create_plan
          inputs:
            requirements: "{{ workflow.input.requirements }}"
```

**Execution Trace (Case: code_generation):**

```
1. execute_workflow() processes "route" step
   ├─→ Detects step_type: switch
   └─→ Calls execute_switch_step(step, context)

2. execute_switch_step() starts

   ├─→ Validate:
   │   ├─→ step.condition exists? YES
   │   └─→ step.branches exists? YES
   │
   ├─→ Evaluate switch expression:
   │   resolve_expression("{{ steps.analyze.outputs.request_type }}")
   │   ├─→ Path: ["steps", "analyze", "outputs", "request_type"]
   │   ├─→ Navigate: context.step_outputs["analyze"]["outputs"]["request_type"]
   │   └─→ Returns: "code_generation"
   │
   │   Log: "Switch evaluated to: code_generation"
   │
   ├─→ Match case:
   │   matched_case = "code_generation"
   │   branch_steps = step.branches["code_generation"]
   │
   │   Log: "Executing case 'code_generation' (1 steps)"
   │
   └─→ Execute branch steps:

3. Execute generate_code_workflow step:
   ├─→ WorkflowStep(**branch_step_data[0])
   ├─→ resolve_inputs({
   │     "workflow_id": "code-generation-v1",
   │     "input": "{{ workflow.input }}"
   │   })
   │   Returns: {
   │     "workflow_id": "code-generation-v1",
   │     "input": {"requirements": "Create hello world"}
   │   }
   ├─→ discover_agent("execute_workflow") → orchestrator
   ├─→ call_agent_skill(...)
   │   # This would trigger nested workflow execution
   └─→ context.set_step_output("generate_code_workflow", {...})

4. Return updated context

5. Context state:
   context.step_outputs = {
     "analyze": {
       "outputs": {"request_type": "code_generation"}
     },
     "generate_code_workflow": {
       "outputs": {...nested workflow results...}
     }
   }

   Note: Only "code_generation" case executed
         "data_analysis", "text_processing", "default" NOT executed
```

**Execution Trace (Case: unknown → default):**

```
1-2. Same setup as above

3. execute_switch_step():
   ├─→ Evaluate switch expression:
   │   Returns: "unknown_type"
   │   Log: "Switch evaluated to: unknown_type"
   │
   ├─→ Match case:
   │   matched_case = "unknown_type"
   │   step.branches["unknown_type"] → None
   │
   │   Fallback to default:
   │   branch_steps = step.branches["default"]
   │
   │   Log: "Executing case 'default' (1 steps)"
   │
   └─→ Execute default branch:

4. Execute fallback step:
   ├─→ WorkflowStep(**branch_step_data[0])
   ├─→ resolve_inputs({
   │     "requirements": "{{ workflow.input.requirements }}"
   │   })
   ├─→ discover_agent("create_plan")
   ├─→ call_agent_skill(...)
   └─→ context.set_step_output("fallback", {...})

5. Context state:
   context.step_outputs = {
     "analyze": {"outputs": {"request_type": "unknown_type"}},
     "fallback": {"outputs": {...plan...}}
   }
```

**Switch vs Conditional Comparison:**

| Feature | Conditional | Switch |
|---------|------------|--------|
| Branching | 2 branches (if_true/if_false) | N branches + default |
| Condition | Boolean expression | Any value (converted to string) |
| Matching | true or false | Exact string match |
| Default | if_false branch | "default" key (optional) |
| Use Case | Binary decisions | Multi-way routing |

---

## Complete Execution Examples

### Example 1: Code Generation Workflow (All Sequential)

**Workflow Definition:**

```yaml
metadata:
  id: code-generation-v1
  name: Code Generation Pipeline
  version: 1.0.0

steps:
  - id: plan
    skill: create_plan
    inputs:
      requirements: "{{ workflow.input.requirements }}"
    outputs: result
    timeout: 300
    step_type: sequential

  - id: build
    skill: generate_code
    inputs:
      plan: "{{ steps.plan.outputs.result }}"
    outputs: result
    timeout: 600
    step_type: sequential

  - id: test
    skill: review_code
    inputs:
      code: "{{ steps.build.outputs.result.code }}"
      language: "{{ steps.build.outputs.result.language }}"
    outputs: result
    timeout: 300
    step_type: sequential
```

**Complete Call Stack:**

```
main.py::main()
│
├─→ orchestrator.py::run_orchestrator(requirements, workflow_name)
│   │
│   ├─→ discovery.py::discover_workflow("code-generation-v1")
│   │   ├─→ Query OCI registry
│   │   ├─→ Pull workflow YAML via ORAS
│   │   └─→ Returns: workflow YAML content
│   │
│   ├─→ workflow_engine.py::load_workflow_from_yaml(yaml_content)
│   │   ├─→ yaml.safe_load(yaml_content)
│   │   ├─→ WorkflowDefinition(**data)
│   │   └─→ Returns: WorkflowDefinition object
│   │
│   ├─→ WorkflowEngine().execute_workflow(workflow, initial_input)
│   │   │
│   │   ├─→ WorkflowContext({"requirements": "Create hello world"})
│   │   │
│   │   ├─────────────────────────────────────────────────────
│   │   │ STEP 1: plan
│   │   ├─────────────────────────────────────────────────────
│   │   │
│   │   ├─→ execute_step(plan_step, context)
│   │   │   │
│   │   │   ├─→ context.resolve_inputs(step.inputs)
│   │   │   │   └─→ {"requirements": "Create hello world"}
│   │   │   │
│   │   │   ├─→ discover_agent_for_skill("create_plan")
│   │   │   │   ├─→ Check cache: MISS
│   │   │   │   ├─→ discovery.py::discover_agent("create_plan")
│   │   │   │   │   ├─→ Query registry for agent cards
│   │   │   │   │   ├─→ Pull plan_agent_card.json
│   │   │   │   │   ├─→ Match skill "create_plan"
│   │   │   │   │   └─→ Returns: "http://localhost:8001"
│   │   │   │   ├─→ Cache: agent_cache["create_plan"] = url
│   │   │   │   └─→ Returns: "http://localhost:8001"
│   │   │   │
│   │   │   ├─→ call_agent_skill(
│   │   │   │     agent_url="http://localhost:8001",
│   │   │   │     skill_id="create_plan",
│   │   │   │     params={"requirements": "Create hello world"},
│   │   │   │     timeout=300
│   │   │   │   )
│   │   │   │   │
│   │   │   │   ├─→ httpx.AsyncClient.post(
│   │   │   │   │     "http://localhost:8001/execute",
│   │   │   │   │     json={
│   │   │   │   │       "jsonrpc": "2.0",
│   │   │   │   │       "method": "create_plan",
│   │   │   │   │       "params": {"requirements": "..."},
│   │   │   │   │       "id": "1"
│   │   │   │   │     }
│   │   │   │   │   )
│   │   │   │   │   │
│   │   │   │   │   └─→ Plan Agent (localhost:8001)
│   │   │   │   │       │
│   │   │   │   │       ├─→ BaseAgent.execute() receives request
│   │   │   │   │       │
│   │   │   │   │       ├─→ PlanAgent.execute_skill("create_plan", params)
│   │   │   │   │       │   │
│   │   │   │   │       │   ├─→ Validate params against input_schema
│   │   │   │   │       │   │
│   │   │   │   │       │   ├─→ BaseAgent.call_claude(system_prompt, user_msg)
│   │   │   │   │       │   │   ├─→ subprocess.run([
│   │   │   │   │       │   │   │     "claude", "-p",
│   │   │   │   │       │   │   │     "--dangerously-skip-permissions",
│   │   │   │   │       │   │   │     ...
│   │   │   │   │       │   │   │   ])
│   │   │   │   │       │   │   ├─→ Claude API processes request
│   │   │   │   │       │   │   └─→ Returns: JSON response
│   │   │   │   │       │   │
│   │   │   │   │       │   ├─→ parse_json_response(response)
│   │   │   │   │       │   │   ├─→ Extract from ```json``` blocks
│   │   │   │   │       │   │   ├─→ Fallback to raw JSON
│   │   │   │   │       │   │   └─→ json.loads()
│   │   │   │   │       │   │
│   │   │   │   │       │   └─→ Returns: {
│   │   │   │   │       │         "title": "Hello World Function",
│   │   │   │   │       │         "steps": [
│   │   │   │   │       │           "Define function signature",
│   │   │   │   │       │           "Implement print statement",
│   │   │   │   │       │           "Add docstring"
│   │   │   │   │       │         ],
│   │   │   │   │       │         "dependencies": [],
│   │   │   │   │       │         "estimated_time": "5 minutes"
│   │   │   │   │       │       }
│   │   │   │   │       │
│   │   │   │   │       └─→ Returns JSON-RPC response:
│   │   │   │   │           {
│   │   │   │   │             "jsonrpc": "2.0",
│   │   │   │   │             "result": {...plan...},
│   │   │   │   │             "id": "1"
│   │   │   │   │           }
│   │   │   │   │
│   │   │   │   ├─→ Parse HTTP response
│   │   │   │   ├─→ Check for "error" key
│   │   │   │   └─→ Returns: result["result"]
│   │   │   │
│   │   │   └─→ Returns: {...plan data...}
│   │   │
│   │   ├─→ context.set_step_output("plan", {
│   │   │     "result": {...plan data...}
│   │   │   })
│   │   │
│   │   │   Context now contains:
│   │   │   {
│   │   │     workflow_input: {"requirements": "Create hello world"},
│   │   │     step_outputs: {
│   │   │       "plan": {
│   │   │         "outputs": {
│   │   │           "result": {...plan data...}
│   │   │         }
│   │   │       }
│   │   │     }
│   │   │   }
│   │   │
│   │   ├─────────────────────────────────────────────────────
│   │   │ STEP 2: build
│   │   ├─────────────────────────────────────────────────────
│   │   │
│   │   ├─→ execute_step(build_step, context)
│   │   │   │
│   │   │   ├─→ context.resolve_inputs(step.inputs)
│   │   │   │   ├─→ Input: {"plan": "{{ steps.plan.outputs.result }}"}
│   │   │   │   ├─→ resolve_expression("{{ steps.plan.outputs.result }}")
│   │   │   │   │   ├─→ Path: ["steps", "plan", "outputs", "result"]
│   │   │   │   │   ├─→ Navigate context.step_outputs
│   │   │   │   │   └─→ Returns: {...plan data...}
│   │   │   │   └─→ {"plan": {...plan data...}}
│   │   │   │
│   │   │   ├─→ discover_agent_for_skill("generate_code")
│   │   │   │   ├─→ Check cache: MISS
│   │   │   │   ├─→ discovery.py::discover_agent("generate_code")
│   │   │   │   │   └─→ Returns: "http://localhost:8002"
│   │   │   │   ├─→ Cache result
│   │   │   │   └─→ Returns: "http://localhost:8002"
│   │   │   │
│   │   │   ├─→ call_agent_skill(
│   │   │   │     agent_url="http://localhost:8002",
│   │   │   │     skill_id="generate_code",
│   │   │   │     params={"plan": {...plan data...}},
│   │   │   │     timeout=600
│   │   │   │   )
│   │   │   │   └─→ [Similar HTTP + agent execution as Step 1]
│   │   │   │   └─→ Returns: {
│   │   │   │         "code": "def hello_world():\n    print('Hello World')",
│   │   │   │         "language": "python",
│   │   │   │         "explanation": "...",
│   │   │   │         "functions": ["hello_world"]
│   │   │   │       }
│   │   │   │
│   │   │   └─→ Returns: {...code data...}
│   │   │
│   │   ├─→ context.set_step_output("build", {
│   │   │     "result": {...code data...}
│   │   │   })
│   │   │
│   │   │   Context now contains:
│   │   │   {
│   │   │     workflow_input: {"requirements": "Create hello world"},
│   │   │     step_outputs: {
│   │   │       "plan": {"outputs": {"result": {...}}},
│   │   │       "build": {"outputs": {"result": {...code data...}}}
│   │   │     }
│   │   │   }
│   │   │
│   │   ├─────────────────────────────────────────────────────
│   │   │ STEP 3: test
│   │   ├─────────────────────────────────────────────────────
│   │   │
│   │   ├─→ execute_step(test_step, context)
│   │   │   │
│   │   │   ├─→ context.resolve_inputs(step.inputs)
│   │   │   │   ├─→ Input: {
│   │   │   │   │     "code": "{{ steps.build.outputs.result.code }}",
│   │   │   │   │     "language": "{{ steps.build.outputs.result.language }}"
│   │   │   │   │   }
│   │   │   │   ├─→ Resolve nested paths:
│   │   │   │   │   ├─→ steps.build.outputs.result.code → "def hello_world()..."
│   │   │   │   │   └─→ steps.build.outputs.result.language → "python"
│   │   │   │   └─→ {
│   │   │   │         "code": "def hello_world()...",
│   │   │   │         "language": "python"
│   │   │   │       }
│   │   │   │
│   │   │   ├─→ discover_agent_for_skill("review_code")
│   │   │   │   ├─→ Check cache: MISS
│   │   │   │   ├─→ discover_agent("review_code")
│   │   │   │   │   └─→ Returns: "http://localhost:8003"
│   │   │   │   └─→ Returns: "http://localhost:8003"
│   │   │   │
│   │   │   ├─→ call_agent_skill(
│   │   │   │     agent_url="http://localhost:8003",
│   │   │   │     skill_id="review_code",
│   │   │   │     params={"code": "...", "language": "python"},
│   │   │   │     timeout=300
│   │   │   │   )
│   │   │   │   └─→ [Similar HTTP + agent execution]
│   │   │   │   └─→ Returns: {
│   │   │   │         "quality_score": 8.5,
│   │   │   │         "issues": [],
│   │   │   │         "suggestions": ["Add type hints"],
│   │   │   │         "approved": true,
│   │   │   │         "summary": "Code is well-structured"
│   │   │   │       }
│   │   │   │
│   │   │   └─→ Returns: {...review data...}
│   │   │
│   │   ├─→ context.set_step_output("test", {
│   │   │     "result": {...review data...}
│   │   │   })
│   │   │
│   │   ├─→ Log: "Workflow completed: Code Generation Pipeline"
│   │   ├─→ Log: "Total execution time: 45.23s"
│   │   ├─→ Log: "  - plan: 10.5s"
│   │   ├─→ Log: "  - build: 30.1s"
│   │   ├─→ Log: "  - test: 4.6s"
│   │   │
│   │   └─→ Returns: context (with all step outputs)
│   │
│   ├─→ Save outputs to files:
│   │   ├─→ app/plan.json
│   │   ├─→ app/main.py (generated code)
│   │   ├─→ app/review.json
│   │   └─→ app/metadata.json
│   │
│   └─→ Returns: execution results

```

**Final Context State:**

```python
context = WorkflowContext({
    workflow_input: {
        "requirements": "Create hello world function"
    },
    step_outputs: {
        "plan": {
            "outputs": {
                "result": {
                    "title": "Hello World Function",
                    "steps": [...],
                    "dependencies": [],
                    "estimated_time": "5 minutes"
                }
            }
        },
        "build": {
            "outputs": {
                "result": {
                    "code": "def hello_world():\n    print('Hello World')",
                    "language": "python",
                    "explanation": "Simple function that prints hello world",
                    "functions": ["hello_world"]
                }
            }
        },
        "test": {
            "outputs": {
                "result": {
                    "quality_score": 8.5,
                    "issues": [],
                    "suggestions": ["Add type hints", "Add docstring"],
                    "approved": true,
                    "summary": "Code is well-structured and functional"
                }
            }
        }
    }
})
```

---

### Example 2: Mixed Workflow (Sequential → Parallel → Sequential)

**Workflow Definition:**

```yaml
metadata:
  id: comprehensive-analysis-v1
  name: Comprehensive Code Analysis
  version: 1.0.0

steps:
  # Step 1: Sequential - Generate code
  - id: generate
    skill: generate_code
    inputs:
      plan: "{{ workflow.input.plan }}"
    outputs: code_result
    step_type: sequential

  # Step 2: Parallel - Run multiple analyses
  - id: analyze_all
    step_type: parallel
    branches:
      steps:
        - id: quality_check
          skill: review_code
          inputs:
            code: "{{ steps.generate.outputs.code_result.code }}"
          outputs: quality

        - id: security_scan
          skill: security_check
          inputs:
            code: "{{ steps.generate.outputs.code_result.code }}"
          outputs: security

        - id: performance_test
          skill: performance_check
          inputs:
            code: "{{ steps.generate.outputs.code_result.code }}"
          outputs: performance

  # Step 3: Sequential - Aggregate results
  - id: aggregate
    skill: aggregate_analysis
    inputs:
      quality: "{{ steps.quality_check.outputs.quality }}"
      security: "{{ steps.security_scan.outputs.security }}"
      performance: "{{ steps.performance_test.outputs.performance }}"
    outputs: final_report
    step_type: sequential
```

**Execution Timeline:**

```
Time    Step                Action
════════════════════════════════════════════════════════════════
T=0s    generate            Start sequential execution
T=1s    generate            Resolve inputs
T=2s    generate            Discover agent (generate_code)
T=3s    generate            POST to agent
T=33s   generate            Agent returns result
T=33s   generate            Store in context
T=33s   ──────────────────  STEP 1 COMPLETE

T=33s   analyze_all         Start parallel execution
T=33s   analyze_all         Create 3 tasks:
                            ├─→ Task A: quality_check
                            ├─→ Task B: security_scan
                            └─→ Task C: performance_test

T=34s   [Task A]            Resolve inputs (parallel)
        [Task B]            Resolve inputs (parallel)
        [Task C]            Resolve inputs (parallel)

T=35s   [Task A]            Discover agent: review_code
        [Task B]            Discover agent: security_check (cached)
        [Task C]            Discover agent: performance_check (cached)

T=36s   [Task A]            POST to localhost:8003
        [Task B]            POST to localhost:8004
        [Task C]            POST to localhost:8005

        │                   All HTTP requests in flight...
        │
T=46s   [Task A] ✓          Returns quality result
T=48s   [Task C] ✓          Returns performance result
T=50s   [Task B] ✓          Returns security result

T=50s   analyze_all         All tasks complete
T=50s   analyze_all         Store all outputs in context
T=50s   ──────────────────  STEP 2 COMPLETE

T=50s   aggregate           Start sequential execution
T=51s   aggregate           Resolve inputs (3 nested paths)
T=52s   aggregate           Discover agent (aggregate_analysis)
T=53s   aggregate           POST to agent
T=58s   aggregate           Agent returns result
T=58s   aggregate           Store in context
T=58s   ──────────────────  STEP 3 COMPLETE

T=58s   WORKFLOW            Complete
        COMPLETE            Total time: 58s
                            (vs 88s if all sequential)
```

**Key Observations:**

1. **Sequential steps block**: Step 2 can't start until Step 1 finishes
2. **Parallel optimization**: 3 analyses run concurrently (14s vs 36s if sequential)
3. **Context sharing**: All parallel tasks read from same context
4. **Output independence**: Each parallel task stores its own output
5. **Template resolution**: Step 3 accesses outputs from parallel steps

---

## Summary

### Execution Pattern Decision Tree

```
Step.step_type?
│
├─→ SEQUENTIAL
│   └─→ execute_step(step, context)
│       └─→ Single agent call, store result
│
├─→ PARALLEL
│   └─→ execute_parallel_steps(step.branches["steps"], context)
│       └─→ asyncio.gather(execute_step() × N)
│       └─→ Store all results
│
├─→ CONDITIONAL
│   └─→ execute_conditional_step(step, context)
│       ├─→ Evaluate condition → true/false
│       ├─→ Select if_true or if_false branch
│       └─→ Execute branch steps sequentially
│
└─→ SWITCH
    └─→ execute_switch_step(step, context)
        ├─→ Evaluate condition → string value
        ├─→ Match case or default
        └─→ Execute matched branch steps sequentially
```

### Template Resolution Flow

```
"{{ steps.plan.outputs.result }}"
    ↓
resolve_expression()
    ↓
Match {{ ... }} pattern
    ↓
Parse path: ["steps", "plan", "outputs", "result"]
    ↓
Navigate context:
  context.step_outputs["plan"]["outputs"]["result"]
    ↓
Return resolved value
```

### Agent Discovery & Caching

```
discover_agent_for_skill("create_plan")
    ↓
Check agent_cache
    ├─→ HIT: Return cached URL (fast)
    └─→ MISS:
        ├─→ discover_agent("create_plan")  # Query registry
        ├─→ Cache result
        └─→ Return URL
```

### Error Handling

- **Sequential**: Stop immediately on error, propagate exception
- **Parallel**: Wait for all tasks, then check for exceptions
- **Conditional/Switch**: Stop on branch execution error
- **Template Resolution**: Return `None` if path doesn't exist

---

## Related Files

- `src/workflow_engine.py` - Complete implementation
- `src/orchestrator.py` - Workflow execution orchestrator
- `src/discovery.py` - Agent and workflow discovery
- `workflows/*.yaml` - Example workflow definitions
- `docs/WORKFLOW_ENGINE.md` - High-level workflow documentation
- `tests/integration/test_workflow_execution.py` - Workflow tests
