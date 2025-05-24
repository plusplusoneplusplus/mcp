"""GraphRAG utility for building and querying knowledge graphs.

This module provides a comprehensive GraphRAG implementation that integrates
Microsoft's GraphRAG library with the MCP project's existing utilities.
"""

from utils.graphrag.config import (
    GraphRAGConfig,
    LLMConfig,
    EmbeddingConfig,
    ConfigLoader,
    load_config,
)

__all__ = [
    "GraphRAGConfig",
    "LLMConfig", 
    "EmbeddingConfig",
    "ConfigLoader",
    "load_config",
]

__version__ = "0.1.0" 