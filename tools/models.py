from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolCall:
    """
    Represents a request to execute a tool.
    """

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolResult:
    """
    Represents the result returned by a tool.
    """

    tool: str
    success: bool

    output: Any = None
    error: str |None = None

    @property
    def failed(self) -> bool:
        return not self.success