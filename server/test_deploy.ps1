# PowerShell script to handle deployment parameters
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "staging", "prod")]
    [string]$environment = "dev",

    [Parameter(Mandatory=$false)]
    [string]$version = "1.0.0",

    [Parameter(Mandatory=$false)]
    [bool]$force = $false
)

# Print deployment information
Write-Host "Starting deployment process..."
Write-Host "Environment: $environment"
Write-Host "Version: $version"
Write-Host "Force deployment: $force"

# Example deployment logic
if ($force) {
    Write-Host "Force flag is set - proceeding with deployment even if version exists"
}

# Simulate deployment steps
Write-Host "`nDeployment steps:"
Write-Host "1. Validating environment configuration..."
Write-Host "2. Checking version compatibility..."
Write-Host "3. Preparing deployment package..."
Write-Host "4. Deploying to $environment environment..."
Write-Host "5. Running post-deployment checks..."

Write-Host "`nDeployment completed successfully!" 