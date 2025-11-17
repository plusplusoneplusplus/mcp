"""
Schema definitions for workflow operation results.

Provides typed data structures for operation outputs to make it easier
to access and validate data flowing between workflow steps.
"""

from typing import TypedDict, List, Optional, Any, Literal


# Decompose Operation Schemas
class SubtopicSchema(TypedDict):
    """Schema for a single subtopic from decompose operation."""
    subtopic_id: str
    title: str
    exploration_task: str
    importance: Literal["high", "medium", "low"]
    expected_findings: str


class DecomposeMetadata(TypedDict):
    """Metadata for decompose operation."""
    original_question: str
    cli_type: str
    model: Optional[str]
    ai_decomposition: bool
    fallback: Optional[bool]


class DecomposeResult(TypedDict):
    """Result schema for decompose operation.

    Example:
        {
            "subtopics": [
                {
                    "subtopic_id": "subtopic_1",
                    "title": "Workflow Definition",
                    "exploration_task": "How are workflows defined in YAML?",
                    "importance": "high",
                    "expected_findings": "YAML structure and validation"
                }
            ],
            "subtopic_count": 3,
            "reasoning": "Decomposed into architecture, execution, and integration",
            "metadata": {...}
        }
    """
    subtopics: List[SubtopicSchema]
    subtopic_count: int
    reasoning: str
    metadata: DecomposeMetadata


# Loop Operation Schemas
class LoopIterationResult(TypedDict):
    """Result from a single loop iteration."""
    status: str  # "completed", "failed", "skipped"
    step_results: dict  # Step results keyed by step ID
    error: Optional[str]


class LoopResult(TypedDict):
    """Result schema for loop operation.

    Example:
        {
            "iterations": 3,
            "successful": 3,
            "failed": 0,
            "results": [
                {
                    "status": "completed",
                    "step_results": {...},
                    "error": None
                }
            ]
        }
    """
    iterations: int
    successful: int
    failed: int
    results: List[LoopIterationResult]


# Aggregate Operation Schemas
class AggregateResult(TypedDict):
    """Result schema for aggregate operation.

    Example:
        {
            "result": 150,
            "function": "sum",
            "item_count": 10
        }
    """
    result: Any  # Number, list, or other aggregated value
    function: str  # "sum", "avg", "count", etc.
    item_count: int


# Summarize Operation Schemas
class SummarizeSection(TypedDict):
    """A section in a summarized report."""
    title: str
    content: str


class SummarizeResult(TypedDict):
    """Result schema for summarize operation.

    Example:
        {
            "summary": "Overall findings summary...",
            "sections": [
                {"title": "Findings", "content": "..."},
                {"title": "Analysis", "content": "..."}
            ],
            "result": {...}
        }
    """
    summary: str
    sections: Optional[List[SummarizeSection]]
    result: Optional[Any]  # Structured result data


# Helper functions for type-safe access
def get_decompose_result(step_result: Any) -> Optional[DecomposeResult]:
    """
    Safely extract and validate decompose operation result.

    Args:
        step_result: Raw step result from workflow execution

    Returns:
        DecomposeResult dict if valid, None otherwise

    Example:
        result = workflow.execute(...)
        decompose = get_decompose_result(result.step_results["decompose_question"].result)
        if decompose:
            for subtopic in decompose["subtopics"]:
                print(f"Task: {subtopic['exploration_task']}")
    """
    if not isinstance(step_result, dict):
        return None

    required_keys = {"subtopics", "subtopic_count", "reasoning", "metadata"}
    if not all(key in step_result for key in required_keys):
        return None

    return step_result  # type: ignore


def get_loop_result(step_result: Any) -> Optional[LoopResult]:
    """
    Safely extract and validate loop operation result.

    Args:
        step_result: Raw step result from workflow execution

    Returns:
        LoopResult dict if valid, None otherwise

    Example:
        result = workflow.execute(...)
        loop = get_loop_result(result.step_results["parallel_exploration"].result)
        if loop:
            print(f"Completed {loop['successful']}/{loop['iterations']} iterations")
    """
    if not isinstance(step_result, dict):
        return None

    required_keys = {"iterations", "successful", "failed", "results"}
    if not all(key in step_result for key in required_keys):
        return None

    return step_result  # type: ignore


def get_subtopics(decompose_result: DecomposeResult) -> List[SubtopicSchema]:
    """
    Extract subtopics from decompose result.

    Args:
        decompose_result: Decompose operation result

    Returns:
        List of subtopic schemas

    Example:
        subtopics = get_subtopics(decompose_result)
        for i, subtopic in enumerate(subtopics, 1):
            print(f"{i}. {subtopic['title']} [{subtopic['importance']}]")
            print(f"   Task: {subtopic['exploration_task']}")
    """
    return decompose_result["subtopics"]


def get_exploration_findings(loop_result: LoopResult) -> List[Any]:
    """
    Extract findings from parallel exploration loop.

    Args:
        loop_result: Loop operation result

    Returns:
        List of findings from each iteration

    Example:
        findings = get_exploration_findings(loop_result)
        for i, finding in enumerate(findings, 1):
            print(f"Finding {i}: {finding}")
    """
    findings = []
    for iteration in loop_result["results"]:
        if iteration["status"] == "completed" and iteration["step_results"]:
            # Get first step result from iteration
            first_step = list(iteration["step_results"].values())[0]

            # Handle different result formats
            if hasattr(first_step, 'result'):
                # StepResult object - extract the result
                result = first_step.result

                # If result is a dict with 'finding' key (from exploration operation)
                if isinstance(result, dict) and 'finding' in result:
                    findings.append(result['finding'])
                # Otherwise use the result directly (e.g., string from agent step)
                else:
                    findings.append(result)
            elif isinstance(first_step, dict):
                # Already a dict - use directly
                findings.append(first_step)
    return findings
