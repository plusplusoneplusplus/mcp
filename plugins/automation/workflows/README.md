# Workflow System

Deterministic orchestration of AI agents and operations through declarative YAML workflows.

## Overview

The workflow system enables deterministic orchestration of AI agents and other operations in a declarative, reproducible manner. Workflows are defined in YAML format and executed by a workflow engine that manages state, dependencies, and error handling.

### Features

- **Chain AI agents** in a deterministic, reproducible manner
- **Define workflows declaratively** using YAML
- **Manage complex automation** with dependency resolution
- **Track execution state** with full observability
- **Handle errors gracefully** with retry policies
- **Resume interrupted workflows** from last successful step
- **Template expressions** for dynamic value resolution

## Architecture

### Core Components

```
plugins/automation/
├── context.py             # WorkflowContext - shared execution context
├── workflows/
│   ├── __init__.py
│   ├── README.md          # This documentation
│   ├── definition.py      # WorkflowDefinition - parse and validate
│   ├── engine.py          # WorkflowEngine - main execution engine
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── base.py       # BaseStep - abstract base class
│   │   ├── agent_step.py # AgentStep - execute agent operations
│   │   ├── conditional_step.py  # ConditionalStep - branching logic (future)
│   │   ├── parallel_step.py  # ParallelStep - parallel execution (future)
│   │   ├── loop_step.py  # LoopStep - iteration (future)
│   │   └── transform_step.py # TransformStep - data transformation (future)
│   └── examples/
│       ├── feature_exploration.yaml
│       └── codebase_onboarding.yaml
└── tests/
    ├── test_workflow_context.py     # Context tests
    ├── test_workflow_definition.py  # Definition tests
    └── test_workflow_engine.py      # Engine tests
```

### Workflow Execution Flow

```
1. Load & Validate
   ├─ Parse YAML
   ├─ Validate structure
   └─ Check dependencies

2. Create Context
   ├─ Initialize inputs
   ├─ Generate execution ID
   └─ Prepare state tracking

3. Execute Steps
   ├─ Resolve dependencies
   ├─ Execute in order
   ├─ Handle retries
   └─ Store results

4. Collect Results
   ├─ Gather step outputs
   ├─ Determine status
   └─ Return result
```

## Quick Start

### Define a Workflow

Create a YAML file describing your workflow:

```yaml
workflow:
  name: "feature-exploration"
  version: "1.0"
  description: "Explore a specific feature implementation"

  inputs:
    feature_name:
      type: string
      required: true
    codebase_path:
      type: string
      required: true

  steps:
    - id: find_implementation
      type: agent
      agent: explore
      operation: find_implementation
      inputs:
        feature_or_function: "{{ inputs.feature_name }}"
        codebase_path: "{{ inputs.codebase_path }}"

    - id: find_usage
      type: agent
      agent: explore
      operation: find_usage
      inputs:
        symbol: "{{ inputs.feature_name }}"
        codebase_path: "{{ inputs.codebase_path }}"
      depends_on: [find_implementation]
```

### Execute the Workflow

```python
from plugins.automation.workflows import WorkflowDefinition, WorkflowEngine

# Load workflow
workflow = WorkflowDefinition.from_file("feature_exploration.yaml")

# Execute with inputs
engine = WorkflowEngine()
result = await engine.execute(
    workflow,
    inputs={
        "feature_name": "authentication",
        "codebase_path": "/path/to/code"
    }
)

# Check results
print(f"Status: {result.status}")
print(f"Outputs: {result.outputs}")
```

## Workflow Definition Format

### Basic Structure

```yaml
workflow:
  name: string          # Workflow identifier
  version: string       # Semantic version
  description: string   # Human-readable description

  inputs:               # Input parameters
    param_name:
      type: string      # string, number, boolean, array, object
      required: bool    # Is this input required?
      default: any      # Default value if not provided
      description: string

  outputs:              # Output definitions
    output_name:
      type: string
      description: string

  steps:                # Workflow steps
    - id: step_id       # Unique step identifier
      type: step_type   # agent, conditional, parallel, loop, transform
      depends_on: []    # List of step IDs this depends on
      # ... step-specific fields

  error_handling:       # Global error handling
    on_failure: stop    # stop, continue
    retry_policy:
      max_attempts: 3
      backoff: exponential
```

### Template Expressions

Access dynamic values using `{{ }}` syntax:

