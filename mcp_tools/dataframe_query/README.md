# DataFrame Query Tool

A dedicated tool for querying and manipulating stored DataFrames by ID within the MCP framework.

## Purpose

This tool enables users to perform interactive data exploration on large DataFrames that have been stored by other tools (like Kusto queries, CSV imports, etc.) without having to reload the data. It provides a set of common DataFrame operations for data analysis and exploration.

## Supported Operations

- **head**: Get the first n rows of a DataFrame
- **tail**: Get the last n rows of a DataFrame
- **sample**: Get a random sample of rows from a DataFrame
- **filter**: Filter DataFrame rows based on conditions
- **describe**: Generate descriptive statistics for the DataFrame
- **info**: Get DataFrame info including column types and memory usage

## Usage

The tool accepts the following parameters:

- `dataframe_id` (required): The ID of the stored DataFrame to query
- `operation` (required): The operation to perform (head, tail, sample, filter, describe, info)
- `parameters` (optional): Operation-specific parameters

### Examples

```json
{
  "dataframe_id": "dataframe-abc123",
  "operation": "head",
  "parameters": {"n": 10}
}
```

```json
{
  "dataframe_id": "dataframe-abc123",
  "operation": "filter",
  "parameters": {
    "conditions": {
      "age": {"gt": 30},
      "status": "active"
    }
  }
}
```

## Integration

This tool integrates with the DataFrame management framework located in `utils/dataframe_manager` and requires DataFrames to be stored using that system before they can be queried.

## Dependencies

- pandas: For DataFrame operations
- utils.dataframe_manager: For DataFrame storage and retrieval
