"""
Loop Step

Execute steps for each item in a collection.
"""

import logging
from typing import Any, Dict, List
from datetime import datetime

from ...runtime_data import WorkflowContext, StepResult, StepStatus
from ..definition import StepDefinition
from .base import BaseStep


class LoopStep(BaseStep):
    """
    Loop step that executes child steps for each item in a collection.

    The loop step iterates over items and executes its child steps for each item,
    making the current item available in the context via the item_var.

    Example YAML:
        - id: process_chunks
          type: loop
          items: "{{ steps.split.result.tasks }}"
          item_var: chunk
          steps:
            - id: sum_chunk
              type: transform
              config:
                operation: aggregate
                function: sum
              inputs:
                items: "{{ chunk.items }}"
    """

    def __init__(self, definition: StepDefinition):
        """
        Initialize loop step.

        Args:
            definition: Step definition with loop configuration
        """
        super().__init__(definition)
        self.logger = logging.getLogger(__name__)

    async def execute(self, context: WorkflowContext) -> StepResult:
        """
        Execute loop step.

        Args:
            context: Workflow execution context

        Returns:
            StepResult with loop execution results
        """
        started_at = datetime.utcnow()

        # Resolve items to iterate over
        items_expr = self.definition.items
        if not items_expr:
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.FAILED,
                error="Loop step requires 'items' expression",
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

        # Resolve items from context
        items = context.resolve_template(items_expr)

        if not isinstance(items, list):
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.FAILED,
                error=f"Loop items must be a list, got {type(items)}",
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

        self.logger.info(
            f"Loop step '{self.step_id}' iterating over {len(items)} items"
        )

        # Get item variable name (default: "item")
        item_var = self.definition.item_var or "item"

        # Get child steps
        if not self.definition.loop_steps:
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.FAILED,
                error="Loop step requires child steps",
                started_at=started_at,
                completed_at=datetime.utcnow(),
            )

        # Execute loop iterations
        iteration_results = []
        failed_iterations = 0

        for index, item in enumerate(items):
            self.logger.debug(f"Loop iteration {index + 1}/{len(items)}")

            # Create iteration context by injecting item variable
            # We need to inject at the workflow-level context so templates can resolve it
            # Store original value if it exists
            original_value = None
            had_original = False

            # Check if item_var was in inputs
            if item_var in context.inputs:
                original_value = context.inputs[item_var]
                had_original = True

            # Inject current item into context inputs
            # This makes it available via {{ item_var }} templates
            context.inputs[item_var] = item

            # Also store in a temporary step result so it's accessible via steps.X pattern
            # Create a pseudo step result for the iteration variable
            temp_step_id = f"_loop_var_{item_var}"
            if temp_step_id in context.step_results:
                original_step_result = context.step_results[temp_step_id]
            else:
                original_step_result = None

            context.step_results[temp_step_id] = StepResult(
                step_id=temp_step_id,
                status=StepStatus.COMPLETED,
                result=item
            )

            try:
                # Execute child steps for this iteration
                iteration_result = await self._execute_iteration(
                    index, item, context, item_var
                )
                iteration_results.append(iteration_result)

                if iteration_result.get("status") == "failed":
                    failed_iterations += 1

            finally:
                # Restore original values
                if had_original:
                    context.inputs[item_var] = original_value
                else:
                    context.inputs.pop(item_var, None)

                if original_step_result is not None:
                    context.step_results[temp_step_id] = original_step_result
                else:
                    context.step_results.pop(temp_step_id, None)

        # Aggregate results
        completed_at = datetime.utcnow()
        success_count = len(iteration_results) - failed_iterations

        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED if failed_iterations == 0 else StepStatus.PARTIAL,
            result={
                "iterations": len(items),
                "successful": success_count,
                "failed": failed_iterations,
                "results": iteration_results,
            },
            started_at=started_at,
            completed_at=completed_at,
        )

    async def _execute_iteration(
        self,
        index: int,
        item: Any,
        context: WorkflowContext,
        item_var: str,
    ) -> Dict[str, Any]:
        """
        Execute child steps for one iteration.

        Args:
            index: Iteration index
            item: Current item
            context: Workflow context
            item_var: Variable name for current item

        Returns:
            Dictionary with iteration results
        """
        from ..engine import WorkflowEngine

        iteration_results = {}
        iteration_status = "completed"

        # Import step creation method
        engine = WorkflowEngine()

        # Execute each child step
        for child_def in self.definition.loop_steps:
            # Create unique step ID for this iteration
            iteration_step_id = f"{self.step_id}.{index}.{child_def.id}"

            self.logger.debug(f"Executing loop child step '{iteration_step_id}'")

            try:
                # Create step instance
                child_step = engine._create_step(child_def)

                # Override step ID to make it unique per iteration
                child_step.step_id = iteration_step_id
                child_step.definition.id = iteration_step_id

                # Execute child step
                step_result = await child_step.execute_with_retry(context)

                # Store result
                iteration_results[child_def.id] = {
                    "status": step_result.status.value,
                    "result": step_result.result,
                    "error": step_result.error,
                }

                if step_result.status == StepStatus.FAILED:
                    iteration_status = "failed"
                    # Check error handling
                    if child_def.on_error == "stop":
                        break

            except Exception as e:
                self.logger.error(
                    f"Error executing child step '{child_def.id}': {e}",
                    exc_info=True,
                )
                iteration_results[child_def.id] = {
                    "status": "failed",
                    "error": str(e),
                }
                iteration_status = "failed"

                if child_def.on_error == "stop":
                    break

        return {
            "index": index,
            "item": item,
            "status": iteration_status,
            "step_results": iteration_results,
        }
