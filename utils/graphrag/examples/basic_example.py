"""
Basic GraphRAG Example

This example demonstrates how to use Microsoft's GraphRAG package to:
1. Index documents and build a knowledge graph
2. Perform global and local queries
3. Get structured responses with source attribution

Note: You'll need to configure the settings in the config section below.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import List, Optional

# GraphRAG imports
from graphrag.config import GraphRagConfig
from graphrag.index import create_pipeline_config
from graphrag.index.run import run_pipeline_with_config
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_communities,
    read_indexer_entities,
    read_indexer_relationships,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.structured_search.global_search.community_context import (
    GlobalCommunityContext,
)
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.local_search.mixed_context import (
    LocalSearchMixedContext,
)
from graphrag.query.structured_search.local_search.search import LocalSearch


class BasicGraphRAG:
    """A basic GraphRAG implementation using Microsoft's GraphRAG package."""
    
    def __init__(self, data_dir: str = "./graphrag_data"):
        """Initialize the GraphRAG instance.
        
        Args:
            data_dir: Directory to store GraphRAG data and outputs
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Configuration placeholders - YOU NEED TO FILL THESE IN
        self.config = {
            "provider": "openai",  # "openai" or "azure_openai"
            "llm": {
                # OpenAI Configuration
                "api_key": "YOUR_OPENAI_API_KEY",  # Set your OpenAI API key
                "model": "gpt-4-turbo-preview",
                "max_tokens": 4000,
                "temperature": 0.0,
                # Azure OpenAI Configuration (only needed if provider is "azure_openai")
                "azure_endpoint": "YOUR_AZURE_ENDPOINT",  # e.g., "https://your-resource.openai.azure.com/"
                "azure_deployment": "YOUR_DEPLOYMENT_NAME",  # Your deployment name
                "api_version": "2024-02-15-preview",  # Azure API version
            },
            "embeddings": {
                # OpenAI Configuration
                "api_key": "YOUR_OPENAI_API_KEY",  # Set your OpenAI API key
                "model": "text-embedding-3-small",
                # Azure OpenAI Configuration (only needed if provider is "azure_openai")
                "azure_endpoint": "YOUR_AZURE_ENDPOINT",  # e.g., "https://your-resource.openai.azure.com/"
                "azure_deployment": "YOUR_EMBEDDING_DEPLOYMENT_NAME",  # Your embedding deployment name
                "api_version": "2024-02-15-preview",  # Azure API version
            },
            "chunk_size": 1200,
            "chunk_overlap": 100,
        }
        
        # Validate configuration
        self._validate_config()
        
        # Initialize LLM and embedding models
        self.llm = None
        self.embedding_model = None
        self._initialize_models()
    
    def _validate_config(self):
        """Validate configuration based on provider."""
        if self.config["provider"] == "azure_openai":
            required_vars = {
                "api_key": self.config["llm"]["api_key"],
                "azure_endpoint": self.config["llm"]["azure_endpoint"],
                "azure_deployment": self.config["llm"]["azure_deployment"],
                "embedding_deployment": self.config["embeddings"]["azure_deployment"],
            }
            
            missing_vars = []
            for key, value in required_vars.items():
                if not value or value.startswith("YOUR_"):
                    missing_vars.append(key)
            
            if missing_vars:
                print("❌ Missing Azure OpenAI configuration:")
                for var in missing_vars:
                    print(f"   - {var}")
                print("\nFor Azure OpenAI, you need to set:")
                print("   - api_key: Your Azure OpenAI API key")
                print("   - azure_endpoint: https://your-resource.openai.azure.com/")
                print("   - azure_deployment: Your GPT deployment name")
                print("   - embedding_deployment: Your embedding deployment name")
                
            # Validate endpoint format
            endpoint = self.config["llm"]["azure_endpoint"]
            if endpoint and not endpoint.startswith("YOUR_"):
                if not endpoint.startswith("https://") or not endpoint.endswith("/"):
                    print("⚠️  Warning: Azure endpoint should start with 'https://' and end with '/'")
                    print(f"   Current: {endpoint}")
                    print("   Expected: https://your-resource.openai.azure.com/")
        else:
            # OpenAI validation
            api_key = self.config["llm"]["api_key"]
            if not api_key or api_key.startswith("YOUR_"):
                print("❌ Missing OpenAI configuration:")
                print("   - Set your OpenAI API key in the config")
    
    def _initialize_models(self):
        """Initialize LLM and embedding models."""
        try:
            if self.config["provider"] == "azure_openai":
                # Azure OpenAI configuration
                self.llm = ChatOpenAI(
                    api_key=self.config["llm"]["api_key"],
                    azure_endpoint=self.config["llm"]["azure_endpoint"],
                    azure_deployment=self.config["llm"]["azure_deployment"],
                    api_version=self.config["llm"]["api_version"],
                    max_tokens=self.config["llm"]["max_tokens"],
                    temperature=self.config["llm"]["temperature"],
                )
                
                self.embedding_model = OpenAIEmbedding(
                    api_key=self.config["embeddings"]["api_key"],
                    azure_endpoint=self.config["embeddings"]["azure_endpoint"],
                    azure_deployment=self.config["embeddings"]["azure_deployment"],
                    api_version=self.config["embeddings"]["api_version"],
                )
            else:
                # Standard OpenAI configuration
                self.llm = ChatOpenAI(
                    api_key=self.config["llm"]["api_key"],
                    model=self.config["llm"]["model"],
                    max_tokens=self.config["llm"]["max_tokens"],
                    temperature=self.config["llm"]["temperature"],
                )
                
                self.embedding_model = OpenAIEmbedding(
                    api_key=self.config["embeddings"]["api_key"],
                    model=self.config["embeddings"]["model"],
                )
        except Exception as e:
            print(f"Warning: Could not initialize models. Please check your API keys and configuration. Error: {e}")
    
    def show_config(self):
        """Display current configuration."""
        provider = self.config["provider"]
        print(f"📋 Current Configuration ({provider}):")
        print("=" * 40)
        
        if provider == "azure_openai":
            api_key = self.config["llm"]["api_key"]
            endpoint = self.config["llm"]["azure_endpoint"]
            llm_deployment = self.config["llm"]["azure_deployment"]
            embedding_deployment = self.config["embeddings"]["azure_deployment"]
            api_version = self.config["llm"]["api_version"]
            
            print(f"Provider: Azure OpenAI")
            if api_key and not api_key.startswith("YOUR_"):
                print(f"API Key: ✅ Set ({'*' * 20}...{api_key[-4:]})")
            else:
                print(f"API Key: ❌ Not set")
            print(f"Endpoint: {endpoint}")
            print(f"LLM Deployment: {llm_deployment}")
            print(f"Embedding Deployment: {embedding_deployment}")
            print(f"API Version: {api_version}")
        else:
            api_key = self.config["llm"]["api_key"]
            model = self.config["llm"]["model"]
            embedding_model = self.config["embeddings"]["model"]
            
            print(f"Provider: OpenAI")
            if api_key and not api_key.startswith("YOUR_"):
                print(f"API Key: ✅ Set ({'*' * 20}...{api_key[-4:]})")
            else:
                print(f"API Key: ❌ Not set")
            print(f"Model: {model}")
            print(f"Embedding Model: {embedding_model}")
        
        print(f"Data Directory: {self.data_dir}")
        print(f"Chunk Size: {self.config['chunk_size']}")
        print(f"Chunk Overlap: {self.config['chunk_overlap']}")
    
    async def index_documents(self, documents: List[str], input_dir: Optional[str] = None) -> bool:
        """Index documents to build the knowledge graph.
        
        Args:
            documents: List of document content or file paths
            input_dir: Directory containing input documents (if documents are file paths)
            
        Returns:
            True if indexing was successful, False otherwise
        """
        try:
            # Create input directory if not provided
            if input_dir is None:
                input_dir = self.data_dir / "input"
                input_dir.mkdir(exist_ok=True)
                
                # Write documents to files if they're content strings
                for i, doc in enumerate(documents):
                    if not Path(doc).exists():  # Assume it's content, not a file path
                        doc_path = input_dir / f"document_{i}.txt"
                        with open(doc_path, "w", encoding="utf-8") as f:
                            f.write(doc)
            
            # Create GraphRAG configuration
            config = self._create_config(str(input_dir))
            
            # Run the indexing pipeline
            print("Starting document indexing...")
            await run_pipeline_with_config(config)
            print("Indexing completed successfully!")
            
            return True
            
        except Exception as e:
            print(f"Error during indexing: {e}")
            return False
    
    def _create_config(self, input_dir: str) -> GraphRagConfig:
        """Create GraphRAG configuration."""
        # Base configuration
        config_data = {
            "input": {
                "type": "file",
                "file_type": "text",
                "base_dir": input_dir,
                "file_encoding": "utf-8",
                "file_pattern": ".*\\.txt$",
            },
            "cache": {
                "type": "file",
                "base_dir": str(self.data_dir / "cache"),
            },
            "storage": {
                "type": "file",
                "base_dir": str(self.data_dir / "output"),
            },
            "reporting": {
                "type": "file",
                "base_dir": str(self.data_dir / "reporting"),
            },
            "chunks": {
                "size": self.config["chunk_size"],
                "overlap": self.config["chunk_overlap"],
            },
        }
        
        # Configure LLM based on provider
        if self.config["provider"] == "azure_openai":
            config_data["llm"] = {
                "api_key": self.config["llm"]["api_key"],
                "type": "azure_openai_chat",
                "azure_endpoint": self.config["llm"]["azure_endpoint"],
                "azure_deployment": self.config["llm"]["azure_deployment"],
                "api_version": self.config["llm"]["api_version"],
                "max_tokens": self.config["llm"]["max_tokens"],
                "temperature": self.config["llm"]["temperature"],
            }
            
            config_data["embeddings"] = {
                "api_key": self.config["embeddings"]["api_key"],
                "type": "azure_openai_embedding",
                "azure_endpoint": self.config["embeddings"]["azure_endpoint"],
                "azure_deployment": self.config["embeddings"]["azure_deployment"],
                "api_version": self.config["embeddings"]["api_version"],
            }
        else:
            config_data["llm"] = {
                "api_key": self.config["llm"]["api_key"],
                "type": "openai_chat",
                "model": self.config["llm"]["model"],
                "max_tokens": self.config["llm"]["max_tokens"],
                "temperature": self.config["llm"]["temperature"],
            }
            
            config_data["embeddings"] = {
                "api_key": self.config["embeddings"]["api_key"],
                "type": "openai_embedding",
                "model": self.config["embeddings"]["model"],
            }
        
        return GraphRagConfig.from_dict(config_data)
    
    async def global_search(self, query: str) -> str:
        """Perform a global search across the entire knowledge graph.
        
        Args:
            query: The search query
            
        Returns:
            The search response
        """
        try:
            # Load the indexed data
            output_dir = self.data_dir / "output"
            
            # Read the indexed data
            entities = read_indexer_entities(output_dir, None, 10)
            reports = read_indexer_reports(output_dir, None, 10)
            
            # Create context builder
            context_builder = GlobalCommunityContext(
                community_reports=reports,
                entities=entities,
                token_encoder=self.llm.get_token_encoder() if self.llm else None,
            )
            
            # Create search engine
            search_engine = GlobalSearch(
                llm=self.llm,
                context_builder=context_builder,
                token_encoder=self.llm.get_token_encoder() if self.llm else None,
                max_data_tokens=12000,
                map_llm_params={
                    "max_tokens": 1000,
                    "temperature": 0.0,
                },
                reduce_llm_params={
                    "max_tokens": 2000,
                    "temperature": 0.0,
                },
            )
            
            # Perform the search
            result = await search_engine.asearch(query)
            return result.response
            
        except Exception as e:
            return f"Error during global search: {e}"
    
    async def local_search(self, query: str) -> str:
        """Perform a local search for specific entities and relationships.
        
        Args:
            query: The search query
            
        Returns:
            The search response
        """
        try:
            # Load the indexed data
            output_dir = self.data_dir / "output"
            
            # Read the indexed data
            entities = read_indexer_entities(output_dir, None, 10)
            relationships = read_indexer_relationships(output_dir, None, 10)
            reports = read_indexer_reports(output_dir, None, 10)
            text_units = read_indexer_text_units(output_dir, None, 10)
            
            # Create context builder
            context_builder = LocalSearchMixedContext(
                community_reports=reports,
                text_units=text_units,
                entities=entities,
                relationships=relationships,
                entity_text_embeddings=None,  # You can add embeddings here
                embedding_vectorstore_key=EntityVectorStoreKey.ID,
                text_embedder=self.embedding_model,
                token_encoder=self.llm.get_token_encoder() if self.llm else None,
            )
            
            # Create search engine
            search_engine = LocalSearch(
                llm=self.llm,
                context_builder=context_builder,
                token_encoder=self.llm.get_token_encoder() if self.llm else None,
                llm_params={
                    "max_tokens": 2000,
                    "temperature": 0.0,
                },
            )
            
            # Perform the search
            result = await search_engine.asearch(query)
            return result.response
            
        except Exception as e:
            return f"Error during local search: {e}"


async def main():
    """Main example function demonstrating GraphRAG usage."""
    print("🚀 Basic GraphRAG Example")
    print("=" * 50)
    
    # Sample documents to index
    sample_documents = [
        """
        Artificial Intelligence (AI) is transforming various industries. Machine learning, 
        a subset of AI, enables computers to learn from data without explicit programming. 
        Deep learning, which uses neural networks, has achieved remarkable success in 
        image recognition and natural language processing.
        """,
        """
        Climate change is one of the most pressing challenges of our time. Rising global 
        temperatures are causing sea levels to rise, extreme weather events to become more 
        frequent, and ecosystems to shift. Renewable energy sources like solar and wind 
        power are crucial for reducing greenhouse gas emissions.
        """,
        """
        The COVID-19 pandemic has accelerated digital transformation across organizations. 
        Remote work has become the norm, leading to increased adoption of cloud technologies 
        and collaboration tools. This shift has also highlighted the importance of 
        cybersecurity and data privacy.
        """
    ]
    
    # Initialize GraphRAG
    print("📊 Initializing GraphRAG...")
    graphrag = BasicGraphRAG(data_dir="./example_graphrag_data")
    
    # Show current configuration
    graphrag.show_config()
    
    # Check if models are properly initialized
    if graphrag.llm is None or graphrag.embedding_model is None:
        print("\n⚠️  Warning: Models not initialized. Please set your API keys in the config.")
        print("   You can still run this example to see the structure, but queries won't work.")
        print("\n💡 Configuration Tips:")
        if graphrag.config["provider"] == "azure_openai":
            print("   For Azure OpenAI:")
            print("   1. Set provider to 'azure_openai'")
            print("   2. Configure azure_endpoint, azure_deployment, and api_key")
            print("   3. Set embedding deployment name")
        else:
            print("   For OpenAI:")
            print("   1. Set provider to 'openai' (default)")
            print("   2. Set your OpenAI API key")
            print("   3. Optionally customize model names")
        return
    
    # Index documents
    print("\n📚 Indexing documents...")
    success = await graphrag.index_documents(sample_documents)
    
    if not success:
        print("❌ Indexing failed. Please check your configuration and try again.")
        return
    
    print("✅ Documents indexed successfully!")
    
    # Perform global search
    print("\n🌍 Performing global search...")
    global_query = "What are the main themes and topics discussed in the documents?"
    global_result = await graphrag.global_search(global_query)
    print(f"Query: {global_query}")
    print(f"Response: {global_result}")
    
    # Perform local search
    print("\n🔍 Performing local search...")
    local_query = "Tell me about artificial intelligence and machine learning"
    local_result = await graphrag.local_search(local_query)
    print(f"Query: {local_query}")
    print(f"Response: {local_result}")
    
    print("\n✨ Example completed!")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 