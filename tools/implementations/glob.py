from __future__ import annotations

from pathlib import Path

from ..base import Tool
from ..models import ToolResult


class GlobTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="glob",
            description="Find files matching a glob pattern.",
        )

    def execute(
        self,
        *,
        pattern: str,
        root: str = ".",
        recursive: bool = True,
    ) -> ToolResult:
        try:
            root_path = Path(root)

            if not root_path.exists():
                raise FileNotFoundError(f"'{root}' does not exist.")

            if not root_path.is_dir():
                raise ValueError(f"'{root}' is not a directory.")

            matches = (
                root_path.rglob(pattern)
                if recursive
                else root_path.glob(pattern)
            )

            return ToolResult(
                tool=self.name,
                success=True,
                output=sorted(str(path) for path in matches),
            )

        except Exception as exc:
            return ToolResult(
                tool=self.name,
                success=False,
                error=str(exc),
            )