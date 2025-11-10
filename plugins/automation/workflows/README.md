# Workflow System

Deterministic orchestration of AI agents and data operations through declarative YAML workflows.

## Overview

The workflow system enables reproducible automation through:
- **Declarative YAML workflows** - Define complex operations as configuration
- **Dependency resolution** - Automatic execution ordering via DAG
- **Template expressions** - Dynamic data flow between steps
- **Error handling** - Configurable retry policies and failure modes
- **Pluggable operations** - Extensible step types and operations

## Quick Start

**Define workflow (YAML):**
```yaml
workflow:
  name: "analyze-feature"
  inputs:
    feature_name: {type: string, required: true}
    codebase_path: {type: string, required: true}

  steps:
    - id: find_impl
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
      depends_on: [find_impl]
      inputs:
        symbol: "{{ inputs.feature_name }}"
        codebase_path: "{{ inputs.codebase_path }}"
```

**Execute (Python):**
```python
from plugins.automation.workflows import WorkflowDefinition, WorkflowEngine

workflow = WorkflowDefinition.from_file("analyze-feature.yaml")
engine = WorkflowEngine()
result = await engine.execute(workflow, inputs={
    "feature_name": "authentication",
    "codebase_path": "/path/to/code"
})

print(f"Status: {result.status}")
print(f"Results: {result.outputs}")
```

## Step Types

### 1. Agent Step

Execute AI agent operations.

```yaml
- id: explore_code
  type: agent
  agent: explore                    # Agent type
  operation: find_implementation    # Agent operation
  inputs:
    feature_or_function: "auth"
    codebase_path: "/code"
  config:
    model: haiku                   # Optional: model override
  retry:
    max_attempts: 3
    backoff: exponential
  timeout: 300
  on_error: stop                    # stop | continue
```

**Available agents:**
- `explore`: Codebase exploration (find_implementation, analyze_structure, find_usage, explain_flow)

### 2. Transform Step

Generic data transformation with pluggable operations.

**Comparison (Multi-model validation):**
```yaml
- id: compare
  type: transform
  config:
    operation: compare_results
  inputs:
    model_1_result: "{{ steps.sonnet.result }}"
    model_2_result: "{{ steps.haiku.result }}"
    threshold: 0.75
```

**Aggregation:**
```yaml
- id: total
  type: transform
  config:
    operation: aggregate
    function: sum              # sum, avg, count, min, max, group_by, concat
  inputs:
    items: [1, 2, 3, 4, 5]
```

**Filtering:**
```yaml
- id: active_only
  type: transform
  config:
    operation: filter
    condition: equals          # equals, contains, greater_than, less_than, regex
    field: status
    value: "active"
  inputs:
    items: "{{ steps.users.result }}"
```

**Mapping:**
```yaml
- id: extract_names
  type: transform
  config:
    operation: map
    function: extract          # extract, project, compute, transform
    fields: name
  inputs:
    items: "{{ steps.users.result }}"
```

### 3. Map-Reduce Exploration Operations

**Split:** Divide exploration tasks into parallel chunks
```yaml
- id: split_tasks
  type: transform
  config:
    operation: split
    strategy: by_items         # by_items, by_count, by_chunk_size, custom
  inputs:
    items: ["Q1", "Q2", "Q3"]
```

**AI Split:** Let AI intelligently decompose exploration goals (uses CLIExecutor)
```yaml
- id: ai_split
  type: transform
  config:
    operation: ai_split
    model: haiku              # Fast model for task decomposition
    max_tasks: 8
  inputs:
    goal: "Understand how authentication works"
    codebase_path: "/code"
```

**Explore:** AI-powered exploration with session storage (uses ExploreAgent)
```yaml
- id: explore_task
  type: transform
  config:
    operation: explore
    exploration_type: question  # question, implementation, structure, usage, flow
    session_dir: .mcp_sessions
    save_to_session: true
  inputs:
    task: "{{ task }}"
    codebase_path: "/code"
```

