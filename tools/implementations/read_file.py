from __future__ import annotations

from pathlib import Path

from ..base import Tool


class ReadFileTool(Tool):
    """
    Reads the contents of a file.
    """

    name = "read_file"
    description = "Read the contents of a file."

    def execute(self, *, path: str, encoding: str = "utf-8") -> str:
        file_path = Path(path)

        if not file_path.exists():
            raise FileNotFoundError(f"'{path}' does not exist.")

        if not file_path.is_file():
            raise ValueError(f"'{path}' is not a file.")

        return file_path.read_text(encoding=encoding)