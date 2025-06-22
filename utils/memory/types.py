"""
Type definitions for the memory module.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MemoryType(Enum):
    """Types of memory entries."""
    CONVERSATION = "conversation"
    CONTEXT = "context"
    SYSTEM = "system"


@dataclass
class MemoryEntry:
    """Base memory entry structure."""
    id: str
    content: str
    timestamp: datetime
    memory_type: MemoryType
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "memory_type": self.memory_type.value,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary representation."""
        return cls(
            id=data["id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            memory_type=MemoryType(data["memory_type"]),
            metadata=data.get("metadata")
        )


@dataclass
class ConversationEntry(MemoryEntry):
    """Conversation-specific memory entry."""
    role: str = ""  # user, assistant, system
    session_id: Optional[str] = None

    def __post_init__(self):
        self.memory_type = MemoryType.CONVERSATION

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "role": self.role,
            "session_id": self.session_id
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationEntry":
        return cls(
            id=data["id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            memory_type=MemoryType(data["memory_type"]),
            metadata=data.get("metadata"),
            role=data["role"],
            session_id=data.get("session_id")
        )


@dataclass
class ContextEntry(MemoryEntry):
    """Context-specific memory entry for storing factual information."""
    topic: str = ""
    importance: float = 1.0  # 0.0 to 1.0 importance score

    def __post_init__(self):
        self.memory_type = MemoryType.CONTEXT

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "topic": self.topic,
            "importance": self.importance
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        return cls(
            id=data["id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            memory_type=MemoryType(data["memory_type"]),
            metadata=data.get("metadata"),
            topic=data["topic"],
            importance=data.get("importance", 1.0)
        )
