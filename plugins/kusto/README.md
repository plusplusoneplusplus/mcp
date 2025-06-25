# Azure Data Explorer (Kusto) Plugin

This plugin provides tools for executing KQL (Kusto Query Language) queries against Azure Data Explorer (Kusto) databases. It automatically handles authentication and connection management while providing flexible configuration options.

## Features

- **KQL Query Execution**: Execute Kusto Query Language queries against Azure Data Explorer clusters
- **Multiple Authentication Methods**: Supports Service Principal, DefaultAzureCredential, and Azure CLI authentication
- **Flexible Cluster URL Handling**: Accepts various cluster URL formats and normalizes them automatically
- **Intelligent Result Formatting**: Automatically formats query results for optimal LLM analysis
- **Comprehensive Error Handling**: Detailed error reporting with specific error types and traces
- **Environment-Based Configuration**: Automatic configuration loading from environment variables

## Prerequisites

- Azure Data Explorer cluster access
- Appropriate permissions to query the target databases
- Authentication configured (one of the methods below)
- Required Python packages: `azure-kusto-data`, `azure-identity`

## Configuration

The plugin automatically loads configuration from environment variables with the `KUSTO_` prefix:

### Environment Variables

Add these to your `.env` file or set them as environment variables:

```bash
# Required: Cluster Configuration
KUSTO_CLUSTER_URL=https://your-cluster.kusto.windows.net
KUSTO_DATABASE=your-default-database

# Optional: Service Principal Authentication
KUSTO_APP_ID=your-app-id
KUSTO_APP_KEY=your-app-key
KUSTO_TENANT_ID=your-tenant-id
```

### Configuration Benefits

- **Convenience**: Set cluster and database once instead of passing them to every query
- **Flexibility**: Override defaults by providing explicit parameters when needed
- **Security**: Store sensitive authentication details in environment variables

## Authentication

The plugin tries multiple authentication methods in order of preference:

### 1. Service Principal (App Registration)
**Best for**: Production environments, automated scripts

```bash
KUSTO_APP_ID=your-app-id
KUSTO_APP_KEY=your-app-key
KUSTO_TENANT_ID=your-tenant-id
```

### 2. DefaultAzureCredential
**Best for**: Development environments, managed identities

Automatically tries multiple authentication methods:
- Managed Identity
- Visual Studio authentication
- Azure CLI authentication
- Environment variables
- And more...

### 3. Azure CLI Authentication
**Best for**: Local development, interactive scenarios

Requires `az login` to be completed:
```bash
az login
```

## Usage

The plugin is automatically registered and can be used through the tool interface:

### Basic Query Execution

```python
# Execute a simple query (uses configured defaults)
arguments = {
    "operation": "execute_query",
    "database": "MyDatabase",
    "query": "MyTable | limit 10"
}
result = await kusto_client.execute_tool(arguments)
print(result["result"])
```

### Advanced Query Examples

```python
# Query with custom cluster
arguments = {
    "operation": "execute_query",
    "database": "LogsDatabase",
    "query": """
        SecurityEvent
        | where TimeGenerated > ago(1h)
        | summarize count() by Computer
        | order by count_ desc
    """,
    "cluster": "security-cluster"
}
result = await kusto_client.execute_tool(arguments)

# Complex analytics query
arguments = {
    "operation": "execute_query",
    "database": "TelemetryDB",
    "query": """
        AppTraces
        | where TimeGenerated between (ago(24h) .. now())
        | where SeverityLevel >= 3
        | summarize
            ErrorCount = count(),
            UniqueUsers = dcount(UserId)
          by bin(TimeGenerated, 1h), AppName
        | order by TimeGenerated desc
    """
}
result = await kusto_client.execute_tool(arguments)
```

### Programmatic Usage

```python
# Direct method call with custom formatting
kusto_client = KustoClient()

# Get raw results for programmatic processing
result = await kusto_client.execute_query(
    database="MyDatabase",
    query="MyTable | count",
    format_results=False  # Returns raw KustoResponseDataSet
)

# Access raw data
if result["success"]:
    raw_response = result["raw_response"]
    primary_results = result["primary_results"]
    tables = result["tables"]
```

## Tool Reference

### execute_query

Execute a KQL query against an Azure Data Explorer database.

**Parameters:**
- `operation` (required): Must be "execute_query"
- `database` (required): Name of the database to query
- `query` (required): KQL query to execute
- `cluster` (optional): Cluster URL or name (uses configured default if not provided)
- `format_results` (optional): Whether to format results for LLM analysis (default: true)

**Response Format:**
```python
{
    "success": bool,
    "result": str,  # Formatted query results (when format_results=True)
    "error_type": str,  # Present if success=False
    "traceback": str  # Present if success=False for debugging
}
```

**Raw Response Format** (when `format_results=False`):
```python
{
    "success": bool,
    "raw_response": KustoResponseDataSet,
    "primary_results": List[KustoTable],
    "tables": List[KustoTable]
}
```

## Cluster URL Formats

The plugin accepts various cluster URL formats and automatically normalizes them:

```python
# Full URL (preferred)
"https://mycluster.kusto.windows.net"

# Domain without protocol
"mycluster.kusto.windows.net"

# Cluster name only
"mycluster"
```

All formats are converted to: `https://mycluster.kusto.windows.net`

## KQL Query Examples

### Basic Data Exploration

