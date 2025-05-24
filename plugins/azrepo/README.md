# Azure DevOps Repository Plugin

This plugin provides tools for interacting with Azure DevOps repositories, including pull request management and other repository operations.

## Features

The Azure Repo Client plugin supports the following operations:

- **List Pull Requests**: Get a list of pull requests with various filtering options
- **Get Pull Request**: Retrieve detailed information about a specific pull request
- **Create Pull Request**: Create a new pull request with customizable options
- **Update Pull Request**: Modify existing pull request properties
- **Set Vote**: Vote on a pull request (approve, reject, etc.)
- **Add Reviewers**: Add reviewers to a pull request
- **Add Work Items**: Link work items to a pull request

## Prerequisites

- Azure CLI must be installed and configured
- Appropriate permissions to access the Azure DevOps repository
- Command executor tool must be available in the MCP tools registry

## Usage

The plugin is automatically registered when the MCP tools system discovers plugins. You can use it through the tool interface:

```python
# Example usage through the tool interface
arguments = {
    "operation": "list_pull_requests",
    "repository": "my-repo",
    "project": "my-project",
    "status": "active"
}

result = await azure_repo_client.execute_tool(arguments)
```

## Operations

### list_pull_requests
List pull requests with optional filtering.

**Parameters:**
- `repository` (optional): Name or ID of the repository
- `project` (optional): Name or ID of the project
- `organization` (optional): Azure DevOps organization URL
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
- `organization` (optional): Azure DevOps organization URL

### create_pull_request
Create a new pull request.

**Parameters:**
- `title` (required): Title for the pull request
- `source_branch` (required): Name of the source branch
- `target_branch` (optional): Name of the target branch
- `description` (optional): Description for the pull request
- `repository` (optional): Name or ID of the repository
- `project` (optional): Name or ID of the project
- `organization` (optional): Azure DevOps organization URL
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
- `organization` (optional): Azure DevOps organization URL
- `auto_complete` (optional): Enable/disable auto-complete
- `squash` (optional): Enable/disable squash merge
- `delete_source_branch` (optional): Enable/disable source branch deletion
- `draft` (optional): Enable/disable draft mode

### set_vote
Set your vote on a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `vote` (required): Vote value (approve, approve-with-suggestions, reset, reject, wait-for-author)
- `organization` (optional): Azure DevOps organization URL

### add_reviewers
Add reviewers to a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `reviewers` (required): List of reviewers to add
- `organization` (optional): Azure DevOps organization URL

### add_work_items
Add work items to a pull request.

**Parameters:**
- `pull_request_id` (required): ID of the pull request
- `work_items` (required): List of work item IDs to add
- `organization` (optional): Azure DevOps organization URL

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