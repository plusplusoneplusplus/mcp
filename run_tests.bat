@echo off
rem Script to run all tests in the MCP project
rem This will run tests for mcp_core, mcp_tools, and any other tests in the project

echo === Running all tests for MCP project ===
echo.

set failures=0

rem Function to run tests for a component
call :run_tests "mcp_core" "mcp_core\tests"
call :run_tests "mcp_tools" "mcp_tools\tests"

rem Run server tests if they exist
if exist "server\tests" (
    call :run_tests "server" "server\tests"
)

rem Run project tests if they exist
if exist "tests" (
    call :run_tests "project" "tests"
)

echo === Test Summary ===
if %failures%==0 (
    echo All tests passed successfully!
    exit /b 0
) else (
    echo %failures% test suite^(s^) had failures!
    exit /b 1
)

rem Test running function
:run_tests
setlocal
set component=%~1
set test_path=%~2

echo Running tests for %component%...

rem Check if directory exists
if not exist "%test_path%" (
    echo Test directory %test_path% not found. Skipping...
    echo.
    endlocal
    exit /b 1
)

rem Run the tests
python -m pytest "%test_path%" -v
if %ERRORLEVEL% == 0 (
    echo.
    echo [SUCCESS] All tests for %component% passed!
    echo.
    endlocal
    exit /b 0
) else (
    echo.
    echo [FAILED] Some tests for %component% failed!
    echo.
    set /A failures+=1
    endlocal & set failures=%failures%
    exit /b 1
) 