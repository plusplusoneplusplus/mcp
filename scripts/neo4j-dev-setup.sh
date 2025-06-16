#!/bin/bash

# Neo4j Test Environment Setup Script
# This script sets up the Neo4j test environment

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
    print_status "Starting Neo4j Test Environment Setup..."

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
# Neo4j Test Environment Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=testpassword
NEO4J_DATABASE=neo4j

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

    # Start Neo4j service
    print_status "Starting Neo4j test database..."
    docker-compose -f docker/neo4j/docker-compose.yml up -d

    # Wait for service to be ready
    wait_for_neo4j "mcp-neo4j" "neo4j" "testpassword"

    # Install Python dependencies
    print_status "Installing Python dependencies..."
    uv sync

    # Test the connection
    print_status "Testing Neo4j connection..."

    # Test database
    if uv run python -c "
import asyncio
import sys
import traceback
from utils.graph_interface.neo4j_client import Neo4jClient
from utils.graph_interface.config import Neo4jConfig

async def test_connection():
    try:
        print('DEBUG: Starting connection test for database')

        config = Neo4jConfig()
        config.connection.uri = 'bolt://localhost:7687'
        config.connection.username = 'neo4j'
        config.connection.password_env = 'NEO4J_PASSWORD'

        print(f'DEBUG: Config created - URI: {config.connection.uri}, Username: {config.connection.username}')

        client = Neo4jClient(config)
        print('DEBUG: Neo4j client created')

        try:
            print('DEBUG: Attempting to connect...')
            await client.connect()
            print('DEBUG: Connection successful')

            print('DEBUG: Executing test query...')
            result = await client.execute_query('RETURN 1 as test')
            print(f'DEBUG: Query result: {result.records}')

            print('Database connection: OK')
            return True
        except Exception as e:
            print(f'DEBUG: Connection/query error: {type(e).__name__}: {e}')
            print(f'DEBUG: Traceback: {traceback.format_exc()}')
            return False
        finally:
            print('DEBUG: Disconnecting...')
            await client.disconnect()
            print('DEBUG: Disconnected')
    except Exception as e:
        print(f'DEBUG: Outer exception: {type(e).__name__}: {e}')
        print(f'DEBUG: Traceback: {traceback.format_exc()}')
        return False

import os
print('DEBUG: Setting environment variable NEO4J_PASSWORD=testpassword')
os.environ['NEO4J_PASSWORD'] = 'testpassword'
print('DEBUG: Starting asyncio.run()')
result = asyncio.run(test_connection())
print(f'DEBUG: Final result: {result}')
sys.exit(0 if result else 1)
"; then
        print_success "Database connection successful"
    else
        print_error "Failed to connect to database"
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
    print_success "Neo4j Test Environment Setup Complete!"
    echo ""
    echo "Access Information:"
    echo "  Database Web UI: http://localhost:7474"
    echo "    Username: neo4j"
    echo "    Password: testpassword"
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
