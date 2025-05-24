"""
GraphRAG Configuration Module

This module provides configuration management for GraphRAG, supporting:
- YAML file configuration
- Environment variable overrides
- Validation for OpenAI and Azure OpenAI
- Default values and type conversion
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM configuration for both OpenAI and Azure OpenAI."""
    api_key: str
    model: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.0
    # Azure OpenAI specific
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    api_version: str = "2024-02-15-preview"


@dataclass
class EmbeddingConfig:
    """Embedding configuration for both OpenAI and Azure OpenAI."""
    api_key: str
    model: Optional[str] = None
    # Azure OpenAI specific
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    api_version: str = "2024-02-15-preview"


@dataclass
class GraphRAGConfig:
    """Main GraphRAG configuration."""
    provider: str = "openai"  # "openai" or "azure_openai"
    llm: LLMConfig = field(default_factory=lambda: LLMConfig(api_key=""))
    embeddings: EmbeddingConfig = field(default_factory=lambda: EmbeddingConfig(api_key=""))
    chunk_size: int = 1200
    chunk_overlap: int = 100
    data_dir: str = "./graphrag_data"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self):
        """Validate the configuration based on provider."""
        if self.provider == "azure_openai":
            self._validate_azure_openai()
        else:
            self._validate_openai()
    
    def _validate_openai(self):
        """Validate OpenAI configuration."""
        if not self.llm.api_key or self.llm.api_key.startswith("YOUR_"):
            raise ValueError("OpenAI API key is required")
        
        if not self.llm.model:
            self.llm.model = "gpt-4.1"
        
        if not self.embeddings.model:
            self.embeddings.model = "text-embedding-3-small"
        
        # Use same API key for embeddings if not specified
        if not self.embeddings.api_key:
            self.embeddings.api_key = self.llm.api_key
    
    def _validate_azure_openai(self):
        """Validate Azure OpenAI configuration."""
        required_fields = [
            (self.llm.api_key, "LLM API key"),
            (self.llm.azure_endpoint, "LLM Azure endpoint"),
            (self.llm.azure_deployment, "LLM Azure deployment"),
            (self.embeddings.azure_deployment, "Embeddings Azure deployment"),
        ]
        
        missing = []
        for value, name in required_fields:
            if not value or (isinstance(value, str) and value.startswith("YOUR_")):
                missing.append(name)
        
        if missing:
            raise ValueError(f"Missing Azure OpenAI configuration: {', '.join(missing)}")
        
        # Use same API key and endpoint for embeddings if not specified
        if not self.embeddings.api_key:
            self.embeddings.api_key = self.llm.api_key
        if not self.embeddings.azure_endpoint:
            self.embeddings.azure_endpoint = self.llm.azure_endpoint
        
        # Validate endpoint format
        if self.llm.azure_endpoint:
            if not self.llm.azure_endpoint.startswith("https://"):
                raise ValueError("Azure endpoint must start with 'https://'")
            if not self.llm.azure_endpoint.endswith("/"):
                self.llm.azure_endpoint += "/"
    
    def show_config(self):
        """Display current configuration."""
        print(f"📋 GraphRAG Configuration ({self.provider}):")
        print("=" * 50)
        
        if self.provider == "azure_openai":
            print(f"Provider: Azure OpenAI")
            print(f"API Key: {'✅ Set (' + '*' * 20 + '...' + self.llm.api_key[-4:] + ')' if self.llm.api_key else '❌ Not set'}")
            print(f"Endpoint: {self.llm.azure_endpoint}")
            print(f"LLM Deployment: {self.llm.azure_deployment}")
            print(f"Embedding Deployment: {self.embeddings.azure_deployment}")
            print(f"API Version: {self.llm.api_version}")
        else:
            print(f"Provider: OpenAI")
            print(f"API Key: {'✅ Set (' + '*' * 20 + '...' + self.llm.api_key[-4:] + ')' if self.llm.api_key else '❌ Not set'}")
            print(f"LLM Model: {self.llm.model}")
            print(f"Embedding Model: {self.embeddings.model}")
        
        print(f"Data Directory: {self.data_dir}")
        print(f"Chunk Size: {self.chunk_size}")
        print(f"Chunk Overlap: {self.chunk_overlap}")


