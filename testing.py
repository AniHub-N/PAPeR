from tools.registry import ToolRegistry
from tools.dispatcher import ToolDispatcher
from tools.models import ToolCall
from tools.parser import ToolParser
from tools.executor import ToolExecutor

from tools.implementations.echo import EchoTool
from tools.implementations.read_file import ReadFileTool
from tools.implementations.glob import GlobTool
from tools.implementations.grep import GrepTool
from tools.implementations.list_directory import ListDirectoryTool


def header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    registry = ToolRegistry()

    registry.register(EchoTool())
    registry.register(ReadFileTool())
    registry.register(GlobTool())
    registry.register(GrepTool())
    registry.register(ListDirectoryTool())

    dispatcher = ToolDispatcher(registry)
    parser = ToolParser()
    executor = ToolExecutor(dispatcher)

    # --------------------------------------------------
    header("REGISTERED TOOLS")

    for tool in registry.list_tools():
        print(tool)

    # --------------------------------------------------
    header("ECHO TOOL")

    result = dispatcher.dispatch(
        ToolCall(
            tool="echo",
            arguments={
                "text": "Hello PAPeR!"
            }
        )
    )

    print(result)

    # --------------------------------------------------
    header("UNKNOWN TOOL")

    result = dispatcher.dispatch(
        ToolCall(
            tool="banana",
            arguments={}
        )
    )

    print(result)

    # --------------------------------------------------
    header("READ FILE")

    result = dispatcher.dispatch(
        ToolCall(
            tool="read_file",
            arguments={
                "path": "README.md"
            }
        )
    )

    if result.success:
        print(result.output[:500])
    else:
        print(result.error)

    # --------------------------------------------------
    header("GLOB")

    result = dispatcher.dispatch(
        ToolCall(
            tool="glob",
            arguments={
                "pattern": "*.py",
                "root": "."
            }
        )
    )

    if result.success:
        print(f"Found {len(result.output)} files")
        for file in result.output[:10]:
            print(file)
    else:
        print(result.error)

    # --------------------------------------------------
    header("GREP")

    result = dispatcher.dispatch(
        ToolCall(
            tool="grep",
            arguments={
                "pattern": "ToolRegistry",
                "root": "."
            }
        )
    )

    if result.success:
        print(f"Found {len(result.output)} matches")
        for match in result.output[:10]:
            print(match)
    else:
        print(result.error)

    # --------------------------------------------------
    header("LIST DIRECTORY")

    result = dispatcher.dispatch(
        ToolCall(
            tool="list_directory",
            arguments={
                "path": "."
            }
        )
    )

    if result.success:
        print(f"{len(result.output)} entries")
        for item in result.output[:10]:
            print(item)
    else:
        print(result.error)

    # --------------------------------------------------
    header("PARSER -> EXECUTOR")

    llm_response = """
{
    "type": "tool_call",
    "tool": "grep",
    "arguments": {
        "pattern": "ToolRegistry",
        "root": "."
    }
}
"""

    response = parser.parse(llm_response)

    print(response)

    result = executor.execute(response)

    print(result)

    # --------------------------------------------------
    header("FINAL ANSWER PARSER")

    llm_response = """
{
    "type": "final_answer",
    "content": "Everything works!"
}
"""

    response = parser.parse(llm_response)

    print(response)

    print("\n")
    print("=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70)

    from tools.runner import ToolRunner
    from tools.prompt import PromptBuilder


    # --------------------------------------------------
    header("RUNNER")


    def fake_llm(prompt: str) -> str:
        print("\n----- PROMPT SENT TO LLM -----")
        print(prompt)
        print("------------------------------\n")

        # First call -> ask for a tool
        if "Tool 'echo' returned:" not in prompt:
            return """
    {
        "type": "tool_call",
        "tool": "echo",
        "arguments": {
            "text": "Hello from the fake LLM!"
        }
    }
    """

        # Second call -> final answer
        return """
    {
        "type": "final_answer",
        "content": "Runner works!"
    }
    """


    prompt_builder = PromptBuilder(registry)

    system_prompt = prompt_builder.build()

    runner = ToolRunner(
        llm=fake_llm,
        parser=parser,
        executor=executor,
    )

    result = runner.run(
        system_prompt
        + "\n\nUser:\nSay hello."
    )

    print("\nRunner Result:")
    print(result)


if __name__ == "__main__":
    main()