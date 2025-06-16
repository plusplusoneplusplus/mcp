#!/usr/bin/env python3
"""
Test cases for the embedding service module.

This module provides comprehensive test coverage for:
1. EmbeddingInterface abstract base class
2. SentenceTransformerEmbedding implementation
3. OpenAIEmbedding implementation
4. Factory functions
5. Integration with existing segmenters
6. Error handling and edge cases
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from utils.vector_store.embedding_service import (
    EmbeddingInterface,
    SentenceTransformerEmbedding,
    OpenAIEmbedding,
    EmbeddingServiceFactory,
    create_default_embedding_service
)
from utils.vector_store.markdown_segmenter import MarkdownSegmenter
from utils.vector_store.markdown_table_segmenter import MarkdownTableSegmenter
from utils.vector_store.vector_store import ChromaVectorStore


class TestEmbeddingInterface(unittest.TestCase):
    """Test cases for the EmbeddingInterface abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that EmbeddingInterface cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            EmbeddingInterface()

    def test_abstract_methods_exist(self):
        """Test that abstract methods are properly defined."""
        # Check that the abstract methods exist
        self.assertTrue(hasattr(EmbeddingInterface, 'encode'))
        self.assertTrue(hasattr(EmbeddingInterface, 'model_name'))
        self.assertTrue(hasattr(EmbeddingInterface, 'dimension'))


class TestSentenceTransformerEmbedding(unittest.TestCase):
    """Test cases for SentenceTransformerEmbedding."""

    def setUp(self):
        """Set up test fixtures."""
        self.embedding_service = SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")

    def test_initialization(self):
        """Test proper initialization of SentenceTransformerEmbedding."""
        self.assertIsNotNone(self.embedding_service._model)
        self.assertEqual(self.embedding_service.model_name, "all-MiniLM-L6-v2")
        self.assertIsInstance(self.embedding_service.dimension, int)
        self.assertGreater(self.embedding_service.dimension, 0)

    def test_encode_single_text(self):
        """Test encoding a single text string."""
        text = "This is a test sentence."
        embedding = self.embedding_service.encode(text)

        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), self.embedding_service.dimension)
        self.assertTrue(all(isinstance(x, (float, int)) for x in embedding))

    def test_encode_multiple_texts(self):
        """Test encoding multiple text strings."""
        texts = ["First sentence.", "Second sentence.", "Third sentence."]
        embeddings = self.embedding_service.encode(texts)

        self.assertIsInstance(embeddings, list)
        self.assertEqual(len(embeddings), 3)
        for embedding in embeddings:
            self.assertIsInstance(embedding, list)
            self.assertEqual(len(embedding), self.embedding_service.dimension)
            self.assertTrue(all(isinstance(x, (float, int)) for x in embedding))

    def test_encode_empty_string(self):
        """Test encoding an empty string."""
        embedding = self.embedding_service.encode("")

        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), self.embedding_service.dimension)

    def test_encode_empty_list(self):
        """Test encoding an empty list."""
        embeddings = self.embedding_service.encode([])

        self.assertIsInstance(embeddings, list)
        self.assertEqual(len(embeddings), 0)

    def test_fallback_model_initialization(self):
        """Test that fallback models are defined."""
        # Test that fallback models are properly configured
        embedding_service = SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")

        # Should have fallback models defined
        self.assertIsInstance(embedding_service._fallback_models, list)
        self.assertGreater(len(embedding_service._fallback_models), 0)

        # Should be able to encode text
        embedding = embedding_service.encode("test")
        self.assertIsInstance(embedding, list)
        self.assertGreater(len(embedding), 0)


