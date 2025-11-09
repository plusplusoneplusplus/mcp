"""
Storage abstraction for session persistence.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import json
import os

from .models import Session, SessionMetadata, SessionStatus


class SessionStorage(ABC):
    """Abstract storage interface for sessions"""

    @abstractmethod
    def save_session(self, session: Session):
        """Persist session to storage"""
        pass

    @abstractmethod
    def load_session(self, session_id: str) -> Optional[Session]:
        """Load session from storage"""
        pass

    @abstractmethod
    def link_invocation(self, session_id: str, invocation_id: str, invocation_dir: Path):
        """Create link between session and invocation"""
        pass

    @abstractmethod
    def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Session]:
        """Query sessions with filters"""
        pass

    @abstractmethod
    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        pass

    @abstractmethod
    def delete_session(self, session_id: str):
        """Delete a session"""
        pass

    @abstractmethod
    def cleanup_sessions(self, cutoff_date: datetime):
        """Remove sessions older than cutoff"""
        pass


class FileSystemSessionStorage(SessionStorage):
    """Filesystem-based session storage with symlinks to invocations"""

    def __init__(self, sessions_dir: Path, history_dir: Path):
        self.sessions_dir = Path(sessions_dir)
        self.history_dir = Path(history_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: Session):
        """Save session to filesystem"""
        session_path = self.sessions_dir / session.metadata.session_id
        session_path.mkdir(exist_ok=True)

        # Save metadata
        metadata_path = session_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(session.metadata.to_dict(), f, indent=2)

        # Save conversation
        if session.conversation:
            conversation_path = session_path / "conversation.jsonl"
            with open(conversation_path, "w") as f:
                for msg in session.conversation:
                    f.write(json.dumps(msg.to_dict()) + "\n")

        # Save invocation IDs list
        invocations_list_path = session_path / "invocations.json"
        with open(invocations_list_path, "w") as f:
            json.dump(session.invocation_ids, f, indent=2)

        # NEW: Save data field
        if session.data:
            data_path = session_path / "data.json"
            with open(data_path, "w") as f:
                json.dump(session.data, f, indent=2)

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load session from filesystem"""
        session_path = self.sessions_dir / session_id
        if not session_path.exists():
            return None

        # Load metadata
        metadata_path = session_path / "metadata.json"
        if not metadata_path.exists():
            return None

        with open(metadata_path, "r") as f:
            metadata_dict = json.load(f)
        metadata = SessionMetadata.from_dict(metadata_dict)

        # Load invocation IDs
        invocations_list_path = session_path / "invocations.json"
        invocation_ids = []
        if invocations_list_path.exists():
            with open(invocations_list_path, "r") as f:
                invocation_ids = json.load(f)

        # Load conversation
        conversation = []
        conversation_path = session_path / "conversation.jsonl"
        if conversation_path.exists():
            with open(conversation_path, "r") as f:
                for line in f:
                    if line.strip():
                        from .models import ConversationMessage

                        msg_dict = json.loads(line)
                        conversation.append(ConversationMessage.from_dict(msg_dict))

        # NEW: Load data field
        data = {}
        data_path = session_path / "data.json"
        if data_path.exists():
            with open(data_path, "r") as f:
                data = json.load(f)

        return Session(
            metadata=metadata,
            invocation_ids=invocation_ids,
            conversation=conversation,
            data=data,
        )

    def link_invocation(
        self, session_id: str, invocation_id: str, invocation_dir: Path
    ):
        """Create symlink from session to invocation directory"""
        session_path = self.sessions_dir / session_id / "invocations"
        session_path.mkdir(parents=True, exist_ok=True)

        # Create symlink to invocation directory
        symlink_path = session_path / invocation_dir.name

        # Only create symlink if it doesn't exist
        if not symlink_path.exists():
            try:
                # Use relative path for better portability
                relative_invocation_dir = os.path.relpath(
                    invocation_dir, session_path
                )
                symlink_path.symlink_to(relative_invocation_dir)
            except (OSError, FileNotFoundError) as e:
                # If symlink creation fails, just skip it
                # This can happen on systems without symlink support
                print(f"Warning: Could not create symlink for invocation: {e}")

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Session]:
        """Query sessions with filters"""
        sessions = []

        # Iterate through all session directories
        if not self.sessions_dir.exists():
            return []

        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            try:
                session = self.load_session(session_dir.name)
                if session is None:
                    continue

                # Apply filters
                if user_id and session.metadata.user_id != user_id:
                    continue
                if status and session.metadata.status != status:
                    continue
                if tags:
                    # Check if any of the requested tags are in the session tags
                    if not any(tag in session.metadata.tags for tag in tags):
                        continue

                sessions.append(session)

                # Check limit
                if len(sessions) >= limit:
                    break

            except Exception as e:
                # Skip sessions that can't be loaded
                print(f"Warning: Could not load session {session_dir.name}: {e}")
                continue

        # Sort by updated_at descending (most recent first)
        sessions.sort(key=lambda s: s.metadata.updated_at, reverse=True)

        return sessions[:limit]

    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        session_path = self.sessions_dir / session_id
        metadata_path = session_path / "metadata.json"
        return metadata_path.exists()

    def delete_session(self, session_id: str):
        """Delete a session directory"""
        session_path = self.sessions_dir / session_id
        if session_path.exists():
            import shutil

            shutil.rmtree(session_path)

    def cleanup_sessions(self, cutoff_date: datetime):
        """Remove sessions older than cutoff date"""
        if not self.sessions_dir.exists():
            return

        for session_dir in self.sessions_dir.iterdir():
            if not session_dir.is_dir():
                continue

            try:
                session = self.load_session(session_dir.name)
                if session and session.metadata.updated_at < cutoff_date:
                    self.delete_session(session_dir.name)
            except Exception as e:
                # Skip sessions that can't be processed
                print(f"Warning: Could not cleanup session {session_dir.name}: {e}")


class MemorySessionStorage(SessionStorage):
    """In-memory session storage for testing"""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def save_session(self, session: Session):
        """Save session to memory"""
        # Store a deep copy to avoid mutation issues
        import copy

        self._sessions[session.metadata.session_id] = copy.deepcopy(session)

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load session from memory"""
        import copy

        session = self._sessions.get(session_id)
        return copy.deepcopy(session) if session else None

    def link_invocation(
        self, session_id: str, invocation_id: str, invocation_dir: Path
    ):
        """No-op for memory storage (no filesystem operations)"""
        pass

    def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Session]:
        """Query sessions with filters"""
        import copy

        sessions = []

        for session in self._sessions.values():
            # Apply filters
            if user_id and session.metadata.user_id != user_id:
                continue
            if status and session.metadata.status != status:
                continue
            if tags:
                if not any(tag in session.metadata.tags for tag in tags):
                    continue

            sessions.append(copy.deepcopy(session))

            if len(sessions) >= limit:
                break

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.metadata.updated_at, reverse=True)

        return sessions[:limit]

    def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        return session_id in self._sessions

    def delete_session(self, session_id: str):
        """Delete a session"""
        self._sessions.pop(session_id, None)

    def cleanup_sessions(self, cutoff_date: datetime):
        """Remove sessions older than cutoff date"""
        sessions_to_delete = [
            session_id
            for session_id, session in self._sessions.items()
            if session.metadata.updated_at < cutoff_date
        ]
        for session_id in sessions_to_delete:
            del self._sessions[session_id]
