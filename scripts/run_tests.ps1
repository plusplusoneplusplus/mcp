# Script to run all tests in the MCP project
# This will run tests for mcp_core, mcp_tools, and any other tests in the project
#
# Usage:
#   ./run_tests.ps1 [test_pattern] [--parallel|-p] [max_jobs]
#
#   test_pattern: Optional pytest pattern to filter tests (e.g., "test_async")
#   --parallel|-p: Run test components in parallel for faster execution
#   max_jobs: Maximum number of concurrent test components (default: 4)
#
# Examples:
#   ./run_tests.ps1                    # Run all tests sequentially
#   ./run_tests.ps1 "" --parallel      # Run all tests in parallel (4 jobs)
#   ./run_tests.ps1 "" -p 8            # Run all tests in parallel (8 jobs)
#   ./run_tests.ps1 "test_async" -p 2  # Run async tests in parallel (2 jobs)

# We'll continue execution even if a test fails
$ErrorActionPreference = "Continue"

# Define colors for output
function Write-ColorMessage {
    param(
        [string]$Message,
        [string]$Color = "White"
    )

    $originalColor = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $Color
    Write-Host $Message
    $host.UI.RawUI.ForegroundColor = $originalColor
}

Write-ColorMessage "=== Running all tests for MCP project ===" "Blue"
Write-Host ""

# Initialize counters
$failures = 0
$passed = 0
$skipped = 0

# Function to run tests for a specific component
function Run-ComponentTests {
    param(
        [string]$Component,
        [string]$TestPath,
        [string]$TestPattern = ""
    )

    if (Test-Path $TestPath -PathType Container) {
        Write-ColorMessage "Running tests for $Component..." "Blue"

        # Run the tests and capture output
        try {
            # Use uv instead of python directly with parallel execution
            if ($TestPattern -ne "") {
                $output = & uv run python -m pytest "$TestPath" -k "$TestPattern" -n auto 2>&1 | Out-String
            } else {
                $output = & uv run python -m pytest "$TestPath" -n auto 2>&1 | Out-String
            }
            $exitCode = $LASTEXITCODE

            # Print the output
            Write-Host $output

            # Parse output to get test statistics
            if ($output -match "no tests ran") {
                Write-ColorMessage "! No tests ran for $Component" "Yellow"
                $script:skipped++
            }
            elseif ($output -match "collected \d+ items / \d+ deselected / 0 selected") {
                Write-ColorMessage "No matching tests for $Component, skipping." "Yellow"
                $script:skipped++
            }
            elseif (($exitCode -ne 0) -or ($output -match "ERROR") -or ($output -match "FAILED")) {
                # Get summary of failures/passed/skipped from the output
                if ($output -match "(\d+) failed, (\d+) passed, (\d+) skipped") {
                    $summary = $Matches[0]
                    Write-ColorMessage "X Some tests for $Component failed: $summary" "Red"
                }
                elseif (($output -match "ERROR") -and ($output -match "Interrupted")) {
                    Write-ColorMessage "X Tests for $Component failed due to import errors or collection failures" "Red"
                }
                else {
                    Write-ColorMessage "X Tests for $Component failed!" "Red"
                }
                $script:failures++
            }
            else {
                Write-ColorMessage "+ All tests for $Component passed!" "Green"
                $script:passed++
            }
        }
        catch {
            $errorMessage = $_.Exception.Message
            Write-ColorMessage "X Error running tests for ${Component}: $errorMessage" "Red"
            $script:failures++
        }
        Write-Host ""
    }
    else {
        Write-ColorMessage "No tests found for $Component at $TestPath" "Yellow"
        Write-Host ""
        $script:skipped++
    }
}

# Function to run tests for a specific component in parallel
function Run-ComponentTestsParallel {
    param(
        [string]$Component,
        [string]$TestPath,
        [string]$TestPattern = "",
        [string]$ResultFile
    )

    if (Test-Path $TestPath -PathType Container) {
        Write-Host "Starting tests for $Component..."

        # Run the tests and capture output
        try {
            # Use uv instead of python directly with parallel execution
            if ($TestPattern -ne "") {
                $output = & uv run python -m pytest "$TestPath" -k "$TestPattern" -n auto 2>&1 | Out-String
            } else {
                $output = & uv run python -m pytest "$TestPath" -n auto 2>&1 | Out-String
            }
            $exitCode = $LASTEXITCODE

            # Write results to file
            "COMPONENT:$Component" | Out-File -FilePath $ResultFile -Encoding UTF8
            "EXIT_CODE:$exitCode" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
            "OUTPUT_START" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
            $output | Out-File -FilePath $ResultFile -Append -Encoding UTF8
            "OUTPUT_END" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
        }
        catch {
            $errorMessage = $_.Exception.Message
            "COMPONENT:$Component" | Out-File -FilePath $ResultFile -Encoding UTF8
            "EXIT_CODE:1" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
            "OUTPUT_START" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
            "Error running tests: $errorMessage" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
            "OUTPUT_END" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
        }
    }
    else {
        "COMPONENT:$Component" | Out-File -FilePath $ResultFile -Encoding UTF8
        "EXIT_CODE:404" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
        "OUTPUT_START" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
        "No tests found for $Component at $TestPath" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
        "OUTPUT_END" | Out-File -FilePath $ResultFile -Append -Encoding UTF8
    }
}

