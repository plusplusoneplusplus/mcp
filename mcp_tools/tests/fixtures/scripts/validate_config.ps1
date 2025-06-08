# validate_config.ps1 - Configuration validation script
# This script demonstrates the post_processing feature by generating both stdout and stderr

param(
    [string]$ConfigFile = "config.yaml"
)

Write-Host "Starting configuration validation for: $ConfigFile"
Write-Host "Validation timestamp: $(Get-Date)"

# Simulate validation process with verbose output to stdout
Write-Host "Checking file existence..."
if (-not (Test-Path $ConfigFile)) {
    Write-Error "Configuration file '$ConfigFile' not found"
    exit 1
}

Write-Host "Parsing YAML structure..."
Write-Host "Validating required fields..."
Write-Host "Checking data types..."

# Simulate some warnings to stderr (these should be filtered out with attach_stderr: false)
Write-Warning "Deprecated field 'old_setting' found in config"
Write-Information "Using default value for optional field 'timeout'" -InformationAction Continue

# Simulate validation results
if ($ConfigFile -like "*invalid*") {
    Write-Error "VALIDATION FAILED: Invalid configuration detected"
    Write-Error "Missing required field 'database.host'"
    Write-Error "Invalid value for 'port': must be a number"
    exit 1
} else {
    Write-Host "Configuration validation completed successfully"
    Write-Host "All required fields present and valid"
    exit 0
}
