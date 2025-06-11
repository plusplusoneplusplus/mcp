# Azure HTTP Client

A centralized HTTP client utility for Azure DevOps REST API operations, designed to eliminate HTTP message proliferation and provide robust connection management.

## Features

- **Connection Pooling**: Reuses connections to improve performance
- **Automatic Retries**: Handles transient failures with exponential backoff
- **Standardized Error Handling**: Consistent error responses across all operations
- **Resource Management**: Proper cleanup of connections and sessions
- **Azure DevOps Integration**: Built-in support for authentication and URL building
- **Configurable**: Customizable timeouts, retry policies, and connection limits

## Quick Start

### Basic Usage with Azure DevOps Integration

```python
from plugins.azrepo.azure_rest_utils import AzureHttpClient

async def example_usage():
    async with AzureHttpClient() as client:
        # Get work items - automatically handles auth and URL building
        result = await client.azure_get(
            organization="myorg",
            project="myproject",
            endpoint="wit/workitems/123",
            params={"api-version": "7.1"}
        )

        if result['success']:
            work_item = result['data']
            print(f"Work item title: {work_item['fields']['System.Title']}")
        else:
            print(f"Error: {result['error']}")

        # Create a work item
        work_item_data = {
            "op": "add",
            "path": "/fields/System.Title",
            "value": "New Bug Report"
        }

        result = await client.azure_patch(
            organization="myorg",
            project="myproject",
            endpoint="wit/workitems/$Bug",
            json=[work_item_data],
            params={"api-version": "7.1"}
        )

        if result['success']:
            print(f"Created work item: {result['data']['id']}")
```

### Advanced Usage with Custom Configuration

```python
from plugins.azrepo.azure_rest_utils import AzureHttpClient

# Custom configuration for high-throughput scenarios
async def high_performance_example():
    client = AzureHttpClient(
        total_connections=200,      # Increase connection pool
        per_host_connections=50,    # More connections per host
        request_timeout=30,         # Longer timeout
        max_retries=5,             # More retry attempts
        retry_backoff_factor=2.0   # Faster backoff
    )

    async with client:
        # Batch operations
        tasks = []
        for work_item_id in range(1, 101):
            task = client.azure_get(
                organization="myorg",
                project="myproject",
                endpoint=f"wit/workitems/{work_item_id}",
                params={"api-version": "7.1"}
            )
            tasks.append(task)

        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_items = [r['data'] for r in results if isinstance(r, dict) and r.get('success')]
        print(f"Retrieved {len(successful_items)} work items")
```

## API Reference

### Azure DevOps Convenience Methods

These methods automatically handle authentication, URL building, and response processing:

#### `azure_get(organization, project, endpoint, params=None, **kwargs)`
Perform GET requests to Azure DevOps REST API.

#### `azure_post(organization, project, endpoint, json=None, data=None, **kwargs)`
Perform POST requests to Azure DevOps REST API.

#### `azure_patch(organization, project, endpoint, json=None, data=None, **kwargs)`
Perform PATCH requests to Azure DevOps REST API.

#### `azure_put(organization, project, endpoint, json=None, data=None, **kwargs)`
Perform PUT requests to Azure DevOps REST API.

#### `azure_delete(organization, project, endpoint, **kwargs)`
Perform DELETE requests to Azure DevOps REST API.

**Parameters:**
- `organization`: Azure DevOps organization name or full URL
- `project`: Azure DevOps project name
- `endpoint`: API endpoint path (without leading slash)
- `json`: JSON payload for POST/PATCH/PUT requests
- `data`: Raw data payload for POST/PATCH/PUT requests
- `params`: Query parameters for GET requests
- `**kwargs`: Additional arguments passed to the underlying request

**Returns:**
All methods return a standardized response dictionary:
```python
{
    "success": bool,
    "data": Optional[Dict[str, Any]],    # Present on success
    "error": Optional[str],              # Present on failure
    "raw_output": Optional[str]          # Present on failure or parse error
}
```

