#!/usr/bin/env python3
"""Claude Code's lightweight UserPromptSubmit routing hook.

The hook deliberately does only synchronous validation and deterministic routing.
It exposes the session and transcript coordinates as ``HookNotification`` for
the Context Daemon introduced in Phase 2, but never reads a transcript, calls a
model, or waits on a background service.
"""

import json
import os
import signal
import socket
import sys

try:
    from .models import HookNotification, HookPayload, Route
    from .router import PromptRouter
except ImportError:  # pragma: no cover - Claude Code executes this as a script
    from models import HookNotification, HookPayload, Route
    from router import PromptRouter


HARD_TIMEOUT_SEC = 2
_router = PromptRouter()


def parse_hook_payload(raw: str) -> HookPayload:
    """Parse Claude Code input into the stable Phase 1/2 hook contract."""
    data = json.loads(raw or "{}")
    prompt = data.get("prompt", "")
    if not isinstance(prompt, str):
        raise ValueError("hook prompt must be a string")
    return HookPayload(
        prompt=prompt,
        session_id=str(data.get("session_id", "")),
        transcript_path=str(data.get("transcript_path", "")),
        cwd=str(data.get("cwd", "")),
        hook_event_name=str(data.get("hook_event_name", "UserPromptSubmit")),
    )


def classify_payload(payload: HookPayload) -> HookNotification:
    """Return daemon-ready metadata without I/O or side-model work."""
    result = _router.route(payload.prompt)
    return HookNotification(
        session_id=payload.session_id,
        transcript_path=payload.transcript_path,
        cwd=payload.cwd,
        hook_event_name=payload.hook_event_name,
        prompt=payload.prompt,
        route=result.route,
    )


def notify_context_daemon(notification: HookNotification) -> None:
    """Best-effort, non-blocking handoff to the local Context Daemon.

    UDP intentionally gives the hook no dependency on daemon availability. A
    missing or restarting daemon must never delay or block Claude Code.
    """
    configured_port = os.environ.get("PAPER_CONTEXT_DAEMON_PORT")
    if not configured_port:
        return
    try:
        port = int(configured_port)
        if not 1 <= port <= 65535:
            return
        body = json.dumps({
            "session_id": notification.session_id,
            "transcript_path": notification.transcript_path,
            "cwd": notification.cwd,
            "hook_event_name": notification.hook_event_name,
            "prompt": notification.prompt,
            "route": notification.route.value,
        }).encode("utf-8")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.setblocking(False)
            client.sendto(body, ("127.0.0.1", port))
    except (OSError, ValueError):
        return


def pass_through() -> None:
    """Exit silently so Claude Code processes the original prompt."""
    raise SystemExit(0)


def block(reason: str) -> None:
    """Prevent Claude Code from processing a deflected conceptual question."""
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    sys.stdout.flush()
    raise SystemExit(0)


def _on_timeout(signum, frame) -> None:
    pass_through()


def main() -> None:
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _on_timeout)
        signal.alarm(HARD_TIMEOUT_SEC)

    notification = classify_payload(parse_hook_payload(sys.stdin.read()))
    notify_context_daemon(notification)
    if notification.route == Route.SIDE_LLM:
        block("Thinking - answer will appear shortly")
    pass_through()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # Fail open: a faulty router must never prevent Claude Code from working.
        pass_through()
