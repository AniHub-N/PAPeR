from __future__ import annotations

import re
from pathlib import Path

from ..base import Tool


class GrepTool(Tool):
    """
    Search for a regex pattern inside files.
    """

    name = "grep"
    description = "Search for a regex pattern in files."

    def execute(
        self,
        *,
        pattern: str,
        root: str = ".",
        recursive: bool = True,
        ignore_case: bool = False,
    ) -> list[dict]:
        root_path = Path(root)

        if not root_path.exists():
            raise FileNotFoundError(f"'{root}' does not exist.")

        if not root_path.is_dir():
            raise ValueError(f"'{root}' is not a directory.")

        flags = re.IGNORECASE if ignore_case else 0
        regex = re.compile(pattern, flags)

        iterator = root_path.rglob("*") if recursive else root_path.glob("*")

        matches = []

        for path in iterator:
            if not path.is_file():
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue

            for line_number, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    matches.append(
                        {
                            "file": str(path),
                            "line": line_number,
                            "text": line.strip(),
                        }
                    )

        return matches