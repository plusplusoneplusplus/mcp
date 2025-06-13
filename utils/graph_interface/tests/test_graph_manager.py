"""Tests for GraphManager class."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from ..graph_manager import GraphManager
from ..models import GraphNode, GraphRelationship, GraphPath, GraphStats, QueryResult
from ..exceptions import GraphOperationError, ValidationError
from ..neo4j_client import Neo4jClient


class TestGraphManager:
    """Test GraphManager class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Neo4j client."""
        client = AsyncMock(spec=Neo4jClient)
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def graph_manager(self, mock_client):
        """Create GraphManager instance with mock client."""
        return GraphManager(mock_client)

    @pytest.mark.asyncio
    async def test_init(self, mock_client):
        """Test GraphManager initialization."""
        manager = GraphManager(mock_client)
        assert manager.client == mock_client
        assert manager.node_manager is not None
        assert manager.relationship_manager is not None

    @pytest.mark.asyncio
    async def test_create_factory_method(self):
        """Test GraphManager.create factory method."""
        with patch('utils.graph_interface.graph_manager.Neo4jClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            manager = await GraphManager.create(
                "bolt://localhost:7687",
                "neo4j",
                "password"
            )

            mock_client_class.assert_called_once_with(
                "bolt://localhost:7687", "neo4j", "password", "neo4j"
            )
            mock_client.connect.assert_called_once()
            assert isinstance(manager, GraphManager)

    @pytest.mark.asyncio
    async def test_create_factory_method_failure(self):
        """Test GraphManager.create factory method failure."""
        with patch('utils.graph_interface.graph_manager.Neo4jClient') as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            with pytest.raises(GraphOperationError, match="Failed to create GraphManager"):
                await GraphManager.create("bolt://localhost:7687", "neo4j", "password")

    @pytest.mark.asyncio
    async def test_close(self, graph_manager, mock_client):
        """Test closing graph manager."""
        await graph_manager.close()
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_graph_stats(self, graph_manager, mock_client):
        """Test getting graph statistics."""
        # Mock node query result
        node_result = QueryResult(
            records=[
                {'node_count': 10, 'node_labels': ['Person', 'Company']},
                {'node_count': 5, 'node_labels': ['Person']},
                {'node_count': 3, 'node_labels': ['Company']}
            ]
        )

        # Mock relationship query result
        rel_result = QueryResult(
            records=[
                {'rel_count': 8, 'rel_type': 'WORKS_FOR'},
                {'rel_count': 5, 'rel_type': 'KNOWS'}
            ]
        )

        mock_client.execute_query.side_effect = [node_result, rel_result]

        stats = await graph_manager.get_graph_stats()

        assert isinstance(stats, GraphStats)
        assert stats.node_count == 18  # 10 + 5 + 3
        assert stats.relationship_count == 13  # 8 + 5
        assert 'Person' in stats.labels
        assert 'Company' in stats.labels
        assert 'WORKS_FOR' in stats.relationship_types
        assert 'KNOWS' in stats.relationship_types

    @pytest.mark.asyncio
    async def test_calculate_graph_density(self, graph_manager):
        """Test calculating graph density."""
        with patch.object(graph_manager, 'get_graph_stats') as mock_stats:
            mock_stats.return_value = GraphStats(
                node_count=4,
                relationship_count=6
            )

            density = await graph_manager.calculate_graph_density()
            assert density == 0.5  # 6 / (4 * 3) = 0.5

    @pytest.mark.asyncio
    async def test_get_degree_distribution(self, graph_manager, mock_client):
        """Test getting degree distribution."""
        result = QueryResult(
            records=[
                {'degree': 0, 'node_count': 2},
                {'degree': 1, 'node_count': 5},
                {'degree': 2, 'node_count': 3},
                {'degree': 3, 'node_count': 1}
            ]
        )
        mock_client.execute_query.return_value = result

        distribution = await graph_manager.get_degree_distribution()

        assert distribution == {0: 2, 1: 5, 2: 3, 3: 1}

    @pytest.mark.asyncio
    async def test_find_paths(self, graph_manager, mock_client):
        """Test finding paths between nodes."""
        # Mock path result
        mock_path_data = MagicMock()
        result = QueryResult(
            records=[
                {'path': mock_path_data, 'path_length': 2}
            ]
        )
        mock_client.execute_query.return_value = result

        # Mock path conversion
        with patch.object(graph_manager, '_neo4j_path_to_graph_path') as mock_convert:
            # Create a valid GraphPath with relationships to match length
            mock_rel1 = GraphRelationship(type="CONNECTS", start_node_id="node1", end_node_id="node2")
            mock_rel2 = GraphRelationship(type="CONNECTS", start_node_id="node2", end_node_id="node3")
            mock_path = GraphPath(length=2, relationships=[mock_rel1, mock_rel2])
            mock_convert.return_value = mock_path

            paths = await graph_manager.find_paths("node1", "node2", max_depth=3)

            assert len(paths) == 1
            assert paths[0] == mock_path
            mock_convert.assert_called_once_with(mock_path_data)

    @pytest.mark.asyncio
    async def test_find_paths_validation_error(self, graph_manager):
        """Test find_paths with invalid input."""
        with pytest.raises(ValidationError, match="Start node ID cannot be empty"):
            await graph_manager.find_paths("", "node2")

        with pytest.raises(ValidationError, match="End node ID cannot be empty"):
            await graph_manager.find_paths("node1", "")

        with pytest.raises(ValidationError, match="Max depth must be at least 1"):
            await graph_manager.find_paths("node1", "node2", max_depth=0)

    @pytest.mark.asyncio
    async def test_calculate_shortest_path(self, graph_manager, mock_client):
        """Test calculating shortest path."""
        mock_path_data = MagicMock()
        result = QueryResult(
            records=[
                {'path': mock_path_data, 'path_length': 2}
            ]
        )
        mock_client.execute_query.return_value = result

        with patch.object(graph_manager, '_neo4j_path_to_graph_path') as mock_convert:
            # Create a valid GraphPath with relationships to match length
            mock_rel1 = GraphRelationship(type="CONNECTS", start_node_id="node1", end_node_id="node2")
            mock_rel2 = GraphRelationship(type="CONNECTS", start_node_id="node2", end_node_id="node3")
            mock_path = GraphPath(length=2, relationships=[mock_rel1, mock_rel2])
            mock_convert.return_value = mock_path

            path = await graph_manager.calculate_shortest_path("node1", "node2")

            assert path == mock_path

    @pytest.mark.asyncio
    async def test_calculate_shortest_path_no_path(self, graph_manager, mock_client):
        """Test calculating shortest path when no path exists."""
        result = QueryResult(records=[])
        mock_client.execute_query.return_value = result

        path = await graph_manager.calculate_shortest_path("node1", "node2")
        assert path is None

    @pytest.mark.asyncio
    async def test_detect_cycles(self, graph_manager, mock_client):
        """Test detecting cycles in the graph."""
        result = QueryResult(
            records=[
                {'cycle': ['A', 'B', 'C', 'A']},
                {'cycle': ['D', 'E', 'D']},
                {'cycle': ['A', 'B', 'C', 'A']}  # Duplicate
            ]
        )
        mock_client.execute_query.return_value = result

        cycles = await graph_manager.detect_cycles()

        # Should deduplicate cycles
        assert len(cycles) == 2
        assert ['A', 'B', 'C', 'A'] in cycles
        assert ['D', 'E', 'D'] in cycles

    @pytest.mark.asyncio
    async def test_detect_cycles_validation_error(self, graph_manager):
        """Test detect_cycles with invalid max_depth."""
        with pytest.raises(ValidationError, match="Max depth must be at least 2"):
            await graph_manager.detect_cycles(max_depth=1)

    @pytest.mark.asyncio
    async def test_get_connected_components_gds(self, graph_manager, mock_client):
        """Test getting connected components with GDS."""
        result = QueryResult(
            records=[
                {'componentId': 1, 'component_nodes': ['A', 'B', 'C']},
                {'componentId': 2, 'component_nodes': ['D', 'E']}
            ]
        )
        mock_client.execute_query.return_value = result

        components = await graph_manager.get_connected_components()

        assert len(components) == 2
        assert ['A', 'B', 'C'] in components
        assert ['D', 'E'] in components

    @pytest.mark.asyncio
    async def test_get_connected_components_fallback(self, graph_manager, mock_client):
        """Test getting connected components with fallback method."""
        from ..exceptions import Neo4jQueryError

        # First call fails (GDS not available), second succeeds (fallback)
        mock_client.execute_query.side_effect = [
            Neo4jQueryError("GDS not available"),
            QueryResult(records=[{'node_id': 'A'}, {'node_id': 'B'}])
        ]

        with patch.object(graph_manager, '_bfs_component') as mock_bfs:
            # Mock BFS to return component for first unvisited node only
            mock_bfs.side_effect = lambda node_id, visited: ['A', 'B'] if node_id == 'A' else []

            components = await graph_manager.get_connected_components()

            assert len(components) == 1
            assert ['A', 'B'] in components

    @pytest.mark.asyncio
    async def test_get_neighbors(self, graph_manager, mock_client):
        """Test getting neighbors of a node."""
        result = QueryResult(
            records=[
                {'neighbor': {'id': 'B', 'name': 'Node B'}},
                {'neighbor': {'id': 'C', 'name': 'Node C'}}
            ]
        )
        mock_client.execute_query.return_value = result

        # Mock node manager's _record_to_node method
        mock_node_b = GraphNode(id='B', properties={'name': 'Node B'})
        mock_node_c = GraphNode(id='C', properties={'name': 'Node C'})

        with patch.object(graph_manager.node_manager, '_record_to_node') as mock_convert:
            mock_convert.side_effect = [mock_node_b, mock_node_c]

            neighbors = await graph_manager.get_neighbors("A", depth=1)

            assert len(neighbors) == 2
            assert neighbors[0].id == 'B'
            assert neighbors[1].id == 'C'

    @pytest.mark.asyncio
    async def test_get_neighbors_validation_error(self, graph_manager):
        """Test get_neighbors with invalid input."""
        with pytest.raises(ValidationError, match="Node ID cannot be empty"):
            await graph_manager.get_neighbors("")

        with pytest.raises(ValidationError, match="Depth must be at least 1"):
            await graph_manager.get_neighbors("A", depth=0)

        with pytest.raises(ValidationError, match="Direction must be IN, OUT, or BOTH"):
            await graph_manager.get_neighbors("A", direction="INVALID")

    @pytest.mark.asyncio
    async def test_subgraph(self, graph_manager, mock_client):
        """Test extracting subgraph."""
        # Mock node retrieval
        mock_node_a = GraphNode(id='A')
        mock_node_b = GraphNode(id='B')

        with patch.object(graph_manager.node_manager, 'get_node') as mock_get_node:
            mock_get_node.side_effect = [mock_node_a, mock_node_b]

            # Mock relationship query
            result = QueryResult(
                records=[
                    {
                        'r': {'weight': 1.0},
                        'start_id': 'A',
                        'end_id': 'B',
                        'rel_type': 'CONNECTS'
                    }
                ]
            )
            mock_client.execute_query.return_value = result

            # Mock relationship conversion
            mock_rel = GraphRelationship(
                type='CONNECTS',
                start_node_id='A',
                end_node_id='B',
                properties={'weight': 1.0}
            )

            with patch.object(graph_manager.relationship_manager, '_record_to_relationship') as mock_convert:
                mock_convert.return_value = mock_rel

                subgraph = await graph_manager.subgraph(['A', 'B'])

                assert 'nodes' in subgraph
                assert 'relationships' in subgraph
                assert len(subgraph['nodes']) == 2
                assert len(subgraph['relationships']) == 1

    @pytest.mark.asyncio
    async def test_subgraph_validation_error(self, graph_manager):
        """Test subgraph with empty node list."""
        with pytest.raises(ValidationError, match="Node IDs list cannot be empty"):
            await graph_manager.subgraph([])

    @pytest.mark.asyncio
    async def test_breadth_first_traversal(self, graph_manager, mock_client):
        """Test breadth-first traversal."""
        result = QueryResult(
            records=[
                {'node': {'id': 'A'}, 'depth': 0},
                {'node': {'id': 'B'}, 'depth': 1},
                {'node': {'id': 'C'}, 'depth': 1}
            ]
        )
        mock_client.execute_query.return_value = result

        mock_nodes = [
            GraphNode(id='A'),
            GraphNode(id='B'),
            GraphNode(id='C')
        ]

        with patch.object(graph_manager.node_manager, '_record_to_node') as mock_convert:
            mock_convert.side_effect = mock_nodes

            nodes = await graph_manager.breadth_first_traversal("A", max_depth=2)

            assert len(nodes) == 3
            assert nodes[0].id == 'A'
            assert nodes[1].id == 'B'
            assert nodes[2].id == 'C'

    @pytest.mark.asyncio
    async def test_depth_first_traversal(self, graph_manager):
        """Test depth-first traversal."""
        with patch.object(graph_manager, '_dfs_recursive') as mock_dfs:
            await graph_manager.depth_first_traversal("A", max_depth=2)
            mock_dfs.assert_called_once()

    @pytest.mark.asyncio
    async def test_dfs_recursive(self, graph_manager):
        """Test DFS recursive helper method."""
        # Mock get_node and get_neighbors
        mock_node = GraphNode(id='A')
        mock_neighbors = [GraphNode(id='B'), GraphNode(id='C')]

        with patch.object(graph_manager.node_manager, 'get_node') as mock_get_node:
            with patch.object(graph_manager, 'get_neighbors') as mock_get_neighbors:
                mock_get_node.return_value = mock_node
                mock_get_neighbors.return_value = mock_neighbors

                visited = set()
                result_nodes = []

                await graph_manager._dfs_recursive(
                    'A', 0, 2, None, visited, result_nodes
                )

                assert 'A' in visited
                assert len(result_nodes) >= 1
                assert result_nodes[0].id == 'A'

    @pytest.mark.asyncio
    async def test_neo4j_path_to_graph_path(self, graph_manager):
        """Test converting Neo4j path to GraphPath."""
        mock_neo4j_path = MagicMock()

        path = await graph_manager._neo4j_path_to_graph_path(mock_neo4j_path)

        assert isinstance(path, GraphPath)
        assert path.length == 0  # Basic implementation returns empty path

    @pytest.mark.asyncio
    async def test_bfs_component(self, graph_manager):
        """Test BFS component finding."""
        mock_neighbors = [GraphNode(id='B'), GraphNode(id='C')]

        with patch.object(graph_manager, 'get_neighbors') as mock_get_neighbors:
            mock_get_neighbors.return_value = mock_neighbors

            visited = set()
            component = await graph_manager._bfs_component('A', visited)

            assert 'A' in component
            assert 'A' in visited
