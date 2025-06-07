# Chunking and Reference Strategy

## Overview
Implement a system that breaks large MCP tool outputs into manageable chunks, stores them in the existing vector store infrastructure, and returns references that allow selective retrieval and querying of specific content sections.

## Goals
- Handle arbitrarily large outputs without context window limitations
- Enable semantic search and retrieval of specific content sections
- Integrate seamlessly with existing vector store and segmentation systems
- Provide efficient storage and retrieval of large outputs
- Allow progressive content exploration and analysis

## Current Infrastructure Analysis

### Existing Vector Store Capabilities
Your codebase already has:
- **ChromaVectorStore**: Vector database with persistence
- **MarkdownSegmenter**: Intelligent text chunking with overlap
- **Segmentation Workflow**: File processing and storage pipeline
- **Search Functionality**: Semantic search across stored content

### Integration Points
- `utils/vector_store/vector_store.py` - Core vector operations
- `utils/vector_store/markdown_segmenter.py` - Text chunking logic
- `utils/segmenter/workflow.py` - Processing workflows
- `server/templates/index.html` - Search UI components

## Identified Gaps

### 1. **Real-time Output Processing**
**Current**: Designed for file-based markdown processing
**Needed**: Stream processing of tool outputs as they're generated

### 2. **Output-Specific Metadata**
**Current**: Document-centric metadata (headings, file info)
**Needed**: Tool execution context (command, timestamp, tool name, execution ID)

### 3. **Temporary vs Persistent Storage**
**Current**: Assumes long-term document storage
**Needed**: Configurable retention policies for tool outputs

### 4. **Reference Resolution System**
**Current**: Direct content retrieval
**Needed**: Chunk reference IDs and lazy loading mechanisms

### 5. **Cross-Output Relationships**
**Current**: Independent document processing
**Needed**: Link related tool executions and their outputs

## Architecture Design

### Core Components

#### 1. Output Chunk Manager
```python
class OutputChunkManager:
    def __init__(self, vector_store: ChromaVectorStore, segmenter: MarkdownSegmenter)
    def store_output(self, output: str, context: ExecutionContext) -> ChunkReference
    def retrieve_chunk(self, chunk_id: str) -> ChunkContent
    def search_chunks(self, query: str, execution_id: str = None) -> List[ChunkMatch]
    def cleanup_expired(self, retention_policy: RetentionPolicy) -> None
```

#### 2. Execution Context
```python
@dataclass
class ExecutionContext:
    execution_id: str
    tool_name: str
    command: str
    timestamp: datetime
    user_id: str
    session_id: str
    retention_days: int = 7
```

#### 3. Chunk Reference System
```python
@dataclass
class ChunkReference:
    execution_id: str
    chunk_ids: List[str]
    total_chunks: int
    original_size: int
    summary: str
    searchable: bool = True

@dataclass
class ChunkContent:
    chunk_id: str
    content: str
    position: int
    metadata: Dict[str, Any]
```

### Storage Schema Extensions

#### Enhanced Metadata Structure
```python
chunk_metadata = {
    # Existing fields
    "type": "tool_output",
    "heading": "",
    "position": 0,

    # New fields for tool outputs
    "execution_id": "exec_123",
    "tool_name": "command_executor",
    "command": "ls -la /large/directory",
    "timestamp": "2024-01-15T10:30:00Z",
    "chunk_index": 0,
    "total_chunks": 5,
    "original_size": 150000,
    "retention_until": "2024-01-22T10:30:00Z"
}
```

#### Collection Strategy
- **Separate Collections**: Tool outputs in dedicated collections
- **Namespaced IDs**: Prefix chunk IDs with execution context
- **Retention Metadata**: Automatic cleanup based on policies

## Implementation Plan

### Phase 1: Core Integration (Week 1-2)
1. **Extend MarkdownSegmenter**
   - Add tool output processing mode
   - Support for non-markdown content (logs, JSON, etc.)
   - Configurable chunking strategies

