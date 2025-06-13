"""Graph analytics and metrics calculations."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import GraphOperationError, Neo4jQueryError
from .neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class GraphAnalytics:
    """Advanced graph analytics and metrics calculations."""

    def __init__(self, client: Neo4jClient):
        """Initialize GraphAnalytics with Neo4j client.

        Args:
            client: Neo4jClient instance
        """
        self.client = client

    async def calculate_clustering_coefficient(
        self, node_id: Optional[str] = None
    ) -> Dict[str, float]:
        """Calculate clustering coefficient for a node or the entire graph.

        Args:
            node_id: Optional node ID to calculate for specific node

        Returns:
            Dictionary with clustering coefficient metrics

        Raises:
            GraphOperationError: If calculation fails
        """
        try:
            if node_id:
                # Calculate for specific node
                query = """
                MATCH (n {id: $node_id})-[:*1]-(neighbor)
                WITH n, collect(DISTINCT neighbor) as neighbors
                UNWIND neighbors as neighbor1
                UNWIND neighbors as neighbor2
                WITH n, neighbor1, neighbor2, neighbors
                WHERE neighbor1 <> neighbor2
                OPTIONAL MATCH (neighbor1)-[:*1]-(neighbor2)
                WITH n, count(DISTINCT [neighbor1, neighbor2]) as possible_edges,
                     count(DISTINCT CASE WHEN neighbor1 <> neighbor2 THEN [neighbor1, neighbor2] END) as actual_edges
                RETURN n.id as node_id,
                       CASE WHEN possible_edges > 0 THEN toFloat(actual_edges) / possible_edges ELSE 0.0 END as clustering_coefficient
                """
                params = {"node_id": node_id}
                result = await self.client.execute_query(query, params)

                if result.records:
                    record = result.records[0]
                    return {
                        "node_id": record.get("node_id"),
                        "clustering_coefficient": record.get(
                            "clustering_coefficient", 0.0
                        ),
                    }
                else:
                    return {"node_id": node_id, "clustering_coefficient": 0.0}
            else:
                # Calculate average clustering coefficient for entire graph
                query = """
                MATCH (n)
                OPTIONAL MATCH (n)-[:*1]-(neighbor)
                WITH n, collect(DISTINCT neighbor) as neighbors
                WHERE size(neighbors) >= 2
                UNWIND neighbors as neighbor1
                UNWIND neighbors as neighbor2
                WITH n, neighbor1, neighbor2, neighbors
                WHERE neighbor1 <> neighbor2
                OPTIONAL MATCH (neighbor1)-[:*1]-(neighbor2)
                WITH n, count(DISTINCT [neighbor1, neighbor2]) as possible_edges,
                     count(DISTINCT CASE WHEN neighbor1 <> neighbor2 THEN [neighbor1, neighbor2] END) as actual_edges
                WITH n, CASE WHEN possible_edges > 0 THEN toFloat(actual_edges) / possible_edges ELSE 0.0 END as node_clustering
                RETURN avg(node_clustering) as average_clustering_coefficient,
                       count(n) as nodes_with_clustering
                """
                result = await self.client.execute_query(query)

                if result.records:
                    record = result.records[0]
                    return {
                        "average_clustering_coefficient": record.get(
                            "average_clustering_coefficient", 0.0
                        ),
                        "nodes_with_clustering": record.get("nodes_with_clustering", 0),
                    }
                else:
                    return {
                        "average_clustering_coefficient": 0.0,
                        "nodes_with_clustering": 0,
                    }

        except Neo4jQueryError as e:
            raise GraphOperationError(
                f"Failed to calculate clustering coefficient: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error calculating clustering coefficient: {e}")
            raise GraphOperationError(
                f"Unexpected error calculating clustering coefficient: {e}"
            )

    async def find_central_nodes(
        self, centrality_type: str = "betweenness", limit: int = 10
    ) -> List[Tuple[str, float]]:
        """Find central nodes using various centrality measures.

        Args:
            centrality_type: Type of centrality ("betweenness", "closeness", "degree", "pagerank")
            limit: Maximum number of nodes to return

        Returns:
            List of tuples (node_id, centrality_score)

        Raises:
            GraphOperationError: If calculation fails
        """
        try:
            if centrality_type == "degree":
                query = """
                MATCH (n)
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(r) as degree
                RETURN n.id as node_id, degree as centrality_score
                ORDER BY centrality_score DESC
                LIMIT $limit
                """
            elif centrality_type == "closeness":
                query = """
                MATCH (n)
                OPTIONAL MATCH (n)-[*1..6]-(other)
                WITH n, count(DISTINCT other) as reachable_nodes,
                     sum(length(shortestPath((n)-[*]-(other)))) as total_distance
                WITH n, CASE WHEN total_distance > 0 THEN toFloat(reachable_nodes) / total_distance ELSE 0.0 END as closeness
                RETURN n.id as node_id, closeness as centrality_score
                ORDER BY centrality_score DESC
                LIMIT $limit
                """
            elif centrality_type == "betweenness":
                # Simplified betweenness centrality approximation
                query = """
                MATCH (n)
                OPTIONAL MATCH (start)-[*1..4]-(n)-[*1..4]-(end)
                WHERE start <> end AND start <> n AND end <> n
                WITH n, count(DISTINCT [start, end]) as paths_through_node
                RETURN n.id as node_id, paths_through_node as centrality_score
                ORDER BY centrality_score DESC
                LIMIT $limit
                """
            elif centrality_type == "pagerank":
                # Basic PageRank approximation
                query = """
                MATCH (n)
                OPTIONAL MATCH (n)<-[r]-()
                WITH n, count(r) as incoming_links
                RETURN n.id as node_id, incoming_links as centrality_score
                ORDER BY centrality_score DESC
                LIMIT $limit
                """
            else:
                raise GraphOperationError(f"Unknown centrality type: {centrality_type}")

            params = {"limit": limit}
            result = await self.client.execute_query(query, params)

            central_nodes = []
            for record in result.records:
                node_id = record.get("node_id")
                score = record.get("centrality_score", 0.0)
                if node_id is not None:
                    central_nodes.append((node_id, float(score)))

            return central_nodes

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to find central nodes: {e}")
        except Exception as e:
            logger.error(f"Unexpected error finding central nodes: {e}")
            raise GraphOperationError(f"Unexpected error finding central nodes: {e}")

    async def analyze_graph_diameter(self) -> Dict[str, Any]:
        """Analyze graph diameter and related metrics.

        Returns:
            Dictionary with diameter, radius, and average path length

        Raises:
            GraphOperationError: If analysis fails
        """
        try:
            # Calculate shortest paths between all pairs (limited for performance)
            query = """
            MATCH (start), (end)
            WHERE start <> end
            WITH start, end, shortestPath((start)-[*1..10]-(end)) as path
            WHERE path IS NOT NULL
            WITH length(path) as path_length
            RETURN max(path_length) as diameter,
                   min(path_length) as radius,
                   avg(toFloat(path_length)) as average_path_length,
                   count(*) as path_count
            """
            result = await self.client.execute_query(query)

            if result.records:
                record = result.records[0]
                return {
                    "diameter": record.get("diameter", 0),
                    "radius": record.get("radius", 0),
                    "average_path_length": record.get("average_path_length", 0.0),
                    "analyzed_paths": record.get("path_count", 0),
                }
            else:
                return {
                    "diameter": 0,
                    "radius": 0,
                    "average_path_length": 0.0,
                    "analyzed_paths": 0,
                }

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to analyze graph diameter: {e}")
        except Exception as e:
            logger.error(f"Unexpected error analyzing graph diameter: {e}")
            raise GraphOperationError(f"Unexpected error analyzing graph diameter: {e}")

    async def detect_communities(self, algorithm: str = "louvain") -> List[List[str]]:
        """Detect communities in the graph.

        Args:
            algorithm: Community detection algorithm ("louvain", "label_propagation")

        Returns:
            List of communities, each community is a list of node IDs

        Raises:
            GraphOperationError: If detection fails
        """
        try:
            if algorithm == "louvain":
                # Try to use GDS Louvain algorithm
                try:
                    query = """
                    CALL gds.louvain.stream('*')
                    YIELD nodeId, communityId
                    RETURN communityId, collect(gds.util.asNode(nodeId).id) as community_nodes
                    ORDER BY communityId
                    """
                    result = await self.client.execute_query(query)

                    communities = []
                    for record in result.records:
                        community_nodes = record.get("community_nodes", [])
                        if community_nodes:
                            communities.append(community_nodes)

                    return communities

                except Neo4jQueryError:
                    # Fallback to basic community detection
                    return await self._basic_community_detection()

            elif algorithm == "label_propagation":
                # Try to use GDS Label Propagation algorithm
                try:
                    query = """
                    CALL gds.labelPropagation.stream('*')
                    YIELD nodeId, communityId
                    RETURN communityId, collect(gds.util.asNode(nodeId).id) as community_nodes
                    ORDER BY communityId
                    """
                    result = await self.client.execute_query(query)

                    communities = []
                    for record in result.records:
                        community_nodes = record.get("community_nodes", [])
                        if community_nodes:
                            communities.append(community_nodes)

                    return communities

                except Neo4jQueryError:
                    # Fallback to basic community detection
                    return await self._basic_community_detection()
            else:
                raise GraphOperationError(
                    f"Unknown community detection algorithm: {algorithm}"
                )

        except GraphOperationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error detecting communities: {e}")
            raise GraphOperationError(f"Unexpected error detecting communities: {e}")

    async def _basic_community_detection(self) -> List[List[str]]:
        """Basic community detection using connected components."""
        try:
            query = """
            MATCH (n)
            OPTIONAL MATCH path = (n)-[*1..3]-(connected)
            WITH n, collect(DISTINCT connected.id) as connected_nodes
            RETURN n.id as node_id, connected_nodes
            """
            result = await self.client.execute_query(query)

            # Simple clustering based on shared connections
            node_connections = {}
            for record in result.records:
                node_id = record.get("node_id")
                connections = record.get("connected_nodes", [])
                if node_id:
                    node_connections[node_id] = set(connections)

            # Group nodes with similar connection patterns
            communities = []
            processed = set()

            for node_id, connections in node_connections.items():
                if node_id in processed:
                    continue

                community = [node_id]
                processed.add(node_id)

                # Find nodes with similar connections
                for other_node, other_connections in node_connections.items():
                    if other_node in processed:
                        continue

                    # Calculate Jaccard similarity
                    intersection = len(connections & other_connections)
                    union = len(connections | other_connections)
                    similarity = intersection / union if union > 0 else 0

                    if similarity > 0.3:  # Threshold for community membership
                        community.append(other_node)
                        processed.add(other_node)

                if len(community) > 1:
                    communities.append(community)

            return communities

        except Exception as e:
            raise GraphOperationError(f"Failed basic community detection: {e}")

    async def calculate_graph_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive graph metrics.

        Returns:
            Dictionary with various graph metrics

        Raises:
            GraphOperationError: If calculation fails
        """
        try:
            # Get basic stats
            stats_query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            RETURN count(DISTINCT n) as node_count,
                   count(r) as relationship_count,
                   avg(count(r)) as avg_degree
            """
            stats_result = await self.client.execute_query(stats_query)

            basic_metrics = {}
            if stats_result.records:
                record = stats_result.records[0]
                basic_metrics = {
                    "node_count": record.get("node_count", 0),
                    "relationship_count": record.get("relationship_count", 0),
                    "average_degree": record.get("avg_degree", 0.0),
                }

            # Calculate density
            node_count = basic_metrics.get("node_count", 0)
            rel_count = basic_metrics.get("relationship_count", 0)

            if node_count > 1:
                max_possible_edges = node_count * (node_count - 1)
                density = (
                    rel_count / max_possible_edges if max_possible_edges > 0 else 0.0
                )
            else:
                density = 0.0

            # Get clustering coefficient
            clustering_info = await self.calculate_clustering_coefficient()

            # Get diameter info
            diameter_info = await self.analyze_graph_diameter()

            # Combine all metrics
            metrics = {
                **basic_metrics,
                "density": density,
                "clustering_coefficient": clustering_info.get(
                    "average_clustering_coefficient", 0.0
                ),
                "diameter": diameter_info.get("diameter", 0),
                "radius": diameter_info.get("radius", 0),
                "average_path_length": diameter_info.get("average_path_length", 0.0),
            }

            return metrics

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to calculate graph metrics: {e}")
        except Exception as e:
            logger.error(f"Unexpected error calculating graph metrics: {e}")
            raise GraphOperationError(
                f"Unexpected error calculating graph metrics: {e}"
            )

    async def analyze_node_importance(self, node_id: str) -> Dict[str, Any]:
        """Analyze the importance of a specific node in the graph.

        Args:
            node_id: Node ID to analyze

        Returns:
            Dictionary with importance metrics

        Raises:
            GraphOperationError: If analysis fails
        """
        try:
            # Get degree centrality
            degree_query = """
            MATCH (n {id: $node_id})
            OPTIONAL MATCH (n)-[r]-()
            RETURN count(r) as degree,
                   count(CASE WHEN startNode(r) = n THEN 1 END) as out_degree,
                   count(CASE WHEN endNode(r) = n THEN 1 END) as in_degree
            """
            degree_result = await self.client.execute_query(
                degree_query, {"node_id": node_id}
            )

            degree_metrics = {}
            if degree_result.records:
                record = degree_result.records[0]
                degree_metrics = {
                    "degree": record.get("degree", 0),
                    "out_degree": record.get("out_degree", 0),
                    "in_degree": record.get("in_degree", 0),
                }

            # Get clustering coefficient for this node
            clustering_info = await self.calculate_clustering_coefficient(node_id)

            # Get neighbors count at different depths
            neighbors_query = """
            MATCH (n {id: $node_id})
            OPTIONAL MATCH (n)-[*1]-(neighbor1)
            OPTIONAL MATCH (n)-[*2]-(neighbor2)
            OPTIONAL MATCH (n)-[*3]-(neighbor3)
            RETURN count(DISTINCT neighbor1) as neighbors_depth_1,
                   count(DISTINCT neighbor2) as neighbors_depth_2,
                   count(DISTINCT neighbor3) as neighbors_depth_3
            """
            neighbors_result = await self.client.execute_query(
                neighbors_query, {"node_id": node_id}
            )

            neighbors_metrics = {}
            if neighbors_result.records:
                record = neighbors_result.records[0]
                neighbors_metrics = {
                    "neighbors_depth_1": record.get("neighbors_depth_1", 0),
                    "neighbors_depth_2": record.get("neighbors_depth_2", 0),
                    "neighbors_depth_3": record.get("neighbors_depth_3", 0),
                }

            # Combine all importance metrics
            importance_metrics = {
                "node_id": node_id,
                **degree_metrics,
                "clustering_coefficient": clustering_info.get(
                    "clustering_coefficient", 0.0
                ),
                **neighbors_metrics,
            }

            return importance_metrics

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to analyze node importance: {e}")
        except Exception as e:
            logger.error(f"Unexpected error analyzing node importance: {e}")
            raise GraphOperationError(
                f"Unexpected error analyzing node importance: {e}"
            )
