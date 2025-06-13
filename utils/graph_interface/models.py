"""Data models for the Neo4j graph interface."""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class QueryResult(BaseModel):
    """Result of a Neo4j query execution."""

    records: List[Dict[str, Any]] = Field(default_factory=list, description="Query result records")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Query execution summary")
    execution_time: float = Field(0.0, description="Query execution time in seconds")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GraphNode(BaseModel):
    """Generic graph node representation."""

    id: str = Field(..., description="Unique node identifier")
    labels: List[str] = Field(default_factory=list, description="Node labels")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        """Validate node ID is not empty."""
        if not v or not v.strip():
            raise ValueError("Node ID cannot be empty")
        return v.strip()

    @field_validator('labels')
    @classmethod
    def validate_labels(cls, v):
        """Validate labels are non-empty strings."""
        if v:
            for label in v:
                if not isinstance(label, str) or not label.strip():
                    raise ValueError("All labels must be non-empty strings")
        return [label.strip() for label in v]

    def add_label(self, label: str) -> None:
        """Add a label to the node."""
        if label and label.strip() and label not in self.labels:
            self.labels.append(label.strip())

    def remove_label(self, label: str) -> None:
        """Remove a label from the node."""
        if label in self.labels:
            self.labels.remove(label)

    def has_label(self, label: str) -> bool:
        """Check if node has a specific label."""
        return label in self.labels

    def set_property(self, key: str, value: Any) -> None:
        """Set a property on the node."""
        self.properties[key] = value
        self.updated_at = datetime.utcnow()

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a property from the node."""
        return self.properties.get(key, default)

    def remove_property(self, key: str) -> None:
        """Remove a property from the node."""
        if key in self.properties:
            del self.properties[key]
            self.updated_at = datetime.utcnow()

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GraphRelationship(BaseModel):
    """Generic graph relationship representation."""

    id: Optional[str] = Field(None, description="Relationship ID (if available)")
    type: str = Field(..., description="Relationship type")
    start_node_id: str = Field(..., description="Start node ID")
    end_node_id: str = Field(..., description="End node ID")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Relationship properties")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        """Validate relationship type is not empty."""
        if not v or not v.strip():
            raise ValueError("Relationship type cannot be empty")
        return v.strip().upper()  # Neo4j convention: uppercase relationship types

    @field_validator('start_node_id', 'end_node_id')
    @classmethod
    def validate_node_ids(cls, v):
        """Validate node IDs are not empty."""
        if not v or not v.strip():
            raise ValueError("Node IDs cannot be empty")
        return v.strip()

    def set_property(self, key: str, value: Any) -> None:
        """Set a property on the relationship."""
        self.properties[key] = value

    def get_property(self, key: str, default: Any = None) -> Any:
        """Get a property from the relationship."""
        return self.properties.get(key, default)

    def remove_property(self, key: str) -> None:
        """Remove a property from the relationship."""
        if key in self.properties:
            del self.properties[key]

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GraphPath(BaseModel):
    """Represents a path in the graph."""

    nodes: List[GraphNode] = Field(default_factory=list, description="Nodes in the path")
    relationships: List[GraphRelationship] = Field(default_factory=list, description="Relationships in the path")
    length: int = Field(0, description="Path length (number of relationships)")
    total_weight: Optional[float] = Field(None, description="Total path weight (if applicable)")

    @field_validator('length')
    @classmethod
    def validate_length(cls, v, info):
        """Validate path length matches relationships count."""
        if hasattr(info, 'data') and 'relationships' in info.data:
            relationships = info.data.get('relationships', [])
            if v != len(relationships):
                raise ValueError("Path length must equal the number of relationships")
        return v

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the path."""
        self.nodes.append(node)

    def add_relationship(self, relationship: GraphRelationship) -> None:
        """Add a relationship to the path."""
        self.relationships.append(relationship)
        self.length = len(self.relationships)

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GraphStats(BaseModel):
    """Graph statistics and metrics."""

    node_count: int = Field(0, description="Total number of nodes")
    relationship_count: int = Field(0, description="Total number of relationships")
    labels: Dict[str, int] = Field(default_factory=dict, description="Node labels and their counts")
    relationship_types: Dict[str, int] = Field(default_factory=dict, description="Relationship types and their counts")
    density: Optional[float] = Field(None, description="Graph density (0-1)")
    is_connected: Optional[bool] = Field(None, description="Whether the graph is connected")

    @field_validator('density')
    @classmethod
    def validate_density(cls, v):
        """Validate density is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("Graph density must be between 0 and 1")
        return v

    def calculate_density(self) -> float:
        """Calculate graph density."""
        if self.node_count < 2:
            return 0.0

        max_relationships = self.node_count * (self.node_count - 1)
        if max_relationships == 0:
            return 0.0

        self.density = self.relationship_count / max_relationships
        return self.density

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ConnectionStatus(str, Enum):
    """Neo4j connection status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class HealthCheckResult(BaseModel):
    """Result of a Neo4j health check."""

    status: ConnectionStatus = Field(..., description="Connection status")
    response_time: Optional[float] = Field(None, description="Response time in seconds")
    error_message: Optional[str] = Field(None, description="Error message if status is ERROR")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    database_info: Optional[Dict[str, Any]] = Field(None, description="Database information")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
