import os
from typing import Any, Dict

import httpx

from mcp_tools.interfaces import ToolInterface
from mcp_tools.plugin import register_tool
from mcp_tools.constants import Ecosystem, OSType


@register_tool(ecosystem=Ecosystem.GENERAL, os_type=OSType.ALL)
class CircleCITool(ToolInterface):
    """Interact with the CircleCI REST API."""

    @property
    def name(self) -> str:
        return "circleci"

    @property
    def description(self) -> str:
        return "Trigger and inspect CircleCI pipelines"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["trigger_pipeline", "get_pipeline_workflows"],
                    "description": "CircleCI operation to perform",
                },
                "project_slug": {
                    "type": "string",
                    "description": "Project slug in 'vcs/org/repo' format",
                    "nullable": True,
                },
                "branch": {
                    "type": "string",
                    "description": "Branch for the pipeline",
                    "nullable": True,
                },
                "pipeline_id": {
                    "type": "string",
                    "description": "Pipeline ID for workflow lookup",
                    "nullable": True,
                },
                "parameters": {
                    "type": "object",
                    "description": "Additional pipeline parameters",
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
        token = os.getenv("CIRCLECI_TOKEN")
        if not token:
            return {"success": False, "error": "CIRCLECI_TOKEN not set"}

        headers = {"Circle-Token": token}
        base_url = "https://circleci.com/api/v2"

        if function_name == "trigger_pipeline":
            project_slug = parameters.get("project_slug")
            branch = parameters.get("branch")
            if not project_slug or not branch:
                return {
                    "success": False,
                    "error": "Missing required parameters: project_slug and branch",
                }
            url = f"{base_url}/project/{project_slug}/pipeline"
            data: Dict[str, Any] = {"branch": branch}
            if parameters.get("parameters"):
                data["parameters"] = parameters.get("parameters")
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=data, headers=headers, timeout=30)
            if resp.status_code >= 400:
                return {"success": False, "error": resp.text}
            return {"success": True, "result": resp.json()}

        if function_name == "get_pipeline_workflows":
            pipeline_id = parameters.get("pipeline_id")
            if not pipeline_id:
                return {"success": False, "error": "Missing required parameter: pipeline_id"}
            url = f"{base_url}/pipeline/{pipeline_id}/workflow"
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=30)
            if resp.status_code >= 400:
                return {"success": False, "error": resp.text}
            return {"success": True, "result": resp.json()}

        return {"error": f"Unknown CircleCI operation: {function_name}"}
