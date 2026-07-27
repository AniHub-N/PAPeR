from __future__ import annotations

from pathlib import Path

from ..base import Tool
from ..models import ToolResult


class ListDirectoryTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="list_directory",
            description="List the contents of a directory.",
        )

    def execute(
        self,
        *,
        path: str = ".",
        recursive: bool = False,
    ) -> ToolResult:
        try:
            directory = Path(path)

            if not directory.exists():
                raise FileNotFoundError(f"'{path}' does not exist.")

            if not directory.is_dir():
                raise ValueError(f"'{path}' is not a directory.")

            iterator = (
                directory.rglob("*")
                if recursive
                else directory.iterdir()
            )

            entries = []

            for item in sorted(iterator):
                entries.append(
                    {
                        "name": item.name,
                        "path": str(item),
                        "type": (
                            "directory"
                            if item.is_dir()
                            else "file"
                        ),
                    }
                )

            return ToolResult(
                tool=self.name,
                success=True,
                output=entries,
            )

        except Exception as exc:
            return ToolResult(
                tool=self.name,
                success=False,
                error=str(exc),
            )