```kql
// Get table schema
MyTable | getschema

// Sample data
MyTable | take 100

// Count records
MyTable | count

// Recent data
MyTable
| where TimeGenerated > ago(1h)
| limit 50
```

### Analytics and Aggregations

```kql
// Time-based analysis
MyTable
| where TimeGenerated > ago(24h)
| summarize count() by bin(TimeGenerated, 1h)
| render timechart

// Top N analysis
MyTable
| summarize total = count() by Category
| top 10 by total desc

// Statistical analysis
MyTable
| summarize
    avg_value = avg(NumericColumn),
    percentiles(NumericColumn, 50, 95, 99)
by Category
```

### Advanced Queries

```kql
// Join operations
Table1
| join kind=inner (
    Table2
    | where Condition == "value"
) on CommonColumn

// Window functions
MyTable
| extend
    prev_value = prev(Value, 1),
    running_total = row_cumsum(Value)
| where TimeGenerated > ago(1d)

// Complex filtering and transformations
MyTable
| where TimeGenerated between (datetime(2024-01-01) .. datetime(2024-01-31))
| extend parsed_data = parse_json(JsonColumn)
| extend category = tostring(parsed_data.category)
| summarize count() by category, bin(TimeGenerated, 1d)
```

## Error Handling

The plugin provides comprehensive error handling with specific error types:

### Common Error Types

- **`ValueError`**: Configuration issues (missing cluster URL, database)
- **`KustoServiceError`**: Query execution errors, authentication failures
- **`Exception`**: General errors during execution

### Error Response Example

```python
{
    "success": False,
    "result": "Query execution failed: Syntax error at line 2",
    "error_type": "KustoServiceError",
    "error_code": "BadRequest",
    "error_category": "UserError",
    "traceback": "Full stack trace..."
}
```

## Best Practices

### Query Optimization

1. **Use time filters**: Always filter by time ranges for better performance
2. **Limit results**: Use `limit` or `take` for exploratory queries
3. **Project early**: Select only needed columns with `project`
4. **Use summarize**: Aggregate data instead of returning raw records when possible

### Security

1. **Use Service Principal**: For production environments
2. **Limit permissions**: Grant minimum required database permissions
3. **Protect credentials**: Store authentication details in environment variables
4. **Query validation**: Validate and sanitize dynamic query inputs

### Performance

1. **Connection reuse**: The client automatically manages connections
2. **Batch operations**: Combine multiple related queries when possible
3. **Monitor query cost**: Use `.show queries` to monitor resource usage
4. **Use materialized views**: For frequently accessed aggregated data

## Troubleshooting

### Authentication Issues

```bash
# Verify Azure CLI login
az account show

# Test cluster connectivity
az kusto cluster show --name <cluster-name> --resource-group <rg-name>

# Check permissions
az kusto database show --cluster-name <cluster> --name <database> --resource-group <rg>
```

### Common Solutions

1. **"Cluster URL not found"**: Ensure `KUSTO_CLUSTER_URL` is set
2. **Authentication failed**: Check credentials and permissions
3. **Database not found**: Verify database name and access permissions
4. **Query timeout**: Optimize query or increase timeout settings
5. **Syntax errors**: Validate KQL syntax in Azure Data Explorer portal

## Dependencies

This plugin depends on:
- `azure-kusto-data`: Azure Data Explorer client library
- `azure-identity`: Azure authentication library
- `mcp_tools.interfaces.ToolInterface`: MCP tool interface
- `mcp_tools.interfaces.KustoClientInterface`: Kusto-specific interface
- `config.env`: Environment configuration manager

## Development

### Running Tests

```bash
# Run all tests
python -m pytest plugins/kusto/tests/

# Run with coverage
python -m pytest plugins/kusto/tests/ --cov=plugins.kusto

# Run specific test
python -m pytest plugins/kusto/tests/test_kusto_client.py::test_format_results
```

### Adding New Features

1. Extend the `KustoClient` class
2. Update the input schema for new parameters
3. Add comprehensive tests
4. Update this documentation

## Examples

### Log Analysis

```python
# Analyze error logs
arguments = {
    "operation": "execute_query",
    "database": "ApplicationLogs",
    "query": """
        AppTraces
        | where TimeGenerated > ago(24h)
        | where SeverityLevel >= 3
        | summarize count() by bin(TimeGenerated, 1h), SeverityLevel
        | order by TimeGenerated desc
    """
}
```

### Performance Monitoring

```python
# Monitor request performance
arguments = {
    "operation": "execute_query",
    "database": "Metrics",
    "query": """
        RequestMetrics
        | where TimeGenerated > ago(1h)
        | summarize
            avg_duration = avg(Duration),
            p95_duration = percentile(Duration, 95),
            request_count = count()
        by bin(TimeGenerated, 5m), Endpoint
        | order by TimeGenerated desc
    """
}
```

### Security Analysis

```python
# Analyze security events
arguments = {
    "operation": "execute_query",
    "database": "SecurityLogs",
    "query": """
        SecurityEvent
        | where TimeGenerated > ago(24h)
        | where EventID in (4625, 4648, 4656)  // Failed logons and suspicious activities
        | summarize
            event_count = count(),
            unique_accounts = dcount(TargetAccount)
        by bin(TimeGenerated, 1h), Computer, EventID
        | where event_count > 10  // Filter for significant activity
        | order by TimeGenerated desc
    """
}
```
