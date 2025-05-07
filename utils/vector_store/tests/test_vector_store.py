import pytest
from utils.vector_store import ChromaVectorStore
import numpy as np
import tempfile
import shutil
import os

def test_init_and_collection_switch():
    store = ChromaVectorStore(collection_name="test_collection")
    assert store.collection.name == "test_collection"
    store.get_collection("another_collection")
    assert store.collection.name == "another_collection"

def test_add_and_query():
    store = ChromaVectorStore(collection_name="test_add_query")
    ids = ["id1", "id2"]
    embeddings = [np.random.rand(3).tolist(), np.random.rand(3).tolist()]
    metadatas = [{"label": "a"}, {"label": "b"}]
    documents = ["doc a", "doc b"]
    store.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
    # Query with one of the embeddings
    result = store.query(query_embeddings=[embeddings[0]], n_results=2)
    assert "ids" in result
    assert len(result["ids"][0]) > 0

def test_delete():
    store = ChromaVectorStore(collection_name="test_delete")
    ids = ["id1", "id2"]
    embeddings = [np.random.rand(3).tolist(), np.random.rand(3).tolist()]
    store.add(ids=ids, embeddings=embeddings)
    store.delete(ids=["id1"])
    result = store.query(query_embeddings=[embeddings[1]], n_results=2)
    # Only id2 should remain
    all_ids = [item for sublist in result["ids"] for item in sublist]
    assert "id1" not in all_ids
    assert "id2" in all_ids

def test_list_collections():
    store = ChromaVectorStore(collection_name="test_list_collections")
    store.get_collection("another_collection")
    collections = store.list_collections()
    assert "test_list_collections" in collections
    assert "another_collection" in collections

def test_persistent_mode():
    # Create a temporary directory for persistence
    temp_dir = tempfile.mkdtemp()
    try:
        # First instance: add data
        store1 = ChromaVectorStore(collection_name="persisted", persist_directory=temp_dir)
        ids = ["pid1", "pid2"]
        embeddings = [np.random.rand(3).tolist(), np.random.rand(3).tolist()]
        store1.add(ids=ids, embeddings=embeddings)
        # Second instance: query data (should persist)
        store2 = ChromaVectorStore(collection_name="persisted", persist_directory=temp_dir)
        result = store2.query(query_embeddings=[embeddings[0]], n_results=2)
        all_ids = [item for sublist in result["ids"] for item in sublist]
        assert "pid1" in all_ids or "pid2" in all_ids
    finally:
        shutil.rmtree(temp_dir) 