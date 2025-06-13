"""Advanced graph algorithms implementation."""

import logging
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import GraphOperationError, Neo4jQueryError, ValidationError
from .neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class GraphAlgorithms:
    """Advanced graph algorithms implementation."""

    def __init__(self, client: Neo4jClient):
        """Initialize GraphAlgorithms with Neo4j client.

        Args:
            client: Neo4jClient instance
        """
        self.client = client

    async def topological_sort(self, labels: Optional[List[str]] = None) -> List[str]:
        """Perform topological sort on the graph.

        Args:
            labels: Optional node labels to filter by

        Returns:
            List of node IDs in topological order

        Raises:
            GraphOperationError: If graph has cycles or sort fails
        """
        try:
            # Build label filter
            label_filter = ""
            if labels:
                label_filter = f":{':'.join(labels)}"

            # Get all nodes and their incoming edges
            query = f"""
            MATCH (n{label_filter})
            OPTIONAL MATCH (n)<-[r]-(m{label_filter})
            WITH n, count(r) as in_degree, collect(m.id) as predecessors
            RETURN n.id as node_id, in_degree, predecessors
            ORDER BY in_degree
            """

            result = await self.client.execute_query(query)

            # Build adjacency list and in-degree count
            in_degree = {}
            adjacency = defaultdict(list)
            all_nodes = set()

            for record in result.records:
                node_id = record.get("node_id")
                degree = record.get("in_degree", 0)
                predecessors = record.get("predecessors", [])

                if node_id:
                    all_nodes.add(node_id)
                    in_degree[node_id] = degree

                    for pred in predecessors:
                        if pred:
                            adjacency[pred].append(node_id)

            # Kahn's algorithm for topological sorting
            queue = deque([node for node in all_nodes if in_degree.get(node, 0) == 0])
            topo_order = []

            while queue:
                current = queue.popleft()
                topo_order.append(current)

                # Reduce in-degree of neighbors
                for neighbor in adjacency[current]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            # Check for cycles
            if len(topo_order) != len(all_nodes):
                remaining_nodes = all_nodes - set(topo_order)
                raise GraphOperationError(
                    f"Graph contains cycles. Remaining nodes: {remaining_nodes}"
                )

            return topo_order

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to perform topological sort: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in topological sort: {e}")
            raise GraphOperationError(f"Unexpected error in topological sort: {e}")

    async def find_strongly_connected_components(self) -> List[List[str]]:
        """Find strongly connected components using Tarjan's algorithm.

        Returns:
            List of strongly connected components, each as a list of node IDs

        Raises:
            GraphOperationError: If algorithm fails
        """
        try:
            # Get all nodes and their outgoing relationships
            query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]->(m)
            WITH n, collect(m.id) as successors
            RETURN n.id as node_id, successors
            """

            result = await self.client.execute_query(query)

            # Build adjacency list
            adjacency = {}
            all_nodes = set()

            for record in result.records:
                node_id = record.get("node_id")
                successors = record.get("successors", [])

                if node_id:
                    all_nodes.add(node_id)
                    adjacency[node_id] = [s for s in successors if s]

            # Tarjan's algorithm implementation
            index_counter = [0]
            stack = []
            lowlinks = {}
            index = {}
            on_stack = {}
            components = []

            def strongconnect(node):
                # Set the depth index for this node to the smallest unused index
                index[node] = index_counter[0]
                lowlinks[node] = index_counter[0]
                index_counter[0] += 1
                stack.append(node)
                on_stack[node] = True

                # Consider successors of node
                for successor in adjacency.get(node, []):
                    if successor not in index:
                        # Successor has not yet been visited; recurse on it
                        strongconnect(successor)
                        lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                    elif on_stack.get(successor, False):
                        # Successor is in stack and hence in the current SCC
                        lowlinks[node] = min(lowlinks[node], index[successor])

                # If node is a root node, pop the stack and create an SCC
                if lowlinks[node] == index[node]:
                    component = []
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        component.append(w)
                        if w == node:
                            break
                    components.append(component)

            # Run algorithm on all unvisited nodes
            for node in all_nodes:
                if node not in index:
                    strongconnect(node)

            return components

        except Neo4jQueryError as e:
            raise GraphOperationError(
                f"Failed to find strongly connected components: {e}"
            )
        except Exception as e:
            logger.error(f"Unexpected error finding strongly connected components: {e}")
            raise GraphOperationError(
                f"Unexpected error finding strongly connected components: {e}"
            )

    async def detect_bridges(self) -> List[Tuple[str, str]]:
        """Detect bridge edges in the graph using Tarjan's bridge-finding algorithm.

        Returns:
            List of bridge edges as tuples (start_node_id, end_node_id)

        Raises:
            GraphOperationError: If algorithm fails
        """
        try:
            # Get all relationships
            query = """
            MATCH (a)-[r]->(b)
            RETURN a.id as start_id, b.id as end_id, type(r) as rel_type
            """

            result = await self.client.execute_query(query)

            # Build adjacency list for undirected graph
            adjacency = defaultdict(list)
            edges = set()
            all_nodes = set()

            for record in result.records:
                start_id = record.get("start_id")
                end_id = record.get("end_id")

                if start_id and end_id:
                    all_nodes.add(start_id)
                    all_nodes.add(end_id)
                    adjacency[start_id].append(end_id)
                    adjacency[end_id].append(start_id)  # Treat as undirected
                    edges.add((start_id, end_id))

            # Tarjan's bridge-finding algorithm
            visited = set()
            disc = {}
            low = {}
            parent = {}
            bridges = []
            time = [0]

            def bridge_util(u):
                visited.add(u)
                disc[u] = low[u] = time[0]
                time[0] += 1

                for v in adjacency[u]:
                    if v not in visited:
                        parent[v] = u
                        bridge_util(v)

                        # Check if the subtree rooted at v has a connection back
                        # to one of the ancestors of u
                        low[u] = min(low[u], low[v])

                        # If the lowest vertex reachable from subtree under v
                        # is below u in DFS tree, then u-v is a bridge
                        if low[v] > disc[u]:
                            bridges.append((u, v))
                    elif v != parent.get(u):
                        # Update low value of u for parent function calls
                        low[u] = min(low[u], disc[v])

            # Run algorithm on all unvisited nodes
            for node in all_nodes:
                if node not in visited:
                    bridge_util(node)

            # Filter bridges to only include original directed edges
            filtered_bridges = []
            for bridge in bridges:
                start, end = bridge
                if (start, end) in edges:
                    filtered_bridges.append((start, end))
                elif (end, start) in edges:
                    filtered_bridges.append((end, start))

            return filtered_bridges

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to detect bridges: {e}")
        except Exception as e:
            logger.error(f"Unexpected error detecting bridges: {e}")
            raise GraphOperationError(f"Unexpected error detecting bridges: {e}")

    async def find_articulation_points(self) -> List[str]:
        """Find articulation points (cut vertices) in the graph.

        Returns:
            List of node IDs that are articulation points

        Raises:
            GraphOperationError: If algorithm fails
        """
        try:
            # Get all relationships to build adjacency list
            query = """
            MATCH (a)-[r]-(b)
            RETURN DISTINCT a.id as node_a, b.id as node_b
            """

            result = await self.client.execute_query(query)

            # Build adjacency list for undirected graph
            adjacency = defaultdict(list)
            all_nodes = set()

            for record in result.records:
                node_a = record.get("node_a")
                node_b = record.get("node_b")

                if node_a and node_b and node_a != node_b:
                    all_nodes.add(node_a)
                    all_nodes.add(node_b)
                    adjacency[node_a].append(node_b)
                    adjacency[node_b].append(node_a)

            # Tarjan's algorithm for finding articulation points
            visited = set()
            disc = {}
            low = {}
            parent = {}
            ap = set()  # Articulation points
            time = [0]

            def ap_util(u):
                children = 0
                visited.add(u)
                disc[u] = low[u] = time[0]
                time[0] += 1

                for v in adjacency[u]:
                    if v not in visited:
                        children += 1
                        parent[v] = u
                        ap_util(v)

                        # Check if subtree rooted at v has a connection back
                        # to one of the ancestors of u
                        low[u] = min(low[u], low[v])

                        # u is an articulation point in the following cases:

                        # (1) u is root of DFS tree and has two or more children
                        if parent.get(u) is None and children > 1:
                            ap.add(u)

                        # (2) u is not root and low value of one of its child
                        # is more than or equal to the discovery value of u
                        if parent.get(u) is not None and low[v] >= disc[u]:
                            ap.add(u)

                    elif v != parent.get(u):
                        # Update low value of u for parent function calls
                        low[u] = min(low[u], disc[v])

            # Run algorithm on all unvisited nodes
            for node in all_nodes:
                if node not in visited:
                    ap_util(node)

            return list(ap)

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to find articulation points: {e}")
        except Exception as e:
            logger.error(f"Unexpected error finding articulation points: {e}")
            raise GraphOperationError(
                f"Unexpected error finding articulation points: {e}"
            )

    async def find_minimum_spanning_tree(
        self, weight_property: str = "weight"
    ) -> List[Tuple[str, str, float]]:
        """Find minimum spanning tree using Kruskal's algorithm.

        Args:
            weight_property: Property name for edge weights

        Returns:
            List of edges in MST as tuples (start_id, end_id, weight)

        Raises:
            GraphOperationError: If algorithm fails
        """
        try:
            # Get all relationships with weights
            query = f"""
            MATCH (a)-[r]-(b)
            WHERE r.{weight_property} IS NOT NULL
            RETURN DISTINCT a.id as start_id, b.id as end_id, r.{weight_property} as weight
            ORDER BY weight
            """

            result = await self.client.execute_query(query)

            # Collect edges and nodes
            edges = []
            all_nodes = set()

            for record in result.records:
                start_id = record.get("start_id")
                end_id = record.get("end_id")
                weight = record.get("weight", 0.0)

                if start_id and end_id and start_id != end_id:
                    all_nodes.add(start_id)
                    all_nodes.add(end_id)
                    edges.append((weight, start_id, end_id))

            # Sort edges by weight
            edges.sort()

            # Union-Find data structure
            parent = {node: node for node in all_nodes}
            rank = {node: 0 for node in all_nodes}

            def find(node):
                if parent[node] != node:
                    parent[node] = find(parent[node])
                return parent[node]

            def union(node1, node2):
                root1 = find(node1)
                root2 = find(node2)

                if root1 != root2:
                    if rank[root1] < rank[root2]:
                        parent[root1] = root2
                    elif rank[root1] > rank[root2]:
                        parent[root2] = root1
                    else:
                        parent[root2] = root1
                        rank[root1] += 1
                    return True
                return False

            # Kruskal's algorithm
            mst_edges = []
            edges_added = 0
            target_edges = len(all_nodes) - 1

            for weight, start_id, end_id in edges:
                if union(start_id, end_id):
                    mst_edges.append((start_id, end_id, weight))
                    edges_added += 1
                    if edges_added == target_edges:
                        break

            return mst_edges

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to find minimum spanning tree: {e}")
        except Exception as e:
            logger.error(f"Unexpected error finding minimum spanning tree: {e}")
            raise GraphOperationError(
                f"Unexpected error finding minimum spanning tree: {e}"
            )

    async def detect_negative_cycles(
        self, weight_property: str = "weight"
    ) -> List[List[str]]:
        """Detect negative cycles using Bellman-Ford algorithm.

        Args:
            weight_property: Property name for edge weights

        Returns:
            List of negative cycles, each as a list of node IDs

        Raises:
            GraphOperationError: If algorithm fails
        """
        try:
            # Get all nodes and relationships with weights
            nodes_query = "MATCH (n) RETURN n.id as node_id"
            nodes_result = await self.client.execute_query(nodes_query)

            edges_query = f"""
            MATCH (a)-[r]->(b)
            WHERE r.{weight_property} IS NOT NULL
            RETURN a.id as start_id, b.id as end_id, r.{weight_property} as weight
            """
            edges_result = await self.client.execute_query(edges_query)

            # Collect nodes and edges
            nodes = [
                record["node_id"]
                for record in nodes_result.records
                if record["node_id"]
            ]
            edges = []

            for record in edges_result.records:
                start_id = record.get("start_id")
                end_id = record.get("end_id")
                weight = record.get("weight", 0.0)

                if start_id and end_id:
                    edges.append((start_id, end_id, weight))

            if not nodes:
                return []

            # Bellman-Ford algorithm to detect negative cycles
            negative_cycles = []

            for source in nodes:
                # Initialize distances
                dist = {node: float("inf") for node in nodes}
                dist[source] = 0
                predecessor = {node: None for node in nodes}

                # Relax edges |V| - 1 times
                for _ in range(len(nodes) - 1):
                    for start_id, end_id, weight in edges:
                        if (
                            dist[start_id] != float("inf")
                            and dist[start_id] + weight < dist[end_id]
                        ):
                            dist[end_id] = dist[start_id] + weight
                            predecessor[end_id] = start_id

                # Check for negative cycles
                for start_id, end_id, weight in edges:
                    if (
                        dist[start_id] != float("inf")
                        and dist[start_id] + weight < dist[end_id]
                    ):
                        # Negative cycle detected, trace it
                        cycle = []
                        current = end_id
                        visited = set()

                        while current not in visited:
                            visited.add(current)
                            cycle.append(current)
                            current = predecessor[current]
                            if current is None:
                                break

                        if current in visited:
                            # Find the actual cycle
                            cycle_start = cycle.index(current)
                            actual_cycle = cycle[cycle_start:]
                            if actual_cycle not in negative_cycles:
                                negative_cycles.append(actual_cycle)

            return negative_cycles

        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to detect negative cycles: {e}")
        except Exception as e:
            logger.error(f"Unexpected error detecting negative cycles: {e}")
            raise GraphOperationError(
                f"Unexpected error detecting negative cycles: {e}"
            )

    async def find_maximum_flow(
        self, source_id: str, sink_id: str, capacity_property: str = "capacity"
    ) -> Dict[str, Any]:
        """Find maximum flow using Ford-Fulkerson algorithm.

        Args:
            source_id: Source node ID
            sink_id: Sink node ID
            capacity_property: Property name for edge capacities

        Returns:
            Dictionary with max_flow value and flow details

        Raises:
            ValidationError: If input is invalid
            GraphOperationError: If algorithm fails
        """
        try:
            if not source_id or not source_id.strip():
                raise ValidationError("Source node ID cannot be empty")

            if not sink_id or not sink_id.strip():
                raise ValidationError("Sink node ID cannot be empty")

            # Get all relationships with capacities
            query = f"""
            MATCH (a)-[r]->(b)
            WHERE r.{capacity_property} IS NOT NULL
            RETURN a.id as start_id, b.id as end_id, r.{capacity_property} as capacity
            """

            result = await self.client.execute_query(query)

            # Build capacity matrix
            capacity = defaultdict(lambda: defaultdict(int))
            nodes = set()

            for record in result.records:
                start_id = record.get("start_id")
                end_id = record.get("end_id")
                cap = record.get("capacity", 0)

                if start_id and end_id:
                    nodes.add(start_id)
                    nodes.add(end_id)
                    capacity[start_id][end_id] = cap

            if source_id not in nodes or sink_id not in nodes:
                raise GraphOperationError("Source or sink node not found in graph")

            # Ford-Fulkerson algorithm with BFS (Edmonds-Karp)
            def bfs_find_path():
                visited = set()
                queue = deque([(source_id, [source_id])])
                visited.add(source_id)

                while queue:
                    current, path = queue.popleft()

                    if current == sink_id:
                        return path

                    for neighbor in capacity[current]:
                        if neighbor not in visited and capacity[current][neighbor] > 0:
                            visited.add(neighbor)
                            queue.append((neighbor, path + [neighbor]))

                return None

            max_flow_value = 0
            flow_paths = []

            while True:
                path = bfs_find_path()
                if not path:
                    break

                # Find minimum capacity along the path
                path_flow = float("inf")
                for i in range(len(path) - 1):
                    path_flow = min(path_flow, capacity[path[i]][path[i + 1]])

                # Update capacities
                for i in range(len(path) - 1):
                    capacity[path[i]][path[i + 1]] -= path_flow
                    capacity[path[i + 1]][path[i]] += path_flow  # Reverse edge

                max_flow_value += path_flow
                flow_paths.append({"path": path, "flow": path_flow})

            return {
                "max_flow": max_flow_value,
                "flow_paths": flow_paths,
                "source": source_id,
                "sink": sink_id,
            }

        except ValidationError:
            raise
        except Neo4jQueryError as e:
            raise GraphOperationError(f"Failed to find maximum flow: {e}")
        except Exception as e:
            logger.error(f"Unexpected error finding maximum flow: {e}")
            raise GraphOperationError(f"Unexpected error finding maximum flow: {e}")
