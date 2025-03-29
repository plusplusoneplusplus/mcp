# Sentinel

A browser automation and command execution utility for testing and monitoring.

## Setup Guide

### 1. Set up Python Virtual Environment

```bash
# Create a virtual environment
python -m venv ./venv

# Activate the virtual environment
# On Linux/Mac:
source ./venv/bin/activate

# On Windows (Command Prompt):
.\venv\Scripts\activate.bat

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
```

### 2. Install Python Dependencies

```bash
pip install -r sentinel/requirements.txt
pip install uv # for mcp server
```

> **Note for Windows Users:**
> If you encounter an error like: "Microsoft Visual C++ 14.0 or greater is required",
> install the Microsoft C++ Build Tools from:
> https://visualstudio.microsoft.com/visual-cpp-build-tools/

### 3. Install Local Sentinel Package

```bash
pip install -e ./sentinel
```

### 4. Install Browser Drivers

#### ChromeDriver

- **Linux**:
  ```bash
  apt install chromium-chromedriver
  ```

- **Windows**:
  - Download the appropriate ChromeDriver from [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/)
  - Add the directory containing the chromedriver.exe to your PATH environment variable

#### EdgeDriver (Optional)

- Follow the instructions in the [Microsoft Edge WebDriver documentation](https://learn.microsoft.com/en-us/microsoft-edge/webdriver-chromium/?tabs=python)

## Running Tests

### Using Bash Script (Linux/Mac)

```bash
# Run all tests
./sentinel/run_tests.sh
```

### Using PowerShell Script (Windows)

```powershell
# Run all tests
.\sentinel\run_tests.ps1
```

# Config MCP server as part of cursor/vscode
```json
{
    "mcpServers": {
      "mymcp": {
        "command": "mcp\\venv\\scripts\\python",
        "args": ["mcp\\server\\main.py"]
      },
      "fastmcp" : {
        "command": "mcp\\venv\\scripts\\python",
        "args": ["-m", "uv", "run", "--with", "mcp", "mcp", "run", "mcp\\server\\fast-main.py"]
      }
    }
  }
```

![MCP Server Configuration](assets/mcp-server.png)