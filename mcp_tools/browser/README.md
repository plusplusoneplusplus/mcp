# Browser Tool Setup

This document outlines the requirements and setup instructions for using the `BrowserClient` tool for web automation.

## Requirements

- Google Chrome browser
- ChromeDriver executable 
- Python packages:
  - selenium
  - webdriver-manager

## Installation

### 1. Install Google Chrome

#### Windows
Download and install from [https://www.google.com/chrome/](https://www.google.com/chrome/)

#### macOS
```
brew install --cask google-chrome
```

#### Linux (Ubuntu/Debian)
```
sudo apt update
sudo apt install google-chrome-stable
```

### 2. Install ChromeDriver

#### Option 1: Using webdriver-manager (Recommended)
The tool uses `webdriver-manager` to automatically handle ChromeDriver installation.
```
pip install webdriver-manager
```

#### Option 2: Manual installation

##### Windows
1. Check your Chrome version: Open Chrome and go to Settings > About Chrome
2. Download matching ChromeDriver from [https://chromedriver.chromium.org/downloads](https://chromedriver.chromium.org/downloads)
3. Extract and add to PATH

##### macOS
```
brew install chromedriver
```

##### Linux (Ubuntu/Debian)
```
sudo apt install chromium-chromedriver
```

### 3. Install Python Packages
```
pip install selenium webdriver-manager
```

## WSL-specific Setup

If using Windows Subsystem for Linux:

1. Install Chrome in Windows (not WSL)
2. Install ChromeDriver in WSL:
   ```
   sudo apt install chromium-chromedriver
   ```
3. For non-headless mode, you'll need an X server running in Windows

## Troubleshooting

If you encounter issues:

1. Ensure Chrome is properly installed
2. Verify ChromeDriver is installed and matches your Chrome version
3. Try killing any existing Chrome processes:
   - Windows: `taskkill /F /IM chrome.exe`
   - WSL/Linux: `pkill chrome`
4. Check that the paths in the code match your system configuration

## Usage Example

```python
from mcp_tools.browser.client import BrowserClient

# Get HTML from a webpage
html = BrowserClient.get_page_html("https://example.com")

# Take a screenshot of a webpage
BrowserClient.take_screenshot("https://example.com", "screenshot.png")
``` 