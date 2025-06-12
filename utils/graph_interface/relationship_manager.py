"""Relationship manager for Neo4j graph operations."""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from .neo4j_client import Neo4jClient
from .models import GraphRelationship, GraphNode, QueryResult
from .query_builder import QueryBuilder
from .exceptions import (
    RelationshipNotFoundError,
    ValidationError,
    GraphOperationError,
    Neo4jQueryError
)

logger = logging.getLogger(__name__)


class RelationshipManager:
    """High-level manager for Neo4j relationship operations."""

    def __init__(self, client: Neo4jClient):
        """Initialize RelationshipManager with Neo4j client.

        Args:
            client: Neo4jClient instance
        """
        self.client = client

    async def create_relationship(self, relationship: GraphRelationship) -> Optional[str]:
        """Create a new relationship in the graph.

        Args:
            relationship: GraphRelationship instance to create

        Returns:
            Relationship ID if available, None otherwise

        Raises:
            ValidationError: If relationship data is invalid
            GraphOperationError: If creation fails
        """
        try:
            # Validate relationship
            if not relationship.start_node_id:
                raise ValidationError("Start node ID is required")

            if not relationship.end_node_id:
                raise ValidationError("End node ID is required")

            if not relationship.type:
                raise ValidationError("Relationship type is required")

            # Check if relationship already exists
            if await self.relationship_exists(
                relationship.start_node_id,
                relationship.end_node_id,
                relationship.type
            ):
                raise GraphOperationError(
                    f"Relationship '{relationship.type}' between nodes "
                    f"'{relationship.start_node_id}' and '{relationship.end_node_id}' already exists"
                )

            # Prepare properties with timestamp
            properties = dict(relationship.properties)
            properties['created_at'] = relationship.created_at.isoformat() if relationship.created_at else datetime.utcnow().isoformat()

            # Build and execute query
            query, params = QueryBuilder.create_relationship_query(
                relationship.start_node_id,
                relationship.end_node_id,
                relationship.type,
                properties
            )
            result = await self.client.execute_query(query, params)

            if not result.records:
                raise GraphOperationError("Failed to create relationship - no records returned")

            # Extract relationship ID if available
            record = result.records[0]
            rel_data = record.get('r', {})
            rel_id = rel_data.get('id') or rel_data.get('element_id')

            logger.info(f"Created relationship '{relationship.type}' between nodes "
                       f"'{relationship.start_node_id}' and '{relationship.end_node_id}'")
            return rel_id

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to create relationship: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating relationship: {e}")
            raise GraphOperationError(f"Unexpected error creating relationship: {e}")

    async def get_relationship(
        self,
        start_id: str,
        end_id: str,
        rel_type: str
    ) -> Optional[GraphRelationship]:
        """Get a relationship by start node, end node, and type.

        Args:
            start_id: Start node ID
            end_id: End node ID
            rel_type: Relationship type

        Returns:
            GraphRelationship instance or None if not found

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if not start_id or not start_id.strip():
                raise ValidationError("Start node ID cannot be empty")

            if not end_id or not end_id.strip():
                raise ValidationError("End node ID cannot be empty")

            if not rel_type or not rel_type.strip():
                raise ValidationError("Relationship type cannot be empty")

            query, params = QueryBuilder.match_relationship_query(
                start_id.strip(), end_id.strip(), rel_type.strip()
            )
            result = await self.client.execute_query(query, params)

            if not result.records:
                return None

            # Convert Neo4j record to GraphRelationship
            record = result.records[0]
            rel_data = record.get('r', {})

            return self._record_to_relationship(rel_data, start_id, end_id, rel_type)

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to get relationship: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting relationship: {e}")
            raise GraphOperationError(f"Unexpected error getting relationship: {e}")

    async def update_relationship(
        self,
        start_id: str,
        end_id: str,
        rel_type: str,
        properties: Dict[str, Any]
    ) -> bool:
        """Update relationship properties.

        Args:
            start_id: Start node ID
            end_id: End node ID
            rel_type: Relationship type
            properties: Properties to update

        Returns:
            True if relationship was updated, False if not found

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If update fails
        """
        try:
            if not start_id or not start_id.strip():
                raise ValidationError("Start node ID cannot be empty")

            if not end_id or not end_id.strip():
                raise ValidationError("End node ID cannot be empty")

            if not rel_type or not rel_type.strip():
                raise ValidationError("Relationship type cannot be empty")

            if not properties:
                raise ValidationError("Properties cannot be empty")

            # Remove system properties that shouldn't be updated directly
            update_props = {k: v for k, v in properties.items()
                          if k not in ['created_at']}

            if not update_props:
                logger.warning("No valid properties to update")
                return False

            query, params = QueryBuilder.update_relationship_query(
                start_id.strip(), end_id.strip(), rel_type.strip(), update_props
            )
            result = await self.client.execute_query(query, params)

            if not result.records:
                return False

            logger.info(f"Updated relationship '{rel_type}' between nodes '{start_id}' and '{end_id}'")
            return True

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to update relationship: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating relationship: {e}")
            raise GraphOperationError(f"Unexpected error updating relationship: {e}")

    async def delete_relationship(
        self,
        start_id: str,
        end_id: str,
        rel_type: str
    ) -> bool:
        """Delete a relationship.

        Args:
            start_id: Start node ID
            end_id: End node ID
            rel_type: Relationship type

        Returns:
            True if relationship was deleted, False if not found

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If deletion fails
        """
        try:
            if not start_id or not start_id.strip():
                raise ValidationError("Start node ID cannot be empty")

            if not end_id or not end_id.strip():
                raise ValidationError("End node ID cannot be empty")

            if not rel_type or not rel_type.strip():
                raise ValidationError("Relationship type cannot be empty")

            query, params = QueryBuilder.delete_relationship_query(
                start_id.strip(), end_id.strip(), rel_type.strip()
            )
            result = await self.client.execute_query(query, params)

            # Check if any relationships were deleted by examining the summary
            rels_deleted = result.summary.get('counters', {}).get('relationships_deleted', 0)

            if rels_deleted > 0:
                logger.info(f"Deleted relationship '{rel_type}' between nodes '{start_id}' and '{end_id}'")
                return True

            return False

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to delete relationship: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting relationship: {e}")
            raise GraphOperationError(f"Unexpected error deleting relationship: {e}")

    async def find_relationships(
        self,
        rel_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        start_node_id: Optional[str] = None,
        end_node_id: Optional[str] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None
    ) -> List[GraphRelationship]:
        """Find relationships by criteria.

        Args:
            rel_type: Optional relationship type to match
            properties: Optional properties to match
            start_node_id: Optional start node ID to match
            end_node_id: Optional end node ID to match
            limit: Optional result limit
            skip: Optional number of results to skip

        Returns:
            List of matching GraphRelationship instances

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if limit is not None and limit <= 0:
                raise ValidationError("Limit must be positive")

            if skip is not None and skip < 0:
                raise ValidationError("Skip must be non-negative")

            query, params = QueryBuilder.find_relationships_query(
                rel_type, properties, start_node_id, end_node_id, limit, skip
            )
            result = await self.client.execute_query(query, params)

            relationships = []
            for record in result.records:
                rel_data = record.get('r', {})
                start_data = record.get('start', {})
                end_data = record.get('end', {})

                # Extract node IDs
                start_id = start_data.get('id', '')
                end_id = end_data.get('id', '')

                # Extract relationship type from data or use the filter
                relationship_type = rel_data.get('type', rel_type or '')

                relationship = self._record_to_relationship(rel_data, start_id, end_id, relationship_type)
                if relationship:
                    relationships.append(relationship)

            logger.info(f"Found {len(relationships)} relationships matching criteria")
            return relationships

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to find relationships: {e}")
        except Exception as e:
            logger.error(f"Unexpected error finding relationships: {e}")
            raise GraphOperationError(f"Unexpected error finding relationships: {e}")

    async def relationship_exists(
        self,
        start_id: str,
        end_id: str,
        rel_type: str
    ) -> bool:
        """Check if a relationship exists.

        Args:
            start_id: Start node ID
            end_id: End node ID
            rel_type: Relationship type

        Returns:
            True if relationship exists, False otherwise

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if not start_id or not start_id.strip():
                raise ValidationError("Start node ID cannot be empty")

            if not end_id or not end_id.strip():
                raise ValidationError("End node ID cannot be empty")

            if not rel_type or not rel_type.strip():
                raise ValidationError("Relationship type cannot be empty")

            query, params = QueryBuilder.relationship_exists_query(
                start_id.strip(), end_id.strip(), rel_type.strip()
            )
            result = await self.client.execute_query(query, params)

            if result.records:
                return result.records[0].get('exists', False)

            return False

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to check relationship existence: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking relationship existence: {e}")
            raise GraphOperationError(f"Unexpected error checking relationship existence: {e}")

    async def create_relationships_batch(
        self,
        relationships: List[GraphRelationship],
        batch_size: int = 100
    ) -> List[Optional[str]]:
        """Create multiple relationships in batches.

        Args:
            relationships: List of GraphRelationship instances to create
            batch_size: Number of relationships to create per batch

        Returns:
            List of created relationship IDs (None if ID not available)

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If batch creation fails
        """
        try:
            if not relationships:
                return []

            if batch_size <= 0:
                raise ValidationError("Batch size must be positive")

            created_ids = []

            # Process relationships in batches
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i:i + batch_size]
                batch_queries = []

                for relationship in batch:
                    if not relationship.start_node_id:
                        raise ValidationError("Start node ID is required for batch creation")

                    if not relationship.end_node_id:
                        raise ValidationError("End node ID is required for batch creation")

                    if not relationship.type:
                        raise ValidationError("Relationship type is required for batch creation")

                    # Prepare properties
                    properties = dict(relationship.properties)
                    properties['created_at'] = relationship.created_at.isoformat() if relationship.created_at else datetime.utcnow().isoformat()

                    query, params = QueryBuilder.create_relationship_query(
                        relationship.start_node_id,
                        relationship.end_node_id,
                        relationship.type,
                        properties
                    )
                    batch_queries.append({
                        'query': query,
                        'parameters': params
                    })

                # Execute batch
                results = await self.client.execute_batch(batch_queries)

                # Collect created IDs
                for result in results:
                    if result.records:
                        record = result.records[0]
                        rel_data = record.get('r', {})
                        rel_id = rel_data.get('id') or rel_data.get('element_id')
                        created_ids.append(rel_id)
                    else:
                        created_ids.append(None)

            logger.info(f"Created {len([id for id in created_ids if id])} relationships in batch")
            return created_ids

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to create relationships batch: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating relationships batch: {e}")
            raise GraphOperationError(f"Unexpected error creating relationships batch: {e}")

    async def update_relationships_batch(
        self,
        updates: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """Update multiple relationships in batches.

        Args:
            updates: List of update dictionaries with 'start_id', 'end_id', 'rel_type', and 'properties'
            batch_size: Number of updates per batch

        Returns:
            Number of relationships updated

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If batch update fails
        """
        try:
            if not updates:
                return 0

            if batch_size <= 0:
                raise ValidationError("Batch size must be positive")

            updated_count = 0

            # Process updates in batches
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                batch_queries = []

                for update in batch:
                    start_id = update.get('start_id')
                    end_id = update.get('end_id')
                    rel_type = update.get('rel_type')
                    properties = update.get('properties', {})

                    if not start_id:
                        raise ValidationError("Start node ID is required for batch update")

                    if not end_id:
                        raise ValidationError("End node ID is required for batch update")

                    if not rel_type:
                        raise ValidationError("Relationship type is required for batch update")

                    if not properties:
                        continue  # Skip empty updates

                    # Remove system properties
                    update_props = {k: v for k, v in properties.items()
                                  if k not in ['created_at']}

                    if update_props:
                        query, params = QueryBuilder.update_relationship_query(
                            start_id, end_id, rel_type, update_props
                        )
                        batch_queries.append({
                            'query': query,
                            'parameters': params
                        })

                # Execute batch
                if batch_queries:
                    results = await self.client.execute_batch(batch_queries)

                    # Count successful updates
                    for result in results:
                        if result.records:
                            updated_count += 1

            logger.info(f"Updated {updated_count} relationships in batch")
            return updated_count

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to update relationships batch: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating relationships batch: {e}")
            raise GraphOperationError(f"Unexpected error updating relationships batch: {e}")

    async def delete_relationships_batch(
        self,
        relationships: List[Dict[str, str]],
        batch_size: int = 100
    ) -> int:
        """Delete multiple relationships in batches.

        Args:
            relationships: List of relationship dictionaries with 'start_id', 'end_id', and 'rel_type'
            batch_size: Number of deletions per batch

        Returns:
            Number of relationships deleted

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If batch deletion fails
        """
        try:
            if not relationships:
                return 0

            if batch_size <= 0:
                raise ValidationError("Batch size must be positive")

            deleted_count = 0

            # Process deletions in batches
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i:i + batch_size]
                batch_queries = []

                for rel_info in batch:
                    start_id = rel_info.get('start_id')
                    end_id = rel_info.get('end_id')
                    rel_type = rel_info.get('rel_type')

                    if not start_id:
                        raise ValidationError("Start node ID is required for batch deletion")

                    if not end_id:
                        raise ValidationError("End node ID is required for batch deletion")

                    if not rel_type:
                        raise ValidationError("Relationship type is required for batch deletion")

                    query, params = QueryBuilder.delete_relationship_query(
                        start_id, end_id, rel_type
                    )
                    batch_queries.append({
                        'query': query,
                        'parameters': params
                    })

                # Execute batch
                if batch_queries:
                    results = await self.client.execute_batch(batch_queries)

                    # Count successful deletions
                    for result in results:
                        rels_deleted = result.summary.get('counters', {}).get('relationships_deleted', 0)
                        deleted_count += rels_deleted

            logger.info(f"Deleted {deleted_count} relationships in batch")
            return deleted_count

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to delete relationships batch: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting relationships batch: {e}")
            raise GraphOperationError(f"Unexpected error deleting relationships batch: {e}")

    def _record_to_relationship(
        self,
        record_data: Dict[str, Any],
        start_id: str,
        end_id: str,
        rel_type: str
    ) -> Optional[GraphRelationship]:
        """Convert Neo4j record data to GraphRelationship.

        Args:
            record_data: Neo4j record data
            start_id: Start node ID
            end_id: End node ID
            rel_type: Relationship type

        Returns:
            GraphRelationship instance or None if conversion fails
        """
        try:
            if not record_data:
                return None

            # Extract relationship ID if available
            rel_id = record_data.get('id') or record_data.get('element_id')

            # Extract properties (excluding system properties)
            properties = {}
            created_at = None

            for key, value in record_data.items():
                if key in ['id', 'element_id', 'type']:
                    continue
                elif key == 'created_at':
                    try:
                        created_at = datetime.fromisoformat(value) if value else None
                    except (ValueError, TypeError):
                        created_at = None
                else:
                    properties[key] = value

            return GraphRelationship(
                id=rel_id,
                type=rel_type,
                start_node_id=start_id,
                end_node_id=end_id,
                properties=properties,
                created_at=created_at
            )

        except Exception as e:
            logger.error(f"Failed to convert record to relationship: {e}")
            return None