- `{{ inputs.name }}` - Access workflow inputs
- `{{ steps.step_id.result }}` - Access step results
- `{{ steps.step_id.status }}` - Access step status
- `{{ context.get("key", "default") }}` - Access context with default
- `{{ env.VARIABLE }}` - Access environment variables (future)

**Examples:**

```yaml
inputs:
  question: "{{ inputs.user_question }}"                    # Access workflow input
  previous_result: "{{ steps.analyze_structure.result }}"  # Access step result
  codebase: "{{ context.get('config.path', '/default') }}" # Context with default
```

## Step Types

### 1. Agent Step (✅ Implemented)

Execute an AI agent operation.

```yaml
- id: explore_code
  type: agent
  agent: explore                    # Agent type (explore, review, etc.)
  operation: find_implementation    # Agent operation
  inputs:
    feature_or_function: "authentication"
    codebase_path: "/path/to/code"
  outputs:
    implementation: result          # Store result as 'explore_code.implementation'
  config:
    cli_type: claude               # claude, codex, copilot
    model: haiku                   # Model to use
  retry:
    max_attempts: 3
    backoff: exponential           # exponential or fixed
    backoff_multiplier: 2
  timeout: 300                      # seconds
  on_error: stop                    # stop or continue
```

**Available Agents:**

- `explore`: ExploreAgent with operations:
  - `explore`: Answer general codebase questions
  - `find_implementation`: Locate feature/function implementations
  - `analyze_structure`: Analyze component or codebase structure
  - `find_usage`: Find all usages of symbols
  - `explain_flow`: Explain execution flows and processes

### 2. Conditional Step (🚧 Future)

Branch execution based on conditions.

```yaml
- id: check_complexity
  type: conditional
  condition: "{{ steps.analyze_structure.result.files_count > 100 }}"
  then:
    - id: detailed_analysis
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "Provide detailed complexity analysis"
  else:
    - id: simple_analysis
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "Provide basic overview"
```

### 3. Parallel Step (🚧 Future)

Execute multiple steps concurrently.

```yaml
- id: parallel_analysis
  type: parallel
  steps:
    - id: find_tests
      type: agent
      agent: explore
      operation: find_usage
      inputs:
        symbol: "test"

    - id: find_docs
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "Where is the documentation?"

    - id: find_config
      type: agent
      agent: explore
      operation: find_implementation
      inputs:
        feature_or_function: "configuration"
  max_concurrency: 3
```

### 4. Loop Step (🚧 Future)

Iterate over a collection.

```yaml
- id: analyze_modules
  type: loop
  items: "{{ inputs.module_list }}"
  item_var: module
  steps:
    - id: analyze_module
      type: agent
      agent: explore
      operation: analyze_structure
      inputs:
        component_or_module: "{{ module }}"
  outputs:
    results: collected  # Collect all iteration results
```

### 5. Transform Step (🚧 Future)

Transform data using Python expressions.

```yaml
- id: transform_results
  type: transform
  script: |
    # Python code to transform data
    results = []
    for item in context.get("parallel_analysis.results", []):
      results.append({
        "summary": item["result"][:100],
        "full": item["result"]
      })
    return {"processed": results}
  outputs:
    transformed: result
```

## Workflow Context

The workflow context manages execution state and data flow between steps.

### Context Structure

```python
{
  "inputs": {
    "codebase_path": "/path/to/code",
    "focus_area": "authentication"
  },
  "steps": {
    "analyze_structure": {
      "status": "completed",
      "result": {...},
      "started_at": "2025-11-08T10:00:00Z",
      "completed_at": "2025-11-08T10:00:05Z"
    },
    "find_patterns": {
      "status": "running",
      "started_at": "2025-11-08T10:00:05Z"
    }
  },
  "outputs": {},
  "metadata": {
    "workflow_id": "uuid-here",
    "execution_id": "uuid-here",
    "started_at": "2025-11-08T10:00:00Z"
  }
}
```

## Execution Model

### Dependency Resolution

The engine automatically determines execution order based on `depends_on` declarations:

```yaml
steps:
  - id: step1
    type: agent
    # ... (runs first)

  - id: step2
    type: agent
    depends_on: [step1]  # Waits for step1

  - id: step3
    type: agent
    depends_on: [step1, step2]  # Waits for both
```

**Key behaviors:**
- Steps without dependencies execute first
- Dependencies form a DAG (no circular references allowed)
- Engine validates dependencies before execution
- Execution stops if dependencies fail (unless on_error: continue)

