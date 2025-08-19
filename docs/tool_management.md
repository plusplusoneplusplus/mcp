# Tool Management Guide

This guide explains how to enable and disable tools in the MCP (Model Context Protocol) system. The MCP system provides multiple methods for controlling which tools are available and active.

## Overview

The MCP system supports two types of tools:
- **Code-based tools**: Python classes that implement the `ToolInterface`
- **YAML-based tools**: Tools defined in YAML configuration files

Tools can be controlled through:
1. Environment variables (startup configuration)
2. YAML configuration files
3. Runtime administration via the MCP Admin tool

## Configuration Methods

### 1. Environment Variables

Environment variables provide the primary method for configuring tool availability at startup. These are typically set in your `.env` file based on the template in `config/env.template`.

#### Plugin Enable/Disable Configuration

```bash
# Mode for plugin filtering: "all" (default), "whitelist", or "blacklist"
MCP_PLUGIN_MODE=all

# Comma-separated list of plugins to enable (used with whitelist mode)
MCP_ENABLED_PLUGINS=tool1,tool2,tool3

# Comma-separated list of plugins to disable (used with blacklist mode)
MCP_DISABLED_PLUGINS=tool4,tool5
```

**Plugin Modes:**
- `all`: Enable all discovered tools (default behavior)
- `whitelist`: Only enable explicitly listed tools in `MCP_ENABLED_PLUGINS`
- `blacklist`: Enable all tools except those listed in `MCP_DISABLED_PLUGINS`

#### Tool Source Configuration

```bash
# Whether to register code-based tools (default: true)
MCP_REGISTER_CODE_TOOLS=true

# Whether to register YAML-based tools (default: true)
MCP_REGISTER_YAML_TOOLS=true

# Whether YAML definitions should override code tools (default: true)
MCP_YAML_OVERRIDES_CODE=true
```

#### Tool Discovery Configuration

```bash
# Comma-separated list of additional plugin root directories
MCP_PLUGIN_ROOTS=/path/to/custom/plugins,/path/to/other/plugins

# Comma-separated list of additional YAML tool paths
MCP_YAML_TOOL_PATHS=/path/to/tools.yaml,/path/to/other/tools.yaml

# Comma-separated list of base classes to exclude from registration
MCP_EXCLUDED_BASE_CLASSES=CustomBaseClass,AnotherBaseClass

# Comma-separated list of tool names to exclude from registration
MCP_EXCLUDED_TOOL_NAMES=unwanted_tool,deprecated_tool
```

#### Ecosystem and OS Filtering

```bash
# Ecosystems to enable: "*" for all (default) or comma-separated list
# Available ecosystems: microsoft, general, open-source
MCP_ECOSYSTEMS=*

# OS types to enable: "*" for all, comma-separated list, or leave empty for auto-detection
# Available OS types: windows, non-windows, all
MCP_OS=*
```

### 2. YAML Configuration Files

#### Tools Configuration (`server/tools.yaml`)

Individual tools can be enabled or disabled in the YAML configuration:

```yaml
tools:
  execute_command_async:
    enabled: false  # Disable this tool
    name: execute_command_async
    category: command
    description: |
      Start a command execution asynchronously and return a token for tracking.
    # ... rest of tool definition

  execute_task:
    enabled: true   # Enable this tool
    name: execute_task
    category: task
    description: |
      Execute a predefined task by name and start it asynchronously.
    # ... rest of tool definition
```

#### Plugin Configuration (`plugin_config.yaml`)

External plugins can be configured for installation and management:

```yaml
plugins:
  - plugin_repo: "plusplusoneplusplus/mcp"
    sub_dir: "plugin/logcli"
    type: "python"
  - plugin_repo: "tcauth/boltx_deploy"
    type: "python"
```

### 3. Runtime Administration

The MCP Admin tool (`mcp_admin`) allows you to enable/disable tools at runtime without restarting the server.

#### Available Operations

1. **Enable a plugin:**
   ```json
   {
     "operation": "enable_plugin",
     "plugin": "tool_name"
   }
   ```

2. **Disable a plugin:**
   ```json
   {
     "operation": "disable_plugin",
     "plugin": "tool_name"
   }
   ```

3. **Refresh plugins:**
   ```json
   {
     "operation": "refresh_plugins",
     "force": false
   }
   ```

## Practical Examples

### Example 1: Whitelist Mode (Only Specific Tools)

```bash
# Enable only specific tools
MCP_PLUGIN_MODE=whitelist
MCP_ENABLED_PLUGINS=execute_task,list_tasks,dataframe_query,browser_get_page
```

