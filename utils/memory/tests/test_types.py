import pytest
from datetime import datetime
from enum import Enum

from ..types import (
    MemoryType,
    MemoryEntry,
    ConversationEntry,
    ContextEntry
)


class TestMemoryType:
    """Test cases for MemoryType enum."""

    def test_memory_type_values(self):
        """Test that MemoryType enum has expected values."""
        assert MemoryType.CONVERSATION.value == "conversation"
        assert MemoryType.CONTEXT.value == "context"
        assert MemoryType.SYSTEM.value == "system"

    def test_memory_type_is_enum(self):
        """Test that MemoryType is an Enum."""
        assert issubclass(MemoryType, Enum)


class TestMemoryEntry:
    """Test cases for MemoryEntry dataclass."""

    def test_memory_entry_creation(self):
        """Test creating a MemoryEntry."""
        timestamp = datetime.now()
        entry = MemoryEntry(
            id="test_id",
            content="Test content",
            timestamp=timestamp,
            memory_type=MemoryType.SYSTEM,
            metadata={"key": "value"}
        )

        assert entry.id == "test_id"
        assert entry.content == "Test content"
        assert entry.timestamp == timestamp
        assert entry.memory_type == MemoryType.SYSTEM
        assert entry.metadata == {"key": "value"}

    def test_memory_entry_optional_metadata(self):
        """Test MemoryEntry with optional metadata."""
        entry = MemoryEntry(
            id="test_id",
            content="Test content",
            timestamp=datetime.now(),
            memory_type=MemoryType.SYSTEM
        )

        assert entry.metadata is None

    def test_memory_entry_to_dict(self):
        """Test converting MemoryEntry to dictionary."""
        timestamp = datetime.now()
        entry = MemoryEntry(
            id="test_id",
            content="Test content",
            timestamp=timestamp,
            memory_type=MemoryType.SYSTEM,
            metadata={"source": "test"}
        )

        result = entry.to_dict()

        expected = {
            "id": "test_id",
            "content": "Test content",
            "timestamp": timestamp.isoformat(),
            "memory_type": "system",
            "metadata": {"source": "test"}
        }

        assert result == expected

    def test_memory_entry_to_dict_no_metadata(self):
        """Test converting MemoryEntry to dict with no metadata."""
        timestamp = datetime.now()
        entry = MemoryEntry(
            id="test_id",
            content="Test content",
            timestamp=timestamp,
            memory_type=MemoryType.SYSTEM
        )

        result = entry.to_dict()

        assert result["metadata"] == {}

    def test_memory_entry_from_dict(self):
        """Test creating MemoryEntry from dictionary."""
        timestamp = datetime.now()
        data = {
            "id": "test_id",
            "content": "Test content",
            "timestamp": timestamp.isoformat(),
            "memory_type": "system",
            "metadata": {"source": "test"}
        }

        entry = MemoryEntry.from_dict(data)

        assert entry.id == "test_id"
        assert entry.content == "Test content"
        assert entry.timestamp == timestamp
        assert entry.memory_type == MemoryType.SYSTEM
        assert entry.metadata == {"source": "test"}

    def test_memory_entry_from_dict_no_metadata(self):
        """Test creating MemoryEntry from dict without metadata."""
        timestamp = datetime.now()
        data = {
            "id": "test_id",
            "content": "Test content",
            "timestamp": timestamp.isoformat(),
            "memory_type": "system"
        }

        entry = MemoryEntry.from_dict(data)

        assert entry.metadata is None


class TestConversationEntry:
    """Test cases for ConversationEntry dataclass."""

    def test_conversation_entry_creation(self):
        """Test creating a ConversationEntry."""
        timestamp = datetime.now()
        entry = ConversationEntry(
            id="conv_id",
            content="Hello world",
            timestamp=timestamp,
            memory_type=MemoryType.CONVERSATION,  # This will be overridden
            role="user",
            session_id="session_123",
            metadata={"source": "chat"}
        )

        assert entry.id == "conv_id"
        assert entry.content == "Hello world"
        assert entry.timestamp == timestamp
        assert entry.memory_type == MemoryType.CONVERSATION  # Auto-set in __post_init__
        assert entry.role == "user"
        assert entry.session_id == "session_123"
        assert entry.metadata == {"source": "chat"}

    def test_conversation_entry_post_init(self):
        """Test that __post_init__ sets memory_type correctly."""
        entry = ConversationEntry(
            id="conv_id",
            content="Hello",
            timestamp=datetime.now(),
            memory_type=MemoryType.SYSTEM,  # This should be overridden
            role="user"
        )

        # Should be automatically set to CONVERSATION
        assert entry.memory_type == MemoryType.CONVERSATION

    def test_conversation_entry_optional_session(self):
        """Test ConversationEntry with optional session_id."""
        entry = ConversationEntry(
            id="conv_id",
            content="Hello",
            timestamp=datetime.now(),
            memory_type=MemoryType.CONVERSATION,
            role="user"
        )

        assert entry.session_id is None

    def test_conversation_entry_to_dict(self):
        """Test converting ConversationEntry to dictionary."""
        timestamp = datetime.now()
        entry = ConversationEntry(
            id="conv_id",
            content="Hello world",
            timestamp=timestamp,
            memory_type=MemoryType.CONVERSATION,
            role="user",
            session_id="session_123",
            metadata={"source": "chat"}
        )

        result = entry.to_dict()

        expected = {
            "id": "conv_id",
            "content": "Hello world",
            "timestamp": timestamp.isoformat(),
            "memory_type": "conversation",
            "metadata": {"source": "chat"},
            "role": "user",
            "session_id": "session_123"
        }

        assert result == expected

    def test_conversation_entry_from_dict(self):
        """Test creating ConversationEntry from dictionary."""
        timestamp = datetime.now()
        data = {
            "id": "conv_id",
            "content": "Hello world",
            "timestamp": timestamp.isoformat(),
            "memory_type": "conversation",
            "metadata": {"source": "chat"},
            "role": "user",
            "session_id": "session_123"
        }

        entry = ConversationEntry.from_dict(data)

        assert entry.id == "conv_id"
        assert entry.content == "Hello world"
        assert entry.timestamp == timestamp
        assert entry.memory_type == MemoryType.CONVERSATION
        assert entry.role == "user"
        assert entry.session_id == "session_123"
        assert entry.metadata == {"source": "chat"}

    def test_conversation_entry_from_dict_no_session(self):
        """Test creating ConversationEntry from dict without session_id."""
        timestamp = datetime.now()
        data = {
            "id": "conv_id",
            "content": "Hello world",
            "timestamp": timestamp.isoformat(),
            "memory_type": "conversation",
            "role": "user"
        }

        entry = ConversationEntry.from_dict(data)

        assert entry.session_id is None


