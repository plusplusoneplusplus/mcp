"""Test cases for knowledge indexer tools."""

import pytest
import tempfile
import shutil
import os
import base64
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from plugins.knowledge_indexer.tool import (
    KnowledgeIndexerTool,
    KnowledgeQueryTool,
    KnowledgeCollectionManagerTool,
)


@pytest.fixture
def temp_vector_store():
    """Create a temporary directory for vector store testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_vector_store_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_markdown_content():
    """Sample markdown content for testing."""
    return """# Test Document

This is a test document for knowledge indexing.

## Section 1

Some content in section 1 with important information.

## Section 2

More content in section 2 with different topics.

### Subsection 2.1

Detailed information in a subsection.
"""


@pytest.fixture
def sample_files_data(sample_markdown_content):
    """Sample files data for testing."""
    return [
        {
            "filename": "test1.md",
            "content": sample_markdown_content,
            "encoding": "utf-8",
        },
        {
            "filename": "test2.md",
            "content": base64.b64encode(sample_markdown_content.encode()).decode(),
            "encoding": "base64",
        },
    ]


class TestKnowledgeIndexerTool:
    """Test cases for KnowledgeIndexerTool."""

    def test_tool_properties(self):
        """Test tool basic properties."""
        tool = KnowledgeIndexerTool()

        assert tool.name == "knowledge_indexer"
        assert "Upload and index new knowledge from files" in tool.description
        assert "files" in tool.input_schema["properties"]
        assert "collection" in tool.input_schema["properties"]
        assert "overwrite" in tool.input_schema["properties"]
        assert "persist_directory" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_execute_tool_no_files(self):
        """Test tool execution with no files."""
        tool = KnowledgeIndexerTool()

        result = await tool.execute_tool({"files": []})

        assert result["success"] is False
        assert "No files provided" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_tool_no_markdown_files(self):
        """Test tool execution with no markdown files."""
        tool = KnowledgeIndexerTool()

        files_data = [
            {
                "filename": "test.txt",
                "content": "This is a text file",
                "encoding": "utf-8",
            }
        ]

        result = await tool.execute_tool({"files": files_data})

        assert result["success"] is False
        assert "No markdown files found" in result["error"]

    @pytest.mark.asyncio
    @patch("plugins.knowledge_indexer.tool.ChromaVectorStore")
    @patch("plugins.knowledge_indexer.tool.MarkdownSegmenter")
    async def test_execute_tool_success(
        self,
        mock_segmenter_class,
        mock_store_class,
        sample_files_data,
        temp_vector_store,
    ):
        """Test successful tool execution."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        mock_segmenter = Mock()
        mock_segmenter_class.return_value = mock_segmenter
        mock_segmenter.segment_and_store.return_value = (5, {})  # 5 segments created

        # Create tool with temp directory
        tool = KnowledgeIndexerTool()
        tool.persist_dir = temp_vector_store

        result = await tool.execute_tool(
            {
                "files": sample_files_data,
                "collection": "test_collection",
                "overwrite": False,
            }
        )

        assert result["success"] is True
        assert result["collection"] == "test_collection"
        assert result["imported_files"] == 2
        assert result["total_segments"] == 10  # 5 segments per file
        assert len(result["processed_files"]) == 2

    @pytest.mark.asyncio
    @patch("plugins.knowledge_indexer.tool.ChromaVectorStore")
    async def test_execute_tool_with_overwrite(
        self, mock_store_class, sample_files_data
    ):
        """Test tool execution with overwrite option."""
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        tool = KnowledgeIndexerTool()

        with patch(
            "plugins.knowledge_indexer.tool.MarkdownSegmenter"
        ) as mock_segmenter_class:
            mock_segmenter = Mock()
            mock_segmenter_class.return_value = mock_segmenter
            mock_segmenter.segment_and_store.return_value = (3, {})

            result = await tool.execute_tool(
                {
                    "files": sample_files_data,
                    "collection": "test_collection",
                    "overwrite": True,
                }
            )

        # Verify that delete_collection was called
        mock_store.client.delete_collection.assert_called_once_with("test_collection")

    @pytest.mark.asyncio
    async def test_execute_tool_exception_handling(self, sample_files_data):
        """Test tool exception handling."""
        tool = KnowledgeIndexerTool()

        with patch(
            "plugins.knowledge_indexer.tool.ChromaVectorStore",
            side_effect=Exception("Test error"),
        ):
            result = await tool.execute_tool(
                {"files": sample_files_data, "collection": "test_collection"}
            )

        assert result["success"] is False
        assert ("Knowledge indexing failed" in result["error"] or "Processing failed" in result["error"])

    @pytest.mark.asyncio
    @patch("plugins.knowledge_indexer.tool.ChromaVectorStore")
    @patch("plugins.knowledge_indexer.tool.MarkdownSegmenter")
    async def test_execute_tool_custom_persist_directory(
        self,
        mock_segmenter_class,
        mock_store_class,
        sample_files_data,
        temp_vector_store,
    ):
        """Test tool execution with custom persist directory."""
        # Setup mocks
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        mock_segmenter = Mock()
        mock_segmenter_class.return_value = mock_segmenter
        mock_segmenter.segment_and_store.return_value = (3, {})

        tool = KnowledgeIndexerTool()
        custom_persist_dir = "/custom/persist/path"

        result = await tool.execute_tool(
            {
                "files": sample_files_data,
                "collection": "test_collection",
                "persist_directory": custom_persist_dir,
            }
        )

        # Verify that ChromaVectorStore was called with custom persist directory
        mock_store_class.assert_called_with(
            collection_name="test_collection", persist_directory=custom_persist_dir
        )

        assert result["success"] is True


