#!/bin/bash
# Installation script for MCP project
# Installs all local packages in development mode

set -e  # Exit on error

echo "Installing local packages in development mode..."

# Check if uv is available
if command -v uv &> /dev/null; then
    INSTALL_CMD="uv pip install -e"
    echo "Using uv for installation"
else
    INSTALL_CMD="pip install -e"
    echo "Using pip for installation (uv not found)"
fi

# Install the local packages
echo "Installing mcp_core..."
$INSTALL_CMD ./mcp_core

echo "Installing mcp_tools..."
$INSTALL_CMD ./mcp_tools

echo "Installing utils..."
$INSTALL_CMD ./utils

echo "Installing main package..."
$INSTALL_CMD .

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install
playwright install msedge

echo ""
echo "Installation complete! You can now run:"
echo "  - Python scripts directly"
echo "  - 'python -m server.main' to start the server" 