**Summarize:** Aggregate findings from session files
```yaml
- id: summarize
  type: transform
  config:
    operation: summarize
    summary_format: structured  # detailed, concise, structured
    output_file: summary.json
  inputs:
    session_id: "{{ context.execution_id }}"
```

The map-reduce exploration pattern enables parallel AI exploration of codebases with automatic result aggregation. **AI Split** uses Claude to intelligently decompose goals into focused tasks, **Explore** operations use ExploreAgent to investigate each task independently (storing findings in session files), and **Summarize** aggregates all results into comprehensive reports. See [examples/ai_exploration_workflow.yaml](examples/ai_exploration_workflow.yaml) for AI-driven exploration or [examples/exploration_mapreduce.yaml](examples/exploration_mapreduce.yaml) for manual task specification.

See [TRANSFORM_GUIDE.md](examples/TRANSFORM_GUIDE.md) for complete operation reference.

## Template Expressions

Access dynamic values using `{{ }}`:

```yaml
"{{ inputs.param }}"                    # Workflow inputs
"{{ steps.step_id.result }}"            # Step results
"{{ steps.step_id.result.field }}"      # Nested field access
"{{ context.get('key', 'default') }}"   # Context with default
```

## Workflow Definition

```yaml
workflow:
  name: string                    # Required: workflow identifier
  version: string                 # Optional: semantic version
  description: string             # Optional: description

  inputs:                         # Input parameters
    param_name:
      type: string                # string, number, boolean, array, object
      required: bool
      default: any
      description: string

  outputs:                        # Output definitions
    output_name:
      value: "{{ steps.x.result }}"
      description: string

  steps:                          # Workflow steps
    - id: step_id                 # Unique identifier
      type: agent | transform     # Step type
      depends_on: []              # Step dependencies
      # ... type-specific config

  error_handling:                 # Optional: global error handling
    on_failure: stop              # stop | continue
    retry_policy:
      max_attempts: 3
      backoff: exponential        # exponential | fixed
```

## Execution Model

**Dependency Resolution:**
- Steps execute in dependency order (DAG)
- Independent steps can run concurrently (future)
- Circular dependencies are rejected during validation

**Error Handling:**
- `stop` (default): Halt workflow on step failure
- `continue`: Mark failed, continue with remaining steps
- Retry with exponential/fixed backoff

**State Management:**
- Track step status (pending, running, completed, failed)
- Store results, timing, retry counts
- Resume from last successful step (future)

## Architecture

```
plugins/automation/workflows/
├── definition.py               # WorkflowDefinition - YAML parsing
├── engine.py                   # WorkflowEngine - execution orchestrator
├── steps/
│   ├── base.py                 # BaseStep - abstract base
│   ├── agent_step.py           # AgentStep - AI agent operations
│   ├── transform_step.py       # TransformStep - data operations
│   └── operations/             # Pluggable transform operations
│       ├── base.py             # BaseOperation, OperationRegistry
│       ├── comparison.py       # Model comparison operations
│       ├── aggregation.py      # Data aggregation
│       ├── filtering.py        # Data filtering
│       ├── mapping.py          # Data mapping/transformation
│       ├── split.py            # Task splitting for map-reduce
│       ├── exploration.py      # AI exploration with session storage
│       └── summarize.py        # Result aggregation and summarization
└── examples/
    ├── TRANSFORM_GUIDE.md      # Transform operations reference
    ├── feature_exploration.yaml
    ├── codebase_onboarding.yaml
    ├── model_comparison_mapreduce.yaml
    └── exploration_mapreduce.yaml        # Map-reduce exploration workflow
```

## Common Patterns

### Pattern 1: Map-Reduce (Multi-model Consensus)

```yaml
# Map: Execute on multiple models
- id: model_1
  type: agent
  inputs: {question: "{{ inputs.prompt }}"}

- id: model_2
  type: agent
  inputs: {question: "{{ inputs.prompt }}"}

# Reduce: Compare and verify
- id: compare
  type: transform
  depends_on: [model_1, model_2]
  config: {operation: compare_results}
  inputs:
    model_1_result: "{{ steps.model_1.result }}"
    model_2_result: "{{ steps.model_2.result }}"
    threshold: 0.75

- id: verify
  type: transform
  depends_on: [compare]
  config: {operation: verify_consensus}
  inputs:
    comparison: "{{ steps.compare.result }}"
    threshold: 0.75
```

