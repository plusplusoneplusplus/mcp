"""
Tests for the MemoryManager class.
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta

from ..memory_manager import MemoryManager


class TestMemoryManager:
    """Test cases for MemoryManager."""

    def test_init_without_persistence(self):
        """Test initialization without persistence."""
        manager = MemoryManager()
        assert manager.persist_directory is None
        assert manager.conversation_memory is not None
        assert manager.context_memory is not None

    def test_init_with_persistence(self):
        """Test initialization with persistence directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = MemoryManager(persist_directory=temp_dir)
            assert manager.persist_directory == temp_dir
            assert os.path.exists(temp_dir)

    def test_add_conversation(self):
        """Test adding conversation entries."""
        manager = MemoryManager()

        entry_id = manager.add_conversation(
            role="user",
            content="Hello, world!",
            session_id="test_session"
        )

        assert entry_id is not None
        assert len(manager.conversation_memory.entries) == 1

    def test_add_context(self):
        """Test adding context entries."""
        manager = MemoryManager()

        entry_id = manager.add_context(
            content="Python is a programming language",
            topic="programming",
            importance=0.8
        )

        assert entry_id is not None
        assert len(manager.context_memory.entries) == 1

    def test_get_conversation_history(self):
        """Test retrieving conversation history."""
        manager = MemoryManager()

        # Add some conversations
        manager.add_conversation("user", "Hello", "session1")
        manager.add_conversation("assistant", "Hi there!", "session1")
        manager.add_conversation("user", "How are you?", "session2")

        # Get all history
        all_history = manager.get_conversation_history()
        assert len(all_history) == 3

        # Get session-specific history
        session1_history = manager.get_conversation_history(session_id="session1")
        assert len(session1_history) == 2

        # Get limited history
        limited_history = manager.get_conversation_history(limit=1)
        assert len(limited_history) == 1

    def test_search_context(self):
        """Test searching context entries."""
        manager = MemoryManager()

        # Add context entries
        manager.add_context("Python is great for data science", "programming")
        manager.add_context("Machine learning uses Python", "ai")
        manager.add_context("JavaScript runs in browsers", "programming")

        # Search for Python
        results = manager.search_context("Python")
        assert len(results) == 2

        # Search with topic filter
        results = manager.search_context("Python", topic="programming")
        assert len(results) == 1

    def test_clear_conversation(self):
        """Test clearing conversation history."""
        manager = MemoryManager()

        # Add conversations
        manager.add_conversation("user", "Hello", "session1")
        manager.add_conversation("user", "Hi", "session2")

        # Clear specific session
        manager.clear_conversation(session_id="session1")
        history = manager.get_conversation_history()
        assert len(history) == 1
        assert history[0]["session_id"] == "session2"

        # Clear all conversations
        manager.clear_conversation()
        assert len(manager.get_conversation_history()) == 0

    def test_clear_context(self):
        """Test clearing context entries."""
        manager = MemoryManager()

        # Add context entries
        manager.add_context("Python info", "programming")
        manager.add_context("AI info", "ai")

        # Clear specific topic
        manager.clear_context(topic="programming")
        results = manager.search_context("Python")
        assert len(results) == 0

        # Verify other topic still exists
        results = manager.search_context("AI")
        assert len(results) == 1

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries."""
        manager = MemoryManager()

        # Add some entries
        manager.add_conversation("user", "Hello", "session1")
        manager.add_context("Some context", "test")

        # Cleanup entries older than 1 day (should keep recent entries)
        manager.cleanup_old_entries(days_old=1)

        # Entries should still exist since they were just created
        assert len(manager.get_conversation_history()) == 1
        assert len(manager.search_context("context")) == 1

    def test_get_stats(self):
        """Test getting memory statistics."""
        manager = MemoryManager()

        # Add some data
        manager.add_conversation("user", "Hello", "session1")
        manager.add_conversation("user", "Hi", "session2")
        manager.add_context("Context 1", "topic1")
        manager.add_context("Context 2", "topic2")

        stats = manager.get_stats()
        assert stats["conversation_entries"] == 2
        assert stats["context_entries"] == 2
        assert stats["total_entries"] == 4
        assert stats["sessions"] == 2
        assert stats["topics"] == 2

    def test_persistence(self):
        """Test saving and loading from disk."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create manager and add data
            manager1 = MemoryManager(persist_directory=temp_dir)
            manager1.add_conversation("user", "Hello", "test_session")
            manager1.add_context("Test context", "test_topic")

            # Save to disk
            manager1.save_to_disk()

            # Create new manager and verify data loads
            manager2 = MemoryManager(persist_directory=temp_dir)

            history = manager2.get_conversation_history()
            assert len(history) == 1
            assert history[0]["content"] == "Hello"

            results = manager2.search_context("Test")
            assert len(results) == 1
            assert results[0]["content"] == "Test context"

    def test_invalid_data_handling(self):
        """Test handling of invalid data during loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with invalid data
            conv_file = os.path.join(temp_dir, "conversations.json")
            ctx_file = os.path.join(temp_dir, "context.json")

            with open(conv_file, 'w') as f:
                f.write('[{"invalid": "data"}]')

            with open(ctx_file, 'w') as f:
                f.write('[{"also_invalid": "data"}]')

            # Manager should handle invalid data gracefully
            manager = MemoryManager(persist_directory=temp_dir)
            assert len(manager.get_conversation_history()) == 0
            assert len(manager.search_context("anything")) == 0
