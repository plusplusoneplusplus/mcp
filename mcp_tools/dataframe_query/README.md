# DataFrame Query Tool

## Overview
A dedicated tool for querying and manipulating stored DataFrames by ID within the MCP framework. Enables interactive exploration of large DataFrames stored by other tools (Kusto, CSV import, etc.) without reloading data.

---

## Features
- Query and manipulate DataFrames by ID
- Perform common DataFrame operations: head, tail, sample, filter, describe, info
- Supports complex filter conditions (gt, lt, ne, contains, etc.)
- Integrates with DataFrame management framework
- Async/await compatible
- Comprehensive error handling and validation

---

## Supported Operations
- **head**: Get the first n rows of a DataFrame
- **tail**: Get the last n rows of a DataFrame
- **sample**: Get a random sample of rows (by count or fraction)
- **filter**: Filter DataFrame rows based on conditions
- **describe**: Generate descriptive statistics
- **info**: Get DataFrame info (column types, memory usage)

---

## Supported Filter Operators
- `eq`: Equal to
- `ne`: Not equal to
- `gt`: Greater than
- `gte`: Greater than or equal to
- `lt`: Less than
- `lte`: Less than or equal to
- `contains`: Substring or value containment

---

## Usage Examples

### 1. Basic Operations

#### Get the first 10 rows
```json
{
  "dataframe_id": "my-df-123",
  "operation": "head",
  "parameters": {"n": 10}
}
```

#### Get the last 5 rows
```json
{
  "dataframe_id": "my-df-123",
  "operation": "tail",
  "parameters": {"n": 5}
}
```

#### Get a random 10% sample
```json
{
  "dataframe_id": "my-df-123",
  "operation": "sample",
  "parameters": {"frac": 0.1}
}
```

#### Describe DataFrame
```json
{
  "dataframe_id": "my-df-123",
  "operation": "describe"
}
```

#### Get DataFrame info
```json
{
  "dataframe_id": "my-df-123",
  "operation": "info"
}
```

### 2. Complex Filter Examples

#### Filter: age > 30 and status != "inactive"
```json
{
  "dataframe_id": "my-df-123",
  "operation": "filter",
  "parameters": {
    "conditions": {
      "age": {"gt": 30},
      "status": {"ne": "inactive"}
    }
  }
}
```

#### Filter: score < 50 or name contains "John"
```json
{
  "dataframe_id": "my-df-123",
  "operation": "filter",
  "parameters": {
    "conditions": {
      "score": {"lt": 50},
      "name": {"contains": "John"}
    }
  }
}
```

#### Filter: age between 18 and 65, status == "active", score != 0
```json
{
  "dataframe_id": "my-df-123",
  "operation": "filter",
  "parameters": {
    "conditions": {
      "age": {"gte": 18, "lte": 65},
      "status": {"eq": "active"},
      "score": {"ne": 0}
    }
  }
}
```

---

## Error Handling
- Clear error messages for invalid parameters, missing DataFrames, or unsupported operations
- Input validation for all parameters

---

## References
- [Tool API documentation](../docs/creating_tools.md)
- [Test suite](../tests/test_dataframe_query_tool.py)
