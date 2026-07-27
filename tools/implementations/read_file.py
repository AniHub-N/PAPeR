from __future__ import annotations

from pathlib import Path

from tools.base import Tool
from tools.models import ToolResult


class ReadFileTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="read_file",
            description="Read the contents of a file."
        )

    def execute(self, path: str) -> ToolResult:
        try:
            content = Path(path).read_text(encoding="utf-8")

            return ToolResult(
                tool=self.name,
                success=True,
                output=content,
            )

        except Exception as exc:
            return ToolResult(
                tool=self.name,
                success=False,
                error=str(exc),
            )

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "path": "string"
            }
        }