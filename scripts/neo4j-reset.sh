#!/bin/bash

# Neo4j Database Reset Script
# This script resets the development database to a clean state with sample data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to wait for Neo4j to be ready
wait_for_neo4j() {
    local container_name=$1
    local username=$2
    local password=$3
    local max_attempts=30
    local attempt=1

    print_status "Waiting for $container_name to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if docker exec $container_name cypher-shell -u $username -p $password "RETURN 1" >/dev/null 2>&1; then
            print_success "$container_name is ready!"
            return 0
        fi

        print_status "Attempt $attempt/$max_attempts - waiting for $container_name..."
        sleep 3
        attempt=$((attempt + 1))
    done

    print_error "$container_name failed to start within expected time"
    return 1
}

main() {
    print_status "Resetting Neo4j Development Database..."

    # Check if we're in the right directory
    if [ ! -f "pyproject.toml" ]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi

    # Check if Docker Compose file exists
    if [ ! -f "docker/neo4j/docker-compose.yml" ]; then
        print_error "Docker Compose file not found. Please run neo4j-dev-setup.sh first."
        exit 1
    fi

    # Ask for confirmation
    echo -e "${YELLOW}WARNING: This will delete all data in the development database!${NC}"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Reset cancelled."
        exit 0
    fi

    # Stop the development container
    print_status "Stopping Neo4j development container..."
    docker-compose -f docker/neo4j/docker-compose.yml stop neo4j

    # Remove the data volume
    print_status "Removing development database data..."
    docker volume rm mcp_neo4j_data 2>/dev/null || true

    # Start the container again
    print_status "Starting Neo4j development container..."
    docker-compose -f docker/neo4j/docker-compose.yml up -d neo4j

    # Wait for Neo4j to be ready
    wait_for_neo4j "mcp-neo4j-dev" "neo4j" "development"

    # Re-run initialization scripts
    print_status "Re-initializing database with sample data..."

    # Run index creation script
    if [ -f "docker/neo4j/init-scripts/01-create-indexes.cypher" ]; then
        print_status "Creating indexes and constraints..."
        docker exec -i mcp-neo4j-dev cypher-shell -u neo4j -p development < docker/neo4j/init-scripts/01-create-indexes.cypher
        print_success "Indexes and constraints created"
    fi

    # Run sample data script
    if [ -f "docker/neo4j/init-scripts/02-sample-data.cypher" ]; then
        print_status "Loading sample data..."
        docker exec -i mcp-neo4j-dev cypher-shell -u neo4j -p development < docker/neo4j/init-scripts/02-sample-data.cypher
        print_success "Sample data loaded"
    fi

    # Verify the reset
    print_status "Verifying database reset..."
    node_count=$(docker exec mcp-neo4j-dev cypher-shell -u neo4j -p development "MATCH (n) RETURN count(n) as count" --format plain | tail -n 1 | tr -d '"')

    if [ "$node_count" -gt 0 ]; then
        print_success "Database reset complete! Node count: $node_count"
    else
        print_warning "Database appears to be empty. This might indicate an issue with sample data loading."
    fi

    echo ""
    print_success "Neo4j Development Database Reset Complete!"
    echo ""
    echo "You can now access the fresh database at:"
    echo "  Web UI: http://localhost:7474"
    echo "  Username: neo4j"
    echo "  Password: development"
    echo ""
}

main "$@"
