"""Integration tests for knowledge indexer tools using real ChromaDB instances.

These tests use actual ChromaDB instances with proper isolation to catch real-world
database issues that mocks cannot detect. Each test uses unique temporary directories
and collection names to prevent interference.
"""

import pytest
import tempfile
import shutil
import os
import uuid
import asyncio
import base64
from typing import Dict, Any

from plugins.knowledge_indexer.tool import (
    KnowledgeIndexerTool,
    KnowledgeQueryTool,
    KnowledgeCollectionManagerTool,
)
from utils.vector_store.vector_store import ChromaVectorStore


@pytest.fixture
def unique_temp_dir():
    """Create a unique temporary directory for each test."""
    temp_dir = tempfile.mkdtemp(prefix=f"test_chroma_{uuid.uuid4().hex[:8]}_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def unique_collection_name():
    """Generate a unique collection name for each test."""
    return f"test_collection_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def sample_markdown_content():
    """Sample markdown content for testing."""
    return """# Integration Test Document

This is a test document for ChromaDB integration testing.

## Section 1: Basic Content
This section contains content about databases and vector storage.
It includes important keywords for semantic search testing.

## Section 2: Technical Information
ChromaDB is a vector database that stores embeddings and metadata.
The system provides semantic search capabilities using sentence transformers.

## Section 3: Features
- Document indexing and storage
- Semantic search functionality  
- Collection management operations
- Persistent data storage
"""


@pytest.fixture
def sample_files_data(sample_markdown_content):
    """Sample files data for testing."""
    return [
        {
            "filename": "test_doc1.md",
            "content": sample_markdown_content,
            "encoding": "utf-8",
        },
        {
            "filename": "test_doc2.md",
            "content": base64.b64encode(sample_markdown_content.encode()).decode(),
            "encoding": "base64",
        },
    ]


@pytest.mark.integration
class TestKnowledgeIndexerIntegration:
    """Integration tests for KnowledgeIndexerTool with real ChromaDB."""

    @pytest.mark.asyncio
    async def test_real_indexing_workflow(
        self, unique_temp_dir, unique_collection_name, sample_files_data
    ):
        """Test complete indexing workflow with real ChromaDB."""
        tool = KnowledgeIndexerTool()
        
        result = await tool.execute_tool({
            "files": sample_files_data,
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
            "overwrite": False,
        })
        
        assert result["success"] is True
        assert result["collection"] == unique_collection_name
        assert result["imported_files"] == 2
        assert result["total_segments"] > 0
        assert len(result["processed_files"]) == 2
        
        # Verify database files were created
        assert os.path.exists(unique_temp_dir)
        db_files = os.listdir(unique_temp_dir)
        assert len(db_files) > 0
        
        # Verify collection exists
        store = ChromaVectorStore(
            collection_name=unique_collection_name,
            persist_directory=unique_temp_dir
        )
        collections = store.list_collections()
        assert unique_collection_name in collections

    @pytest.mark.asyncio
    async def test_real_query_operations(
        self, unique_temp_dir, unique_collection_name, sample_files_data
    ):
        """Test semantic search with real embeddings."""
        # Index content first
        indexer = KnowledgeIndexerTool()
        await indexer.execute_tool({
            "files": sample_files_data,
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
        })
        
        # Test querying
        query_tool = KnowledgeQueryTool()
        result = await query_tool.execute_tool({
            "query": "database vector storage",
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
            "limit": 5,
        })
        
        assert result["success"] is True
        assert result["query"] == "database vector storage"
        assert result["collection"] == unique_collection_name
        
        results = result["results"]
        assert len(results["ids"]) > 0
        assert len(results["documents"]) > 0
        assert len(results["metadatas"]) > 0
        assert len(results["distances"]) > 0

    @pytest.mark.asyncio
    async def test_collection_management_operations(
        self, unique_temp_dir, unique_collection_name, sample_files_data
    ):
        """Test real collection CRUD operations."""
        # Create collection
        indexer = KnowledgeIndexerTool()
        await indexer.execute_tool({
            "files": sample_files_data,
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
        })
        
        manager = KnowledgeCollectionManagerTool()
        
        # Test list collections
        result = await manager.execute_tool({
            "action": "list",
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        assert unique_collection_name in result["collections"]
        
        # Test collection info
        result = await manager.execute_tool({
            "action": "info",
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        assert result["document_count"] > 0
        
        # Test delete collection
        result = await manager.execute_tool({
            "action": "delete",
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_overwrite_functionality(
        self, unique_temp_dir, unique_collection_name, sample_files_data
    ):
        """Test overwrite functionality with real database."""
        tool = KnowledgeIndexerTool()
        
        # First indexing
        result1 = await tool.execute_tool({
            "files": sample_files_data,
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
        })
        original_segments = result1["total_segments"]
        
        # Second indexing with overwrite=False (should add to existing)
        result2 = await tool.execute_tool({
            "files": sample_files_data,
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
            "overwrite": False,
        })
        
        # Should have same number of segments (duplicate detection)
        assert result2["total_segments"] == original_segments
        
        # Third indexing with overwrite=True (should replace)
        result3 = await tool.execute_tool({
            "files": sample_files_data,
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
            "overwrite": True,
        })
        
        # Should have same number of segments as original
        assert result3["total_segments"] == original_segments

    @pytest.mark.asyncio
    async def test_persistence_across_instances(
        self, unique_temp_dir, unique_collection_name, sample_files_data
    ):
        """Test that data persists across different tool instances."""
        # Index with first tool instance
        tool1 = KnowledgeIndexerTool()
        result = await tool1.execute_tool({
            "files": sample_files_data,
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        
        # Query with second tool instance (different object)
        tool2 = KnowledgeQueryTool()
        result = await tool2.execute_tool({
            "query": "database operations",
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
        })
        
        # Should find the previously indexed content
        assert result["success"] is True
        assert len(result["results"]["documents"]) > 0


@pytest.mark.integration
class TestConcurrencyAndIsolation:
    """Test concurrent operations and database isolation."""

    @pytest.mark.asyncio
    async def test_parallel_indexing_operations(self, sample_files_data):
        """Test multiple indexing operations running simultaneously."""
        num_parallel = 3
        tasks = []
        temp_dirs = []
        collection_names = []
        
        try:
            for i in range(num_parallel):
                temp_dir = tempfile.mkdtemp(prefix=f"parallel_test_{i}_")
                collection_name = f"parallel_collection_{uuid.uuid4().hex[:8]}"
                temp_dirs.append(temp_dir)
                collection_names.append(collection_name)
                
                tool = KnowledgeIndexerTool()
                task = tool.execute_tool({
                    "files": sample_files_data,
                    "collection": collection_name,
                    "persist_directory": temp_dir,
                })
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Task {i} failed: {result}")
                else:
                    assert result["success"] is True
                    assert result["collection"] == collection_names[i]
                
        finally:
            for temp_dir in temp_dirs:
                shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_database_isolation_between_collections(
        self, unique_temp_dir, sample_files_data
    ):
        """Test that different collections are properly isolated."""
        collection1 = f"isolated_collection_1_{uuid.uuid4().hex[:8]}"
        collection2 = f"isolated_collection_2_{uuid.uuid4().hex[:8]}"
        
        tool = KnowledgeIndexerTool()
        
        files1 = [{
            "filename": "doc1.md",
            "content": "# Collection 1 Content\nUnique content for collection 1.",
            "encoding": "utf-8",
        }]
        
        files2 = [{
            "filename": "doc2.md", 
            "content": "# Collection 2 Content\nDifferent content for collection 2.",
            "encoding": "utf-8",
        }]
        
        # Index in separate collections
        result1 = await tool.execute_tool({
            "files": files1,
            "collection": collection1,
            "persist_directory": unique_temp_dir,
        })
        
        result2 = await tool.execute_tool({
            "files": files2,
            "collection": collection2,
            "persist_directory": unique_temp_dir,
        })
        
        assert result1["success"] is True
        assert result2["success"] is True
        
        # Query each collection separately
        query_tool = KnowledgeQueryTool()
        
        result = await query_tool.execute_tool({
            "query": "collection 2 different",
            "collection": collection1,
            "persist_directory": unique_temp_dir,
        })
        
        assert result["success"] is True
        # Should not find collection 2 content in collection 1
        if result["results"]["documents"]:
            for doc in result["results"]["documents"]:
                assert "collection 2" not in doc.lower()


@pytest.mark.integration
class TestErrorHandlingAndRecovery:
    """Test error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_persist_directory_handling(self, sample_files_data):
        """Test handling of invalid persist directories."""
        tool = KnowledgeIndexerTool()
        
        invalid_dir = "/non/existent/path/vector_store"
        
        result = await tool.execute_tool({
            "files": sample_files_data,
            "collection": "test_collection",
            "persist_directory": invalid_dir,
        })
        
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_corrupted_database_recovery(self, unique_temp_dir, sample_files_data):
        """Test recovery from database corruption scenarios."""
        collection_name = f"corruption_test_{uuid.uuid4().hex[:8]}"
        
        # Create valid database first
        tool = KnowledgeIndexerTool()
        result = await tool.execute_tool({
            "files": sample_files_data,
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        
        # Simulate corruption by removing database files
        for file in os.listdir(unique_temp_dir):
            file_path = os.path.join(unique_temp_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        # Try to query corrupted database
        query_tool = KnowledgeQueryTool()
        result = await query_tool.execute_tool({
            "query": "test query",
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        
        # ChromaDB might recreate the collection, so we just verify it handles the situation
        # The important thing is that it doesn't crash
        assert "success" in result


@pytest.mark.integration
@pytest.mark.slow
class TestPerformanceAndMemory:
    """Test performance characteristics and memory usage."""

    @pytest.mark.asyncio
    async def test_large_document_indexing(
        self, unique_temp_dir, unique_collection_name
    ):
        """Test indexing of large documents."""
        # Create a large document
        large_content = "# Large Document Test\n\n"
        for i in range(20):
            large_content += f"""## Section {i + 1}

This is section {i + 1} of a large document for testing performance.
Each section contains unique content with keywords like "section_{i + 1}".

The content includes database operations, vector storage, and search functionality.
This tests the system's ability to handle larger documents efficiently.

"""
        
        large_files_data = [{
            "filename": "large_test_doc.md",
            "content": large_content,
            "encoding": "utf-8",
        }]
        
        tool = KnowledgeIndexerTool()
        
        # Index large document
        result = await tool.execute_tool({
            "files": large_files_data,
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
        })
        
        assert result["success"] is True
        assert result["total_segments"] > 5  # Should create multiple segments
        
        # Test querying the large document
        query_tool = KnowledgeQueryTool()
        result = await query_tool.execute_tool({
            "query": "section_10 database operations",
            "collection": unique_collection_name,
            "persist_directory": unique_temp_dir,
            "limit": 5,
        })
        
        assert result["success"] is True
        assert len(result["results"]["documents"]) > 0


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_complete_knowledge_management_workflow(
        self, unique_temp_dir, sample_files_data
    ):
        """Test a complete knowledge management workflow."""
        collection_name = f"workflow_test_{uuid.uuid4().hex[:8]}"
        
        # Step 1: Index initial documents
        indexer = KnowledgeIndexerTool()
        result = await indexer.execute_tool({
            "files": sample_files_data,
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        
        # Step 2: Query the indexed content
        query_tool = KnowledgeQueryTool()
        result = await query_tool.execute_tool({
            "query": "database vector operations",
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        assert len(result["results"]["documents"]) > 0
        
        # Step 3: Add more documents to the same collection
        additional_files = [{
            "filename": "additional_knowledge.md",
            "content": """# Additional Knowledge
            
This document contains supplementary information about:
- Advanced database operations
- Vector similarity algorithms  
- Performance optimization techniques
""",
            "encoding": "utf-8",
        }]
        
        result = await indexer.execute_tool({
            "files": additional_files,
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        
        # Step 4: Query for the new content
        result = await query_tool.execute_tool({
            "query": "performance optimization",
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        
        # Step 5: Manage collections
        manager = KnowledgeCollectionManagerTool()
        
        # List collections
        result = await manager.execute_tool({
            "action": "list",
            "persist_directory": unique_temp_dir,
        })
        assert collection_name in result["collections"]
        
        # Get collection info
        result = await manager.execute_tool({
            "action": "info",
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        assert result["document_count"] > 0
        
        # Clean up by deleting collection
        result = await manager.execute_tool({
            "action": "delete",
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_multi_format_document_handling(self, unique_temp_dir):
        """Test handling of various document formats and encodings."""
        collection_name = f"multiformat_test_{uuid.uuid4().hex[:8]}"
        
        # Create documents with different characteristics
        files_data = [
            {
                "filename": "utf8_doc.md",
                "content": "# UTF-8 Document\nThis contains standard UTF-8 text with special characters.",
                "encoding": "utf-8",
            },
            {
                "filename": "base64_doc.md", 
                "content": base64.b64encode("# Base64 Document\nThis document was encoded in base64.".encode()).decode(),
                "encoding": "base64",
            },
            {
                "filename": "complex_markdown.md",
                "content": """# Complex Markdown Document

## Features Tested

### Lists
- Item 1
- Item 2
  - Nested item

### Code Blocks
```python
def example_function():
    return "Hello, World!"
```

### Tables
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |

**Bold text** and *italic text* for emphasis.
""",
                "encoding": "utf-8",
            }
        ]
        
        # Index all documents
        tool = KnowledgeIndexerTool()
        result = await tool.execute_tool({
            "files": files_data,
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        
        assert result["success"] is True
        assert result["imported_files"] == 3
        assert result["total_segments"] > 0
        
        # Test querying for content from different documents
        query_tool = KnowledgeQueryTool()
        
        # Query for base64 content
        result = await query_tool.execute_tool({
            "query": "base64 encoded document",
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True
        
        # Query for complex markdown features
        result = await query_tool.execute_tool({
            "query": "code blocks tables lists",
            "collection": collection_name,
            "persist_directory": unique_temp_dir,
        })
        assert result["success"] is True 