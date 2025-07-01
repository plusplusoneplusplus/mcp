from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStore(ABC):
    """Abstract interface for vector store backends."""

    @abstractmethod
    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None,
    ) -> None:
        """Add records to the store."""

    @abstractmethod
    def query(
        self,
        query_embeddings: List[List[float]],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Query for similar embeddings."""

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """Delete records by id."""

    @abstractmethod
    def list_collections(self) -> List[str]:
        """Return all collection names."""

    @abstractmethod
    def get_collection(self, collection_name: str) -> None:
        """Switch the active collection."""
