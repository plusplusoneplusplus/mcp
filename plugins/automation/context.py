"""
Workflow Context

Manages execution state, data flow, and template resolution for workflows.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from copy import deepcopy


class StepStatus(str, Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a step execution."""

    step_id: str
    status: StepStatus
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "retry_count": self.retry_count,
        }


class WorkflowContext:
    """
    Workflow execution context.

    Manages state, data flow, and template resolution during workflow execution.
    """

    def __init__(
        self,
        inputs: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        execution_id: Optional[str] = None,
    ):
        """
        Initialize workflow context.

        Args:
            inputs: Workflow input parameters
            workflow_id: Unique workflow identifier
            execution_id: Unique execution identifier
        """
        self.inputs = inputs or {}
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.step_results: Dict[str, StepResult] = {}
        self.outputs: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "started_at": datetime.utcnow().isoformat(),
        }

    def get(self, path: str, default: Any = None) -> Any:
        """
        Get value from context using dot notation path.

        Supports:
        - inputs.key
        - steps.step_id.result
        - steps.step_id.status
        - outputs.key

        Args:
            path: Dot-notation path (e.g., "steps.step1.result")
            default: Default value if path not found

        Returns:
            Value at path or default
        """
        parts = path.split(".")
        if not parts:
            return default

        # Navigate through context
        if parts[0] == "inputs":
            obj = self.inputs
            parts = parts[1:]
        elif parts[0] == "steps":
            if len(parts) < 2:
                return default
            step_id = parts[1]
            if step_id not in self.step_results:
                return default
            step_result = self.step_results[step_id]
            if len(parts) == 2:
                return step_result.result
            elif parts[2] == "result":
                obj = step_result.result
                parts = parts[3:]
            elif parts[2] == "status":
                return step_result.status.value
            elif parts[2] == "error":
                return step_result.error
            else:
                return default
        elif parts[0] == "outputs":
            obj = self.outputs
            parts = parts[1:]
        else:
            return default

        # Navigate remaining path
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
                if obj is None:
                    return default
            else:
                return default

        return obj if obj is not None else default

    def set_step_result(self, step_id: str, result: StepResult):
        """
        Set result for a step.

        Args:
            step_id: Step identifier
            result: Step execution result
        """
        self.step_results[step_id] = result

    def get_step_result(self, step_id: str) -> Optional[StepResult]:
        """
        Get result for a step.

        Args:
            step_id: Step identifier

        Returns:
            Step result or None if not found
        """
        return self.step_results.get(step_id)

    def get_step_status(self, step_id: str) -> Optional[StepStatus]:
        """
        Get status for a step.

        Args:
            step_id: Step identifier

        Returns:
            Step status or None if not found
        """
        result = self.step_results.get(step_id)
        return result.status if result else None

    def set_output(self, key: str, value: Any):
        """
        Set workflow output.

        Args:
            key: Output key
            value: Output value
        """
        self.outputs[key] = value

    def resolve_template(self, template: str) -> Any:
        """
        Resolve template expression to value.

        Supports {{ expression }} syntax:
        - {{ inputs.key }}
        - {{ steps.step_id.result }}
        - {{ context.get("path", "default") }}

        Args:
            template: Template string with {{ }} expressions

        Returns:
            Resolved value
        """
        if not isinstance(template, str):
            return template

        # Find all {{ }} expressions
        pattern = r"\{\{\s*([^}]+)\s*\}\}"
        matches = list(re.finditer(pattern, template))

        if not matches:
            return template

        # If entire string is a single template, return the value directly
        if len(matches) == 1 and matches[0].group(0) == template:
            expr = matches[0].group(1).strip()
            return self._evaluate_expression(expr)

        # Replace all templates in string
        result = template
        for match in matches:
            expr = match.group(1).strip()
            value = self._evaluate_expression(expr)
            # Convert value to string for replacement
            str_value = str(value) if value is not None else ""
            result = result.replace(match.group(0), str_value)

        return result

    def _evaluate_expression(self, expr: str) -> Any:
        """
        Evaluate a template expression.

        Args:
            expr: Expression to evaluate

        Returns:
            Evaluated value
        """
        # Handle context.get() calls
        if expr.startswith("context.get("):
            # Extract arguments
            args_str = expr[12:-1]  # Remove "context.get(" and ")"
            args = [arg.strip().strip('"\'') for arg in args_str.split(",")]
            path = args[0]
            default = args[1] if len(args) > 1 else None
            return self.get(path, default)

        # Handle direct paths (inputs.key, steps.step_id.result, etc.)
        return self.get(expr)

    def resolve_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all templates in a dictionary.

        Args:
            data: Dictionary with potential template values

        Returns:
            Dictionary with resolved values
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.resolve_template(value)
            elif isinstance(value, dict):
                result[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.resolve_template(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "inputs": deepcopy(self.inputs),
            "step_results": {
                step_id: result.to_dict()
                for step_id, result in self.step_results.items()
            },
            "outputs": deepcopy(self.outputs),
            "metadata": deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowContext":
        """
        Create context from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            WorkflowContext instance
        """
        metadata = data.get("metadata", {})
        context = cls(
            inputs=data.get("inputs", {}),
            workflow_id=metadata.get("workflow_id"),
            execution_id=metadata.get("execution_id"),
        )
        context.outputs = data.get("outputs", {})
        context.metadata = metadata

        # Restore step results
        for step_id, result_dict in data.get("step_results", {}).items():
            result = StepResult(
                step_id=result_dict["step_id"],
                status=StepStatus(result_dict["status"]),
                result=result_dict.get("result"),
                error=result_dict.get("error"),
                started_at=(
                    datetime.fromisoformat(result_dict["started_at"])
                    if result_dict.get("started_at")
                    else None
                ),
                completed_at=(
                    datetime.fromisoformat(result_dict["completed_at"])
                    if result_dict.get("completed_at")
                    else None
                ),
                retry_count=result_dict.get("retry_count", 0),
            )
            context.step_results[step_id] = result

        return context

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"WorkflowContext(workflow_id={self.workflow_id}, "
            f"execution_id={self.execution_id}, "
            f"steps={len(self.step_results)})"
        )
