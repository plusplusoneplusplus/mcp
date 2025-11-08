"""
Workflow Engine

Execute workflows with dependency resolution and state management.
"""

import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from ..runtime_data import WorkflowContext, StepResult, StepStatus
from .definition import WorkflowDefinition, StepDefinition
from .steps import BaseStep, AgentStep, TransformStep


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some steps completed, some failed


@dataclass
class WorkflowExecutionResult:
    """Result of workflow execution."""

    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "status": self.status.value,
            "outputs": self.outputs,
            "step_results": {
                step_id: result.to_dict()
                for step_id, result in self.step_results.items()
            },
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }


class WorkflowEngine:
    """
    Workflow execution engine.

    Executes workflows with dependency resolution, error handling, and state management.
    """

    def __init__(self):
        """Initialize workflow engine."""
        self.logger = logging.getLogger(__name__)

    async def execute(
        self,
        workflow: WorkflowDefinition,
        inputs: Optional[Dict[str, Any]] = None,
        context: Optional[WorkflowContext] = None,
    ) -> WorkflowExecutionResult:
        """
        Execute a workflow.

        Args:
            workflow: Workflow definition
            inputs: Workflow inputs
            context: Existing context (for resume)

        Returns:
            WorkflowExecutionResult with execution outcome

        Raises:
            ValueError: If workflow is invalid
        """
        # Validate workflow
        errors = workflow.validate()
        if errors:
            raise ValueError(f"Invalid workflow: {', '.join(errors)}")

        # Validate inputs
        self._validate_inputs(workflow, inputs or {})

        # Create or use existing context
        if context is None:
            execution_id = str(uuid.uuid4())
            context = WorkflowContext(
                inputs=inputs or {},
                workflow_id=workflow.name,
                execution_id=execution_id,
            )
        else:
            execution_id = context.execution_id or str(uuid.uuid4())

        # Create execution result
        result = WorkflowExecutionResult(
            workflow_id=workflow.name,
            execution_id=execution_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        self.logger.info(
            f"Starting workflow '{workflow.name}' (execution: {execution_id})"
        )

        try:
            # Execute steps
            await self._execute_steps(workflow, context)

            # Collect outputs
            result.outputs = context.outputs
            result.step_results = context.step_results

            # Determine final status
            result.status = self._determine_status(context, workflow)
            result.completed_at = datetime.utcnow()

            self.logger.info(
                f"Workflow '{workflow.name}' completed with status: {result.status}"
            )

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            # Include step results and outputs even on failure
            result.step_results = context.step_results
            result.outputs = context.outputs

        return result

    def _validate_inputs(
        self, workflow: WorkflowDefinition, inputs: Dict[str, Any]
    ):
        """
        Validate workflow inputs.

        Args:
            workflow: Workflow definition
            inputs: Provided inputs

        Raises:
            ValueError: If required inputs are missing
        """
        for name, input_def in workflow.inputs.items():
            if input_def.required and name not in inputs:
                raise ValueError(f"Required input '{name}' not provided")

    async def _execute_steps(
        self, workflow: WorkflowDefinition, context: WorkflowContext
    ):
        """
        Execute workflow steps in dependency order.

        Args:
            workflow: Workflow definition
            context: Execution context
        """
        # Create step instances
        steps = []
        for step_def in workflow.steps:
            step = self._create_step(step_def)
            steps.append(step)

        # Execute steps in order, respecting dependencies
        executed = set()
        max_iterations = len(steps) * 2  # Prevent infinite loops
        iteration = 0

        while len(executed) < len(steps) and iteration < max_iterations:
            iteration += 1
            progress = False

            for step in steps:
                if step.step_id in executed:
                    continue

                # Check if dependencies are met
                if step.can_execute(context):
                    self.logger.info(f"Executing step '{step.step_id}'")

                    # Execute step with retry
                    step_result = await step.execute_with_retry(context)

                    # Store step result in context
                    context.set_step_result(step.step_id, step_result)

                    # Handle step result
                    if step_result.status == StepStatus.COMPLETED:
                        executed.add(step.step_id)
                        progress = True
                    elif step_result.status == StepStatus.FAILED:
                        # Check error handling policy
                        on_error = step.definition.on_error
                        if on_error == "stop":
                            raise Exception(
                                f"Step '{step.step_id}' failed: {step_result.error}"
                            )
                        elif on_error == "continue":
                            self.logger.warning(
                                f"Step '{step.step_id}' failed but continuing: "
                                f"{step_result.error}"
                            )
                            executed.add(step.step_id)
                            progress = True

            # If no progress was made, we have a dependency deadlock
            if not progress:
                break

        # Check if all steps executed
        if len(executed) < len(steps):
            unexecuted = [s.step_id for s in steps if s.step_id not in executed]
            self.logger.warning(
                f"Not all steps executed. Unexecuted: {', '.join(unexecuted)}"
            )

    def _create_step(self, step_def: StepDefinition) -> BaseStep:
        """
        Create step instance from definition.

        Args:
            step_def: Step definition

        Returns:
            BaseStep instance

        Raises:
            ValueError: If step type not supported
        """
        if step_def.type == "agent":
            return AgentStep(step_def)
        elif step_def.type == "transform":
            return TransformStep(step_def)
        else:
            raise ValueError(
                f"Step type '{step_def.type}' not yet implemented. "
                f"Currently supported types: 'agent', 'transform'"
            )

    def _determine_status(
        self, context: WorkflowContext, workflow: WorkflowDefinition
    ) -> WorkflowStatus:
        """
        Determine final workflow status based on step results.

        Args:
            context: Execution context
            workflow: Workflow definition

        Returns:
            Final workflow status
        """
        total_steps = len(workflow.steps)
        completed = sum(
            1
            for r in context.step_results.values()
            if r.status == StepStatus.COMPLETED
        )
        failed = sum(
            1
            for r in context.step_results.values()
            if r.status == StepStatus.FAILED
        )

        if completed == total_steps:
            return WorkflowStatus.COMPLETED
        elif failed > 0 and completed == 0:
            return WorkflowStatus.FAILED
        elif failed > 0 or completed < total_steps:
            return WorkflowStatus.PARTIAL
        else:
            return WorkflowStatus.COMPLETED
