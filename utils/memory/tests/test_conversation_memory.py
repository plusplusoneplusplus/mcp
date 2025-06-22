import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

from ..conversation_memory import ConversationMemory
from ..types import ConversationEntry


class TestConversationMemory:
    """Test cases for ConversationMemory class."""

    def test_init(self):
        """Test initialization of ConversationMemory."""
        memory = ConversationMemory(max_entries=100)
        assert memory.max_entries == 100
        assert len(memory.entries) == 0

    def test_add_message(self):
        """Test adding messages to conversation memory."""
        memory = ConversationMemory()

        entry_id = memory.add_message(
            role="user",
            content="Hello, world!",
            session_id="session1"
        )

        assert entry_id is not None
        assert len(memory.entries) == 1

        entry = memory.entries[0]
        assert entry.role == "user"
        assert entry.content == "Hello, world!"
        assert entry.session_id == "session1"
        assert entry.id == entry_id

    def test_add_message_with_metadata(self):
        """Test adding messages with metadata."""
        memory = ConversationMemory()
        metadata = {"source": "test", "priority": "high"}

        entry_id = memory.add_message(
            role="assistant",
            content="Response",
            metadata=metadata
        )

        entry = memory.entries[0]
        assert entry.metadata == metadata

    def test_get_history_all(self):
        """Test retrieving all conversation history."""
        memory = ConversationMemory()

        # Add multiple messages
        memory.add_message("user", "Message 1", "session1")
        memory.add_message("assistant", "Response 1", "session1")
        memory.add_message("user", "Message 2", "session2")

        history = memory.get_history()
        assert len(history) == 3

        # Check chronological order
        assert history[0]["content"] == "Message 1"
        assert history[1]["content"] == "Response 1"
        assert history[2]["content"] == "Message 2"

    def test_get_history_by_session(self):
        """Test retrieving history filtered by session."""
        memory = ConversationMemory()

        memory.add_message("user", "Message 1", "session1")
        memory.add_message("assistant", "Response 1", "session1")
        memory.add_message("user", "Message 2", "session2")

        session1_history = memory.get_history(session_id="session1")
        assert len(session1_history) == 2
        assert all(msg["session_id"] == "session1" for msg in session1_history)

        session2_history = memory.get_history(session_id="session2")
        assert len(session2_history) == 1
        assert session2_history[0]["content"] == "Message 2"

    def test_get_history_with_limit(self):
        """Test retrieving history with limit."""
        memory = ConversationMemory()

        # Add 5 messages
        for i in range(5):
            memory.add_message("user", f"Message {i}", "session1")

        # Get limited history
        limited_history = memory.get_history(limit=3)
        assert len(limited_history) == 3

        # Should get the most recent 3 messages
        assert limited_history[0]["content"] == "Message 2"
        assert limited_history[1]["content"] == "Message 3"
        assert limited_history[2]["content"] == "Message 4"

    def test_get_recent_context(self):
        """Test retrieving recent context within token limit."""
        memory = ConversationMemory()

        # Add messages with different lengths
        memory.add_message("user", "a" * 800, "session1")  # ~200 tokens
        memory.add_message("assistant", "b" * 1200, "session1")  # ~300 tokens
        memory.add_message("user", "c" * 2000, "session1")  # ~500 tokens
        memory.add_message("assistant", "d" * 3200, "session1")  # ~800 tokens

        # Get context within 1500 token limit (6000 chars)
        context = memory.get_recent_context(session_id="session1", max_tokens=1500)

        # Should include the most recent messages that fit
        assert len(context) >= 1
        total_chars = sum(len(msg["content"]) for msg in context)
        assert total_chars <= 1500 * 4  # 4 chars per token estimate

    def test_clear_all(self):
        """Test clearing all conversation history."""
        memory = ConversationMemory()

        memory.add_message("user", "Message 1", "session1")
        memory.add_message("user", "Message 2", "session2")

        memory.clear()
        assert len(memory.entries) == 0
        assert len(memory.get_history()) == 0

    def test_clear_by_session(self):
        """Test clearing history for specific session."""
        memory = ConversationMemory()

        memory.add_message("user", "Message 1", "session1")
        memory.add_message("user", "Message 2", "session1")
        memory.add_message("user", "Message 3", "session2")

        memory.clear(session_id="session1")

        remaining_history = memory.get_history()
        assert len(remaining_history) == 1
        assert remaining_history[0]["session_id"] == "session2"

    def test_get_sessions(self):
        """Test retrieving unique session IDs."""
        memory = ConversationMemory()

        memory.add_message("user", "Message 1", "session1")
        memory.add_message("user", "Message 2", "session1")
        memory.add_message("user", "Message 3", "session2")
        memory.add_message("user", "Message 4", None)  # No session

        sessions = memory.get_sessions()
        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions
        assert None not in sessions

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries."""
        memory = ConversationMemory()

        # Mock timestamps
        now = datetime.now()
        old_time = now - timedelta(days=5)
        recent_time = now - timedelta(hours=1)

        with patch('utils.memory.conversation_memory.datetime') as mock_datetime:
            # Add old entry
            mock_datetime.now.return_value = old_time
            memory.add_message("user", "Old message", "session1")

            # Add recent entry
            mock_datetime.now.return_value = recent_time
            memory.add_message("user", "Recent message", "session1")

        # Cleanup entries older than 2 days
        cutoff_date = now - timedelta(days=2)
        memory.cleanup_old_entries(cutoff_date)

        remaining_history = memory.get_history()
        assert len(remaining_history) == 1
        assert remaining_history[0]["content"] == "Recent message"

    def test_max_entries_limit(self):
        """Test that max_entries limit is enforced."""
        memory = ConversationMemory(max_entries=3)

        # Add more entries than the limit
        for i in range(5):
            memory.add_message("user", f"Message {i}", "session1")

        # Should only keep the most recent 3 entries
        assert len(memory.entries) == 3

        history = memory.get_history()
        assert len(history) == 3
        assert history[0]["content"] == "Message 2"
        assert history[1]["content"] == "Message 3"
        assert history[2]["content"] == "Message 4"

    def test_load_from_data_valid(self):
        """Test loading valid data from serialized format."""
        memory = ConversationMemory()

        # Create test data
        test_data = [
            {
                "id": "test1",
                "content": "Hello",
                "timestamp": datetime.now().isoformat(),
                "memory_type": "conversation",
                "role": "user",
                "session_id": "session1",
                "metadata": {"test": True}
            },
            {
                "id": "test2",
                "content": "Hi there",
                "timestamp": datetime.now().isoformat(),
                "memory_type": "conversation",
                "role": "assistant",
                "session_id": "session1"
            }
        ]

        memory.load_from_data(test_data)

        assert len(memory.entries) == 2
        assert memory.entries[0].content == "Hello"
        assert memory.entries[0].role == "user"
        assert memory.entries[1].content == "Hi there"
        assert memory.entries[1].role == "assistant"

    def test_load_from_data_invalid(self):
        """Test loading invalid data - should skip bad entries."""
        memory = ConversationMemory()

        # Mix of valid and invalid data
        test_data = [
            {
                "id": "test1",
                "content": "Valid entry",
                "timestamp": datetime.now().isoformat(),
                "memory_type": "conversation",
                "role": "user"
            },
            {
                "invalid": "data",
                "missing": "required_fields"
            },
            {
                "id": "test2",
                "content": "Another valid entry",
                "timestamp": datetime.now().isoformat(),
                "memory_type": "conversation",
                "role": "assistant"
            }
        ]

        memory.load_from_data(test_data)

        # Should only load valid entries
        assert len(memory.entries) == 2
        assert memory.entries[0].content == "Valid entry"
        assert memory.entries[1].content == "Another valid entry"

    def test_entry_serialization(self):
        """Test that entries can be properly serialized and deserialized."""
        memory = ConversationMemory()

        entry_id = memory.add_message(
            role="user",
            content="Test message",
            session_id="test_session",
            metadata={"source": "test"}
        )

        # Get the serialized entry
        history = memory.get_history()
        serialized_entry = history[0]

        # Verify all fields are present
        required_fields = ["id", "content", "timestamp", "memory_type", "role"]
        for field in required_fields:
            assert field in serialized_entry

        assert serialized_entry["id"] == entry_id
        assert serialized_entry["content"] == "Test message"
        assert serialized_entry["role"] == "user"
        assert serialized_entry["session_id"] == "test_session"
        assert serialized_entry["metadata"] == {"source": "test"}
        assert serialized_entry["memory_type"] == "conversation"
