from __future__ import annotations

from typing import Any

from bridge.registry import Registry, default_registry


class McpRegistryAdapter:
    """Registry-backed MCP surface.

    This is deliberately transport-neutral. The stdio/Streamable HTTP server can
    use these methods once the MCP SDK is wired in.
    """

    def __init__(self, registry: Registry = default_registry) -> None:
        self.registry = registry

    def list_tools(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for app in self.registry.apps():
            for action in app.actions.values():
                tools.append(
                    {
                        "name": f"{app.name}.{action.name}",
                        "description": _tool_description(action.title, action.description),
                        "inputSchema": action.input_schema,
                    }
                )
        return sorted(tools, key=lambda tool: tool["name"])

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        app_name, separator, action_name = name.partition(".")
        if not separator:
            raise ValueError(f"Invalid MCP tool name: {name}.")
        return self.registry.invoke(app_name, action_name, arguments).data

    def list_resources(self) -> list[dict[str, str]]:
        resources = [
            {
                "uri": "bridge://apps",
                "name": "Bridge mini-app manifest",
                "mimeType": "application/json",
            }
        ]
        for app in self.registry.apps():
            resources.append(
                {
                    "uri": f"bridge://apps/{app.name}",
                    "name": app.title,
                    "mimeType": "application/json",
                }
            )
        return resources

    def read_resource(self, uri: str) -> dict[str, Any]:
        if uri == "bridge://apps":
            return self.registry.manifest()
        prefix = "bridge://apps/"
        if uri.startswith(prefix):
            return self.registry.app_manifest(uri.removeprefix(prefix))
        raise ValueError(f"Unknown Bridge resource: {uri}.")


def _tool_description(title: str, description: str) -> str:
    return f"{title}. {description}".strip()