class TestKnowledgeQueryTool:
    """Test cases for KnowledgeQueryTool."""

    def test_tool_properties(self):
        """Test tool basic properties."""
        tool = KnowledgeQueryTool()

        assert tool.name == "knowledge_query"
        assert "Search and retrieve relevant knowledge" in tool.description
        assert "query" in tool.input_schema["properties"]
        assert "collection" in tool.input_schema["properties"]
        assert "limit" in tool.input_schema["properties"]
        assert "persist_directory" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_execute_tool_no_query(self):
        """Test tool execution with no query."""
        tool = KnowledgeQueryTool()

        result = await tool.execute_tool({"collection": "test"})

        assert result["success"] is False
        assert "Query text is required" in result["error"]

    @pytest.mark.asyncio
    @patch("sentence_transformers.SentenceTransformer")
    @patch("plugins.knowledge_indexer.tool.ChromaVectorStore")
    async def test_execute_tool_success(self, mock_store_class, mock_transformer_class):
        """Test successful query execution."""
        # Setup mocks
        mock_embedder = Mock()
        mock_embedder.encode.return_value.tolist.return_value = [[0.1, 0.2, 0.3]]
        mock_transformer_class.return_value = mock_embedder

        mock_store = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [["meta1", "meta2"]],
            "distances": [[0.1, 0.2]],
        }
        mock_store.collection = mock_collection
        mock_store_class.return_value = mock_store

        tool = KnowledgeQueryTool()

        result = await tool.execute_tool(
            {"query": "test query", "collection": "test_collection", "limit": 5}
        )

        assert result["success"] is True
        assert result["query"] == "test query"
        assert result["collection"] == "test_collection"
        assert result["results"]["ids"] == ["id1", "id2"]
        assert result["results"]["documents"] == ["doc1", "doc2"]

    @pytest.mark.asyncio
    async def test_execute_tool_exception_handling(self):
        """Test query tool exception handling."""
        tool = KnowledgeQueryTool()

        with patch(
            "sentence_transformers.SentenceTransformer",
            side_effect=Exception("Test error"),
        ):
            result = await tool.execute_tool(
                {"query": "test query", "collection": "test_collection"}
            )

        assert result["success"] is False
        assert "Knowledge query failed" in result["error"]


