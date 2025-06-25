# Azure DevOps Repository Plugin

This plugin provides tools for interacting with Azure DevOps repositories, pull requests, and work items through three dedicated specialized tools. Each tool is designed for specific functionality and automatically loads default configuration values from environment variables while allowing parameter overrides for specific operations.

## Architecture

The plugin consists of three separate tools:

- **AzureRepoClient** (`azure_repo_client`) - Repository-level operations
- **AzurePullRequestTool** (`azure_pull_request`) - Pull request management
- **AzureWorkItemTool** (`azure_work_item`) - Work item management

## Features

### Repository Operations (AzureRepoClient)
- **List Repositories**: Get a list of repositories in a project
- **Get Repository**: Retrieve detailed information about a specific repository
- **Clone Repository**: Clone a repository to a local path

### Pull Request Operations (AzurePullRequestTool)
- **List Pull Requests**: Get filtered lists of pull requests
- **Get Pull Request**: Retrieve detailed information about a specific pull request
- **Create Pull Request**: Create new pull requests with auto-branch creation
- **Update Pull Request**: Modify existing pull request properties
- **Vote**: Vote on pull requests (approve, reject, etc.)
- **Add Work Items**: Link work items to pull requests
- **Get Comments**: Retrieve PR comments and discussion threads
- **Add Comment**: Add comments to pull requests
- **Update Comment**: Modify existing comments
- **Resolve Comment**: Resolve comment threads

### Work Item Operations (AzureWorkItemTool)
- **Get Work Item**: Retrieve detailed information about a specific work item
- **Create Work Item**: Create new work items with title, description, and assignment
- **Update Work Item**: Modify existing work item properties

## Configuration

All tools automatically load default values from environment variables with the `AZREPO_` prefix:

### Environment Variables

Add these to your `.env` file or set them as environment variables:

```bash
# Core Azure DevOps Configuration
AZREPO_ORG=https://dev.azure.com/your-organization
AZREPO_PROJECT=your-project-name
AZREPO_REPO=your-repository-name
AZREPO_BRANCH=main

# Work Item Defaults
AZREPO_AREA_PATH=your-area-path
AZREPO_ITERATION=your-iteration-path

# Authentication (choose one method)
AZREPO_BEARER_TOKEN=your-static-bearer-token
# OR
AZREPO_BEARER_TOKEN_COMMAND=az account get-access-token --scope "499b84ac-1321-427f-aa17-267ca6975798/.default"

# Pull Request Defaults
AZREPO_PR_BRANCH_PREFIX=feature/
```

### Configuration Benefits

- **Convenience**: Set your Azure DevOps details once instead of passing them to every operation
- **Flexibility**: Override defaults by providing explicit parameters when needed
- **Consistency**: Ensures all operations use the same organization/project/repository by default

## Prerequisites

- Appropriate permissions to access the Azure DevOps organization
- Authentication configured (bearer token or Azure CLI)
- Command executor tool available in the MCP tools registry

## Usage

Each tool is automatically registered and can be used through the tool interface:

### Repository Operations

```python
# List repositories
arguments = {
    "operation": "list_repos"
}
result = await azure_repo_client.execute_tool(arguments)

# Get specific repository
arguments = {
    "operation": "get_repo",
    "repository": "my-repo"
}
result = await azure_repo_client.execute_tool(arguments)

# Clone repository
arguments = {
    "operation": "clone_repo",
    "local_path": "/path/to/clone"
}
result = await azure_repo_client.execute_tool(arguments)
```

### Pull Request Operations

```python
# List active pull requests
arguments = {
    "operation": "list",
    "status": "active"
}
result = await azure_pull_request.execute_tool(arguments)

# Create pull request with auto-generated branch
arguments = {
    "operation": "create",
    "title": "My Feature",
    "description": "Feature description with **markdown** support"
}
result = await azure_pull_request.execute_tool(arguments)

# Get PR details
arguments = {
    "operation": "get",
    "pull_request_id": 123
}
result = await azure_pull_request.execute_tool(arguments)

# Vote on PR
arguments = {
    "operation": "vote",
    "pull_request_id": 123,
    "vote": "approve"
}
result = await azure_pull_request.execute_tool(arguments)

# Get PR comments
arguments = {
    "operation": "get_comments",
    "pull_request_id": 123
}
result = await azure_pull_request.execute_tool(arguments)
```

