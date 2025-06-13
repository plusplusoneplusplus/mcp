"""Tests for GraphAlgorithms class."""

import pytest
from unittest.mock import AsyncMock

from ..algorithms import GraphAlgorithms
from ..models import QueryResult
from ..exceptions import GraphOperationError, ValidationError
from ..neo4j_client import Neo4jClient


class TestGraphAlgorithms:
    """Test GraphAlgorithms class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Neo4j client."""
        client = AsyncMock(spec=Neo4jClient)
        return client

    @pytest.fixture
    def algorithms(self, mock_client):
        """Create GraphAlgorithms instance with mock client."""
        return GraphAlgorithms(mock_client)

    @pytest.mark.asyncio
    async def test_init(self, mock_client):
        """Test GraphAlgorithms initialization."""
        algorithms = GraphAlgorithms(mock_client)
        assert algorithms.client == mock_client

    @pytest.mark.asyncio
    async def test_topological_sort(self, algorithms, mock_client):
        """Test topological sort algorithm."""
        result = QueryResult(records=[
            {'node_id': 'A', 'in_degree': 0, 'predecessors': []},
            {'node_id': 'B', 'in_degree': 1, 'predecessors': ['A']},
            {'node_id': 'C', 'in_degree': 1, 'predecessors': ['A']},
            {'node_id': 'D', 'in_degree': 2, 'predecessors': ['B', 'C']}
        ])
        mock_client.execute_query.return_value = result

        topo_order = await algorithms.topological_sort()

        # A should come first (no dependencies)
        assert topo_order[0] == 'A'
        # D should come last (depends on B and C)
        assert topo_order[-1] == 'D'
        assert len(topo_order) == 4

    @pytest.mark.asyncio
    async def test_topological_sort_with_cycle(self, algorithms, mock_client):
        """Test topological sort with cycle detection."""
        result = QueryResult(records=[
            {'node_id': 'A', 'in_degree': 1, 'predecessors': ['B']},
            {'node_id': 'B', 'in_degree': 1, 'predecessors': ['A']}
        ])
        mock_client.execute_query.return_value = result

        with pytest.raises(GraphOperationError, match="Graph contains cycles"):
            await algorithms.topological_sort()

    @pytest.mark.asyncio
    async def test_topological_sort_with_labels(self, algorithms, mock_client):
        """Test topological sort with label filtering."""
        result = QueryResult(records=[
            {'node_id': 'A', 'in_degree': 0, 'predecessors': []},
            {'node_id': 'B', 'in_degree': 1, 'predecessors': ['A']}
        ])
        mock_client.execute_query.return_value = result

        topo_order = await algorithms.topological_sort(['Task'])

        assert len(topo_order) == 2
        assert 'A' in topo_order
        assert 'B' in topo_order

    @pytest.mark.asyncio
    async def test_find_strongly_connected_components(self, algorithms, mock_client):
        """Test finding strongly connected components."""
        result = QueryResult(records=[
            {'node_id': 'A', 'successors': ['B']},
            {'node_id': 'B', 'successors': ['C']},
            {'node_id': 'C', 'successors': ['A']},
            {'node_id': 'D', 'successors': ['E']},
            {'node_id': 'E', 'successors': []}
        ])
        mock_client.execute_query.return_value = result

        components = await algorithms.find_strongly_connected_components()

        # Should find at least one component
        assert len(components) >= 1
        # Each component should be a list of node IDs
        for component in components:
            assert isinstance(component, list)
            assert all(isinstance(node_id, str) for node_id in component)

    @pytest.mark.asyncio
    async def test_detect_bridges(self, algorithms, mock_client):
        """Test detecting bridge edges."""
        result = QueryResult(records=[
            {'start_id': 'A', 'end_id': 'B', 'rel_type': 'CONNECTS'},
            {'start_id': 'B', 'end_id': 'C', 'rel_type': 'CONNECTS'},
            {'start_id': 'C', 'end_id': 'D', 'rel_type': 'CONNECTS'},
            {'start_id': 'D', 'end_id': 'E', 'rel_type': 'CONNECTS'}
        ])
        mock_client.execute_query.return_value = result

        bridges = await algorithms.detect_bridges()

        # Should return list of tuples
        assert isinstance(bridges, list)
        for bridge in bridges:
            assert isinstance(bridge, tuple)
            assert len(bridge) == 2

    @pytest.mark.asyncio
    async def test_find_articulation_points(self, algorithms, mock_client):
        """Test finding articulation points."""
        result = QueryResult(records=[
            {'node_a': 'A', 'node_b': 'B'},
            {'node_a': 'B', 'node_b': 'C'},
            {'node_a': 'B', 'node_b': 'D'},
            {'node_a': 'C', 'node_b': 'D'}
        ])
        mock_client.execute_query.return_value = result

        articulation_points = await algorithms.find_articulation_points()

        # Should return list of node IDs
        assert isinstance(articulation_points, list)
        assert all(isinstance(node_id, str) for node_id in articulation_points)

    @pytest.mark.asyncio
    async def test_find_minimum_spanning_tree(self, algorithms, mock_client):
        """Test finding minimum spanning tree."""
        result = QueryResult(records=[
            {'start_id': 'A', 'end_id': 'B', 'weight': 1.0},
            {'start_id': 'B', 'end_id': 'C', 'weight': 2.0},
            {'start_id': 'A', 'end_id': 'C', 'weight': 3.0},
            {'start_id': 'C', 'end_id': 'D', 'weight': 1.5}
        ])
        mock_client.execute_query.return_value = result

        mst_edges = await algorithms.find_minimum_spanning_tree()

        # Should return list of tuples (start_id, end_id, weight)
        assert isinstance(mst_edges, list)
        for edge in mst_edges:
            assert isinstance(edge, tuple)
            assert len(edge) == 3
            assert isinstance(edge[2], (int, float))  # weight

    @pytest.mark.asyncio
    async def test_find_minimum_spanning_tree_custom_property(self, algorithms, mock_client):
        """Test finding MST with custom weight property."""
        result = QueryResult(records=[
            {'start_id': 'A', 'end_id': 'B', 'cost': 5.0},
            {'start_id': 'B', 'end_id': 'C', 'cost': 3.0}
        ])
        mock_client.execute_query.return_value = result

        mst_edges = await algorithms.find_minimum_spanning_tree('cost')

        assert len(mst_edges) <= 2  # At most n-1 edges for n nodes

    @pytest.mark.asyncio
    async def test_detect_negative_cycles(self, algorithms, mock_client):
        """Test detecting negative cycles."""
        nodes_result = QueryResult(records=[
            {'node_id': 'A'},
            {'node_id': 'B'},
            {'node_id': 'C'}
        ])
        edges_result = QueryResult(records=[
            {'start_id': 'A', 'end_id': 'B', 'weight': 1.0},
            {'start_id': 'B', 'end_id': 'C', 'weight': -2.0},
            {'start_id': 'C', 'end_id': 'A', 'weight': 0.5}
        ])
        mock_client.execute_query.side_effect = [nodes_result, edges_result]

        negative_cycles = await algorithms.detect_negative_cycles()

        # Should return list of cycles (each cycle is a list of node IDs)
        assert isinstance(negative_cycles, list)
        for cycle in negative_cycles:
            assert isinstance(cycle, list)
            assert all(isinstance(node_id, str) for node_id in cycle)

    @pytest.mark.asyncio
    async def test_detect_negative_cycles_no_nodes(self, algorithms, mock_client):
        """Test detecting negative cycles with no nodes."""
        empty_result = QueryResult(records=[])
        mock_client.execute_query.return_value = empty_result

        negative_cycles = await algorithms.detect_negative_cycles()

        assert negative_cycles == []

    @pytest.mark.asyncio
    async def test_find_maximum_flow(self, algorithms, mock_client):
        """Test finding maximum flow."""
        result = QueryResult(records=[
            {'start_id': 'S', 'end_id': 'A', 'capacity': 10},
            {'start_id': 'S', 'end_id': 'B', 'capacity': 10},
            {'start_id': 'A', 'end_id': 'T', 'capacity': 10},
            {'start_id': 'B', 'end_id': 'T', 'capacity': 10},
            {'start_id': 'A', 'end_id': 'B', 'capacity': 2}
        ])
        mock_client.execute_query.return_value = result

        flow_result = await algorithms.find_maximum_flow('S', 'T')

        assert 'max_flow' in flow_result
        assert 'flow_paths' in flow_result
        assert 'source' in flow_result
        assert 'sink' in flow_result
        assert flow_result['source'] == 'S'
        assert flow_result['sink'] == 'T'
        assert isinstance(flow_result['max_flow'], (int, float))
        assert isinstance(flow_result['flow_paths'], list)

    @pytest.mark.asyncio
    async def test_find_maximum_flow_validation_error(self, algorithms):
        """Test maximum flow with invalid input."""
        with pytest.raises(ValidationError, match="Source node ID cannot be empty"):
            await algorithms.find_maximum_flow('', 'T')

        with pytest.raises(ValidationError, match="Sink node ID cannot be empty"):
            await algorithms.find_maximum_flow('S', '')

    @pytest.mark.asyncio
    async def test_find_maximum_flow_nodes_not_found(self, algorithms, mock_client):
        """Test maximum flow when source or sink not found."""
        result = QueryResult(records=[
            {'start_id': 'A', 'end_id': 'B', 'capacity': 10}
        ])
        mock_client.execute_query.return_value = result

        with pytest.raises(GraphOperationError, match="Source or sink node not found"):
            await algorithms.find_maximum_flow('S', 'T')

    @pytest.mark.asyncio
    async def test_find_maximum_flow_custom_capacity_property(self, algorithms, mock_client):
        """Test maximum flow with custom capacity property."""
        result = QueryResult(records=[
            {'start_id': 'S', 'end_id': 'T', 'bandwidth': 100}
        ])
        mock_client.execute_query.return_value = result

        flow_result = await algorithms.find_maximum_flow('S', 'T', 'bandwidth')

        assert flow_result['source'] == 'S'
        assert flow_result['sink'] == 'T'

    @pytest.mark.asyncio
    async def test_find_maximum_flow_no_path(self, algorithms, mock_client):
        """Test maximum flow when no path exists."""
        result = QueryResult(records=[
            {'start_id': 'S', 'end_id': 'A', 'capacity': 10},
            {'start_id': 'B', 'end_id': 'T', 'capacity': 10}
            # No path from S to T
        ])
        mock_client.execute_query.return_value = result

        flow_result = await algorithms.find_maximum_flow('S', 'T')

        assert flow_result['max_flow'] == 0
        assert flow_result['flow_paths'] == []