class TestKnowledgeCollectionManagerTool:
    """Test cases for KnowledgeCollectionManagerTool."""

    def test_tool_properties(self):
        """Test tool basic properties."""
        tool = KnowledgeCollectionManagerTool()

        assert tool.name == "knowledge_collections"
        assert "Internal tool for managing knowledge collections" in tool.description
        assert "action" in tool.input_schema["properties"]
        assert "collection" in tool.input_schema["properties"]
        assert "persist_directory" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    @patch("plugins.knowledge_indexer.tool.ChromaVectorStore")
    async def test_list_collections(self, mock_store_class):
        """Test listing collections."""
        mock_store = Mock()
        mock_store.list_collections.return_value = ["collection1", "collection2"]
        mock_store_class.return_value = mock_store

        tool = KnowledgeCollectionManagerTool()

        result = await tool.execute_tool({"action": "list"})

        assert result["success"] is True
        assert result["action"] == "list"
        assert result["collections"] == ["collection1", "collection2"]

    @pytest.mark.asyncio
    @patch("plugins.knowledge_indexer.tool.ChromaVectorStore")
    async def test_delete_collection_success(self, mock_store_class):
        """Test successful collection deletion."""
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        tool = KnowledgeCollectionManagerTool()

        result = await tool.execute_tool(
            {"action": "delete", "collection": "test_collection"}
        )

        assert result["success"] is True
        assert result["action"] == "delete"
        assert result["collection"] == "test_collection"
        assert "deleted successfully" in result["message"]
        mock_store.client.delete_collection.assert_called_once_with("test_collection")

    @pytest.mark.asyncio
    async def test_delete_collection_no_name(self):
        """Test collection deletion without collection name."""
        tool = KnowledgeCollectionManagerTool()

        result = await tool.execute_tool({"action": "delete"})

        assert result["success"] is False
        assert "Collection name is required" in result["error"]

    @pytest.mark.asyncio
    @patch("plugins.knowledge_indexer.tool.ChromaVectorStore")
    async def test_collection_info(self, mock_store_class):
        """Test getting collection info."""
        # Setup mocks for collection info
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["id1", "id2", "id3"]],
            "documents": [["doc1", "doc2", "doc3"]],
            "metadatas": [["meta1", "meta2", "meta3"]],
            "distances": [[0.1, 0.2, 0.3]],
        }

        mock_store = Mock()
        mock_store.collection = mock_collection
        mock_store_class.return_value = mock_store

        tool = KnowledgeCollectionManagerTool()

        result = await tool.execute_tool(
            {"action": "info", "collection": "test_collection"}
        )

        assert result["success"] is True
        assert result["action"] == "info"
        assert result["collection"] == "test_collection"
        assert result["document_count"] == 3
        assert len(result["sample_documents"]) == 3

    @pytest.mark.asyncio
    async def test_collection_info_no_name(self):
        """Test getting collection info without collection name."""
        tool = KnowledgeCollectionManagerTool()

        result = await tool.execute_tool({"action": "info"})

        assert result["success"] is False
        assert "Collection name is required" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        """Test unknown action handling."""
        tool = KnowledgeCollectionManagerTool()

        result = await tool.execute_tool({"action": "unknown"})

        assert result["success"] is False
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test collection manager exception handling."""
        tool = KnowledgeCollectionManagerTool()

        with patch(
            "plugins.knowledge_indexer.tool.ChromaVectorStore",
            side_effect=Exception("Test error"),
        ):
            result = await tool.execute_tool({"action": "list"})

        assert result["success"] is False
        assert "Collection management failed" in result["error"]


class TestToolIntegration:
    """Integration tests for knowledge tools."""

    @pytest.mark.asyncio
    @patch("plugins.knowledge_indexer.tool.ChromaVectorStore")
    @patch("plugins.knowledge_indexer.tool.MarkdownSegmenter")
    @patch("sentence_transformers.SentenceTransformer")
    async def test_index_and_query_workflow(
        self,
        mock_transformer_class,
        mock_segmenter_class,
        mock_store_class,
        sample_files_data,
    ):
        """Test the complete workflow of indexing and querying."""
        # Setup mocks for indexing
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        mock_segmenter = Mock()
        mock_segmenter_class.return_value = mock_segmenter
        mock_segmenter.segment_and_store.return_value = (3, {})

        # Setup mocks for querying
        mock_embedder = Mock()
        mock_embedder.encode.return_value.tolist.return_value = [[0.1, 0.2, 0.3]]
        mock_transformer_class.return_value = mock_embedder

        mock_collection = Mock()
        mock_collection.query.return_value = {
            "ids": [["id1"]],
            "documents": [["Found document"]],
            "metadatas": [["metadata"]],
            "distances": [[0.1]],
        }
        mock_store.collection = mock_collection

        # Test indexing
        indexer = KnowledgeIndexerTool()
        index_result = await indexer.execute_tool(
            {"files": sample_files_data, "collection": "test_workflow"}
        )

        assert index_result["success"] is True

        # Test querying
        query_tool = KnowledgeQueryTool()
        query_result = await query_tool.execute_tool(
            {"query": "test query", "collection": "test_workflow"}
        )

        assert query_result["success"] is True
        assert query_result["results"]["documents"] == ["Found document"]

    def test_all_tools_implement_interface(self):
        """Test that all tools properly implement the ToolInterface."""
        from mcp_tools.interfaces import ToolInterface

        tools = [
            KnowledgeIndexerTool(),
            KnowledgeQueryTool(),
            KnowledgeCollectionManagerTool(),
        ]

        for tool in tools:
            assert isinstance(tool, ToolInterface)
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "input_schema")
            assert hasattr(tool, "execute_tool")

            # Test that properties return expected types
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)
            assert isinstance(tool.input_schema, dict)
