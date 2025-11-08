"""
Runtime Data Module

Manages runtime data for automation workflows, including:
- State: Structural context (WorkflowContext, StepResult, StepStatus)
- Session: Session-level storage and persistence
"""

# State management (structural context)
from .state import StepResult, StepStatus, WorkflowContext

# Session storage
from .session import SessionData, SessionStorage, get_storage

__all__ = [
    # State
    "StepResult",
    "StepStatus",
    "WorkflowContext",
    # Session
    "SessionData",
    "SessionStorage",
    "get_storage",
]
