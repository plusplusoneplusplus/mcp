# MCP Project Overview

## Project Description
MCP is a sophisticated AI-powered development framework built around the Model Context Protocol. It consists of a Python-based MCP server and a TypeScript VS Code extension called "Wu Wei" that provides effortless development automation.

## Tech Stack

### Python Backend (MCP Server)
- **Core**: Python 3.11+, MCP SDK 1.7.1+, uv package manager
- **Web Framework**: Starlette (ASGI) with Uvicorn server
- **Databases**: Neo4j (graph), ChromaDB (vector)
- **Browser Automation**: Selenium, Playwright, WebDriver Manager
- **AI/ML**: OpenAI API, Microsoft GraphRAG, Sentence Transformers
- **Azure Integration**: Azure Data Explorer (Kusto), Azure DevOps REST API
- **Testing**: Pytest with async support

### TypeScript Frontend (Wu Wei Extension)
- **Platform**: VS Code Extension (Node.js 16+, VS Code 1.90+)
- **Build**: TypeScript 4.9+, ESBuild bundling
- **UI Framework**: @vscode/prompt-tsx for prompt composition
- **Testing**: Mocha with VS Code test framework

## Key Directories

### `/mcp_tools/` - Core MCP Tools Framework
Plugin system providing command execution, browser automation, time utilities, and YAML-based tool definitions.

### `/server/` - Server Infrastructure
HTTP/SSE API, background jobs, tool history, configuration management, and web UI dashboard.

### `/plugins/` - Specialized Plugins
- **azure_devops**: Repository management, PR operations, work items
- **circleci**: CI/CD pipeline integration
- **git_tools**: Advanced Git operations
- **knowledge_indexer**: Document processing and semantic search
- **kusto**: Azure Data Explorer query interface
- **log_analysis**: Log compression and parsing
- **text_summarization**: AI-powered content summarization

### `/utils/` - Utility Libraries
Async jobs, graph interface, vector store, memory management, security, content processing.

### `/wu-wei/` - VS Code Extension
Chat participant, prompt store, agent panel, tool integration, webview panels.

### `/graphrag/` - GraphRAG Integration
Microsoft GraphRAG implementation for knowledge graph construction and document processing.

## Commands

### Python Execution
- Always use `uv run python` instead of just `python` for running Python scripts
- Always use `uv run pytest` instead of just `pytest` for running tests
- For installing packages, use `uv add` instead of `pip install`
- For package management operations, use `uv` commands consistently

### Examples:
- Running tests: `uv run pytest tests/`
- Running Python scripts: `uv run python script.py`
- Installing dependencies: `uv add package_name`
- Running modules: `uv run python -m module_name`

### TypeScript/VS Code Extension
- Building: `npm run compile` (in wu-wei directory)
- Testing: `npm test` (in wu-wei directory)
- Packaging: `npm run package` (creates .vsix file)

## Key Features
- Plugin-based architecture with modular design
- AI-powered automation with OpenAI integration
- Multi-database support (Neo4j, ChromaDB)
- Enterprise integrations (Azure DevOps, Kusto, CircleCI)
- Advanced browser automation capabilities
- Real-time communication via Server-Sent Events
- Comprehensive testing framework
- Security features with secret scanning

## Additional References
- github issue workflow @.cursor/rules/github_issue_workflow.mdc
