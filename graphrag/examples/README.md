# GraphRAG Examples

This directory contains examples demonstrating how to use Microsoft's GraphRAG package for building and querying knowledge graphs.

## Basic Example

The `basic_example.py` file provides a complete, runnable example that shows:

1. **Document Indexing**: How to process documents and build a knowledge graph
2. **Global Search**: How to perform high-level queries across the entire knowledge graph
3. **Local Search**: How to search for specific entities and relationships

### Prerequisites

1. **Install GraphRAG**: Make sure you have Microsoft's GraphRAG package installed:
   ```bash
   pip install graphrag
   ```

2. **API Keys**: You'll need an OpenAI API key for both LLM and embedding services.

### Quick Start

1. **Configure API Keys**: Edit the configuration in `basic_example.py`:
   ```python
   self.config = {
       "llm": {
           "api_key": "your-actual-openai-api-key-here",
           # ... other settings
       },
       "embeddings": {
           "api_key": "your-actual-openai-api-key-here", 
           # ... other settings
       }
   }
   ```

2. **Run the Example**:
   ```bash
   cd utils/graphrag/examples
   python basic_example.py
   ```

### What the Example Does

1. **Initializes GraphRAG** with basic configuration
2. **Indexes sample documents** about AI, climate change, and digital transformation
3. **Performs a global search** to find main themes across all documents
4. **Performs a local search** to find specific information about AI and ML

### Expected Output

```
🚀 Basic GraphRAG Example
==================================================
📊 Initializing GraphRAG...
📚 Indexing documents...
Starting document indexing...
Indexing completed successfully!
✅ Documents indexed successfully!

🌍 Performing global search...
Query: What are the main themes and topics discussed in the documents?
Response: [GraphRAG will provide a comprehensive summary of themes]

🔍 Performing local search...
Query: Tell me about artificial intelligence and machine learning
Response: [GraphRAG will provide specific information about AI/ML]

✨ Example completed!
```

## Configuration

### Using Environment Variables

Instead of hardcoding API keys, you can use environment variables:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Then modify the code to use:
```python
import os
"api_key": os.getenv("OPENAI_API_KEY")
```

### Using Configuration Files

You can also use the `config_template.yaml` file:

1. Copy `config_template.yaml` to `config.yaml`
2. Fill in your API keys and customize settings
3. Load the config in your code:

```python
import yaml

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
```

## Understanding GraphRAG

### Global vs Local Search

- **Global Search**: Analyzes the entire knowledge graph to provide comprehensive, high-level insights
- **Local Search**: Focuses on specific entities and their relationships for detailed information

### Key Components

1. **Indexing Pipeline**: Processes documents, extracts entities/relationships, builds communities
2. **Knowledge Graph**: Stores entities, relationships, and community structures
3. **Search Engines**: Provide different query capabilities (global/local)

## Customization

### Adding Your Own Documents

Replace the sample documents with your own:

```python
my_documents = [
    "Path/to/your/document1.txt",
    "Path/to/your/document2.pdf",  # Note: PDF support may require additional setup
    # Or direct text content:
    "Your document content here..."
]

await graphrag.index_documents(my_documents)
```

### Advanced Configuration

You can customize many aspects of GraphRAG:

- **Chunk sizes**: Adjust how documents are split
- **LLM models**: Use different OpenAI models or other providers
- **Community detection**: Tune how entities are grouped
- **Search parameters**: Adjust token limits and search behavior

## Troubleshooting

### Common Issues

1. **API Key Errors**: Make sure your OpenAI API key is valid and has sufficient credits
2. **Import Errors**: Ensure GraphRAG is properly installed: `pip install graphrag`
3. **Memory Issues**: For large documents, consider reducing batch sizes or chunk sizes
4. **Rate Limits**: OpenAI has rate limits; the example includes basic error handling

### Getting Help

- Check the [GraphRAG documentation](https://github.com/microsoft/graphrag)
- Review the error messages for specific configuration issues
- Ensure all dependencies are properly installed

## Next Steps

Once you have the basic example working:

1. Try with your own documents
2. Experiment with different query types
3. Customize the configuration for your use case
4. Explore advanced features like custom embeddings or different LLM providers 