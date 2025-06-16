"""
Sample data fixtures for Neo4j Graph Interface testing.

This module provides sample data that can be used for testing and development
of the graph interface functionality.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any

# Sample Tasks
SAMPLE_TASKS = [
    {
        "id": "task-001",
        "labels": ["Task"],
        "properties": {
            "name": "Setup Database",
            "description": "Configure Neo4j database with proper indexes and constraints",
            "status": "completed",
            "priority": "high",
            "created_at": datetime.now() - timedelta(days=5),
            "updated_at": datetime.now() - timedelta(days=1),
            "estimated_hours": 8,
            "actual_hours": 6,
            "project_id": "project-001"
        }
    },
    {
        "id": "task-002",
        "labels": ["Task"],
        "properties": {
            "name": "Implement Node Manager",
            "description": "Create node management functionality for graph operations",
            "status": "in_progress",
            "priority": "high",
            "created_at": datetime.now() - timedelta(days=3),
            "updated_at": datetime.now(),
            "estimated_hours": 16,
            "actual_hours": 8,
            "project_id": "project-001"
        }
    },
    {
        "id": "task-003",
        "labels": ["Task"],
        "properties": {
            "name": "Create Relationship Manager",
            "description": "Implement relationship management for graph connections",
            "status": "pending",
            "priority": "high",
            "created_at": datetime.now() - timedelta(days=2),
            "updated_at": datetime.now() - timedelta(days=2),
            "estimated_hours": 12,
            "actual_hours": 0,
            "project_id": "project-001"
        }
    },
    {
        "id": "task-004",
        "labels": ["Task"],
        "properties": {
            "name": "Write Unit Tests",
            "description": "Create comprehensive unit tests for graph interface",
            "status": "pending",
            "priority": "medium",
            "created_at": datetime.now() - timedelta(days=1),
            "updated_at": datetime.now() - timedelta(days=1),
            "estimated_hours": 20,
            "actual_hours": 0,
            "project_id": "project-001"
        }
    },
    {
        "id": "task-005",
        "labels": ["Task"],
        "properties": {
            "name": "API Documentation Draft",
            "description": "Create initial draft of API documentation",
            "status": "not_started",
            "priority": "medium",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "estimated_hours": 12,
            "actual_hours": 0,
            "project_id": "project-002"
        }
    }
]

# Sample Projects
SAMPLE_PROJECTS = [
    {
        "id": "project-001",
        "labels": ["Project"],
        "properties": {
            "name": "Neo4j Integration",
            "description": "Implement Neo4j graph interface for the MCP system",
            "status": "active",
            "priority": "high",
            "created_at": datetime.now() - timedelta(days=10),
            "updated_at": datetime.now(),
            "start_date": datetime.now().date(),
            "estimated_completion": datetime.now().date() + timedelta(days=30)
        }
    },
    {
        "id": "project-002",
        "labels": ["Project"],
        "properties": {
            "name": "API Documentation",
            "description": "Create comprehensive API documentation",
            "status": "planning",
            "priority": "medium",
            "created_at": datetime.now() - timedelta(days=5),
            "updated_at": datetime.now(),
            "start_date": datetime.now().date() + timedelta(days=7),
            "estimated_completion": datetime.now().date() + timedelta(days=21)
        }
    }
]

# Sample Users
SAMPLE_USERS = [
    {
        "id": "user-001",
        "labels": ["User"],
        "properties": {
            "username": "alice_dev",
            "email": "alice@example.com",
            "full_name": "Alice Developer",
            "active": True,
            "created_at": datetime.now() - timedelta(days=30),
            "role": "developer"
        }
    },
    {
        "id": "user-002",
        "labels": ["User"],
        "properties": {
            "username": "bob_pm",
            "email": "bob@example.com",
            "full_name": "Bob Project Manager",
            "active": True,
            "created_at": datetime.now() - timedelta(days=25),
            "role": "project_manager"
        }
    },
    {
        "id": "user-003",
        "labels": ["User"],
        "properties": {
            "username": "charlie_qa",
            "email": "charlie@example.com",
            "full_name": "Charlie QA Engineer",
            "active": True,
            "created_at": datetime.now() - timedelta(days=20),
            "role": "qa_engineer"
        }
    }
]

# Sample Resources
SAMPLE_RESOURCES = [
    {
        "id": "resource-001",
        "labels": ["Resource"],
        "properties": {
            "name": "Development Server",
            "type": "server",
            "available": True,
            "capacity": 100,
            "current_usage": 45,
            "location": "datacenter-1"
        }
    },
    {
        "id": "resource-002",
        "labels": ["Resource"],
        "properties": {
            "name": "Testing Environment",
            "type": "environment",
            "available": True,
            "capacity": 50,
            "current_usage": 20,
            "location": "cloud-1"
        }
    }
]

# Sample Dependencies (Relationships)
SAMPLE_DEPENDENCIES = [
    {
        "type": "DEPENDS_ON",
        "start_node_id": "task-002",
        "end_node_id": "task-001",
        "properties": {
            "dependency_type": "hard",
            "created_at": datetime.now() - timedelta(days=3)
        }
    },
    {
        "type": "DEPENDS_ON",
        "start_node_id": "task-003",
        "end_node_id": "task-002",
        "properties": {
            "dependency_type": "soft",
            "created_at": datetime.now() - timedelta(days=2)
        }
    },
    {
        "type": "DEPENDS_ON",
        "start_node_id": "task-004",
        "end_node_id": "task-002",
        "properties": {
            "dependency_type": "hard",
            "created_at": datetime.now() - timedelta(days=1)
        }
    },
    {
        "type": "DEPENDS_ON",
        "start_node_id": "task-004",
        "end_node_id": "task-003",
        "properties": {
            "dependency_type": "hard",
            "created_at": datetime.now() - timedelta(days=1)
        }
    }
]

# Sample Assignments (Relationships)
SAMPLE_ASSIGNMENTS = [
    {
        "type": "ASSIGNED_TO",
        "start_node_id": "user-001",
        "end_node_id": "task-001",
        "properties": {
            "role": "developer",
            "assigned_at": datetime.now() - timedelta(days=5)
        }
    },
    {
        "type": "ASSIGNED_TO",
        "start_node_id": "user-001",
        "end_node_id": "task-002",
        "properties": {
            "role": "developer",
            "assigned_at": datetime.now() - timedelta(days=3)
        }
    },
    {
        "type": "MANAGES",
        "start_node_id": "user-002",
        "end_node_id": "project-001",
        "properties": {
            "role": "project_manager",
            "assigned_at": datetime.now() - timedelta(days=10)
        }
    },
    {
        "type": "MANAGES",
        "start_node_id": "user-002",
        "end_node_id": "project-002",
        "properties": {
            "role": "project_manager",
            "assigned_at": datetime.now() - timedelta(days=5)
        }
    }
]

# Sample Project Memberships (Relationships)
SAMPLE_PROJECT_MEMBERSHIPS = [
    {
        "type": "BELONGS_TO",
        "start_node_id": "task-001",
        "end_node_id": "project-001",
        "properties": {
            "created_at": datetime.now() - timedelta(days=5)
        }
    },
    {
        "type": "BELONGS_TO",
        "start_node_id": "task-002",
        "end_node_id": "project-001",
        "properties": {
            "created_at": datetime.now() - timedelta(days=3)
        }
    },
    {
        "type": "BELONGS_TO",
        "start_node_id": "task-003",
        "end_node_id": "project-001",
        "properties": {
            "created_at": datetime.now() - timedelta(days=2)
        }
    },
    {
        "type": "BELONGS_TO",
        "start_node_id": "task-004",
        "end_node_id": "project-001",
        "properties": {
            "created_at": datetime.now() - timedelta(days=1)
        }
    },
    {
        "type": "BELONGS_TO",
        "start_node_id": "task-005",
        "end_node_id": "project-002",
        "properties": {
            "created_at": datetime.now()
        }
    }
]

# Sample Resource Allocations (Relationships)
SAMPLE_RESOURCE_ALLOCATIONS = [
    {
        "type": "USES",
        "start_node_id": "project-001",
        "end_node_id": "resource-001",
        "properties": {
            "allocation_percentage": 45,
            "allocated_at": datetime.now() - timedelta(days=10)
        }
    },
    {
        "type": "USES",
        "start_node_id": "project-001",
        "end_node_id": "resource-002",
        "properties": {
            "allocation_percentage": 20,
            "allocated_at": datetime.now() - timedelta(days=8)
        }
    }
]

# Combined sample data for easy access
SAMPLE_NODES = SAMPLE_TASKS + SAMPLE_PROJECTS + SAMPLE_USERS + SAMPLE_RESOURCES

SAMPLE_RELATIONSHIPS = (
    SAMPLE_DEPENDENCIES +
    SAMPLE_ASSIGNMENTS +
    SAMPLE_PROJECT_MEMBERSHIPS +
    SAMPLE_RESOURCE_ALLOCATIONS
)

# Helper functions for test data management
def get_sample_data_by_type(node_type: str) -> List[Dict[str, Any]]:
    """Get sample data filtered by node type."""
    type_mapping = {
        "Task": SAMPLE_TASKS,
        "Project": SAMPLE_PROJECTS,
        "User": SAMPLE_USERS,
        "Resource": SAMPLE_RESOURCES
    }
    return type_mapping.get(node_type, [])

def get_sample_relationships_by_type(relationship_type: str) -> List[Dict[str, Any]]:
    """Get sample relationships filtered by relationship type."""
    return [rel for rel in SAMPLE_RELATIONSHIPS if rel["type"] == relationship_type]

def get_node_by_id(node_id: str) -> Dict[str, Any]:
    """Get a specific node by its ID."""
    for node in SAMPLE_NODES:
        if node["id"] == node_id:
            return node
    raise ValueError(f"Node with ID '{node_id}' not found in sample data")

def get_relationships_for_node(node_id: str) -> List[Dict[str, Any]]:
    """Get all relationships involving a specific node."""
    relationships = []
    for rel in SAMPLE_RELATIONSHIPS:
        if rel["start_node_id"] == node_id or rel["end_node_id"] == node_id:
            relationships.append(rel)
    return relationships

# Test data validation
def validate_sample_data():
    """Validate the integrity of sample data."""
    errors = []

    # Check for duplicate node IDs
    node_ids = [node["id"] for node in SAMPLE_NODES]
    if len(node_ids) != len(set(node_ids)):
        errors.append("Duplicate node IDs found in sample data")

    # Check that all relationship references exist
    for rel in SAMPLE_RELATIONSHIPS:
        start_id = rel["start_node_id"]
        end_id = rel["end_node_id"]

        if start_id not in node_ids:
            errors.append(f"Relationship references non-existent start node: {start_id}")

        if end_id not in node_ids:
            errors.append(f"Relationship references non-existent end node: {end_id}")

    if errors:
        raise ValueError("Sample data validation failed:\n" + "\n".join(errors))

    return True

# Validate sample data on import
validate_sample_data()
