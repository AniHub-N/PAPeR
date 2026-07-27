from __future__ import annotations

from tools.dispatcher import ToolDispatcher
from tools.executor import ToolExecutor
from tools.parser import ToolParser
from tools.prompt import PromptBuilder
from tools.registry import ToolRegistry
from tools.runner import ToolRunner

from tools.implementations.echo import EchoTool
from tools.implementations.glob import GlobTool
from tools.implementations.grep import GrepTool
from tools.implementations.list_directory import ListDirectoryTool
from tools.implementations.read_file import ReadFileTool


# ----------------------------
# Register tools
# ----------------------------

registry = ToolRegistry()

registry.register(EchoTool())
registry.register(ReadFileTool())
registry.register(GrepTool())
registry.register(GlobTool())
registry.register(ListDirectoryTool())


# ----------------------------
# Runtime
# ----------------------------

dispatcher = ToolDispatcher(registry)
executor = ToolExecutor(dispatcher)
parser = ToolParser()
prompt_builder = PromptBuilder(registry)


# ----------------------------
# Replace this with your real LLM
# ----------------------------

def llm(prompt: str) -> str:
    """
    Stub LLM.

    Replace this with your OpenAI /
    Anthropic / Ollama call.
    """
    raise NotImplementedError


runner = ToolRunner(
    llm=llm,
    parser=parser,
    executor=executor,
)


# ----------------------------
# Example
# ----------------------------

system_prompt = prompt_builder.build()

user_prompt = (
    "Find every implementation of ToolRegistry."
)

full_prompt = f"""{system_prompt}

User:
{user_prompt}
"""

answer = runner.run(full_prompt)

print(answer)