# Function to process results from parallel execution
function Process-ParallelResults {
    param([string]$ResultFile)

    $content = Get-Content $ResultFile -Raw
    $lines = $content -split "`n"

    $component = ($lines | Where-Object { $_ -match "^COMPONENT:" }) -replace "^COMPONENT:", ""
    $exitCode = ($lines | Where-Object { $_ -match "^EXIT_CODE:" }) -replace "^EXIT_CODE:", ""

    # Extract output between OUTPUT_START and OUTPUT_END
    $startIndex = [array]::IndexOf($lines, "OUTPUT_START")
    $endIndex = [array]::IndexOf($lines, "OUTPUT_END")

    if ($startIndex -ge 0 -and $endIndex -gt $startIndex) {
        $output = $lines[($startIndex + 1)..($endIndex - 1)] -join "`n"
    } else {
        $output = ""
    }

    Write-ColorMessage "Results for $component:" "Blue"
    Write-Host $output

    if ($exitCode -eq "404") {
        Write-ColorMessage "No tests found for $component" "Yellow"
        $script:skipped++
    }
    elseif ($output -match "no tests ran") {
        Write-ColorMessage "! No tests ran for $component" "Yellow"
        $script:skipped++
    }
    elseif ($output -match "collected \d+ items / \d+ deselected / 0 selected") {
        Write-ColorMessage "No matching tests for $component, skipping." "Yellow"
        $script:skipped++
    }
    elseif (($exitCode -ne "0") -or ($output -match "ERROR") -or ($output -match "FAILED")) {
        if ($output -match "(\d+) failed, (\d+) passed, (\d+) skipped") {
            $summary = $Matches[0]
            Write-ColorMessage "X Some tests for $component failed: $summary" "Red"
        }
        elseif (($output -match "ERROR") -and ($output -match "Interrupted")) {
            Write-ColorMessage "X Tests for $component failed due to import errors or collection failures" "Red"
        }
        else {
            Write-ColorMessage "X Tests for $component failed!" "Red"
        }
        $script:failures++
    }
    else {
        Write-ColorMessage "+ All tests for $component passed!" "Green"
        $script:passed++
    }
    Write-Host ""
}

# Parse optional test pattern argument, parallel flag, and max parallel jobs
$TestPattern = if ($args.Count -ge 1) { $args[0] } else { "" }
$ParallelMode = if ($args.Count -ge 2) { $args[1] } else { "" }
$MaxParallelJobs = if ($args.Count -ge 3) { [int]$args[2] } else { 4 }  # Default to 4 parallel jobs

