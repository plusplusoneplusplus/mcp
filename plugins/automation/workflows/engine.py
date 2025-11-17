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
from pathlib import Path

from ..runtime_data import WorkflowContext, StepResult, StepStatus
from .definition import WorkflowDefinition, StepDefinition
from .steps import BaseStep, AgentStep, TransformStep, LoopStep
from utils.session import SessionManager, Session
from utils.session.storage import FileSystemSessionStorage


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

    def __init__(self, session_manager: Optional[SessionManager] = None):
        """
        Initialize workflow engine.

        Args:
            session_manager: Optional SessionManager for state persistence.
                           If not provided, creates a default file-based one.
        """
        self.logger = logging.getLogger(__name__)

        # Initialize session management
        if session_manager is None:
            # Create default session storage in .mcp/workflows directory
            workflows_dir = Path.home() / ".mcp" / "workflows"
            history_dir = workflows_dir / ".history"
            storage = FileSystemSessionStorage(
                sessions_dir=workflows_dir / "sessions",
                history_dir=history_dir
            )
            self.session_manager = SessionManager(storage)
        else:
            self.session_manager = session_manager

    async def execute(
        self,
        workflow: WorkflowDefinition,
        inputs: Optional[Dict[str, Any]] = None,
        context: Optional[WorkflowContext] = None,
        session_id: Optional[str] = None,
        persist: bool = True,
    ) -> WorkflowExecutionResult:
        """
        Execute a workflow.

        Args:
            workflow: Workflow definition
            inputs: Workflow inputs
            context: Existing context (for resume)
            session_id: Optional session ID for persistence. If not provided, creates new session.
            persist: Whether to persist state to session (default: True)

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

        # Session management
        session: Optional[Session] = None
        if persist:
            # Create or get session
            if session_id:
                session = self.session_manager.get_session(session_id)
                if not session:
                    raise ValueError(f"Session {session_id} not found")
            else:
                # Create new session
                session = self.session_manager.create_session(
                    purpose=f"Workflow: {workflow.name}",
                    tags=["workflow", workflow.name],
                )
                session_id = session.metadata.session_id
                self.logger.info(f"Created session: {session_id}")

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

        # Store session_id in context metadata
        if session_id:
            context.metadata["session_id"] = session_id

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

        # Save initial state to session
        if persist and session:
            self._save_to_session(session, workflow, context, result)

        try:
            # Execute steps
            await self._execute_steps(workflow, context, session if persist else None)

            # Collect outputs
            result.outputs = context.outputs
            result.step_results = context.step_results

            # Determine final status
            result.status = self._determine_status(context, workflow)
            result.completed_at = datetime.utcnow()

            self.logger.info(
                f"Workflow '{workflow.name}' completed with status: {result.status}"
            )

            # Final save to session
            if persist and session:
                self._save_to_session(session, workflow, context, result)
                from utils.session.models import SessionStatus
                self.session_manager.complete_session(
                    session_id,
                    SessionStatus.COMPLETED if result.status == WorkflowStatus.COMPLETED else SessionStatus.FAILED
                )

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}", exc_info=True)
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            # Include step results and outputs even on failure
            result.step_results = context.step_results
            result.outputs = context.outputs

            # Save error state to session
            if persist and session:
                self._save_to_session(session, workflow, context, result)
                from utils.session.models import SessionStatus
                self.session_manager.complete_session(session_id, SessionStatus.FAILED)

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
        self, workflow: WorkflowDefinition, context: WorkflowContext, session: Optional[Session] = None
    ):
        """
        Execute workflow steps in dependency order.

        Args:
            workflow: Workflow definition
            context: Execution context
            session: Optional session for persistence
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

                    # Save intermediate state to session
                    if session:
                        self._save_step_to_session(session, step.step_id, step_result)

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
        elif step_def.type == "loop":
            return LoopStep(step_def)
        else:
            raise ValueError(
                f"Step type '{step_def.type}' not yet implemented. "
                f"Currently supported types: 'agent', 'transform', 'loop'"
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

    def _save_to_session(
        self,
        session: Session,
        workflow: WorkflowDefinition,
        context: WorkflowContext,
        result: WorkflowExecutionResult,
    ):
        """
        Save workflow state to session.

        Args:
            session: Session to save to
            workflow: Workflow definition
            context: Execution context
            result: Execution result
        """
        # Store workflow definition as YAML
        session.set("workflow_name", workflow.name)
        session.set("workflow_version", workflow.version)

        # Store execution state
        session.set("execution_id", result.execution_id)
        session.set("workflow_status", result.status.value)
        session.set("started_at", result.started_at.isoformat() if result.started_at else None)
        session.set("completed_at", result.completed_at.isoformat() if result.completed_at else None)

        # Store context
        session.set("context", context.to_dict())

        # Store outputs and error
        session.set("outputs", result.outputs)
        if result.error:
            session.set("error", result.error)

        # Save session
        self.session_manager.storage.save_session(session)

    def _save_step_to_session(
        self,
        session: Session,
        step_id: str,
        step_result: StepResult,
    ):
        """
        Save individual step result to session.

        Args:
            session: Session to save to
            step_id: Step identifier
            step_result: Step execution result
        """
        # Get existing step results
        step_results = session.get("step_results", {})

        # Add new step result
        step_results[step_id] = step_result.to_dict()

        # Save back to session
        session.set("step_results", step_results)
        session.set("last_completed_step", step_id)

        # Save session
        self.session_manager.storage.save_session(session)

    def load_from_session(self, session_id: str) -> Optional[tuple[WorkflowContext, Dict[str, Any]]]:
        """
        Load workflow state from session.

        Args:
            session_id: Session identifier

        Returns:
            Tuple of (WorkflowContext, workflow_metadata) if found, None otherwise
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            return None

        # Load context
        context_dict = session.get("context")
        if not context_dict:
            return None

        context = WorkflowContext.from_dict(context_dict)

        # Load workflow metadata
        metadata = {
            "workflow_name": session.get("workflow_name"),
            "workflow_version": session.get("workflow_version"),
            "execution_id": session.get("execution_id"),
            "workflow_status": session.get("workflow_status"),
            "started_at": session.get("started_at"),
            "completed_at": session.get("completed_at"),
            "outputs": session.get("outputs", {}),
            "error": session.get("error"),
            "last_completed_step": session.get("last_completed_step"),
        }

        return context, metadata

    async def resume_from_session(
        self,
        session_id: str,
        workflow: WorkflowDefinition,
    ) -> WorkflowExecutionResult:
        """
        Resume workflow execution from a saved session.

        Args:
            session_id: Session identifier to resume from
            workflow: Workflow definition (must match the saved workflow)

        Returns:
            WorkflowExecutionResult with execution outcome

        Raises:
            ValueError: If session not found or workflow doesn't match
        """
        loaded = self.load_from_session(session_id)
        if not loaded:
            raise ValueError(f"Session {session_id} not found or has no workflow state")

        context, metadata = loaded

        # Validate workflow matches
        if metadata["workflow_name"] != workflow.name:
            raise ValueError(
                f"Workflow mismatch: session has '{metadata['workflow_name']}', "
                f"but trying to resume with '{workflow.name}'"
            )

        self.logger.info(
            f"Resuming workflow '{workflow.name}' from session {session_id} "
            f"(last step: {metadata['last_completed_step']})"
        )

        # Resume execution with existing context
        return await self.execute(
            workflow=workflow,
            inputs=context.inputs,
            context=context,
            session_id=session_id,
            persist=True,
        )

    def list_workflow_sessions(
        self,
        workflow_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List workflow sessions with optional filtering.

        Args:
            workflow_name: Optional workflow name to filter by
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        # Get all workflow sessions
        sessions = self.session_manager.list_sessions(
            tags=["workflow"] if not workflow_name else ["workflow", workflow_name],
            limit=limit,
        )

        summaries = []
        for session in sessions:
            summary = {
                "session_id": session.metadata.session_id,
                "workflow_name": session.get("workflow_name"),
                "status": session.metadata.status.value,
                "created_at": session.metadata.created_at.isoformat(),
                "updated_at": session.metadata.updated_at.isoformat(),
                "execution_id": session.get("execution_id"),
                "last_completed_step": session.get("last_completed_step"),
                "error": session.get("error"),
            }
            summaries.append(summary)

        return summaries
