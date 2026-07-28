from primary_router.context.daemon import ContextDaemon, create_context_daemon, notification_from_wire
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


def test_standard_daemon_synchronizes_new_transcript_lines(tmp_path):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("", encoding="utf-8")
    daemon = create_context_daemon(tmp_path / "checkpoints.json")
    notification = HookNotification("session-3", str(transcript), str(tmp_path), "UserPromptSubmit", "Explain OAuth", Route.SIDE_LLM)

    daemon.receive(notification)  # establish EOF checkpoint
    transcript.write_text('{"type": "user"}\n', encoding="utf-8")
    daemon.synchronize_all()

    assert daemon.runtime("session-3").pending_transcript_lines == ['{"type": "user"}']
