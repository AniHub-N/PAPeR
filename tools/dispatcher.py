from __future__ import annotations

from .models import ToolCall, ToolResult
from .registry import ToolRegistry


class ToolDispatcher:
    """
    Executes tool calls using the registered tools.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def dispatch(self, call: ToolCall) -> ToolResult:
        """
        Execute a tool call and return the result.
        """
        try:
            tool = self._registry.get(call.tool)

            output = tool.execute(**call.arguments)

            return ToolResult(
                tool=call.tool,
                success=True,
                output=output,
            )

        except Exception as e:
            return ToolResult(
                tool=call.tool,
                success=False,
                error=str(e),
            )