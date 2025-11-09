"""
Session data models for managing conversation sessions across tools.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class SessionStatus(str, Enum):
    """Status of a session"""
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


@dataclass
class SessionMetadata:
    """Metadata for a session"""
    session_id: str
    created_at: datetime
    updated_at: datetime
    status: SessionStatus

    # Context
    user_id: Optional[str] = None
    purpose: Optional[str] = None  # "Debug login issue", "Create PR", etc.
    tags: List[str] = field(default_factory=list)

    # Statistics
    total_invocations: int = 0
    total_duration_ms: float = 0.0
    tools_used: List[str] = field(default_factory=list)

    # Cost tracking (if applicable)
    estimated_cost: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)  # {"input": 1000, "output": 500}

    # Custom metadata
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status.value,
            "user_id": self.user_id,
            "purpose": self.purpose,
            "tags": self.tags,
            "total_invocations": self.total_invocations,
            "total_duration_ms": self.total_duration_ms,
            "tools_used": self.tools_used,
            "estimated_cost": self.estimated_cost,
            "token_usage": self.token_usage,
            "custom_metadata": self.custom_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionMetadata":
        """Create metadata from dictionary"""
        return cls(
            session_id=data["session_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            status=SessionStatus(data["status"]),
            user_id=data.get("user_id"),
            purpose=data.get("purpose"),
            tags=data.get("tags", []),
            total_invocations=data.get("total_invocations", 0),
            total_duration_ms=data.get("total_duration_ms", 0.0),
            tools_used=data.get("tools_used", []),
            estimated_cost=data.get("estimated_cost", 0.0),
            token_usage=data.get("token_usage", {}),
            custom_metadata=data.get("custom_metadata", {}),
        )


@dataclass
class ConversationMessage:
    """A message in the conversation history"""
    role: str  # "user" | "assistant" | "tool"
    content: str
    timestamp: datetime
    tool_name: Optional[str] = None  # For tool messages
    invocation_id: Optional[str] = None  # Link to tool invocation

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_name": self.tool_name,
            "invocation_id": self.invocation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMessage":
        """Create message from dictionary"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tool_name=data.get("tool_name"),
            invocation_id=data.get("invocation_id"),
        )


@dataclass
class Session:
    """A conversation session that can span multiple tool invocations"""
    metadata: SessionMetadata
    invocation_ids: List[str] = field(default_factory=list)
    conversation: List[ConversationMessage] = field(default_factory=list)
    # NEW: Workflow data storage
    data: Dict[str, Any] = field(default_factory=dict)

    def add_invocation(self, invocation_id: str, duration_ms: Optional[float] = None):
        """Link an invocation to this session"""
        if invocation_id not in self.invocation_ids:
            self.invocation_ids.append(invocation_id)
            self.metadata.total_invocations += 1
            if duration_ms is not None:
                self.metadata.total_duration_ms += duration_ms
            self.metadata.updated_at = datetime.now()

    def add_message(
        self,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        invocation_id: Optional[str] = None,
    ):
        """Add a message to the conversation"""
        message = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            tool_name=tool_name,
            invocation_id=invocation_id,
        )
        self.conversation.append(message)
        self.metadata.updated_at = datetime.now()

    # NEW: Data storage methods (from automation/session.py)
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from session data."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set value in session data."""
        self.data[key] = value
        self.metadata.updated_at = datetime.now()

    def delete(self, key: str) -> None:
        """Delete value from session data."""
        if key in self.data:
            del self.data[key]
            self.metadata.updated_at = datetime.now()

    def clear_data(self) -> None:
        """Clear all session data (preserves conversation)."""
        self.data.clear()
        self.metadata.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization"""
        return {
            "metadata": self.metadata.to_dict(),
            "invocation_ids": self.invocation_ids,
            "conversation": [msg.to_dict() for msg in self.conversation],
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary"""
        return cls(
            metadata=SessionMetadata.from_dict(data["metadata"]),
            invocation_ids=data.get("invocation_ids", []),
            conversation=[
                ConversationMessage.from_dict(msg) for msg in data.get("conversation", [])
            ],
            data=data.get("data", {}),
        )