### Error Handling

Configure retry and failure behavior at step or workflow level:

```yaml
# Workflow-level error handling
error_handling:
  on_failure: stop              # stop or continue
  retry_policy:
    max_attempts: 3
    backoff: exponential        # exponential or fixed
    backoff_multiplier: 2

# Step-level error handling (overrides workflow-level)
steps:
  - id: risky_step
    type: agent
    retry:
      max_attempts: 3
      backoff: exponential
      backoff_multiplier: 2
    timeout: 300                 # seconds
    on_error: continue          # stop or continue
```

**Error Policies:**
- `stop` (default): Stop workflow on failure
- `continue`: Mark step as failed but continue with remaining steps

**Retry Strategies:**
- `fixed`: Wait same amount between retries
- `exponential`: Exponentially increase wait time (backoff_multiplier ** retry_count)

### State Management

The engine tracks:
- **Step Status**: pending, running, completed, failed, skipped
- **Step Results**: Output data from each step
- **Execution Timing**: Start and completion timestamps
- **Retry Counts**: Number of retry attempts per step

Access state in templates:
```yaml
"{{ steps.step_id.result }}"      # Step result data
"{{ steps.step_id.status }}"      # Step status
"{{ steps.step_id.error }}"       # Error message (if failed)
```

## Integration with Agents

### Agent Registry

The `AgentRegistry` manages available agents for workflows:

```python
from plugins.automation.workflows.steps.agent_step import AgentRegistry

# Built-in agents are auto-registered:
# - "explore": ExploreAgent

# Register custom agents:
class ReviewAgent(SpecializedAgent):
    async def review_code(self, file_path):
        # Implementation
        pass

AgentRegistry.register("review", ReviewAgent)
```

### Agent Step Execution

When an agent step executes:

1. **Get agent from registry** based on `agent` field
2. **Create agent configuration** from step `config` and inputs
3. **Resolve inputs** from workflow context
4. **Execute agent operation** (explore, find_implementation, etc.)
5. **Store result** in workflow context
6. **Handle errors** according to retry policy

## Example Workflows

### Example 1: Feature Exploration

Comprehensive exploration of a feature implementation.

```yaml
workflow:
  name: "feature-exploration"
  version: "1.0"
  description: "Comprehensive exploration of a specific feature implementation"

  inputs:
    feature_name:
      type: string
      required: true
      description: "Name of the feature to explore"
    codebase_path:
      type: string
      required: true
      description: "Path to the codebase root directory"

  outputs:
    exploration_report:
      type: object
      description: "Complete feature exploration report"

  steps:
    # Step 1: Find the implementation
    - id: find_implementation
      type: agent
      agent: explore
      operation: find_implementation
      inputs:
        feature_or_function: "{{ inputs.feature_name }}"
        codebase_path: "{{ inputs.codebase_path }}"
      outputs:
        implementation_details: result

    # Step 2: Find where it's used
    - id: find_usage
      type: agent
      agent: explore
      operation: find_usage
      inputs:
        symbol: "{{ inputs.feature_name }}"
        codebase_path: "{{ inputs.codebase_path }}"
      depends_on: [find_implementation]
      outputs:
        usage_locations: result

    # Step 3: Explain the flow
    - id: explain_flow
      type: agent
      agent: explore
      operation: explain_flow
      inputs:
        flow_description: "{{ inputs.feature_name }} implementation and usage"
        codebase_path: "{{ inputs.codebase_path }}"
      depends_on: [find_implementation, find_usage]
      outputs:
        flow_explanation: result

  error_handling:
    on_failure: stop
    retry_policy:
      max_attempts: 2
      backoff: exponential
```

### Example 2: Codebase Onboarding

Generate comprehensive onboarding documentation for a codebase.

