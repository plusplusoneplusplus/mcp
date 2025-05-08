# Markdown Segmentation and Vector Storage Examples

This directory contains examples demonstrating how to segment markdown content and store it in a vector database for semantic retrieval.

## Files

- `table_segmentation_demo.py`: Demonstrates table extraction and storage
- `markdown_segmentation_demo.py`: Demonstrates comprehensive markdown segmentation (text and tables)
- `html_to_table_vectors.py`: Demonstrates a complete workflow from HTML to vector storage and search

## Usage

### Table Segmentation Demo

This script demonstrates table extraction using sample markdown content with an in-memory database:

```bash
python table_segmentation_demo.py
```

### Markdown Segmentation Demo

This script demonstrates comprehensive markdown segmentation (both text and tables):

```bash
python markdown_segmentation_demo.py
```

Features:
- Segments text into chunks with overlap
- Extracts and segments tables
- Splits large tables into smaller chunks
- Preserves heading context for each segment
- Stores all segments in a vector database
- Performs semantic search across all segment types

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

### Table Segmentation
1. **Table Extraction**: Tables are extracted from markdown using regex patterns
2. **Context Extraction**: Surrounding text and headings are extracted to provide context
3. **Vector Storage**: Tables and their embeddings are stored in ChromaDB

### Comprehensive Markdown Segmentation
1. **Text Chunking**: Text content is split into overlapping chunks
2. **Table Extraction**: Tables are identified and extracted
3. **Large Table Splitting**: Tables with many rows are split into smaller chunks
4. **Context Preservation**: Headings are associated with each segment
5. **Vector Storage**: All segments are stored with their embeddings
6. **Semantic Search**: Queries can retrieve both text and table segments

## Requirements

- sentence-transformers
- chromadb
- markdownify (for HTML conversion)
- beautifulsoup4 (for HTML parsing) 