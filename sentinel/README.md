# Sentinel

A powerful MCP (Message Control Protocol) server that combines local command execution capabilities with semantic search functionality using vector databases.

## Features

- MCP Protocol Server Implementation
- Local Command Execution
- Vector Database Integration for Semantic Search
- Configurable Settings

## Prerequisites

- Python 3.8+
- pip package manager
- Virtual environment (recommended)

## Installation

1. Clone the repository
2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Configure the server in `config/config.yaml`
2. Start the server:
```bash
python src/main.py
```

## Project Structure

```
sentinel/
├── src/          # Main source code
├── tests/        # Test files
├── docs/         # Documentation
└── config/       # Configuration files
```

## License

MIT License 