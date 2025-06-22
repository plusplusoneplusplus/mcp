"""
Context memory for storing and retrieving factual information and knowledge.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import defaultdict

from .types import ContextEntry, MemoryType


class ContextMemory:
    """
    Manages contextual information and knowledge base.
    Supports topic-based organization and importance scoring.
    """

    def __init__(self, max_entries: int = 500):
        """
        Initialize context memory.

        Args:
            max_entries: Maximum number of entries to keep
        """
        self.max_entries = max_entries
        self.entries: List[ContextEntry] = []
        self._topic_index: Dict[str, List[str]] = defaultdict(list)  # topic -> entry_ids

    def add_context(self,
                   content: str,
                   topic: str,
                   importance: float = 1.0,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add contextual information.

        Args:
            content: The contextual information
            topic: Topic/category for organization
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata

        Returns:
            The entry ID
        """
        entry_id = str(uuid.uuid4())
        entry = ContextEntry(
            id=entry_id,
            content=content,
            timestamp=datetime.now(),
            memory_type=MemoryType.CONTEXT,
            metadata=metadata,
            topic=topic,
            importance=max(0.0, min(1.0, importance))  # Clamp to [0, 1]
        )

        # Add to entries
        self.entries.append(entry)

        # Update topic index
        self._topic_index[topic].append(entry_id)

        # Maintain max entries limit
        if len(self.entries) > self.max_entries:
            self._cleanup_entries()

        return entry_id

    def search(self,
              query: str,
              topic: Optional[str] = None,
              limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search context entries by content similarity.

        Args:
            query: Search query
            topic: Filter by topic (None for all topics)
            limit: Maximum results to return

        Returns:
            List of matching context entries, ranked by relevance
        """
        query_lower = query.lower()
        matches = []

        for entry in self.entries:
            # Filter by topic if specified
            if topic and entry.topic != topic:
                continue

            # Simple text matching (could be enhanced with embeddings)
            content_lower = entry.content.lower()
            relevance_score = 0.0

            # Exact phrase match gets highest score
            if query_lower in content_lower:
                relevance_score = 1.0
            else:
                # Word-based matching
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                common_words = query_words.intersection(content_words)

                if common_words:
                    relevance_score = len(common_words) / len(query_words)

            if relevance_score > 0:
                # Combine relevance with importance score
                final_score = relevance_score * entry.importance
                matches.append((final_score, entry))

        # Sort by score (descending)
        matches.sort(key=lambda x: x[0], reverse=True)

        # Return top matches
        return [entry.to_dict() for _, entry in matches[:limit]]

    def get_by_topic(self, topic: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all entries for a specific topic.

        Args:
            topic: Topic to filter by
            limit: Maximum results to return

        Returns:
            List of context entries for the topic
        """
        topic_entries = [
            entry for entry in self.entries
            if entry.topic == topic
        ]

        # Sort by importance and recency
        topic_entries.sort(
            key=lambda x: (x.importance, x.timestamp),
            reverse=True
        )

        if limit:
            topic_entries = topic_entries[:limit]

        return [entry.to_dict() for entry in topic_entries]

    def get_topics(self) -> List[str]:
        """Get list of all topics."""
        return list(self._topic_index.keys())

    def update_importance(self, entry_id: str, importance: float) -> bool:
        """
        Update the importance score of an entry.

        Args:
            entry_id: ID of the entry to update
            importance: New importance score

        Returns:
            True if updated, False if entry not found
        """
        for entry in self.entries:
            if entry.id == entry_id:
                entry.importance = max(0.0, min(1.0, importance))
                return True
        return False

    def remove_entry(self, entry_id: str) -> bool:
        """
        Remove a specific entry.

        Args:
            entry_id: ID of the entry to remove

        Returns:
            True if removed, False if not found
        """
        for i, entry in enumerate(self.entries):
            if entry.id == entry_id:
                # Remove from entries
                removed_entry = self.entries.pop(i)

                # Update topic index
                topic_list = self._topic_index[removed_entry.topic]
                if entry_id in topic_list:
                    topic_list.remove(entry_id)

                # Clean up empty topic
                if not topic_list:
                    del self._topic_index[removed_entry.topic]

                return True
        return False

    def clear(self, topic: Optional[str] = None):
        """
        Clear context entries.

        Args:
            topic: Clear specific topic (None clears all)
        """
        if topic is None:
            self.entries.clear()
            self._topic_index.clear()
        else:
            # Remove entries for specific topic
            self.entries = [
                entry for entry in self.entries
                if entry.topic != topic
            ]

            # Remove from topic index
            if topic in self._topic_index:
                del self._topic_index[topic]

    def cleanup_old_entries(self, cutoff_date: datetime):
        """Remove entries older than cutoff date."""
        old_entries = []
        self.entries = [
            entry for entry in self.entries
            if entry.timestamp > cutoff_date or old_entries.append(entry)
        ]

        # Update topic index
        for entry in old_entries:
            topic_list = self._topic_index[entry.topic]
            if entry.id in topic_list:
                topic_list.remove(entry.id)

            # Clean up empty topics
            if not topic_list:
                del self._topic_index[entry.topic]

    def _cleanup_entries(self):
        """Remove least important entries to maintain max_entries limit."""
        if len(self.entries) <= self.max_entries:
            return

        # Sort by importance (ascending) and timestamp (ascending)
        # This prioritizes keeping recent and important entries
        self.entries.sort(key=lambda x: (x.importance, x.timestamp))

        # Remove least important/oldest entries
        entries_to_remove = len(self.entries) - self.max_entries
        removed_entries = self.entries[:entries_to_remove]
        self.entries = self.entries[entries_to_remove:]

        # Update topic index
        for entry in removed_entries:
            topic_list = self._topic_index[entry.topic]
            if entry.id in topic_list:
                topic_list.remove(entry.id)

            # Clean up empty topics
            if not topic_list:
                del self._topic_index[entry.topic]

    def load_from_data(self, data: List[Dict[str, Any]]):
        """Load context data from serialized format."""
        self.entries.clear()
        self._topic_index.clear()

        for item in data:
            try:
                entry = ContextEntry.from_dict(item)
                self.entries.append(entry)
                self._topic_index[entry.topic].append(entry.id)
            except Exception as e:
                # Skip invalid entries
                continue
