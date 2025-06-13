"""Tests for GraphAnalytics class."""

import pytest
from unittest.mock import AsyncMock, patch

from ..analytics import GraphAnalytics
from ..models import QueryResult
from ..exceptions import GraphOperationError
from ..neo4j_client import Neo4jClient


class TestGraphAnalytics:
    """Test GraphAnalytics class."""

    @pytest.fixture
    def mock_client(self):
        """Create mock Neo4j client."""
        client = AsyncMock(spec=Neo4jClient)
        return client

    @pytest.fixture
    def analytics(self, mock_client):
        """Create GraphAnalytics instance with mock client."""
        return GraphAnalytics(mock_client)

    @pytest.mark.asyncio
    async def test_init(self, mock_client):
        """Test GraphAnalytics initialization."""
        analytics = GraphAnalytics(mock_client)
        assert analytics.client == mock_client

    @pytest.mark.asyncio
    async def test_calculate_clustering_coefficient_specific_node(self, analytics, mock_client):
        """Test calculating clustering coefficient for a specific node."""
        result = QueryResult(
            records=[
                {
                    'node_id': 'A',
                    'clustering_coefficient': 0.5
                }
            ]
        )
        mock_client.execute_query.return_value = result

        coefficient = await analytics.calculate_clustering_coefficient('A')

        assert coefficient['node_id'] == 'A'
        assert coefficient['clustering_coefficient'] == 0.5

    @pytest.mark.asyncio
    async def test_calculate_clustering_coefficient_specific_node_not_found(self, analytics, mock_client):
        """Test calculating clustering coefficient for non-existent node."""
        result = QueryResult(records=[])
        mock_client.execute_query.return_value = result

        coefficient = await analytics.calculate_clustering_coefficient('NONEXISTENT')

        assert coefficient['node_id'] == 'NONEXISTENT'
        assert coefficient['clustering_coefficient'] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_clustering_coefficient_entire_graph(self, analytics, mock_client):
        """Test calculating average clustering coefficient for entire graph."""
        result = QueryResult(
            records=[
                {
                    'average_clustering_coefficient': 0.3,
                    'nodes_with_clustering': 10
                }
            ]
        )
        mock_client.execute_query.return_value = result

        coefficient = await analytics.calculate_clustering_coefficient()

        assert coefficient['average_clustering_coefficient'] == 0.3
        assert coefficient['nodes_with_clustering'] == 10

    @pytest.mark.asyncio
    async def test_find_central_nodes_degree(self, analytics, mock_client):
        """Test finding central nodes by degree centrality."""
        result = QueryResult(
            records=[
                {'node_id': 'A', 'centrality_score': 5},
                {'node_id': 'B', 'centrality_score': 3},
                {'node_id': 'C', 'centrality_score': 2}
            ]
        )
        mock_client.execute_query.return_value = result

        central_nodes = await analytics.find_central_nodes('degree', limit=3)

        assert len(central_nodes) == 3
        assert central_nodes[0] == ('A', 5.0)
        assert central_nodes[1] == ('B', 3.0)
        assert central_nodes[2] == ('C', 2.0)

    @pytest.mark.asyncio
    async def test_find_central_nodes_closeness(self, analytics, mock_client):
        """Test finding central nodes by closeness centrality."""
        result = QueryResult(
            records=[
                {'node_id': 'A', 'centrality_score': 0.8},
                {'node_id': 'B', 'centrality_score': 0.6}
            ]
        )
        mock_client.execute_query.return_value = result

        central_nodes = await analytics.find_central_nodes('closeness', limit=2)

        assert len(central_nodes) == 2
        assert central_nodes[0] == ('A', 0.8)
        assert central_nodes[1] == ('B', 0.6)

    @pytest.mark.asyncio
    async def test_find_central_nodes_betweenness(self, analytics, mock_client):
        """Test finding central nodes by betweenness centrality."""
        result = QueryResult(
            records=[
                {'node_id': 'A', 'centrality_score': 10},
                {'node_id': 'B', 'centrality_score': 5}
            ]
        )
        mock_client.execute_query.return_value = result

        central_nodes = await analytics.find_central_nodes('betweenness', limit=2)

        assert len(central_nodes) == 2
        assert central_nodes[0] == ('A', 10.0)
        assert central_nodes[1] == ('B', 5.0)

    @pytest.mark.asyncio
    async def test_find_central_nodes_pagerank(self, analytics, mock_client):
        """Test finding central nodes by PageRank."""
        result = QueryResult(
            records=[
                {'node_id': 'A', 'centrality_score': 3},
                {'node_id': 'B', 'centrality_score': 1}
            ]
        )
        mock_client.execute_query.return_value = result

        central_nodes = await analytics.find_central_nodes('pagerank', limit=2)

        assert len(central_nodes) == 2
        assert central_nodes[0] == ('A', 3.0)
        assert central_nodes[1] == ('B', 1.0)

    @pytest.mark.asyncio
    async def test_find_central_nodes_unknown_type(self, analytics):
        """Test finding central nodes with unknown centrality type."""
        with pytest.raises(GraphOperationError, match="Unknown centrality type"):
            await analytics.find_central_nodes('unknown')

    @pytest.mark.asyncio
    async def test_analyze_graph_diameter(self, analytics, mock_client):
        """Test analyzing graph diameter."""
        result = QueryResult(
            records=[
                {
                    'diameter': 4,
                    'radius': 2,
                    'average_path_length': 2.5,
                    'path_count': 100
                }
            ]
        )
        mock_client.execute_query.return_value = result

        diameter_info = await analytics.analyze_graph_diameter()

        assert diameter_info['diameter'] == 4
        assert diameter_info['radius'] == 2
        assert diameter_info['average_path_length'] == 2.5
        assert diameter_info['analyzed_paths'] == 100

    @pytest.mark.asyncio
    async def test_analyze_graph_diameter_no_paths(self, analytics, mock_client):
        """Test analyzing graph diameter with no paths."""
        result = QueryResult(records=[])
        mock_client.execute_query.return_value = result

        diameter_info = await analytics.analyze_graph_diameter()

        assert diameter_info['diameter'] == 0
        assert diameter_info['radius'] == 0
        assert diameter_info['average_path_length'] == 0.0
        assert diameter_info['analyzed_paths'] == 0

    @pytest.mark.asyncio
    async def test_detect_communities_louvain(self, analytics, mock_client):
        """Test detecting communities with Louvain algorithm."""
        result = QueryResult(
            records=[
                {'communityId': 1, 'community_nodes': ['A', 'B', 'C']},
                {'communityId': 2, 'community_nodes': ['D', 'E']}
            ]
        )
        mock_client.execute_query.return_value = result

        communities = await analytics.detect_communities('louvain')

        assert len(communities) == 2
        assert ['A', 'B', 'C'] in communities
        assert ['D', 'E'] in communities

    @pytest.mark.asyncio
    async def test_detect_communities_label_propagation(self, analytics, mock_client):
        """Test detecting communities with label propagation."""
        result = QueryResult(
            records=[
                {'communityId': 1, 'community_nodes': ['A', 'B']},
                {'communityId': 2, 'community_nodes': ['C', 'D']}
            ]
        )
        mock_client.execute_query.return_value = result

        communities = await analytics.detect_communities('label_propagation')

        assert len(communities) == 2
        assert ['A', 'B'] in communities
        assert ['C', 'D'] in communities

    @pytest.mark.asyncio
    async def test_detect_communities_fallback(self, analytics, mock_client):
        """Test detecting communities with fallback method."""
        from ..exceptions import Neo4jQueryError

        # First call fails (GDS not available)
        mock_client.execute_query.side_effect = [
            Neo4jQueryError("GDS not available"),
            QueryResult(records=[
                {'node_id': 'A', 'connected_nodes': ['B', 'C']},
                {'node_id': 'B', 'connected_nodes': ['A', 'C']},
                {'node_id': 'C', 'connected_nodes': ['A', 'B']},
                {'node_id': 'D', 'connected_nodes': ['E']},
                {'node_id': 'E', 'connected_nodes': ['D']}
            ])
        ]

        communities = await analytics.detect_communities('louvain')

        # Should use basic community detection
        assert len(communities) >= 1

    @pytest.mark.asyncio
    async def test_detect_communities_unknown_algorithm(self, analytics):
        """Test detecting communities with unknown algorithm."""
        with pytest.raises(GraphOperationError, match="Unknown community detection algorithm"):
            await analytics.detect_communities('unknown')

    @pytest.mark.asyncio
    async def test_basic_community_detection(self, analytics, mock_client):
        """Test basic community detection method."""
        result = QueryResult(
            records=[
                {'node_id': 'A', 'connected_nodes': ['B', 'C']},
                {'node_id': 'B', 'connected_nodes': ['A', 'C']},
                {'node_id': 'C', 'connected_nodes': ['A', 'B']},
                {'node_id': 'D', 'connected_nodes': ['E']},
                {'node_id': 'E', 'connected_nodes': ['D']}
            ]
        )
        mock_client.execute_query.return_value = result

        communities = await analytics._basic_community_detection()

        # Should find communities based on connection similarity
        assert len(communities) >= 1

    @pytest.mark.asyncio
    async def test_calculate_graph_metrics(self, analytics, mock_client):
        """Test calculating comprehensive graph metrics."""
        # Mock basic stats query
        stats_result = QueryResult(
            records=[
                {
                    'node_count': 10,
                    'relationship_count': 20,
                    'avg_degree': 4.0
                }
            ]
        )

        # Mock clustering coefficient
        clustering_result = {
            'average_clustering_coefficient': 0.3,
            'nodes_with_clustering': 8
        }

        # Mock diameter analysis
        diameter_result = {
            'diameter': 4,
            'radius': 2,
            'average_path_length': 2.5
        }

        mock_client.execute_query.return_value = stats_result

        with patch.object(analytics, 'calculate_clustering_coefficient') as mock_clustering:
            with patch.object(analytics, 'analyze_graph_diameter') as mock_diameter:
                mock_clustering.return_value = clustering_result
                mock_diameter.return_value = diameter_result

                metrics = await analytics.calculate_graph_metrics()

                assert metrics['node_count'] == 10
                assert metrics['relationship_count'] == 20
                assert metrics['average_degree'] == 4.0
                assert metrics['density'] == 20 / (10 * 9)  # 20 / 90
                assert metrics['clustering_coefficient'] == 0.3
                assert metrics['diameter'] == 4
                assert metrics['radius'] == 2
                assert metrics['average_path_length'] == 2.5

    @pytest.mark.asyncio
    async def test_analyze_node_importance(self, analytics, mock_client):
        """Test analyzing node importance."""
        # Mock degree query
        degree_result = QueryResult(
            records=[
                {
                    'degree': 5,
                    'out_degree': 3,
                    'in_degree': 2
                }
            ]
        )

        # Mock neighbors query
        neighbors_result = QueryResult(
            records=[
                {
                    'neighbors_depth_1': 3,
                    'neighbors_depth_2': 8,
                    'neighbors_depth_3': 15
                }
            ]
        )

        # Mock clustering coefficient
        clustering_result = {
            'clustering_coefficient': 0.4
        }

        mock_client.execute_query.side_effect = [degree_result, neighbors_result]

        with patch.object(analytics, 'calculate_clustering_coefficient') as mock_clustering:
            mock_clustering.return_value = clustering_result

            importance = await analytics.analyze_node_importance('A')

            assert importance['node_id'] == 'A'
            assert importance['degree'] == 5
            assert importance['out_degree'] == 3
            assert importance['in_degree'] == 2
            assert importance['clustering_coefficient'] == 0.4
            assert importance['neighbors_depth_1'] == 3
            assert importance['neighbors_depth_2'] == 8
            assert importance['neighbors_depth_3'] == 15

    @pytest.mark.asyncio
    async def test_analyze_node_importance_no_data(self, analytics, mock_client):
        """Test analyzing node importance with no data."""
        empty_result = QueryResult(records=[])
        clustering_result = {'clustering_coefficient': 0.0}

        mock_client.execute_query.return_value = empty_result

        with patch.object(analytics, 'calculate_clustering_coefficient') as mock_clustering:
            mock_clustering.return_value = clustering_result

            importance = await analytics.analyze_node_importance('NONEXISTENT')

            assert importance['node_id'] == 'NONEXISTENT'
            assert importance['clustering_coefficient'] == 0.0
