from __future__ import annotations

from .models import ToolCall, ToolResult
from .registry import ToolRegistry


class ToolDispatcher:
    """
    Looks up and executes tools from the registry.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def dispatch(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute the requested tool.

        This method never raises because of an unknown tool or
        execution failure. Those are converted into ToolResults.
        """

        if not self.registry.has(tool_call.tool):
            return ToolResult(
                tool=tool_call.tool,
                success=False,
                error=f"Unknown tool '{tool_call.tool}'.",
            )

        tool = self.registry.get(tool_call.tool)

        try:
            return tool.execute(**tool_call.arguments)

        except Exception as exc:
            return ToolResult(
                tool=tool.name,
                success=False,
                error=str(exc),
            )