class ConfigLoader:
    """Configuration loader that supports YAML files and environment variables."""
    
    @staticmethod
    def from_yaml(config_path: Union[str, Path]) -> GraphRAGConfig:
        """Load configuration from YAML file with environment variable overrides."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Load YAML configuration
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f)
        
        # Apply environment variable overrides
        yaml_config = ConfigLoader._apply_env_overrides(yaml_config)
        
        # Convert to configuration objects
        return ConfigLoader._dict_to_config(yaml_config)
    
    @staticmethod
    def from_env() -> GraphRAGConfig:
        """Load configuration entirely from environment variables."""
        provider = os.getenv("GRAPHRAG_PROVIDER", "openai").lower()
        
        if provider == "azure_openai":
            config_dict = {
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
                "data_dir": os.getenv("GRAPHRAG_DATA_DIR", "./graphrag_data"),
            }
        else:
            config_dict = {
                "provider": "openai",
                "llm": {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "model": os.getenv("OPENAI_MODEL", "gpt-4.1"),
                    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
                    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.0")),
                },
                "embeddings": {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
                },
                "chunk_size": int(os.getenv("GRAPHRAG_CHUNK_SIZE", "1200")),
                "chunk_overlap": int(os.getenv("GRAPHRAG_CHUNK_OVERLAP", "100")),
                "data_dir": os.getenv("GRAPHRAG_DATA_DIR", "./graphrag_data"),
            }
        
        return ConfigLoader._dict_to_config(config_dict)
    
    @staticmethod
    def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to YAML configuration."""
        # Provider override
        if os.getenv("GRAPHRAG_PROVIDER"):
            config["provider"] = os.getenv("GRAPHRAG_PROVIDER").lower()
        
        provider = config.get("provider", "openai")
        
        if provider == "azure_openai":
            # Azure OpenAI overrides
            env_overrides = {
                ("llm", "api_key"): "AZURE_OPENAI_API_KEY",
                ("llm", "azure_endpoint"): "AZURE_OPENAI_ENDPOINT",
                ("llm", "azure_deployment"): "AZURE_OPENAI_LLM_DEPLOYMENT",
                ("llm", "api_version"): "AZURE_OPENAI_API_VERSION",
                ("llm", "max_tokens"): "AZURE_OPENAI_MAX_TOKENS",
                ("llm", "temperature"): "AZURE_OPENAI_TEMPERATURE",
                ("embeddings", "api_key"): "AZURE_OPENAI_API_KEY",
                ("embeddings", "azure_endpoint"): "AZURE_OPENAI_ENDPOINT",
                ("embeddings", "azure_deployment"): "AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
                ("embeddings", "api_version"): "AZURE_OPENAI_API_VERSION",
            }
        else:
            # OpenAI overrides
            env_overrides = {
                ("llm", "api_key"): "OPENAI_API_KEY",
                ("llm", "model"): "OPENAI_MODEL",
                ("llm", "max_tokens"): "OPENAI_MAX_TOKENS",
                ("llm", "temperature"): "OPENAI_TEMPERATURE",
                ("embeddings", "api_key"): "OPENAI_API_KEY",
                ("embeddings", "model"): "OPENAI_EMBEDDING_MODEL",
            }
        
        # Common overrides
        env_overrides.update({
            ("chunk_size",): "GRAPHRAG_CHUNK_SIZE",
            ("chunk_overlap",): "GRAPHRAG_CHUNK_OVERLAP",
            ("data_dir",): "GRAPHRAG_DATA_DIR",
        })
        
        # Apply overrides
        for path, env_var in env_overrides.items():
            env_value = os.getenv(env_var)
            if env_value:
                # Navigate to the correct nested dictionary
                current = config
                for key in path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                # Convert type if needed
                final_key = path[-1]
                if final_key in ["max_tokens", "chunk_size", "chunk_overlap"]:
                    current[final_key] = int(env_value)
                elif final_key == "temperature":
                    current[final_key] = float(env_value)
                else:
                    current[final_key] = env_value
        
        return config
    
    @staticmethod
    def _dict_to_config(config_dict: Dict[str, Any]) -> GraphRAGConfig:
        """Convert dictionary to GraphRAGConfig object."""
        llm_config = LLMConfig(**config_dict.get("llm", {}))
        embeddings_config = EmbeddingConfig(**config_dict.get("embeddings", {}))
        
        return GraphRAGConfig(
            provider=config_dict.get("provider", "openai"),
            llm=llm_config,
            embeddings=embeddings_config,
            chunk_size=config_dict.get("chunk_size", 1200),
            chunk_overlap=config_dict.get("chunk_overlap", 100),
            data_dir=config_dict.get("data_dir", "./graphrag_data"),
        )


def load_config(config_path: Optional[Union[str, Path]] = None) -> GraphRAGConfig:
    """
    Load GraphRAG configuration with automatic detection.
    
    Args:
        config_path: Path to YAML config file. If None, loads from environment variables.
        
    Returns:
        GraphRAGConfig: Validated configuration object
        
    Examples:
        # Load from YAML file with env overrides
        config = load_config("config.yaml")
        
        # Load entirely from environment variables
        config = load_config()
    """
    if config_path:
        return ConfigLoader.from_yaml(config_path)
    else:
        return ConfigLoader.from_env() 