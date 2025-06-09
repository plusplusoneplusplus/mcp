# Tool History API

The server exposes endpoints for accessing recorded tool invocations when `tool_history_enabled` is true.

## List History

`GET /api/tool-history`

Returns a list of invocation summaries.

## Invocation Details

`GET /api/tool-history/{invocation_id}`

Returns all records for the specified invocation.

## Statistics

`GET /api/tool-history/stats`

Returns aggregate statistics such as total invocations and success rate.

## Clear History

`POST /api/tool-history/clear`

Request body: `{ "confirm": true }`

Clears all recorded history.

## Export History

`GET /api/tool-history/export`

Exports all history records as JSON.
