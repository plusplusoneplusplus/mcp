"""Browser client factory.

This module provides a factory for creating browser clients.
"""

from typing import Optional, Literal

from mcp_tools.browser.interface import IBrowserClient
from mcp_tools.browser.selenium_client import SeleniumBrowserClient
from mcp_tools.browser.playwright_client import PlaywrightBrowserClient
from config.manager import EnvironmentManager


class BrowserClientFactory:
    """Factory for creating browser clients.

    This class provides methods for creating different types of browser clients.
    """

    @staticmethod
    def create_client(
        client_type: str = "playwright",
        user_data_dir: Optional[str] = None,
        browser_type: Optional[Literal["chrome", "edge", "chromium"]] = None,
    ) -> IBrowserClient:
        """Create a browser client of the specified type.

        Args:
            client_type: Type of client to create ('selenium' or 'playwright')
            user_data_dir: Path to user data directory for browser profiles
            browser_type: Type of browser to use:
                        - For selenium: 'chrome' or 'edge'
                        - For playwright: 'chrome' or 'edge'

        Returns:
            Browser client instance

        Raises:
            ValueError: If an unsupported client type is specified
        """
        client_type = client_type.lower()

        if user_data_dir is None:
            user_data_dir = EnvironmentManager().get_setting(
                "browser_profile_path", ".browserprofile"
            )
        # print(f"Creating browser client with user data directory: {user_data_dir}")

        if client_type == "selenium":
            if browser_type not in [None, "chrome", "edge"]:
                raise ValueError(
                    f"Unsupported browser type for Selenium: {browser_type}"
                )
            return SeleniumBrowserClient(browser_type or "chrome")
        elif client_type == "playwright":
            if browser_type not in [None, "chrome", "edge"]:
                raise ValueError(
                    f"Unsupported browser type for Playwright: {browser_type}"
                )
            return PlaywrightBrowserClient(browser_type or "chrome", user_data_dir)
        else:
            raise ValueError(f"Unsupported client type: {client_type}")
