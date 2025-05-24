"""
Basic GraphRAG Example

This example demonstrates how to use Microsoft's GraphRAG 2.3.0 package to:
1. Index documents and build a knowledge graph
2. Perform global and local queries
3. Get structured responses with source attribution

Usage:
    python basic_example.py config.yaml  # Use YAML config file
    python basic_example.py              # Use environment variables
"""

import asyncio
import sys
import os
import yaml
from pathlib import Path
from typing import List, Optional

# GraphRAG imports
from graphrag.config.load_config import load_config as load_graphrag_config
from graphrag.index.run.run_pipeline import run_pipeline
from graphrag.logger.rich_progress import RichProgressLogger
from graphrag.query.factory import (
    get_global_search_engine,
    get_local_search_engine,
)
from graphrag.query.indexer_adapters import (
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)

# Import our configuration module
from utils.graphrag.config import load_config, GraphRAGConfig


class BasicGraphRAG:
    """A basic GraphRAG implementation using Microsoft's GraphRAG 2.3.0 Python API."""
    
    def __init__(self, config: GraphRAGConfig):
        """Initialize the GraphRAG instance."""
        self.config = config
        self.data_dir = Path(config.data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # GraphRAG workspace directories
        self.input_dir = self.data_dir / "input"
        self.output_dir = self.data_dir / "output"
        self.cache_dir = self.data_dir / "cache"
        self.reporting_dir = self.data_dir / "reporting"
        
        # Create directories
        for dir_path in [self.input_dir, self.output_dir, self.cache_dir, self.reporting_dir]:
            dir_path.mkdir(exist_ok=True)
    
    async def index_documents(self, documents: List[str]) -> bool:
        """Index documents to build the knowledge graph."""
        try:
            # Write documents to input directory
            print("📝 Writing documents to input directory...")
            for i, doc in enumerate(documents):
                if isinstance(doc, str) and len(doc) < 260 and Path(doc).exists():
                    # It's a file path, copy it
                    import shutil
                    print(f"  📄 Copying file: {doc}")
                    shutil.copy2(doc, self.input_dir)
                else:
                    # It's content, write it to a file
                    doc_path = self.input_dir / f"document_{i}.txt"
                    print(f"  📄 Writing content to: {doc_path}")
                    with open(doc_path, "w", encoding="utf-8") as f:
                        f.write(doc.strip())
            
            # Create configuration files
            print("⚙️ Creating configuration files...")
            try:
                self._create_config_files()
                print("✅ Configuration files created successfully")
            except Exception as config_error:
                print(f"❌ Error creating config files: {config_error}")
                import traceback
                traceback.print_exc()
                return False
            
            # Load GraphRAG configuration and run pipeline
            print("📖 Loading GraphRAG configuration...")
            try:
                graphrag_config = load_graphrag_config(self.data_dir)
                print("✅ GraphRAG configuration loaded successfully")
            except Exception as load_error:
                print(f"❌ Error loading GraphRAG config: {load_error}")
                print(f"Error type: {type(load_error)}")
                print(f"Error args: {load_error.args}")
                
                # Check if it's the placeholder error and provide more details
                if "Invalid placeholder" in str(load_error):
                    print("\n🔍 Placeholder Error Details:")
                    settings_file = self.data_dir / "settings.yaml"
                    if settings_file.exists():
                        print(f"Settings file: {settings_file}")
                        with open(settings_file, "r") as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines, 1):
                                print(f"{i:2d}: {line.rstrip()}")
                                if i == 10:  # Line 10 where the error occurs
                                    print(f"    {'':2s}  {'':24s}^ Error at column 25")
                    
                    print("\n🔍 Environment Variables:")
                    for key, value in os.environ.items():
                        if key.startswith("GRAPHRAG_"):
                            print(f"  {key}={value}")
                
                import traceback
                traceback.print_exc()
                return False
            
            # Create logger
            logger = RichProgressLogger("GraphRAG Indexing")
            
            # Run the indexing pipeline directly
            print("🚀 Starting document indexing...")
            try:
                async for result in run_pipeline(
                    config=graphrag_config,
                    logger=logger,
                    is_update_run=False
                ):
                    pass  # Process results silently
                
                print("✅ Indexing completed successfully!")
                return True
                
            except Exception as pipeline_run_error:
                print(f"❌ Error running pipeline: {pipeline_run_error}")
                import traceback
                traceback.print_exc()
                return False
            
        except Exception as e:
            print(f"❌ Unexpected error during indexing: {e}")
            print(f"Error type: {type(e)}")
            print(f"Error args: {e.args}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_config_files(self):
        """Create the configuration files that GraphRAG expects."""
        print("  🔧 Setting environment variables...")
        
        # Set environment variables for GraphRAG
        if self.config.provider == "azure_openai":
            env_vars = {
                "GRAPHRAG_API_KEY": self.config.llm.api_key,
                "GRAPHRAG_LLM_API_BASE": self.config.llm.azure_endpoint,
                "GRAPHRAG_LLM_DEPLOYMENT": self.config.llm.azure_deployment,
                "GRAPHRAG_LLM_API_VERSION": self.config.llm.api_version,
                "GRAPHRAG_EMBEDDING_API_KEY": self.config.embeddings.api_key,
                "GRAPHRAG_EMBEDDING_API_BASE": self.config.embeddings.azure_endpoint,
                "GRAPHRAG_EMBEDDING_DEPLOYMENT": self.config.embeddings.azure_deployment,
                "GRAPHRAG_EMBEDDING_API_VERSION": self.config.embeddings.api_version,
            }
        else:
            env_vars = {
                "GRAPHRAG_API_KEY": self.config.llm.api_key,
                "GRAPHRAG_LLM_MODEL": self.config.llm.model,
                "GRAPHRAG_EMBEDDING_API_KEY": self.config.embeddings.api_key,
                "GRAPHRAG_EMBEDDING_MODEL": self.config.embeddings.model,
            }
        
        os.environ.update(env_vars)
        print(f"  ✅ Set {len(env_vars)} environment variables")
        
        # Create .env file
        print("  📝 Creating .env file...")
        env_file = self.data_dir / ".env"
        with open(env_file, "w") as f:
            for key, value in os.environ.items():
                if key.startswith("GRAPHRAG_"):
                    f.write(f"{key}={value}\n")
        print(f"  ✅ Created .env file: {env_file}")
        
        # Create settings.yaml file
        print("  📝 Creating settings.yaml file...")
        settings_file = self.data_dir / "settings.yaml"
        
        settings_data = {
            "input": {
                "type": "file",
                "file_type": "text",
                "base_dir": str(self.input_dir),
                "file_encoding": "utf-8",
                "file_pattern": ".*\\.txt$$",
            },
            "cache": {"type": "file", "base_dir": str(self.cache_dir)},
            "storage": {"type": "file", "base_dir": str(self.output_dir)},
            "reporting": {"type": "file", "base_dir": str(self.reporting_dir)},
            "chunks": {"size": self.config.chunk_size, "overlap": self.config.chunk_overlap},
        }
        
        # Configure models based on provider
        if self.config.provider == "azure_openai":
            settings_data["models"] = {
                "default_chat_model": {
                    "api_key": "${GRAPHRAG_API_KEY}",
                    "type": "azure_openai_chat",
                    "model": "${GRAPHRAG_LLM_DEPLOYMENT}",
                    "api_base": "${GRAPHRAG_LLM_API_BASE}",
                    "deployment_name": "${GRAPHRAG_LLM_DEPLOYMENT}",
                    "api_version": "${GRAPHRAG_LLM_API_VERSION}",
                    "max_tokens": self.config.llm.max_tokens,
                    "temperature": self.config.llm.temperature,
                    "encoding_model": "gpt-4",
                },
                "default_embedding_model": {
                    "api_key": "${GRAPHRAG_EMBEDDING_API_KEY}",
                    "type": "azure_openai_embedding",
                    "model": "${GRAPHRAG_EMBEDDING_DEPLOYMENT}",
                    "api_base": "${GRAPHRAG_EMBEDDING_API_BASE}",
                    "deployment_name": "${GRAPHRAG_EMBEDDING_DEPLOYMENT}",
                    "api_version": "${GRAPHRAG_EMBEDDING_API_VERSION}",
                }
            }
        else:
            settings_data["models"] = {
                "default_chat_model": {
                    "api_key": "${GRAPHRAG_API_KEY}",
                    "type": "openai_chat",
                    "model": "${GRAPHRAG_LLM_MODEL}",
                    "max_tokens": self.config.llm.max_tokens,
                    "temperature": self.config.llm.temperature,
                    "encoding_model": "gpt-4",
                },
                "default_embedding_model": {
                    "api_key": "${GRAPHRAG_EMBEDDING_API_KEY}",
                    "type": "openai_embedding",
                    "model": "${GRAPHRAG_EMBEDDING_MODEL}",
                }
            }
        
        try:
            with open(settings_file, "w") as f:
                yaml.dump(settings_data, f, default_flow_style=False)
            print(f"  ✅ Created settings.yaml file: {settings_file}")
            
            # Show the content for debugging
            print("  📋 Settings.yaml content:")
            with open(settings_file, "r") as f:
                lines = f.readlines()
                for i, line in enumerate(lines, 1):
                    print(f"    {i:2d}: {line.rstrip()}")
                    
        except Exception as yaml_error:
            print(f"  ❌ Error writing settings.yaml: {yaml_error}")
            raise
    
    async def global_search(self, query: str) -> str:
        """Perform a global search across the entire knowledge graph."""
        try:
            entities = read_indexer_entities(self.output_dir, None, 10)
            reports = read_indexer_reports(self.output_dir, None, 10)
            graphrag_config = load_graphrag_config(self.data_dir)
            
            search_engine = get_global_search_engine(
                config=graphrag_config,
                reports=reports,
                entities=entities,
                response_type="Multiple Paragraphs",
            )
            
            result = await search_engine.asearch(query)
            return result.response
            
        except Exception as e:
            return f"Error during global search: {e}"
    
    async def local_search(self, query: str) -> str:
        """Perform a local search for specific entities and relationships."""
        try:
            entities = read_indexer_entities(self.output_dir, None, 10)
            relationships = read_indexer_relationships(self.output_dir, None, 10)
            reports = read_indexer_reports(self.output_dir, None, 10)
            text_units = read_indexer_text_units(self.output_dir, None, 10)
            graphrag_config = load_graphrag_config(self.data_dir)
            
            search_engine = get_local_search_engine(
                config=graphrag_config,
                reports=reports,
                text_units=text_units,
                entities=entities,
                relationships=relationships,
                response_type="Multiple Paragraphs",
            )
            
            result = await search_engine.asearch(query)
            return result.response
            
        except Exception as e:
            return f"Error during local search: {e}"


async def main():
    """Main example function demonstrating GraphRAG usage."""
    print("🚀 Basic GraphRAG Example (GraphRAG 2.3.0)")
    print("=" * 50)
    
    # Load configuration
    try:
        if len(sys.argv) > 1:
            config_path = sys.argv[1]
            print(f"📁 Loading configuration from: {config_path}")
            config = load_config(config_path)
        else:
            print("🌍 Loading configuration from environment variables...")
            config = load_config()
        
        print("✅ Configuration loaded successfully!")
        config.show_config()
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("\n💡 Configuration options:")
        print("1. YAML file: python basic_example.py config.yaml")
        print("2. Environment variables: Set OPENAI_API_KEY or Azure OpenAI vars")
        print("\n📋 Required environment variables:")
        print("   For OpenAI:")
        print("     export OPENAI_API_KEY='your-api-key'")
        print("   For Azure OpenAI:")
        print("     export GRAPHRAG_PROVIDER='azure_openai'")
        print("     export AZURE_OPENAI_API_KEY='your-api-key'")
        print("     export AZURE_OPENAI_ENDPOINT='https://your-resource.openai.azure.com/'")
        print("     export AZURE_OPENAI_LLM_DEPLOYMENT='your-gpt-deployment'")
        print("     export AZURE_OPENAI_EMBEDDING_DEPLOYMENT='your-embedding-deployment'")
        return
    
    # Sample documents to index (loaded from fixture files)
    fixtures_dir = Path(__file__).parent / "fixtures"
    sample_documents = [
        str(fixtures_dir / "artificial_intelligence.txt"),
        str(fixtures_dir / "climate_change.txt"),
        str(fixtures_dir / "digital_transformation.txt"),
    ]
    
    # Initialize and run GraphRAG
    print("\n📊 Initializing GraphRAG...")
    try:
        graphrag = BasicGraphRAG(config)
        print("✅ GraphRAG initialized successfully!")
        
        # Index documents
        print("\n📚 Indexing documents...")
        success = await graphrag.index_documents(sample_documents)
        
        if not success:
            print("❌ Indexing failed. Please check your configuration and try again.")
            return
        
        print("✅ Documents indexed successfully!")
        
        # Perform searches
        print("\n🌍 Performing global search...")
        global_query = "What are the main themes and topics discussed in the documents?"
        global_result = await graphrag.global_search(global_query)
        print(f"Query: {global_query}")
        print(f"Response: {global_result}")
        
        print("\n🔍 Performing local search...")
        local_query = "Tell me about artificial intelligence and machine learning"
        local_result = await graphrag.local_search(local_query)
        print(f"Query: {local_query}")
        print(f"Response: {local_result}")
        
        print("\n✨ Example completed!")
        
    except Exception as e:
        print(f"❌ Failed to run GraphRAG: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 