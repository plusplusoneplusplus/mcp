# Technology Stack

## Core Technologies

- **Python 3.11+**: Primary language with type hints and modern async features
- **MCP SDK**: Model Context Protocol Python SDK for AI integration
- **Starlette + Uvicorn**: ASGI web framework and server for HTTP/SSE endpoints
- **Pydantic**: Data validation and settings management

## Key Dependencies

- **Database & Storage**: ChromaDB (vector), Neo4j (graph), pandas (dataframes)
- **Web Automation**: Playwright, Selenium with webdriver-manager
- **AI/ML**: OpenAI SDK, sentence-transformers, GraphRAG
- **Processing**: BeautifulSoup4, trafilatura, easyocr, opencv-python
- **Azure Integration**: azure-kusto-data, azure-identity, aiohttp

## Build System

- **Package Manager**: `uv` (preferred) with `uv.lock` for dependency management
- **Build Backend**: setuptools with pyproject.toml configuration
- **Development Mode**: Local packages installed via setuptools in dev mode

## Common Commands

```bash
# Start the server
uv run server/main.py

# Run all tests
scripts/run_tests.sh

# Run tests in parallel
scripts/run_tests.sh --parallel

# Run specific test pattern
scripts/run_tests.sh "test_pattern"

# Install dependencies
uv sync

# Format code
black .
isort .

# Type checking
mypy .

# Docker build
docker build -t mcp-server .
docker run -p 8000:8000 mcp-server
```

## Development Tools

- **Testing**: pytest with asyncio, xdist (parallel), timeout support
- **Code Quality**: black (formatting), isort (imports), mypy (typing), flake8 (linting)
- **Pre-commit**: Automated code quality checks
- **Secrets**: detect-secrets for security scanning
