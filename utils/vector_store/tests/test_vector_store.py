import pytest
from utils.vector_store import ChromaVectorStore
import numpy as np
import tempfile
import shutil
from sentence_transformers import SentenceTransformer

# Use a lightweight model for embedding generation
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def test_init_and_collection_switch():
    store = ChromaVectorStore(collection_name="test_collection")
    assert store.collection.name == "test_collection"
    store.get_collection("another_collection")
    assert store.collection.name == "another_collection"


def test_add_and_query():
    store = ChromaVectorStore(collection_name="test_add_query")
    ids = ["id1", "id2"]
    documents = ["This is a test document about cats.", "Another document about dogs."]
    embeddings = EMBED_MODEL.encode(documents).tolist()
    metadatas = [{"label": "a"}, {"label": "b"}]
    store.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
    # Query with a similar sentence
    query = EMBED_MODEL.encode(["A text about cats."]).tolist()
    result = store.query(query_embeddings=query, n_results=2)
    assert "ids" in result
    assert len(result["ids"][0]) > 0


def test_query_with_metadata_filter():
    store = ChromaVectorStore(collection_name="test_metadata_query")
    ids = ["id1", "id2", "id3"]
    documents = [
        "Document about apples.",
        "Document about bananas.",
        "Document about apples and bananas.",
    ]
    metadatas = [{"fruit": "apple"}, {"fruit": "banana"}, {"fruit": "apple"}]
    embeddings = EMBED_MODEL.encode(documents).tolist()
    store.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
    # Query for 'apple' fruit only
    query = EMBED_MODEL.encode(["A text about apples."]).tolist()
    result = store.query(query_embeddings=query, n_results=3, where={"fruit": "apple"})
    # All returned metadatas should have fruit == 'apple'
    for meta in result["metadatas"][0]:
        assert meta["fruit"] == "apple"
    # Should not return the banana-only doc
    for doc in result["documents"][0]:
        assert "banana" not in doc or "apple" in doc


def test_delete():
    store = ChromaVectorStore(collection_name="test_delete")
    ids = ["id1", "id2"]
    documents = ["Delete test document one.", "Delete test document two."]
    embeddings = EMBED_MODEL.encode(documents).tolist()
    store.add(ids=ids, embeddings=embeddings)
    store.delete(ids=["id1"])
    query = EMBED_MODEL.encode([documents[1]]).tolist()
    result = store.query(query_embeddings=query, n_results=2)
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
        store1 = ChromaVectorStore(
            collection_name="persisted", persist_directory=temp_dir
        )
        ids = ["pid1", "pid2"]
        documents = ["Persistent doc one.", "Persistent doc two."]
        embeddings = EMBED_MODEL.encode(documents).tolist()
        store1.add(ids=ids, embeddings=embeddings)
        # Second instance: query data (should persist)
        store2 = ChromaVectorStore(
            collection_name="persisted", persist_directory=temp_dir
        )
        query = EMBED_MODEL.encode([documents[0]]).tolist()
        result = store2.query(query_embeddings=query, n_results=2)
        all_ids = [item for sublist in result["ids"] for item in sublist]
        assert "pid1" in all_ids or "pid2" in all_ids
    finally:
        shutil.rmtree(temp_dir)
