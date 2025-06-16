#!/bin/bash

# Neo4j Database Backup Script
# This script creates a backup of the development database

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

# Function to show usage
show_usage() {
    echo "Usage: $0 [backup_name]"
    echo ""
    echo "Creates a backup of the Neo4j development database."
    echo ""
    echo "Arguments:"
    echo "  backup_name    Optional name for the backup file (default: neo4j-backup-TIMESTAMP)"
    echo ""
    echo "Examples:"
    echo "  $0                           # Creates backup with timestamp"
    echo "  $0 before-major-changes      # Creates backup with custom name"
    echo ""
}

main() {
    # Parse arguments
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_usage
        exit 0
    fi

    # Set backup name
    if [ -n "$1" ]; then
        backup_name="$1"
    else
        backup_name="neo4j-backup-$(date +%Y%m%d-%H%M%S)"
    fi

    print_status "Creating Neo4j Development Database Backup: $backup_name"

    # Check if we're in the right directory
    if [ ! -f "pyproject.toml" ]; then
        print_error "Please run this script from the project root directory"
        exit 1
    fi

    # Check if Neo4j container is running
    if ! docker ps | grep -q "mcp-neo4j-dev"; then
        print_error "Neo4j development container is not running. Please start it first with:"
        print_error "  docker-compose -f docker/neo4j/docker-compose.yml up -d neo4j"
        exit 1
    fi

    # Create backups directory if it doesn't exist
    mkdir -p backups/neo4j

    # Create backup using neo4j-admin dump
    print_status "Creating database dump..."

    # Stop the database temporarily for consistent backup
    print_status "Stopping database for consistent backup..."
    docker exec mcp-neo4j-dev neo4j stop

    # Create the dump
    backup_file="backups/neo4j/${backup_name}.dump"
    docker exec mcp-neo4j-dev neo4j-admin database dump neo4j --to-path=/tmp/

    # Copy the dump file from container to host
    docker cp mcp-neo4j-dev:/tmp/neo4j.dump "$backup_file"

    # Restart the database
    print_status "Restarting database..."
    docker exec mcp-neo4j-dev neo4j start

    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 10

    # Verify backup was created
    if [ -f "$backup_file" ]; then
        backup_size=$(du -h "$backup_file" | cut -f1)
        print_success "Backup created successfully!"
        print_success "File: $backup_file"
        print_success "Size: $backup_size"
    else
        print_error "Backup file was not created"
        exit 1
    fi

    # Create metadata file
    metadata_file="backups/neo4j/${backup_name}.metadata"
    cat > "$metadata_file" << EOF
# Neo4j Backup Metadata
Backup Name: $backup_name
Created: $(date)
Database: neo4j (development)
Container: mcp-neo4j-dev
Backup File: $backup_file
Size: $backup_size

# Restore Instructions:
# 1. Stop the Neo4j container:
#    docker-compose -f docker/neo4j/docker-compose.yml stop neo4j
# 2. Remove the existing data volume:
#    docker volume rm mcp_neo4j_data
# 3. Start the container:
#    docker-compose -f docker/neo4j/docker-compose.yml up -d neo4j
# 4. Wait for it to be ready, then restore:
#    ./scripts/neo4j-restore.sh $backup_file
EOF

    print_success "Metadata file created: $metadata_file"

    # List all backups
    echo ""
    print_status "Available backups:"
    ls -lh backups/neo4j/*.dump 2>/dev/null || print_warning "No backup files found"

    echo ""
    print_success "Backup Complete!"
    echo ""
    echo "To restore this backup later, run:"
    echo "  ./scripts/neo4j-restore.sh $backup_file"
    echo ""
}

main "$@"
