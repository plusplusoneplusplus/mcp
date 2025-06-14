# GitHub CLI Plugin

This plugin exposes basic GitHub functionality using the `gh` command line tool.
It can create issues and pull requests or report authentication status through
MCP's plugin system.

## Operations

- `auth_status` – Show the current authentication status.
- `issue_create` – Create a new issue given a title and body.
- `pr_create` – Create a pull request with a title, body and optional base/head.

The plugin requires the GitHub CLI (`gh`) to be installed and authenticated.
