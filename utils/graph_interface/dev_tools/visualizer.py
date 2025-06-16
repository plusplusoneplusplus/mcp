"""
Graph visualization utility for Neo4j Graph Interface development.

This module provides tools for visualizing graph data and relationships
for development and debugging purposes.
"""

import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..neo4j_client import Neo4jClient
from ..config import Neo4jConfig


@dataclass
class GraphNode:
    """Represents a node in the graph visualization."""
    id: str
    labels: List[str]
    properties: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'labels': self.labels,
            'properties': self.properties
        }


@dataclass
class GraphRelationship:
    """Represents a relationship in the graph visualization."""
    id: str
    type: str
    start_node_id: str
    end_node_id: str
    properties: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'start_node_id': self.start_node_id,
            'end_node_id': self.end_node_id,
            'properties': self.properties
        }


@dataclass
class GraphVisualization:
    """Contains the complete graph visualization data."""
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'nodes': [node.to_dict() for node in self.nodes],
            'relationships': [rel.to_dict() for rel in self.relationships],
            'metadata': self.metadata
        }


class GraphVisualizer:
    """
    Visualize Neo4j graph data for development purposes.

    This class provides utilities for:
    - Extracting graph data from Neo4j
    - Converting to visualization formats
    - Generating graph statistics
    - Creating subgraph views
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        """
        Initialize the graph visualizer.

        Args:
            client: Neo4j client instance. If None, creates a new one.
        """
        self.client = client or Neo4jClient()

    def visualize_full_graph(self, limit: int = 100) -> GraphVisualization:
        """
        Create a visualization of the entire graph.

        Args:
            limit: Maximum number of nodes to include

        Returns:
            GraphVisualization object
        """
        # Get nodes
        nodes_query = f"""
        MATCH (n)
        RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
        LIMIT {limit}
        """

        nodes_result = self.client.execute_query(nodes_query)
        nodes = []
        node_ids = set()

        for record in nodes_result:
            node_id = str(record['node_id'])
            node_ids.add(node_id)
            nodes.append(GraphNode(
                id=node_id,
                labels=record['labels'],
                properties=record['properties']
            ))

        # Get relationships between the selected nodes
        relationships_query = f"""
        MATCH (n)-[r]->(m)
        WHERE id(n) IN {list(node_ids)} AND id(m) IN {list(node_ids)}
        RETURN id(r) as rel_id, type(r) as rel_type,
               id(n) as start_id, id(m) as end_id,
               properties(r) as properties
        """

        relationships_result = self.client.execute_query(relationships_query)
        relationships = []

        for record in relationships_result:
            relationships.append(GraphRelationship(
                id=str(record['rel_id']),
                type=record['rel_type'],
                start_node_id=str(record['start_id']),
                end_node_id=str(record['end_id']),
                properties=record['properties']
            ))

        metadata = {
            'total_nodes': len(nodes),
            'total_relationships': len(relationships),
            'node_labels': self._get_node_label_counts(nodes),
            'relationship_types': self._get_relationship_type_counts(relationships),
            'generated_at': datetime.now().isoformat()
        }

        return GraphVisualization(nodes, relationships, metadata)

    def visualize_subgraph(
        self,
        center_node_id: str,
        depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> GraphVisualization:
        """
        Create a visualization of a subgraph around a center node.

        Args:
            center_node_id: ID of the center node
            depth: How many hops to include
            relationship_types: Filter by relationship types

        Returns:
            GraphVisualization object
        """
        # Build relationship type filter
        rel_filter = ""
        if relationship_types:
            rel_types = "|".join(relationship_types)
            rel_filter = f":{rel_types}"

        # Get subgraph
        subgraph_query = f"""
        MATCH path = (center)-[{rel_filter}*1..{depth}]-(connected)
        WHERE id(center) = {center_node_id}
        WITH nodes(path) as path_nodes, relationships(path) as path_rels
        UNWIND path_nodes as n
        WITH collect(DISTINCT n) as all_nodes, path_rels
        UNWIND path_rels as r
        WITH all_nodes, collect(DISTINCT r) as all_rels
        UNWIND all_nodes as node
        WITH all_rels, collect({{
            id: id(node),
            labels: labels(node),
            properties: properties(node)
        }}) as nodes
        UNWIND all_rels as rel
        RETURN nodes,
               collect({{
                   id: id(rel),
                   type: type(rel),
                   start_id: id(startNode(rel)),
                   end_id: id(endNode(rel)),
                   properties: properties(rel)
               }}) as relationships
        """

        result = self.client.execute_query(subgraph_query)

        if not result:
            return GraphVisualization([], [], {
                'message': f'No subgraph found for node {center_node_id}',
                'generated_at': datetime.now().isoformat()
            })

        record = result[0]

        # Convert to GraphNode objects
        nodes = []
        for node_data in record['nodes']:
            nodes.append(GraphNode(
                id=str(node_data['id']),
                labels=node_data['labels'],
                properties=node_data['properties']
            ))

        # Convert to GraphRelationship objects
        relationships = []
        for rel_data in record['relationships']:
            relationships.append(GraphRelationship(
                id=str(rel_data['id']),
                type=rel_data['type'],
                start_node_id=str(rel_data['start_id']),
                end_node_id=str(rel_data['end_id']),
                properties=rel_data['properties']
            ))

        metadata = {
            'center_node_id': center_node_id,
            'depth': depth,
            'relationship_types_filter': relationship_types,
            'total_nodes': len(nodes),
            'total_relationships': len(relationships),
            'node_labels': self._get_node_label_counts(nodes),
            'relationship_types': self._get_relationship_type_counts(relationships),
            'generated_at': datetime.now().isoformat()
        }

        return GraphVisualization(nodes, relationships, metadata)

    def visualize_by_labels(self, labels: List[str], limit: int = 50) -> GraphVisualization:
        """
        Create a visualization filtered by node labels.

        Args:
            labels: List of node labels to include
            limit: Maximum number of nodes

        Returns:
            GraphVisualization object
        """
        # Build label filter
        label_conditions = []
        for label in labels:
            label_conditions.append(f"n:{label}")
        label_filter = " OR ".join(label_conditions)

        # Get nodes with specified labels
        nodes_query = f"""
        MATCH (n)
        WHERE {label_filter}
        RETURN id(n) as node_id, labels(n) as labels, properties(n) as properties
        LIMIT {limit}
        """

        nodes_result = self.client.execute_query(nodes_query)
        nodes = []
        node_ids = set()

        for record in nodes_result:
            node_id = str(record['node_id'])
            node_ids.add(node_id)
            nodes.append(GraphNode(
                id=node_id,
                labels=record['labels'],
                properties=record['properties']
            ))

        # Get relationships between these nodes
        if node_ids:
            relationships_query = f"""
            MATCH (n)-[r]->(m)
            WHERE id(n) IN {list(node_ids)} AND id(m) IN {list(node_ids)}
            RETURN id(r) as rel_id, type(r) as rel_type,
                   id(n) as start_id, id(m) as end_id,
                   properties(r) as properties
            """

            relationships_result = self.client.execute_query(relationships_query)
            relationships = []

            for record in relationships_result:
                relationships.append(GraphRelationship(
                    id=str(record['rel_id']),
                    type=record['rel_type'],
                    start_node_id=str(record['start_id']),
                    end_node_id=str(record['end_id']),
                    properties=record['properties']
                ))
        else:
            relationships = []

        metadata = {
            'label_filter': labels,
            'total_nodes': len(nodes),
            'total_relationships': len(relationships),
            'node_labels': self._get_node_label_counts(nodes),
            'relationship_types': self._get_relationship_type_counts(relationships),
            'generated_at': datetime.now().isoformat()
        }

        return GraphVisualization(nodes, relationships, metadata)

    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the graph.

        Returns:
            Dictionary with graph statistics
        """
        stats_query = """
        CALL {
            MATCH (n) RETURN count(n) as node_count, collect(DISTINCT labels(n)) as all_labels
        }
        CALL {
            MATCH ()-[r]->() RETURN count(r) as rel_count, collect(DISTINCT type(r)) as all_rel_types
        }
        CALL {
            MATCH (n)
            WITH labels(n) as node_labels
            UNWIND node_labels as label
            RETURN label, count(*) as label_count
            ORDER BY label_count DESC
        }
        CALL {
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(*) as type_count
            ORDER BY type_count DESC
        }
        RETURN node_count, rel_count, all_labels, all_rel_types,
               collect({label: label, count: label_count}) as label_stats,
               collect({type: rel_type, count: type_count}) as rel_type_stats
        """

        result = self.client.execute_query(stats_query)

        if result:
            record = result[0]
            return {
                'total_nodes': record['node_count'],
                'total_relationships': record['rel_count'],
                'unique_labels': len([label for labels in record['all_labels'] for label in labels]),
                'unique_relationship_types': len(record['all_rel_types']),
                'label_distribution': record['label_stats'],
                'relationship_type_distribution': record['rel_type_stats'],
                'generated_at': datetime.now().isoformat()
            }

        return {'error': 'Could not retrieve graph statistics'}

    def export_to_json(self, visualization: GraphVisualization, filename: str):
        """
        Export visualization to JSON file.

        Args:
            visualization: GraphVisualization to export
            filename: Output filename
        """
        with open(filename, 'w') as f:
            json.dump(visualization.to_dict(), f, indent=2, default=str)

        print(f"Exported visualization to {filename}")
        print(f"Nodes: {len(visualization.nodes)}, Relationships: {len(visualization.relationships)}")

    def export_to_cytoscape(self, visualization: GraphVisualization, filename: str):
        """
        Export visualization to Cytoscape.js format.

        Args:
            visualization: GraphVisualization to export
            filename: Output filename
        """
        cytoscape_data = {
            'elements': {
                'nodes': [],
                'edges': []
            }
        }

        # Convert nodes
        for node in visualization.nodes:
            cytoscape_data['elements']['nodes'].append({
                'data': {
                    'id': node.id,
                    'label': ', '.join(node.labels),
                    'properties': node.properties
                }
            })

        # Convert relationships
        for rel in visualization.relationships:
            cytoscape_data['elements']['edges'].append({
                'data': {
                    'id': rel.id,
                    'source': rel.start_node_id,
                    'target': rel.end_node_id,
                    'label': rel.type,
                    'properties': rel.properties
                }
            })

        with open(filename, 'w') as f:
            json.dump(cytoscape_data, f, indent=2, default=str)

        print(f"Exported Cytoscape.js format to {filename}")

    def export_to_d3(self, visualization: GraphVisualization, filename: str):
        """
        Export visualization to D3.js format.

        Args:
            visualization: GraphVisualization to export
            filename: Output filename
        """
        d3_data = {
            'nodes': [],
            'links': []
        }

        # Convert nodes
        for node in visualization.nodes:
            d3_data['nodes'].append({
                'id': node.id,
                'group': node.labels[0] if node.labels else 'Unknown',
                'labels': node.labels,
                'properties': node.properties
            })

        # Convert relationships
        for rel in visualization.relationships:
            d3_data['links'].append({
                'source': rel.start_node_id,
                'target': rel.end_node_id,
                'type': rel.type,
                'properties': rel.properties
            })

        with open(filename, 'w') as f:
            json.dump(d3_data, f, indent=2, default=str)

        print(f"Exported D3.js format to {filename}")

    def print_visualization_summary(self, visualization: GraphVisualization):
        """
        Print a summary of the visualization.

        Args:
            visualization: GraphVisualization to summarize
        """
        print("\nGraph Visualization Summary")
        print("=" * 40)
        print(f"Nodes: {len(visualization.nodes)}")
        print(f"Relationships: {len(visualization.relationships)}")

        if visualization.metadata.get('node_labels'):
            print("\nNode Labels:")
            for label, count in visualization.metadata['node_labels'].items():
                print(f"  {label}: {count}")

        if visualization.metadata.get('relationship_types'):
            print("\nRelationship Types:")
            for rel_type, count in visualization.metadata['relationship_types'].items():
                print(f"  {rel_type}: {count}")

        print(f"\nGenerated: {visualization.metadata.get('generated_at', 'Unknown')}")

    def _get_node_label_counts(self, nodes: List[GraphNode]) -> Dict[str, int]:
        """Get counts of each node label."""
        label_counts = {}
        for node in nodes:
            for label in node.labels:
                label_counts[label] = label_counts.get(label, 0) + 1
        return label_counts

    def _get_relationship_type_counts(self, relationships: List[GraphRelationship]) -> Dict[str, int]:
        """Get counts of each relationship type."""
        type_counts = {}
        for rel in relationships:
            type_counts[rel.type] = type_counts.get(rel.type, 0) + 1
        return type_counts


