# Supported MCP Tools Overview

This document provides a high-level overview of the core MCP tools available in the `mcp_tools` directory. Each section describes the functionality and usage of a major tool. For detailed API documentation, see the code comments and docstrings in each module.

---

## Azure Repo Client (`AzureRepoClient`)

**Functionality:**
- Interacts with Azure DevOps Repositories using Azure CLI commands.
- Manages pull requests and repository operations programmatically.

**Usage:**
- Main class: `AzureRepoClient(command_executor)`
- Key operations: `list_pull_requests`, `get_pull_request`, `create_pull_request`, `update_pull_request`, `set_vote`, `add_reviewers`, `add_work_items`.
- Input: Repository/project/PR identifiers and parameters.
- Output: Structured results from Azure DevOps.

---

## Browser Client (`BrowserClient`)

**Functionality:**
- Provides browser automation for web scraping, testing, and screenshot capture.
- Supports operations such as opening web pages, extracting HTML/Markdown, and taking screenshots.

**Usage:**
- Main class: `BrowserClient(browser_type, client_type)`
- Key operations: `get_page_html`, `take_screenshot`, `get_page_markdown`, `capture_panels`.
- Input: URL and operation-specific parameters.
- Output: HTML, Markdown, screenshots, or panel images.

---

## Command Executor (`CommandExecutor`)

**Functionality:**
- Executes shell commands synchronously or asynchronously, capturing output and errors.
- Supports process monitoring, termination, and status queries.

**Usage:**
- Main class: `CommandExecutor()`
- Key operations: `execute`, `execute_async`, `get_process_status`, `terminate_process`.
- Input: Shell command and optional timeout.
- Output: Execution results, process tokens, and logs.

---

## Kusto Client (`KustoClient`)

**Functionality:**
- Connects to Azure Data Explorer (Kusto) clusters and executes KQL queries.
- Handles authentication and result formatting for downstream analysis.

**Usage:**
- Main class: `KustoClient()`
- Key operation: `execute_query(database, query, cluster, format_results)`
- Input: Database, KQL query, (optional) cluster URL.
- Output: Query results (formatted or raw).

---

## Time Tool (`TimeTool`)

**Functionality:**
- Provides current time or shifted time based on a delta string (e.g., '5m', '2d').
- Supports timezone-aware results.

**Usage:**
- Main class: `TimeTool()`
- Key operation: `get_time(time_point, delta, timezone)`
- Input: Optional base time, delta, and timezone.
- Output: Time string in the specified timezone.

---

For more details, see the source code and inline documentation in each tool's module.
