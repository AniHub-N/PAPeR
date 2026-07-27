from __future__ import annotations

from .base import Tool


class ToolRegistry:
    """
    Stores and retrieves available tools.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a tool.

        Raises:
            ValueError: If a tool with the same name already exists.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """
        Retrieve a registered tool.

        Raises:
            KeyError: If the tool does not exist.
        """
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool '{name}'.") from exc

    def has(self, name: str) -> bool:
        """
        Check whether a tool is registered.
        """
        return name in self._tools

    def list_tools(self) -> list[Tool]:
        """
        Return all registered tools.
        """
        return list(self._tools.values())

    def clear(self) -> None:
        """
        Remove all registered tools.
        """
        self._tools.clear()