### Work Item Operations

```python
# Get work item
arguments = {
    "operation": "get",
    "work_item_id": 12345
}
result = await azure_work_item.execute_tool(arguments)

# Create work item
arguments = {
    "operation": "create",
    "title": "Bug Report",
    "description": "# Login Issue\n\nThe login functionality is **not working** properly.",
    "work_item_type": "Bug"
}
result = await azure_work_item.execute_tool(arguments)

# Update work item
arguments = {
    "operation": "update",
    "work_item_id": 12345,
    "title": "Updated Bug Report",
    "description": "Updated description with additional details"
}
result = await azure_work_item.execute_tool(arguments)
```

## Tool Reference

### AzureRepoClient (azure_repo_client)

#### list_repos
List repositories in the project.

**Parameters:**
- `project` (optional): Name or ID of the project (uses configured default)
- `organization` (optional): Azure DevOps organization URL (uses configured default)

#### get_repo
Get details of a specific repository.

**Parameters:**
- `repository` (optional): Name or ID of the repository (uses configured default)
- `project` (optional): Name or ID of the project (uses configured default)
- `organization` (optional): Azure DevOps organization URL (uses configured default)

#### clone_repo
Clone a repository to a local path.

**Parameters:**
- `clone_url` (optional): URL to clone (if not provided, constructed from other params)
- `local_path` (optional): Local path where to clone the repository
- `repository` (optional): Name or ID of the repository (uses configured default)
- `project` (optional): Name or ID of the project (uses configured default)
- `organization` (optional): Azure DevOps organization URL (uses configured default)

### AzurePullRequestTool (azure_pull_request)

#### list
List pull requests with optional filtering.

**Parameters:**
- `repository` (optional): Repository name/ID (uses configured default)
- `project` (optional): Project name/ID (uses configured default)
- `organization` (optional): Organization URL (uses configured default)
- `creator` (optional): Filter by creator ("default" for current user, empty for all)
- `reviewer` (optional): Filter by reviewer
- `status` (optional): Filter by status (active, completed, abandoned, all)
- `source_branch` (optional): Filter by source branch
- `target_branch` (optional): Filter by target branch ("default" for configured default)
- `exclude_drafts` (optional): Exclude draft PRs (default: true)
- `top` (optional): Maximum number of PRs to return
- `skip` (optional): Number of PRs to skip

#### get
Get details of a specific pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `organization` (optional): Organization URL (uses configured default)

#### create
Create a new pull request.

**Parameters:**
- `title` (optional): PR title (uses last commit message if not provided)
- `source_branch` (optional): Source branch (auto-creates from current HEAD if not provided)
- `target_branch` (optional): Target branch (uses configured default)
- `description` (optional): PR description (supports markdown)
- `repository` (optional): Repository name/ID (uses configured default)
- `project` (optional): Project name/ID (uses configured default)
- `organization` (optional): Organization URL (uses configured default)
- `reviewers` (optional): List of reviewers to add
- `work_items` (optional): List of work item IDs to link
- `draft` (optional): Create as draft PR (default: false)
- `auto_complete` (optional): Enable auto-complete (default: false)
- `squash` (optional): Enable squash merge (default: false)
- `delete_source_branch` (optional): Delete source branch after merge (default: false)

#### update
Update an existing pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request to update
- `title` (optional): New title
- `description` (optional): New description (supports markdown)
- `status` (optional): New status (active, abandoned, completed)
- `organization` (optional): Organization URL (uses configured default)
- `auto_complete` (optional): Enable/disable auto-complete
- `squash` (optional): Enable/disable squash merge
- `delete_source_branch` (optional): Enable/disable source branch deletion
- `draft` (optional): Enable/disable draft mode

#### vote
Set your vote on a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `vote` (required): Vote value (approve, approve-with-suggestions, reset, reject, wait-for-author)
- `organization` (optional): Organization URL (uses configured default)

#### add_work_items
Add work items to a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `work_items` (required): List of work item IDs to add
- `organization` (optional): Organization URL (uses configured default)

