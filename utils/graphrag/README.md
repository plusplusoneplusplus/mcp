# GraphRAG Utility

A comprehensive GraphRAG (Graph-based Retrieval-Augmented Generation) implementation for the MCP project, integrating Microsoft's GraphRAG library to build and query knowledge graphs from unstructured text.

## Overview

This utility enhances LLM capabilities by:
- Building knowledge graphs from unstructured documents
- Enabling sophisticated query patterns (global and local search)
- Providing structured responses with source attribution
- Supporting multiple storage backends and LLM providers

## Quick Start

> **Note**: This utility is currently under development. See [PLAN.md](./PLAN.md) for the complete implementation roadmap.

### Installation

The GraphRAG utility will be automatically available when you install the MCP project dependencies:

```bash
pip install -e .
```

### Basic Usage (Planned)

```python
from utils.graphrag import GraphRAGBuilder

# Initialize GraphRAG
builder = GraphRAGBuilder(config_path="config/graphrag.yaml")

# Index documents
result = await builder.index_documents([
    "docs/",
    "reports/annual_report.pdf"
])

# Query the knowledge graph
response = await builder.query(
    "What are the main themes in the documents?",
    search_type="global"
)

print(response.answer)
```

## Configuration

GraphRAG uses YAML configuration files following the project's patterns:

```yaml
graphrag:
  llm:
    provider: "openai"
    model: "gpt-4-turbo"
    api_key_env: "OPENAI_API_KEY"
  
  storage:
    type: "local"
    path: "./graphrag_data"
  
  indexing:
    chunk_size: 1200
    batch_size: 10
```

## Features

### Current Status: 🚧 Under Development

- [ ] **Core Infrastructure**: Configuration management, storage backends
- [ ] **Document Processing**: Multi-format support, batch processing
- [ ] **Query Engine**: Global/local search, response formatting
- [ ] **Advanced Features**: Cloud storage, monitoring, optimization

### Planned Features

- **Multiple Document Formats**: Text, Markdown, PDF, HTML support
- **Flexible Storage**: Local filesystem, Azure Blob, AWS S3, Google Cloud
- **Advanced Querying**: Global summaries, local entity search, hybrid approaches
- **Performance Optimization**: Parallel processing, caching, resumable indexing
- **Integration**: Seamless integration with existing MCP utilities

## Architecture

The GraphRAG utility is designed with modularity and extensibility in mind:

```
utils/graphrag/
├── graphrag_builder.py    # Main orchestrator
├── config.py             # Configuration management
├── indexer.py            # Document processing
├── query_engine.py       # Query interface
├── storage.py            # Storage backends
├── examples/             # Usage examples
└── tests/               # Test suite
```

## Development

See [PLAN.md](./PLAN.md) for the complete implementation plan, including:
- Detailed component specifications
- Implementation phases and timeline
- Testing strategy
- Performance considerations
- Security and privacy features

## Contributing

This utility follows the MCP project's contribution guidelines. Please see the main project's CONTRIBUTING.md for details.

## License

This utility is part of the MCP project and is licensed under the MIT License. 