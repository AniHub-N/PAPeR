from __future__ import annotations

from typing import Dict

from .base import Tool


class ToolRegistry:
    """
    Stores and manages all available tools.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a new tool.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")

        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        """
        Retrieve a tool by name.
        """
        if name not in self._tools:
            raise KeyError(f"Unknown tool '{name}'.")

        return self._tools[name]

    def list(self) -> list[Tool]:
        """
        Return all registered tools.
        """
        return list(self._tools.values())

    def names(self) -> list[str]:
        """
        Return the names of all registered tools.
        """
        return list(self._tools.keys())

    def definitions(self) -> list[dict[str, str]]:
        """
        Return metadata describing every registered tool.
        """
        return [tool.definition for tool in self._tools.values()]

    def exists(self, name: str) -> bool:
        """
        Check whether a tool exists.
        """
        return name in self._tools