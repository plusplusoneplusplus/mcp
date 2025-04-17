#!/bin/bash

# Default parameter values
environment="dev"
version="1.0.0"
force=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment)
            environment="$2"
            if [[ ! "$environment" =~ ^(dev|staging|prod)$ ]]; then
                echo "Error: environment must be one of: dev, staging, prod"
                exit 1
            fi
            shift 2
            ;;
        --version)
            version="$2"
            shift 2
            ;;
        --force)
            if [[ "$2" == "true" ]]; then
                force=true
            fi
            shift 2
            ;;
        --timeout)
            # Just consume but ignore timeout parameter
            shift 2
            ;;
        *)
            echo "Unknown parameter: $1"
            shift
            ;;
    esac
done

# Print deployment information
echo "Starting deployment process..."
echo "Environment: $environment"
echo "Version: $version"
echo "Force deployment: $force"

# Example deployment logic
if $force; then
    echo "Force flag is set - proceeding with deployment even if version exists"
fi

# Simulate deployment steps
echo
echo "Deployment steps:"
echo "1. Validating environment configuration..."
echo "2. Checking version compatibility..."
echo "3. Preparing deployment package..."
echo "4. Deploying to $environment environment..."
echo "5. Running post-deployment checks..."

echo
echo "Deployment completed successfully!" 