### Pattern 2: Filter → Transform → Aggregate

```yaml
- id: filter
  type: transform
  config: {operation: filter, condition: equals, field: status, value: "active"}
  inputs: {items: "{{ inputs.users }}"}

- id: extract
  type: transform
  depends_on: [filter]
  config: {operation: map, function: extract, fields: score}
  inputs: {items: "{{ steps.filter.result.filtered_items }}"}

- id: average
  type: transform
  depends_on: [extract]
  config: {operation: aggregate, function: avg}
  inputs: {items: "{{ steps.extract.result.mapped_items }}"}
```

## Python API

```python
from plugins.automation.workflows import WorkflowDefinition, WorkflowEngine

# Load and validate
workflow = WorkflowDefinition.from_file("workflow.yaml")
errors = workflow.validate()
if errors:
    print(f"Validation errors: {errors}")

# Execute
engine = WorkflowEngine()
result = await engine.execute(workflow, inputs={...})

# Access results
if result.status == "completed":
    for step_id, step_result in result.step_results.items():
        print(f"{step_id}: {step_result.status}")
else:
    print(f"Failed: {result.error}")
```

## Extending the System

### Add Custom Agent

```python
from utils.agent import SpecializedAgent
from plugins.automation.workflows.steps.agent_step import AgentRegistry

class ReviewAgent(SpecializedAgent):
    async def review_code(self, file_path: str) -> str:
        return await self._executor.execute(f"Review {file_path}")

AgentRegistry.register("review", ReviewAgent)
```

### Add Custom Transform Operation

```python
from plugins.automation.workflows.steps.operations.base import BaseOperation
from plugins.automation.workflows.steps.operations import registry

class MyOperation(BaseOperation):
    def validate(self) -> Optional[str]:
        if "required_field" not in self.inputs:
            return "MyOperation requires 'required_field'"
        return None

    async def execute(self) -> Dict[str, Any]:
        data = self.inputs["required_field"]
        return {"result": process(data)}

registry.register("my_operation", MyOperation)
```

## Testing

```bash
# Test workflow engine
uv run pytest plugins/automation/tests/test_workflow_engine.py -v

# Test transform operations
uv run pytest plugins/automation/tests/test_transform_operations.py -v

# Test all
uv run pytest plugins/automation/tests/ -v
```

## Examples

See `examples/` directory:
- `feature_exploration.yaml` - Sequential agent workflow
- `codebase_onboarding.yaml` - Multi-step codebase analysis
- `model_comparison_mapreduce.yaml` - Multi-model validation with consensus
- `TRANSFORM_GUIDE.md` - Complete transform operations reference

## Best Practices

1. **Keep workflows focused** - One workflow, one purpose
2. **Use meaningful IDs** - Clear step identifiers
3. **Document thoroughly** - Add descriptions to inputs/outputs
4. **Handle errors** - Set appropriate retry policies
5. **Minimize dependencies** - Only declare necessary dependencies
6. **Use appropriate models** - Haiku for simple tasks, Sonnet for complex
7. **Chain operations** - Use transform steps for data pipelines

## Implementation Status

**✅ Implemented:**
- Workflow definition (YAML parsing, validation)
- Workflow engine (DAG resolution, execution)
- Agent step type (ExploreAgent integration)
- Transform step type (11 operations: comparison, aggregation, filtering, mapping, split, explore, summarize)
- Map-reduce exploration pattern with session storage
- Error handling (retry policies, failure modes)
- Template expression system

**🚧 Future:**
- Conditional steps (branching)
- Parallel execution (true concurrent processing)
- Loop steps (iteration)
- State persistence
- MCP tool interface
- Webhook triggers
