# Security Filtering for Script-Based Tools

## Overview

The security filtering feature automatically detects and redacts sensitive information from script outputs using the existing `utils.secret_scanner` infrastructure. This feature is integrated into the YAML tools post-processing pipeline and provides the same proven security detection used by the browser client.

## Features

- **Automatic Secret Detection**: Uses the existing secret scanner to detect passwords, API keys, tokens, and other sensitive data
- **Configurable Filtering**: Choose to filter stdout, stderr, or both
- **Security Logging**: Logs security alerts without exposing the actual secrets
- **Opt-in Security**: Disabled by default to reduce false positives, can be enabled when needed
- **Integration with Post-Processing**: Works seamlessly with existing output attachment controls

## Configuration

Security filtering is configured in the `post_processing.security_filtering` section of a tool definition:

```yaml
tools:
  my_secure_tool:
    type: script
    scripts:
      darwin: bash /path/to/script.sh
    post_processing:
             security_filtering:
         enabled: true                    # Enable security filtering (default: true)
         apply_to: ["stdout", "stderr"]   # Which outputs to filter (default: both)
         log_findings: true               # Log security alerts (default: true)
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable or disable security filtering |
| `apply_to` | array | `["stdout", "stderr"]` | Which outputs to filter. Options: `"stdout"`, `"stderr"` |
| `log_findings` | boolean | `true` | Whether to log security alerts when secrets are detected |

## Examples

### Basic Security Filtering (Default Behavior)

```yaml
deploy_app:
  type: script
  scripts:
    darwin: bash deploy.sh
  # Security filtering is disabled by default - no configuration needed for basic commands
```

### Enable Security Filtering for Sensitive Operations

```yaml
deploy_app:
  type: script
  scripts:
    darwin: bash deploy.sh
  post_processing:
    security_filtering:
      enabled: true  # Enable for deployment scripts that may handle secrets
```

### Filter Only Standard Output

```yaml
backup_database:
  type: script
  scripts:
    darwin: bash backup.sh
  post_processing:
    security_filtering:
      enabled: true
      apply_to: ["stdout"]  # Only filter stdout, allow stderr for debugging
```

### Explicitly Disable Security Filtering (Default Behavior)

```yaml
legacy_tool:
  type: script
  scripts:
    darwin: bash legacy.sh
  # Security filtering is disabled by default, but can be explicitly set
  post_processing:
    security_filtering:
      enabled: false  # Explicitly disable (same as default behavior)
```

### Silent Security Filtering

```yaml
migration_tool:
  type: script
  scripts:
    darwin: bash migrate.sh
  post_processing:
    security_filtering:
      enabled: true
      log_findings: false  # Don't log security alerts
```

### Combined with Output Attachment Controls

```yaml
secure_deployment:
  type: script
  scripts:
    darwin: bash deploy.sh
  post_processing:
    attach_stdout: true
    attach_stderr: false
    stderr_on_failure_only: true
    security_filtering:
      enabled: true
      apply_to: ["stdout", "stderr"]  # Filter both even though stderr may not be attached
```

## Security Detection

The security filtering uses the same detection algorithms as the browser client:

- **Password-like strings**: High-entropy strings with mixed character classes
- **API keys and tokens**: Common patterns for various services
- **Database connection strings**: Passwords in connection strings
- **Environment variables**: Common secret environment variable patterns
- **Custom patterns**: Extensible detection through the secret scanner

## Security Logging

When secrets are detected, the system logs security alerts without exposing the actual secrets:

```
*** SECURITY ALERT: Detected and redacted 3 potential secrets
*** Tool: deploy_app
*** Type: Script output
***
SECURITY DETAIL: Found 2 instance(s) of 'Password' at lines 1-2 in tool 'deploy_app' output
SECURITY DETAIL: Found 1 instance(s) of 'API_Key' at line 5 in tool 'deploy_app' output
```

## Integration with Existing Features

Security filtering integrates seamlessly with existing post-processing features:

1. **Security filtering is applied first** to the raw command output
2. **Output attachment controls** are applied second to determine what gets included in the final result
3. **Result formatting** happens last

This ensures that:
- Secrets are redacted even if stderr is later excluded
- Security logging captures all detected secrets regardless of attachment settings
- The filtering process is transparent to existing tools

## Best Practices

### Enable for Sensitive Operations

Always enable security filtering for tools that might handle sensitive data:

```yaml
# Database operations
db_migrate:
  post_processing:
    security_filtering:
      enabled: true

# Deployment scripts
deploy:
  post_processing:
    security_filtering:
      enabled: true

# Configuration management
update_config:
  post_processing:
    security_filtering:
      enabled: true
```

### Consider Output Filtering Strategy

Choose the appropriate filtering strategy based on your needs:

- **Both stdout and stderr**: Maximum security, filter everything
- **Stdout only**: Keep stderr for debugging while securing main output
- **Stderr only**: Secure debug output while preserving main results

### Monitor Security Logs

Regularly review security logs to:
- Identify scripts that are inadvertently exposing secrets
- Validate that security filtering is working correctly
- Improve script security practices

## Testing

The security filtering feature includes comprehensive tests:

```bash
# Run security filtering tests
cd mcp_tools
python -m pytest tests/test_security_filtering.py -v

# Test with demo tool
# The security_demo tool outputs various secrets for testing
```

## Migration Guide

**Important**: Security filtering is now disabled by default for all script-based tools. This reduces false positives while maintaining the option to enable security filtering when needed.

### For New Tools
- Security filtering is disabled by default - no configuration needed for basic commands
- Enable security filtering for tools that handle sensitive data by adding configuration
- Scripts will only have secrets redacted when explicitly enabled

### For Existing Tools
- Security filtering is now disabled by default
- Tools with explicit `security_filtering.enabled: true` will continue to work as before
- Tools with explicit `security_filtering.enabled: false` will continue to work as before
- Tools without security filtering configuration will now default to disabled

### Recommended Approach
- Enable security filtering for tools that handle sensitive operations (deployments, database operations, configuration management)
- Keep security filtering disabled for general-purpose commands to avoid false positives
- Review and enable security filtering on a per-tool basis based on the sensitivity of the operations

## Troubleshooting

### Security Filtering Not Working

1. Verify `enabled: true` is set in the configuration
2. Check that the tool type is `script`
3. Ensure the secret scanner dependencies are installed
4. Review logs for any error messages

### Too Many False Positives

1. Review the detected patterns in the logs
2. Consider filtering only specific outputs (`stdout` or `stderr`)
3. The secret scanner uses proven algorithms from the browser client

### Missing Secret Detection

1. The secret scanner uses industry-standard detection patterns
2. Very short or low-entropy secrets may not be detected
3. Consider improving script practices to avoid outputting secrets

## Related Documentation

- [Post-Processing Configuration](post_processing.md)
- [Secret Scanner Documentation](utils_overview.md#secret-scanner)
- [Browser Client Security](browser_security.md) 