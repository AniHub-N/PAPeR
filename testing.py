from tools.registry import ToolRegistry
from tools.dispatcher import ToolDispatcher
from tools.models import ToolCall

from tools.implementations.echo import EchoTool
from tools.implementations.read_file import ReadFileTool
from tools.implementations.glob import GlobTool
from tools.implementations.grep import GrepTool
from tools.implementations.list_directory import ListDirectoryTool

def main():
    # Create registry
    registry = ToolRegistry()

    # Register tools
    registry.register(EchoTool())
    registry.register(ReadFileTool())
    registry.register(GlobTool())
    registry.register(GrepTool())
    registry.register(ListDirectoryTool())

    # Create dispatcher
    dispatcher = ToolDispatcher(registry)

    print("=" * 50)
    print("Available Tools")
    print("=" * 50)

    for tool in registry.definitions():
        print(tool)

    print()

    print("=" * 50)
    print("Testing Echo Tool")
    print("=" * 50)

    echo_result = dispatcher.dispatch(
        ToolCall(
            tool="echo",
            arguments={
                "message": "Hello PAPeR!",
                "number": 42,
            },
        )
    )

    print(echo_result)
    print()

    print("=" * 50)
    print("Testing Read File Tool")
    print("=" * 50)

    read_result = dispatcher.dispatch(
        ToolCall(
            tool="read_file",
            arguments={
                "path": "README.md"
            },
        )
    )

    if read_result.success:
        print(read_result.output)
    else:
        print(read_result.error)


    print("=" * 50)
    print("Testing Glob Tool")
    print("=" * 50)

    glob_result = dispatcher.dispatch(
        ToolCall(
            tool="glob",
            arguments={
                "pattern": "*.py",
                "root": ".",
            },
        )
    )

    if glob_result.success:
        for file in glob_result.output:
            print(file)
    else:
        print(glob_result.error)


    print("=" * 50)
    print("Testing Grep Tool")
    print("=" * 50)

    grep_result = dispatcher.dispatch(
        ToolCall(
            tool="grep",
            arguments={
                "pattern": "ToolRegistry",
                "root": ".",
            },
        )
    )

    if grep_result.success:
        for match in grep_result.output:
            print(match)
    else:
        print(grep_result.error)

    print("=" * 50)
    print("Testing List Directory Tool")
    print("=" * 50)

    result = dispatcher.dispatch(
        ToolCall(
            tool="list_directory",
            arguments={
                "path": "."
            }
        )
    )

    if result.success:
        for item in result.output:
            print(item)
    else:
        print(result.error)


if __name__ == "__main__":
    main()