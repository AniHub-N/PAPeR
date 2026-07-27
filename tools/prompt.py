from __future__ import annotations

import json

from .registry import ToolRegistry


class PromptBuilder:
    """
    Builds the system prompt describing the available tools
    and the required JSON response format.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def build(self) -> str:
        tool_schemas = [
            tool.schema()
            for tool in self.registry.list_tools()
        ]

        return f"""You are an AI coding assistant.

You may use the available tools to answer the user's request.

Available tools:

{json.dumps(tool_schemas, indent=2)}

When you want to use a tool, respond ONLY with JSON in this format:

{{
    "type": "tool_call",
    "tool": "<tool_name>",
    "arguments": {{
        ...
    }}
}}

When you have enough information to answer, respond ONLY with JSON in this format:

{{
    "type": "final_answer",
    "content": "<your answer>"
}}

Rules:
- Output valid JSON only.
- Never include markdown.
- Never explain your reasoning.
- Call one tool at a time.
- If a tool fails, you may try another tool.
"""