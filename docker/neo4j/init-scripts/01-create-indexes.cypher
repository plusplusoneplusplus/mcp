// Neo4j Graph Interface - Index and Constraint Creation Script
// This script creates the necessary indexes and constraints for optimal performance

// Create constraints for unique identifiers
CREATE CONSTRAINT task_id_unique IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT resource_id_unique IF NOT EXISTS FOR (r:Resource) REQUIRE r.id IS UNIQUE;

// Create indexes for commonly queried properties
CREATE INDEX task_status_index IF NOT EXISTS FOR (t:Task) ON (t.status);
CREATE INDEX task_priority_index IF NOT EXISTS FOR (t:Task) ON (t.priority);
CREATE INDEX task_created_at_index IF NOT EXISTS FOR (t:Task) ON (t.created_at);
CREATE INDEX task_updated_at_index IF NOT EXISTS FOR (t:Task) ON (t.updated_at);
CREATE INDEX task_name_index IF NOT EXISTS FOR (t:Task) ON (t.name);

CREATE INDEX project_status_index IF NOT EXISTS FOR (p:Project) ON (p.status);
CREATE INDEX project_created_at_index IF NOT EXISTS FOR (p:Project) ON (p.created_at);
CREATE INDEX project_name_index IF NOT EXISTS FOR (p:Project) ON (p.name);

CREATE INDEX user_email_index IF NOT EXISTS FOR (u:User) ON (u.email);
CREATE INDEX user_username_index IF NOT EXISTS FOR (u:User) ON (u.username);
CREATE INDEX user_active_index IF NOT EXISTS FOR (u:User) ON (u.active);

CREATE INDEX resource_type_index IF NOT EXISTS FOR (r:Resource) ON (r.type);
CREATE INDEX resource_available_index IF NOT EXISTS FOR (r:Resource) ON (r.available);

// Create composite indexes for complex queries
CREATE INDEX task_status_priority_index IF NOT EXISTS FOR (t:Task) ON (t.status, t.priority);
CREATE INDEX task_project_status_index IF NOT EXISTS FOR (t:Task) ON (t.project_id, t.status);

// Create full-text search indexes
CALL db.index.fulltext.createNodeIndex('taskFullText', ['Task'], ['name', 'description']) YIELD name;
CALL db.index.fulltext.createNodeIndex('projectFullText', ['Project'], ['name', 'description']) YIELD name;
CALL db.index.fulltext.createNodeIndex('userFullText', ['User'], ['username', 'email', 'full_name']) YIELD name;

// Create relationship indexes for performance
CREATE INDEX depends_on_type_index IF NOT EXISTS FOR ()-[r:DEPENDS_ON]-() ON (r.dependency_type);
CREATE INDEX assigned_to_role_index IF NOT EXISTS FOR ()-[r:ASSIGNED_TO]-() ON (r.role);
CREATE INDEX belongs_to_created_at_index IF NOT EXISTS FOR ()-[r:BELONGS_TO]-() ON (r.created_at);

// Log completion
RETURN 'Indexes and constraints created successfully' AS result;
