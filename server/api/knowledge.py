"""
Knowledge management API endpoints.

This module provides backward compatibility by importing all refactored
knowledge management API endpoints from the knowledge package.
"""

# Import all functions from the refactored knowledge package
from .knowledge import (
    # Core knowledge operations
    api_import_knowledge,
    api_list_collections,
    api_list_documents,
    api_query_segments,
    api_delete_collection,

    # Knowledge sync operations
    api_knowledge_sync_status,
    api_knowledge_sync_trigger,
    api_knowledge_sync_folder,

    # Code indexing operations
    api_code_indexing_ctags,
    api_code_indexing_tree_sitter,
    api_code_indexing_async,
    api_code_indexing_status,

    # Code viewer operations
    api_code_viewer_paths,
    api_code_viewer_classes,
    api_code_viewer_cleanup,

    # Tool management (for backward compatibility)
    get_knowledge_indexer,
    get_knowledge_query,
    get_knowledge_collections
)
