import json

from primary_router.classifier_hook import classify_payload, parse_hook_payload
from primary_router.models import Route


def test_hook_payload_preserves_context_daemon_session_metadata():
    payload = parse_hook_payload(json.dumps({
        "prompt": "What is OAuth?",
        "session_id": "session-123",
        "transcript_path": "/tmp/session-123.jsonl",
        "cwd": "/workspace/project",
        "hook_event_name": "UserPromptSubmit",
    }))

    notification = classify_payload(payload)

    assert notification.route == Route.SIDE_LLM
    assert notification.session_id == "session-123"
    assert notification.transcript_path == "/tmp/session-123.jsonl"
    assert notification.cwd == "/workspace/project"


def test_hook_routes_code_tasks_to_claude():
    assert classify_payload(parse_hook_payload('{"prompt": "Fix src/auth.py"}')).route == Route.CLAUDE