def main():
    """Main function for running the visualizer interactively."""
    visualizer = GraphVisualizer()

    print("Neo4j Graph Visualizer")
    print("Type 'help' for available commands, 'quit' to exit")

    while True:
        try:
            command = input("\nvisualizer> ").strip()

            if command.lower() in ['quit', 'exit']:
                break
            elif command.lower() == 'help':
                print_help()
            elif command.lower() == 'stats':
                stats = visualizer.get_graph_statistics()
                print(json.dumps(stats, indent=2, default=str))
            elif command.lower().startswith('full'):
                parts = command.split()
                limit = int(parts[1]) if len(parts) > 1 else 100
                viz = visualizer.visualize_full_graph(limit)
                visualizer.print_visualization_summary(viz)
            elif command.lower().startswith('subgraph'):
                parts = command.split()
                if len(parts) < 2:
                    print("Usage: subgraph <node_id> [depth]")
                    continue
                node_id = parts[1]
                depth = int(parts[2]) if len(parts) > 2 else 2
                viz = visualizer.visualize_subgraph(node_id, depth)
                visualizer.print_visualization_summary(viz)
            elif command.lower().startswith('labels'):
                parts = command.split()
                if len(parts) < 2:
                    print("Usage: labels <label1> [label2] ...")
                    continue
                labels = parts[1:]
                viz = visualizer.visualize_by_labels(labels)
                visualizer.print_visualization_summary(viz)
            else:
                print("Unknown command. Type 'help' for available commands.")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


def print_help():
    """Print help information."""
    print("""
Available commands:
  full [limit]              - Visualize full graph (default limit: 100)
  subgraph <id> [depth]     - Visualize subgraph around node (default depth: 2)
  labels <label1> [label2]  - Visualize nodes with specific labels
  stats                     - Show graph statistics
  help                      - Show this help
  quit/exit                 - Exit the visualizer
    """)


if __name__ == "__main__":
    main()
