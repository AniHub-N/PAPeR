import json

from primary_router.context.events import AssistantMessage, CommandRun, DesignDecision, ErrorObserved, FileRead, UserPrompt
from primary_router.context.runtime import SessionRuntime
from primary_router.context.transcript_parser import TranscriptParser
from primary_router.context.transcript_watcher import TranscriptLine


def test_parser_emits_typed_events_for_transcript_content():
    records = [
        {"type": "user", "timestamp": "1", "message": {"content": "Explain this architecture"}},
        {"type": "assistant", "timestamp": "2", "message": {"content": [
            {"type": "text", "text": "The architecture decision is to use a daemon."},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "src/app.py"}},
            {"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q"}},
        ]}},
        {"type": "user", "timestamp": "3", "message": {"content": [
            {"type": "tool_result", "is_error": True, "content": "tests failed"},
        ]}},
    ]
    lines = tuple(TranscriptLine(index, index + 1, json.dumps(record)) for index, record in enumerate(records))

    events = TranscriptParser().parse("session-1", lines)

    assert any(isinstance(event, UserPrompt) for event in events)
    assert any(isinstance(event, AssistantMessage) for event in events)
    assert any(isinstance(event, DesignDecision) for event in events)
    assert any(isinstance(event, FileRead) and event.file_path == "src/app.py" for event in events)
    assert any(isinstance(event, CommandRun) and event.command == "pytest -q" for event in events)
    assert any(isinstance(event, ErrorObserved) and event.text == "tests failed" for event in events)


def test_parser_drains_only_watcher_supplied_lines():
    runtime = SessionRuntime("session-2", "/tmp/session.jsonl", "/tmp")
    runtime.pending_transcript_lines.append(TranscriptLine(0, 1, '{"type":"user","message":{"content":"hello"}}'))

    events = TranscriptParser().drain(runtime)

    assert len(events) == 1
    assert isinstance(events[0], UserPrompt)
    assert runtime.pending_transcript_lines == []