# Check if parallel mode is requested
if (($ParallelMode -eq "--parallel") -or ($ParallelMode -eq "-p")) {
    Write-ColorMessage "Running tests in parallel mode (max $MaxParallelJobs concurrent jobs)..." "Blue"
    Write-Host ""

    # Create temporary directory for results
    $tempDir = [System.IO.Path]::GetTempPath() + [System.Guid]::NewGuid().ToString()
    New-Item -ItemType Directory -Path $tempDir | Out-Null

    # Define test components
    $components = @(
        @{Name="config"; Path="config/tests"},
        @{Name="mcp_core"; Path="mcp_core/tests"},
        @{Name="mcp_tools"; Path="mcp_tools/tests"},
        @{Name="server"; Path="server/tests"},
        @{Name="utils.html_to_markdown"; Path="utils/html_to_markdown/tests"},
        @{Name="utils.vector_store"; Path="utils/vector_store/tests"},
        @{Name="utils.secret_scanner"; Path="utils/secret_scanner/tests"},
        @{Name="utils.ocr_extractor"; Path="utils/ocr_extractor/tests"},
        @{Name="utils.playwright"; Path="utils/playwright/tests"},
        @{Name="plugins.azrepo"; Path="plugins/azrepo/tests"},
        @{Name="plugins.kusto"; Path="plugins/kusto/tests"},
        @{Name="plugins.git_tool"; Path="plugins/git_tool/tests"},
        @{Name="plugins.knowledge_indexer"; Path="plugins/knowledge_indexer/tests"}
    )

    # Add project-level tests if they exist
    if (Test-Path "tests" -PathType Container) {
        $components += @{Name="project"; Path="tests"}
    }

    # Start background jobs with thread limiting
    $jobs = @()
    $resultFiles = @()

    foreach ($component in $components) {
        $resultFile = Join-Path $tempDir "result_$($component.Name -replace '[./]', '_').txt"
        $resultFiles += $resultFile

        # Wait for available slot before starting new job
        while (($jobs | Where-Object { $_.State -eq "Running" }).Count -ge $MaxParallelJobs) {
            Start-Sleep -Milliseconds 100
            # Clean up completed jobs
            $jobs = $jobs | Where-Object { $_.State -ne "Completed" -and $_.State -ne "Failed" -and $_.State -ne "Stopped" }
        }

        $runningCount = ($jobs | Where-Object { $_.State -eq "Running" }).Count
        Write-ColorMessage "Starting $($component.Name) ($runningCount/$MaxParallelJobs slots used)..." "Blue"

        $job = Start-Job -ScriptBlock {
            param($ComponentName, $TestPath, $TestPattern, $ResultFile, $FunctionDef)

            # Define the function in the job context
            Invoke-Expression $FunctionDef

            Run-ComponentTestsParallel -Component $ComponentName -TestPath $TestPath -TestPattern $TestPattern -ResultFile $ResultFile
        } -ArgumentList $component.Name, $component.Path, $TestPattern, $resultFile, ${function:Run-ComponentTestsParallel}.ToString()

        $jobs += $job
    }

    # Wait for all jobs to complete
    Write-ColorMessage "Waiting for all test suites to complete..." "Blue"
    $jobs | Wait-Job | Out-Null

    # Clean up jobs
    $jobs | Remove-Job

    # Process and display results
    Write-ColorMessage "Processing results..." "Blue"
    Write-Host ""

    foreach ($resultFile in $resultFiles) {
        if (Test-Path $resultFile) {
            Process-ParallelResults -ResultFile $resultFile
        }
    }

    # Clean up temporary directory
    Remove-Item -Path $tempDir -Recurse -Force

} else {
    # Original sequential mode
    Write-ColorMessage "Running tests in sequential mode..." "Blue"
    Write-Host ""

    # Run tests for each component
    Run-ComponentTests "config" "config/tests" $TestPattern
    Run-ComponentTests "mcp_core" "mcp_core/tests" $TestPattern
    Run-ComponentTests "mcp_tools" "mcp_tools/tests" $TestPattern
    Run-ComponentTests "server" "server/tests" $TestPattern
    Run-ComponentTests "utils.html_to_markdown" "utils/html_to_markdown/tests" $TestPattern
    Run-ComponentTests "utils.vector_store" "utils/vector_store/tests" $TestPattern
    Run-ComponentTests "utils.secret_scanner" "utils/secret_scanner/tests" $TestPattern
    Run-ComponentTests "utils.ocr_extractor" "utils/ocr_extractor/tests" $TestPattern
    Run-ComponentTests "utils.playwright" "utils/playwright/tests" $TestPattern

    # Run tests for plugins
    Run-ComponentTests "plugins.azrepo" "plugins/azrepo/tests" $TestPattern
    Run-ComponentTests "plugins.kusto" "plugins/kusto/tests" $TestPattern
    Run-ComponentTests "plugins.git_tool" "plugins/git_tool/tests" $TestPattern
    Run-ComponentTests "plugins.knowledge_indexer" "plugins/knowledge_indexer/tests" $TestPattern
    # Add more plugin components as needed

    # Run project-level tests if they exist
    if (Test-Path "tests" -PathType Container) {
        Run-ComponentTests "project" "tests" $TestPattern
    }
}

# Print summary
Write-ColorMessage "=== Test Summary ===" "Blue"
if ($failures -gt 0) {
    Write-ColorMessage "$failures test suite(s) had failures!" "Red"
}
elseif ($passed -eq 0) {
    Write-ColorMessage "No test suites were executed successfully." "Yellow"
}
else {
    Write-ColorMessage "All $passed test suite(s) completed successfully!" "Green"
}

if ($skipped -gt 0) {
    Write-ColorMessage "$skipped test suite(s) were skipped." "Yellow"
}

# Exit with error code if any failures
if ($failures -gt 0) {
    exit 1
}

exit 0
