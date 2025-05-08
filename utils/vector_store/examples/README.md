# Markdown Table Segmentation and Vector Storage Examples

This directory contains examples demonstrating how to segment markdown tables and store them in a vector database for semantic retrieval.

## Files

- `table_segmentation_demo.py`: Demonstrates the basic functionality using sample markdown content
- `html_to_table_vectors.py`: Demonstrates a complete workflow from HTML to vector storage and search

## Usage

### Table Segmentation Demo

This script demonstrates the basic functionality using sample markdown content with an in-memory database:

```bash
python table_segmentation_demo.py
```

### HTML to Table Vectors

This script demonstrates a complete workflow:

```bash
python html_to_table_vectors.py path/to/your/file.html
```

Optional arguments:
- `--persist-dir`: Directory to persist the vector database (default: in-memory)
- `--collection`: Name of the collection in the vector database (default: "html_tables")

Example with in-memory database (default):
```bash
python html_to_table_vectors.py example.html
```

Example with persistent database:
```bash
python html_to_table_vectors.py example.html --persist-dir ./vector_db --collection financial_tables
```

## How It Works

1. **HTML Conversion**: HTML content is converted to markdown format
2. **Table Extraction**: Tables are extracted from markdown using regex patterns
3. **Context Extraction**: Surrounding text and headings are extracted to provide context
4. **Embedding Generation**: Embeddings are created for each table using sentence transformers
5. **Vector Storage**: Tables and their embeddings are stored in ChromaDB (in-memory by default)
6. **Semantic Search**: Queries are converted to embeddings and used to find relevant tables

## Requirements

- sentence-transformers
- chromadb
- markdownify (for HTML conversion)
- beautifulsoup4 (for HTML parsing) 