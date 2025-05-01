# Configuration

This directory contains configuration modules and templates for the MCP project.

## Environment Configuration

The environment configuration manages repository information and environment settings through `.env` files and environment variables.

### Template

A template file is provided at `templates/env.template` which can be copied to create your `.env` file:

```bash
# From project root
cp config/templates/env.template .env
```

### Configuration Options

The environment manager supports several categories of configuration:

- Repository information (git root, workspace folder, etc.)
- Project settings (name, paths, etc.)
- Additional paths with the `MCP_PATH_` prefix
- Azure Repo parameters with the `AZREPO_` prefix
- Kusto parameters with the `KUSTO_` prefix

### Parameter Prefixes

Special prefix support is provided for several parameter types:

- `MCP_PATH_*` - Adds to `additional_paths` with the suffix as the key
- `AZREPO_*` - Added to Azure Repo parameters
- `KUSTO_*` - Added to Kusto parameters

Example:
```
MCP_PATH_DATA=/path/to/data
AZREPO_ORG=myorg
KUSTO_CLUSTER=mycluster
```

### Configuration Sources and Precedence

The environment manager loads configuration from multiple sources in the following order of precedence (highest to lowest):

1. Custom providers (registered through `register_provider()`)
2. OS environment variables
3. `.env` file

This means values from OS environment variables will override those from the `.env` file, and provider values will override both.

### .env File Search Order

The environment manager looks for `.env` files in the following locations (in order):

1. Workspace folder
2. Git root directory
3. Current working directory
4. User's home directory
5. The template file (as a fallback)

The first file found will be used.

### Usage in Code

```python
from config import env_manager, env

# Load the environment information
env_manager.load()

# Get git root directory
git_root = env_manager.get_git_root()

# Get parameter dictionary for command substitution
params = env_manager.get_parameter_dict()

# Get Azure repo parameters
azrepo_params = env_manager.get_azrepo_parameters()

# Get Kusto parameters
kusto_params = env_manager.get_kusto_parameters()
``` 