import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from ..context_memory import ContextMemory
from ..types import ContextEntry


class TestContextMemory:
    """Test cases for ContextMemory class."""

    def test_init(self):
        """Test initialization of ContextMemory."""
        memory = ContextMemory(max_entries=100)
        assert memory.max_entries == 100
        assert len(memory.entries) == 0
        assert len(memory._topic_index) == 0

    def test_add_context(self):
        """Test adding context entries."""
        memory = ContextMemory()

        entry_id = memory.add_context(
            content="Python is a programming language",
            topic="programming",
            importance=0.8
        )

        assert entry_id is not None
        assert len(memory.entries) == 1

        entry = memory.entries[0]
        assert entry.content == "Python is a programming language"
        assert entry.topic == "programming"
        assert entry.importance == 0.8
        assert entry.id == entry_id

    def test_add_context_with_metadata(self):
        """Test adding context with metadata."""
        memory = ContextMemory()
        metadata = {"source": "documentation", "url": "https://python.org"}

        entry_id = memory.add_context(
            content="Python documentation",
            topic="programming",
            metadata=metadata
        )

        entry = memory.entries[0]
        assert entry.metadata == metadata

    def test_importance_clamping(self):
        """Test that importance scores are clamped to [0, 1]."""
        memory = ContextMemory()

        # Test values outside range
        entry_id1 = memory.add_context("Test 1", "test", importance=-0.5)
        entry_id2 = memory.add_context("Test 2", "test", importance=1.5)

        assert memory.entries[0].importance == 0.0
        assert memory.entries[1].importance == 1.0

    def test_topic_indexing(self):
        """Test that topic index is maintained correctly."""
        memory = ContextMemory()

        entry_id1 = memory.add_context("Python info", "programming")
        entry_id2 = memory.add_context("AI info", "ai")
        entry_id3 = memory.add_context("More Python info", "programming")

        # Check topic index
        assert "programming" in memory._topic_index
        assert "ai" in memory._topic_index
        assert len(memory._topic_index["programming"]) == 2
        assert len(memory._topic_index["ai"]) == 1
        assert entry_id1 in memory._topic_index["programming"]
        assert entry_id3 in memory._topic_index["programming"]
        assert entry_id2 in memory._topic_index["ai"]

    def test_search_exact_match(self):
        """Test searching with exact phrase match."""
        memory = ContextMemory()

        memory.add_context("Python is great for data science", "programming", 0.9)
        memory.add_context("Machine learning uses Python", "ai", 0.8)
        memory.add_context("JavaScript runs in browsers", "programming", 0.7)

        # Search for exact phrase
        results = memory.search("data science")
        assert len(results) == 1
        assert results[0]["content"] == "Python is great for data science"

    def test_search_word_matching(self):
        """Test searching with word-based matching."""
        memory = ContextMemory()

        memory.add_context("Python programming language", "programming", 0.9)
        memory.add_context("Java programming concepts", "programming", 0.8)
        memory.add_context("Web development tools", "web", 0.7)

        # Search for words that appear in multiple entries
        results = memory.search("programming")
        assert len(results) == 2

        # Results should be sorted by combined score (relevance * importance)
        assert results[0]["content"] == "Python programming language"  # Higher importance
        assert results[1]["content"] == "Java programming concepts"

    def test_search_with_topic_filter(self):
        """Test searching with topic filter."""
        memory = ContextMemory()

        memory.add_context("Python programming", "programming", 0.9)
        memory.add_context("Python for AI", "ai", 0.8)
        memory.add_context("Java programming", "programming", 0.7)

        # Search with topic filter
        results = memory.search("Python", topic="programming")
        assert len(results) == 1
        assert results[0]["content"] == "Python programming"
        assert results[0]["topic"] == "programming"

    def test_search_with_limit(self):
        """Test search result limiting."""
        memory = ContextMemory()

        # Add multiple entries that match
        for i in range(10):
            memory.add_context(f"Python tutorial {i}", "programming", 0.5)

        # Search with limit
        results = memory.search("Python", limit=3)
        assert len(results) == 3

    def test_search_no_matches(self):
        """Test searching with no matches."""
        memory = ContextMemory()

        memory.add_context("Python programming", "programming")
        memory.add_context("Java development", "programming")

        results = memory.search("Ruby")
        assert len(results) == 0

    def test_get_by_topic(self):
        """Test retrieving entries by topic."""
        memory = ContextMemory()

        memory.add_context("Python basics", "programming", 0.9)
        memory.add_context("Advanced Python", "programming", 0.8)
        memory.add_context("AI concepts", "ai", 0.7)

        # Get programming entries
        prog_entries = memory.get_by_topic("programming")
        assert len(prog_entries) == 2

        # Should be sorted by importance (descending)
        assert prog_entries[0]["content"] == "Python basics"
        assert prog_entries[1]["content"] == "Advanced Python"

        # Get AI entries
        ai_entries = memory.get_by_topic("ai")
        assert len(ai_entries) == 1
        assert ai_entries[0]["content"] == "AI concepts"

    def test_get_by_topic_with_limit(self):
        """Test retrieving entries by topic with limit."""
        memory = ContextMemory()

        # Add multiple entries for same topic
        for i in range(5):
            memory.add_context(f"Entry {i}", "test", importance=i * 0.2)

        # Get limited results
        entries = memory.get_by_topic("test", limit=3)
        assert len(entries) == 3

        # Should be most important/recent entries
        assert entries[0]["content"] == "Entry 4"  # Highest importance

    def test_get_topics(self):
        """Test retrieving list of topics."""
        memory = ContextMemory()

        memory.add_context("Python info", "programming")
        memory.add_context("AI info", "ai")
        memory.add_context("Web info", "web")

        topics = memory.get_topics()
        assert len(topics) == 3
        assert "programming" in topics
        assert "ai" in topics
        assert "web" in topics

    def test_update_importance(self):
        """Test updating importance score."""
        memory = ContextMemory()

        entry_id = memory.add_context("Test content", "test", importance=0.5)

        # Update importance
        success = memory.update_importance(entry_id, 0.9)
        assert success is True
        assert memory.entries[0].importance == 0.9

        # Try updating non-existent entry
        success = memory.update_importance("nonexistent", 0.5)
        assert success is False

    def test_update_importance_clamping(self):
        """Test that importance updates are clamped."""
        memory = ContextMemory()

        entry_id = memory.add_context("Test content", "test")

        # Test clamping
        memory.update_importance(entry_id, -0.5)
        assert memory.entries[0].importance == 0.0

        memory.update_importance(entry_id, 1.5)
        assert memory.entries[0].importance == 1.0

    def test_remove_entry(self):
        """Test removing specific entries."""
        memory = ContextMemory()

        entry_id1 = memory.add_context("Entry 1", "topic1")
        entry_id2 = memory.add_context("Entry 2", "topic1")
        entry_id3 = memory.add_context("Entry 3", "topic2")

        # Remove entry
        success = memory.remove_entry(entry_id2)
        assert success is True
        assert len(memory.entries) == 2

        # Check topic index updated
        assert entry_id2 not in memory._topic_index["topic1"]
        assert entry_id1 in memory._topic_index["topic1"]

        # Try removing non-existent entry
        success = memory.remove_entry("nonexistent")
        assert success is False

    def test_remove_entry_cleans_empty_topics(self):
        """Test that removing entries cleans up empty topics."""
        memory = ContextMemory()

        entry_id = memory.add_context("Only entry", "solo_topic")

        # Remove the only entry for this topic
        memory.remove_entry(entry_id)

        # Topic should be removed from index
        assert "solo_topic" not in memory._topic_index
        assert "solo_topic" not in memory.get_topics()

    def test_clear_all(self):
        """Test clearing all context entries."""
        memory = ContextMemory()

        memory.add_context("Entry 1", "topic1")
        memory.add_context("Entry 2", "topic2")

        memory.clear()
        assert len(memory.entries) == 0
        assert len(memory._topic_index) == 0
        assert len(memory.get_topics()) == 0

    def test_clear_by_topic(self):
        """Test clearing entries for specific topic."""
        memory = ContextMemory()

        memory.add_context("Entry 1", "topic1")
        memory.add_context("Entry 2", "topic1")
        memory.add_context("Entry 3", "topic2")

        memory.clear(topic="topic1")

        # Only topic2 entries should remain
        assert len(memory.entries) == 1
        assert memory.entries[0].topic == "topic2"

        # Topic index should be updated
        assert "topic1" not in memory._topic_index
        assert "topic2" in memory._topic_index

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries."""
        memory = ContextMemory()

        # Mock timestamps
        now = datetime.now()
        old_time = now - timedelta(days=5)
        recent_time = now - timedelta(hours=1)

        with patch('utils.memory.context_memory.datetime') as mock_datetime:
            # Add old entry
            mock_datetime.now.return_value = old_time
            old_entry_id = memory.add_context("Old entry", "topic1")

            # Add recent entry
            mock_datetime.now.return_value = recent_time
            recent_entry_id = memory.add_context("Recent entry", "topic1")

        # Cleanup entries older than 2 days
        cutoff_date = now - timedelta(days=2)
        memory.cleanup_old_entries(cutoff_date)

        # Only recent entry should remain
        assert len(memory.entries) == 1
        assert memory.entries[0].content == "Recent entry"

        # Topic index should be updated
        assert old_entry_id not in memory._topic_index["topic1"]
        assert recent_entry_id in memory._topic_index["topic1"]

    def test_max_entries_cleanup(self):
        """Test that max_entries limit triggers cleanup."""
        memory = ContextMemory(max_entries=3)

        # Add entries with different importance scores
        memory.add_context("Low importance", "test", importance=0.1)
        memory.add_context("Medium importance", "test", importance=0.5)
        memory.add_context("High importance", "test", importance=0.9)
        memory.add_context("Another high", "test", importance=0.8)  # Should trigger cleanup

        # Should only keep 3 most important/recent entries
        assert len(memory.entries) == 3

        # Check that least important entry was removed
        contents = [entry.content for entry in memory.entries]
        assert "Low importance" not in contents
        assert "High importance" in contents
        assert "Another high" in contents
        assert "Medium importance" in contents

    def test_load_from_data_valid(self):
        """Test loading valid data from serialized format."""
        memory = ContextMemory()

        # Create test data
        test_data = [
            {
                "id": "test1",
                "content": "Python programming",
                "timestamp": datetime.now().isoformat(),
                "memory_type": "context",
                "topic": "programming",
                "importance": 0.9,
                "metadata": {"source": "docs"}
            },
            {
                "id": "test2",
                "content": "AI concepts",
                "timestamp": datetime.now().isoformat(),
                "memory_type": "context",
                "topic": "ai",
                "importance": 0.8
            }
        ]

        memory.load_from_data(test_data)

        assert len(memory.entries) == 2
        assert memory.entries[0].content == "Python programming"
        assert memory.entries[0].topic == "programming"
        assert memory.entries[0].importance == 0.9
        assert memory.entries[1].content == "AI concepts"
        assert memory.entries[1].topic == "ai"

        # Check topic index
        assert "programming" in memory._topic_index
        assert "ai" in memory._topic_index

    def test_load_from_data_invalid(self):
        """Test loading invalid data - should skip bad entries."""
        memory = ContextMemory()

        # Mix of valid and invalid data
        test_data = [
            {
                "id": "test1",
                "content": "Valid entry",
                "timestamp": datetime.now().isoformat(),
                "memory_type": "context",
                "topic": "test",
                "importance": 0.5
            },
            {
                "invalid": "data",
                "missing": "required_fields"
            },
            {
                "id": "test2",
                "content": "Another valid entry",
                "timestamp": datetime.now().isoformat(),
                "memory_type": "context",
                "topic": "test2",
                "importance": 0.7
            }
        ]

        memory.load_from_data(test_data)

        # Should only load valid entries
        assert len(memory.entries) == 2
        assert memory.entries[0].content == "Valid entry"
        assert memory.entries[1].content == "Another valid entry"

        # Topic index should be built correctly
        assert "test" in memory._topic_index
        assert "test2" in memory._topic_index

    def test_entry_serialization(self):
        """Test that entries can be properly serialized and deserialized."""
        memory = ContextMemory()

        entry_id = memory.add_context(
            content="Test context",
            topic="test_topic",
            importance=0.8,
            metadata={"source": "test"}
        )

        # Get the serialized entry
        results = memory.get_by_topic("test_topic")
        serialized_entry = results[0]

        # Verify all fields are present
        required_fields = ["id", "content", "timestamp", "memory_type", "topic", "importance"]
        for field in required_fields:
            assert field in serialized_entry

        assert serialized_entry["id"] == entry_id
        assert serialized_entry["content"] == "Test context"
        assert serialized_entry["topic"] == "test_topic"
        assert serialized_entry["importance"] == 0.8
        assert serialized_entry["metadata"] == {"source": "test"}
        assert serialized_entry["memory_type"] == "context"
