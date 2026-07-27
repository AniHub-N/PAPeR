from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    Base interface for every tool.
    """

    name: str
    description: str

    @property
    def definition(self) -> dict[str, str]:
        """
        Metadata describing this tool.
        """
        return {
            "name": self.name,
            "description": self.description,
        }

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        Execute the tool.

        Parameters
        ----------
        kwargs:
            Tool-specific arguments.

        Returns
        -------
        Any
            Tool output.
        """
        raise NotImplementedError