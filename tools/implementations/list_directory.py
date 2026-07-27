from __future__ import annotations

from pathlib import Path

from ..base import Tool


class ListDirectoryTool(Tool):
    """
    Lists the contents of a directory.
    """

    name = "list_directory"
    description = "List the contents of a directory."

    def execute(
        self,
        *,
        path: str = ".",
        recursive: bool = False,
    ) -> list[dict]:
        directory = Path(path)

        if not directory.exists():
            raise FileNotFoundError(f"'{path}' does not exist.")

        if not directory.is_dir():
            raise ValueError(f"'{path}' is not a directory.")

        if recursive:
            iterator = directory.rglob("*")
        else:
            iterator = directory.iterdir()

        entries = []

        for item in sorted(iterator):
            entries.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                }
            )

        return entries