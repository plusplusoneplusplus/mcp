"""Custom exceptions for the Neo4j graph interface."""

from typing import Optional, Any, Dict


class GraphInterfaceError(Exception):
    """Base exception for all graph interface errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class Neo4jConnectionError(GraphInterfaceError):
    """Raised when Neo4j connection fails."""

    def __init__(self, message: str, uri: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.uri = uri


class Neo4jQueryError(GraphInterfaceError):
    """Raised when Neo4j query execution fails."""

    def __init__(self, message: str, query: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.query = query
        self.parameters = parameters


class Neo4jConfigurationError(GraphInterfaceError):
    """Raised when Neo4j configuration is invalid."""

    def __init__(self, message: str, config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.config_key = config_key


class GraphOperationError(GraphInterfaceError):
    """Raised when graph operations fail."""

    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.operation = operation


class NodeNotFoundError(GraphOperationError):
    """Raised when a requested node is not found."""

    def __init__(self, node_id: str, labels: Optional[list] = None, details: Optional[Dict[str, Any]] = None):
        message = f"Node with ID '{node_id}' not found"
        if labels:
            message += f" with labels {labels}"
        super().__init__(message, "node_lookup", details)
        self.node_id = node_id
        self.labels = labels


class RelationshipNotFoundError(GraphOperationError):
    """Raised when a requested relationship is not found."""

    def __init__(self, start_node_id: str, end_node_id: str, rel_type: str, details: Optional[Dict[str, Any]] = None):
        message = f"Relationship '{rel_type}' from '{start_node_id}' to '{end_node_id}' not found"
        super().__init__(message, "relationship_lookup", details)
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        self.rel_type = rel_type


class ValidationError(GraphInterfaceError):
    """Raised when data validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.field = field
        self.value = value


class TransactionError(GraphInterfaceError):
    """Raised when transaction operations fail."""

    def __init__(self, message: str, transaction_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.transaction_id = transaction_id
