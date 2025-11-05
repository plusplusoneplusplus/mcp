"""
Knowledge management API package.

This package contains refactored knowledge management API endpoints,
organized into logical modules for better maintainability.
"""

# Import all endpoint functions to maintain backward compatibility
from .core import (
    api_import_knowledge,
    api_list_collections,
    api_list_documents,
    api_query_segments,
    api_delete_collection
)

from .sync import (
    api_knowledge_sync_status,
    api_knowledge_sync_trigger,
    api_knowledge_sync_folder
)

from .code_indexing import (
    api_code_indexing_ctags,
    api_code_indexing_tree_sitter
)

from .async_code_indexing import (
    api_code_indexing_async,
    api_code_indexing_status
)

from .code_viewer import (
    api_code_viewer_paths,
    api_code_viewer_classes,
    api_code_viewer_cleanup
)

from .tools import (
    get_knowledge_indexer,
    get_knowledge_query,
    get_knowledge_collections
)

__all__ = [
    # Core knowledge operations
    'api_import_knowledge',
    'api_list_collections',
    'api_list_documents',
    'api_query_segments',
    'api_delete_collection',

    # Knowledge sync operations
    'api_knowledge_sync_status',
    'api_knowledge_sync_trigger',
    'api_knowledge_sync_folder',

    # Code indexing operations
    'api_code_indexing_ctags',
    'api_code_indexing_tree_sitter',
    'api_code_indexing_async',
    'api_code_indexing_status',

    # Code viewer operations
    'api_code_viewer_paths',
    'api_code_viewer_classes',
    'api_code_viewer_cleanup',

    # Tool management
    'get_knowledge_indexer',
    'get_knowledge_query',
    'get_knowledge_collections'
]
