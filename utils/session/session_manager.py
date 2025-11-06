"""
Session manager for managing conversation sessions across tools.
"""

from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

from .models import Session, SessionMetadata, SessionStatus
from .storage import SessionStorage


class SessionManager:
    """Manages sessions across all tools"""

    def __init__(self, storage: SessionStorage):
        self.storage = storage
        self._active_sessions: Dict[str, Session] = {}

    def create_session(
        self,
        session_id: Optional[str] = None,
        purpose: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            session_id: Optional custom session ID. If not provided, generates one.
            purpose: Description of the session purpose
            user_id: User identifier
            tags: List of tags for categorizing the session

        Returns:
            Created Session object
        """
        if session_id is None:
            session_id = self._generate_session_id()

        # Check if session already exists
        if self.storage.session_exists(session_id):
            raise ValueError(f"Session {session_id} already exists")

        metadata = SessionMetadata(
            session_id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=SessionStatus.ACTIVE,
            purpose=purpose,
            user_id=user_id,
            tags=tags or [],
            tools_used=[],
        )

        session = Session(metadata=metadata, invocation_ids=[], conversation=[])

        self.storage.save_session(session)
        self._active_sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session object if found, None otherwise
        """
        # Check in-memory cache first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]

        # Load from storage
        session = self.storage.load_session(session_id)
        if session:
            self._active_sessions[session_id] = session
        return session

    def link_invocation(
        self,
        session_id: str,
        invocation_id: str,
        tool_name: str,
        invocation_dir: Path,
        duration_ms: Optional[float] = None,
    ):
        """
        Link a tool invocation to a session.

        Args:
            session_id: Session identifier
            invocation_id: Invocation identifier
            tool_name: Name of the tool that was invoked
            invocation_dir: Path to the invocation directory in .history
            duration_ms: Duration of the invocation in milliseconds
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Add invocation to session
        session.add_invocation(invocation_id, duration_ms)

        # Track tool usage
        if tool_name not in session.metadata.tools_used:
            session.metadata.tools_used.append(tool_name)

        # Save session
        self.storage.save_session(session)

        # Create symlink
        self.storage.link_invocation(session_id, invocation_id, invocation_dir)

    def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        invocation_id: Optional[str] = None,
    ):
        """
        Add a message to the session conversation.

        Args:
            session_id: Session identifier
            role: Message role ("user", "assistant", "tool")
            content: Message content
            tool_name: Optional tool name for tool messages
            invocation_id: Optional invocation ID to link the message
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.add_message(
            role=role, content=content, tool_name=tool_name, invocation_id=invocation_id
        )

        self.storage.save_session(session)

    def update_session_metadata(
        self,
        session_id: str,
        purpose: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_metadata: Optional[Dict] = None,
    ):
        """
        Update session metadata.

        Args:
            session_id: Session identifier
            purpose: Updated purpose description
            tags: Updated tags list
            custom_metadata: Custom metadata to merge/update
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if purpose is not None:
            session.metadata.purpose = purpose

        if tags is not None:
            session.metadata.tags = tags

        if custom_metadata is not None:
            session.metadata.custom_metadata.update(custom_metadata)

        session.metadata.updated_at = datetime.now()
        self.storage.save_session(session)

    def complete_session(
        self, session_id: str, status: SessionStatus = SessionStatus.COMPLETED
    ):
        """
        Mark session as completed/failed/abandoned.

        Args:
            session_id: Session identifier
            status: Final status for the session
        """
        session = self.get_session(session_id)
        if session:
            session.metadata.status = status
            session.metadata.updated_at = datetime.now()
            self.storage.save_session(session)
            self._active_sessions.pop(session_id, None)

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Session]:
        """
        List sessions with filtering.

        Args:
            user_id: Filter by user ID
            status: Filter by status
            tags: Filter by tags (sessions matching any of the tags)
            limit: Maximum number of sessions to return

        Returns:
            List of Session objects matching the filters
        """
        return self.storage.list_sessions(
            user_id=user_id, status=status, tags=tags, limit=limit
        )

    def delete_session(self, session_id: str):
        """
        Delete a session permanently.

        Args:
            session_id: Session identifier
        """
        self._active_sessions.pop(session_id, None)
        self.storage.delete_session(session_id)

    def cleanup_old_sessions(self, max_age_days: int = 30):
        """
        Remove sessions older than specified days.

        Args:
            max_age_days: Maximum age of sessions in days
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        self.storage.cleanup_sessions(cutoff)

        # Also cleanup from active sessions cache
        sessions_to_remove = [
            session_id
            for session_id, session in self._active_sessions.items()
            if session.metadata.updated_at < cutoff
        ]
        for session_id in sessions_to_remove:
            del self._active_sessions[session_id]

    def get_session_statistics(self, session_id: str) -> Optional[Dict]:
        """
        Get statistics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session statistics or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return None

        return {
            "session_id": session.metadata.session_id,
            "status": session.metadata.status.value,
            "created_at": session.metadata.created_at.isoformat(),
            "updated_at": session.metadata.updated_at.isoformat(),
            "duration_seconds": (
                session.metadata.updated_at - session.metadata.created_at
            ).total_seconds(),
            "total_invocations": session.metadata.total_invocations,
            "total_duration_ms": session.metadata.total_duration_ms,
            "tools_used": session.metadata.tools_used,
            "message_count": len(session.conversation),
            "estimated_cost": session.metadata.estimated_cost,
            "token_usage": session.metadata.token_usage,
        }

    @staticmethod
    def _generate_session_id() -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}_{uuid4().hex[:8]}"
