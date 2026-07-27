from __future__ import annotations

from pathlib import Path

from ..base import Tool


class GlobTool(Tool):
    """
    Find files matching a glob pattern.
    """

    name = "glob"
    description = "Find files matching a glob pattern."

    def execute(
        self,
        *,
        pattern: str,
        root: str = ".",
        recursive: bool = True,
    ) -> list[str]:
        root_path = Path(root)

        if not root_path.exists():
            raise FileNotFoundError(f"'{root}' does not exist.")

        if not root_path.is_dir():
            raise ValueError(f"'{root}' is not a directory.")

        if recursive:
            matches = root_path.rglob(pattern)
        else:
            matches = root_path.glob(pattern)

        return sorted(str(path) for path in matches)