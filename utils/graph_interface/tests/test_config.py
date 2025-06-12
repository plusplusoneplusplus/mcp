"""Tests for graph interface configuration."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from ..config import (
    Neo4jConnectionConfig,
    Neo4jPoolConfig,
    Neo4jPerformanceConfig,
    Neo4jIndexConfig,
    Neo4jConfig,
    ConfigLoader,
    load_neo4j_config
)
from ..exceptions import Neo4jConfigurationError


class TestNeo4jConnectionConfig:
    """Test Neo4j connection configuration."""

    def test_default_config(self):
        """Test default connection configuration."""
        config = Neo4jConnectionConfig()
        assert config.uri == "bolt://localhost:7687"
        assert config.username == "neo4j"
        assert config.password_env == "NEO4J_PASSWORD"
        assert config.database == "neo4j"

    def test_uri_validation(self):
        """Test URI validation."""
        # Valid URIs
        valid_uris = [
            "bolt://localhost:7687",
            "bolt+s://localhost:7687",
            "neo4j://localhost:7687",
            "neo4j+s://localhost:7687"
        ]

        for uri in valid_uris:
            config = Neo4jConnectionConfig(uri=uri)
            assert config.uri == uri

    @patch.dict(os.environ, {'TEST_PASSWORD': 'secret123'})
    def test_password_from_env(self):
        """Test password retrieval from environment."""
        config = Neo4jConnectionConfig(password_env='TEST_PASSWORD')
        assert config.password == 'secret123'

    def test_password_missing_env(self):
        """Test error when password environment variable is missing."""
        config = Neo4jConnectionConfig(password_env='NONEXISTENT_PASSWORD')
        with pytest.raises(Neo4jConfigurationError):
            _ = config.password


class TestNeo4jPoolConfig:
    """Test Neo4j pool configuration."""

    def test_default_config(self):
        """Test default pool configuration."""
        config = Neo4jPoolConfig()
        assert config.max_connections == 50
        assert config.connection_timeout == 30
        assert config.max_retry_time == 30


class TestNeo4jPerformanceConfig:
    """Test Neo4j performance configuration."""

    def test_default_config(self):
        """Test default performance configuration."""
        config = Neo4jPerformanceConfig()
        assert config.query_timeout == 60
        assert config.batch_size == 1000
        assert config.enable_query_logging is False


class TestNeo4jIndexConfig:
    """Test Neo4j index configuration."""

    def test_default_config(self):
        """Test default index configuration."""
        config = Neo4jIndexConfig()
        assert config.auto_create is True
        assert config.node_indexes == []
        assert config.relationship_indexes == []


class TestNeo4jConfig:
    """Test complete Neo4j configuration."""

    def test_default_config(self):
        """Test default complete configuration."""
        config = Neo4jConfig()
        assert isinstance(config.connection, Neo4jConnectionConfig)
        assert isinstance(config.pool, Neo4jPoolConfig)
        assert isinstance(config.performance, Neo4jPerformanceConfig)
        assert isinstance(config.indexes, Neo4jIndexConfig)

    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            'connection': {
                'uri': 'bolt://test:7687',
                'username': 'testuser'
            },
            'pool': {
                'max_connections': 100
            }
        }

        config = Neo4jConfig.from_dict(config_dict)
        assert config.connection.uri == 'bolt://test:7687'
        assert config.connection.username == 'testuser'
        assert config.pool.max_connections == 100

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = Neo4jConfig()
        config_dict = config.to_dict()

        assert 'connection' in config_dict
        assert 'pool' in config_dict
        assert 'performance' in config_dict
        assert 'indexes' in config_dict

    def test_from_yaml_file(self):
        """Test loading config from YAML file."""
        yaml_content = """
neo4j:
  connection:
    uri: "bolt://test:7687"
    username: "testuser"
  pool:
    max_connections: 100
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = Neo4jConfig.from_yaml_file(Path(f.name))
                assert config.connection.uri == "bolt://test:7687"
                assert config.connection.username == "testuser"
                assert config.pool.max_connections == 100
            finally:
                os.unlink(f.name)

    def test_to_yaml_file(self):
        """Test saving config to YAML file."""
        config = Neo4jConfig()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            try:
                config.to_yaml_file(Path(f.name))

                # Verify file was created and contains expected content
                with open(f.name, 'r') as read_f:
                    content = read_f.read()
                    assert 'neo4j:' in content
                    assert 'connection:' in content
                    assert 'pool:' in content
            finally:
                os.unlink(f.name)


class TestConfigLoader:
    """Test configuration loader."""

    def test_load_default_config(self):
        """Test loading default configuration when no file exists."""
        # Test with None to get default config
        config = ConfigLoader.load_config(None)
        assert isinstance(config, Neo4jConfig)

    @patch.dict(os.environ, {
        'NEO4J_URI': 'bolt://env:7687',
        'NEO4J_USERNAME': 'envuser',
        'NEO4J_MAX_CONNECTIONS': '75'
    })
    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        config = ConfigLoader.load_from_env()

        assert config.connection.uri == 'bolt://env:7687'
        assert config.connection.username == 'envuser'
        assert config.pool.max_connections == 75


def test_load_neo4j_config():
    """Test convenience function."""
    config = load_neo4j_config()
    assert isinstance(config, Neo4jConfig)
