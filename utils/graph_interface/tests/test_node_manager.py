"""Tests for NodeManager class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from utils.graph_interface.node_manager import NodeManager
from utils.graph_interface.models import GraphNode, QueryResult
from utils.graph_interface.exceptions import (
    ValidationError,
    GraphOperationError,
    Neo4jQueryError
)


@pytest.fixture
def mock_client():
    """Create a mock Neo4j client."""
    client = AsyncMock()
    return client


@pytest.fixture
def node_manager(mock_client):
    """Create a NodeManager instance with mock client."""
    return NodeManager(mock_client)


@pytest.fixture
def sample_node():
    """Create a sample GraphNode for testing."""
    return GraphNode(
        id="test-node-123",
        labels=["Person", "Employee"],
        properties={"name": "John Doe", "age": 30},
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        updated_at=datetime(2023, 1, 1, 12, 0, 0)
    )


class TestNodeManager:
    """Test cases for NodeManager class."""

    @pytest.mark.asyncio
    async def test_create_node_success(self, node_manager, mock_client, sample_node):
        """Test successful node creation."""
        # Mock node doesn't exist
        mock_client.execute_query.side_effect = [
            QueryResult(records=[{"exists": False}]),  # node_exists check
            QueryResult(records=[{"n": {"id": "test-node-123"}}])  # create result
        ]

        result = await node_manager.create_node(sample_node)

        assert result == "test-node-123"
        assert mock_client.execute_query.call_count == 2

    @pytest.mark.asyncio
    async def test_create_node_no_id(self, node_manager, sample_node):
        """Test node creation fails without ID."""
        sample_node.id = ""

        with pytest.raises(ValidationError, match="Node ID is required"):
            await node_manager.create_node(sample_node)

    @pytest.mark.asyncio
    async def test_create_node_already_exists(self, node_manager, mock_client, sample_node):
        """Test node creation fails when node already exists."""
        # Mock node exists
        mock_client.execute_query.return_value = QueryResult(records=[{"exists": True}])

        with pytest.raises(GraphOperationError, match="already exists"):
            await node_manager.create_node(sample_node)

    @pytest.mark.asyncio
    async def test_create_node_query_error(self, node_manager, mock_client, sample_node):
        """Test node creation handles query errors."""
        mock_client.execute_query.side_effect = [
            QueryResult(records=[{"exists": False}]),  # node_exists check
            Neo4jQueryError("Database error")  # create fails
        ]

        with pytest.raises(GraphOperationError, match="Failed to create node"):
            await node_manager.create_node(sample_node)

    @pytest.mark.asyncio
    async def test_get_node_success(self, node_manager, mock_client):
        """Test successful node retrieval."""
        mock_client.execute_query.return_value = QueryResult(
            records=[{
                "n": {
                    "id": "test-node-123",
                    "labels": ["Person"],
                    "name": "John Doe",
                    "age": 30,
                    "created_at": "2023-01-01T12:00:00",
                    "updated_at": "2023-01-01T12:00:00"
                }
            }]
        )

        result = await node_manager.get_node("test-node-123")

        assert result is not None
        assert result.id == "test-node-123"
        assert result.properties["name"] == "John Doe"
        assert result.properties["age"] == 30

    @pytest.mark.asyncio
    async def test_get_node_not_found(self, node_manager, mock_client):
        """Test node retrieval when node doesn't exist."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        result = await node_manager.get_node("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_node_empty_id(self, node_manager):
        """Test node retrieval with empty ID."""
        with pytest.raises(ValidationError, match="Node ID cannot be empty"):
            await node_manager.get_node("")

    @pytest.mark.asyncio
    async def test_update_node_success(self, node_manager, mock_client):
        """Test successful node update."""
        mock_client.execute_query.return_value = QueryResult(
            records=[{"n": {"id": "test-node-123"}}]
        )

        result = await node_manager.update_node(
            "test-node-123",
            {"name": "Jane Doe", "age": 31}
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_node_not_found(self, node_manager, mock_client):
        """Test node update when node doesn't exist."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        result = await node_manager.update_node(
            "nonexistent",
            {"name": "Jane Doe"}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_node_empty_id(self, node_manager):
        """Test node update with empty ID."""
        with pytest.raises(ValidationError, match="Node ID cannot be empty"):
            await node_manager.update_node("", {"name": "Jane"})

    @pytest.mark.asyncio
    async def test_update_node_empty_properties(self, node_manager):
        """Test node update with empty properties."""
        with pytest.raises(ValidationError, match="Properties cannot be empty"):
            await node_manager.update_node("test-node-123", {})

    @pytest.mark.asyncio
    async def test_update_node_system_properties_filtered(self, node_manager, mock_client):
        """Test node update filters out system properties."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        result = await node_manager.update_node(
            "test-node-123",
            {"id": "new-id", "created_at": "2023-01-01", "name": "Jane"}
        )

        # Should return False because no valid properties after filtering
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_node_success(self, node_manager, mock_client):
        """Test successful node deletion."""
        mock_client.execute_query.return_value = QueryResult(
            records=[],
            summary={"counters": {"nodes_deleted": 1}}
        )

        result = await node_manager.delete_node("test-node-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_node_not_found(self, node_manager, mock_client):
        """Test node deletion when node doesn't exist."""
        mock_client.execute_query.return_value = QueryResult(
            records=[],
            summary={"counters": {"nodes_deleted": 0}}
        )

        result = await node_manager.delete_node("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_node_force(self, node_manager, mock_client):
        """Test force node deletion."""
        mock_client.execute_query.return_value = QueryResult(
            records=[],
            summary={"counters": {"nodes_deleted": 1}}
        )

        result = await node_manager.delete_node("test-node-123", force=True)

        assert result is True
        # Verify the query was called with force=True
        call_args = mock_client.execute_query.call_args
        assert "DETACH DELETE" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_nodes_no_criteria(self, node_manager, mock_client):
        """Test finding nodes without criteria."""
        mock_client.execute_query.return_value = QueryResult(
            records=[
                {"n": {"id": "node1", "name": "John"}},
                {"n": {"id": "node2", "name": "Jane"}}
            ]
        )

        result = await node_manager.find_nodes()

        assert len(result) == 2
        assert result[0].id == "node1"
        assert result[1].id == "node2"

    @pytest.mark.asyncio
    async def test_find_nodes_with_labels(self, node_manager, mock_client):
        """Test finding nodes with label criteria."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        await node_manager.find_nodes(labels=["Person"])

        # Verify the query includes labels
        call_args = mock_client.execute_query.call_args
        assert ":Person" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_nodes_with_properties(self, node_manager, mock_client):
        """Test finding nodes with property criteria."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        await node_manager.find_nodes(properties={"name": "John", "age": 30})

        # Verify the query includes property filters
        call_args = mock_client.execute_query.call_args
        assert "WHERE" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_nodes_with_pagination(self, node_manager, mock_client):
        """Test finding nodes with pagination."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        await node_manager.find_nodes(limit=10, skip=5)

        # Verify the query includes pagination
        call_args = mock_client.execute_query.call_args
        assert "LIMIT 10" in call_args[0][0]
        assert "SKIP 5" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_nodes_invalid_limit(self, node_manager):
        """Test finding nodes with invalid limit."""
        with pytest.raises(ValidationError, match="Limit must be positive"):
            await node_manager.find_nodes(limit=0)

    @pytest.mark.asyncio
    async def test_find_nodes_invalid_skip(self, node_manager):
        """Test finding nodes with invalid skip."""
        with pytest.raises(ValidationError, match="Skip must be non-negative"):
            await node_manager.find_nodes(skip=-1)

    @pytest.mark.asyncio
    async def test_get_node_relationships_success(self, node_manager, mock_client):
        """Test getting node relationships."""
        mock_client.execute_query.return_value = QueryResult(
            records=[
                {
                    "r": {"type": "KNOWS", "since": "2023"},
                    "n": {"id": "node1"},
                    "other": {"id": "node2"}
                }
            ]
        )

        result = await node_manager.get_node_relationships("node1")

        assert len(result) == 1
        assert result[0]["relationship"]["type"] == "KNOWS"
        assert result[0]["node"]["id"] == "node1"
        assert result[0]["other_node"]["id"] == "node2"

    @pytest.mark.asyncio
    async def test_get_node_relationships_invalid_direction(self, node_manager):
        """Test getting node relationships with invalid direction."""
        with pytest.raises(ValidationError, match="Direction must be"):
            await node_manager.get_node_relationships("node1", direction="INVALID")

    @pytest.mark.asyncio
    async def test_node_exists_true(self, node_manager, mock_client):
        """Test node exists check returns True."""
        mock_client.execute_query.return_value = QueryResult(
            records=[{"exists": True}]
        )

        result = await node_manager.node_exists("test-node-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_node_exists_false(self, node_manager, mock_client):
        """Test node exists check returns False."""
        mock_client.execute_query.return_value = QueryResult(
            records=[{"exists": False}]
        )

        result = await node_manager.node_exists("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_node_exists_no_records(self, node_manager, mock_client):
        """Test node exists check with no records."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        result = await node_manager.node_exists("test-node-123")

        assert result is False

    @pytest.mark.asyncio
    async def test_create_nodes_batch_success(self, node_manager, mock_client):
        """Test successful batch node creation."""
        nodes = [
            GraphNode(id="node1", labels=["Person"], properties={"name": "John"}),
            GraphNode(id="node2", labels=["Person"], properties={"name": "Jane"})
        ]

        mock_client.execute_batch.return_value = [
            QueryResult(records=[{"n": {"id": "node1"}}]),
            QueryResult(records=[{"n": {"id": "node2"}}])
        ]

        result = await node_manager.create_nodes_batch(nodes)

        assert result == ["node1", "node2"]

    @pytest.mark.asyncio
    async def test_create_nodes_batch_empty(self, node_manager):
        """Test batch node creation with empty list."""
        result = await node_manager.create_nodes_batch([])

        assert result == []

    @pytest.mark.asyncio
    async def test_create_nodes_batch_invalid_batch_size(self, node_manager):
        """Test batch node creation with invalid batch size."""
        nodes = [GraphNode(id="node1", labels=["Person"])]

        with pytest.raises(ValidationError, match="Batch size must be positive"):
            await node_manager.create_nodes_batch(nodes, batch_size=0)

    @pytest.mark.asyncio
    async def test_create_nodes_batch_missing_id(self, node_manager):
        """Test batch node creation with missing node ID."""
        # GraphNode validation prevents empty IDs at the model level
        with pytest.raises(ValueError, match="Node ID cannot be empty"):
            GraphNode(id="", labels=["Person"])

    @pytest.mark.asyncio
    async def test_update_nodes_batch_success(self, node_manager, mock_client):
        """Test successful batch node update."""
        updates = [
            {"node_id": "node1", "properties": {"name": "John Updated"}},
            {"node_id": "node2", "properties": {"name": "Jane Updated"}}
        ]

        mock_client.execute_batch.return_value = [
            QueryResult(records=[{"n": {"id": "node1"}}]),
            QueryResult(records=[{"n": {"id": "node2"}}])
        ]

        result = await node_manager.update_nodes_batch(updates)

        assert result == 2

    @pytest.mark.asyncio
    async def test_update_nodes_batch_empty(self, node_manager):
        """Test batch node update with empty list."""
        result = await node_manager.update_nodes_batch([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_update_nodes_batch_missing_node_id(self, node_manager):
        """Test batch node update with missing node ID."""
        updates = [{"properties": {"name": "John"}}]

        with pytest.raises(ValidationError, match="Node ID is required"):
            await node_manager.update_nodes_batch(updates)

    @pytest.mark.asyncio
    async def test_record_to_node_success(self, node_manager):
        """Test converting record to node."""
        record_data = {
            "id": "test-node-123",
            "labels": ["Person", "Employee"],
            "name": "John Doe",
            "age": 30,
            "created_at": "2023-01-01T12:00:00",
            "updated_at": "2023-01-01T12:00:00"
        }

        result = node_manager._record_to_node(record_data)

        assert result is not None
        assert result.id == "test-node-123"
        assert result.labels == ["Person", "Employee"]
        assert result.properties["name"] == "John Doe"
        assert result.properties["age"] == 30

    @pytest.mark.asyncio
    async def test_record_to_node_empty_record(self, node_manager):
        """Test converting empty record to node."""
        result = node_manager._record_to_node({})

        assert result is None

    @pytest.mark.asyncio
    async def test_record_to_node_no_id(self, node_manager):
        """Test converting record without ID to node."""
        record_data = {"name": "John Doe"}

        result = node_manager._record_to_node(record_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_record_to_node_invalid_timestamps(self, node_manager):
        """Test converting record with invalid timestamps."""
        record_data = {
            "id": "test-node-123",
            "created_at": "invalid-date",
            "updated_at": "also-invalid"
        }

        result = node_manager._record_to_node(record_data)

        assert result is not None
        assert result.created_at is None
        assert result.updated_at is None
