# CircleCI Plugin

This plugin provides basic interaction with the CircleCI REST API.

## Operations

- `trigger_pipeline` – Trigger a new pipeline for a given project and branch.
- `get_pipeline_workflows` – Retrieve workflows for a specific pipeline ID.

The plugin requires a `CIRCLECI_TOKEN` environment variable containing a
CircleCI personal API token.
