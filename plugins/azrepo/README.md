# Azure DevOps Repository Plugin

This plugin provides tools for interacting with Azure DevOps repositories, including pull request management and other repository operations. It automatically loads default configuration values from environment variables while allowing parameter overrides for specific operations.

## Features

The Azure Repo Client plugin supports the following operations:

- **List Pull Requests**: Get a list of pull requests with various filtering options
- **Get Pull Request**: Retrieve detailed information about a specific pull request
- **Create Pull Request**: Create a new pull request with customizable options
- **Update Pull Request**: Modify existing pull request properties
- **Set Vote**: Vote on a pull request (approve, reject, etc.)
- **Add Reviewers**: Add reviewers to a pull request
- **Add Work Items**: Link work items to a pull request
- **Get Work Item**: Retrieve detailed information about a specific work item
- **Create Work Item**: Create a new work item with title, description, and optional area/iteration paths

## Configuration

The plugin automatically loads default values from environment variables with the `AZREPO_` prefix. This allows you to configure your Azure DevOps settings once and use them across all operations.

### Environment Variables

Add these to your `.env` file or set them as environment variables:

```bash
# Azure DevOps Configuration
AZREPO_ORG=https://dev.azure.com/your-organization
AZREPO_PROJECT=your-project-name
AZREPO_REPO=your-repository-name
AZREPO_BRANCH=main
# Work item defaults
AZREPO_AREA_PATH=your-area-path
AZREPO_ITERATION=your-iteration-path
```

### Configuration Benefits

- **Convenience**: Set your Azure DevOps details once instead of passing them to every operation
- **Flexibility**: Override defaults by providing explicit parameters when needed
- **Consistency**: Ensures all operations use the same organization/project/repository by default

## Prerequisites

- Azure CLI must be installed and configured
- Appropriate permissions to access the Azure DevOps repository
- Command executor tool must be available in the MCP tools registry

## Usage

The plugin is automatically registered when the MCP tools system discovers plugins. You can use it through the tool interface:

```python
# Example usage with configured defaults
# (assumes AZREPO_* environment variables are set)
arguments = {
    "operation": "list_pull_requests",
    "status": "active"  # Uses configured org/project/repo
}

result = await azure_repo_client.execute_tool(arguments)

# Example with parameter overrides
arguments = {
    "operation": "create_pull_request",
    "title": "My Feature",
    "source_branch": "feature/my-feature",
    "organization": "different-org"  # Override configured default
}

result = await azure_repo_client.execute_tool(arguments)
```

## Operations

### list_pull_requests
List pull requests with optional filtering.

**Parameters:**
- `repository` (optional): Name or ID of the repository (uses configured default if not provided)
- `project` (optional): Name or ID of the project (uses configured default if not provided)
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)
- `creator` (optional): Filter by PR creator
- `reviewer` (optional): Filter by reviewer
- `status` (optional): Filter by status (abandoned, active, all, completed)
- `source_branch` (optional): Filter by source branch
- `target_branch` (optional): Filter by target branch
- `top` (optional): Maximum number of PRs to return
- `skip` (optional): Number of PRs to skip

### get_pull_request
Get details of a specific pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)

### create_pull_request
Create a new pull request.

**Parameters:**
- `title` (required): Title for the pull request
- `source_branch` (required): Name of the source branch
- `target_branch` (optional): Name of the target branch (uses configured default if not provided)
- `description` (optional): Description for the pull request
- `repository` (optional): Name or ID of the repository (uses configured default if not provided)
- `project` (optional): Name or ID of the project (uses configured default if not provided)
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)
- `reviewers` (optional): List of reviewers to add
- `work_items` (optional): List of work item IDs to link
- `draft` (optional): Create as draft PR
- `auto_complete` (optional): Enable auto-complete
- `squash` (optional): Enable squash merge
- `delete_source_branch` (optional): Delete source branch after merge

### update_pull_request
Update an existing pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request to update
- `title` (optional): New title
- `description` (optional): New description
- `status` (optional): New status (active, abandoned, completed)
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)
- `auto_complete` (optional): Enable/disable auto-complete
- `squash` (optional): Enable/disable squash merge
- `delete_source_branch` (optional): Enable/disable source branch deletion
- `draft` (optional): Enable/disable draft mode

### set_vote
Set your vote on a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `vote` (required): Vote value (approve, approve-with-suggestions, reset, reject, wait-for-author)
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)

### add_reviewers
Add reviewers to a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `reviewers` (required): List of reviewers to add
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)

### add_work_items
Add work items to a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `work_items` (required): List of work item IDs to add
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)

### get_work_item
Get details of a specific work item.

**Parameters:**
- `work_item_id` (required): ID of the work item
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)
- `project` (optional): Name or ID of the project (uses configured default if not provided)
- `as_of` (optional): Work item details as of a particular date and time (e.g., '2019-01-20', '2019-01-20 00:20:00')
- `expand` (optional): The expand parameters for work item attributes (all, fields, links, none, relations)
- `fields` (optional): Comma-separated list of requested fields (e.g., System.Id,System.AreaPath)

### create_work_item
Create a new work item.

**Parameters:**
- `title` (required): Title of the work item
- `description` (optional): Description of the work item. **Supports markdown format** - will be automatically converted to HTML for Azure DevOps
- `work_item_type` (optional): Type of work item (Bug, Task, User Story, etc.) - defaults to "Task"
- `area_path` (optional): Area path for the work item (uses configured default if not provided)
- `iteration_path` (optional): Iteration path for the work item (uses configured default if not provided)
- `organization` (optional): Azure DevOps organization URL (uses configured default if not provided)
- `project` (optional): Name or ID of the project (uses configured default if not provided)

**Markdown Support:**
The `description` parameter supports full markdown syntax including:
- Headers (`# ## ###`)
- Bold and italic text (`**bold**`, `*italic*`)
- Lists (ordered and unordered)
- Code blocks and inline code
- Links and images
- Tables
- Blockquotes
- Horizontal rules

Example with markdown description:
```json
{
  "operation": "create",
  "title": "Bug Report",
  "description": "# Login Issue\n\n## Description\nThe login functionality is **not working** properly.\n\n## Steps to Reproduce\n1. Navigate to login page\n2. Enter credentials\n3. Click login\n\n```bash\n# Error in console\nError: Invalid credentials\n```"
}
```

## Dependencies

This plugin depends on:
- `mcp_tools.interfaces.ToolInterface`
- `mcp_tools.interfaces.RepoClientInterface`
- `mcp_tools.plugin.register_tool`
- Command executor tool (automatically resolved from registry)

## Error Handling

The plugin includes comprehensive error handling for:
- Azure CLI command failures
- JSON parsing errors
- Missing dependencies
- Invalid parameters

All operations return a dictionary with a `success` field indicating the operation status, and an `error` field containing error details when applicable.
