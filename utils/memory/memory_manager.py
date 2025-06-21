"""
Main memory manager for coordinating different memory systems.
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from .types import MemoryEntry, MemoryType
from .conversation_memory import ConversationMemory
from .context_memory import ContextMemory


class MemoryManager:
    """
    Central manager for different types of memory systems.
    Coordinates conversation memory, context memory, and persistence.
    """

    def __init__(self,
                 persist_directory: Optional[str] = None,
                 max_conversation_history: int = 1000,
                 max_context_entries: int = 500):
        """
        Initialize the memory manager.

        Args:
            persist_directory: Directory for persistent storage
            max_conversation_history: Maximum conversation entries to keep
            max_context_entries: Maximum context entries to keep
        """
        self.persist_directory = persist_directory
        if persist_directory:
            Path(persist_directory).mkdir(parents=True, exist_ok=True)

        self.conversation_memory = ConversationMemory(
            max_entries=max_conversation_history
        )
        self.context_memory = ContextMemory(
            max_entries=max_context_entries
        )

        self._load_from_disk()

    def add_conversation(self,
                        role: str,
                        content: str,
                        session_id: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a conversation entry."""
        return self.conversation_memory.add_message(
            role=role,
            content=content,
            session_id=session_id,
            metadata=metadata
        )

    def add_context(self,
                   content: str,
                   topic: str,
                   importance: float = 1.0,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a context entry."""
        return self.context_memory.add_context(
            content=content,
            topic=topic,
            importance=importance,
            metadata=metadata
        )

    def get_conversation_history(self,
                               session_id: Optional[str] = None,
                               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.conversation_memory.get_history(
            session_id=session_id,
            limit=limit
        )

    def search_context(self,
                      query: str,
                      topic: Optional[str] = None,
                      limit: int = 5) -> List[Dict[str, Any]]:
        """Search context entries."""
        return self.context_memory.search(
            query=query,
            topic=topic,
            limit=limit
        )

    def clear_conversation(self, session_id: Optional[str] = None):
        """Clear conversation history."""
        self.conversation_memory.clear(session_id=session_id)

    def clear_context(self, topic: Optional[str] = None):
        """Clear context entries."""
        self.context_memory.clear(topic=topic)

    def cleanup_old_entries(self, days_old: int = 30):
        """Remove entries older than specified days."""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        self.conversation_memory.cleanup_old_entries(cutoff_date)
        self.context_memory.cleanup_old_entries(cutoff_date)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        return {
            "conversation_entries": len(self.conversation_memory.entries),
            "context_entries": len(self.context_memory.entries),
            "total_entries": len(self.conversation_memory.entries) + len(self.context_memory.entries),
            "sessions": len(set(
                entry.session_id for entry in self.conversation_memory.entries
                if entry.session_id
            )),
            "topics": len(set(
                entry.topic for entry in self.context_memory.entries
            ))
        }

    def save_to_disk(self):
        """Persist memory to disk."""
        if not self.persist_directory:
            return

        # Save conversation memory
        conv_file = os.path.join(self.persist_directory, "conversations.json")
        conv_data = [entry.to_dict() for entry in self.conversation_memory.entries]
        with open(conv_file, 'w') as f:
            json.dump(conv_data, f, indent=2)

        # Save context memory
        ctx_file = os.path.join(self.persist_directory, "context.json")
        ctx_data = [entry.to_dict() for entry in self.context_memory.entries]
        with open(ctx_file, 'w') as f:
            json.dump(ctx_data, f, indent=2)

    def _load_from_disk(self):
        """Load memory from disk."""
        if not self.persist_directory:
            return

        # Load conversation memory
        conv_file = os.path.join(self.persist_directory, "conversations.json")
        if os.path.exists(conv_file):
            with open(conv_file, 'r') as f:
                conv_data = json.load(f)
                self.conversation_memory.load_from_data(conv_data)

        # Load context memory
        ctx_file = os.path.join(self.persist_directory, "context.json")
        if os.path.exists(ctx_file):
            with open(ctx_file, 'r') as f:
                ctx_data = json.load(f)
                self.context_memory.load_from_data(ctx_data)

    def __del__(self):
        """Auto-save on destruction."""
        try:
            self.save_to_disk()
        except Exception:
            pass
