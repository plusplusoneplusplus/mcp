# Configuration

This directory contains configuration modules and templates for the MCP project.

## Environment Configuration

The environment configuration manages repository information and environment settings through `.env` files.

### Template

A template file is provided at `templates/env.template` which can be copied to create your `.env` file:

```bash
# From project root
cp config/templates/env.template .env
```

### Configuration Options

The following configuration keys are recognized:

- `GIT_ROOT` - Path to the git repository root
- `WORKSPACE_FOLDER` - Path to the workspace folder
- `PROJECT_NAME` - Name of the project
- `PRIVATE_TOOL_ROOT` - Path to the private tool root
- `MCP_PATH_*` - Additional paths (e.g., `MCP_PATH_DATA=/path/to/data`)

### Azure Repo Parameters

Special support is provided for Azure Repo parameters. Any `.env` entry with the prefix `AZREPO_` will be loaded as an Azure Repo parameter. For example:

```
AZREPO_ORG=myorg
AZREPO_PROJECT=myproject
AZREPO_REPO=myrepo
```

### Search Order

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
``` 