from __future__ import annotations

import json

from .models import (
    FinalAnswer,
    LLMResponse,
    ResponseType,
    ToolCall,
)


class ToolParser:
    """
    Parses an LLM JSON response into internal models.
    """

    @staticmethod
    def parse(response: str) -> LLMResponse:
        data = json.loads(response)

        response_type = ResponseType(data["type"])

        if response_type is ResponseType.TOOL_CALL:
            return LLMResponse(
                type=ResponseType.TOOL_CALL,
                tool_call=ToolCall(
                    tool=data["tool"],
                    arguments=data.get("arguments", {}),
                ),
            )

        if response_type is ResponseType.FINAL_ANSWER:
            return LLMResponse(
                type=ResponseType.FINAL_ANSWER,
                final_answer=FinalAnswer(
                    content=data["content"],
                ),
            )

        raise ValueError(f"Unknown response type: {response_type}")