from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseType(str, Enum):
    TOOL_CALL = "tool_call"
    FINAL_ANSWER = "final_answer"


@dataclass(slots=True)
class ToolCall:
    """
    Represents a request from the LLM to execute a tool.
    """

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FinalAnswer:
    """
    Represents the final response from the LLM.
    """

    content: str


@dataclass(slots=True)
class LLMResponse:
    """
    Parsed response from the LLM.

    Exactly ONE of `tool_call` or `final_answer`
    should be populated depending on `type`.
    """

    type: ResponseType
    tool_call: ToolCall | None = None
    final_answer: FinalAnswer | None = None

    def __post_init__(self) -> None:
        if self.type is ResponseType.TOOL_CALL:
            if self.tool_call is None:
                raise ValueError("tool_call must be provided for TOOL_CALL responses.")
            if self.final_answer is not None:
                raise ValueError("final_answer must be None for TOOL_CALL responses.")

        elif self.type is ResponseType.FINAL_ANSWER:
            if self.final_answer is None:
                raise ValueError("final_answer must be provided for FINAL_ANSWER responses.")
            if self.tool_call is not None:
                raise ValueError("tool_call must be None for FINAL_ANSWER responses.")


@dataclass(slots=True)
class ToolResult:
    """
    Result returned by every tool.
    """

    tool: str
    success: bool
    output: Any = None
    error: str | None = None

    @property
    def failed(self) -> bool:
        return not self.success