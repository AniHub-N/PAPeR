from __future__ import annotations

from tools.base import Tool
from tools.models import ToolResult


class EchoTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="echo",
            description="Echoes the provided text."
        )

    def execute(self, text: str) -> ToolResult:
        return ToolResult(
            tool=self.name,
            success=True,
            output=text,
        )

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "text": "string"
            }
        }