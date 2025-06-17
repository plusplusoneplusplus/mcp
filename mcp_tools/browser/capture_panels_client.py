"""
Dedicated client for capturing dashboard panels as PNGs via browser automation.
"""

from typing import Dict, Any, Optional, Literal
from mcp_tools.browser.factory import BrowserClientFactory
from mcp_tools.plugin import register_tool
from mcp_tools.interfaces import CapturePanelsClientInterface
from mcp_tools.constants import OSType
from config import env

DEFAULT_BROWSER_TYPE: Literal["chrome", "edge"] = env.get_setting(
    "browser_type", "chrome"
)
DEFAULT_CLIENT_TYPE: str = env.get_setting("client_type", "playwright")


@register_tool(os_type=OSType.ALL)
class CapturePanelsClient(CapturePanelsClientInterface):
    """Dedicated client for capturing dashboard panels as PNGs."""

    def __init__(
        self, browser_type: Literal["chrome", "edge"] = None, client_type: str = None
    ):
        self.browser_type = browser_type or DEFAULT_BROWSER_TYPE
        self.client_type = client_type or DEFAULT_CLIENT_TYPE

    @property
    def name(self) -> str:
        return "capture_panels_client"

    @property
    def description(self) -> str:
        return "Capture dashboard panels as PNG images via browser automation."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "The operation to perform (capture_panels)",
                    "enum": ["capture_panels"],
                    "default": "capture_panels",
                },
                "url": {"type": "string", "description": "The dashboard URL to visit"},
                "selector": {
                    "type": "string",
                    "description": "CSS selector for chart containers",
                    "default": ".react-grid-item",
                },
                "width": {
                    "type": "integer",
                    "description": "Viewport width",
                    "default": 1600,
                },
                "height": {
                    "type": "integer",
                    "description": "Viewport height",
                    "default": 900,
                },
                "token": {
                    "type": "string",
                    "description": "Bearer token for Authorization header",
                    "nullable": True,
                },
                "wait_time": {
                    "type": "integer",
                    "description": "Time to wait for page load in seconds",
                    "default": 7,
                },
                "headless": {
                    "type": "boolean",
                    "description": "Whether to run browser in headless mode.",
                    "default": False,
                },
                "autoscroll": {
                    "type": "boolean",
                    "description": "If true, autoscroll each panel into view and scroll its contents before capturing.",
                    "default": False,
                },
            },
            "required": ["operation", "url"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", "")
        if operation != "capture_panels":
            return {"success": False, "error": f"Unsupported operation: {operation}"}
        url = arguments.get("url", "")
        selector = arguments.get("selector", ".react-grid-item")
        out_dir = env.get_setting("image_dir", ".images")
        width = arguments.get("width", 1600)
        height = arguments.get("height", 900)
        token = arguments.get("token", None)
        wait_time = arguments.get("wait_time", 7)
        headless = arguments.get("headless", False)

        browser_type = arguments.get("browser_type", self.browser_type)
        autoscroll = arguments.get("autoscroll", False)
        return await self.capture_panels(
            url,
            selector,
            width,
            height,
            token,
            wait_time,
            headless,
            autoscroll,
        )

    async def capture_panels(
        self,
        url: str,
        selector: str = ".react-grid-item",
        width: int = 1600,
        height: int = 900,
        token: Optional[str] = None,
        wait_time: int = 30,
        headless: bool = True,
        autoscroll: bool = False,
        max_parallelism: int = 4,
    ) -> int:
        """
        Capture each matching element as an image and save to the output directory.
        Args:
            url: The dashboard URL to visit
            selector: CSS selector for chart/panel containers
            out_dir: Directory to write PNGs
            width: Browser viewport width
            height: Browser viewport height
            token: Bearer token for Authorization header (optional)
            wait_time: Time to wait for page load in seconds
            headless: Whether to run browser in headless mode
            options: Browser-specific options
            autoscroll: If true, autoscroll each panel into view and scroll its contents before capturing.
            max_parallelism: Maximum number of panels to capture in parallel (default 4)
        Returns:
            The number of panels captured (saved as PNGs)
        """
        browser_type = self.browser_type
        client = BrowserClientFactory.create_client(
            client_type=self.client_type, browser_type=browser_type
        )
        return await client.capture_panels(
            url,
            selector,
            width,
            height,
            token,
            wait_time,
            headless,
            autoscroll=autoscroll,
            max_parallelism=max_parallelism,
        )
