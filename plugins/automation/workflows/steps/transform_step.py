"""Transform step implementation for data transformation and aggregation operations."""

from typing import Any, Dict, Optional
from .base import BaseStep, StepStatus
from ...context import WorkflowContext, StepResult
from .operations import registry


class TransformStep(BaseStep):
    """
    Generic step for transforming and aggregating data.

    Uses a pluggable operation system that supports:
    - Comparison operations (compare_results, verify_consensus)
    - Aggregation operations (sum, avg, count, min, max, group_by, concat)
    - Filtering operations (equals, contains, greater_than, less_than, regex)
    - Mapping operations (extract, project, compute, transform)
    - Custom operations (register your own)

    Example usage in YAML:

    ```yaml
    # Model comparison
    - id: compare_models
      type: transform
      config:
        operation: compare_results
      inputs:
        model_1_result: "{{ steps.model_1.result }}"
        model_2_result: "{{ steps.model_2.result }}"
        threshold: 0.75

    # Aggregation
    - id: aggregate_scores
      type: transform
      config:
        operation: aggregate
        function: avg
      inputs:
        items: "{{ steps.evaluate.result.scores }}"

    # Filtering
    - id: filter_errors
      type: transform
      config:
        operation: filter
        condition: contains
        field: message
        value: "error"
      inputs:
        items: "{{ steps.logs.result }}"

    # Mapping
    - id: extract_names
      type: transform
      config:
        operation: map
        function: extract
        fields: ["name", "id"]
      inputs:
        items: "{{ steps.users.result }}"
    ```
    """

    def __init__(self, definition):
        """
        Initialize transform step.

        Args:
            definition: Step definition

        Raises:
            ValueError: If step configuration is invalid
        """
        super().__init__(definition)
        if definition.type != "transform":
            raise ValueError(f"Step {definition.id} is not a transform step")

        # Get operation name
        operation_name = definition.config.get("operation", "transform")

        # Get operation class from registry
        operation_class = registry.get(operation_name)
        if not operation_class:
            # For backward compatibility, allow custom operations
            # They will use the default pass-through behavior
            if operation_name != "transform":
                raise ValueError(
                    f"Unknown operation '{operation_name}'. "
                    f"Available: {', '.join(registry.list_operations())}"
                )

        # Validate operation if it's registered
        if operation_class:
            # Create a temporary instance to validate
            temp_inputs = definition.inputs or {}
            temp_operation = operation_class(definition.config, temp_inputs)
            validation_error = temp_operation.validate()
            if validation_error:
                raise ValueError(
                    f"Transform step '{definition.id}' validation failed: {validation_error}"
                )

    async def execute(self, context: WorkflowContext) -> StepResult:
        """
        Execute the transformation operation.

        Args:
            context: Workflow execution context

        Returns:
            StepResult with transformed/aggregated result
        """
        # Resolve inputs from context
        inputs = self.resolve_inputs(context)
        operation_name = self.definition.config.get("operation", "transform")

        # Get operation class from registry
        operation_class = registry.get(operation_name)

        if operation_class:
            # Execute registered operation
            operation = operation_class(self.definition.config, inputs)
            result = await operation.execute()
        else:
            # Fall back to custom transform (pass-through)
            result = {
                "transformed": True,
                "inputs": inputs,
                "operation": operation_name,
            }

        return StepResult(
            step_id=self.step_id,
            status=StepStatus.COMPLETED,
            result=result,
        )