class TestContextEntry:
    """Test cases for ContextEntry dataclass."""

    def test_context_entry_creation(self):
        """Test creating a ContextEntry."""
        timestamp = datetime.now()
        entry = ContextEntry(
            id="ctx_id",
            content="Python is a programming language",
            timestamp=timestamp,
            memory_type=MemoryType.CONTEXT,  # This will be overridden
            topic="programming",
            importance=0.8,
            metadata={"source": "docs"}
        )

        assert entry.id == "ctx_id"
        assert entry.content == "Python is a programming language"
        assert entry.timestamp == timestamp
        assert entry.memory_type == MemoryType.CONTEXT  # Auto-set in __post_init__
        assert entry.topic == "programming"
        assert entry.importance == 0.8
        assert entry.metadata == {"source": "docs"}

    def test_context_entry_post_init(self):
        """Test that __post_init__ sets memory_type correctly."""
        entry = ContextEntry(
            id="ctx_id",
            content="Test content",
            timestamp=datetime.now(),
            memory_type=MemoryType.SYSTEM,  # This should be overridden
            topic="test"
        )

        # Should be automatically set to CONTEXT
        assert entry.memory_type == MemoryType.CONTEXT

    def test_context_entry_default_importance(self):
        """Test ContextEntry with default importance."""
        entry = ContextEntry(
            id="ctx_id",
            content="Test content",
            timestamp=datetime.now(),
            memory_type=MemoryType.CONTEXT,
            topic="test"
        )

        assert entry.importance == 1.0

    def test_context_entry_to_dict(self):
        """Test converting ContextEntry to dictionary."""
        timestamp = datetime.now()
        entry = ContextEntry(
            id="ctx_id",
            content="Python info",
            timestamp=timestamp,
            memory_type=MemoryType.CONTEXT,
            topic="programming",
            importance=0.8,
            metadata={"source": "docs"}
        )

        result = entry.to_dict()

        expected = {
            "id": "ctx_id",
            "content": "Python info",
            "timestamp": timestamp.isoformat(),
            "memory_type": "context",
            "metadata": {"source": "docs"},
            "topic": "programming",
            "importance": 0.8
        }

        assert result == expected

    def test_context_entry_from_dict(self):
        """Test creating ContextEntry from dictionary."""
        timestamp = datetime.now()
        data = {
            "id": "ctx_id",
            "content": "Python info",
            "timestamp": timestamp.isoformat(),
            "memory_type": "context",
            "metadata": {"source": "docs"},
            "topic": "programming",
            "importance": 0.8
        }

        entry = ContextEntry.from_dict(data)

        assert entry.id == "ctx_id"
        assert entry.content == "Python info"
        assert entry.timestamp == timestamp
        assert entry.memory_type == MemoryType.CONTEXT
        assert entry.topic == "programming"
        assert entry.importance == 0.8
        assert entry.metadata == {"source": "docs"}

    def test_context_entry_from_dict_default_importance(self):
        """Test creating ContextEntry from dict with default importance."""
        timestamp = datetime.now()
        data = {
            "id": "ctx_id",
            "content": "Test content",
            "timestamp": timestamp.isoformat(),
            "memory_type": "context",
            "topic": "test"
        }

        entry = ContextEntry.from_dict(data)

        assert entry.importance == 1.0

    def test_context_entry_inheritance(self):
        """Test that ContextEntry inherits from MemoryEntry correctly."""
        entry = ContextEntry(
            id="ctx_id",
            content="Test content",
            timestamp=datetime.now(),
            memory_type=MemoryType.CONTEXT,
            topic="test"
        )

        assert isinstance(entry, MemoryEntry)

        # Test that parent methods work
        entry_dict = entry.to_dict()
        assert "id" in entry_dict
        assert "content" in entry_dict
        assert "timestamp" in entry_dict
        assert "memory_type" in entry_dict

    def test_conversation_entry_inheritance(self):
        """Test that ConversationEntry inherits from MemoryEntry correctly."""
        entry = ConversationEntry(
            id="conv_id",
            content="Test message",
            timestamp=datetime.now(),
            memory_type=MemoryType.CONVERSATION,
            role="user"
        )

        assert isinstance(entry, MemoryEntry)

        # Test that parent methods work
        entry_dict = entry.to_dict()
        assert "id" in entry_dict
        assert "content" in entry_dict
        assert "timestamp" in entry_dict
        assert "memory_type" in entry_dict
