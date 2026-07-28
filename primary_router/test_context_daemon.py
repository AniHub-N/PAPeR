from primary_router.context.daemon import ContextDaemon, notification_from_wire
from primary_router.models import HookNotification, Route


def test_daemon_creates_and_updates_one_runtime_per_session():
    synchronized = []
    daemon = ContextDaemon(synchronizer=lambda runtime: synchronized.append(runtime.session_id))
    first = HookNotification("session-1", "/tmp/one.jsonl", "/repo", "UserPromptSubmit", "What is OAuth?", Route.SIDE_LLM)
    second = HookNotification("session-1", "/tmp/one.jsonl", "/repo", "UserPromptSubmit", "Explain JWT", Route.SIDE_LLM)

    daemon.receive(first)
    runtime = daemon.receive(second)

    assert len(daemon.active_sessions()) == 1
    assert runtime.last_prompt == "Explain JWT"
    assert synchronized == ["session-1", "session-1"]


def test_wire_notification_preserves_session_coordinates():
    notification = notification_from_wire({
        "session_id": "session-2",
        "transcript_path": "/tmp/two.jsonl",
        "cwd": "/repo",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Explain the architecture",
        "route": "side_llm",
    })

    assert notification.route == Route.SIDE_LLM
    assert notification.transcript_path == "/tmp/two.jsonl"
