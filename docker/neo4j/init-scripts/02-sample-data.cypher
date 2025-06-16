// Neo4j Graph Interface - Sample Data Creation Script
// This script creates sample data for development and testing

// Clear existing data (for development environment only)
MATCH (n) DETACH DELETE n;

// Create sample users
CREATE (u1:User {
    id: 'user-001',
    username: 'alice_dev',
    email: 'alice@example.com',
    full_name: 'Alice Developer',
    active: true,
    created_at: datetime(),
    role: 'developer'
});

CREATE (u2:User {
    id: 'user-002',
    username: 'bob_pm',
    email: 'bob@example.com',
    full_name: 'Bob Project Manager',
    active: true,
    created_at: datetime(),
    role: 'project_manager'
});

CREATE (u3:User {
    id: 'user-003',
    username: 'charlie_qa',
    email: 'charlie@example.com',
    full_name: 'Charlie QA Engineer',
    active: true,
    created_at: datetime(),
    role: 'qa_engineer'
});

// Create sample projects
CREATE (p1:Project {
    id: 'project-001',
    name: 'Neo4j Integration',
    description: 'Implement Neo4j graph interface for the MCP system',
    status: 'active',
    priority: 'high',
    created_at: datetime(),
    updated_at: datetime(),
    start_date: date(),
    estimated_completion: date() + duration('P30D')
});

CREATE (p2:Project {
    id: 'project-002',
    name: 'API Documentation',
    description: 'Create comprehensive API documentation',
    status: 'planning',
    priority: 'medium',
    created_at: datetime(),
    updated_at: datetime(),
    start_date: date() + duration('P7D'),
    estimated_completion: date() + duration('P21D')
});

// Create sample tasks
CREATE (t1:Task {
    id: 'task-001',
    name: 'Setup Neo4j Database',
    description: 'Configure Neo4j database with proper indexes and constraints',
    status: 'completed',
    priority: 'high',
    created_at: datetime() - duration('P5D'),
    updated_at: datetime() - duration('P1D'),
    estimated_hours: 8,
    actual_hours: 6,
    project_id: 'project-001'
});

CREATE (t2:Task {
    id: 'task-002',
    name: 'Implement Node Manager',
    description: 'Create node management functionality for graph operations',
    status: 'in_progress',
    priority: 'high',
    created_at: datetime() - duration('P3D'),
    updated_at: datetime(),
    estimated_hours: 16,
    actual_hours: 8,
    project_id: 'project-001'
});

CREATE (t3:Task {
    id: 'task-003',
    name: 'Create Relationship Manager',
    description: 'Implement relationship management for graph connections',
    status: 'pending',
    priority: 'high',
    created_at: datetime() - duration('P2D'),
    updated_at: datetime() - duration('P2D'),
    estimated_hours: 12,
    actual_hours: 0,
    project_id: 'project-001'
});

CREATE (t4:Task {
    id: 'task-004',
    name: 'Write Unit Tests',
    description: 'Create comprehensive unit tests for graph interface',
    status: 'pending',
    priority: 'medium',
    created_at: datetime() - duration('P1D'),
    updated_at: datetime() - duration('P1D'),
    estimated_hours: 20,
    actual_hours: 0,
    project_id: 'project-001'
});

CREATE (t5:Task {
    id: 'task-005',
    name: 'API Documentation Draft',
    description: 'Create initial draft of API documentation',
    status: 'not_started',
    priority: 'medium',
    created_at: datetime(),
    updated_at: datetime(),
    estimated_hours: 12,
    actual_hours: 0,
    project_id: 'project-002'
});

// Create sample resources
CREATE (r1:Resource {
    id: 'resource-001',
    name: 'Development Server',
    type: 'server',
    available: true,
    capacity: 100,
    current_usage: 45,
    location: 'datacenter-1'
});

CREATE (r2:Resource {
    id: 'resource-002',
    name: 'Testing Environment',
    type: 'environment',
    available: true,
    capacity: 50,
    current_usage: 20,
    location: 'cloud-1'
});

// Create relationships
MATCH (u1:User {id: 'user-001'}), (t1:Task {id: 'task-001'})
CREATE (u1)-[:ASSIGNED_TO {role: 'developer', assigned_at: datetime() - duration('P5D')}]->(t1);

MATCH (u1:User {id: 'user-001'}), (t2:Task {id: 'task-002'})
CREATE (u1)-[:ASSIGNED_TO {role: 'developer', assigned_at: datetime() - duration('P3D')}]->(t2);

MATCH (u2:User {id: 'user-002'}), (p1:Project {id: 'project-001'})
CREATE (u2)-[:MANAGES {role: 'project_manager', assigned_at: datetime() - duration('P10D')}]->(p1);

MATCH (u2:User {id: 'user-002'}), (p2:Project {id: 'project-002'})
CREATE (u2)-[:MANAGES {role: 'project_manager', assigned_at: datetime() - duration('P5D')}]->(p2);

MATCH (t1:Task {id: 'task-001'}), (p1:Project {id: 'project-001'})
CREATE (t1)-[:BELONGS_TO {created_at: datetime() - duration('P5D')}]->(p1);

MATCH (t2:Task {id: 'task-002'}), (p1:Project {id: 'project-001'})
CREATE (t2)-[:BELONGS_TO {created_at: datetime() - duration('P3D')}]->(p1);

MATCH (t3:Task {id: 'task-003'}), (p1:Project {id: 'project-001'})
CREATE (t3)-[:BELONGS_TO {created_at: datetime() - duration('P2D')}]->(p1);

MATCH (t4:Task {id: 'task-004'}), (p1:Project {id: 'project-001'})
CREATE (t4)-[:BELONGS_TO {created_at: datetime() - duration('P1D')}]->(p1);

MATCH (t5:Task {id: 'task-005'}), (p2:Project {id: 'project-002'})
CREATE (t5)-[:BELONGS_TO {created_at: datetime()}]->(p2);

// Create task dependencies
MATCH (t2:Task {id: 'task-002'}), (t1:Task {id: 'task-001'})
CREATE (t2)-[:DEPENDS_ON {dependency_type: 'hard', created_at: datetime() - duration('P3D')}]->(t1);

MATCH (t3:Task {id: 'task-003'}), (t2:Task {id: 'task-002'})
CREATE (t3)-[:DEPENDS_ON {dependency_type: 'soft', created_at: datetime() - duration('P2D')}]->(t2);

MATCH (t4:Task {id: 'task-004'}), (t2:Task {id: 'task-002'})
CREATE (t4)-[:DEPENDS_ON {dependency_type: 'hard', created_at: datetime() - duration('P1D')}]->(t2);

MATCH (t4:Task {id: 'task-004'}), (t3:Task {id: 'task-003'})
CREATE (t4)-[:DEPENDS_ON {dependency_type: 'hard', created_at: datetime() - duration('P1D')}]->(t3);

// Create resource allocations
MATCH (r1:Resource {id: 'resource-001'}), (p1:Project {id: 'project-001'})
CREATE (p1)-[:USES {allocation_percentage: 45, allocated_at: datetime() - duration('P10D')}]->(r1);

MATCH (r2:Resource {id: 'resource-002'}), (p1:Project {id: 'project-001'})
CREATE (p1)-[:USES {allocation_percentage: 20, allocated_at: datetime() - duration('P8D')}]->(r2);

// Log completion
RETURN 'Sample data created successfully' AS result,
       count{(n:User)} AS users_created,
       count{(n:Project)} AS projects_created,
       count{(n:Task)} AS tasks_created,
       count{(n:Resource)} AS resources_created;
