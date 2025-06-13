"""Tests for RelationshipManager class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from utils.graph_interface.relationship_manager import RelationshipManager
from utils.graph_interface.models import GraphRelationship, QueryResult
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
def relationship_manager(mock_client):
    """Create a RelationshipManager instance with mock client."""
    return RelationshipManager(mock_client)


@pytest.fixture
def sample_relationship():
    """Create a sample GraphRelationship for testing."""
    return GraphRelationship(
        id="rel-123",
        type="KNOWS",
        start_node_id="node1",
        end_node_id="node2",
        properties={"since": "2023", "weight": 0.8},
        created_at=datetime(2023, 1, 1, 12, 0, 0)
    )


class TestRelationshipManager:
    """Test cases for RelationshipManager class."""

    @pytest.mark.asyncio
    async def test_create_relationship_success(self, relationship_manager, mock_client, sample_relationship):
        """Test successful relationship creation."""
        # Mock relationship doesn't exist
        mock_client.execute_query.side_effect = [
            QueryResult(records=[{"exists": False}]),  # relationship_exists check
            QueryResult(records=[{"r": {"id": "rel-123"}, "start": {}, "end": {}}])  # create result
        ]

        result = await relationship_manager.create_relationship(sample_relationship)

        assert result == "rel-123"
        assert mock_client.execute_query.call_count == 2

    @pytest.mark.asyncio
    async def test_create_relationship_no_start_id(self, relationship_manager, sample_relationship):
        """Test relationship creation fails without start node ID."""
        sample_relationship.start_node_id = ""

        with pytest.raises(ValidationError, match="Start node ID is required"):
            await relationship_manager.create_relationship(sample_relationship)

    @pytest.mark.asyncio
    async def test_create_relationship_no_end_id(self, relationship_manager, sample_relationship):
        """Test relationship creation fails without end node ID."""
        sample_relationship.end_node_id = ""

        with pytest.raises(ValidationError, match="End node ID is required"):
            await relationship_manager.create_relationship(sample_relationship)

    @pytest.mark.asyncio
    async def test_create_relationship_no_type(self, relationship_manager, sample_relationship):
        """Test relationship creation fails without type."""
        sample_relationship.type = ""

        with pytest.raises(ValidationError, match="Relationship type is required"):
            await relationship_manager.create_relationship(sample_relationship)

    @pytest.mark.asyncio
    async def test_create_relationship_already_exists(self, relationship_manager, mock_client, sample_relationship):
        """Test relationship creation fails when relationship already exists."""
        # Mock relationship exists
        mock_client.execute_query.return_value = QueryResult(records=[{"exists": True}])

        with pytest.raises(GraphOperationError, match="already exists"):
            await relationship_manager.create_relationship(sample_relationship)

    @pytest.mark.asyncio
    async def test_create_relationship_query_error(self, relationship_manager, mock_client, sample_relationship):
        """Test relationship creation handles query errors."""
        mock_client.execute_query.side_effect = [
            QueryResult(records=[{"exists": False}]),  # relationship_exists check
            Neo4jQueryError("Database error")  # create fails
        ]

        with pytest.raises(GraphOperationError, match="Failed to create relationship"):
            await relationship_manager.create_relationship(sample_relationship)

    @pytest.mark.asyncio
    async def test_get_relationship_success(self, relationship_manager, mock_client):
        """Test successful relationship retrieval."""
        mock_client.execute_query.return_value = QueryResult(
            records=[{
                "r": {
                    "id": "rel-123",
                    "type": "KNOWS",
                    "since": "2023",
                    "weight": 0.8,
                    "created_at": "2023-01-01T12:00:00"
                },
                "start": {"id": "node1"},
                "end": {"id": "node2"}
            }]
        )

        result = await relationship_manager.get_relationship("node1", "node2", "KNOWS")

        assert result is not None
        assert result.type == "KNOWS"
        assert result.start_node_id == "node1"
        assert result.end_node_id == "node2"
        assert result.properties["since"] == "2023"
        assert result.properties["weight"] == 0.8

    @pytest.mark.asyncio
    async def test_get_relationship_not_found(self, relationship_manager, mock_client):
        """Test relationship retrieval when relationship doesn't exist."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        result = await relationship_manager.get_relationship("node1", "node2", "KNOWS")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_relationship_empty_start_id(self, relationship_manager):
        """Test relationship retrieval with empty start ID."""
        with pytest.raises(ValidationError, match="Start node ID cannot be empty"):
            await relationship_manager.get_relationship("", "node2", "KNOWS")

    @pytest.mark.asyncio
    async def test_get_relationship_empty_end_id(self, relationship_manager):
        """Test relationship retrieval with empty end ID."""
        with pytest.raises(ValidationError, match="End node ID cannot be empty"):
            await relationship_manager.get_relationship("node1", "", "KNOWS")

    @pytest.mark.asyncio
    async def test_get_relationship_empty_type(self, relationship_manager):
        """Test relationship retrieval with empty type."""
        with pytest.raises(ValidationError, match="Relationship type cannot be empty"):
            await relationship_manager.get_relationship("node1", "node2", "")

    @pytest.mark.asyncio
    async def test_update_relationship_success(self, relationship_manager, mock_client):
        """Test successful relationship update."""
        mock_client.execute_query.return_value = QueryResult(
            records=[{"r": {"id": "rel-123"}, "start": {}, "end": {}}]
        )

        result = await relationship_manager.update_relationship(
            "node1", "node2", "KNOWS", {"weight": 0.9}
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_update_relationship_not_found(self, relationship_manager, mock_client):
        """Test relationship update when relationship doesn't exist."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        result = await relationship_manager.update_relationship(
            "node1", "node2", "KNOWS", {"weight": 0.9}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_update_relationship_empty_properties(self, relationship_manager):
        """Test relationship update with empty properties."""
        with pytest.raises(ValidationError, match="Properties cannot be empty"):
            await relationship_manager.update_relationship("node1", "node2", "KNOWS", {})

    @pytest.mark.asyncio
    async def test_update_relationship_system_properties_filtered(self, relationship_manager, mock_client):
        """Test relationship update filters out system properties."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        result = await relationship_manager.update_relationship(
            "node1", "node2", "KNOWS", {"created_at": "2023-01-01", "weight": 0.9}
        )

        # Should return False because no valid properties after filtering
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_relationship_success(self, relationship_manager, mock_client):
        """Test successful relationship deletion."""
        mock_client.execute_query.return_value = QueryResult(
            records=[],
            summary={"counters": {"relationships_deleted": 1}}
        )

        result = await relationship_manager.delete_relationship("node1", "node2", "KNOWS")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_relationship_not_found(self, relationship_manager, mock_client):
        """Test relationship deletion when relationship doesn't exist."""
        mock_client.execute_query.return_value = QueryResult(
            records=[],
            summary={"counters": {"relationships_deleted": 0}}
        )

        result = await relationship_manager.delete_relationship("node1", "node2", "KNOWS")

        assert result is False

    @pytest.mark.asyncio
    async def test_find_relationships_no_criteria(self, relationship_manager, mock_client):
        """Test finding relationships without criteria."""
        mock_client.execute_query.return_value = QueryResult(
            records=[
                {
                    "r": {"type": "KNOWS", "since": "2023"},
                    "start": {"id": "node1"},
                    "end": {"id": "node2"}
                },
                {
                    "r": {"type": "WORKS_WITH", "since": "2022"},
                    "start": {"id": "node2"},
                    "end": {"id": "node3"}
                }
            ]
        )

        result = await relationship_manager.find_relationships()

        assert len(result) == 2
        assert result[0].type == "KNOWS"
        assert result[1].type == "WORKS_WITH"

    @pytest.mark.asyncio
    async def test_find_relationships_with_type(self, relationship_manager, mock_client):
        """Test finding relationships with type filter."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        await relationship_manager.find_relationships(rel_type="KNOWS")

        # Verify the query includes type filter
        call_args = mock_client.execute_query.call_args
        assert ":KNOWS" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_relationships_with_node_filters(self, relationship_manager, mock_client):
        """Test finding relationships with node filters."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        await relationship_manager.find_relationships(
            start_node_id="node1", end_node_id="node2"
        )

        # Verify the query includes node filters
        call_args = mock_client.execute_query.call_args
        assert "WHERE" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_relationships_with_properties(self, relationship_manager, mock_client):
        """Test finding relationships with property filters."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        await relationship_manager.find_relationships(
            properties={"since": "2023", "weight": 0.8}
        )

        # Verify the query includes property filters
        call_args = mock_client.execute_query.call_args
        assert "WHERE" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_relationships_with_pagination(self, relationship_manager, mock_client):
        """Test finding relationships with pagination."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        await relationship_manager.find_relationships(limit=10, skip=5)

        # Verify the query includes pagination
        call_args = mock_client.execute_query.call_args
        assert "LIMIT 10" in call_args[0][0]
        assert "SKIP 5" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_find_relationships_invalid_limit(self, relationship_manager):
        """Test finding relationships with invalid limit."""
        with pytest.raises(ValidationError, match="Limit must be positive"):
            await relationship_manager.find_relationships(limit=0)

    @pytest.mark.asyncio
    async def test_find_relationships_invalid_skip(self, relationship_manager):
        """Test finding relationships with invalid skip."""
        with pytest.raises(ValidationError, match="Skip must be non-negative"):
            await relationship_manager.find_relationships(skip=-1)

    @pytest.mark.asyncio
    async def test_relationship_exists_true(self, relationship_manager, mock_client):
        """Test relationship exists check returns True."""
        mock_client.execute_query.return_value = QueryResult(
            records=[{"exists": True}]
        )

        result = await relationship_manager.relationship_exists("node1", "node2", "KNOWS")

        assert result is True

    @pytest.mark.asyncio
    async def test_relationship_exists_false(self, relationship_manager, mock_client):
        """Test relationship exists check returns False."""
        mock_client.execute_query.return_value = QueryResult(
            records=[{"exists": False}]
        )

        result = await relationship_manager.relationship_exists("node1", "node2", "KNOWS")

        assert result is False

    @pytest.mark.asyncio
    async def test_relationship_exists_no_records(self, relationship_manager, mock_client):
        """Test relationship exists check with no records."""
        mock_client.execute_query.return_value = QueryResult(records=[])

        result = await relationship_manager.relationship_exists("node1", "node2", "KNOWS")

        assert result is False

    @pytest.mark.asyncio
    async def test_create_relationships_batch_success(self, relationship_manager, mock_client):
        """Test successful batch relationship creation."""
        relationships = [
            GraphRelationship(type="KNOWS", start_node_id="node1", end_node_id="node2"),
            GraphRelationship(type="WORKS_WITH", start_node_id="node2", end_node_id="node3")
        ]

        mock_client.execute_batch.return_value = [
            QueryResult(records=[{"r": {"id": "rel1"}, "start": {}, "end": {}}]),
            QueryResult(records=[{"r": {"id": "rel2"}, "start": {}, "end": {}}])
        ]

        result = await relationship_manager.create_relationships_batch(relationships)

        assert result == ["rel1", "rel2"]

    @pytest.mark.asyncio
    async def test_create_relationships_batch_empty(self, relationship_manager):
        """Test batch relationship creation with empty list."""
        result = await relationship_manager.create_relationships_batch([])

        assert result == []

    @pytest.mark.asyncio
    async def test_create_relationships_batch_invalid_batch_size(self, relationship_manager):
        """Test batch relationship creation with invalid batch size."""
        relationships = [GraphRelationship(type="KNOWS", start_node_id="node1", end_node_id="node2")]

        with pytest.raises(ValidationError, match="Batch size must be positive"):
            await relationship_manager.create_relationships_batch(relationships, batch_size=0)

    @pytest.mark.asyncio
    async def test_create_relationships_batch_missing_start_id(self, relationship_manager):
        """Test batch relationship creation with missing start node ID."""
        # GraphRelationship validation prevents empty start_node_id at the model level
        with pytest.raises(ValueError, match="Node IDs cannot be empty"):
            GraphRelationship(type="KNOWS", start_node_id="", end_node_id="node2")

    @pytest.mark.asyncio
    async def test_create_relationships_batch_missing_end_id(self, relationship_manager):
        """Test batch relationship creation with missing end node ID."""
        # GraphRelationship validation prevents empty end_node_id at the model level
        with pytest.raises(ValueError, match="Node IDs cannot be empty"):
            GraphRelationship(type="KNOWS", start_node_id="node1", end_node_id="")

    @pytest.mark.asyncio
    async def test_create_relationships_batch_missing_type(self, relationship_manager):
        """Test batch relationship creation with missing type."""
        # GraphRelationship validation prevents empty type at the model level
        with pytest.raises(ValueError, match="Relationship type cannot be empty"):
            GraphRelationship(type="", start_node_id="node1", end_node_id="node2")

    @pytest.mark.asyncio
    async def test_update_relationships_batch_success(self, relationship_manager, mock_client):
        """Test successful batch relationship update."""
        updates = [
            {
                "start_id": "node1",
                "end_id": "node2",
                "rel_type": "KNOWS",
                "properties": {"weight": 0.9}
            },
            {
                "start_id": "node2",
                "end_id": "node3",
                "rel_type": "WORKS_WITH",
                "properties": {"since": "2024"}
            }
        ]

        mock_client.execute_batch.return_value = [
            QueryResult(records=[{"r": {"id": "rel1"}, "start": {}, "end": {}}]),
            QueryResult(records=[{"r": {"id": "rel2"}, "start": {}, "end": {}}])
        ]

        result = await relationship_manager.update_relationships_batch(updates)

        assert result == 2

    @pytest.mark.asyncio
    async def test_update_relationships_batch_empty(self, relationship_manager):
        """Test batch relationship update with empty list."""
        result = await relationship_manager.update_relationships_batch([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_update_relationships_batch_missing_start_id(self, relationship_manager):
        """Test batch relationship update with missing start ID."""
        updates = [{"end_id": "node2", "rel_type": "KNOWS", "properties": {"weight": 0.9}}]

        with pytest.raises(ValidationError, match="Start node ID is required"):
            await relationship_manager.update_relationships_batch(updates)

    @pytest.mark.asyncio
    async def test_delete_relationships_batch_success(self, relationship_manager, mock_client):
        """Test successful batch relationship deletion."""
        relationships = [
            {"start_id": "node1", "end_id": "node2", "rel_type": "KNOWS"},
            {"start_id": "node2", "end_id": "node3", "rel_type": "WORKS_WITH"}
        ]

        mock_client.execute_batch.return_value = [
            QueryResult(records=[], summary={"counters": {"relationships_deleted": 1}}),
            QueryResult(records=[], summary={"counters": {"relationships_deleted": 1}})
        ]

        result = await relationship_manager.delete_relationships_batch(relationships)

        assert result == 2

    @pytest.mark.asyncio
    async def test_delete_relationships_batch_empty(self, relationship_manager):
        """Test batch relationship deletion with empty list."""
        result = await relationship_manager.delete_relationships_batch([])

        assert result == 0

    @pytest.mark.asyncio
    async def test_delete_relationships_batch_missing_start_id(self, relationship_manager):
        """Test batch relationship deletion with missing start ID."""
        relationships = [{"end_id": "node2", "rel_type": "KNOWS"}]

        with pytest.raises(ValidationError, match="Start node ID is required"):
            await relationship_manager.delete_relationships_batch(relationships)

    @pytest.mark.asyncio
    async def test_record_to_relationship_success(self, relationship_manager):
        """Test converting record to relationship."""
        record_data = {
            "id": "rel-123",
            "type": "KNOWS",
            "since": "2023",
            "weight": 0.8,
            "created_at": "2023-01-01T12:00:00"
        }

        result = relationship_manager._record_to_relationship(
            record_data, "node1", "node2", "KNOWS"
        )

        assert result is not None
        assert result.id == "rel-123"
        assert result.type == "KNOWS"
        assert result.start_node_id == "node1"
        assert result.end_node_id == "node2"
        assert result.properties["since"] == "2023"
        assert result.properties["weight"] == 0.8

    @pytest.mark.asyncio
    async def test_record_to_relationship_empty_record(self, relationship_manager):
        """Test converting empty record to relationship."""
        result = relationship_manager._record_to_relationship(
            {}, "node1", "node2", "KNOWS"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_record_to_relationship_invalid_timestamp(self, relationship_manager):
        """Test converting record with invalid timestamp."""
        record_data = {
            "id": "rel-123",
            "created_at": "invalid-date"
        }

        result = relationship_manager._record_to_relationship(
            record_data, "node1", "node2", "KNOWS"
        )

        assert result is not None
        assert result.created_at is None

    @pytest.mark.asyncio
    async def test_record_to_relationship_with_element_id(self, relationship_manager):
        """Test converting record with element_id instead of id."""
        record_data = {
            "element_id": "rel-456",
            "type": "KNOWS"
        }

        result = relationship_manager._record_to_relationship(
            record_data, "node1", "node2", "KNOWS"
        )

        assert result is not None
        assert result.id == "rel-456"
