"""Cypher query builder utilities for Neo4j operations."""

from typing import Dict, Any, List, Optional, Union, Tuple
import re
from datetime import datetime


class QueryBuilder:
    """Utility class for building Cypher queries with parameter binding."""

    @staticmethod
    def escape_identifier(identifier: str) -> str:
        """Escape Neo4j identifiers (labels, property names, etc.)."""
        if not identifier:
            raise ValueError("Identifier cannot be empty")

        # Remove any backticks and escape special characters
        escaped = identifier.replace("`", "")

        # If identifier contains special characters, wrap in backticks
        if re.search(r'[^a-zA-Z0-9_]', escaped):
            return f"`{escaped}`"

        return escaped

    @staticmethod
    def format_labels(labels: List[str]) -> str:
        """Format node labels for Cypher queries."""
        if not labels:
            return ""

        escaped_labels = [QueryBuilder.escape_identifier(label) for label in labels]
        return ":" + ":".join(escaped_labels)

    @staticmethod
    def format_properties(properties: Dict[str, Any], param_prefix: str = "props") -> Tuple[str, Dict[str, Any]]:
        """Format properties for Cypher queries with parameter binding.

        Returns:
            Tuple of (cypher_string, parameters_dict)
        """
        if not properties:
            return "", {}

        params = {}
        prop_parts = []

        for i, (key, value) in enumerate(properties.items()):
            param_name = f"{param_prefix}_{i}"
            prop_parts.append(f"{QueryBuilder.escape_identifier(key)}: ${param_name}")
            params[param_name] = value

        return "{" + ", ".join(prop_parts) + "}", params

    @staticmethod
    def create_node_query(labels: List[str], properties: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Build CREATE query for a node.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        labels_str = QueryBuilder.format_labels(labels)
        props_str, params = QueryBuilder.format_properties(properties, "create_props")

        if props_str:
            query = f"CREATE (n{labels_str} {props_str}) RETURN n"
        else:
            query = f"CREATE (n{labels_str}) RETURN n"

        return query, params

    @staticmethod
    def match_node_by_id_query(node_id: str, labels: Optional[List[str]] = None) -> Tuple[str, Dict[str, Any]]:
        """Build MATCH query for a node by ID.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        labels_str = QueryBuilder.format_labels(labels) if labels else ""
        query = f"MATCH (n{labels_str}) WHERE n.id = $node_id RETURN n"
        params = {"node_id": node_id}

        return query, params

    @staticmethod
    def update_node_query(node_id: str, properties: Dict[str, Any], labels: Optional[List[str]] = None) -> Tuple[str, Dict[str, Any]]:
        """Build query to update node properties.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        labels_str = QueryBuilder.format_labels(labels) if labels else ""

        # Build SET clauses for properties
        set_clauses = []
        params = {"node_id": node_id}

        for i, (key, value) in enumerate(properties.items()):
            param_name = f"update_prop_{i}"
            set_clauses.append(f"n.{QueryBuilder.escape_identifier(key)} = ${param_name}")
            params[param_name] = value

        # Add updated_at timestamp
        set_clauses.append("n.updated_at = $updated_at")
        params["updated_at"] = datetime.utcnow().isoformat()

        set_clause = ", ".join(set_clauses)
        query = f"MATCH (n{labels_str}) WHERE n.id = $node_id SET {set_clause} RETURN n"

        return query, params

    @staticmethod
    def delete_node_query(node_id: str, force: bool = False, labels: Optional[List[str]] = None) -> Tuple[str, Dict[str, Any]]:
        """Build query to delete a node.

        Args:
            node_id: Node ID to delete
            force: If True, delete relationships as well (DETACH DELETE)
            labels: Optional labels to match

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        labels_str = QueryBuilder.format_labels(labels) if labels else ""
        delete_clause = "DETACH DELETE n" if force else "DELETE n"

        query = f"MATCH (n{labels_str}) WHERE n.id = $node_id {delete_clause}"
        params = {"node_id": node_id}

        return query, params

    @staticmethod
    def find_nodes_query(
        labels: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to find nodes by criteria.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        labels_str = QueryBuilder.format_labels(labels) if labels else ""
        params = {}

        # Build WHERE clause for properties
        where_clauses = []
        if properties:
            for i, (key, value) in enumerate(properties.items()):
                param_name = f"find_prop_{i}"
                where_clauses.append(f"n.{QueryBuilder.escape_identifier(key)} = ${param_name}")
                params[param_name] = value

        # Build query
        query_parts = [f"MATCH (n{labels_str})"]

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query_parts.append("RETURN n")

        # Add pagination
        if skip is not None:
            query_parts.append(f"SKIP {skip}")
        if limit is not None:
            query_parts.append(f"LIMIT {limit}")

        query = " ".join(query_parts)
        return query, params

    @staticmethod
    def create_relationship_query(
        start_id: str,
        end_id: str,
        rel_type: str,
        properties: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build CREATE query for a relationship.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())
        props_str, props_params = QueryBuilder.format_properties(properties, "rel_props")

        params = {
            "start_id": start_id,
            "end_id": end_id,
            **props_params
        }

        if props_str:
            query = f"""
            MATCH (start), (end)
            WHERE start.id = $start_id AND end.id = $end_id
            CREATE (start)-[r:{rel_type_escaped} {props_str}]->(end)
            RETURN r, start, end
            """
        else:
            query = f"""
            MATCH (start), (end)
            WHERE start.id = $start_id AND end.id = $end_id
            CREATE (start)-[r:{rel_type_escaped}]->(end)
            RETURN r, start, end
            """

        return query.strip(), params

    @staticmethod
    def match_relationship_query(
        start_id: str,
        end_id: str,
        rel_type: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Build MATCH query for a specific relationship.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())

        query = f"""
        MATCH (start)-[r:{rel_type_escaped}]->(end)
        WHERE start.id = $start_id AND end.id = $end_id
        RETURN r, start, end
        """

        params = {
            "start_id": start_id,
            "end_id": end_id
        }

        return query.strip(), params

    @staticmethod
    def update_relationship_query(
        start_id: str,
        end_id: str,
        rel_type: str,
        properties: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to update relationship properties.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())

        # Build SET clauses for properties
        set_clauses = []
        params = {
            "start_id": start_id,
            "end_id": end_id
        }

        for i, (key, value) in enumerate(properties.items()):
            param_name = f"update_rel_prop_{i}"
            set_clauses.append(f"r.{QueryBuilder.escape_identifier(key)} = ${param_name}")
            params[param_name] = value

        set_clause = ", ".join(set_clauses)

        query = f"""
        MATCH (start)-[r:{rel_type_escaped}]->(end)
        WHERE start.id = $start_id AND end.id = $end_id
        SET {set_clause}
        RETURN r, start, end
        """

        return query.strip(), params

    @staticmethod
    def delete_relationship_query(
        start_id: str,
        end_id: str,
        rel_type: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to delete a relationship.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())

        query = f"""
        MATCH (start)-[r:{rel_type_escaped}]->(end)
        WHERE start.id = $start_id AND end.id = $end_id
        DELETE r
        """

        params = {
            "start_id": start_id,
            "end_id": end_id
        }

        return query.strip(), params

    @staticmethod
    def find_relationships_query(
        rel_type: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        start_node_id: Optional[str] = None,
        end_node_id: Optional[str] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to find relationships by criteria.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        # Build relationship pattern
        rel_pattern = "-[r"
        if rel_type:
            rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())
            rel_pattern += f":{rel_type_escaped}"
        rel_pattern += "]->"

        params = {}
        where_clauses = []

        # Add node ID constraints
        if start_node_id:
            where_clauses.append("start.id = $start_node_id")
            params["start_node_id"] = start_node_id

        if end_node_id:
            where_clauses.append("end.id = $end_node_id")
            params["end_node_id"] = end_node_id

        # Add property constraints
        if properties:
            for i, (key, value) in enumerate(properties.items()):
                param_name = f"find_rel_prop_{i}"
                where_clauses.append(f"r.{QueryBuilder.escape_identifier(key)} = ${param_name}")
                params[param_name] = value

        # Build query
        query_parts = [f"MATCH (start){rel_pattern}(end)"]

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query_parts.append("RETURN r, start, end")

        # Add pagination
        if skip is not None:
            query_parts.append(f"SKIP {skip}")
        if limit is not None:
            query_parts.append(f"LIMIT {limit}")

        query = " ".join(query_parts)
        return query, params

    @staticmethod
    def get_node_relationships_query(
        node_id: str,
        direction: str = "BOTH",
        rel_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to get node relationships.

        Args:
            node_id: Node ID
            direction: "INCOMING", "OUTGOING", or "BOTH"
            rel_type: Optional relationship type filter
            limit: Optional result limit

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        params = {"node_id": node_id}

        # Build relationship pattern based on direction
        if direction.upper() == "INCOMING":
            if rel_type:
                rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())
                pattern = f"(other)-[r:{rel_type_escaped}]->(n)"
            else:
                pattern = "(other)-[r]->(n)"
        elif direction.upper() == "OUTGOING":
            if rel_type:
                rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())
                pattern = f"(n)-[r:{rel_type_escaped}]->(other)"
            else:
                pattern = "(n)-[r]->(other)"
        else:  # BOTH
            if rel_type:
                rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())
                pattern = f"(n)-[r:{rel_type_escaped}]-(other)"
            else:
                pattern = "(n)-[r]-(other)"

        query_parts = [
            f"MATCH {pattern}",
            "WHERE n.id = $node_id",
            "RETURN r, n, other"
        ]

        if limit is not None:
            query_parts.append(f"LIMIT {limit}")

        query = " ".join(query_parts)
        return query, params

    @staticmethod
    def find_paths_query(
        start_id: str,
        end_id: str,
        max_depth: int = 5,
        rel_type: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to find paths between nodes.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        params = {
            "start_id": start_id,
            "end_id": end_id
        }

        # Build relationship pattern
        if rel_type:
            rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())
            rel_pattern = f"[r:{rel_type_escaped}*1..{max_depth}]"
        else:
            rel_pattern = f"[r*1..{max_depth}]"

        query = f"""
        MATCH path = (start)-{rel_pattern}-(end)
        WHERE start.id = $start_id AND end.id = $end_id
        RETURN path, length(path) as path_length
        ORDER BY path_length
        """

        return query.strip(), params

    @staticmethod
    def detect_cycles_query(max_depth: int = 10) -> Tuple[str, Dict[str, Any]]:
        """Build query to detect cycles in the graph.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        query = f"""
        MATCH path = (n)-[*1..{max_depth}]-(n)
        WHERE length(path) > 2
        RETURN path, length(path) as cycle_length, n
        ORDER BY cycle_length
        """

        return query.strip(), {}

    @staticmethod
    def node_exists_query(node_id: str, labels: Optional[List[str]] = None) -> Tuple[str, Dict[str, Any]]:
        """Build query to check if a node exists.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        labels_str = QueryBuilder.format_labels(labels) if labels else ""

        query = f"""
        MATCH (n{labels_str})
        WHERE n.id = $node_id
        RETURN count(n) > 0 as exists
        """

        params = {"node_id": node_id}
        return query.strip(), params

    @staticmethod
    def relationship_exists_query(
        start_id: str,
        end_id: str,
        rel_type: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Build query to check if a relationship exists.

        Returns:
            Tuple of (query_string, parameters_dict)
        """
        rel_type_escaped = QueryBuilder.escape_identifier(rel_type.upper())

        query = f"""
        MATCH (start)-[r:{rel_type_escaped}]->(end)
        WHERE start.id = $start_id AND end.id = $end_id
        RETURN count(r) > 0 as exists
        """

        params = {
            "start_id": start_id,
            "end_id": end_id
        }

        return query.strip(), params