```yaml
workflow:
  name: "codebase-onboarding"
  version: "1.0"
  description: "Generate comprehensive onboarding documentation for a codebase"

  inputs:
    codebase_path:
      type: string
      required: true
      description: "Path to the codebase root directory"

  outputs:
    onboarding_guide:
      type: object
      description: "Complete onboarding guide"

  steps:
    # Step 1: Analyze overall structure
    - id: analyze_structure
      type: agent
      agent: explore
      operation: analyze_structure
      inputs:
        codebase_path: "{{ inputs.codebase_path }}"
      outputs:
        structure: result

    # Step 2: Find main entry points
    - id: find_entry_points
      type: agent
      agent: explore
      operation: find_implementation
      inputs:
        feature_or_function: "main entry point"
        codebase_path: "{{ inputs.codebase_path }}"
      depends_on: [analyze_structure]
      outputs:
        entry_points: result

    # Step 3: Find configuration
    - id: find_configuration
      type: agent
      agent: explore
      operation: find_implementation
      inputs:
        feature_or_function: "configuration"
        codebase_path: "{{ inputs.codebase_path }}"
      depends_on: [analyze_structure]
      outputs:
        configuration: result

    # Step 4: Find tests
    - id: find_tests
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "Where are the tests located and how do I run them?"
        codebase_path: "{{ inputs.codebase_path }}"
      depends_on: [analyze_structure]
      outputs:
        testing_info: result

    # Step 5: Find documentation
    - id: find_documentation
      type: agent
      agent: explore
      operation: explore
      inputs:
        question: "Where is the documentation located?"
        codebase_path: "{{ inputs.codebase_path }}"
      depends_on: [analyze_structure]
      outputs:
        documentation: result

  error_handling:
    on_failure: continue  # Continue even if some steps fail
    retry_policy:
      max_attempts: 2
      backoff: fixed
```

## Python API

### Basic Usage

```python
from plugins.automation.workflows import WorkflowDefinition, WorkflowEngine
from plugins.automation.context import WorkflowContext

# Load workflow
workflow = WorkflowDefinition.from_file("workflow.yaml")

# Validate before execution
errors = workflow.validate()
if errors:
    print(f"Validation errors: {errors}")
    return

# Execute
engine = WorkflowEngine()
result = await engine.execute(
    workflow,
    inputs={
        "param1": "value1",
        "param2": "value2"
    }
)

# Check results
if result.status == "completed":
    print(f"Success! Outputs: {result.outputs}")
else:
    print(f"Failed: {result.error}")
```

### Resume Execution

```python
# Save context for later resume
context_dict = context.to_dict()

# Later... restore and resume
context = WorkflowContext.from_dict(context_dict)
result = await engine.execute(workflow, context=context)
```

### Access Step Results

```python
# Get specific step result
step_result = result.step_results.get("find_implementation")
if step_result:
    print(f"Status: {step_result.status}")
    print(f"Result: {step_result.result}")
    print(f"Duration: {step_result.completed_at - step_result.started_at}")
    print(f"Retries: {step_result.retry_count}")
```

### Workflow Validation

```python
# Load and validate
workflow = WorkflowDefinition.from_file("workflow.yaml")
errors = workflow.validate()

if errors:
    print("Validation errors found:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Workflow is valid!")
```

## Adding New Agent Types

To add a new agent to workflows:

```python
# 1. Create your agent class
from utils.agent import SpecializedAgent

class ReviewAgent(SpecializedAgent):
    def get_system_prompt(self) -> str:
        return "You are a code review agent..."

    async def review_code(self, file_path: str) -> str:
        # Implementation
        return await self._executor.execute(
            f"Review the code in {file_path}"
        )

# 2. Register with AgentRegistry
from plugins.automation.workflows.steps.agent_step import AgentRegistry

AgentRegistry.register("review", ReviewAgent)

# 3. Use in workflows
# - id: review_step
#   type: agent
#   agent: review
#   operation: review_code
#   inputs:
#     file_path: "src/main.py"
```

## State Persistence (Future)

### Storage Options

1. **In-Memory** (default, current implementation)
2. **File-based** (future: JSON files in .workflows/ directory)
3. **Database** (future: PostgreSQL, SQLite)

### Planned State Structure

