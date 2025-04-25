@echo off
rem Installation script for MCP project
rem Installs all local packages in development mode

echo Installing local packages in development mode...

rem Check if uv is available
where uv >nul 2>&1
if %ERRORLEVEL% == 0 (
    set INSTALL_CMD=uv pip install -e
    echo Using uv for installation
) else (
    set INSTALL_CMD=pip install -e
    echo Using pip for installation (uv not found)
)

echo Installing mcp_core...
%INSTALL_CMD% ./mcp_core

echo Installing mcp_tools...
%INSTALL_CMD% ./mcp_tools

echo Installing main package...
%INSTALL_CMD% .

echo.
echo Installation complete! You can now run:
echo   - Python scripts directly
echo   - 'python -m server.main' to start the server 