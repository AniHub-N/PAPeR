from __future__ import annotations

from typing import Any

from ..base import Tool


class EchoTool(Tool):
    """
    Simple tool used to verify the tool pipeline.
    """

    name = "echo"
    description = "Returns the provided arguments unchanged."

    def execute(self, **kwargs: Any) -> Any:
        return kwargs