### Example 2: Blacklist Mode (Exclude Specific Tools)

```bash
# Enable all tools except specified ones
MCP_PLUGIN_MODE=blacklist
MCP_DISABLED_PLUGINS=execute_command_async,unsafe_tool,deprecated_tool
```

### Example 3: Ecosystem-Specific Configuration

```bash
# Only enable Microsoft ecosystem tools
MCP_ECOSYSTEMS=microsoft

# Only enable open-source tools
MCP_ECOSYSTEMS=open-source

# Enable multiple ecosystems
MCP_ECOSYSTEMS=microsoft,general
```

### Example 4: OS-Specific Configuration

```bash
# Auto-detect OS and load appropriate tools (default)
# MCP_OS=  (empty or unset)

# Force enable all OS types
MCP_OS=*

# Only Windows tools
MCP_OS=windows

# Only non-Windows tools (macOS/Linux)
MCP_OS=non-windows
```

### Example 5: Development vs Production

**Development Environment:**
```bash
# Enable all tools for development
MCP_PLUGIN_MODE=all
MCP_REGISTER_CODE_TOOLS=true
MCP_REGISTER_YAML_TOOLS=true
```

**Production Environment:**
```bash
# Strict whitelist for production
MCP_PLUGIN_MODE=whitelist
MCP_ENABLED_PLUGINS=execute_task,query_task_status,dataframe_query
MCP_REGISTER_CODE_TOOLS=false  # Only YAML-defined tools
```

### Example 6: Custom Tool Paths

```bash
# Add custom plugin directories
MCP_PLUGIN_ROOTS=/opt/company-tools,/home/user/custom-tools

# Add custom YAML tool definitions
MCP_YAML_TOOL_PATHS=/etc/mcp/company-tools.yaml,/opt/tools/external.yaml
```

## Tool Priority and Overrides

The system follows this priority order:

1. **Explicit disable** (via `MCP_DISABLED_PLUGINS` or runtime disable) - highest priority
2. **Explicit enable** (via `MCP_ENABLED_PLUGINS` or runtime enable)
3. **Mode-based filtering** (whitelist/blacklist/all)
4. **Source-based filtering** (code vs YAML tools)
5. **Ecosystem filtering**
6. **OS filtering** - lowest priority

### YAML Override Behavior

When `MCP_YAML_OVERRIDES_CODE=true` (default):
- If both a code-based tool and YAML-based tool have the same name
- The YAML definition takes precedence
- The code-based tool is not registered

## Monitoring and Debugging

### Check Available Plugins

Use the plugin registry API to see all available plugins:

```bash
curl http://localhost:8000/api/tools
```

### View Plugin Status

Each plugin in the API response includes:
- `enabled`: Whether the plugin is currently enabled
- `registered`: Whether the plugin is registered in the system
- `explicitly_configured`: Whether the plugin has explicit enable/disable configuration
- `source`: Whether the plugin comes from "code" or "yaml"
- `ecosystem`: The plugin's ecosystem (if specified)
- `os`: The plugin's OS compatibility

### Logging

Enable debug logging to see tool discovery and registration details:

```bash
export LOG_LEVEL=DEBUG
```

## Best Practices

1. **Use environment variables** for permanent configuration
2. **Use YAML enabled/disabled flags** for tool-specific control
3. **Use runtime admin operations** for temporary changes
4. **Use whitelist mode in production** for security
5. **Test configurations** in development before deploying
6. **Document custom configurations** for team members
7. **Monitor tool usage** to optimize enabled tool sets

## Troubleshooting

### Tool Not Appearing

1. Check if the tool source is enabled (`MCP_REGISTER_CODE_TOOLS`/`MCP_REGISTER_YAML_TOOLS`)
2. Verify the tool isn't in the disabled list (`MCP_DISABLED_PLUGINS`)
3. Check ecosystem and OS filtering
4. Look for registration errors in logs

### Tool Not Working After Enable

1. Restart the server if using environment variable changes
2. Use the `refresh_plugins` operation to reload tools
3. Check for dependency issues in logs
4. Verify tool definition syntax in YAML files

### Performance Issues

1. Disable unused tools to reduce memory usage
2. Use ecosystem filtering to load only relevant tools
3. Consider using whitelist mode in production
4. Monitor tool execution times and disable slow tools if needed

## Security Considerations

- Use whitelist mode in production environments
- Regularly audit enabled tools
- Disable development/debug tools in production
- Monitor tool usage for unusual activity
- Keep tool definitions up to date
- Use ecosystem filtering to avoid unnecessary external dependencies
