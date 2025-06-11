# AzureHttpClient Usage Guide

## Overview

The `AzureHttpClient` class provides a centralized HTTP client for Azure DevOps REST API operations. It replaces the need for multiple individual `aiohttp.ClientSession()` instances throughout the Azure DevOps tools, providing connection pooling, retry logic, and standardized error handling.

## Key Benefits

- **Connection Pooling**: Reuses connections across multiple requests (100 total, 30 per-host)
- **Retry Logic**: Automatic retries with exponential backoff for transient failures
- **Standardized Error Handling**: Consistent error processing and response formatting
- **Resource Management**: Proper async context manager for cleanup
- **Authentication Integration**: Seamless integration with existing `get_auth_headers()` function

## Basic Usage

```python
from azure_rest_utils import AzureHttpClient, get_auth_headers, build_api_url

async def make_api_request():
    # Create client with default configuration
    async with AzureHttpClient() as client:
        headers = get_auth_headers()
        url = build_api_url(organization, project, endpoint)
        
        # Make GET request
        response = await client.get(url, headers=headers)
        
        if response['success']:
            data = response['data']
            print(f"Success: {data}")
        else:
            print(f"Error: {response['error']}")
```

## Configuration Options

```python
# Custom configuration
async with AzureHttpClient(
    total_connections=50,        # Total connection pool limit
    per_host_connections=15,     # Per-host connection limit
    dns_cache_ttl=600,          # DNS cache TTL in seconds
    request_timeout=60,         # Request timeout in seconds
    max_retries=5,              # Maximum retry attempts
    retry_backoff_factor=1.0,   # Exponential backoff factor
    retry_statuses=[429, 500, 502, 503, 504]  # Status codes to retry
) as client:
    # Use client...
```

## HTTP Methods

The client supports all standard HTTP methods:

```python
async with AzureHttpClient() as client:
    # GET request
    response = await client.get(url, headers=headers, params=params)
    
    # POST request with JSON
    response = await client.post(url, headers=headers, json=data)
    
    # PATCH request
    response = await client.patch(url, headers=headers, json=update_data)
    
    # PUT request
    response = await client.put(url, headers=headers, json=data)
    
    # DELETE request
    response = await client.delete(url, headers=headers)
```

## Response Format

All methods return a standardized response format:

```python
{
    "success": bool,                    # True if request succeeded
    "data": dict,                      # Response data (on success)
    "error": str,                      # Error message (on failure)
    "status_code": int,                # HTTP status code
    "raw_response": str                # Raw response text
}
```

## Error Handling and Retries

The client automatically retries requests for the following conditions:

- **HTTP Status Codes**: 429 (Too Many Requests), 500, 502, 503, 504
- **Timeout Errors**: Server timeout and connection timeout errors
- **Exponential Backoff**: Delays increase exponentially between retries

```python
# Example with custom retry configuration
async with AzureHttpClient(
    max_retries=3,
    retry_backoff_factor=0.5,
    retry_statuses=[429, 500, 503]
) as client:
    response = await client.get(url, headers=headers)
    # Will retry up to 3 times with delays: 0.5s, 1.0s, 2.0s
```

## Migration from Individual Sessions

### Before (Multiple Sessions)
```python
# Old pattern - creates new session for each request
async def old_make_request():
    headers = get_auth_headers()
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"HTTP {response.status}")
```

### After (Centralized Client)
```python
# New pattern - reuses connection pool
async def new_make_request():
    async with AzureHttpClient() as client:
        headers = get_auth_headers()
        response = await client.get(url, headers=headers)
        
        if response['success']:
            return response['data']
        else:
            raise Exception(response['error'])
```

## Integration with Existing Tools

The `AzureHttpClient` is designed to integrate seamlessly with existing Azure DevOps utilities:

```python
from azure_rest_utils import AzureHttpClient, get_auth_headers, build_api_url, process_rest_response

async def list_pull_requests(organization, project, repository):
    async with AzureHttpClient() as client:
        # Use existing utilities
        headers = get_auth_headers()
        endpoint = f"git/repositories/{repository}/pullrequests"
        url = build_api_url(organization, project, endpoint)
        
        # Make request with automatic retry and error handling
        response = await client.get(url, headers=headers, params={
            "api-version": "7.1",
            "searchCriteria.status": "active"
        })
        
        return response
```

## Performance Benefits

- **Reduced Connection Overhead**: Connection pooling eliminates the need to establish new connections for each request
- **DNS Caching**: Reduces DNS lookup overhead for repeated requests to the same hosts
- **Keep-Alive Connections**: Maintains persistent connections for better performance
- **Configurable Limits**: Prevents resource exhaustion with configurable connection limits

## Best Practices

1. **Use Context Manager**: Always use `async with` to ensure proper cleanup
2. **Reuse Client Instance**: Create one client per operation scope, not per request
3. **Configure Appropriately**: Adjust connection limits and timeouts based on your use case
4. **Handle Errors Gracefully**: Check the `success` field in responses
5. **Monitor Retry Behavior**: Log retry attempts for debugging and monitoring

## Example: Complete Tool Integration

```python
class AzurePullRequestTool:
    def __init__(self):
        # Configure client for this tool's needs
        self.http_client_config = {
            'total_connections': 20,
            'per_host_connections': 10,
            'request_timeout': 30,
            'max_retries': 3
        }
    
    async def execute_tool(self, arguments):
        async with AzureHttpClient(**self.http_client_config) as client:
            if arguments['operation'] == 'list':
                return await self._list_pull_requests(client, arguments)
            elif arguments['operation'] == 'create':
                return await self._create_pull_request(client, arguments)
            # ... other operations
    
    async def _list_pull_requests(self, client, args):
        headers = get_auth_headers()
        url = build_api_url(args['org'], args['project'], 
                           f"git/repositories/{args['repo']}/pullrequests")
        
        response = await client.get(url, headers=headers, params={
            "api-version": "7.1",
            "searchCriteria.status": args.get('status', 'active')
        })
        
        if response['success']:
            return {"success": True, "data": response['data']}
        else:
            return {"success": False, "error": response['error']}
```

This centralized approach eliminates the HTTP message proliferation issue and provides a robust foundation for all Azure DevOps REST API operations. 