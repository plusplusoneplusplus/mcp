"""Knowledge indexing plugin for MCP."""

import os
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
import datetime

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool
from utils.vector_store.markdown_segmenter import MarkdownSegmenter
from utils.vector_store.vector_store import ChromaVectorStore
from config import env


@register_tool(os_type="all")
class KnowledgeIndexerTool(ToolInterface):
    """Tool for users to upload and index new knowledge from files into a vector store."""

    def __init__(self):
        super().__init__()
        # Use configuration manager to get vector store path
        self.persist_dir = env.get_vector_store_path()

    @property
    def name(self) -> str:
        return "knowledge_indexer"

    @property
    def description(self) -> str:
        return "Upload and index new knowledge from files (markdown format) into a vector store. This tool is intended for users to add new documents and knowledge bases that can later be searched and retrieved. Supports multiple file uploads and organizes content into searchable collections. Files with fewer than the configured line count threshold (default: 500 lines) are stored as single segments without chunking."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "content": {
                                "type": "string",
                                "description": "Base64 encoded file content or raw text content",
                            },
                            "encoding": {
                                "type": "string",
                                "enum": ["base64", "utf-8"],
                                "default": "utf-8",
                            },
                        },
                        "required": ["filename", "content"],
                    },
                    "description": "List of files to index",
                },
                "collection": {
                    "type": "string",
                    "default": "default",
                    "description": "Name of the collection to store the knowledge in",
                },
                "overwrite": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to overwrite existing collection",
                },
                "persist_directory": {
                    "type": "string",
                    "description": "Optional custom path for vector store persistence. If not provided, uses default server directory",
                },
                "line_count_threshold": {
                    "type": "integer",
                    "default": 500,
                    "minimum": 1,
                    "description": "Minimum number of lines before chunking is applied. Files with fewer lines are kept as single segments",
                },
            },
            "required": ["files"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the knowledge indexing tool."""
        try:
            files = arguments.get("files", [])
            collection = arguments.get("collection", "default")
            overwrite = arguments.get("overwrite", False)
            persist_directory = arguments.get("persist_directory", self.persist_dir)
            line_count_threshold = arguments.get("line_count_threshold", 500)

            if not files:
                return {"success": False, "error": "No files provided for indexing"}

            # Handle overwrite - delete collection if requested
            if overwrite:
                try:
                    store = ChromaVectorStore(persist_directory=persist_directory)
                    store.client.delete_collection(collection)
                except Exception:
                    # If collection doesn't exist, ignore
                    pass

            # Create temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix="knowledge_index_")

            try:
                # Process uploaded files
                filepaths = []
                for file_data in files:
                    filename = file_data.get("filename")
                    content = file_data.get("content")
                    encoding = file_data.get("encoding", "utf-8")

                    if not filename or not content:
                        continue

                    # Create file path in temp directory
                    dest_path = os.path.join(temp_dir, filename)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                    # Write content to file
                    if encoding == "base64":
                        import base64

                        decoded_content = base64.b64decode(content)
                        with open(dest_path, "wb") as f:
                            f.write(decoded_content)
                    else:
                        with open(dest_path, "w", encoding="utf-8") as f:
                            f.write(content)

                    filepaths.append(dest_path)

                # Filter for markdown files
                md_files = [f for f in filepaths if f.lower().endswith(".md")]

                if not md_files:
                    return {
                        "success": False,
                        "error": "No markdown files found in the provided files",
                    }

                # Initialize vector store and segmenter
                vector_store = ChromaVectorStore(
                    collection_name=collection, persist_directory=persist_directory
                )
                segmenter = MarkdownSegmenter(vector_store, line_count_threshold=line_count_threshold)

                # Process each markdown file
                total_segments = 0
                processed_files = []

                for md_path in md_files:
                    try:
                        with open(md_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Get file metadata
                        stat = os.stat(md_path)
                        file_name = os.path.basename(md_path)
                        rel_path = os.path.relpath(md_path, temp_dir)
                        file_size = stat.st_size
                        file_date = datetime.datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat()

                        # Segment and store
                        n_segments, _ = segmenter.segment_and_store(
                            content,
                            file_name=file_name,
                            rel_path=rel_path,
                            file_size=file_size,
                            file_date=file_date,
                        )

                        total_segments += n_segments
                        processed_files.append(
                            {
                                "filename": file_name,
                                "segments": n_segments,
                                "size": file_size,
                            }
                        )

                    except Exception as e:
                        # Log error but continue with other files
                        processed_files.append(
                            {"filename": os.path.basename(md_path), "error": str(e)}
                        )

                return {
                    "success": True,
                    "collection": collection,
                    "imported_files": len(
                        [f for f in processed_files if "error" not in f]
                    ),
                    "total_segments": total_segments,
                    "processed_files": processed_files,
                }

            except Exception as inner_e:
                # Handle any exceptions that occur during processing
                return {"success": False, "error": f"Processing failed: {str(inner_e)}"}
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            return {"success": False, "error": f"Knowledge indexing failed: {str(e)}"}


@register_tool(os_type="all")
class KnowledgeQueryTool(ToolInterface):
    """Tool for language models to query and retrieve indexed knowledge from the vector store."""

    def __init__(self):
        super().__init__()
        # Use configuration manager to get vector store path
        self.persist_dir = env.get_vector_store_path()

    @property
    def name(self) -> str:
        return "knowledge_query"

    @property
    def description(self) -> str:
        return "Search and retrieve relevant knowledge from indexed documents using semantic search. This tool is designed for language models to automatically find and access contextual information from the knowledge base to enhance responses and provide more informed answers."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query text"},
                "collection": {
                    "type": "string",
                    "default": "default",
                    "description": "Name of the collection to search in",
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                    "description": "Maximum number of results to return",
                },
                "persist_directory": {
                    "type": "string",
                    "description": "Optional custom path for vector store persistence. If not provided, uses default server directory",
                },
            },
            "required": ["query"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the knowledge query tool."""
        try:
            query_text = arguments.get("query")
            collection = arguments.get("collection", "default")
            limit = arguments.get("limit", 5)
            persist_directory = arguments.get("persist_directory", self.persist_dir)

            if not query_text:
                return {"success": False, "error": "Query text is required"}

            # Initialize embedder and vector store
            from sentence_transformers import SentenceTransformer

            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            query_vec = embedder.encode([query_text]).tolist()

            store = ChromaVectorStore(
                collection_name=collection, persist_directory=persist_directory
            )

            # Perform the query
            results = store.collection.query(
                query_embeddings=query_vec, n_results=limit
            )

            # Handle potential None results with safe defaults
            result_ids = results.get("ids") or [[]]
            result_documents = results.get("documents") or [[]]
            result_metadatas = results.get("metadatas") or [[]]
            result_distances = results.get("distances") or [[]]

            return {
                "success": True,
                "query": query_text,
                "collection": collection,
                "results": {
                    "ids": result_ids[0] if result_ids else [],
                    "documents": result_documents[0] if result_documents else [],
                    "metadatas": result_metadatas[0] if result_metadatas else [],
                    "distances": result_distances[0] if result_distances else [],
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Knowledge query failed: {str(e)}"}


@register_tool(os_type="all")
class KnowledgeCollectionManagerTool(ToolInterface):
    """Internal administrative tool for managing knowledge collections - not for general use."""

    def __init__(self):
        super().__init__()
        # Use configuration manager to get vector store path
        self.persist_dir = env.get_vector_store_path()

    @property
    def name(self) -> str:
        return "knowledge_collections"

    @property
    def description(self) -> str:
        return "Internal tool for managing knowledge collections (list, delete, get info). This tool is primarily for system administration and debugging purposes and should not be used in normal workflows. Use knowledge_indexer for adding content and knowledge_query for retrieving information."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "delete", "info"],
                    "description": "Action to perform on collections",
                },
                "collection": {
                    "type": "string",
                    "description": "Name of the collection (required for delete and info actions)",
                },
                "persist_directory": {
                    "type": "string",
                    "description": "Optional custom path for vector store persistence. If not provided, uses default server directory",
                },
            },
            "required": ["action"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the collection management tool."""
        try:
            action = arguments.get("action")
            collection = arguments.get("collection")
            persist_directory = arguments.get("persist_directory", self.persist_dir)

            store = ChromaVectorStore(persist_directory=persist_directory)

            if action == "list":
                collections = store.list_collections()
                return {"success": True, "action": "list", "collections": collections}

            elif action == "delete":
                if not collection:
                    return {
                        "success": False,
                        "error": "Collection name is required for delete action",
                    }

                try:
                    store.client.delete_collection(collection)
                    return {
                        "success": True,
                        "action": "delete",
                        "collection": collection,
                        "message": f"Collection '{collection}' deleted successfully",
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to delete collection '{collection}': {str(e)}",
                    }

            elif action == "info":
                if not collection:
                    return {
                        "success": False,
                        "error": "Collection name is required for info action",
                    }

                try:
                    # Get collection info by querying with dummy vector
                    collection_store = ChromaVectorStore(
                        collection_name=collection, persist_directory=persist_directory
                    )

                    # Use a zero-vector to get all documents (hack for ChromaDB)
                    # Fix: Use proper embedding dimension and format as List[List[float]]
                    dummy_vec = [[0.0] * 384]
                    results = collection_store.collection.query(
                        query_embeddings=dummy_vec, n_results=1000
                    )

                    # Handle potential None results with safe defaults
                    result_ids = results.get("ids") or [[]]
                    result_documents = results.get("documents") or [[]]

                    document_count = len(result_ids[0]) if result_ids else 0
                    sample_documents = result_documents[0][:5] if result_documents else []

                    return {
                        "success": True,
                        "action": "info",
                        "collection": collection,
                        "document_count": document_count,
                        "sample_documents": sample_documents,
                    }

                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to get info for collection '{collection}': {str(e)}",
                    }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {
                "success": False,
                "error": f"Collection management failed: {str(e)}",
            }
