"""Tests for session storage"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from utils.session.models import Session, SessionMetadata, SessionStatus
from utils.session.storage import (
    FileSystemSessionStorage,
    MemorySessionStorage,
)


class TestMemorySessionStorage:
    """Tests for MemorySessionStorage"""

    def test_save_and_load_session(self):
        """Test saving and loading a session"""
        storage = MemorySessionStorage()

        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        storage.save_session(session)
        loaded = storage.load_session("test_session")

        assert loaded is not None
        assert loaded.metadata.session_id == "test_session"
        assert loaded.metadata.status == SessionStatus.ACTIVE

    def test_load_nonexistent_session(self):
        """Test loading a session that doesn't exist"""
        storage = MemorySessionStorage()
        loaded = storage.load_session("nonexistent")
        assert loaded is None

    def test_session_exists(self):
        """Test checking if session exists"""
        storage = MemorySessionStorage()

        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        assert not storage.session_exists("test_session")
        storage.save_session(session)
        assert storage.session_exists("test_session")

    def test_delete_session(self):
        """Test deleting a session"""
        storage = MemorySessionStorage()

        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        storage.save_session(session)
        assert storage.session_exists("test_session")

        storage.delete_session("test_session")
        assert not storage.session_exists("test_session")

    def test_list_sessions(self):
        """Test listing sessions"""
        storage = MemorySessionStorage()
        now = datetime.now()

        # Create multiple sessions
        for i in range(3):
            metadata = SessionMetadata(
                session_id=f"session_{i}",
                created_at=now,
                updated_at=now,
                status=SessionStatus.ACTIVE,
                user_id="user1",
                tags=["test"],
            )
            session = Session(metadata=metadata)
            storage.save_session(session)

        sessions = storage.list_sessions()
        assert len(sessions) == 3

    def test_list_sessions_with_user_filter(self):
        """Test listing sessions filtered by user"""
        storage = MemorySessionStorage()
        now = datetime.now()

        # Create sessions for different users
        for i in range(3):
            user_id = "user1" if i < 2 else "user2"
            metadata = SessionMetadata(
                session_id=f"session_{i}",
                created_at=now,
                updated_at=now,
                status=SessionStatus.ACTIVE,
                user_id=user_id,
            )
            session = Session(metadata=metadata)
            storage.save_session(session)

        sessions = storage.list_sessions(user_id="user1")
        assert len(sessions) == 2
        assert all(s.metadata.user_id == "user1" for s in sessions)

    def test_list_sessions_with_status_filter(self):
        """Test listing sessions filtered by status"""
        storage = MemorySessionStorage()
        now = datetime.now()

        # Create sessions with different statuses
        for i, status in enumerate(
            [SessionStatus.ACTIVE, SessionStatus.COMPLETED, SessionStatus.FAILED]
        ):
            metadata = SessionMetadata(
                session_id=f"session_{i}",
                created_at=now,
                updated_at=now,
                status=status,
            )
            session = Session(metadata=metadata)
            storage.save_session(session)

        sessions = storage.list_sessions(status=SessionStatus.ACTIVE)
        assert len(sessions) == 1
        assert sessions[0].metadata.status == SessionStatus.ACTIVE

    def test_list_sessions_with_tags_filter(self):
        """Test listing sessions filtered by tags"""
        storage = MemorySessionStorage()
        now = datetime.now()

        # Create sessions with different tags
        sessions_data = [
            ("session_0", ["tag1", "tag2"]),
            ("session_1", ["tag2", "tag3"]),
            ("session_2", ["tag3", "tag4"]),
        ]

        for session_id, tags in sessions_data:
            metadata = SessionMetadata(
                session_id=session_id,
                created_at=now,
                updated_at=now,
                status=SessionStatus.ACTIVE,
                tags=tags,
            )
            session = Session(metadata=metadata)
            storage.save_session(session)

        # Filter by tag2 (should match first two sessions)
        sessions = storage.list_sessions(tags=["tag2"])
        assert len(sessions) == 2

        # Filter by tag4 (should match last session)
        sessions = storage.list_sessions(tags=["tag4"])
        assert len(sessions) == 1

    def test_list_sessions_with_limit(self):
        """Test listing sessions with limit"""
        storage = MemorySessionStorage()
        now = datetime.now()

        # Create multiple sessions
        for i in range(10):
            metadata = SessionMetadata(
                session_id=f"session_{i}",
                created_at=now,
                updated_at=now,
                status=SessionStatus.ACTIVE,
            )
            session = Session(metadata=metadata)
            storage.save_session(session)

        sessions = storage.list_sessions(limit=5)
        assert len(sessions) == 5

    def test_cleanup_sessions(self):
        """Test cleaning up old sessions"""
        storage = MemorySessionStorage()
        now = datetime.now()
        old_date = now - timedelta(days=60)

        # Create old and new sessions
        old_metadata = SessionMetadata(
            session_id="old_session",
            created_at=old_date,
            updated_at=old_date,
            status=SessionStatus.COMPLETED,
        )
        old_session = Session(metadata=old_metadata)
        storage.save_session(old_session)

        new_metadata = SessionMetadata(
            session_id="new_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        new_session = Session(metadata=new_metadata)
        storage.save_session(new_session)

        # Cleanup sessions older than 30 days
        cutoff = now - timedelta(days=30)
        storage.cleanup_sessions(cutoff)

        assert not storage.session_exists("old_session")
        assert storage.session_exists("new_session")


class TestFileSystemSessionStorage:
    """Tests for FileSystemSessionStorage"""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing"""
        with tempfile.TemporaryDirectory() as sessions_dir:
            with tempfile.TemporaryDirectory() as history_dir:
                yield Path(sessions_dir), Path(history_dir)

    def test_save_and_load_session(self, temp_dirs):
        """Test saving and loading a session to filesystem"""
        sessions_dir, history_dir = temp_dirs
        storage = FileSystemSessionStorage(sessions_dir, history_dir)

        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
            purpose="Test session",
            tags=["test"],
        )
        session = Session(metadata=metadata)
        session.add_invocation("inv1", duration_ms=100.0)
        session.add_message("user", "Hello")

        storage.save_session(session)
        loaded = storage.load_session("test_session")

        assert loaded is not None
        assert loaded.metadata.session_id == "test_session"
        assert loaded.metadata.purpose == "Test session"
        assert len(loaded.invocation_ids) == 1
        assert len(loaded.conversation) == 1
        assert loaded.conversation[0].content == "Hello"

    def test_session_directory_structure(self, temp_dirs):
        """Test that session directory structure is created correctly"""
        sessions_dir, history_dir = temp_dirs
        storage = FileSystemSessionStorage(sessions_dir, history_dir)

        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)
        session.add_message("user", "Hello")

        storage.save_session(session)

        session_dir = sessions_dir / "test_session"
        assert session_dir.exists()
        assert (session_dir / "metadata.json").exists()
        assert (session_dir / "conversation.jsonl").exists()
        assert (session_dir / "invocations.json").exists()

    def test_load_nonexistent_session(self, temp_dirs):
        """Test loading a session that doesn't exist"""
        sessions_dir, history_dir = temp_dirs
        storage = FileSystemSessionStorage(sessions_dir, history_dir)

        loaded = storage.load_session("nonexistent")
        assert loaded is None

    def test_session_exists(self, temp_dirs):
        """Test checking if session exists"""
        sessions_dir, history_dir = temp_dirs
        storage = FileSystemSessionStorage(sessions_dir, history_dir)

        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        assert not storage.session_exists("test_session")
        storage.save_session(session)
        assert storage.session_exists("test_session")

    def test_delete_session(self, temp_dirs):
        """Test deleting a session"""
        sessions_dir, history_dir = temp_dirs
        storage = FileSystemSessionStorage(sessions_dir, history_dir)

        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)

        storage.save_session(session)
        session_dir = sessions_dir / "test_session"
        assert session_dir.exists()

        storage.delete_session("test_session")
        assert not session_dir.exists()

    def test_link_invocation(self, temp_dirs):
        """Test linking invocation to session"""
        sessions_dir, history_dir = temp_dirs
        storage = FileSystemSessionStorage(sessions_dir, history_dir)

        # Create fake invocation directory
        invocation_dir = history_dir / "2024-11-06_14-23-45_123456_git_tool"
        invocation_dir.mkdir(parents=True)

        now = datetime.now()
        metadata = SessionMetadata(
            session_id="test_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        session = Session(metadata=metadata)
        storage.save_session(session)

        storage.link_invocation("test_session", "inv123", invocation_dir)

        # Check symlink was created
        session_invocations_dir = sessions_dir / "test_session" / "invocations"
        assert session_invocations_dir.exists()
        # Symlink should exist (if platform supports it)
        # Note: on some systems symlinks may not be supported

    def test_list_sessions(self, temp_dirs):
        """Test listing sessions"""
        sessions_dir, history_dir = temp_dirs
        storage = FileSystemSessionStorage(sessions_dir, history_dir)
        now = datetime.now()

        # Create multiple sessions
        for i in range(3):
            metadata = SessionMetadata(
                session_id=f"session_{i}",
                created_at=now,
                updated_at=now,
                status=SessionStatus.ACTIVE,
            )
            session = Session(metadata=metadata)
            storage.save_session(session)

        sessions = storage.list_sessions()
        assert len(sessions) == 3

    def test_cleanup_sessions(self, temp_dirs):
        """Test cleaning up old sessions"""
        sessions_dir, history_dir = temp_dirs
        storage = FileSystemSessionStorage(sessions_dir, history_dir)
        now = datetime.now()
        old_date = now - timedelta(days=60)

        # Create old and new sessions
        old_metadata = SessionMetadata(
            session_id="old_session",
            created_at=old_date,
            updated_at=old_date,
            status=SessionStatus.COMPLETED,
        )
        old_session = Session(metadata=old_metadata)
        storage.save_session(old_session)

        new_metadata = SessionMetadata(
            session_id="new_session",
            created_at=now,
            updated_at=now,
            status=SessionStatus.ACTIVE,
        )
        new_session = Session(metadata=new_metadata)
        storage.save_session(new_session)

        # Cleanup sessions older than 30 days
        cutoff = now - timedelta(days=30)
        storage.cleanup_sessions(cutoff)

        assert not storage.session_exists("old_session")
        assert storage.session_exists("new_session")
