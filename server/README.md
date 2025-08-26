# MCP Server Knowledge

## Overview

The MCP (Model Context Protocol) Server is a comprehensive web-based application that provides a unified interface for knowledge management, tool execution, data processing, and system administration. Built with Starlette/FastAPI and using modern web technologies, it serves as a bridge between various AI tools, data sources, and user interfaces.

## Architecture

### Core Components

```
server/
├── main.py                 # Server entry point and application setup
├── api/                    # REST API endpoints
├── templates/              # HTML templates with Jinja2
├── static/                 # Static assets (CSS, JS, images)
├── tests/                  # Test suite
└── Supporting modules      # Utilities and processors
```

### Technology Stack

- **Backend**: Python 3.11+, Starlette ASGI framework
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), Jinja2 templates
- **APIs**: RESTful APIs with JSON responses
- **Real-time**: Server-Sent Events (SSE) for live updates
- **Data**: ChromaDB for vector storage, in-memory DataFrames
- **Visualization**: Mermaid.js for diagrams, Chart.js for analytics

## Main Application (main.py)

### Server Initialization

The main server performs these startup operations:

1. **Startup Tracing**: Performance monitoring and timing analysis
2. **Tool Discovery**: Automatic discovery and registration of MCP tools
3. **Dependency Resolution**: Dependency injection container setup
4. **Route Configuration**: API and web route registration
5. **Static File Serving**: CSS, JS, and asset serving
6. **Template Engine**: Jinja2 template rendering setup

### Key Features

- **MCP Server Integration**: Full Model Context Protocol support
- **Plugin System**: Dynamic tool loading from YAML and Python modules
- **Performance Monitoring**: Detailed startup timing and operation metrics
- **Configuration Management**: Environment-based configuration with hot reloading

### Route Structure

```python
routes = [
    # Core pages
    Route("/", endpoint=index),                    # Landing page
    Route("/knowledge", endpoint=knowledge),       # Knowledge management
    Route("/jobs", endpoint=jobs),                # Background job monitoring
    Route("/dataframes", endpoint=dataframes),    # Data management
    Route("/tools", endpoint=tools_page),         # Tool interface
    Route("/config", endpoint=config_page),       # Configuration management

    # API routes (150+ endpoints)
    Mount("/api", routes=api_routes),

    # Static assets
    Mount("/static", app=StaticFiles(directory="server/static")),
]
```

## API Architecture (api/)

### Module Organization

The API is organized into specialized modules, each handling specific domain functionality:

#### Knowledge Management (`knowledge.py`)
- **Collections**: Create, list, delete knowledge collections
- **Document Import**: Multi-format document ingestion (MD, TXT, PDF, DOCX)
- **Semantic Search**: Vector-based document querying
- **Knowledge Sync**: Automated folder synchronization
- **Code Indexing**: CTags and Tree-sitter code analysis
- **Code Viewer**: Class definition browsing and UML visualization

**Key Endpoints:**
```
POST /api/import-knowledge        # Import documents
GET  /api/collections            # List collections
GET  /api/query-segments         # Semantic search
POST /api/knowledge-sync/trigger # Sync folders
POST /api/code-indexing/ctags    # Generate code tags
GET  /api/code-viewer/paths      # List indexed code paths
```

#### Background Jobs (`background_jobs.py`)
- **Job Management**: Create, monitor, terminate background tasks
- **Status Tracking**: Real-time job status and progress updates
- **Resource Monitoring**: Memory and CPU usage tracking
- **History Management**: Job execution history and analytics

**Key Endpoints:**
```
GET  /api/background-jobs           # List active jobs
GET  /api/background-jobs/{token}   # Job details
POST /api/background-jobs/{token}/terminate # Kill job
GET  /api/background-jobs/stats     # System statistics
```

#### Data Management (`dataframes.py`)
- **DataFrame Storage**: In-memory data structure management
- **Data Operations**: Filtering, sorting, aggregation, transformations
- **Import/Export**: CSV, JSON, Excel file handling
- **Query Processing**: SQL-like operations on DataFrames
- **Visualization**: Chart generation from data

