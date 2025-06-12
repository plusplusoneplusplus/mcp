"""Tests for graph interface data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from ..models import (
    GraphNode,
    GraphRelationship,
    GraphPath,
    GraphStats,
    QueryResult,
    HealthCheckResult,
    ConnectionStatus
)


class TestGraphNode:
    """Test GraphNode model."""

    def test_create_node_with_minimal_data(self):
        """Test creating node with minimal required data."""
        node = GraphNode(id="test-node")
        assert node.id == "test-node"
        assert node.labels == []
        assert node.properties == {}
        assert isinstance(node.created_at, datetime)
        assert isinstance(node.updated_at, datetime)

    def test_create_node_with_full_data(self):
        """Test creating node with all data."""
        properties = {"name": "Test Node", "value": 42}
        labels = ["TestLabel", "AnotherLabel"]

        node = GraphNode(
            id="test-node",
            labels=labels,
            properties=properties
        )

        assert node.id == "test-node"
        assert node.labels == labels
        assert node.properties == properties

    def test_node_id_validation(self):
        """Test node ID validation."""
        # Empty ID should raise error
        with pytest.raises(ValidationError):
            GraphNode(id="")

        # Whitespace-only ID should raise error
        with pytest.raises(ValidationError):
            GraphNode(id="   ")

        # Valid ID with whitespace should be stripped
        node = GraphNode(id="  test-node  ")
        assert node.id == "test-node"

    def test_labels_validation(self):
        """Test labels validation."""
        # Empty labels should be filtered out
        with pytest.raises(ValidationError):
            GraphNode(id="test", labels=["valid", "", "another"])

        # Labels with whitespace should be stripped
        node = GraphNode(id="test", labels=["  label1  ", "label2"])
        assert node.labels == ["label1", "label2"]

    def test_node_methods(self):
        """Test node utility methods."""
        node = GraphNode(id="test")

        # Test label operations
        node.add_label("TestLabel")
        assert node.has_label("TestLabel")
        assert "TestLabel" in node.labels

        # Adding duplicate label should not duplicate
        node.add_label("TestLabel")
        assert node.labels.count("TestLabel") == 1

        node.remove_label("TestLabel")
        assert not node.has_label("TestLabel")

        # Test property operations
        node.set_property("key", "value")
        assert node.get_property("key") == "value"
        assert node.get_property("nonexistent", "default") == "default"

        node.remove_property("key")
        assert node.get_property("key") is None


class TestGraphRelationship:
    """Test GraphRelationship model."""

    def test_create_relationship_minimal(self):
        """Test creating relationship with minimal data."""
        rel = GraphRelationship(
            type="CONNECTS",
            start_node_id="node1",
            end_node_id="node2"
        )

        assert rel.type == "CONNECTS"
        assert rel.start_node_id == "node1"
        assert rel.end_node_id == "node2"
        assert rel.properties == {}
        assert isinstance(rel.created_at, datetime)

    def test_relationship_type_validation(self):
        """Test relationship type validation."""
        # Empty type should raise error
        with pytest.raises(ValidationError):
            GraphRelationship(type="", start_node_id="n1", end_node_id="n2")

        # Type should be converted to uppercase
        rel = GraphRelationship(
            type="connects",
            start_node_id="n1",
            end_node_id="n2"
        )
        assert rel.type == "CONNECTS"

    def test_node_id_validation(self):
        """Test node ID validation."""
        # Empty node IDs should raise error
        with pytest.raises(ValidationError):
            GraphRelationship(type="TEST", start_node_id="", end_node_id="n2")

        with pytest.raises(ValidationError):
            GraphRelationship(type="TEST", start_node_id="n1", end_node_id="")

    def test_relationship_methods(self):
        """Test relationship utility methods."""
        rel = GraphRelationship(
            type="TEST",
            start_node_id="n1",
            end_node_id="n2"
        )

        # Test property operations
        rel.set_property("weight", 1.5)
        assert rel.get_property("weight") == 1.5

        rel.remove_property("weight")
        assert rel.get_property("weight") is None


class TestGraphPath:
    """Test GraphPath model."""

    def test_create_empty_path(self):
        """Test creating empty path."""
        path = GraphPath()
        assert path.nodes == []
        assert path.relationships == []
        assert path.length == 0
        assert path.total_weight is None

    def test_path_length_validation(self):
        """Test path length validation."""
        # Length should match relationships count
        with pytest.raises(ValidationError):
            GraphPath(length=2, relationships=[])

    def test_path_operations(self):
        """Test path utility methods."""
        path = GraphPath()

        node1 = GraphNode(id="n1")
        node2 = GraphNode(id="n2")
        rel = GraphRelationship(type="CONNECTS", start_node_id="n1", end_node_id="n2")

        path.add_node(node1)
        path.add_node(node2)
        path.add_relationship(rel)

        assert len(path.nodes) == 2
        assert len(path.relationships) == 1
        assert path.length == 1


class TestGraphStats:
    """Test GraphStats model."""

    def test_create_stats(self):
        """Test creating graph stats."""
        stats = GraphStats(
            node_count=100,
            relationship_count=200,
            labels={"Person": 50, "Company": 50},
            relationship_types={"WORKS_FOR": 100, "KNOWS": 100}
        )

        assert stats.node_count == 100
        assert stats.relationship_count == 200
        assert stats.labels["Person"] == 50

    def test_density_calculation(self):
        """Test graph density calculation."""
        stats = GraphStats(node_count=4, relationship_count=6)
        density = stats.calculate_density()

        # For 4 nodes, max relationships = 4 * 3 = 12
        # Density = 6 / 12 = 0.5
        assert density == 0.5
        assert stats.density == 0.5

    def test_density_validation(self):
        """Test density validation."""
        with pytest.raises(ValidationError):
            GraphStats(density=1.5)  # > 1

        with pytest.raises(ValidationError):
            GraphStats(density=-0.1)  # < 0


class TestQueryResult:
    """Test QueryResult model."""

    def test_create_query_result(self):
        """Test creating query result."""
        records = [{"name": "Alice"}, {"name": "Bob"}]
        summary = {"query_type": "r", "counters": {}}

        result = QueryResult(
            records=records,
            summary=summary,
            execution_time=0.123
        )

        assert result.records == records
        assert result.summary == summary
        assert result.execution_time == 0.123


class TestHealthCheckResult:
    """Test HealthCheckResult model."""

    def test_create_health_check_result(self):
        """Test creating health check result."""
        result = HealthCheckResult(
            status=ConnectionStatus.CONNECTED,
            response_time=0.05,
            database_info={"version": "5.0"}
        )

        assert result.status == ConnectionStatus.CONNECTED
        assert result.response_time == 0.05
        assert result.database_info["version"] == "5.0"
        assert isinstance(result.timestamp, datetime)

    def test_error_health_check(self):
        """Test error health check result."""
        result = HealthCheckResult(
            status=ConnectionStatus.ERROR,
            error_message="Connection failed"
        )

        assert result.status == ConnectionStatus.ERROR
        assert result.error_message == "Connection failed"


class TestConnectionStatus:
    """Test ConnectionStatus enum."""

    def test_connection_status_values(self):
        """Test connection status enum values."""
        assert ConnectionStatus.DISCONNECTED == "disconnected"
        assert ConnectionStatus.CONNECTING == "connecting"
        assert ConnectionStatus.CONNECTED == "connected"
        assert ConnectionStatus.ERROR == "error"
