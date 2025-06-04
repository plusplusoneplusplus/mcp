# Knowledge Indexer Plugin

This plugin provides tools for indexing knowledge from uploaded files into a vector store for semantic search and retrieval.

## Tools

### KnowledgeIndexerTool (`knowledge_indexer`)

Indexes knowledge from uploaded files into a vector store.

**Parameters:**
- `files` (array): List of files to index
  - `filename` (string): Name of the file
  - `content` (string): Base64 encoded file content or raw text content
  - `encoding` (string): Either "base64" or "utf-8" (default: "utf-8")
- `collection` (string): Name of the collection to store the knowledge in (default: "default")
- `overwrite` (boolean): Whether to overwrite existing collection (default: false)
- `persist_directory` (string, optional): Custom path for vector store persistence. If not provided, uses default server directory

**Returns:**
- `success` (boolean): Whether the operation was successful
- `collection` (string): Name of the collection used
- `imported_files` (number): Number of files successfully imported
- `total_segments` (number): Total number of segments created
- `processed_files` (array): Details about each processed file

### KnowledgeQueryTool (`knowledge_query`)

Queries indexed knowledge using semantic search.

**Parameters:**
- `query` (string): The search query text
- `collection` (string): Name of the collection to search in (default: "default")
- `limit` (integer): Maximum number of results to return (default: 5, max: 50)
- `persist_directory` (string, optional): Custom path for vector store persistence. If not provided, uses default server directory

**Returns:**
- `success` (boolean): Whether the operation was successful
- `query` (string): The original query text
- `collection` (string): Name of the collection searched
- `results` (object): Search results containing ids, documents, metadatas, and distances

### KnowledgeCollectionManagerTool (`knowledge_collections`)

Manages knowledge collections (list, delete, get info).

**Parameters:**
- `action` (string): Action to perform ("list", "delete", or "info")
- `collection` (string): Name of the collection (required for "delete" and "info" actions)
- `persist_directory` (string, optional): Custom path for vector store persistence. If not provided, uses default server directory

**Returns:**
- `success` (boolean): Whether the operation was successful
- `action` (string): The action that was performed
- Additional fields depending on the action:
  - For "list": `collections` (array) - list of collection names
  - For "delete": `message` (string) - confirmation message
  - For "info": `document_count` (number) and `sample_documents` (array)

## Usage

The tools are automatically registered when the plugin is imported. They can be used through the MCP server or directly through the API endpoints.

## File Support

Currently, the plugin only supports Markdown (.md) files for indexing. Files are segmented into chunks and stored in a ChromaDB vector store for efficient semantic search.

## Configuration

The plugin integrates with the MCP configuration system to determine the vector store persistence path. By default, it uses `server/.vector_store`, but this can be configured through:

1. **Environment Variable**: Set `VECTOR_STORE_PATH` in your environment
2. **Configuration File**: Add `VECTOR_STORE_PATH=.vector_store` to your `.env` file
3. **Runtime Override**: All tools support an optional `persist_directory` parameter to specify a custom location

The configuration manager automatically resolves relative paths to be relative to the server directory.

## Vector Store

The plugin uses ChromaDB as the vector store backend with the `all-MiniLM-L6-v2` sentence transformer model for generating embeddings. 