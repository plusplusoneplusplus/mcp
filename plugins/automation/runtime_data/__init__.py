"""
Runtime Data Module

Manages runtime data for automation workflows:
- State: Structural context (WorkflowContext, StepResult, StepStatus)

Note: Session management has been unified with utils.session.
Use utils.session.SessionManager for session-level storage.
"""

# State management (structural context)
from .state import StepResult, StepStatus, WorkflowContext

__all__ = [
    # State
    "StepResult",
    "StepStatus",
    "WorkflowContext",
]
