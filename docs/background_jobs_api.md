# Background Jobs REST API

The server exposes endpoints for querying running or completed background commands executed by the `CommandExecutor` tool.

## List Jobs

`GET /api/background-jobs`

Query parameters:
- `status` (optional) – filter by job status (`running`, `completed`, `terminated`, `error`)
- `limit` (optional) – maximum number of jobs to return (default `50`)
- `include_completed` (optional) – include completed jobs (default `true`)

Example response:
```json
{
  "jobs": [
    {"token": "abc123...", "pid": 123, "status": "running", "command": "sleep 5"}
  ],
  "total_count": 1,
  "running_count": 1,
  "completed_count": 0
}
```

## Job Details

`GET /api/background-jobs/{token}`

Returns detailed information about a single job identified by its token.

## Job Statistics

`GET /api/background-jobs/stats`

Returns aggregate statistics about job execution including counts of running and completed jobs.
