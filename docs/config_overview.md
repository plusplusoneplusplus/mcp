# Configuration Overview

This document provides a high-level summary of the configuration system and environment management for this project. For details on available options and templates, see the configuration files in the `config/` directory.

---

## Environment Configuration

**Functionality:**
- Manages repository and environment settings using `.env` files and environment variables.
- Supports configuration for repository info, project settings, and integration parameters (e.g., Azure Repo, Kusto).
- Allows custom providers to override or extend configuration sources.

**Usage:**
- Copy the provided template to create your own `.env` file:
  ```bash
  # From project root
  cp config/env.template .env
  ```
- Add or edit configuration parameters in your `.env` file as needed.
- The environment manager loads configuration from:
  1. Custom providers (registered via code)
  2. OS environment variables
  3. `.env` file
  (in order of precedence)

**Parameter Prefixes:**
- `MCP_PATH_*` — Adds to additional paths
- `GIT_ROOT_*` — Multi-project git root support
- `AZREPO_*` — Azure Repo configuration
- `KUSTO_*` — Kusto configuration
- `NEO4J_*` — Neo4j database configuration
- `MCP_*` — Plugin system and tool configuration

Example:
```
MCP_PATH_DATA=/path/to/data
GIT_ROOT_FRONTEND=/path/to/frontend
AZREPO_ORG=myorg
KUSTO_CLUSTER=mycluster
NEO4J_URI=bolt://localhost:7687
MCP_PLUGIN_MODE=whitelist
```

**Configuration Categories:**
- Repository information (git root, workspace folder, multi-project support)
- Database connections (Neo4j configuration)
- Integration services (Azure Repo, Kusto)
- Tool management (plugin system, tool discovery, YAML tools)
- Browser automation (Playwright/Chrome configuration)
- Data persistence (DataFrame storage, vector store, tool history)
- Command execution (periodic reporting, memory management)
- Background processing (job history, async operations)

---

For more details, refer to the configuration source files and templates in the `config/` directory.
