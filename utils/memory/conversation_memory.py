"""
Conversation memory for storing and retrieving chat history.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import deque

from .types import ConversationEntry, MemoryType


class ConversationMemory:
    """
    Manages conversation history with session support.
    """

    def __init__(self, max_entries: int = 1000):
        """
        Initialize conversation memory.

        Args:
            max_entries: Maximum number of entries to keep in memory
        """
        self.max_entries = max_entries
        self.entries: deque[ConversationEntry] = deque(maxlen=max_entries)

    def add_message(self,
                   role: str,
                   content: str,
                   session_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a message to conversation memory.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
            session_id: Optional session identifier
            metadata: Additional metadata

        Returns:
            The entry ID
        """
        entry_id = str(uuid.uuid4())
        entry = ConversationEntry(
            id=entry_id,
            content=content,
            timestamp=datetime.now(),
            memory_type=MemoryType.CONVERSATION,
            metadata=metadata,
            role=role,
            session_id=session_id
        )

        self.entries.append(entry)
        return entry_id

    def get_history(self,
                   session_id: Optional[str] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history.

        Args:
            session_id: Filter by session ID (None for all sessions)
            limit: Maximum number of entries to return

        Returns:
            List of conversation entries as dictionaries
        """
        filtered_entries = []

        # Filter by session if specified
        for entry in reversed(self.entries):
            if session_id is None or entry.session_id == session_id:
                filtered_entries.append(entry.to_dict())

                if limit and len(filtered_entries) >= limit:
                    break

        # Return in chronological order
        return list(reversed(filtered_entries))

    def get_recent_context(self,
                          session_id: Optional[str] = None,
                          max_tokens: int = 4000) -> List[Dict[str, Any]]:
        """
        Get recent conversation context within token limit.

        Args:
            session_id: Filter by session ID
            max_tokens: Approximate maximum tokens (rough estimate: 4 chars = 1 token)

        Returns:
            List of recent conversation entries
        """
        entries = []
        total_chars = 0

        for entry in reversed(self.entries):
            if session_id is None or entry.session_id == session_id:
                entry_chars = len(entry.content)

                # Rough token estimation: 4 characters ≈ 1 token
                if total_chars + entry_chars > max_tokens * 4:
                    break

                entries.append(entry.to_dict())
                total_chars += entry_chars

        return list(reversed(entries))

    def clear(self, session_id: Optional[str] = None):
        """
        Clear conversation history.

        Args:
            session_id: Clear specific session (None clears all)
        """
        if session_id is None:
            self.entries.clear()
        else:
            # Remove entries for specific session
            self.entries = deque(
                (entry for entry in self.entries if entry.session_id != session_id),
                maxlen=self.max_entries
            )

    def get_sessions(self) -> List[str]:
        """Get list of unique session IDs."""
        sessions = set()
        for entry in self.entries:
            if entry.session_id:
                sessions.add(entry.session_id)
        return list(sessions)

    def cleanup_old_entries(self, cutoff_date: datetime):
        """Remove entries older than cutoff date."""
        self.entries = deque(
            (entry for entry in self.entries if entry.timestamp > cutoff_date),
            maxlen=self.max_entries
        )

    def load_from_data(self, data: List[Dict[str, Any]]):
        """Load conversation data from serialized format."""
        self.entries.clear()
        for item in data:
            try:
                entry = ConversationEntry.from_dict(item)
                self.entries.append(entry)
            except Exception as e:
                # Skip invalid entries
                continue
