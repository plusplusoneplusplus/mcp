"""High-level graph manager with advanced operations."""

import logging
from collections import deque
from typing import Any, Dict, List, Optional, Set

from .exceptions import GraphOperationError, Neo4jQueryError, ValidationError
from .models import GraphNode, GraphPath, GraphStats
from .neo4j_client import Neo4jClient
from .node_manager import NodeManager
from .relationship_manager import RelationshipManager

logger = logging.getLogger(__name__)


class GraphManager:
    """High-level manager for advanced Neo4j graph operations.

    This class orchestrates the node and relationship managers while providing
    advanced graph algorithms and analytics like path finding, cycle detection,
    subgraph extraction, and graph traversal.
    """

    def __init__(self, client: Neo4jClient):
        """Initialize GraphManager with Neo4j client.

        Args:
            client: Neo4jClient instance
        """
        self.client = client
        self.node_manager = NodeManager(client)
        self.relationship_manager = RelationshipManager(client)

    @classmethod
    async def create(
        self, uri: str, username: str, password: str, database: str = "neo4j"
    ) -> "GraphManager":
        """Factory method to create GraphManager with connection.

        Args:
            uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
            database: Database name (default: "neo4j")

        Returns:
            GraphManager instance

        Raises:
            GraphOperationError: If connection fails
        """
        try:
            client = Neo4jClient(uri, username, password, database)
            await client.connect()
            return GraphManager(client)
        except Exception as e:
            raise GraphOperationError(f"Failed to create GraphManager: {e}")

    async def close(self) -> None:
        """Close the graph manager and underlying connections."""
        if self.client:
            await self.client.close()

    # Graph Analytics Methods

    async def get_graph_stats(self) -> GraphStats:
        """Get comprehensive graph statistics.

        Returns:
            GraphStats with node count, relationship count, labels, types, etc.

        Raises:
            GraphOperationError: If query fails
        """
        try:
            # Get node count and labels
            node_query = """
            MATCH (n)
            RETURN count(n) as node_count, labels(n) as node_labels
            """
            node_result = await self.client.execute_query(node_query)

            # Get relationship count and types
            rel_query = """
            MATCH ()-[r]->()
            RETURN count(r) as rel_count, type(r) as rel_type
            """
            rel_result = await self.client.execute_query(rel_query)

            # Process node data
            node_count = 0
            labels_count = defaultdict(int)

            for record in node_result.records:
                node_count += record.get("node_count", 0)
                node_labels = record.get("node_labels", [])
                for label in node_labels:
                    labels_count[label] += 1

            # Process relationship data
            rel_count = 0
            rel_types_count = defaultdict(int)

            for record in rel_result.records:
                rel_count += record.get("rel_count", 0)
                rel_type = record.get("rel_type")
                if rel_type:
                    rel_types_count[rel_type] += 1

            # Create stats object
            stats = GraphStats(
                node_count=node_count,
                relationship_count=rel_count,
                labels=dict(labels_count),
                relationship_types=dict(rel_types_count),
            )

            # Calculate density
            stats.calculate_density()

            return stats

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to get graph stats: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting graph stats: {e}")
            raise GraphOperationError(f"Unexpected error getting graph stats: {e}")

    async def calculate_graph_density(self) -> float:
        """Calculate graph density (ratio of actual to possible relationships).

        Returns:
            Graph density value between 0 and 1

        Raises:
            GraphOperationError: If calculation fails
        """
        stats = await self.get_graph_stats()
        return stats.calculate_density()

    async def get_degree_distribution(self) -> Dict[int, int]:
        """Get node degree distribution.

        Returns:
            Dictionary mapping degree to count of nodes with that degree

        Raises:
            GraphOperationError: If query fails
        """
        try:
            query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) as degree
            RETURN degree, count(n) as node_count
            ORDER BY degree
            """
            result = await self.client.execute_query(query)

            distribution = {}
            for record in result.records:
                degree = record.get("degree", 0)
                count = record.get("node_count", 0)
                distribution[degree] = count

            return distribution

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to get degree distribution: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting degree distribution: {e}")
            raise GraphOperationError(
                f"Unexpected error getting degree distribution: {e}"
            )

    # Path Operations

    async def find_paths(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 5,
        rel_types: Optional[List[str]] = None,
    ) -> List[GraphPath]:
        """Find all paths between two nodes.

        Args:
            start_id: Start node ID
            end_id: End node ID
            max_depth: Maximum path depth (default: 5)
            rel_types: Optional relationship types to follow

        Returns:
            List of GraphPath objects

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if not start_id or not start_id.strip():
                raise ValidationError("Start node ID cannot be empty")

            if not end_id or not end_id.strip():
                raise ValidationError("End node ID cannot be empty")

            if max_depth < 1:
                raise ValidationError("Max depth must be at least 1")

            # Build relationship type filter
            rel_filter = ""
            if rel_types:
                rel_filter = f":{':'.join(rel_types)}"

            query = f"""
            MATCH path = (start {{id: $start_id}})-[{rel_filter}*1..{max_depth}]-(end {{id: $end_id}})
            RETURN path, length(path) as path_length
            ORDER BY path_length
            """

            params = {"start_id": start_id.strip(), "end_id": end_id.strip()}

            result = await self.client.execute_query(query, params)

            paths = []
            for record in result.records:
                path_data = record.get("path")
                if path_data:
                    graph_path = await self._neo4j_path_to_graph_path(path_data)
                    paths.append(graph_path)

            return paths

        except ValidationError:
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to find paths: {e}")
        except Exception as e:
            logger.error(f"Unexpected error finding paths: {e}")
            raise GraphOperationError(f"Unexpected error finding paths: {e}")

    async def calculate_shortest_path(
        self,
        start_id: str,
        end_id: str,
        rel_types: Optional[List[str]] = None,
        weight_property: Optional[str] = None,
    ) -> Optional[GraphPath]:
        """Calculate shortest path between two nodes.

        Args:
            start_id: Start node ID
            end_id: End node ID
            rel_types: Optional relationship types to follow
            weight_property: Optional property name for weighted paths

        Returns:
            GraphPath object or None if no path exists

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if not start_id or not start_id.strip():
                raise ValidationError("Start node ID cannot be empty")

            if not end_id or not end_id.strip():
                raise ValidationError("End node ID cannot be empty")

            # Build relationship type filter
            rel_filter = ""
            if rel_types:
                rel_filter = f":{':'.join(rel_types)}"

            if weight_property:
                # Use weighted shortest path
                query = f"""
                MATCH (start {{id: $start_id}}), (end {{id: $end_id}})
                CALL apoc.algo.dijkstra(start, end, '{rel_filter}', '{weight_property}')
                YIELD path, weight
                RETURN path, weight
                """
            else:
                # Use unweighted shortest path
                query = f"""
                MATCH path = shortestPath((start {{id: $start_id}})-[{rel_filter}*]-(end {{id: $end_id}}))
                RETURN path, length(path) as path_length
                """

            params = {"start_id": start_id.strip(), "end_id": end_id.strip()}

            result = await self.client.execute_query(query, params)

            if not result.records:
                return None

            record = result.records[0]
            path_data = record.get("path")

            if path_data:
                graph_path = await self._neo4j_path_to_graph_path(path_data)
                if weight_property:
                    graph_path.total_weight = record.get("weight")
                return graph_path

            return None

        except ValidationError:
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to calculate shortest path: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calculating shortest path: {e}")
            raise GraphOperationError(
                f"Unexpected error calculating shortest path: {e}"
            )

    # Cycle Detection

    async def detect_cycles(self, max_depth: int = 10) -> List[List[str]]:
        """Detect all cycles in the graph.

        Args:
            max_depth: Maximum cycle depth to search (default: 10)

        Returns:
            List of cycles, each cycle is a list of node IDs

        Raises:
            ValidationError: If max_depth is invalid
            GraphOperationError: If query fails
        """
        try:
            if max_depth < 2:
                raise ValidationError("Max depth must be at least 2 for cycles")

            query = f"""
            MATCH path = (n)-[*2..{max_depth}]-(n)
            WHERE ALL(rel in relationships(path) WHERE startNode(rel) <> endNode(rel))
            WITH path, nodes(path) as cycle_nodes
            RETURN [node in cycle_nodes | node.id] as cycle
            """

            result = await self.client.execute_query(query)

            cycles = []
            seen_cycles = set()

            for record in result.records:
                cycle = record.get("cycle", [])
                if cycle:
                    # Normalize cycle to start with smallest ID to avoid duplicates
                    min_idx = cycle.index(min(cycle))
                    normalized_cycle = cycle[min_idx:] + cycle[:min_idx]
                    cycle_key = tuple(normalized_cycle)

                    if cycle_key not in seen_cycles:
                        seen_cycles.add(cycle_key)
                        cycles.append(normalized_cycle)

            return cycles

        except ValidationError:
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to detect cycles: {e}")
        except Exception as e:
            logger.error(f"Unexpected error detecting cycles: {e}")
            raise GraphOperationError(f"Unexpected error detecting cycles: {e}")

    async def get_connected_components(self) -> List[List[str]]:
        """Find strongly connected components in the graph.

        Returns:
            List of components, each component is a list of node IDs

        Raises:
            GraphOperationError: If query fails
        """
        try:
            query = """
            CALL gds.wcc.stream('*')
            YIELD nodeId, componentId
            RETURN componentId, collect(gds.util.asNode(nodeId).id) as component_nodes
            ORDER BY componentId
            """

            result = await self.client.execute_query(query)

            components = []
            for record in result.records:
                component_nodes = record.get("component_nodes", [])
                if component_nodes:
                    components.append(component_nodes)

            return components

        except Neo4jQueryError:
            # Fallback to basic connected components if GDS is not available
            return await self._basic_connected_components()
        except Exception as e:
            logger.error(f"Unexpected error getting connected components: {e}")
            raise GraphOperationError(
                f"Unexpected error getting connected components: {e}"
            )

    async def _basic_connected_components(self) -> List[List[str]]:
        """Basic connected components implementation without GDS."""
        try:
            # Get all nodes
            query = "MATCH (n) RETURN n.id as node_id"
            result = await self.client.execute_query(query)

            all_nodes = {record["node_id"] for record in result.records}
            visited = set()
            components = []

            for node_id in all_nodes:
                if node_id not in visited:
                    component = await self._bfs_component(node_id, visited)
                    if component:
                        components.append(component)

            return components

        except Exception as e:
            raise GraphOperationError(f"Failed to get basic connected components: {e}")

    async def _bfs_component(self, start_id: str, visited: Set[str]) -> List[str]:
        """BFS to find connected component starting from a node."""
        component = []
        queue = deque([start_id])
        visited.add(start_id)

        while queue:
            current_id = queue.popleft()
            component.append(current_id)

            # Get neighbors
            neighbors = await self.get_neighbors(current_id, depth=1)
            for neighbor in neighbors:
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    queue.append(neighbor.id)

        return component

    # Subgraph Operations

    async def get_neighbors(
        self,
        node_id: str,
        depth: int = 1,
        direction: str = "BOTH",
        rel_types: Optional[List[str]] = None,
    ) -> List[GraphNode]:
        """Get neighbors within specified depth.

        Args:
            node_id: Central node ID
            depth: Traversal depth (default: 1)
            direction: Direction ("IN", "OUT", "BOTH")
            rel_types: Optional relationship types to follow

        Returns:
            List of GraphNode objects

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if not node_id or not node_id.strip():
                raise ValidationError("Node ID cannot be empty")

            if depth < 1:
                raise ValidationError("Depth must be at least 1")

            if direction not in ["IN", "OUT", "BOTH"]:
                raise ValidationError("Direction must be IN, OUT, or BOTH")

            # Build direction pattern
            if direction == "IN":
                pattern = "<-"
            elif direction == "OUT":
                pattern = "->"
            else:
                pattern = "-"

            # Build relationship type filter
            rel_filter = ""
            if rel_types:
                rel_filter = f":{':'.join(rel_types)}"

            query = f"""
            MATCH (center {{id: $node_id}}){pattern}[{rel_filter}*1..{depth}]-(neighbor)
            WHERE neighbor.id <> $node_id
            RETURN DISTINCT neighbor
            """

            params = {"node_id": node_id.strip()}
            result = await self.client.execute_query(query, params)

            neighbors = []
            for record in result.records:
                neighbor_data = record.get("neighbor", {})
                if neighbor_data:
                    neighbor = self.node_manager._record_to_node(neighbor_data)
                    if neighbor:
                        neighbors.append(neighbor)

            return neighbors

        except ValidationError:
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to get neighbors: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting neighbors: {e}")
            raise GraphOperationError(f"Unexpected error getting neighbors: {e}")

    async def subgraph(
        self,
        node_ids: List[str],
        include_relationships: bool = True,
        rel_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Extract subgraph by node IDs.

        Args:
            node_ids: List of node IDs to include
            include_relationships: Whether to include relationships
            rel_types: Optional relationship types to include

        Returns:
            Dictionary with 'nodes' and 'relationships' keys

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If query fails
        """
        try:
            if not node_ids:
                raise ValidationError("Node IDs list cannot be empty")

            # Get nodes
            nodes = []
            for node_id in node_ids:
                node = await self.node_manager.get_node(node_id)
                if node:
                    nodes.append(node)

            subgraph_data = {"nodes": nodes, "relationships": []}

            if include_relationships:
                # Build relationship type filter
                rel_filter = ""
                if rel_types:
                    rel_filter = f":{':'.join(rel_types)}"

                query = f"""
                MATCH (a)-[r{rel_filter}]->(b)
                WHERE a.id IN $node_ids AND b.id IN $node_ids
                RETURN r, a.id as start_id, b.id as end_id, type(r) as rel_type
                """

                params = {"node_ids": node_ids}
                result = await self.client.execute_query(query, params)

                relationships = []
                for record in result.records:
                    rel_data = record.get("r", {})
                    start_id = record.get("start_id")
                    end_id = record.get("end_id")
                    rel_type = record.get("rel_type")

                    if rel_data and start_id and end_id and rel_type:
                        relationship = (
                            self.relationship_manager._record_to_relationship(
                                rel_data, start_id, end_id, rel_type
                            )
                        )
                        if relationship:
                            relationships.append(relationship)

                subgraph_data["relationships"] = relationships

            return subgraph_data

        except ValidationError:
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to extract subgraph: {e}")
        except Exception as e:
            logger.error(f"Unexpected error extracting subgraph: {e}")
            raise GraphOperationError(f"Unexpected error extracting subgraph: {e}")

    # Traversal Methods

    async def breadth_first_traversal(
        self, start_id: str, max_depth: int = 5, rel_types: Optional[List[str]] = None
    ) -> List[GraphNode]:
        """Perform breadth-first traversal from a starting node.

        Args:
            start_id: Starting node ID
            max_depth: Maximum traversal depth
            rel_types: Optional relationship types to follow

        Returns:
            List of GraphNode objects in BFS order

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If traversal fails
        """
        try:
            if not start_id or not start_id.strip():
                raise ValidationError("Start node ID cannot be empty")

            if max_depth < 1:
                raise ValidationError("Max depth must be at least 1")

            # Build relationship type filter
            rel_filter = ""
            if rel_types:
                rel_filter = f":{':'.join(rel_types)}"

            query = f"""
            MATCH path = (start {{id: $start_id}})-[{rel_filter}*0..{max_depth}]-(node)
            WITH node, length(path) as depth
            ORDER BY depth, node.id
            RETURN DISTINCT node, depth
            """

            params = {"start_id": start_id.strip()}
            result = await self.client.execute_query(query, params)

            nodes = []
            for record in result.records:
                node_data = record.get("node", {})
                if node_data:
                    node = self.node_manager._record_to_node(node_data)
                    if node:
                        nodes.append(node)

            return nodes

        except ValidationError:
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to perform BFS traversal: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in BFS traversal: {e}")
            raise GraphOperationError(f"Unexpected error in BFS traversal: {e}")

    async def depth_first_traversal(
        self, start_id: str, max_depth: int = 5, rel_types: Optional[List[str]] = None
    ) -> List[GraphNode]:
        """Perform depth-first traversal from a starting node.

        Args:
            start_id: Starting node ID
            max_depth: Maximum traversal depth
            rel_types: Optional relationship types to follow

        Returns:
            List of GraphNode objects in DFS order

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If traversal fails
        """
        try:
            if not start_id or not start_id.strip():
                raise ValidationError("Start node ID cannot be empty")

            if max_depth < 1:
                raise ValidationError("Max depth must be at least 1")

            visited = set()
            result_nodes = []

            await self._dfs_recursive(
                start_id, 0, max_depth, rel_types, visited, result_nodes
            )

            return result_nodes

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in DFS traversal: {e}")
            raise GraphOperationError(f"Unexpected error in DFS traversal: {e}")

    async def _dfs_recursive(
        self,
        node_id: str,
        current_depth: int,
        max_depth: int,
        rel_types: Optional[List[str]],
        visited: Set[str],
        result_nodes: List[GraphNode],
    ) -> None:
        """Recursive DFS helper method."""
        if current_depth > max_depth or node_id in visited:
            return

        visited.add(node_id)

        # Get current node
        node = await self.node_manager.get_node(node_id)
        if node:
            result_nodes.append(node)

        if current_depth < max_depth:
            # Get immediate neighbors
            neighbors = await self.get_neighbors(node_id, depth=1, rel_types=rel_types)
            for neighbor in neighbors:
                if neighbor.id not in visited:
                    await self._dfs_recursive(
                        neighbor.id,
                        current_depth + 1,
                        max_depth,
                        rel_types,
                        visited,
                        result_nodes,
                    )

    # Helper Methods

    async def _neo4j_path_to_graph_path(self, neo4j_path: Any) -> GraphPath:
        """Convert Neo4j path object to GraphPath."""
        try:
            # Extract nodes and relationships from Neo4j path
            # This is a simplified implementation - actual implementation
            # would depend on the Neo4j driver's path object structure

            nodes = []
            relationships = []

            # For now, create a basic GraphPath
            # In a real implementation, you'd extract the actual path data
            path = GraphPath(
                nodes=nodes, relationships=relationships, length=len(relationships)
            )

            return path

        except Exception as e:
            raise GraphOperationError(f"Failed to convert Neo4j path: {e}")
