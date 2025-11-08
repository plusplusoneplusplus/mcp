"""
Base Step

Abstract base class for all workflow steps.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...context import WorkflowContext, StepResult, StepStatus
from ..definition import StepDefinition


class BaseStep(ABC):
    """
    Abstract base class for workflow steps.

    All step types must inherit from this class and implement the execute method.
    """

    def __init__(self, definition: StepDefinition):
        """
        Initialize step.

        Args:
            definition: Step definition from workflow
        """
        self.definition = definition
        self.step_id = definition.id

    @abstractmethod
    async def execute(self, context: WorkflowContext) -> StepResult:
        """
        Execute the step.

        Args:
            context: Workflow execution context

        Returns:
            StepResult with execution outcome

        Raises:
            Exception: If step execution fails
        """
        pass

    def can_execute(self, context: WorkflowContext) -> bool:
        """
        Check if step can execute based on dependencies.

        Args:
            context: Workflow execution context

        Returns:
            True if all dependencies are completed
        """
        for dep_id in self.definition.depends_on:
            dep_status = context.get_step_status(dep_id)
            if dep_status != StepStatus.COMPLETED:
                return False
        return True

    def resolve_inputs(self, context: WorkflowContext) -> Dict[str, Any]:
        """
        Resolve step inputs from context.

        Args:
            context: Workflow execution context

        Returns:
            Resolved inputs dictionary
        """
        return context.resolve_dict(self.definition.inputs)

    def store_outputs(
        self, context: WorkflowContext, result: Any, outputs_config: Dict[str, str]
    ):
        """
        Store step outputs in context.

        Args:
            context: Workflow execution context
            result: Step execution result
            outputs_config: Output configuration (e.g., {"key": "result"})
        """
        for output_key, source_path in outputs_config.items():
            if source_path == "result":
                value = result
            else:
                # Navigate result object if path specified
                value = result
                for part in source_path.split("."):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        break

            # Store in context for other steps to use
            context.set_output(f"{self.step_id}.{output_key}", value)

    async def execute_with_retry(self, context: WorkflowContext) -> StepResult:
        """
        Execute step with retry logic.

        Args:
            context: Workflow execution context

        Returns:
            StepResult with execution outcome
        """
        retry_config = self.definition.retry or {}
        max_attempts = retry_config.get("max_attempts", 1)
        backoff = retry_config.get("backoff", "fixed")
        backoff_multiplier = retry_config.get("backoff_multiplier", 2)

        retry_count = 0
        last_error = None

        while retry_count < max_attempts:
            try:
                # Create step result
                step_result = StepResult(
                    step_id=self.step_id,
                    status=StepStatus.RUNNING,
                    started_at=datetime.utcnow(),
                    retry_count=retry_count,
                )
                context.set_step_result(self.step_id, step_result)

                # Execute step
                result = await self.execute(context)

                # Mark as completed and set retry count
                result.status = StepStatus.COMPLETED
                result.completed_at = datetime.utcnow()
                result.retry_count = retry_count
                context.set_step_result(self.step_id, result)

                # Store outputs if configured
                if self.definition.outputs:
                    self.store_outputs(context, result.result, self.definition.outputs)

                return result

            except Exception as e:
                last_error = str(e)
                retry_count += 1

                if retry_count < max_attempts:
                    # Calculate backoff delay
                    if backoff == "exponential":
                        delay = (backoff_multiplier ** retry_count) - 1
                    else:
                        delay = 1

                    # Wait before retry (in real implementation)
                    # await asyncio.sleep(delay)
                    pass
                else:
                    # Max retries exceeded
                    step_result = StepResult(
                        step_id=self.step_id,
                        status=StepStatus.FAILED,
                        error=last_error,
                        started_at=step_result.started_at,
                        completed_at=datetime.utcnow(),
                        retry_count=retry_count,
                    )
                    context.set_step_result(self.step_id, step_result)
                    return step_result

        # Should never reach here, but just in case
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.FAILED,
            error=last_error,
            retry_count=retry_count,
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"{self.__class__.__name__}("
            f"id='{self.step_id}', "
            f"type='{self.definition.type}')"
        )
