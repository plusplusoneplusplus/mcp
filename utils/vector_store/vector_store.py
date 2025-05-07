import chromadb
from typing import List, Optional, Any, Dict

class ChromaVectorStore:
    """
    Utility class for storing and accessing data through ChromaDB vector database.
    """
    def __init__(self, collection_name: str = "default", persist_directory: Optional[str] = None):
        """
        Initialize the ChromaDB client and collection.
        Args:
            collection_name (str): Name of the collection to use.
            persist_directory (Optional[str]): Directory for persistent storage. If None, uses in-memory DB.
        """
        if persist_directory is not None:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.EphemeralClient()
        self.collection = self.client.get_or_create_collection(collection_name)

    def add(self, ids: List[str], embeddings: List[List[float]], metadatas: Optional[List[Dict[str, Any]]] = None, documents: Optional[List[str]] = None):
        """
        Add vectors/documents to the collection.
        Args:
            ids (List[str]): Unique IDs for the vectors/documents.
            embeddings (List[List[float]]): Embedding vectors.
            metadatas (Optional[List[Dict[str, Any]]]): Metadata for each vector/document.
            documents (Optional[List[str]]): Raw documents (optional).
        """
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

    def query(self, query_embeddings: List[List[float]], n_results: int = 5) -> Dict[str, Any]:
        """
        Query the collection for similar vectors.
        Args:
            query_embeddings (List[List[float]]): Embedding vectors to query.
            n_results (int): Number of results to return.
        Returns:
            Dict[str, Any]: Query results including ids, distances, metadatas, and documents.
        """
        return self.collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results
        )

    def delete(self, ids: List[str]):
        """
        Delete vectors/documents from the collection by IDs.
        Args:
            ids (List[str]): List of IDs to delete.
        """
        self.collection.delete(ids=ids)

    def list_collections(self) -> List[str]:
        """
        List all collection names in the database.
        Returns:
            List[str]: Collection names.
        """
        return [col.name for col in self.client.list_collections()]

    def get_collection(self, collection_name: str):
        """
        Switch to a different collection (creates if not exists).
        Args:
            collection_name (str): Name of the collection.
        """
        self.collection = self.client.get_or_create_collection(collection_name) 