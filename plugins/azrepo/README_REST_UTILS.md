# Azure DevOps REST API Utilities

This module provides shared utilities for interacting with the Azure DevOps REST API across different tools in the Azure DevOps plugin.

## Features

- Authentication and authorization header generation
- URL building for REST API endpoints
- Standardized response processing and error handling
- Helper utilities for common operations (username detection, token acquisition)

## Usage

Import the shared utilities in your Azure DevOps tool:

```python
from .azure_rest_utils import (
    get_current_username,
    get_auth_headers,
    build_api_url,
    process_rest_response,
)
```

### Authentication Headers

Generate standard authentication headers for REST API calls:

```python
# Default headers for GET requests (application/json)
headers = get_auth_headers()

# Custom content type for PATCH operations
headers = get_auth_headers(content_type="application/json-patch+json")
```

### API URL Building

Create properly formatted Azure DevOps REST API URLs:

```python
# Using organization name
url = build_api_url("myorg", "myproject", "wit/workitems/123")

# Using full organization URL
url = build_api_url("https://dev.azure.com/myorg", "myproject", "wit/workitems/123")

# Using custom host
url = build_api_url("https://custom.example.com/myorg", "myproject", "wit/workitems/123")
```

### Response Processing

Process API responses with standardized error handling:

```python
async with aiohttp.ClientSession() as session:
    async with session.get(url, headers=headers) as response:
        response_text = await response.text()
        result = process_rest_response(response_text, response.status)
        
        if result["success"]:
            # Handle successful response
            data = result["data"]
        else:
            # Handle error
            error_message = result["error"]
```

### Other Utilities

Get the current username (for auto-assignment features):

```python
username = get_current_username()
if username:
    # Assign to current user
    patch_document.append({
        "op": "add",
        "path": "/fields/System.AssignedTo",
        "value": username
    })
```

## Configuration

The utilities use the `env_manager` to retrieve Azure DevOps configuration:

- `AZREPO_ORG`: Default organization URL
- `AZREPO_PROJECT`: Default project name/ID
- `AZREPO_BEARER_TOKEN`: Bearer token for REST API authentication (static)
- `AZREPO_BEARER_TOKEN_COMMAND`: Command to get bearer token dynamically (should output JSON with "accessToken" property)

## Testing

Unit tests for the shared utilities are provided in `tests/test_rest_utils.py`. 