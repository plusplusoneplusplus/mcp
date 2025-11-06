"""Tests for session models"""

import pytest
from datetime import datetime
from utils.session.models import (
    Session,
    SessionMetadata,
    SessionStatus,
    ConversationMessage,
)


class TestSessionMetadata:
    """Tests for SessionMetadata"""

    def test_create_session_metadata(self):
        """Test creating session metadata"""
        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
            user_id="user123",
            purpose="Test session",
            tags=["test", "demo"],
        )

        assert metadata.session_id == "test_session"
        assert metadata.status == SessionStatus.ACTIVE
        assert metadata.user_id == "user123"
        assert metadata.purpose == "Test session"
        assert metadata.tags == ["test", "demo"]
        assert metadata.total_invocations == 0
        assert metadata.total_duration_ms == 0.0

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary"""
        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
            purpose="Test",
            tags=["test"],
        )

        data = metadata.to_dict()
        assert data["session_id"] == "test_session"
        assert data["status"] == "active"
        assert data["purpose"] == "Test"
        assert data["tags"] == ["test"]
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_metadata_from_dict(self):
        """Test creating metadata from dictionary"""
        now = datetime.now()
        data = {
            "session_id": "test_session",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "status": "active",
            "user_id": "user123",
            "purpose": "Test",
            "tags": ["test"],
            "total_invocations": 5,
            "total_duration_ms": 1000.0,
            "tools_used": ["tool1", "tool2"],
            "estimated_cost": 0.5,
            "token_usage": {"input": 100, "output": 50},
            "custom_metadata": {"key": "value"},
        }

        metadata = SessionMetadata.from_dict(data)
        assert metadata.session_id == "test_session"
        assert metadata.status == SessionStatus.ACTIVE
        assert metadata.user_id == "user123"
        assert metadata.total_invocations == 5
        assert metadata.total_duration_ms == 1000.0
        assert metadata.tools_used == ["tool1", "tool2"]


class TestConversationMessage:
    """Tests for ConversationMessage"""

    def test_create_message(self):
        """Test creating a conversation message"""
        now = datetime.now()
        msg = ConversationMessage(
            role="user",
            content="Hello",
            timestamp=now,
            tool_name=None,
            invocation_id=None,
        )

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp == now
        assert msg.tool_name is None
        assert msg.invocation_id is None

    def test_message_to_dict(self):
        """Test converting message to dictionary"""
        now = datetime.now()
        msg = ConversationMessage(
            role="tool",
            content="Result",
            timestamp=now,
            tool_name="git_tool",
            invocation_id="inv123",
        )

        data = msg.to_dict()
        assert data["role"] == "tool"
        assert data["content"] == "Result"
        assert data["tool_name"] == "git_tool"
        assert data["invocation_id"] == "inv123"
        assert isinstance(data["timestamp"], str)

    def test_message_from_dict(self):
        """Test creating message from dictionary"""
        now = datetime.now()
        data = {
            "role": "assistant",
            "content": "Response",
            "timestamp": now.isoformat(),
            "tool_name": None,
            "invocation_id": None,
        }

        msg = ConversationMessage.from_dict(data)
        assert msg.role == "assistant"
        assert msg.content == "Response"
        assert msg.tool_name is None
        assert msg.invocation_id is None


class TestSession:
    """Tests for Session"""

    def test_create_session(self):
        """Test creating a session"""
        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )

        session = Session(metadata=metadata)
        assert session.metadata.session_id == "test_session"
        assert len(session.invocation_ids) == 0
        assert len(session.conversation) == 0

    def test_add_invocation(self):
        """Test adding invocations to session"""
        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        session.add_invocation("inv1", duration_ms=100.0)
        assert len(session.invocation_ids) == 1
        assert session.invocation_ids[0] == "inv1"
        assert session.metadata.total_invocations == 1
        assert session.metadata.total_duration_ms == 100.0

        session.add_invocation("inv2", duration_ms=200.0)
        assert len(session.invocation_ids) == 2
        assert session.metadata.total_invocations == 2
        assert session.metadata.total_duration_ms == 300.0

    def test_add_invocation_no_duration(self):
        """Test adding invocation without duration"""
        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        session.add_invocation("inv1")
        assert session.metadata.total_invocations == 1
        assert session.metadata.total_duration_ms == 0.0

    def test_add_message(self):
        """Test adding messages to conversation"""
        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        session.add_message("user", "Hello")
        assert len(session.conversation) == 1
        assert session.conversation[0].role == "user"
        assert session.conversation[0].content == "Hello"

        session.add_message("assistant", "Hi there", tool_name="assistant_tool")
        assert len(session.conversation) == 2
        assert session.conversation[1].tool_name == "assistant_tool"

    def test_session_to_dict(self):
        """Test converting session to dictionary"""
        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)
        session.add_invocation("inv1")
        session.add_message("user", "Hello")

        data = session.to_dict()
        assert data["metadata"]["session_id"] == "test_session"
        assert len(data["invocation_ids"]) == 1
        assert len(data["conversation"]) == 1

    def test_session_from_dict(self):
        """Test creating session from dictionary"""
        now = datetime.now()
        data = {
            "metadata": {
                "session_id": "test_session",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "status": "active",
                "user_id": None,
                "purpose": None,
                "tags": [],
                "total_invocations": 1,
                "total_duration_ms": 100.0,
                "tools_used": [],
                "estimated_cost": 0.0,
                "token_usage": {},
                "custom_metadata": {},
            },
            "invocation_ids": ["inv1"],
            "conversation": [
                {
                    "role": "user",
                    "content": "Hello",
                    "timestamp": now.isoformat(),
                    "tool_name": None,
                    "invocation_id": None,
                }
            ],
        }

        session = Session.from_dict(data)
        assert session.metadata.session_id == "test_session"
        assert len(session.invocation_ids) == 1
        assert len(session.conversation) == 1
        assert session.conversation[0].content == "Hello"

    def test_add_duplicate_invocation(self):
        """Test that duplicate invocations are not added"""
        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        session.add_invocation("inv1", duration_ms=100.0)
        session.add_invocation("inv1", duration_ms=100.0)

        assert len(session.invocation_ids) == 1
        assert session.metadata.total_invocations == 1
