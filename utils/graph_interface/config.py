"""Configuration management for Neo4j graph interface."""

import os
import yaml
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from .exceptions import Neo4jConfigurationError


class Neo4jConnectionConfig(BaseModel):
    """Neo4j connection configuration."""

    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    username: str = Field(default="neo4j", description="Neo4j username")
    password_env: str = Field(default="NEO4J_PASSWORD", description="Environment variable for password")
    database: str = Field(default="neo4j", description="Neo4j database name")

    @field_validator('uri')
    @classmethod
    def validate_uri(cls, v):
        """Validate Neo4j URI format."""
        if not v:
            raise ValueError("Neo4j URI cannot be empty")

        valid_schemes = ['bolt', 'bolt+s', 'bolt+ssc', 'neo4j', 'neo4j+s', 'neo4j+ssc']
        if not any(v.startswith(f"{scheme}://") for scheme in valid_schemes):
            raise ValueError(f"Invalid Neo4j URI scheme. Must be one of: {valid_schemes}")

        return v

    @property
    def password(self) -> str:
        """Get password from environment variable."""
        password = os.getenv(self.password_env)
        if not password:
            raise Neo4jConfigurationError(
                f"Password not found in environment variable: {self.password_env}",
                config_key=self.password_env
            )
        return password


class Neo4jPoolConfig(BaseModel):
    """Neo4j connection pool configuration."""

    max_connections: int = Field(default=50, description="Maximum number of connections in pool")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")
    max_retry_time: int = Field(default=30, description="Maximum retry time in seconds")

    @field_validator('max_connections')
    @classmethod
    def validate_max_connections(cls, v):
        """Validate max connections is positive."""
        if v <= 0:
            raise ValueError("Max connections must be positive")
        return v

    @field_validator('connection_timeout', 'max_retry_time')
    @classmethod
    def validate_timeouts(cls, v):
        """Validate timeout values are positive."""
        if v <= 0:
            raise ValueError("Timeout values must be positive")
        return v


class Neo4jPerformanceConfig(BaseModel):
    """Neo4j performance configuration."""

    query_timeout: int = Field(default=60, description="Query timeout in seconds")
    batch_size: int = Field(default=1000, description="Batch size for bulk operations")
    enable_query_logging: bool = Field(default=False, description="Enable query logging")

    @field_validator('query_timeout', 'batch_size')
    @classmethod
    def validate_positive_values(cls, v):
        """Validate values are positive."""
        if v <= 0:
            raise ValueError("Performance values must be positive")
        return v


class Neo4jIndexConfig(BaseModel):
    """Neo4j index configuration."""

    auto_create: bool = Field(default=True, description="Automatically create indexes")
    node_indexes: list = Field(default_factory=list, description="Node index definitions")
    relationship_indexes: list = Field(default_factory=list, description="Relationship index definitions")


class Neo4jConfig(BaseModel):
    """Complete Neo4j configuration."""

    connection: Neo4jConnectionConfig = Field(default_factory=Neo4jConnectionConfig)
    pool: Neo4jPoolConfig = Field(default_factory=Neo4jPoolConfig)
    performance: Neo4jPerformanceConfig = Field(default_factory=Neo4jPerformanceConfig)
    indexes: Neo4jIndexConfig = Field(default_factory=Neo4jIndexConfig)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Neo4jConfig":
        """Create configuration from dictionary."""
        try:
            return cls(**config_dict)
        except Exception as e:
            raise Neo4jConfigurationError(f"Invalid configuration: {e}")

    @classmethod
    def from_yaml_file(cls, file_path: Path) -> "Neo4jConfig":
        """Load configuration from YAML file."""
        try:
            if not file_path.exists():
                raise Neo4jConfigurationError(f"Configuration file not found: {file_path}")

            with open(file_path, 'r') as f:
                config_data = yaml.safe_load(f)

            # Extract neo4j section if it exists
            if 'neo4j' in config_data:
                config_data = config_data['neo4j']

            return cls.from_dict(config_data)

        except yaml.YAMLError as e:
            raise Neo4jConfigurationError(f"Invalid YAML configuration: {e}")
        except Exception as e:
            raise Neo4jConfigurationError(f"Failed to load configuration: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()

    def to_yaml_file(self, file_path: Path) -> None:
        """Save configuration to YAML file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w') as f:
                yaml.dump({'neo4j': self.to_dict()}, f, default_flow_style=False)

        except Exception as e:
            raise Neo4jConfigurationError(f"Failed to save configuration: {e}")


class ConfigLoader:
    """Configuration loader with multiple sources."""

    DEFAULT_CONFIG_PATHS = [
        Path("config/neo4j.yaml"),
        Path("config/neo4j.yml"),
        Path(".neo4j.yaml"),
        Path(".neo4j.yml"),
    ]

    @classmethod
    def load_config(cls, config_path: Optional[Path] = None) -> Neo4jConfig:
        """Load configuration from file or defaults."""
        if config_path:
            if not config_path.exists():
                raise Neo4jConfigurationError(f"Specified config file not found: {config_path}")
            return Neo4jConfig.from_yaml_file(config_path)

        # Try default paths
        for path in cls.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return Neo4jConfig.from_yaml_file(path)

        # Return default configuration if no file found
        return Neo4jConfig()

    @classmethod
    def load_from_env(cls) -> Neo4jConfig:
        """Load configuration from environment variables."""
        config_dict = {}

        # Connection settings
        if os.getenv('NEO4J_URI'):
            config_dict.setdefault('connection', {})['uri'] = os.getenv('NEO4J_URI')

        if os.getenv('NEO4J_USERNAME'):
            config_dict.setdefault('connection', {})['username'] = os.getenv('NEO4J_USERNAME')

        if os.getenv('NEO4J_PASSWORD_ENV'):
            config_dict.setdefault('connection', {})['password_env'] = os.getenv('NEO4J_PASSWORD_ENV')

        if os.getenv('NEO4J_DATABASE'):
            config_dict.setdefault('connection', {})['database'] = os.getenv('NEO4J_DATABASE')

        # Pool settings
        if os.getenv('NEO4J_MAX_CONNECTIONS'):
            config_dict.setdefault('pool', {})['max_connections'] = int(os.getenv('NEO4J_MAX_CONNECTIONS'))

        if os.getenv('NEO4J_CONNECTION_TIMEOUT'):
            config_dict.setdefault('pool', {})['connection_timeout'] = int(os.getenv('NEO4J_CONNECTION_TIMEOUT'))

        # Performance settings
        if os.getenv('NEO4J_QUERY_TIMEOUT'):
            config_dict.setdefault('performance', {})['query_timeout'] = int(os.getenv('NEO4J_QUERY_TIMEOUT'))

        if os.getenv('NEO4J_BATCH_SIZE'):
            config_dict.setdefault('performance', {})['batch_size'] = int(os.getenv('NEO4J_BATCH_SIZE'))

        return Neo4jConfig.from_dict(config_dict)


def load_neo4j_config(config_path: Optional[Path] = None) -> Neo4jConfig:
    """Convenience function to load Neo4j configuration."""
    return ConfigLoader.load_config(config_path)
