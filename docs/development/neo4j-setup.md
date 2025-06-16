# Neo4j Development Environment Setup

This guide will help you set up a complete Neo4j development environment for the MCP Graph Interface.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ with uv package manager
- Git

## Quick Start

1. **Clone the repository and navigate to the project directory:**
   ```bash
   git clone <repository-url>
   cd mcp
   ```

2. **Start the Neo4j development environment:**
   ```bash
   ./scripts/neo4j-dev-setup.sh
   ```

3. **Verify the setup:**
   ```bash
   # Check if Neo4j is running
   docker-compose -f docker/neo4j/docker-compose.yml ps

   # Test connection
   uv run python -c "from utils.graph_interface.neo4j_client import Neo4jClient; client = Neo4jClient(); print('Connection successful!')"
   ```

## Manual Setup

### 1. Environment Configuration

Create a `.env` file in the project root with the following configuration:

```bash
# Development environment
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=devpassword
NEO4J_DATABASE=neo4j

# Test environment
NEO4J_TEST_URI=bolt://localhost:7688
NEO4J_TEST_USERNAME=neo4j
NEO4J_TEST_PASSWORD=testpassword
NEO4J_TEST_DATABASE=neo4j

# Optional: Enable debug logging
NEO4J_DEBUG=true
```

### 2. Start Neo4j Services

```bash
# Start both development and test databases
docker-compose -f docker/neo4j/docker-compose.yml up -d

# Or start only development database
docker-compose -f docker/neo4j/docker-compose.yml up -d neo4j

# Or start only test database
docker-compose -f docker/neo4j/docker-compose.yml up -d neo4j-test
```

### 3. Verify Installation

```bash
# Check container status
docker-compose -f docker/neo4j/docker-compose.yml ps

# Check logs
docker-compose -f docker/neo4j/docker-compose.yml logs neo4j

# Test connection using cypher-shell
docker exec -it mcp-neo4j-dev cypher-shell -u neo4j -p devpassword
```

## Database Access

### Web Interface

- **Development Database**: http://localhost:7474
  - Username: `neo4j`
  - Password: `devpassword`

- **Test Database**: http://localhost:7475
  - Username: `neo4j`
  - Password: `testpassword`

### Programmatic Access

```python
from utils.graph_interface.neo4j_client import Neo4jClient
from utils.graph_interface.config import Neo4jConfig

# Development database
config = Neo4jConfig()
client = Neo4jClient(config)

# Test database
test_config = Neo4jConfig(
    uri="bolt://localhost:7688",
    username="neo4j",
    password="testpassword"
)
test_client = Neo4jClient(test_config)
```

## Development Workflow

### 1. Database Management

```bash
# Reset development database
./scripts/neo4j-reset.sh

# Backup development data
./scripts/neo4j-backup.sh

# Restore from backup
./scripts/neo4j-restore.sh backup-file.dump
```

### 2. Running Tests

```bash
# Run all graph interface tests
uv run pytest utils/graph_interface/tests/

# Run specific test file
uv run pytest utils/graph_interface/tests/test_neo4j_client.py

# Run tests with coverage
uv run pytest utils/graph_interface/tests/ --cov=utils.graph_interface
```

### 3. Development Tools

```bash
# Start interactive Python shell with graph interface loaded
uv run python -c "
from utils.graph_interface import *
client = Neo4jClient()
print('Graph interface loaded. Use client to interact with Neo4j.')
"

# Run graph visualization tool
uv run python utils/graph_interface/dev_tools/visualizer.py

# Run query debugging utility
uv run python utils/graph_interface/dev_tools/query_debugger.py
```

## Sample Data

The development database comes pre-loaded with sample data including:

- **Users**: 3 sample users with different roles
- **Projects**: 2 sample projects with different statuses
- **Tasks**: 5 sample tasks with various dependencies
- **Resources**: 2 sample resources with allocations

### Exploring Sample Data

```cypher
// View all nodes and relationships
MATCH (n) RETURN n LIMIT 25;

// View task dependencies
MATCH (t1:Task)-[r:DEPENDS_ON]->(t2:Task)
RETURN t1.name, r.dependency_type, t2.name;

// View project assignments
MATCH (u:User)-[r:MANAGES]->(p:Project)
RETURN u.full_name, p.name, r.role;
```

## Performance Monitoring

### 1. Query Performance

```cypher
// Enable query logging
CALL dbms.setConfigValue('dbms.logs.query.enabled', 'true');

// View slow queries
CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Queries')
YIELD attributes
RETURN attributes.RunningQueries;
```

### 2. Memory Usage

```cypher
// Check memory usage
CALL dbms.queryJmx('java.lang:type=Memory')
YIELD attributes
RETURN attributes.HeapMemoryUsage, attributes.NonHeapMemoryUsage;
```

### 3. Index Usage

```cypher
// List all indexes
SHOW INDEXES;

// Check index usage
CALL db.indexes()
YIELD name, state, populationPercent
RETURN name, state, populationPercent;
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Check if containers are running
   docker-compose -f docker/neo4j/docker-compose.yml ps

   # Check container logs
   docker-compose -f docker/neo4j/docker-compose.yml logs neo4j

   # Restart services
   docker-compose -f docker/neo4j/docker-compose.yml restart
   ```

2. **Authentication Failed**
   ```bash
   # Reset password
   docker exec -it mcp-neo4j-dev neo4j-admin set-initial-password devpassword
   ```

3. **Out of Memory**
   ```bash
   # Increase memory limits in docker-compose.yml
   NEO4J_dbms_memory_heap_max_size: 2G
   NEO4J_dbms_memory_pagecache_size: 1G
   ```

4. **Port Conflicts**
   ```bash
   # Check what's using the ports
   lsof -i :7474
   lsof -i :7687

   # Change ports in docker-compose.yml if needed
   ```

### Debug Mode

Enable debug logging by setting environment variables:

```bash
export NEO4J_DEBUG=true
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Log Files

- **Neo4j Logs**: Available in Docker volumes or via `docker logs`
- **Application Logs**: Check `server.log` and `server_debug.log`
- **Test Logs**: Generated during test runs in `pytest` output

## Best Practices

### 1. Development Workflow

- Always use the test database for automated tests
- Use the development database for manual testing and exploration
- Reset databases regularly to ensure clean state
- Backup important development data before major changes

### 2. Query Development

- Use `EXPLAIN` and `PROFILE` to optimize queries
- Create indexes for frequently queried properties
- Use parameters in queries to prevent injection attacks
- Limit result sets during development to avoid memory issues

### 3. Testing

- Write tests that are independent and can run in any order
- Use test fixtures for consistent test data
- Clean up test data after each test
- Test both success and failure scenarios

### 4. Performance

- Monitor query performance regularly
- Use appropriate data types for properties
- Consider denormalization for frequently accessed data
- Use batch operations for large data imports

## Next Steps

1. Read the [Graph Modeling Guide](graph-modeling-guide.md)
2. Explore the [API Documentation](../api/graph-interface.md)
3. Check out [Usage Examples](../api/examples.md)
4. Review [Performance Tuning](performance-tuning.md) guidelines

## Support

If you encounter issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the logs for error messages
3. Search existing GitHub issues
4. Create a new issue with detailed information about the problem
