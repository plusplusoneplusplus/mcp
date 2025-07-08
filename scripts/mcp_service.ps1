# MCP Server Windows Service Management Script
# This script provides complete service management functionality

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("install", "uninstall", "start", "stop", "restart", "status", "logs")]
    [string]$Action,

    [string]$ServiceName = "MCPServer",
    [string]$DisplayName = "MCP Server",
    [string]$Description = "MCP Server daemon service"
)

function Test-Administrator {
    return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
}

function Show-ServiceStatus {
    param($ServiceName)

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Write-Host "Service Status for '$ServiceName':"
        $service | Format-List Name, Status, StartType

        # Show process info if running
        if ($service.Status -eq "Running") {
            $process = Get-WmiObject -Class Win32_Service -Filter "Name='$ServiceName'"
            Write-Host "Process ID: $($process.ProcessId)"
        }
    } else {
        Write-Host "Service '$ServiceName' not found."
    }
}

function Show-ServiceLogs {
    $logPath = Join-Path (Get-Location) "logs\server.log"
    if (Test-Path $logPath) {
        Write-Host "Recent logs from $logPath"
        Write-Host "=" * 50
        Get-Content $logPath -Tail 20
    } else {
        Write-Host "No log file found at $logPath"
    }
}

function Install-MCPService {
    param($ServiceName, $DisplayName, $Description)

    if (-NOT (Test-Administrator)) {
        Write-Error "Installing service requires Administrator privileges!"
        exit 1
    }

    # Check if service already exists
    $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Host "Service '$ServiceName' already exists."
        return
    }

    # Get the current directory and server path
    $currentDir = Get-Location
    $serverPath = Join-Path $currentDir "server\main.py"
    $uvPath = (Get-Command uv -ErrorAction SilentlyContinue).Source

    if (-not $uvPath) {
        Write-Error "uv command not found. Please install uv first."
        exit 1
    }

    # Create service wrapper script
    $wrapperScript = @"
@echo off
cd /d "$currentDir"
"$uvPath" run ./server/main.py
"@

    $wrapperPath = Join-Path $currentDir "scripts\service_wrapper.bat"
    $wrapperScript | Out-File -FilePath $wrapperPath -Encoding ASCII

    Write-Host "Creating Windows service '$ServiceName'..."

    try {
        New-Service -Name $ServiceName -BinaryPathName $wrapperPath -DisplayName $DisplayName -Description $Description -StartupType Automatic
        Write-Host "Service '$ServiceName' created successfully!"
        Write-Host "Starting service..."
        Start-Service -Name $ServiceName
        Write-Host "Service started successfully!"
        Write-Host ""
        Show-ServiceStatus -ServiceName $ServiceName
    } catch {
        Write-Error "Failed to create service: $_"
        exit 1
    }
}

function Uninstall-MCPService {
    param($ServiceName)

    if (-NOT (Test-Administrator)) {
        Write-Error "Uninstalling service requires Administrator privileges!"
        exit 1
    }

    Write-Host "Stopping and removing Windows service '$ServiceName'..."

    try {
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($service) {
            if ($service.Status -eq "Running") {
                Write-Host "Stopping service..."
                Stop-Service -Name $ServiceName -Force
            }

            Write-Host "Removing service..."
            Remove-Service -Name $ServiceName
            Write-Host "Service '$ServiceName' removed successfully!"

            # Remove wrapper script
            $wrapperPath = Join-Path (Get-Location) "scripts\service_wrapper.bat"
            if (Test-Path $wrapperPath) {
                Remove-Item $wrapperPath -Force
                Write-Host "Wrapper script removed."
            }
        } else {
            Write-Host "Service '$ServiceName' not found."
        }
    } catch {
        Write-Error "Failed to remove service: $_"
        exit 1
    }
}

# Main script logic
switch ($Action) {
    "install" {
        Install-MCPService -ServiceName $ServiceName -DisplayName $DisplayName -Description $Description
    }
    "uninstall" {
        Uninstall-MCPService -ServiceName $ServiceName
    }
    "status" {
        Show-ServiceStatus -ServiceName $ServiceName
    }
    "start" {
        Write-Host "Pulling latest git code..."
        try {
            git pull --rebase
            Write-Host "Git pull --rebase completed successfully."
        } catch {
            Write-Warning "Git pull --rebase failed: $_"
        }

        Write-Host "Starting service '$ServiceName'..."
        Start-Service -Name $ServiceName
        Show-ServiceStatus -ServiceName $ServiceName
    }
    "stop" {
        Write-Host "Stopping service '$ServiceName'..."
        Stop-Service -Name $ServiceName
        Show-ServiceStatus -ServiceName $ServiceName
    }
    "restart" {
        Write-Host "Pulling latest git code..."
        try {
            git pull --rebase
            Write-Host "Git pull --rebase completed successfully."
        } catch {
            Write-Warning "Git pull --rebase failed: $_"
        }

        Write-Host "Restarting service '$ServiceName'..."
        Restart-Service -Name $ServiceName
        Show-ServiceStatus -ServiceName $ServiceName
    }
    "logs" {
        Show-ServiceLogs
    }
}

if ($Action -in @("install", "uninstall")) {
    Write-Host ""
    Write-Host "Available commands:"
    Write-Host "- Install: .\scripts\mcp_service.ps1 -Action install"
    Write-Host "- Start: .\scripts\mcp_service.ps1 -Action start"
    Write-Host "- Stop: .\scripts\mcp_service.ps1 -Action stop"
    Write-Host "- Restart: .\scripts\mcp_service.ps1 -Action restart"
    Write-Host "- Status: .\scripts\mcp_service.ps1 -Action status"
    Write-Host "- Logs: .\scripts\mcp_service.ps1 -Action logs"
    Write-Host "- Uninstall: .\scripts\mcp_service.ps1 -Action uninstall"
}