### Low-Level HTTP Methods

For non-Azure DevOps APIs or when you need full control:

#### `request(method, url, **kwargs)`
Generic HTTP request method with retry logic.

#### `get(url, **kwargs)`, `post(url, **kwargs)`, `patch(url, **kwargs)`, `put(url, **kwargs)`, `delete(url, **kwargs)`
Convenience methods for specific HTTP verbs.

## Configuration Options

### Constructor Parameters

```python
AzureHttpClient(
    total_connections: int = 100,           # Total connection pool size
    per_host_connections: int = 30,         # Max connections per host
    dns_cache_ttl: int = 300,              # DNS cache TTL in seconds
    request_timeout: int = 30,              # Request timeout in seconds
    max_retries: int = 3,                   # Maximum retry attempts
    retry_backoff_factor: float = 1.0,      # Exponential backoff factor
    retry_statuses: Optional[List[int]] = None  # HTTP status codes to retry
)
```

### Default Retry Status Codes
- `429` - Too Many Requests
- `500` - Internal Server Error
- `502` - Bad Gateway
- `503` - Service Unavailable
- `504` - Gateway Timeout

## Migration Guide

### From Individual Sessions

**Before:**
```python
async with aiohttp.ClientSession() as session:
    headers = get_auth_headers()
    url = build_api_url(org, project, endpoint)
    async with session.get(url, headers=headers) as response:
        result = process_rest_response(await response.text(), response.status)
```

**After:**
```python
async with AzureHttpClient() as client:
    result = await client.azure_get(org, project, endpoint)
```

### From Multiple Tools

**Before (PR Tool):**
```python
# 11 separate ClientSession instances across different methods
async with aiohttp.ClientSession() as session:
    # ... authentication and URL building logic repeated
```

**After:**
```python
# Single shared client instance
async with AzureHttpClient() as client:
    # All operations use the same connection pool
    pr_result = await client.azure_get(org, project, "git/pullrequests/123")
    comments_result = await client.azure_get(org, project, "git/pullrequests/123/threads")
```

## Best Practices

### 1. Use Context Managers
Always use the client within an async context manager to ensure proper resource cleanup:

```python
async with AzureHttpClient() as client:
    # Your operations here
    pass
# Resources automatically cleaned up
```

### 2. Reuse Client Instances
Create one client instance per logical operation group:

```python
# Good: One client for related operations
async with AzureHttpClient() as client:
    work_item = await client.azure_get(org, project, "wit/workitems/123")
    comments = await client.azure_get(org, project, "wit/workitems/123/comments")

# Avoid: Multiple clients for related operations
async with AzureHttpClient() as client1:
    work_item = await client1.azure_get(org, project, "wit/workitems/123")
async with AzureHttpClient() as client2:
    comments = await client2.azure_get(org, project, "wit/workitems/123/comments")
```

### 3. Handle Errors Gracefully
Always check the `success` field in responses:

```python
result = await client.azure_get(org, project, endpoint)
if result['success']:
    data = result['data']
    # Process successful response
else:
    logger.error(f"API request failed: {result['error']}")
    # Handle error appropriately
```

### 4. Configure for Your Use Case
Adjust configuration based on your application's needs:

```python
# High-throughput applications
client = AzureHttpClient(
    total_connections=200,
    per_host_connections=50,
    max_retries=5
)

# Low-latency applications
client = AzureHttpClient(
    request_timeout=10,
    max_retries=1,
    retry_backoff_factor=0.5
)
```

## Integration with Existing Code

The `AzureHttpClient` seamlessly integrates with existing Azure DevOps utilities:

- **Authentication**: Automatically uses `get_auth_headers()` for all Azure requests
- **URL Building**: Leverages `build_api_url()` for proper endpoint construction
- **Response Processing**: Uses `process_rest_response()` for consistent error handling
- **Environment**: Works with existing environment variable configuration

This ensures backward compatibility while providing the benefits of centralized HTTP management.
