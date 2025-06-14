import logging
import subprocess
from typing import Any, Dict, List, Optional

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool


@register_tool
class GithubCliTool(ToolInterface):
    """Tool that wraps common GitHub CLI commands."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    @property
    def name(self) -> str:
        return "github_cli"

    @property
    def description(self) -> str:
        return "Interact with GitHub using the gh CLI"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["auth_status", "issue_create", "pr_create"],
                    "description": "GitHub CLI operation to perform",
                },
                "repo": {
                    "type": "string",
                    "description": "Repository in 'owner/repo' format",
                    "nullable": True,
                },
                "title": {
                    "type": "string",
                    "description": "Title for issue or pull request",
                    "nullable": True,
                },
                "body": {
                    "type": "string",
                    "description": "Body for issue or pull request",
                    "nullable": True,
                },
                "base": {
                    "type": "string",
                    "description": "Base branch for pull request",
                    "nullable": True,
                },
                "head": {
                    "type": "string",
                    "description": "Head branch for pull request",
                    "nullable": True,
                },
            },
            "required": ["operation"],
        }

    async def execute_tool(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"error": "Missing required parameter: operation"}
        return await self.execute_function(operation, arguments)

    async def execute_function(
        self, function_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        if function_name == "auth_status":
            return self._run_gh(["auth", "status"], parameters.get("repo"))
        if function_name == "issue_create":
            title = parameters.get("title")
            body = parameters.get("body")
            if not title or not body:
                return {"error": "Missing required parameters: title and body"}
            cmd = ["issue", "create", "--title", title, "--body", body]
            return self._run_gh(cmd, parameters.get("repo"))
        if function_name == "pr_create":
            title = parameters.get("title")
            body = parameters.get("body")
            if not title or not body:
                return {"error": "Missing required parameters: title and body"}
            cmd = ["pr", "create", "--title", title, "--body", body]
            base = parameters.get("base")
            head = parameters.get("head")
            if base:
                cmd.extend(["--base", base])
            if head:
                cmd.extend(["--head", head])
            return self._run_gh(cmd, parameters.get("repo"))
        return {"error": f"Unknown GitHub CLI operation: {function_name}"}

    def _run_gh(self, args: List[str], repo: Optional[str]) -> Dict[str, Any]:
        cmd = ["gh"] + args
        if repo:
            cmd.extend(["--repo", repo])
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return {"success": False, "error": result.stderr.strip() or "gh command failed"}
            return {"success": True, "result": result.stdout.strip()}
        except FileNotFoundError:
            return {"success": False, "error": "gh CLI not found"}
        except Exception as e:
            self.logger.error(f"Error running gh command {' '.join(cmd)}: {e}")
            return {"success": False, "error": str(e)}