```python
{
  "workflow_id": "uuid",
  "execution_id": "uuid",
  "status": "running",
  "context": {...},
  "history": [
    {
      "step_id": "analyze_structure",
      "status": "completed",
      "result": {...},
      "started_at": "...",
      "completed_at": "..."
    }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

## Best Practices

### 1. Workflow Design

- **Keep workflows focused**: One workflow, one purpose
- **Use meaningful IDs**: Clear, descriptive step identifiers
- **Document inputs/outputs**: Help users understand requirements
- **Handle errors**: Define retry and failure policies
- **Break complex workflows**: Into smaller, reusable workflows

### 2. Step Dependencies

- **Minimize dependencies**: Only declare truly necessary dependencies
- **Avoid cycles**: Dependencies must form a DAG (no circular references)
- **Group independent steps**: Steps without dependencies run first
- **Consider execution order**: Dependent steps wait for all dependencies

### 3. Error Handling

- **Set appropriate retries**: Balance reliability vs speed
- **Use exponential backoff**: For transient failures
- **Choose error policy carefully**:
  - `stop` for critical steps (default)
  - `continue` for optional steps
- **Set reasonable timeouts**: Based on expected operation duration

### 4. Performance

- **Use lightweight models**: Haiku for simple tasks, Sonnet for complex
- **Keep sessions consistent**: Use same session_id for related operations
- **Monitor execution time**: Adjust timeouts based on observed durations
- **Future: Use parallel steps**: For independent operations (when implemented)

### 5. Template Usage

- **Access inputs**: `{{ inputs.param_name }}`
- **Access step results**: `{{ steps.step_id.result }}`
- **Provide defaults**: `{{ context.get("path", "default") }}`
- **String interpolation**: Mix templates with text
- **Keep templates simple**: Complex logic should be in transform steps (future)

## Troubleshooting

### Workflow Validation Fails

```python
errors = workflow.validate()
for error in errors:
    print(f"Error: {error}")
```

**Common issues:**
- Missing required fields (agent, operation, etc.)
- Unknown step dependencies
- Duplicate step IDs
- Invalid step types
- Circular dependencies

### Step Execution Fails

Check the step result for details:

```python
step_result = result.step_results["step_id"]
print(f"Status: {step_result.status}")
print(f"Error: {step_result.error}")
print(f"Retries: {step_result.retry_count}")
```

**Common issues:**
- Agent not registered
- Invalid operation for agent type
- Missing required inputs
- Timeout exceeded
- Template resolution failures

### Template Resolution Issues

Test template resolution:

```python
from plugins.automation.context import WorkflowContext

context = WorkflowContext(inputs={"key": "value"})
resolved = context.resolve_template("{{ inputs.key }}")
print(resolved)  # Should print "value"
```

**Common issues:**
- Typo in path (e.g., `{{ inputs.keey }}`)
- Accessing non-existent step result
- Incorrect dot notation
- Missing quotes in YAML strings

### Dependency Deadlock

If workflow stalls without completing:

1. Check for circular dependencies
2. Verify all referenced step IDs exist
3. Ensure dependencies are spelled correctly
4. Review error logs for failed dependencies

## Implementation Status

### ✅ Currently Implemented

- [x] Workflow definition (YAML parsing and validation)
- [x] Workflow context (state management, template resolution)
- [x] Workflow engine (dependency resolution, sequential execution)
- [x] Agent step type (ExploreAgent integration)
- [x] Error handling (retry policies, failure modes)
- [x] Step-level configuration
- [x] Template expression system
- [x] Example workflows
- [x] Comprehensive documentation

### 🚧 Planned (Future)

- [ ] Conditional steps (branching logic)
- [ ] Parallel steps (concurrent execution)
- [ ] Loop steps (iteration)
- [ ] Transform steps (data transformation)
- [ ] MCP tool interface
- [ ] State persistence (file-based, database)
- [ ] Workflow templates
- [ ] Dynamic step generation
- [ ] Webhook triggers
- [ ] Scheduled execution
- [ ] Version management
- [ ] Approval steps (human-in-the-loop)
- [ ] Notifications (Slack, email)
- [ ] Metrics and monitoring
- [ ] Visual workflow editor

## Design Principles

1. **Declarative**: Workflows are defined declaratively in YAML, not imperatively
2. **Deterministic**: Same inputs produce same execution path
3. **Observable**: Full visibility into execution state and history
4. **Resumable**: Can resume from failures or interruptions
5. **Extensible**: Easy to add new step types and agents
6. **Type-Safe**: Strong typing and validation
7. **Testable**: Each component is independently testable

## Contributing

To contribute to the workflow system:

1. **New step types**: Extend `BaseStep` in `steps/` directory
2. **New agents**: Register with `AgentRegistry`
3. **Tests**: Add tests for new functionality
4. **Documentation**: Update this README
5. **Examples**: Add example workflows demonstrating new features

## See Also

- [Automation Plugin README](../README.md) - Parent plugin documentation
- [ExploreAgent](../agents/explore_agent.py) - Agent implementation
- [Workflow Context](../context.py) - Shared execution context
- [Agent Base Class](../../../utils/agent/agent.py) - Specialized agent framework
