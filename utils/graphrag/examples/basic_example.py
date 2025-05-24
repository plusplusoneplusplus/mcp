"""
Basic GraphRAG Example

This example demonstrates how to use Microsoft's GraphRAG package to:
1. Index documents and build a knowledge graph
2. Perform global and local queries
3. Get structured responses with source attribution

Configuration options:
1. YAML file: python basic_example.py config.yaml
2. Environment variables: python basic_example.py
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

# GraphRAG imports
from graphrag.config import GraphRagConfig
from graphrag.index.run import run_pipeline_with_config
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
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

# Import our configuration module
from utils.graphrag.config import load_config, GraphRAGConfig


class BasicGraphRAG:
    """A basic GraphRAG implementation using Microsoft's GraphRAG package."""
    
    def __init__(self, config: GraphRAGConfig):
        """Initialize the GraphRAG instance.
        
        Args:
            config: GraphRAG configuration object
        """
        self.config = config
        self.data_dir = Path(config.data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize LLM and embedding models
        self.llm = None
        self.embedding_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize LLM and embedding models."""
        try:
            if self.config.provider == "azure_openai":
                # Azure OpenAI configuration
                self.llm = ChatOpenAI(
                    api_key=self.config.llm.api_key,
                    azure_endpoint=self.config.llm.azure_endpoint,
                    azure_deployment=self.config.llm.azure_deployment,
                    api_version=self.config.llm.api_version,
                    max_tokens=self.config.llm.max_tokens,
                    temperature=self.config.llm.temperature,
                )
                
                self.embedding_model = OpenAIEmbedding(
                    api_key=self.config.embeddings.api_key,
                    azure_endpoint=self.config.embeddings.azure_endpoint,
                    azure_deployment=self.config.embeddings.azure_deployment,
                    api_version=self.config.embeddings.api_version,
                )
            else:
                # Standard OpenAI configuration
                self.llm = ChatOpenAI(
                    api_key=self.config.llm.api_key,
                    model=self.config.llm.model,
                    max_tokens=self.config.llm.max_tokens,
                    temperature=self.config.llm.temperature,
                )
                
                self.embedding_model = OpenAIEmbedding(
                    api_key=self.config.embeddings.api_key,
                    model=self.config.embeddings.model,
                )
        except Exception as e:
            print(f"Warning: Could not initialize models. Please check your configuration. Error: {e}")
    
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
            graphrag_config = self._create_graphrag_config(str(input_dir))
            
            # Run the indexing pipeline
            print("Starting document indexing...")
            await run_pipeline_with_config(graphrag_config)
            print("Indexing completed successfully!")
            
            return True
            
        except Exception as e:
            print(f"Error during indexing: {e}")
            return False
    
    def _create_graphrag_config(self, input_dir: str) -> GraphRagConfig:
        """Create GraphRAG configuration for the indexing pipeline."""
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
                "size": self.config.chunk_size,
                "overlap": self.config.chunk_overlap,
            },
        }
        
        # Configure LLM based on provider
        if self.config.provider == "azure_openai":
            config_data["llm"] = {
                "api_key": self.config.llm.api_key,
                "type": "azure_openai_chat",
                "azure_endpoint": self.config.llm.azure_endpoint,
                "azure_deployment": self.config.llm.azure_deployment,
                "api_version": self.config.llm.api_version,
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
            }
            
            config_data["embeddings"] = {
                "api_key": self.config.embeddings.api_key,
                "type": "azure_openai_embedding",
                "azure_endpoint": self.config.embeddings.azure_endpoint,
                "azure_deployment": self.config.embeddings.azure_deployment,
                "api_version": self.config.embeddings.api_version,
            }
        else:
            config_data["llm"] = {
                "api_key": self.config.llm.api_key,
                "type": "openai_chat",
                "model": self.config.llm.model,
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
            }
            
            config_data["embeddings"] = {
                "api_key": self.config.embeddings.api_key,
                "type": "openai_embedding",
                "model": self.config.embeddings.model,
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
    
    # Show configuration
    config.show_config()
    
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
    print("\n📊 Initializing GraphRAG...")
    graphrag = BasicGraphRAG(config)
    
    # Check if models are properly initialized
    if graphrag.llm is None or graphrag.embedding_model is None:
        print("\n⚠️  Warning: Models not initialized. Please check your configuration.")
        print("   You can still run this example to see the structure, but queries won't work.")
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