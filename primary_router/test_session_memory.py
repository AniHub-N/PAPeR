from primary_router.context.events import CommandRun, DesignDecision, ErrorObserved, FileEdit, UserPrompt
from primary_router.context.session_memory import SessionMemory


def event(event_type, **kwargs):
    return event_type(session_id="session", byte_start=0, byte_end=1, **kwargs)


def test_session_memory_keeps_current_high_signal_context():
    memory = SessionMemory()
    memory.apply(event(UserPrompt, text="Implement transcript synchronization"))
    memory.apply(event(FileEdit, tool_name="Edit", arguments={}, file_path="primary_router/context/daemon.py"))
    memory.apply(event(CommandRun, tool_name="Bash", arguments={}, command="pytest -q"))
    memory.apply(event(ErrorObserved, text="one test failed"))
    memory.apply(event(DesignDecision, text="Use session-scoped Chroma metadata."))

    snapshot = memory.snapshot()

    assert snapshot.current_task == "Implement transcript synchronization"
    assert snapshot.recent_files == ("primary_router/context/daemon.py",)
    assert snapshot.recent_commands == ("pytest -q",)
    assert snapshot.recent_errors == ("one test failed",)
    assert "Chroma" in snapshot.architecture_notes[0]
    assert "Current task" in snapshot.rolling_summary
