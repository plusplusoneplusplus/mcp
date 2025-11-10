# Exploration Map-Reduce Workflow Examples

This directory contains example workflows demonstrating the map-reduce pattern for AI-powered codebase exploration.

## Overview

The exploration map-reduce workflow enables parallel AI exploration of codebases with automatic result aggregation:

1. **Split Phase**: Divide exploration work into smaller tasks
2. **Map Phase**: Execute parallel AI explorations, storing findings in session files
3. **Reduce Phase**: Aggregate and summarize all findings

## Workflow Files

### `exploration_mapreduce.yaml`
Basic map-reduce workflow with fixed number of exploration tasks. Good for understanding the pattern.

**Features:**
- Splits exploration questions into individual tasks
- Runs 4 parallel explorations
- Stores findings in session files
- Aggregates results into a comprehensive summary

**Usage:**
```python
from plugins.automation.workflows import WorkflowEngine, WorkflowDefinition

# Load workflow
workflow = WorkflowDefinition.from_file(
    "plugins/automation/workflows/examples/exploration_mapreduce.yaml"
)

# Execute
engine = WorkflowEngine()
result = await engine.execute(
    workflow,
    inputs={
        "codebase_path": "/path/to/your/project",
        "exploration_questions": [
            "How does authentication work?",
            "What are the main API endpoints?",
            "How is error handling implemented?",
            "What database operations are performed?"
        ],
        "session_dir": ".mcp_sessions",
        "summary_format": "detailed"
    }
)

# Access results
summary = result.outputs["summary"]
print(f"Explored {len(result.outputs['session_files'])} areas")
print(f"Summary: {summary}")
```

### `exploration_mapreduce_dynamic.yaml`
Advanced workflow using loop steps for dynamic task handling (requires loop step support).

**Features:**
- Handles variable numbers of tasks dynamically
- Configurable parallel workers
- Supports different exploration types
- Creates multiple summary formats

**Usage:**
```python
# Execute with custom tasks
result = await engine.execute(
    workflow,
    inputs={
        "codebase_path": "/path/to/project",
        "exploration_tasks": [
            "How does authentication work?",
            {"type": "implementation", "query": "user login"},
            {"type": "structure", "query": "API router"},
            "What testing framework is used?"
        ],
        "parallel_workers": 4
    }
)
```

## Operations Used

### Split Operation
Divides work into smaller tasks for parallel processing.

**Strategies:**
- `by_items`: One task per item
- `by_count`: Divide into N roughly equal tasks
- `by_chunk_size`: Fixed-size chunks
- `custom`: Custom split expression

### Exploration Operation
Performs AI-powered exploration and stores findings in session files.

**Types:**
- `question`: Explore a question about the codebase
- `implementation`: Find implementation of a feature
- `structure`: Analyze component structure
- `usage`: Find symbol usage
- `flow`: Explain execution flow

### Summarize Operation
Aggregates findings from session files into comprehensive summaries.

**Formats:**
- `detailed`: Full information with metadata
- `concise`: Key points only
- `structured`: Grouped by exploration type

## Session Files

Exploration findings are stored in session files with the following structure:

```json
{
  "session_id": "exploration_20240101_120000",
  "task_index": 0,
  "task": {
    "item": "How does authentication work?",
    "index": 0
  },
  "exploration_type": "question",
  "finding": {
    "exploration_type": "question",
    "status": "completed",
    "query": "How does authentication work?",
    "result": "..."
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

## Output Example

The summarize operation produces structured output:

```json
{
  "summary": {
    "total_findings": 4,
    "by_exploration_type": {
      "question": {
        "count": 3,
        "findings": [...]
      },
      "implementation": {
        "count": 1,
        "findings": [...]
      }
    },
    "metadata": {
      "exploration_types": ["question", "implementation"],
      "counts_by_type": {
        "question": 3,
        "implementation": 1
      }
    }
  },
  "finding_count": 4,
  "session_files_read": [
    ".mcp_sessions/exploration_..._task_0.json",
    ".mcp_sessions/exploration_..._task_1.json",
    ...
  ]
}
```

## Customization

### Custom Split Strategy

```yaml
- id: custom_split
  type: transform
  config:
    operation: split
    strategy: custom
    expression: "[{'items': items[:3]}, {'items': items[3:]}]"
  inputs:
    items: "{{ inputs.data }}"
```

### Multiple Summary Formats

```yaml
# Detailed summary
- id: detailed_summary
  type: transform
  config:
    operation: summarize
    summary_format: detailed

# Concise summary
- id: concise_summary
  type: transform
  config:
    operation: summarize
    summary_format: concise
```

## Best Practices

1. **Session Management**: Use consistent session_id across exploration steps for proper aggregation
2. **Error Handling**: Set `error_handling.default: continue` to continue with other tasks on failure
3. **Parallel Workers**: Adjust based on system resources and API rate limits
4. **Session Cleanup**: Clean up old session files periodically
5. **Result Storage**: Store important summaries to files for later reference

## Integration with Agents

The exploration operation is designed to integrate with the ExploreAgent:

```python
# In exploration.py, integrate with actual agent:
from ...agents import ExploreAgent, ExploreAgentConfig
from utils.agent import CLIType

config = ExploreAgentConfig(
    cli_type=CLIType.CLAUDE,
    cwd=codebase_path,
    session_id=session_id
)
agent = ExploreAgent(config)
result = await agent.explore(question=question, codebase_path=codebase_path)
```

## Future Enhancements

- [ ] Parallel step support for true concurrent execution
- [ ] Real-time progress tracking
- [ ] AI-powered summary generation
- [ ] Integration with vector stores for semantic search
- [ ] Cross-codebase exploration
- [ ] Interactive exploration refinement
