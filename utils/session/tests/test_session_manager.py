"""Tests for SessionManager"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from utils.session.models import SessionStatus
from utils.session.storage import MemorySessionStorage
from utils.session.session_manager import SessionManager


class TestSessionManager:
    """Tests for SessionManager"""

    @pytest.fixture
    def manager(self):
        """Create a SessionManager with memory storage"""
        storage = MemorySessionStorage()
        return SessionManager(storage)

    def test_create_session(self, manager):
        """Test creating a new session"""
        session = manager.create_session(
            purpose="Test session", user_id="user123", tags=["test"]
        )

        assert session.metadata.session_id.startswith("session_")
        assert session.metadata.purpose == "Test session"
        assert session.metadata.user_id == "user123"
        assert session.metadata.tags == ["test"]
        assert session.metadata.status == SessionStatus.ACTIVE

    def test_create_session_with_custom_id(self, manager):
        """Test creating session with custom ID"""
        session = manager.create_session(session_id="custom_session")

        assert session.metadata.session_id == "custom_session"
        assert session.metadata.status == SessionStatus.ACTIVE

    def test_create_duplicate_session(self, manager):
        """Test that creating duplicate session raises error"""
        manager.create_session(session_id="test_session")

        with pytest.raises(ValueError, match="already exists"):
            manager.create_session(session_id="test_session")

    def test_get_session(self, manager):
        """Test retrieving a session"""
        created_session = manager.create_session(session_id="test_session")
        retrieved_session = manager.get_session("test_session")

        assert retrieved_session is not None
        assert retrieved_session.metadata.session_id == created_session.metadata.session_id

    def test_get_nonexistent_session(self, manager):
        """Test retrieving a session that doesn't exist"""
        session = manager.get_session("nonexistent")
        assert session is None

    def test_link_invocation(self, manager):
        """Test linking invocation to session"""
        session = manager.create_session(session_id="test_session")
        invocation_dir = Path("/tmp/invocation_dir")

        manager.link_invocation(
            session_id="test_session",
            invocation_id="inv1",
            tool_name="git_tool",
            invocation_dir=invocation_dir,
            duration_ms=100.0,
        )

        updated_session = manager.get_session("test_session")
        assert "inv1" in updated_session.invocation_ids
        assert "git_tool" in updated_session.metadata.tools_used
        assert updated_session.metadata.total_invocations == 1
        assert updated_session.metadata.total_duration_ms == 100.0

    def test_link_invocation_to_nonexistent_session(self, manager):
        """Test linking invocation to non-existent session raises error"""
        invocation_dir = Path("/tmp/invocation_dir")

        with pytest.raises(ValueError, match="not found"):
            manager.link_invocation(
                session_id="nonexistent",
                invocation_id="inv1",
                tool_name="tool",
                invocation_dir=invocation_dir,
            )

    def test_add_conversation_message(self, manager):
        """Test adding conversation message"""
        session = manager.create_session(session_id="test_session")

        manager.add_conversation_message(
            session_id="test_session", role="user", content="Hello"
        )

        updated_session = manager.get_session("test_session")
        assert len(updated_session.conversation) == 1
        assert updated_session.conversation[0].role == "user"
        assert updated_session.conversation[0].content == "Hello"

    def test_add_conversation_message_with_tool_info(self, manager):
        """Test adding conversation message with tool info"""
        session = manager.create_session(session_id="test_session")

        manager.add_conversation_message(
            session_id="test_session",
            role="tool",
            content="Result",
            tool_name="git_tool",
            invocation_id="inv1",
        )

        updated_session = manager.get_session("test_session")
        assert len(updated_session.conversation) == 1
        message = updated_session.conversation[0]
        assert message.role == "tool"
        assert message.tool_name == "git_tool"
        assert message.invocation_id == "inv1"

    def test_add_conversation_message_to_nonexistent_session(self, manager):
        """Test adding message to non-existent session raises error"""
        with pytest.raises(ValueError, match="not found"):
            manager.add_conversation_message(
                session_id="nonexistent", role="user", content="Hello"
            )

    def test_update_session_metadata(self, manager):
        """Test updating session metadata"""
        session = manager.create_session(session_id="test_session")

        manager.update_session_metadata(
            session_id="test_session",
            purpose="Updated purpose",
            tags=["new", "tags"],
            custom_metadata={"key": "value"},
        )

        updated_session = manager.get_session("test_session")
        assert updated_session.metadata.purpose == "Updated purpose"
        assert updated_session.metadata.tags == ["new", "tags"]
        assert updated_session.metadata.custom_metadata["key"] == "value"

    def test_complete_session(self, manager):
        """Test completing a session"""
        session = manager.create_session(session_id="test_session")
        manager.complete_session("test_session", SessionStatus.COMPLETED)

        updated_session = manager.get_session("test_session")
        assert updated_session.metadata.status == SessionStatus.COMPLETED

    def test_complete_session_removes_from_active_cache(self, manager):
        """Test that completing session removes it from active cache"""
        manager.create_session(session_id="test_session")
        assert "test_session" in manager._active_sessions

        manager.complete_session("test_session")
        assert "test_session" not in manager._active_sessions

    def test_list_sessions(self, manager):
        """Test listing sessions"""
        manager.create_session(session_id="session1", user_id="user1")
        manager.create_session(session_id="session2", user_id="user1")
        manager.create_session(session_id="session3", user_id="user2")

        sessions = manager.list_sessions()
        assert len(sessions) == 3

        sessions_user1 = manager.list_sessions(user_id="user1")
        assert len(sessions_user1) == 2

    def test_list_sessions_with_status_filter(self, manager):
        """Test listing sessions with status filter"""
        manager.create_session(session_id="session1")
        manager.create_session(session_id="session2")
        manager.complete_session("session1", SessionStatus.COMPLETED)

        active_sessions = manager.list_sessions(status=SessionStatus.ACTIVE)
        assert len(active_sessions) == 1
        assert active_sessions[0].metadata.session_id == "session2"

        completed_sessions = manager.list_sessions(status=SessionStatus.COMPLETED)
        assert len(completed_sessions) == 1
        assert completed_sessions[0].metadata.session_id == "session1"

    def test_list_sessions_with_tags_filter(self, manager):
        """Test listing sessions with tags filter"""
        manager.create_session(session_id="session1", tags=["tag1", "tag2"])
        manager.create_session(session_id="session2", tags=["tag2", "tag3"])
        manager.create_session(session_id="session3", tags=["tag3"])

        sessions = manager.list_sessions(tags=["tag2"])
        assert len(sessions) == 2

        sessions = manager.list_sessions(tags=["tag1"])
        assert len(sessions) == 1

    def test_delete_session(self, manager):
        """Test deleting a session"""
        manager.create_session(session_id="test_session")
        assert manager.storage.session_exists("test_session")

        manager.delete_session("test_session")
        assert not manager.storage.session_exists("test_session")

    def test_cleanup_old_sessions(self, manager):
        """Test cleaning up old sessions"""
        # Create an old session manually
        storage = manager.storage
        now = datetime.now()
        old_date = now - timedelta(days=60)

        from utils.session.models import Session, SessionMetadata

        old_metadata = SessionMetadata(
            session_id="old_session",
            created_at=old_date,
            updated_at=old_date,
            status=SessionStatus.COMPLETED,
        )
        old_session = Session(metadata=old_metadata)
        storage.save_session(old_session)

        # Create a new session
        manager.create_session(session_id="new_session")

        # Cleanup old sessions
        manager.cleanup_old_sessions(max_age_days=30)

        assert not storage.session_exists("old_session")
        assert storage.session_exists("new_session")

    def test_get_session_statistics(self, manager):
        """Test getting session statistics"""
        session = manager.create_session(session_id="test_session")
        invocation_dir = Path("/tmp/invocation_dir")

        manager.link_invocation(
            session_id="test_session",
            invocation_id="inv1",
            tool_name="git_tool",
            invocation_dir=invocation_dir,
            duration_ms=100.0,
        )
        manager.add_conversation_message(
            session_id="test_session", role="user", content="Hello"
        )

        stats = manager.get_session_statistics("test_session")

        assert stats is not None
        assert stats["session_id"] == "test_session"
        assert stats["total_invocations"] == 1
        assert stats["total_duration_ms"] == 100.0
        assert stats["tools_used"] == ["git_tool"]
        assert stats["message_count"] == 1

    def test_get_statistics_for_nonexistent_session(self, manager):
        """Test getting statistics for non-existent session"""
        stats = manager.get_session_statistics("nonexistent")
        assert stats is None

    def test_generate_session_id(self):
        """Test session ID generation"""
        session_id = SessionManager._generate_session_id()

        assert session_id.startswith("session_")
        assert len(session_id) > len("session_")
        assert "_" in session_id

    def test_multiple_invocations_same_session(self, manager):
        """Test linking multiple invocations to the same session"""
        manager.create_session(session_id="test_session")
        invocation_dir = Path("/tmp/invocation_dir")

        manager.link_invocation(
            session_id="test_session",
            invocation_id="inv1",
            tool_name="git_tool",
            invocation_dir=invocation_dir,
            duration_ms=100.0,
        )
        manager.link_invocation(
            session_id="test_session",
            invocation_id="inv2",
            tool_name="text_summarizer",
            invocation_dir=invocation_dir,
            duration_ms=200.0,
        )

        session = manager.get_session("test_session")
        assert session.metadata.total_invocations == 2
        assert session.metadata.total_duration_ms == 300.0
        assert set(session.metadata.tools_used) == {"git_tool", "text_summarizer"}
        assert len(session.invocation_ids) == 2

    def test_conversation_flow(self, manager):
        """Test a complete conversation flow"""
        manager.create_session(session_id="test_session")

        # User message
        manager.add_conversation_message(
            session_id="test_session", role="user", content="What files changed?"
        )

        # Tool invocation
        invocation_dir = Path("/tmp/invocation_dir")
        manager.link_invocation(
            session_id="test_session",
            invocation_id="inv1",
            tool_name="git_tool",
            invocation_dir=invocation_dir,
        )
        manager.add_conversation_message(
            session_id="test_session",
            role="tool",
            content="3 files changed",
            tool_name="git_tool",
            invocation_id="inv1",
        )

        # Assistant message
        manager.add_conversation_message(
            session_id="test_session",
            role="assistant",
            content="I found 3 files that changed.",
        )

        session = manager.get_session("test_session")
        assert len(session.conversation) == 3
        assert session.conversation[0].role == "user"
        assert session.conversation[1].role == "tool"
        assert session.conversation[2].role == "assistant"
