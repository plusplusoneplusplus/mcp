"""
Data models for the async jobs framework.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Dict


class JobState(Enum):
    """Possible states for a job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """Result of a completed job."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobProgress:
    """Progress information for a running job."""
    current: int
    total: int
    message: Optional[str] = None

    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        return (self.current / self.total) * 100 if self.total > 0 else 0.0
