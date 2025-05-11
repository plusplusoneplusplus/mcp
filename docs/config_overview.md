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
  cp config/templates/env.template .env
  ```
- Add or edit configuration parameters in your `.env` file as needed.
- The environment manager loads configuration from:
  1. Custom providers (registered via code)
  2. OS environment variables
  3. `.env` file
  (in order of precedence)

**Parameter Prefixes:**
- `MCP_PATH_*` — Adds to additional paths
- `AZREPO_*` — Azure Repo configuration
- `KUSTO_*` — Kusto configuration

Example:
```
MCP_PATH_DATA=/path/to/data
AZREPO_ORG=myorg
KUSTO_CLUSTER=mycluster
```

**Typical Categories:**
- Repository information (git root, workspace folder, etc.)
- Project settings (name, paths, etc.)
- Azure Repo and Kusto integration parameters

---

For more details, refer to the configuration source files and templates in the `config/` directory.
