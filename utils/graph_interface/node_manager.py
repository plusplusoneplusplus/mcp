"""Node manager for Neo4j graph operations."""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from .neo4j_client import Neo4jClient
from .models import GraphNode, QueryResult
from .query_builder import QueryBuilder
from .exceptions import (
    NodeNotFoundError,
    ValidationError,
    GraphOperationError,
    Neo4jQueryError
)

logger = logging.getLogger(__name__)


class NodeManager:
    """High-level manager for Neo4j node operations."""

    def __init__(self, client: Neo4jClient):
        """Initialize NodeManager with Neo4j client.

        Args:
            client: Neo4jClient instance
        """
        self.client = client

    async def create_node(self, node: GraphNode) -> str:
        """Create a new node in the graph.

        Args:
            node: GraphNode instance to create

        Returns:
            Node ID of the created node

        Raises:
            ValidationError: If node data is invalid
            GraphOperationError: If creation fails
        """
        try:
            # Validate node
            if not node.id:
                raise ValidationError("Node ID is required")

            # Check if node already exists
            if await self.node_exists(node.id, node.labels):
                raise GraphOperationError(f"Node with ID '{node.id}' already exists")

            # Prepare properties with timestamps
            properties = dict(node.properties)
            properties.update({
                'id': node.id,
                'created_at': node.created_at.isoformat() if node.created_at else datetime.utcnow().isoformat(),
                'updated_at': node.updated_at.isoformat() if node.updated_at else datetime.utcnow().isoformat()
            })

            # Build and execute query
            query, params = QueryBuilder.create_node_query(node.labels, properties)
            result = await self.client.execute_query(query, params)

            if not result.records:
                raise GraphOperationError("Failed to create node - no records returned")

            logger.info(f"Created node with ID: {node.id}")
            return node.id

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to create node: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating node: {e}")
            raise GraphOperationError(f"Unexpected error creating node: {e}")

    async def get_node(self, node_id: str, labels: Optional[List[str]] = None) -> Optional[GraphNode]:
        """Get a node by ID.

        Args:
            node_id: Node ID to retrieve
            labels: Optional labels to match

        Returns:
            GraphNode instance or None if not found

        Raises:
            ValidationError: If node_id is invalid
            GraphOperationError: If query fails
        """
        try:
            if not node_id or not node_id.strip():
                raise ValidationError("Node ID cannot be empty")

            query, params = QueryBuilder.match_node_by_id_query(node_id.strip(), labels)
            result = await self.client.execute_query(query, params)

            if not result.records:
                return None

            # Convert Neo4j record to GraphNode
            record = result.records[0]
            node_data = record.get('n', {})

            return self._record_to_node(node_data)

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to get node: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting node: {e}")
            raise GraphOperationError(f"Unexpected error getting node: {e}")

    async def update_node(self, node_id: str, properties: Dict[str, Any], labels: Optional[List[str]] = None) -> bool:
        """Update node properties.

        Args:
            node_id: Node ID to update
            properties: Properties to update
            labels: Optional labels to match

        Returns:
            True if node was updated, False if not found

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If update fails
        """
        try:
            if not node_id or not node_id.strip():
                raise ValidationError("Node ID cannot be empty")

            if not properties:
                raise ValidationError("Properties cannot be empty")

            # Remove system properties that shouldn't be updated directly
            update_props = {k: v for k, v in properties.items()
                          if k not in ['id', 'created_at']}

            if not update_props:
                logger.warning("No valid properties to update")
                return False

            query, params = QueryBuilder.update_node_query(node_id.strip(), update_props, labels)
            result = await self.client.execute_query(query, params)

            if not result.records:
                return False

            logger.info(f"Updated node with ID: {node_id}")
            return True

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to update node: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating node: {e}")
            raise GraphOperationError(f"Unexpected error updating node: {e}")

    async def delete_node(self, node_id: str, force: bool = False, labels: Optional[List[str]] = None) -> bool:
        """Delete a node.

        Args:
            node_id: Node ID to delete
            force: If True, delete relationships as well (DETACH DELETE)
            labels: Optional labels to match

        Returns:
            True if node was deleted, False if not found

        Raises:
            ValidationError: If node_id is invalid
            GraphOperationError: If deletion fails
        """
        try:
            if not node_id or not node_id.strip():
                raise ValidationError("Node ID cannot be empty")

            query, params = QueryBuilder.delete_node_query(node_id.strip(), force, labels)
            result = await self.client.execute_query(query, params)

            # Check if any nodes were deleted by examining the summary
            nodes_deleted = result.summary.get('counters', {}).get('nodes_deleted', 0)

            if nodes_deleted > 0:
                logger.info(f"Deleted node with ID: {node_id}")
                return True

            return False

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to delete node: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting node: {e}")
            raise GraphOperationError(f"Unexpected error deleting node: {e}")

    async def find_nodes(
        self,
        labels: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None
    ) -> List[GraphNode]:
        """Find nodes by criteria.

        Args:
            labels: Optional labels to match
            properties: Optional properties to match
            limit: Optional result limit
            skip: Optional number of results to skip

        Returns:
            List of matching GraphNode instances

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if limit is not None and limit <= 0:
                raise ValidationError("Limit must be positive")

            if skip is not None and skip < 0:
                raise ValidationError("Skip must be non-negative")

            query, params = QueryBuilder.find_nodes_query(labels, properties, limit, skip)
            result = await self.client.execute_query(query, params)

            nodes = []
            for record in result.records:
                node_data = record.get('n', {})
                node = self._record_to_node(node_data)
                if node:
                    nodes.append(node)

            logger.info(f"Found {len(nodes)} nodes matching criteria")
            return nodes

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to find nodes: {e}")
        except Exception as e:
            logger.error(f"Unexpected error finding nodes: {e}")
            raise GraphOperationError(f"Unexpected error finding nodes: {e}")

    async def get_node_relationships(
        self,
        node_id: str,
        direction: str = "BOTH",
        rel_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get relationships for a node.

        Args:
            node_id: Node ID
            direction: "INCOMING", "OUTGOING", or "BOTH"
            rel_type: Optional relationship type filter
            limit: Optional result limit

        Returns:
            List of relationship data with connected nodes

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if not node_id or not node_id.strip():
                raise ValidationError("Node ID cannot be empty")

            if direction.upper() not in ["INCOMING", "OUTGOING", "BOTH"]:
                raise ValidationError("Direction must be 'INCOMING', 'OUTGOING', or 'BOTH'")

            if limit is not None and limit <= 0:
                raise ValidationError("Limit must be positive")

            query, params = QueryBuilder.get_node_relationships_query(
                node_id.strip(), direction, rel_type, limit
            )
            result = await self.client.execute_query(query, params)

            relationships = []
            for record in result.records:
                rel_data = {
                    'relationship': record.get('r', {}),
                    'node': record.get('n', {}),
                    'other_node': record.get('other', {})
                }
                relationships.append(rel_data)

            logger.info(f"Found {len(relationships)} relationships for node {node_id}")
            return relationships

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to get node relationships: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting node relationships: {e}")
            raise GraphOperationError(f"Unexpected error getting node relationships: {e}")

    async def node_exists(self, node_id: str, labels: Optional[List[str]] = None) -> bool:
        """Check if a node exists.

        Args:
            node_id: Node ID to check
            labels: Optional labels to match

        Returns:
            True if node exists, False otherwise

        Raises:
            ValidationError: If node_id is invalid
            GraphOperationError: If query fails
        """
        try:
            if not node_id or not node_id.strip():
                raise ValidationError("Node ID cannot be empty")

            query, params = QueryBuilder.node_exists_query(node_id.strip(), labels)
            result = await self.client.execute_query(query, params)

            if result.records:
                return result.records[0].get('exists', False)

            return False

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to check node existence: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking node existence: {e}")
            raise GraphOperationError(f"Unexpected error checking node existence: {e}")

    async def create_nodes_batch(self, nodes: List[GraphNode], batch_size: int = 100) -> List[str]:
        """Create multiple nodes in batches.

        Args:
            nodes: List of GraphNode instances to create
            batch_size: Number of nodes to create per batch

        Returns:
            List of created node IDs

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If batch creation fails
        """
        try:
            if not nodes:
                return []

            if batch_size <= 0:
                raise ValidationError("Batch size must be positive")

            created_ids = []

            # Process nodes in batches
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i + batch_size]
                batch_queries = []

                for node in batch:
                    if not node.id:
                        raise ValidationError(f"Node ID is required for batch creation")

                    # Prepare properties
                    properties = dict(node.properties)
                    properties.update({
                        'id': node.id,
                        'created_at': node.created_at.isoformat() if node.created_at else datetime.utcnow().isoformat(),
                        'updated_at': node.updated_at.isoformat() if node.updated_at else datetime.utcnow().isoformat()
                    })

                    query, params = QueryBuilder.create_node_query(node.labels, properties)
                    batch_queries.append({
                        'query': query,
                        'parameters': params
                    })

                # Execute batch
                results = await self.client.execute_batch(batch_queries)

                # Collect created IDs
                for j, result in enumerate(results):
                    if result.records:
                        created_ids.append(batch[j].id)

            logger.info(f"Created {len(created_ids)} nodes in batch")
            return created_ids

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to create nodes batch: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating nodes batch: {e}")
            raise GraphOperationError(f"Unexpected error creating nodes batch: {e}")

    async def update_nodes_batch(
        self,
        updates: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """Update multiple nodes in batches.

        Args:
            updates: List of update dictionaries with 'node_id', 'properties', and optional 'labels'
            batch_size: Number of updates per batch

        Returns:
            Number of nodes updated

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
                    node_id = update.get('node_id')
                    properties = update.get('properties', {})
                    labels = update.get('labels')

                    if not node_id:
                        raise ValidationError("Node ID is required for batch update")

                    if not properties:
                        continue  # Skip empty updates

                    # Remove system properties
                    update_props = {k: v for k, v in properties.items()
                                  if k not in ['id', 'created_at']}

                    if update_props:
                        query, params = QueryBuilder.update_node_query(node_id, update_props, labels)
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

            logger.info(f"Updated {updated_count} nodes in batch")
            return updated_count

        except ValidationError:
            # Re-raise ValidationError as-is
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to update nodes batch: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating nodes batch: {e}")
            raise GraphOperationError(f"Unexpected error updating nodes batch: {e}")

    def _record_to_node(self, record_data: Dict[str, Any]) -> Optional[GraphNode]:
        """Convert Neo4j record data to GraphNode.

        Args:
            record_data: Neo4j record data

        Returns:
            GraphNode instance or None if conversion fails
        """
        try:
            if not record_data:
                return None

            # Extract node properties
            node_id = record_data.get('id')
            if not node_id:
                return None

            # Extract labels (Neo4j returns them as a list)
            labels = record_data.get('labels', [])
            if isinstance(labels, str):
                labels = [labels]

            # Extract properties (excluding system properties)
            properties = {}
            created_at = None
            updated_at = None

            for key, value in record_data.items():
                if key in ['id', 'labels']:
                    continue
                elif key == 'created_at':
                    try:
                        created_at = datetime.fromisoformat(value) if value else None
                    except (ValueError, TypeError):
                        created_at = None
                elif key == 'updated_at':
                    try:
                        updated_at = datetime.fromisoformat(value) if value else None
                    except (ValueError, TypeError):
                        updated_at = None
                else:
                    properties[key] = value

            return GraphNode(
                id=node_id,
                labels=labels,
                properties=properties,
                created_at=created_at,
                updated_at=updated_at
            )

        except Exception as e:
            logger.error(f"Failed to convert record to node: {e}")
            return None
