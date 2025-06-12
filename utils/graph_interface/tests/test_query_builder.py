"""Tests for QueryBuilder utility class."""

import pytest
from datetime import datetime
from utils.graph_interface.query_builder import QueryBuilder


class TestQueryBuilder:
    """Test cases for QueryBuilder utility class."""

    def test_escape_identifier_simple(self):
        """Test escaping simple identifiers."""
        assert QueryBuilder.escape_identifier("simple") == "simple"
        assert QueryBuilder.escape_identifier("with_underscore") == "with_underscore"
        assert QueryBuilder.escape_identifier("with123numbers") == "with123numbers"

    def test_escape_identifier_special_chars(self):
        """Test escaping identifiers with special characters."""
        assert QueryBuilder.escape_identifier("with-dash") == "`with-dash`"
        assert QueryBuilder.escape_identifier("with space") == "`with space`"
        assert QueryBuilder.escape_identifier("with.dot") == "`with.dot`"

    def test_escape_identifier_empty(self):
        """Test escaping empty identifier raises error."""
        with pytest.raises(ValueError, match="Identifier cannot be empty"):
            QueryBuilder.escape_identifier("")

    def test_format_labels_empty(self):
        """Test formatting empty labels."""
        assert QueryBuilder.format_labels([]) == ""

    def test_format_labels_single(self):
        """Test formatting single label."""
        assert QueryBuilder.format_labels(["Person"]) == ":Person"

    def test_format_labels_multiple(self):
        """Test formatting multiple labels."""
        assert QueryBuilder.format_labels(["Person", "Employee"]) == ":Person:Employee"

    def test_format_labels_special_chars(self):
        """Test formatting labels with special characters."""
        assert QueryBuilder.format_labels(["Person-Type"]) == ":`Person-Type`"

    def test_format_properties_empty(self):
        """Test formatting empty properties."""
        props_str, params = QueryBuilder.format_properties({})
        assert props_str == ""
        assert params == {}

    def test_format_properties_single(self):
        """Test formatting single property."""
        props_str, params = QueryBuilder.format_properties({"name": "John"})
        assert props_str == "{name: $props_0}"
        assert params == {"props_0": "John"}

    def test_format_properties_multiple(self):
        """Test formatting multiple properties."""
        props_str, params = QueryBuilder.format_properties({
            "name": "John",
            "age": 30,
            "active": True
        })
        assert "{name: $props_0" in props_str
        assert "age: $props_1" in props_str
        assert "active: $props_2" in props_str
        assert params["props_0"] == "John"
        assert params["props_1"] == 30
        assert params["props_2"] is True

    def test_format_properties_custom_prefix(self):
        """Test formatting properties with custom prefix."""
        props_str, params = QueryBuilder.format_properties(
            {"name": "John"}, "custom"
        )
        assert props_str == "{name: $custom_0}"
        assert params == {"custom_0": "John"}

    def test_create_node_query_simple(self):
        """Test creating simple node query."""
        query, params = QueryBuilder.create_node_query(
            ["Person"], {"name": "John"}
        )
        assert "CREATE (n:Person" in query
        assert "name: $create_props_0" in query
        assert "RETURN n" in query
        assert params["create_props_0"] == "John"

    def test_create_node_query_no_properties(self):
        """Test creating node query without properties."""
        query, params = QueryBuilder.create_node_query(["Person"], {})
        assert query == "CREATE (n:Person) RETURN n"
        assert params == {}

    def test_create_node_query_multiple_labels(self):
        """Test creating node query with multiple labels."""
        query, params = QueryBuilder.create_node_query(
            ["Person", "Employee"], {"name": "John"}
        )
        assert "CREATE (n:Person:Employee" in query

    def test_match_node_by_id_query(self):
        """Test matching node by ID query."""
        query, params = QueryBuilder.match_node_by_id_query("123")
        assert query == "MATCH (n) WHERE n.id = $node_id RETURN n"
        assert params == {"node_id": "123"}

    def test_match_node_by_id_query_with_labels(self):
        """Test matching node by ID with labels."""
        query, params = QueryBuilder.match_node_by_id_query("123", ["Person"])
        assert query == "MATCH (n:Person) WHERE n.id = $node_id RETURN n"
        assert params == {"node_id": "123"}

    def test_update_node_query(self):
        """Test updating node query."""
        query, params = QueryBuilder.update_node_query(
            "123", {"name": "Jane", "age": 25}
        )
        assert "MATCH (n) WHERE n.id = $node_id" in query
        assert "SET" in query
        assert "n.name = $update_prop_0" in query
        assert "n.age = $update_prop_1" in query
        assert "n.updated_at = $updated_at" in query
        assert "RETURN n" in query
        assert params["node_id"] == "123"
        assert params["update_prop_0"] == "Jane"
        assert params["update_prop_1"] == 25
        assert "updated_at" in params

    def test_delete_node_query_simple(self):
        """Test simple delete node query."""
        query, params = QueryBuilder.delete_node_query("123")
        assert query == "MATCH (n) WHERE n.id = $node_id DELETE n"
        assert params == {"node_id": "123"}

    def test_delete_node_query_force(self):
        """Test force delete node query."""
        query, params = QueryBuilder.delete_node_query("123", force=True)
        assert query == "MATCH (n) WHERE n.id = $node_id DETACH DELETE n"
        assert params == {"node_id": "123"}

    def test_find_nodes_query_no_criteria(self):
        """Test finding nodes without criteria."""
        query, params = QueryBuilder.find_nodes_query()
        assert query == "MATCH (n) RETURN n"
        assert params == {}

    def test_find_nodes_query_with_labels(self):
        """Test finding nodes with labels."""
        query, params = QueryBuilder.find_nodes_query(labels=["Person"])
        assert query == "MATCH (n:Person) RETURN n"
        assert params == {}

    def test_find_nodes_query_with_properties(self):
        """Test finding nodes with properties."""
        query, params = QueryBuilder.find_nodes_query(
            properties={"name": "John", "age": 30}
        )
        assert "MATCH (n)" in query
        assert "WHERE" in query
        assert "n.name = $find_prop_0" in query
        assert "n.age = $find_prop_1" in query
        assert "RETURN n" in query
        assert params["find_prop_0"] == "John"
        assert params["find_prop_1"] == 30

    def test_find_nodes_query_with_pagination(self):
        """Test finding nodes with pagination."""
        query, params = QueryBuilder.find_nodes_query(limit=10, skip=5)
        assert "SKIP 5" in query
        assert "LIMIT 10" in query

    def test_create_relationship_query(self):
        """Test creating relationship query."""
        query, params = QueryBuilder.create_relationship_query(
            "start123", "end456", "KNOWS", {"since": "2023"}
        )
        assert "MATCH (start), (end)" in query
        assert "WHERE start.id = $start_id AND end.id = $end_id" in query
        assert "CREATE (start)-[r:KNOWS" in query
        assert "since: $rel_props_0" in query
        assert "]->(end)" in query
        assert "RETURN r, start, end" in query
        assert params["start_id"] == "start123"
        assert params["end_id"] == "end456"
        assert params["rel_props_0"] == "2023"

    def test_create_relationship_query_no_properties(self):
        """Test creating relationship query without properties."""
        query, params = QueryBuilder.create_relationship_query(
            "start123", "end456", "KNOWS", {}
        )
        assert "CREATE (start)-[r:KNOWS]->(end)" in query
        assert "rel_props" not in str(params)

    def test_match_relationship_query(self):
        """Test matching relationship query."""
        query, params = QueryBuilder.match_relationship_query(
            "start123", "end456", "KNOWS"
        )
        assert "MATCH (start)-[r:KNOWS]->(end)" in query
        assert "WHERE start.id = $start_id AND end.id = $end_id" in query
        assert "RETURN r, start, end" in query
        assert params["start_id"] == "start123"
        assert params["end_id"] == "end456"

    def test_update_relationship_query(self):
        """Test updating relationship query."""
        query, params = QueryBuilder.update_relationship_query(
            "start123", "end456", "KNOWS", {"weight": 0.8}
        )
        assert "MATCH (start)-[r:KNOWS]->(end)" in query
        assert "WHERE start.id = $start_id AND end.id = $end_id" in query
        assert "SET r.weight = $update_rel_prop_0" in query
        assert "RETURN r, start, end" in query
        assert params["start_id"] == "start123"
        assert params["end_id"] == "end456"
        assert params["update_rel_prop_0"] == 0.8

    def test_delete_relationship_query(self):
        """Test deleting relationship query."""
        query, params = QueryBuilder.delete_relationship_query(
            "start123", "end456", "KNOWS"
        )
        assert "MATCH (start)-[r:KNOWS]->(end)" in query
        assert "WHERE start.id = $start_id AND end.id = $end_id" in query
        assert "DELETE r" in query
        assert params["start_id"] == "start123"
        assert params["end_id"] == "end456"

    def test_find_relationships_query_no_criteria(self):
        """Test finding relationships without criteria."""
        query, params = QueryBuilder.find_relationships_query()
        assert "MATCH (start)-[r]->(end)" in query
        assert "RETURN r, start, end" in query
        assert params == {}

    def test_find_relationships_query_with_type(self):
        """Test finding relationships with type."""
        query, params = QueryBuilder.find_relationships_query(rel_type="KNOWS")
        assert "MATCH (start)-[r:KNOWS]->(end)" in query

    def test_find_relationships_query_with_node_filters(self):
        """Test finding relationships with node filters."""
        query, params = QueryBuilder.find_relationships_query(
            start_node_id="start123", end_node_id="end456"
        )
        assert "WHERE start.id = $start_node_id AND end.id = $end_node_id" in query
        assert params["start_node_id"] == "start123"
        assert params["end_node_id"] == "end456"

    def test_get_node_relationships_query_both(self):
        """Test getting node relationships in both directions."""
        query, params = QueryBuilder.get_node_relationships_query("123", "BOTH")
        assert "MATCH (n)-[r]-(other)" in query
        assert "WHERE n.id = $node_id" in query
        assert "RETURN r, n, other" in query
        assert params["node_id"] == "123"

    def test_get_node_relationships_query_incoming(self):
        """Test getting incoming node relationships."""
        query, params = QueryBuilder.get_node_relationships_query("123", "INCOMING")
        assert "MATCH (other)-[r]->(n)" in query

    def test_get_node_relationships_query_outgoing(self):
        """Test getting outgoing node relationships."""
        query, params = QueryBuilder.get_node_relationships_query("123", "OUTGOING")
        assert "MATCH (n)-[r]->(other)" in query

    def test_get_node_relationships_query_with_type(self):
        """Test getting node relationships with type filter."""
        query, params = QueryBuilder.get_node_relationships_query(
            "123", "BOTH", "KNOWS"
        )
        assert "MATCH (n)-[r:KNOWS]-(other)" in query

    def test_get_node_relationships_query_with_limit(self):
        """Test getting node relationships with limit."""
        query, params = QueryBuilder.get_node_relationships_query(
            "123", "BOTH", limit=5
        )
        assert "LIMIT 5" in query

    def test_find_paths_query(self):
        """Test finding paths query."""
        query, params = QueryBuilder.find_paths_query("start123", "end456", 3)
        assert "MATCH path = (start)-[r*1..3]-(end)" in query
        assert "WHERE start.id = $start_id AND end.id = $end_id" in query
        assert "RETURN path, length(path) as path_length" in query
        assert "ORDER BY path_length" in query
        assert params["start_id"] == "start123"
        assert params["end_id"] == "end456"

    def test_find_paths_query_with_type(self):
        """Test finding paths query with relationship type."""
        query, params = QueryBuilder.find_paths_query(
            "start123", "end456", 3, "KNOWS"
        )
        assert "MATCH path = (start)-[r:KNOWS*1..3]-(end)" in query

    def test_detect_cycles_query(self):
        """Test detecting cycles query."""
        query, params = QueryBuilder.detect_cycles_query(5)
        assert "MATCH path = (n)-[*1..5]-(n)" in query
        assert "WHERE length(path) > 2" in query
        assert "RETURN path, length(path) as cycle_length, n" in query
        assert "ORDER BY cycle_length" in query
        assert params == {}

    def test_node_exists_query(self):
        """Test node exists query."""
        query, params = QueryBuilder.node_exists_query("123")
        assert "MATCH (n)" in query
        assert "WHERE n.id = $node_id" in query
        assert "RETURN count(n) > 0 as exists" in query
        assert params["node_id"] == "123"

    def test_node_exists_query_with_labels(self):
        """Test node exists query with labels."""
        query, params = QueryBuilder.node_exists_query("123", ["Person"])
        assert "MATCH (n:Person)" in query

    def test_relationship_exists_query(self):
        """Test relationship exists query."""
        query, params = QueryBuilder.relationship_exists_query(
            "start123", "end456", "KNOWS"
        )
        assert "MATCH (start)-[r:KNOWS]->(end)" in query
        assert "WHERE start.id = $start_id AND end.id = $end_id" in query
        assert "RETURN count(r) > 0 as exists" in query
        assert params["start_id"] == "start123"
        assert params["end_id"] == "end456"
