from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import ToolResult


class Tool(ABC):
    """
    Base class for all tools.
    """

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """
        Execute the tool.

        Returns:
            ToolResult
        """
        raise NotImplementedError

    def schema(self) -> dict[str, Any]:
        """
        Schema exposed to the LLM prompt.
        """

        return {
            "name": self.name,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"