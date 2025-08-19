# MCP Server Manager

A Tauri-based desktop application for managing MCP (Model Context Protocol) servers.

## Features

- **Start/Stop/Restart MCP Server**: Easy control over server lifecycle
- **Working Directory Configuration**: Configure custom working directory for server execution
- **Port Configuration**: Configure which port the server runs on
- **Real-time Status**: Live updates on server status including PID and port
- **Logs Monitoring**: View application logs and server management actions
- **Persistent Settings**: Configuration is automatically saved to disk and restored between sessions
- **Cross-platform**: Works on Windows, macOS, and Linux

## Prerequisites

- Node.js (version 16 or higher)
- Rust (latest stable version)
- Python 3.x with uv package manager (for running the MCP server)

## Installation

1. Navigate to the server-ui directory:
   ```bash
   cd server-ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Development

To run the application in development mode:

```bash
npm run tauri dev
```

This will start both the Vite development server for the frontend and the Tauri application.

## Building

To build the application for production:

```bash
npm run tauri build
```

This will create platform-specific installers in the `src-tauri/target/release/bundle/` directory.

## Usage

1. **Configuration**:
   - Set a custom working directory or leave empty for auto-detection
   - Configure the default port (8000 by default)
   - Click "Save Configuration" to persist settings to disk (automatically restored on restart)
2. **Starting the Server**: Click the "Start Server" button to launch the MCP server
3. **Stopping the Server**: Click "Stop Server" to gracefully shutdown the running server
4. **Restarting**: Click "Restart Server" to stop and start the server with current settings
5. **Monitoring**: Watch the status indicator and logs for real-time updates

## Architecture

- **Frontend**: TypeScript + Vite + HTML/CSS
- **Backend**: Rust with Tauri framework
- **Server Management**: Process spawning and monitoring via Rust std::process
- **IPC**: Tauri's built-in invoke system for frontend-backend communication

## Commands

The application exposes the following Tauri commands:

- `start_server(port?: number)`: Start the MCP server on specified port
- `stop_server()`: Stop the running MCP server
- `restart_server(port?: number)`: Restart the server with new settings
- `get_server_status()`: Get current server status
- `get_server_config()`: Get current server configuration
- `set_server_config(config: ServerConfig)`: Save server configuration
- `browse_working_directory()`: Get suggested working directory

## Configuration

The application manages MCP servers by running `uv run server/main.py --port <PORT>` from either:
- The configured working directory (if set in the UI)
- The parent directory of the UI application (auto-detect mode)

Ensure your MCP server project has a `server/main.py` file and is properly configured with uv in the working directory.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