**Key Endpoints:**
```
GET  /api/dataframes            # List all DataFrames
POST /api/dataframes/upload     # Upload data file
GET  /api/dataframes/{id}/data  # Get DataFrame content
POST /api/dataframes/{id}/execute # Execute operation
```

#### Tools (`tools.py`)
- **Tool Registry**: Dynamic tool discovery and registration
- **Execution Engine**: Safe tool execution with parameter validation
- **Category Management**: Tool organization and filtering
- **Usage Analytics**: Tool usage statistics and performance metrics

**Key Endpoints:**
```
GET  /api/tools                 # List available tools
POST /api/tools/{name}/execute  # Execute tool
GET  /api/tools/categories      # Tool categories
GET  /api/tools/stats          # Usage statistics
```

#### Configuration (`configuration.py`)
- **Environment Management**: .env file editing and validation
- **Settings API**: Dynamic configuration updates
- **Backup/Restore**: Configuration backup and rollback
- **Validation**: Configuration syntax and dependency checking

#### Tool History (`tool_history.py`)
- **Execution Tracking**: Detailed tool execution logs
- **Performance Metrics**: Response times, success rates
- **Audit Trail**: User action tracking and compliance
- **Export Functionality**: History data export in various formats

#### Visualizations (`visualizations.py`)
- **Task Dependencies**: Interactive dependency graphs
- **Gantt Charts**: Timeline visualization
- **Resource Allocation**: System resource usage charts
- **Execution Timelines**: Process flow visualization

#### Python Evaluation (`pyeval.py`)
- **Code Execution**: Safe Python code execution
- **Variable Inspection**: Runtime state examination
- **Output Capture**: Stdout/stderr capturing and formatting
- **Security**: Sandboxed execution environment

### Common API Patterns

#### Response Format
```json
{
    "success": true,
    "data": { /* response data */ },
    "error": null,
    "timestamp": "2025-01-01T00:00:00Z"
}
```

#### Error Handling
```json
{
    "success": false,
    "data": null,
    "error": "Detailed error message",
    "error_code": "SPECIFIC_ERROR_CODE"
}
```

#### Pagination
```json
{
    "success": true,
    "data": { /* paginated results */ },
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 150,
        "pages": 8
    }
}
```

## Frontend Templates (templates/)

### Base Template (`base.html`)

The foundational template providing:

- **Responsive Layout**: Mobile-first design with flexbox
- **Navigation**: Persistent navigation bar with active state management
- **Styling**: Comprehensive CSS framework with custom properties
- **JavaScript**: Shared utilities and modal management
- **Component System**: Reusable UI components (modals, toasts, progress bars)

#### CSS Architecture
```css
/* Component-based styling */
.navbar { /* Navigation styles */ }
.card { /* Content container styles */ }
.modal { /* Modal dialog styles */ }
.toast { /* Notification styles */ }
.progress-container { /* Progress indicator styles */ }
.data-table { /* Data table styles */ }
```

#### JavaScript Utilities
```javascript
// Modal management
function showModal(modalId)
function hideModal(modalId)

// Status display
function showStatus(elementId, message, isError)
function clearStatus(elementId)

// Loading indicators
function showLoading()
function hideLoading()
```

### Knowledge Management (`knowledge.html`)

Advanced knowledge management interface with tabbed navigation:

#### Tab Structure
1. **Import**: Folder-based document import with file filtering
2. **List**: Collection browsing and document viewing
3. **Query**: Semantic search with relevance scoring
4. **Collections**: Collection management and deletion
5. **Sync**: Automated folder synchronization
6. **Code Indexing**: Source code analysis and indexing
7. **Code Viewer**: Class browsing with UML visualization

#### Key Features
- **File Upload**: Drag-and-drop folder selection with preview
- **Real-time Search**: Instant search with highlight and scoring
- **Document Viewer**: Syntax-highlighted document display
- **Metadata Display**: Document properties and indexing information
- **Progress Tracking**: Import/sync progress with detailed feedback

