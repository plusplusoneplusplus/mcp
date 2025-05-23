# Installation script for MCP project
# Installs all local packages in development mode

# Exit on error
$ErrorActionPreference = "Stop"

Write-Host "Installing local packages in development mode..."

# Check if uv is available
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $INSTALL_CMD = "uv pip install -e"
    Write-Host "Using uv for installation"
}
else {
    $INSTALL_CMD = "pip install -e"
    Write-Host "Using pip for installation (uv not found)"
}

# Install the local packages
Write-Host "Installing mcp_core..."
Invoke-Expression "$INSTALL_CMD ./mcp_core"

Write-Host "Installing mcp_tools..."
Invoke-Expression "$INSTALL_CMD ./mcp_tools"

Write-Host "Installing utils..."
Invoke-Expression "$INSTALL_CMD ./utils"

Write-Host "Installing main package..."
Invoke-Expression "$INSTALL_CMD ."

# Install Playwright browsers
Write-Host "Installing Playwright browsers..."
playwright install
playwright install msedge

Write-Host ""
Write-Host "Installation complete! You can now run:"
Write-Host "  - Python scripts directly"
Write-Host "  - 'uv run server/main.py' to start the server" 
