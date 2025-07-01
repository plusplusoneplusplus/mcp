# Utilities Overview

This document provides a high-level overview of the utilities available in the `utils` directory. Each section describes the functionality and usage of a utility module. For detailed API documentation, refer to the code comments and docstrings.

---

## Chart Extractor (`chart_extractor`)

**Functionality:**
- Extracts individual chart images from dashboard screenshots using computer vision techniques.
- Detects chart boundaries, merges overlapping regions, and optionally uses adaptive detection to include chart labels and axes.

**Usage:**
- Main function: `extract_charts(image_path, output_dir, ...)`
- Input: Path to a dashboard screenshot image.
- Output: Saves cropped chart images to the specified directory.
- Useful for automating the extraction of visual data from dashboards for further analysis.

---

## HTML to Markdown (`html_to_markdown`)

**Functionality:**
- Converts raw HTML content into Markdown format.
- Supports extraction using either BeautifulSoup or Trafilatura, with configurable options for including links and images.

**Usage:**
- Main function: `html_to_markdown(html, include_links=True, include_images=True)`
- Input: HTML string.
- Output: Markdown-formatted string.
- Useful for cleaning and standardizing web content for downstream processing or storage.

---

## Markdown to HTML (`markdown_to_html`)

**Functionality:**
- Converts Markdown content to HTML format using the fast Mistune parser.
- Automatically detects if content is markdown and converts only when needed.
- Supports all standard markdown features: headers, lists, code blocks, tables, links, etc.

**Usage:**
- Main functions:
  - `markdown_to_html(markdown_text)` - Direct conversion
  - `detect_and_convert_markdown(text)` - Smart detection and conversion
  - `is_markdown_content(text)` - Detection only
- Input: Markdown or plain text string.
- Output: HTML-formatted string (or original text if not markdown).
- Used by the Azure DevOps work item tool to automatically convert markdown descriptions to HTML.

---

## OCR Extractor (`ocr_extractor`)

**Functionality:**
- Extracts text from image files using EasyOCR.
- Designed for quick extraction of visible text from screenshots, scans, or photographs.

**Usage:**
- Main function: `extract_text_from_image(image_path)`
- Input: Path to an image file.
- Output: List of extracted text strings.
- Useful for digitizing printed or handwritten content.

---

## Secret Scanner (`secret_scanner`)

**Functionality:**
- Scans text content for hard-coded secrets such as passwords, API keys, and tokens.
- Uses both pattern-based and entropy-based detection, leveraging the `detect-secrets` library and custom logic.
- Can redact detected secrets from the content.

**Usage:**
- Main functions: `check_secrets(raw_content)`, `redact_secrets(content)`
- Input: String content to scan.
- Output: List of findings (for scanning) or redacted content (for redaction).
- Useful for auditing code, logs, or documents for sensitive information.

---

## Vector Store (`vector_store`)

**Functionality:**
- Provides a wrapper around ChromaDB for storing, querying, and managing vector embeddings and associated metadata.
- Supports persistent or in-memory storage and collection management.

**Usage:**
- Interface: `VectorStore`
- Default implementation: `ChromaVectorStore`
    - `add(ids, embeddings, metadatas, documents)` to store data
    - `query(query_embeddings, n_results, where)` to retrieve similar vectors
    - `delete(ids)` to remove vectors
    - `list_collections()` and `get_collection(collection_name)` for management
- Useful for semantic search, document retrieval, and AI/ML applications.

---

## LLM Clients (`llm_clients`)

**Functionality:**
- Async wrappers for interacting with LLM backends.
- Includes clients for OpenAI and the local Ollama server.

**Usage:**
- `OpenAIClient(api_key, base_url, default_model)` for OpenAI or Azure OpenAI APIs.
- `OllamaClient(base_url, default_model)` for local models via the Ollama service.
- Useful for integrating chat completion features into tools and plugins.

---

For more details, see the source code and inline documentation in each utility folder.
