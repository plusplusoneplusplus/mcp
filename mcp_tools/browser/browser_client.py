"""Browser client for web automation.

This module provides a client for browser automation operations.
"""

import time
import logging
import urllib.parse
from typing import Dict, Any, Optional, Literal

from mcp_tools.browser.factory import BrowserClientFactory
from mcp_tools.plugin import register_tool
from mcp_tools.interfaces import BrowserClientInterface
from config import env
from utils.html_to_markdown import extract_and_format_html
from utils.secret_scanner import redact_secrets


# Global configuration
DEFAULT_BROWSER_TYPE: Literal["chrome", "edge"] = env.get_setting(
    "browser_type", "chrome"
)
DEFAULT_CLIENT_TYPE: str = env.get_setting("client_type", "playwright")
MAX_RETURN_CHARS: int = 100000

# Configure logger
logger = logging.getLogger(__name__)


def _get_domain_from_url(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: The URL to extract domain from

    Returns:
        The domain part of the URL or 'unknown domain'
    """
    try:
        parsed_url = urllib.parse.urlparse(url)
        return parsed_url.netloc or "unknown domain"
    except Exception:
        return "unknown domain"


@register_tool(os_type="all")
class BrowserClient(BrowserClientInterface):
    """Client for browser automation operations.

    This class provides a simplified interface for browser operations like opening pages,
    capturing screenshots, etc. using Playwright with Chrome or Microsoft Edge.

    This class is a wrapper around the browser client implementation provided by the factory.

    Example:
        # Create a browser client
        browser = BrowserClient()

        # Get HTML content of a page
        html = browser.get_page_html("https://example.com")
    """

    def __init__(
        self, browser_type: Literal["chrome", "edge"] = None, client_type: str = None
    ):
        """Initialize the browser client.

        Args:
            browser_type: Type of browser to use ('chrome' or 'edge').
                         If None, uses DEFAULT_BROWSER_TYPE.
            client_type: Type of client implementation to use.
                        If None, uses DEFAULT_CLIENT_TYPE.
        """
        self.browser_type = browser_type or DEFAULT_BROWSER_TYPE
        self.client_type = client_type or DEFAULT_CLIENT_TYPE

    # Implement ToolInterface properties
    @property
    def name(self) -> str:
        """Get the tool name."""
        return "browser_client"

    @property
    def description(self) -> str:
        """Get the tool description."""
        return "Browser automation for web scraping and testing"

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for the tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform (get_page_html, take_screenshot, get_page_markdown, get_cookies, capture_panels)",
                    "enum": ["get_page_html", "take_screenshot", "get_page_markdown", "get_cookies"],
                    "default": "get_page_markdown",
                },
                "url": {"type": "string", "description": "The URL to visit"},
                "wait_time": {
                    "type": "integer",
                    "description": "Time to wait for page load in seconds",
                    "default": 7,
                },
                "output_path": {
                    "type": "string",
                    "description": "Path where the screenshot should be saved (for take_screenshot)",
                    "nullable": True,
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Whether to include links in the extracted markdown (for get_page_markdown)",
                    "default": True,
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image references in the extracted markdown (for get_page_markdown)",
                    "default": False,
                },
                "wait_url": {
                    "type": "string",
                    "description": "URL substring or regex that indicates login success (for get_cookies)",
                    "nullable": True,
                },
                "timeout": {
                    "type": "integer",
                    "description": "Seconds to wait for wait_url before returning cookies",
                    "default": 60,
                },
                "store_key": {
                    "type": "string",
                    "description": "Key to store retrieved cookies in KV store",
                    "default": "browser.cookies/<domain>",
                },
                "headless": {
                    "type": "boolean",
                    "description": "Whether to run the browser in headless mode.",
                    "default": False,
                },
                "redact_secrets": {
                    "type": "boolean",
                    "description": "Whether to scan for and redact potential secrets in the content",
                    "default": False,
                },
            },
            "required": ["operation", "url"],
        }

    def _log_detected_secrets(self, findings, source_url: str, content_type: str):
        """Log information about detected secrets without revealing the secrets themselves.

        Args:
            findings: List of findings from the secret scanner
            source_url: URL where the content was retrieved from
            content_type: Type of content (HTML or Markdown)
        """
        if not findings:
            return

        # Extract domain from URL for more informative messages
        domain = _get_domain_from_url(source_url)

        # Group findings by type to provide more organized error messages
        secret_types = {}
        for finding in findings:
            secret_type = finding.get("SecretType", "Unknown")
            line_num = finding.get("LineNumber", 0)

            if secret_type not in secret_types:
                secret_types[secret_type] = []

            secret_types[secret_type].append(line_num)

        # Log an overall warning first with asterisks to make it stand out
        logger.warning(
            f"*******************************************************************\n"
            f"*** SECURITY ALERT: Detected and redacted {len(findings)} potential secrets\n"
            f"*** Content type: {content_type}\n"
            f"*** Domain: {domain}\n"
            f"*** URL: {source_url}\n"
            f"*******************************************************************"
        )

        # Log details for each type of secret found
        for secret_type, line_numbers in secret_types.items():
            line_ranges = self._summarize_line_numbers(line_numbers)
            logger.warning(
                f"SECURITY DETAIL: Found {len(line_numbers)} instance(s) of '{secret_type}' "
                f"at {line_ranges} in {content_type} from {domain}"
            )

    def _summarize_line_numbers(self, line_numbers):
        """Create a readable summary of line numbers.

        Args:
            line_numbers: List of line numbers

        Returns:
            A string representation of the line numbers in a readable format
        """
        if not line_numbers:
            return "unknown locations"

        # Sort line numbers
        sorted_lines = sorted(line_numbers)

        if len(sorted_lines) == 1:
            return f"line {sorted_lines[0]}"
        elif len(sorted_lines) == 2:
            return f"lines {sorted_lines[0]} and {sorted_lines[1]}"
        else:
            # Group consecutive numbers into ranges
            ranges = []
            range_start = sorted_lines[0]
            range_end = range_start

            for line in sorted_lines[1:]:
                if line == range_end + 1:
                    range_end = line
                else:
                    if range_start == range_end:
                        ranges.append(f"{range_start}")
                    else:
                        ranges.append(f"{range_start}-{range_end}")
                    range_start = line
                    range_end = line

            # Add the last range
            if range_start == range_end:
                ranges.append(f"{range_start}")
            else:
                ranges.append(f"{range_start}-{range_end}")

            if len(ranges) == 1:
                return f"lines {ranges[0]}"
            elif len(ranges) == 2:
                return f"lines {ranges[0]} and {ranges[1]}"
            else:
                last_range = ranges.pop()
                return f"lines {', '.join(ranges)}, and {last_range}"

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the provided arguments.

        Args:
            arguments: Dictionary of arguments for the tool

        Returns:
            Tool execution result
        """
        operation = arguments.get("operation", "")
        url = arguments.get("url", "")
        wait_time = arguments.get("wait_time", 7)
        headless = arguments.get("headless", False)
        browser_options = arguments.get("browser_options", None)
        browser_type = arguments.get("browser_type", self.browser_type)
        client_type = arguments.get("client_type", self.client_type)
        redact_secrets_enabled = arguments.get("redact_secrets", False)

        async with BrowserClientFactory.create_client(
            client_type, user_data_dir=None, browser_type=browser_type
        ) as client:
            if operation == "get_page_html":
                html = await client.get_page_html(
                    url, wait_time, headless, browser_options
                )
                if html:
                    # Apply secret redaction only if enabled
                    if redact_secrets_enabled:
                        html, findings = redact_secrets(html)

                        # Log warnings if secrets were detected
                        if findings:
                            self._log_detected_secrets(findings, url, "HTML")

                    return {
                        "success": True,
                        "html": html[:MAX_RETURN_CHARS]
                        + ("..." if len(html) > MAX_RETURN_CHARS else ""),
                        "html_length": len(html),
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Failed to retrieve HTML from {url}",
                    }
            elif operation == "take_screenshot":
                output_path = arguments.get(
                    "output_path", f"screenshot_{int(time.time())}.png"
                )
                success = await client.take_screenshot(
                    url, output_path, wait_time, headless, browser_options
                )
                return {"success": success, "output_path": output_path}
            elif operation == "get_page_markdown":
                include_links = arguments.get("include_links", True)
                include_images = arguments.get("include_images", True)
                html = await client.get_page_html(
                    url, wait_time, headless, browser_options
                )
                if not html:
                    return {
                        "success": False,
                        "error": f"Failed to retrieve HTML from {url}",
                    }

                # Apply secret redaction to HTML only if enabled
                redacted_html = html
                html_findings = []
                if redact_secrets_enabled:
                    redacted_html, html_findings = redact_secrets(html)

                    # Log warnings if secrets were detected in HTML
                    if html_findings:
                        self._log_detected_secrets(html_findings, url, "HTML")

                result = extract_and_format_html(
                    redacted_html,
                    include_links=include_links,
                    include_images=include_images,
                )

                # Scan the resulting markdown for any missed secrets only if enabled
                markdown_findings = []
                if redact_secrets_enabled and "markdown" in result:
                    redacted_markdown, md_findings = redact_secrets(result["markdown"])
                    result["markdown"] = redacted_markdown

                    # Log warnings if additional secrets were detected in markdown
                    if md_findings:
                        self._log_detected_secrets(md_findings, url, "Markdown")
                        markdown_findings = md_findings

                result["success"] = result.get("extraction_success", False)
                result["url"] = url

                # Log a summary if secrets were detected in either HTML or markdown
                if redact_secrets_enabled and (html_findings or markdown_findings):
                    total_secrets = len(html_findings) + len(markdown_findings)
                    logger.warning(
                        f"SECURITY SUMMARY: Total of {total_secrets} potential secrets detected and "
                        f"redacted from {url}"
                    )

                return result
            elif operation == "get_cookies":
                wait_url = arguments.get("wait_url")
                timeout = arguments.get("timeout", 60)
                store_key = arguments.get("store_key") or f"browser.cookies/{_get_domain_from_url(url)}"
                cookies_key = await client.get_cookies_after_login(
                    url,
                    wait_url,
                    headless=headless,
                    timeout=timeout,
                    store_key=store_key,
                )
                return {"success": True, "cookies_key": cookies_key}
            elif operation == "capture_panels":
                selector = arguments.get("selector", ".react-grid-item")
                out_dir = arguments.get("out_dir", "charts")
                width = arguments.get("width", 1600)
                height = arguments.get("height", 900)
                token = arguments.get("token", None)
                client = BrowserClientFactory.get_client(self.client_type, browser_type)
                return await client.capture_panels(
                    url,
                    selector,
                    out_dir,
                    width,
                    height,
                    token,
                    wait_time,
                    headless,
                    browser_options,
                )
            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

    async def get_page_html(self, url: str, wait_time: int = 30) -> Optional[str]:
        raise NotImplementedError(
            "get_page_html should be implemented by the real client"
        )

    async def take_screenshot(
        self, url: str, output_path: str, wait_time: int = 30
    ) -> bool:
        raise NotImplementedError(
            "take_screenshot should be implemented by the real client"
        )

    @classmethod
    def set_default_browser_type(cls, browser_type: Literal["chrome", "edge"]):
        """Set the default browser type to use globally.

        Args:
            browser_type: Type of browser ('chrome' or 'edge')
        """
        global DEFAULT_BROWSER_TYPE
        DEFAULT_BROWSER_TYPE = browser_type

    @classmethod
    def get_default_browser_type(cls) -> str:
        """Get the current default browser type.

        Returns:
            Current default browser type
        """
        return DEFAULT_BROWSER_TYPE

    @classmethod
    def set_default_client_type(cls, client_type: str):
        """Set the default client type to use globally.

        Args:
            client_type: Type of client implementation
        """
        global DEFAULT_CLIENT_TYPE
        DEFAULT_CLIENT_TYPE = client_type

    @classmethod
    def get_default_client_type(cls) -> str:
        """Get the current default client type.

        Returns:
            Current default client type
        """
        return DEFAULT_CLIENT_TYPE

    async def get_page_html(self, url: str, wait_time: int = 30) -> Optional[str]:
        raise NotImplementedError(
            "get_page_html should be implemented by the real client"
        )

    async def take_screenshot(
        self, url: str, output_path: str, wait_time: int = 30
    ) -> bool:
        raise NotImplementedError(
            "take_screenshot should be implemented by the real client"
        )
