# Azure DevOps REST API Utilities

This module provides shared utilities for interacting with the Azure DevOps REST API across different tools and components.

## Overview

The `azure_rest_utils.py` module contains common functionality that was previously duplicated in different tools like `workitem_tool.py` and `pr_tool.py`. By centralizing these utilities, we achieve:

1. **Reduced code duplication** - Common functionality is defined in one place
2. **Consistent behavior** - Authentication, URL building, and error handling follow the same patterns everywhere
3. **Easier maintenance** - Bug fixes and improvements can be made in one place
4. **Better testability** - Core utilities can be tested independently

## Included Utilities

### Authentication

- `get_auth_headers(content_type: str = "application/json") -> Dict[str, str]`
  - Generates proper authentication headers for Azure DevOps REST API requests
  - Handles both static bearer tokens and dynamic token retrieval via commands
  - Automatically reads configuration from environment variables

### URL Building

- `build_api_url(organization: str, project: str, endpoint: str) -> str`
  - Constructs complete Azure DevOps REST API URLs
  - Handles both organization names and full URLs
  - Formats URLs consistently for all API calls

### Response Processing

- `process_rest_response(response_text: str, status_code: int) -> Dict[str, Any]`
  - Standardizes REST API response handling
  - Provides consistent error formatting
  - Simplifies JSON parsing with proper error handling

### Helper Utilities

- `get_current_username() -> Optional[str]`
  - Cross-platform detection of current username
  - Used for auto-assignment features
  - Falls back to environment variables when needed

- `execute_bearer_token_command(command: str) -> Optional[str]`
  - Executes commands that output bearer tokens (e.g., `az account get-access-token`)
  - Parses JSON output to extract access tokens
  - Provides secure error handling and logging

## Migrating Existing Code

When migrating existing code to use these shared utilities:

1. Replace direct REST API header creation with `get_auth_headers()`
2. Replace URL construction with `build_api_url()`
3. Consider using `process_rest_response()` for consistent response handling

## Backward Compatibility

All backward compatibility wrapper methods have been completely removed from both tools. The methods that were removed include:

- **From AzureWorkItemTool**: `_get_auth_headers()`, `_get_current_username()`
- **From AzurePullRequestTool**: `_get_auth_headers()`, `_get_current_username()`

These methods were either only used in tests or have been replaced with direct calls to shared utilities in production code. This results in:

- **Cleaner code**: No unnecessary wrapper methods
- **Better maintainability**: Direct calls to shared utilities
- **Improved testability**: Tests mock the shared utilities directly
- **Consistency**: Both tools follow the same pattern

All production code now calls the shared utility functions directly, and tests have been updated to mock the appropriate functions where they are imported and used.

## Testing

The shared utilities are tested in `test_rest_utils.py`, which includes:

- Unit tests for each utility function
- Integration tests for combinations of utilities
- Mock tests for command execution and environment handling

## Configuration

All utilities use the standard Azure DevOps configuration values from `env_manager`, including:

- `org` - Azure DevOps organization name or URL
- `project` - Azure DevOps project name
- `bearer_token` - Static bearer token for authentication
- `bearer_token_command` - Command to execute for dynamic token retrieval

## Future Improvements

Potential future improvements to the shared utilities:

1. Add support for additional authentication methods
2. Implement retry logic for transient API failures
3. Add caching for frequently used responses
4. Create higher-level API helpers for common operations
