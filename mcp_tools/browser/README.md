# Browser Tool Setup

This document outlines the requirements and setup instructions for using the `BrowserClient` tool for web automation.

## Requirements

- Google Chrome browser or Microsoft Edge browser
- ChromeDriver executable or Microsoft EdgeDriver executable
- Python packages:
  - selenium
  - webdriver-manager

## Installation

### 1. Install Browsers

#### Google Chrome

##### Windows
Download and install from [https://www.google.com/chrome/](https://www.google.com/chrome/)

##### macOS
```
brew install --cask google-chrome
```

##### Linux (Ubuntu/Debian)
```
sudo apt update
sudo apt install google-chrome-stable
```

#### Microsoft Edge

##### Windows
Microsoft Edge is typically pre-installed on modern Windows versions. You can download it from [https://www.microsoft.com/edge](https://www.microsoft.com/edge) if needed.

*(Note: macOS and Linux setup for Edge is possible but less common for this tool's typical use cases.)*


### 2. Install WebDrivers

#### Option 1: Using webdriver-manager (Recommended)
The tool uses `webdriver-manager` to automatically handle ChromeDriver and EdgeDriver installation and management. Ensure it's installed (see next step).

#### Option 2: Manual installation

##### ChromeDriver - Windows
1. Check your Chrome version: Open Chrome -> Settings -> About Chrome
2. Download matching ChromeDriver from [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)
3. Extract `chromedriver.exe` and add its directory to your system's PATH environment variable.

##### ChromeDriver - macOS
```
brew install chromedriver
```

##### ChromeDriver - Linux (Ubuntu/Debian)
```
sudo apt install chromium-chromedriver
```

##### EdgeDriver - Windows
1. Check your Edge version: Open Edge -> Settings -> About Microsoft Edge
2. Download matching EdgeDriver from [https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)
3. Extract `msedgedriver.exe` and add its directory to your system's PATH environment variable.

*(Note: Manual driver installation for Edge on macOS/Linux is generally not required if using `webdriver-manager`)*


### 3. Install Python Packages
Use `uv` (or `pip`) to install the necessary packages:
```
uv pip install selenium webdriver-manager
```

## WSL-specific Setup

If using Windows Subsystem for Linux with a browser installed on the Windows host:

1. Install Chrome or Edge in Windows (not WSL).
2. Install the corresponding WebDriver *in WSL*:
   - For Chrome: `sudo apt install chromium-chromedriver` (or let `webdriver-manager` handle it)
   - For Edge: `webdriver-manager` should handle downloading the correct EdgeDriver for Linux if needed, but you might need to point Selenium to the Windows Edge binary location. Using Chrome is often simpler in WSL scenarios.
3. For non-headless mode, you'll need an X server running in Windows (e.g., VcXsrv, X410) and configure the `DISPLAY` environment variable in WSL.

## Troubleshooting

If you encounter issues:

1. Ensure your chosen browser (Chrome or Edge) is properly installed.
2. Verify the corresponding WebDriver (ChromeDriver or EdgeDriver) is installed, accessible via PATH (if installed manually), and **matches your browser version**. `webdriver-manager` usually handles this, but version mismatches are common issues.
3. Try killing any existing browser processes:
   - Windows: `taskkill /F /IM chrome.exe` or `taskkill /F /IM msedge.exe`
   - WSL/Linux: `pkill chrome` or `pkill msedge` (may require `sudo`)
4. Check that any paths mentioned in the code (if applicable) match your system configuration.
5. Ensure `webdriver-manager` is installed and up-to-date (`uv pip install --upgrade webdriver-manager`).

## Usage Example

```python
import asyncio
from mcp_tools.browser.client import BrowserClient

async def example():
    # Get HTML from a webpage
    html = await BrowserClient.get_page_html("https://example.com")

    # Take a screenshot of a webpage
    success = await BrowserClient.take_screenshot("https://example.com", "screenshot.png")

    # Launch login page and fetch cookies after URL match
    cookies = await BrowserClient.get_cookies(
        url="https://example.com/login",
        wait_url="dashboard",
        headless=False,
    )
    print(cookies)

# Run the async example
asyncio.run(example())
```
