"""Neo4j Graph Interface - A decoupled, reusable Neo4j graph interface."""

from .neo4j_client import Neo4jClient
from .models import (
    GraphNode,
    GraphRelationship,
    GraphPath,
    GraphStats,
    QueryResult,
    HealthCheckResult,
    ConnectionStatus
)
from .config import (
    Neo4jConfig,
    Neo4jConnectionConfig,
    Neo4jPoolConfig,
    Neo4jPerformanceConfig,
    Neo4jIndexConfig,
    ConfigLoader,
    load_neo4j_config
)
from .exceptions import (
    GraphInterfaceError,
    Neo4jConnectionError,
    Neo4jQueryError,
    Neo4jConfigurationError,
    GraphOperationError,
    NodeNotFoundError,
    RelationshipNotFoundError,
    ValidationError,
    TransactionError
)

__version__ = "0.1.0"
__author__ = "MCP Planning Team"

__all__ = [
    # Core client
    "Neo4jClient",

    # Data models
    "GraphNode",
    "GraphRelationship",
    "GraphPath",
    "GraphStats",
    "QueryResult",
    "HealthCheckResult",
    "ConnectionStatus",

    # Configuration
    "Neo4jConfig",
    "Neo4jConnectionConfig",
    "Neo4jPoolConfig",
    "Neo4jPerformanceConfig",
    "Neo4jIndexConfig",
    "ConfigLoader",
    "load_neo4j_config",

    # Exceptions
    "GraphInterfaceError",
    "Neo4jConnectionError",
    "Neo4jQueryError",
    "Neo4jConfigurationError",
    "GraphOperationError",
    "NodeNotFoundError",
    "RelationshipNotFoundError",
    "ValidationError",
    "TransactionError",
]
