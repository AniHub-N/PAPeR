from __future__ import annotations

from .dispatcher import ToolDispatcher
from .models import LLMResponse, ResponseType, ToolResult


class ToolExecutor:
    """
    Executes tool calls contained in an LLMResponse.
    """

    def __init__(self, dispatcher: ToolDispatcher) -> None:
        self.dispatcher = dispatcher

    def execute(self, response: LLMResponse) -> ToolResult:
        """
        Execute the tool call contained in an LLMResponse.

        Raises:
            ValueError: If the response is not a tool call.
        """

        if response.type is not ResponseType.TOOL_CALL:
            raise ValueError("Cannot execute a final answer.")

        assert response.tool_call is not None

        return self.dispatcher.dispatch(response.tool_call)