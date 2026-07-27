from __future__ import annotations

from collections.abc import Callable

from .executor import ToolExecutor
from .models import ResponseType
from .parser import ToolParser


class ToolRunner:
    """
    Runs the agent loop until the LLM produces a final answer.
    """

    def __init__(
        self,
        llm: Callable[[str], str],
        parser: ToolParser,
        executor: ToolExecutor,
        max_iterations: int = 20,
    ) -> None:
        self.llm = llm
        self.parser = parser
        self.executor = executor
        self.max_iterations = max_iterations

    def run(self, prompt: str) -> str:
        """
        Run the tool loop.

        Args:
            prompt: The initial prompt sent to the LLM.

        Returns:
            The final answer.
        """

        current_prompt = prompt

        for _ in range(self.max_iterations):

            llm_response = self.llm(current_prompt)

            response = self.parser.parse(llm_response)

            if response.type is ResponseType.FINAL_ANSWER:
                assert response.final_answer is not None
                return response.final_answer.content

            tool_result = self.executor.execute(response)

            current_prompt += (
                "\n\n"
                f"Tool '{tool_result.tool}' returned:\n"
                f"Success: {tool_result.success}\n"
                f"Output:\n{tool_result.output}\n"
                f"Error: {tool_result.error}\n"
            )

        raise RuntimeError(
            f"Agent exceeded maximum iterations ({self.max_iterations})."
        )