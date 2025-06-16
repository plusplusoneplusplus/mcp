"""Embedding service for generating semantic vectors from text."""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Union
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingInterface(ABC):
    """Abstract interface for embedding services."""

    @abstractmethod
    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for input text(s).

        Args:
            texts: Single text string or list of text strings

        Returns:
            Single embedding vector or list of embedding vectors
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name/identifier of the embedding model."""
        pass


class SentenceTransformerEmbedding(EmbeddingInterface):
    """Embedding service using SentenceTransformers models."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
        fallback_models: Optional[List[str]] = None
    ):
        """
        Initialize the SentenceTransformer embedding service.

        Args:
            model_name: Name of the SentenceTransformer model
            device: Device to run the model on ('cpu', 'cuda', etc.)
            fallback_models: List of fallback models to try if primary fails
        """
        self._model_name = model_name
        self._device = device
        self._fallback_models = fallback_models or [
            "all-mpnet-base-v2",
            "all-MiniLM-L12-v2",
            "paraphrase-MiniLM-L6-v2"
        ]
        self._model = self._initialize_model()
        self._dimension = self._get_dimension()

    def _initialize_model(self):
        """Initialize the SentenceTransformer model with fallback support."""
        from sentence_transformers import SentenceTransformer

        # Try to load the primary model
        try:
            logger.info(f"Attempting to load primary model: {self._model_name}")
            model = SentenceTransformer(self._model_name, device=self._device)
            logger.info(f"Successfully loaded model: {self._model_name}")
            return model
        except ValueError as e:
            if "Unrecognized model" in str(e):
                logger.warning(f"Failed to load primary model {self._model_name}: {e}")
                return self._try_fallback_models()
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error loading model {self._model_name}: {e}")
            raise

    def _try_fallback_models(self):
        """Try loading fallback models."""
        from sentence_transformers import SentenceTransformer

        for fallback_model in self._fallback_models:
            try:
                logger.info(f"Attempting fallback model: {fallback_model}")
                model = SentenceTransformer(fallback_model, device=self._device)
                logger.warning(f"Successfully loaded fallback model: {fallback_model}")
                self._model_name = fallback_model  # Update the model name
                return model
            except Exception as fallback_error:
                logger.warning(f"Fallback model {fallback_model} also failed: {fallback_error}")
                continue

        # If all fallback models fail, raise an error
        raise RuntimeError(
            f"Failed to load primary model '{self._model_name}' and all fallback models. "
            f"This may be due to a compatibility issue between sentence-transformers and transformers libraries. "
            f"Tried fallback models: {self._fallback_models}"
        )

    def _get_dimension(self) -> int:
        """Get the embedding dimension from the model."""
        try:
            # Get dimension from model configuration
            dimension = self._model.get_sentence_embedding_dimension()
            return dimension if dimension is not None else self._fallback_dimension()
        except Exception:
            return self._fallback_dimension()

    def _fallback_dimension(self) -> int:
        """Fallback method to get dimension by encoding dummy text."""
        dummy_embedding = self._model.encode("test")
        return len(dummy_embedding)

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for input text(s).

        Args:
            texts: Single text string or list of text strings

        Returns:
            Single embedding vector or list of embedding vectors
        """
        if isinstance(texts, str):
            # Single text
            embedding = self._model.encode(texts)
            return embedding.tolist()
        else:
            # List of texts
            embeddings = self._model.encode(texts)
            return embeddings.tolist()

    @property
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return the name of the embedding model."""
        return self._model_name


class OpenAIEmbedding(EmbeddingInterface):
    """Embedding service using OpenAI's embedding API."""

    def __init__(
        self,
        model_name: str = "text-embedding-3-small",
        api_key: Optional[str] = None
    ):
        """
        Initialize the OpenAI embedding service.

        Args:
            model_name: Name of the OpenAI embedding model
            api_key: OpenAI API key (if None, will use environment variable)
        """
        self._model_name = model_name
        self._api_key = api_key
        self._client = self._initialize_client()
        self._dimension = self._get_dimension()

    def _initialize_client(self):
        """Initialize the OpenAI client."""
        try:
            import openai
            if self._api_key:
                return openai.OpenAI(api_key=self._api_key)
            else:
                return openai.OpenAI()  # Will use OPENAI_API_KEY env var
        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")

    def _get_dimension(self) -> int:
        """Get the embedding dimension for the model."""
        # Known dimensions for OpenAI models
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dimensions.get(self._model_name, 1536)  # Default to 1536

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for input text(s).

        Args:
            texts: Single text string or list of text strings

        Returns:
            Single embedding vector or list of embedding vectors
        """
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False

        try:
            response = self._client.embeddings.create(
                model=self._model_name,
                input=texts
            )

            embeddings = [data.embedding for data in response.data]

            if single_text:
                return embeddings[0]
            else:
                return embeddings

        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings: {e}")
            raise

    @property
    def dimension(self) -> int:
        """Return the dimension of the embedding vectors."""
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return the name of the embedding model."""
        return self._model_name


class EmbeddingServiceFactory:
    """Factory for creating embedding services."""

    @staticmethod
    def create_embedding_service(
        provider: str = "sentence_transformers",
        model_name: Optional[str] = None,
        **kwargs
    ) -> EmbeddingInterface:
        """
        Create an embedding service instance.

        Args:
            provider: The embedding provider ('sentence_transformers', 'openai')
            model_name: Name of the model to use
            **kwargs: Additional arguments for the embedding service

        Returns:
            EmbeddingInterface: An embedding service instance
        """
        if provider.lower() == "sentence_transformers":
            model_name = model_name or "all-MiniLM-L6-v2"
            return SentenceTransformerEmbedding(model_name=model_name, **kwargs)

        elif provider.lower() == "openai":
            model_name = model_name or "text-embedding-3-small"
            return OpenAIEmbedding(model_name=model_name, **kwargs)

        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")


# Convenience function for backward compatibility
def create_default_embedding_service(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingInterface:
    """Create a default SentenceTransformer embedding service."""
    return SentenceTransformerEmbedding(model_name=model_name)
