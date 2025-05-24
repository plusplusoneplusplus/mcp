"""
Environment-based GraphRAG Example

This example shows how to use environment variables for configuration,
which is a more secure approach than hardcoding API keys.

Before running this script, set your environment variables:

For OpenAI:
export OPENAI_API_KEY="your-api-key-here"
export GRAPHRAG_PROVIDER="openai"

For Azure OpenAI:
export AZURE_OPENAI_API_KEY="your-azure-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_LLM_DEPLOYMENT="your-gpt-deployment-name"
export AZURE_OPENAI_EMBEDDING_DEPLOYMENT="your-embedding-deployment-name"
export GRAPHRAG_PROVIDER="azure_openai"

Optional:
export GRAPHRAG_DATA_DIR="./my_graphrag_data"
"""

import asyncio
import os
from pathlib import Path
from basic_example import BasicGraphRAG


class EnvGraphRAG(BasicGraphRAG):
    """GraphRAG implementation using environment variables for configuration."""
    
    def __init__(self, data_dir: str = None):
        """Initialize with environment-based configuration."""
        
        # Use environment variable or default
        if data_dir is None:
            data_dir = os.getenv("GRAPHRAG_DATA_DIR", "./graphrag_data")
        
        # Initialize parent with data directory
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Determine provider
        provider = os.getenv("GRAPHRAG_PROVIDER", "openai").lower()
        
        # Load configuration from environment variables
        if provider == "azure_openai":
            self.config = {
                "provider": "azure_openai",
                "llm": {
                    "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                    "azure_deployment": os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT"),
                    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                    "max_tokens": int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "4000")),
                    "temperature": float(os.getenv("AZURE_OPENAI_TEMPERATURE", "0.0")),
                },
                "embeddings": {
                    "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                    "azure_deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
                    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                },
                "chunk_size": int(os.getenv("GRAPHRAG_CHUNK_SIZE", "1200")),
                "chunk_overlap": int(os.getenv("GRAPHRAG_CHUNK_OVERLAP", "100")),
            }
            
            # Validate required Azure OpenAI environment variables
            required_vars = [
                "AZURE_OPENAI_API_KEY",
                "AZURE_OPENAI_ENDPOINT", 
                "AZURE_OPENAI_LLM_DEPLOYMENT",
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
            ]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                raise ValueError(
                    f"Missing required Azure OpenAI environment variables: {', '.join(missing_vars)}. "
                    f"Please set them before running this example."
                )
        else:
            self.config = {
                "provider": "openai",
                "llm": {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "model": os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview"),
                    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
                    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.0")),
                },
                "embeddings": {
                    "api_key": os.getenv("OPENAI_API_KEY"),  # Same key for embeddings
                    "model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
                },
                "chunk_size": int(os.getenv("GRAPHRAG_CHUNK_SIZE", "1200")),
                "chunk_overlap": int(os.getenv("GRAPHRAG_CHUNK_OVERLAP", "100")),
            }
            
            # Validate required OpenAI environment variables
            if not self.config["llm"]["api_key"]:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required. "
                    "Set it with: export OPENAI_API_KEY='your-api-key-here'"
                )
        
        # Initialize models
        self.llm = None
        self.embedding_model = None
        self._initialize_models()


def check_environment():
    """Check if required environment variables are set."""
    provider = os.getenv("GRAPHRAG_PROVIDER", "openai").lower()
    
    if provider == "azure_openai":
        required_vars = [
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_LLM_DEPLOYMENT", 
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        ]
        provider_name = "Azure OpenAI"
    else:
        required_vars = ["OPENAI_API_KEY"]
        provider_name = "OpenAI"
    
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required {provider_name} environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print(f"\nPlease set them before running this example:")
        for var in missing_vars:
            print(f"   export {var}='your-value-here'")
        return False
    
    print(f"✅ All required {provider_name} environment variables are set!")
    return True


def show_current_config():
    """Show current configuration."""
    provider = os.getenv("GRAPHRAG_PROVIDER", "openai").lower()
    
    print("\n📋 Current Configuration:")
    print(f"   Provider: {provider}")
    
    if provider == "azure_openai":
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        llm_deployment = os.getenv("AZURE_OPENAI_LLM_DEPLOYMENT", "")
        embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        print(f"   API Key: {'*' * 20}...{api_key[-4:] if api_key else 'Not set'}")
        print(f"   Endpoint: {endpoint}")
        print(f"   LLM Deployment: {llm_deployment}")
        print(f"   Embedding Deployment: {embedding_deployment}")
        print(f"   API Version: {api_version}")
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        
        print(f"   API Key: {'*' * 20}...{api_key[-4:] if api_key else 'Not set'}")
        print(f"   Model: {model}")
        print(f"   Embedding Model: {embedding_model}")
    
    print(f"   Data Directory: {os.getenv('GRAPHRAG_DATA_DIR', './graphrag_data')}")


async def main():
    """Main example function using environment configuration."""
    print("🌍 Environment-based GraphRAG Example")
    print("=" * 50)
    
    # Check environment variables
    if not check_environment():
        return
    
    # Show current configuration
    show_current_config()
    
    # Sample documents
    documents = [
        """
        Machine Learning Operations (MLOps) is a practice that combines machine learning 
        and DevOps to deploy and maintain ML models in production reliably and efficiently. 
        It includes model versioning, automated testing, continuous integration, and 
        monitoring of model performance in production environments.
        """,
        """
        Sustainable technology focuses on developing solutions that meet present needs 
        without compromising future generations. This includes renewable energy systems, 
        energy-efficient computing, circular economy principles, and green software 
        development practices that minimize environmental impact.
        """,
    ]
    
    try:
        # Initialize GraphRAG with environment configuration
        print("\n📊 Initializing GraphRAG with environment config...")
        graphrag = EnvGraphRAG()
        
        # Index documents
        print("\n📚 Indexing documents...")
        success = await graphrag.index_documents(documents)
        
        if not success:
            print("❌ Indexing failed. Check your configuration and try again.")
            return
        
        print("✅ Documents indexed successfully!")
        
        # Perform searches
        print("\n🌍 Performing global search...")
        global_query = "What are the key concepts and relationships in these documents?"
        global_result = await graphrag.global_search(global_query)
        print(f"Query: {global_query}")
        print(f"Response: {global_result}")
        
        print("\n🔍 Performing local search...")
        local_query = "How does MLOps relate to sustainable technology?"
        local_result = await graphrag.local_search(local_query)
        print(f"Query: {local_query}")
        print(f"Response: {local_result}")
        
        print("\n✨ Example completed successfully!")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 