#### Code Viewer Integration
- **Path Selection**: Visual selection of indexed code repositories
- **Class Search**: Real-time class definition search
- **UML Generation**: Dynamic UML diagram creation
- **Member Expansion**: Collapsible method/property lists
- **Cross-Reference**: File and line number navigation

### Data Management (`dataframes.html`)

Comprehensive data analysis interface:

#### Features
- **Data Grid**: Sortable, filterable data table with pagination
- **Statistics Panel**: Real-time statistics and summary metrics
- **Operation Builder**: Visual query builder with drag-and-drop
- **Chart Generation**: Interactive chart creation from data
- **Export Options**: Multiple format export (CSV, JSON, Excel)
- **Memory Monitoring**: Real-time memory usage tracking

### Tool Management (`tools.html`)

Interactive tool execution environment:

#### Components
- **Tool Browser**: Categorized tool listing with search
- **Parameter Forms**: Dynamic form generation from tool schemas
- **Execution Panel**: Real-time execution status and output
- **History Viewer**: Tool usage history and performance metrics
- **Favorites System**: Bookmarking frequently used tools

### Background Jobs (`jobs.html`)

Real-time job monitoring interface:

#### Features
- **Job List**: Live updating job status with progress bars
- **Resource Monitor**: CPU, memory, and I/O usage graphs
- **Log Viewer**: Real-time log streaming with filtering
- **Control Panel**: Start, stop, restart job controls
- **Analytics Dashboard**: Historical performance metrics

### Configuration (`config.html`)

System configuration interface:

#### Sections
- **Environment Variables**: .env file editor with validation
- **Tool Settings**: Tool-specific configuration options
- **System Settings**: Server configuration and limits
- **Backup Management**: Configuration backup and restore
- **Validation Tools**: Configuration syntax checking

## Supporting Modules

### Tool Result Processor (`tool_result_processor.py`)

Handles the processing and formatting of tool execution results:

```python
def process_tool_result(result: Any) -> List[Union[TextContent, ImageContent]]
def format_result_as_text(result: dict) -> str
```

**Capabilities:**
- Multi-format result processing (text, JSON, binary)
- Image content detection and encoding
- Error message formatting and sanitization
- Content type negotiation

### Prompts System (`prompts.py`)

Dynamic prompt management for AI interactions:

```python
def load_prompts_from_yaml() -> dict
def convert_yaml_to_prompts(yaml_prompts: dict) -> dict
def get_prompt(name: str, arguments: dict) -> GetPromptResult
```

**Features:**
- YAML-based prompt definitions
- Dynamic argument substitution
- Prompt categorization and organization
- Version control and rollback

### Startup Tracer (`startup_tracer.py`)

Performance monitoring and optimization:

```python
def time_operation(operation_name: str)
def trace_startup_time()
def log_startup_summary()
def save_startup_report()
```

**Metrics Collected:**
- Operation timing and dependencies
- Memory usage patterns
- I/O performance statistics
- Bottleneck identification

## Key Features Deep Dive

### Knowledge Management System

The knowledge system provides comprehensive document management:

1. **Multi-Format Support**: MD, TXT, RST, DOCX, PDF processing
2. **Vector Search**: ChromaDB integration for semantic similarity
3. **Collection Management**: Organized document grouping
4. **Metadata Extraction**: Automatic metadata parsing and indexing
5. **Sync Services**: Automated folder monitoring and updates

### Code Analysis and Visualization

Advanced code understanding capabilities:

1. **CTags Integration**: Universal CTags for symbol extraction
2. **Tree-sitter Parsing**: Advanced syntax tree analysis
3. **UML Generation**: Automatic class diagram creation
4. **Cross-referencing**: Symbol definition and usage tracking
5. **Multi-language Support**: C++, Python, JavaScript, Java, etc.

### Real-time Processing

Live data processing and monitoring:

1. **Server-Sent Events**: Real-time UI updates
2. **Background Jobs**: Asynchronous task processing
3. **Progress Tracking**: Detailed operation progress
4. **Resource Monitoring**: System performance tracking
5. **Error Recovery**: Automatic retry and fallback mechanisms