#### get_comments
Get comments for a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `organization` (optional): Organization URL (uses configured default)
- `project` (optional): Project name/ID (uses configured default)
- `repository` (optional): Repository name/ID (uses configured default)
- `comment_status` (optional): Filter by comment status (active, resolved)
- `comment_author` (optional): Filter by comment author
- `top` (optional): Maximum number of comments to return
- `skip` (optional): Number of comments to skip

#### add_comment
Add a comment to a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `comment_content` (required): Content of the comment (supports markdown)
- `thread_id` (optional): ID of existing thread to add comment to
- `parent_comment_id` (optional): ID of parent comment when replying
- `organization` (optional): Organization URL (uses configured default)
- `project` (optional): Project name/ID (uses configured default)
- `repository` (optional): Repository name/ID (uses configured default)

#### update_comment
Update an existing comment.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `thread_id` (required): ID of the comment thread
- `comment_id` (required): ID of the comment to update
- `comment_content` (required): New content for the comment (supports markdown)
- `organization` (optional): Organization URL (uses configured default)
- `project` (optional): Project name/ID (uses configured default)
- `repository` (optional): Repository name/ID (uses configured default)

#### resolve_comment
Resolve a comment thread.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `thread_id` (required): ID of the thread to resolve
- `response_text` (optional): Response text when resolving
- `organization` (optional): Organization URL (uses configured default)
- `project` (optional): Project name/ID (uses configured default)
- `repository` (optional): Repository name/ID (uses configured default)

### AzureWorkItemTool (azure_work_item)

#### get
Get details of a specific work item.

**Parameters:**
- `work_item_id` (required): ID of the work item
- `organization` (optional): Organization URL (uses configured default)
- `project` (optional): Project name/ID (uses configured default)
- `as_of` (optional): Work item details as of date/time (e.g., '2019-01-20')
- `expand` (optional): Expand parameters (all, fields, links, none, relations)
- `fields` (optional): Comma-separated list of requested fields

#### create
Create a new work item.

**Parameters:**
- `title` (required): Title of the work item
- `description` (optional): Description (supports markdown - auto-converted to HTML)
- `work_item_type` (optional): Type of work item (Bug, Task, User Story, etc., default: "Task")
- `area_path` (optional): Area path (uses configured default)
- `iteration_path` (optional): Iteration path (uses configured default)
- `assigned_to` (optional): Assignee ("current", "none", email, or display name, default: "current")
- `auto_assign_to_current_user` (optional): Auto-assign to current user (default: true)
- `organization` (optional): Organization URL (uses configured default)
- `project` (optional): Project name/ID (uses configured default)

#### update
Update an existing work item.

**Parameters:**
- `work_item_id` (required): ID of the work item to update
- `title` (optional): New title
- `description` (optional): New description (supports markdown - auto-converted to HTML)
- `organization` (optional): Organization URL (uses configured default)
- `project` (optional): Project name/ID (uses configured default)

## Authentication

The tools use Azure DevOps REST API with bearer token authentication. Configure authentication using one of these methods:

1. **Static Bearer Token**: Set `AZREPO_BEARER_TOKEN` environment variable
2. **Dynamic Token Command**: Set `AZREPO_BEARER_TOKEN_COMMAND` to a command that outputs the token

## Markdown Support

Both pull request descriptions/comments and work item descriptions support full markdown syntax including:
- Headers (`# ## ###`)
- Bold and italic text (`**bold**`, `*italic*`)
- Lists (ordered and unordered)
- Code blocks and inline code
- Links and images
- Tables
- Blockquotes
- Horizontal rules

Work item descriptions are automatically converted from markdown to HTML for Azure DevOps compatibility.

## Dependencies

This plugin depends on:
- `mcp_tools.interfaces.ToolInterface`
- `mcp_tools.plugin.register_tool`
- Command executor tool (automatically resolved from registry)
- Various utilities for REST API communication and markdown processing

## Error Handling

All tools include comprehensive error handling for:
- REST API failures
- JSON parsing errors
- Missing dependencies
- Invalid parameters
- Authentication failures

All operations return a dictionary with a `success` field indicating the operation status, and an `error` field containing error details when applicable.