class TestOpenAIEmbedding(unittest.TestCase):
    """Test cases for OpenAIEmbedding."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_key = "test-api-key"

    def test_initialization_with_api_key(self):
        """Test initialization with API key."""
        with patch('builtins.__import__') as mock_import:
            mock_openai = Mock()
            mock_import.return_value = mock_openai

            embedding_service = OpenAIEmbedding(api_key=self.api_key)

            self.assertEqual(embedding_service.model_name, "text-embedding-3-small")
            self.assertEqual(embedding_service.dimension, 1536)

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'env-api-key'})
    def test_initialization_with_env_api_key(self):
        """Test initialization with API key from environment."""
        with patch('builtins.__import__') as mock_import:
            mock_openai = Mock()
            mock_import.return_value = mock_openai

            embedding_service = OpenAIEmbedding()

            self.assertEqual(embedding_service.model_name, "text-embedding-3-small")

    def test_encode_single_text(self):
        """Test encoding a single text with OpenAI."""
        with patch('builtins.__import__') as mock_import:
            mock_openai = Mock()
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]

            mock_client.embeddings.create.return_value = mock_response
            mock_openai.OpenAI.return_value = mock_client
            mock_import.return_value = mock_openai

            embedding_service = OpenAIEmbedding(api_key=self.api_key)
            embedding = embedding_service.encode("test text")

            self.assertEqual(embedding, [0.1, 0.2, 0.3])

    def test_encode_multiple_texts(self):
        """Test encoding multiple texts with OpenAI."""
        with patch('builtins.__import__') as mock_import:
            mock_openai = Mock()
            mock_client = Mock()
            mock_response = Mock()
            mock_response.data = [
                Mock(embedding=[0.1, 0.2, 0.3]),
                Mock(embedding=[0.4, 0.5, 0.6])
            ]

            mock_client.embeddings.create.return_value = mock_response
            mock_openai.OpenAI.return_value = mock_client
            mock_import.return_value = mock_openai

            embedding_service = OpenAIEmbedding(api_key=self.api_key)
            embeddings = embedding_service.encode(["text1", "text2"])

            self.assertEqual(embeddings, [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

    def test_encode_error_handling(self):
        """Test error handling during encoding."""
        with patch('builtins.__import__') as mock_import:
            mock_openai = Mock()
            mock_client = Mock()
            mock_client.embeddings.create.side_effect = Exception("API Error")
            mock_openai.OpenAI.return_value = mock_client
            mock_import.return_value = mock_openai

            embedding_service = OpenAIEmbedding(api_key=self.api_key)

            with self.assertRaises(Exception):
                embedding_service.encode("test text")


class TestEmbeddingServiceFactory(unittest.TestCase):
    """Test cases for EmbeddingServiceFactory."""

    def test_create_sentence_transformers_service(self):
        """Test creating SentenceTransformers service via factory."""
        service = EmbeddingServiceFactory.create_embedding_service(
            provider="sentence_transformers",
            model_name="all-MiniLM-L6-v2"
        )

        self.assertIsInstance(service, SentenceTransformerEmbedding)
        self.assertEqual(service.model_name, "all-MiniLM-L6-v2")

    def test_create_openai_service(self):
        """Test creating OpenAI service via factory."""
        with patch('builtins.__import__') as mock_import:
            mock_openai = Mock()
            mock_import.return_value = mock_openai

            service = EmbeddingServiceFactory.create_embedding_service(
                provider="openai",
                api_key="test-key"
            )

            self.assertIsInstance(service, OpenAIEmbedding)

    def test_create_invalid_provider(self):
        """Test creating service with invalid provider."""
        with self.assertRaises(ValueError):
            EmbeddingServiceFactory.create_embedding_service(provider="invalid_provider")

    def test_create_default_embedding_service(self):
        """Test creating default embedding service."""
        service = create_default_embedding_service()

        self.assertIsInstance(service, SentenceTransformerEmbedding)
        self.assertEqual(service.model_name, "all-MiniLM-L6-v2")


class TestEmbeddingServiceIntegration(unittest.TestCase):
    """Test cases for embedding service integration with existing components."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_collection_name = "test_embedding_integration"
        self.vector_store = ChromaVectorStore(
            collection_name=self.test_collection_name,
            persist_directory=None,  # In-memory
        )

    def tearDown(self):
        """Clean up after tests."""
        try:
            if hasattr(self.vector_store, "client") and self.vector_store.client:
                self.vector_store.client.delete_collection(
                    name=self.test_collection_name
                )
        except Exception:
            pass

    def test_markdown_segmenter_backward_compatibility(self):
        """Test that MarkdownSegmenter maintains backward compatibility."""
        # Old API should still work
        segmenter = MarkdownSegmenter(
            vector_store=self.vector_store,
            model_name="all-MiniLM-L6-v2",
            chunk_size=200,
            chunk_overlap=50
        )

        # Should have both old and new interfaces
        self.assertIsNotNone(segmenter.model)
        self.assertIsNotNone(segmenter.embedding_service)
        self.assertIsInstance(segmenter.embedding_service, SentenceTransformerEmbedding)

        # Should work with markdown processing
        markdown = "# Test\nThis is a test document."
        segments = segmenter.segment_markdown(markdown)
        self.assertGreater(len(segments), 0)

    def test_markdown_segmenter_new_api(self):
        """Test MarkdownSegmenter with new embedding service API."""
        embedding_service = SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")

        segmenter = MarkdownSegmenter(
            vector_store=self.vector_store,
            embedding_service=embedding_service,
            chunk_size=200,
            chunk_overlap=50
        )

        # Should use the provided embedding service
        self.assertIs(segmenter.embedding_service, embedding_service)

        # Should work with markdown processing
        markdown = "# Test\nThis is a test document with new API."
        segments = segmenter.segment_markdown(markdown)
        self.assertGreater(len(segments), 0)

    def test_markdown_table_segmenter_integration(self):
        """Test MarkdownTableSegmenter with embedding service."""
        embedding_service = SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")

        table_segmenter = MarkdownTableSegmenter(
            vector_store=self.vector_store,
            embedding_service=embedding_service
        )

        # Should use the provided embedding service
        self.assertIs(table_segmenter.embedding_service, embedding_service)

        # Test with table content
        markdown_with_table = """
# Test Table

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
"""
        count, ids = table_segmenter.segment_and_store(markdown_with_table)
        self.assertGreater(count, 0)
        self.assertGreater(len(ids), 0)

    def test_embedding_consistency_between_apis(self):
        """Test that embeddings are consistent between old and new APIs."""
        # Create segmenters with both APIs
        segmenter_old = MarkdownSegmenter(
            vector_store=ChromaVectorStore("test_old", persist_directory=None),
            model_name="all-MiniLM-L6-v2"
        )

        embedding_service = SentenceTransformerEmbedding(model_name="all-MiniLM-L6-v2")
        segmenter_new = MarkdownSegmenter(
            vector_store=ChromaVectorStore("test_new", persist_directory=None),
            embedding_service=embedding_service
        )

        # Test same text produces similar embeddings
        test_text = "This is a test sentence for embedding comparison."

        embedding_old = segmenter_old.embedding_service.encode(test_text)
        embedding_new = segmenter_new.embedding_service.encode(test_text)

        # Both should be lists of floats with same dimension
        self.assertIsInstance(embedding_old, list)
        self.assertIsInstance(embedding_new, list)
        self.assertEqual(len(embedding_old), len(embedding_new))

        # Embeddings should be very similar (using same model)
        import numpy as np
        similarity = np.dot(embedding_old, embedding_new) / (
            np.linalg.norm(embedding_old) * np.linalg.norm(embedding_new)
        )
        self.assertGreater(similarity, 0.99)  # Should be nearly identical

    def test_mock_embedding_service(self):
        """Test using a mock embedding service for testing purposes."""
        class MockEmbeddingService(EmbeddingInterface):
            @property
            def model_name(self):
                return "mock-model"

            @property
            def dimension(self):
                return 384

            def encode(self, texts):
                if isinstance(texts, str):
                    return [0.1] * 384
                else:
                    return [[0.1] * 384 for _ in texts]

        mock_service = MockEmbeddingService()

        segmenter = MarkdownSegmenter(
            vector_store=self.vector_store,
            embedding_service=mock_service
        )

        # Should use the mock service
        self.assertIs(segmenter.embedding_service, mock_service)

        # Should work with deterministic embeddings
        markdown = "# Test\nMock embedding test."
        segments = segmenter.segment_markdown(markdown)
        self.assertGreater(len(segments), 0)


if __name__ == "__main__":
    unittest.main()