### Security and Safety

Comprehensive security measures:

1. **Input Validation**: Strict parameter validation and sanitization
2. **Sandboxed Execution**: Isolated tool execution environments
3. **Resource Limits**: CPU, memory, and time constraints
4. **Audit Logging**: Comprehensive action logging
5. **Configuration Validation**: Safe configuration management

## API Usage Examples

### Knowledge Import
```bash
curl -X POST http://localhost:8000/api/import-knowledge \
  -F "files=@document.md" \
  -F "collection=my_docs"
```

### Semantic Search
```bash
curl "http://localhost:8000/api/query-segments?collection=my_docs&query=python%20functions&limit=5"
```

### Tool Execution
```bash
curl -X POST http://localhost:8000/api/tools/file_reader/execute \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/path/to/file.txt"}'
```

### DataFrame Operations
```bash
curl -X POST http://localhost:8000/api/dataframes/df_123/execute \
  -H "Content-Type: application/json" \
  -d '{"operation": "filter", "column": "age", "condition": "> 25"}'
```

## Development and Testing

### Test Structure

```
tests/
├── test_server_launch.py          # Server startup tests
├── test_mcp_client_connection.py  # MCP protocol tests
├── test_background_jobs_api.py    # Job management tests
├── test_dataframes_api.py         # Data processing tests
├── test_tools_api.py              # Tool execution tests
└── conftest.py                    # Test configuration
```

### Test Coverage Areas

1. **API Endpoints**: Comprehensive endpoint testing
2. **MCP Integration**: Protocol compliance verification
3. **Tool Execution**: Safe execution environment testing
4. **Data Processing**: DataFrame operation validation
5. **Configuration**: Settings management testing

### Performance Considerations

1. **Startup Optimization**: Sub-second server startup
2. **Memory Management**: Efficient DataFrame handling
3. **Concurrent Processing**: Multi-threaded tool execution
4. **Caching Strategies**: Intelligent result caching
5. **Resource Monitoring**: Proactive resource management

## Integration Points

### MCP Protocol

Full Model Context Protocol implementation:

- **Tool Registration**: Dynamic tool discovery and registration
- **Resource Management**: Efficient resource allocation and cleanup
- **Transport Layer**: SSE-based real-time communication
- **Error Handling**: Robust error propagation and recovery

### External Services

Integration with external systems:

- **ChromaDB**: Vector database for semantic search
- **Neo4j**: Graph database for relationship analysis
- **File Systems**: Local and remote file system access
- **APIs**: REST API integration for external data sources

### Plugin Architecture

Extensible plugin system:

- **YAML Tools**: Declarative tool definitions
- **Python Plugins**: Programmatic tool implementation
- **Dynamic Loading**: Runtime plugin discovery and loading
- **Dependency Management**: Automatic dependency resolution

## Deployment and Configuration

### Environment Setup

Required environment variables:

```bash
# Core configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
MCP_LOG_LEVEL=INFO

# Knowledge management
KNOWLEDGE_SYNC_ENABLED=true
CHROMA_DB_PATH=./data/chroma

# Tool configuration
TOOL_TIMEOUT=300
MAX_CONCURRENT_JOBS=10
```

### Service Management

The server supports various deployment modes:

1. **Development**: Direct Python execution with hot reloading
2. **Production**: Uvicorn ASGI server with process management
3. **Container**: Docker containerization with volume mounts
4. **Service**: System service integration with auto-restart

### Monitoring and Logging

Comprehensive observability:

1. **Structured Logging**: JSON-formatted logs with correlation IDs
2. **Performance Metrics**: Detailed timing and resource usage
3. **Health Checks**: Automated health monitoring endpoints
4. **Error Tracking**: Comprehensive error capture and reporting
5. **Usage Analytics**: Tool usage and system performance analytics

This knowledge index provides a comprehensive overview of the MCP Server architecture, functionality, and usage patterns. The server serves as a powerful platform for AI tool integration, knowledge management, and data processing workflows.
