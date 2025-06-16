#!/bin/bash

# Neo4j Development Environment Setup Script
# This script sets up the complete Neo4j development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
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
        sleep 5
        attempt=$((attempt + 1))
    done

    print_error "$container_name failed to start within expected time"
    return 1
}

# Main setup function
main() {
    print_status "Starting Neo4j Development Environment Setup..."

    # Check prerequisites
    print_status "Checking prerequisites..."

    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    if ! command_exists uv; then
        print_error "uv is not installed. Please install uv first."
        exit 1
    fi

    print_success "All prerequisites are installed"

    # Check if we're in the right directory
    if [ ! -f "pyproject.toml" ]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi

    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating .env file..."
        cat > .env << EOF
# Neo4j Development Environment Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=development
NEO4J_DATABASE=neo4j

# Neo4j Test Environment Configuration
NEO4J_TEST_URI=bolt://localhost:7688
NEO4J_TEST_USERNAME=neo4j
NEO4J_TEST_PASSWORD=test
NEO4J_TEST_DATABASE=neo4j

# Debug Configuration
NEO4J_DEBUG=true
PYTHONPATH=\${PYTHONPATH}:\$(pwd)
EOF
        print_success ".env file created"
    else
        print_warning ".env file already exists, skipping creation"
    fi

    # Stop any existing containers
    print_status "Stopping any existing Neo4j containers..."
    docker-compose -f docker/neo4j/docker-compose.yml down --remove-orphans || true

    # Start Neo4j services
    print_status "Starting Neo4j development and test databases..."
    docker-compose -f docker/neo4j/docker-compose.yml up -d

    # Wait for services to be ready
    wait_for_neo4j "mcp-neo4j-dev" "neo4j" "development"
    wait_for_neo4j "mcp-neo4j-test" "neo4j" "test"

    # Install Python dependencies
    print_status "Installing Python dependencies..."
    uv sync

    # Test the connection
    print_status "Testing Neo4j connections..."

    # Test development database
    if uv run python -c "
from utils.graph_interface.neo4j_client import Neo4jClient
from utils.graph_interface.config import Neo4jConfig
config = Neo4jConfig(uri='bolt://localhost:7687', username='neo4j', password='development')
client = Neo4jClient(config)
result = client.execute_query('RETURN 1 as test')
print('Development database connection: OK')
client.close()
" 2>/dev/null; then
        print_success "Development database connection successful"
    else
        print_error "Failed to connect to development database"
        exit 1
    fi

    # Test test database
    if uv run python -c "
from utils.graph_interface.neo4j_client import Neo4jClient
from utils.graph_interface.config import Neo4jConfig
config = Neo4jConfig(uri='bolt://localhost:7688', username='neo4j', password='test')
client = Neo4jClient(config)
result = client.execute_query('RETURN 1 as test')
print('Test database connection: OK')
client.close()
" 2>/dev/null; then
        print_success "Test database connection successful"
    else
        print_error "Failed to connect to test database"
        exit 1
    fi

    # Run a quick test to ensure everything is working
    print_status "Running basic functionality test..."
    if uv run pytest utils/graph_interface/tests/test_neo4j_client.py::test_connection -v >/dev/null 2>&1; then
        print_success "Basic functionality test passed"
    else
        print_warning "Basic functionality test failed - this might be expected if tests haven't been set up yet"
    fi

    # Display status
    print_status "Displaying container status..."
    docker-compose -f docker/neo4j/docker-compose.yml ps

    # Success message
    echo ""
    print_success "Neo4j Development Environment Setup Complete!"
    echo ""
    echo "Access Information:"
    echo "  Development Database Web UI: http://localhost:7474"
    echo "    Username: neo4j"
    echo "    Password: development"
    echo ""
    echo "  Test Database Web UI: http://localhost:7475"
    echo "    Username: neo4j"
    echo "    Password: test"
    echo ""
    echo "Next Steps:"
    echo "  1. Open the Neo4j Browser at http://localhost:7474"
    echo "  2. Run: uv run pytest utils/graph_interface/tests/"
    echo "  3. Check out the documentation: docs/development/neo4j-setup.md"
    echo ""
    echo "Useful Commands:"
    echo "  - Reset database: ./scripts/neo4j-reset.sh"
    echo "  - Backup database: ./scripts/neo4j-backup.sh"
    echo "  - Stop services: docker-compose -f docker/neo4j/docker-compose.yml down"
    echo ""
}

# Run main function
main "$@"
