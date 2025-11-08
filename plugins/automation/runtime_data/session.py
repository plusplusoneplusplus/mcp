"""
Session Storage Module

Manages session-level storage and persistence for automation workflows.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class SessionData:
    """Session storage for workflow execution context."""

    session_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from session data.

        Args:
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Value from session data or default
        """
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set value in session data.

        Args:
            key: Key to set
            value: Value to store
        """
        self.data[key] = value
        self.updated_at = datetime.utcnow()

    def delete(self, key: str) -> None:
        """
        Delete value from session data.

        Args:
            key: Key to delete
        """
        if key in self.data:
            del self.data[key]
            self.updated_at = datetime.utcnow()

    def clear(self) -> None:
        """Clear all session data."""
        self.data.clear()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
        )


class SessionStorage:
    """In-memory session storage manager."""

    def __init__(self):
        """Initialize session storage."""
        self._sessions: Dict[str, SessionData] = {}

    def create_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> SessionData:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier
            metadata: Optional metadata for the session

        Returns:
            Created SessionData instance
        """
        session = SessionData(
            session_id=session_id,
            metadata=metadata or {}
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            SessionData if found, None otherwise
        """
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session by ID.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[str]:
        """
        List all session IDs.

        Returns:
            List of session IDs
        """
        return list(self._sessions.keys())

    def clear_all(self) -> None:
        """Clear all sessions."""
        self._sessions.clear()


# Global session storage instance
_global_storage = SessionStorage()


def get_storage() -> SessionStorage:
    """Get global session storage instance."""
    return _global_storage
