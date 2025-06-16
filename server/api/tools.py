"""Tools management API endpoints."""

from typing import Any, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_tools.dependency import injector
from mcp_tools.plugin import registry


async def api_list_tools(request: Request) -> JSONResponse:
    tool_sources = registry.get_tool_sources()
    active_instances = injector.get_filtered_instances()
    tools = []
    for name, source in tool_sources.items():
        instance = active_instances.get(name)
        description = instance.description if instance else ""
        input_schema: Dict[str, Any] = (
            instance.input_schema if instance else {}
        )
        category = getattr(instance, "category", "uncategorized")
        tools.append(
            {
                "name": name,
                "source": source,
                "active": name in active_instances,
                "description": description,
                "input_schema": input_schema,
                "category": category,
            }
        )
    return JSONResponse({"tools": tools, "total": len(tools), "active": len(active_instances)})


async def api_get_tool_detail(request: Request) -> JSONResponse:
    tool_name = request.path_params.get("tool_name")
    instance = injector.get_tool_instance(tool_name)
    if not instance:
        return JSONResponse({"error": "Tool not found"}, status_code=404)
    tool_sources = registry.get_tool_sources()
    return JSONResponse(
        {
            "name": tool_name,
            "description": instance.description,
            "input_schema": instance.input_schema,
            "category": getattr(instance, "category", "uncategorized"),
            "source": tool_sources.get(tool_name, "unknown"),
            "active": tool_name in injector.get_filtered_instances(),
        }
    )


async def api_execute_tool(request: Request) -> JSONResponse:
    tool_name = request.path_params.get("tool_name")
    instance = injector.get_tool_instance(tool_name)
    if not instance:
        return JSONResponse({"error": "Tool not found"}, status_code=404)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    result = await instance.execute_tool(payload)
    return JSONResponse({"result": result})


async def api_tool_stats(request: Request) -> JSONResponse:
    tool_sources = registry.get_tool_sources()
    active_instances = injector.get_filtered_instances()
    return JSONResponse(
        {
            "total_tools": len(tool_sources),
            "active_tools": len(active_instances),
            "code_tools": len([s for s in tool_sources.values() if s == "code"]),
            "yaml_tools": len([s for s in tool_sources.values() if s == "yaml"]),
        }
    )


async def api_tool_categories(request: Request) -> JSONResponse:
    summary = registry.get_plugin_loading_summary()
    return JSONResponse({
        "plugin_groups": summary.get("plugin_groups", {}),
        "tool_sources": summary.get("tool_sources", {}),
    })