2. **Create OutputChunkManager**
   - Wrapper around existing vector store
   - Tool output specific metadata handling
   - Reference generation and resolution

3. **Integrate with CommandExecutor**
   - Detect large outputs automatically
   - Store chunks and return references
   - Maintain backward compatibility

### Phase 2: Enhanced Features (Week 3-4)
1. **Search and Retrieval**
   - Semantic search within tool outputs
   - Cross-execution search capabilities
   - Filtered search by tool/time/user

2. **Reference Resolution API**
   - REST endpoints for chunk retrieval
   - Batch chunk loading
   - Progressive content loading

3. **Retention Management**
   - Configurable retention policies
   - Automatic cleanup processes
   - Storage usage monitoring

### Phase 3: Advanced Capabilities (Week 5-6)
1. **Content Analysis**
   - Automatic content type detection
   - Structured data extraction
   - Error/warning indexing

2. **Relationship Mapping**
   - Link related executions
   - Command dependency tracking
   - Session-based grouping

## Technical Implementation

### Modified Segmentation Workflow
```python
class ToolOutputProcessor:
    def process_tool_output(self, output: str, context: ExecutionContext) -> ChunkReference:
        # 1. Determine if chunking is needed
        if len(output) < self.chunk_threshold:
            return self._store_single_chunk(output, context)

        # 2. Apply appropriate segmentation strategy
        segments = self._segment_output(output, context)

        # 3. Store chunks with enhanced metadata
        chunk_ids = self._store_chunks(segments, context)

        # 4. Generate summary and reference
        return self._create_reference(chunk_ids, context, output)
```

### Integration with Existing Tools
```python
# In CommandExecutor
def execute(self, command: str, **kwargs) -> Dict[str, Any]:
    result = self._execute_command(command)

    # Check if output should be chunked
    if self._should_chunk_output(result["output"]):
        chunk_ref = self.chunk_manager.store_output(
            result["output"],
            ExecutionContext(
                tool_name="command_executor",
                command=command,
                # ... other context
            )
        )
        result["output"] = chunk_ref.summary
        result["chunks"] = chunk_ref
        result["chunked"] = True

    return result
```

### API Extensions
```python
# New endpoints for chunk management
@app.get("/api/chunks/{chunk_id}")
async def get_chunk(chunk_id: str) -> ChunkContent:
    pass

@app.post("/api/chunks/search")
async def search_chunks(query: SearchQuery) -> List[ChunkMatch]:
    pass

@app.get("/api/executions/{execution_id}/chunks")
async def get_execution_chunks(execution_id: str) -> List[ChunkReference]:
    pass
```

## Benefits
- **Unlimited Output Size**: No more context window constraints
- **Semantic Search**: Find specific information in large outputs
- **Efficient Storage**: Leverage existing vector store infrastructure
- **Progressive Loading**: Load only needed content sections
- **Historical Analysis**: Search across past tool executions

## Challenges & Solutions

### 1. **Performance Impact**
**Challenge**: Vector operations add latency
**Solution**: Async processing, caching, size thresholds

### 2. **Storage Growth**
**Challenge**: Large outputs consume significant storage
**Solution**: Retention policies, compression, cleanup automation

### 3. **Reference Complexity**
**Challenge**: Users need to understand chunk references
**Solution**: Transparent fallback, clear UI, progressive disclosure

### 4. **Search Quality**
**Challenge**: Tool outputs may not be semantically rich
**Solution**: Content preprocessing, metadata enhancement, hybrid search

## Success Metrics
- Successful processing of outputs >100KB without errors
- Search relevance scores for tool output queries
- Storage efficiency (compression ratios, cleanup effectiveness)
- User adoption of chunk-based exploration features
- Performance impact on tool execution times

## Future Enhancements
- **Cross-tool Analysis**: Correlate outputs from different tools
- **Temporal Queries**: Search outputs by time ranges
- **Collaborative Features**: Share chunk references between users
- **Export Capabilities**: Reconstruct full outputs from chunks
