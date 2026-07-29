"""Background owner for active Claude Code session runtimes.

The daemon receives a fire-and-forget notification from ``classifier_hook``.
Its transcript synchronizer is injected so Phase 3 can add incremental file
watching without changing this lifecycle or the wire protocol.
"""

from __future__ import annotations

import json
import socketserver
from collections.abc import Callable
from pathlib import Path
from threading import Event, RLock, Thread, current_thread
from typing import Optional

try:
    from ..models import HookNotification, Route
except ImportError:  # pragma: no cover - supports direct execution
    from models import HookNotification, Route

from .runtime import SessionRuntime

TranscriptSynchronizer = Callable[[SessionRuntime], None]


class ContextDaemon:
    """Manages isolated session runtimes and coordinates synchronization."""

    def __init__(self, synchronizer: Optional[TranscriptSynchronizer] = None) -> None:
        self._runtimes: dict[str, SessionRuntime] = {}
        self._synchronizer = synchronizer
        self._lock = RLock()
        self._stop_event = Event()
        self._watch_thread: Optional[Thread] = None

    def receive(self, notification: HookNotification) -> SessionRuntime:
        """Register/update a session then request transcript synchronization."""
        if not notification.session_id:
            raise ValueError("context notifications require a session_id")

        with self._lock:
            runtime = self._runtimes.get(notification.session_id)
            if runtime is None:
                runtime = SessionRuntime(
                    session_id=notification.session_id,
                    transcript_path=notification.transcript_path,
                    cwd=notification.cwd,
                )
                self._runtimes[notification.session_id] = runtime
            runtime.update(
                transcript_path=notification.transcript_path,
                cwd=notification.cwd,
                hook_event_name=notification.hook_event_name,
                prompt=notification.prompt,
            )

        self.synchronize(runtime.session_id)
        return runtime

    def synchronize(self, session_id: str) -> None:
        """Run the installed synchronizer for a single session, if available."""
        with self._lock:
            runtime = self._runtimes.get(session_id)
        if runtime is None or self._synchronizer is None:
            return
        self._synchronizer(runtime)
        runtime.synchronization_requested = False

    def synchronize_all(self) -> None:
        """Synchronize every active session once."""
        for runtime in self.active_sessions():
            self.synchronize(runtime.session_id)

    def start_watching(self, interval_seconds: float = 0.25) -> None:
        """Start a tail-like background loop for every active session."""
        if interval_seconds <= 0:
            raise ValueError("watch interval must be positive")
        with self._lock:
            if self._watch_thread and self._watch_thread.is_alive():
                return
            self._stop_event.clear()
            self._watch_thread = Thread(
                target=self._watch_loop,
                args=(interval_seconds,),
                name="paper-context-daemon",
                daemon=True,
            )
            self._watch_thread.start()

    def stop_watching(self) -> None:
        """Stop the background watcher without discarding session runtimes."""
        self._stop_event.set()
        thread = self._watch_thread
        if thread and thread is not current_thread():
            thread.join(timeout=2)

    def _watch_loop(self, interval_seconds: float) -> None:
        while not self._stop_event.is_set():
            self.synchronize_all()
            self._stop_event.wait(interval_seconds)

    def runtime(self, session_id: str) -> Optional[SessionRuntime]:
        with self._lock:
            return self._runtimes.get(session_id)

    def active_sessions(self) -> tuple[SessionRuntime, ...]:
        with self._lock:
            return tuple(self._runtimes.values())


def notification_from_wire(data: dict[str, object]) -> HookNotification:
    """Validate the minimal UDP payload emitted by the classifier hook."""
    return HookNotification(
        session_id=str(data.get("session_id", "")),
        transcript_path=str(data.get("transcript_path", "")),
        cwd=str(data.get("cwd", "")),
        hook_event_name=str(data.get("hook_event_name", "UserPromptSubmit")),
        prompt=str(data.get("prompt", "")),
        route=Route(str(data.get("route", Route.CLAUDE.value))),
    )


class _NotificationHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        raw = self.request[0]
        try:
            body = json.loads(raw.decode("utf-8"))
            if isinstance(body, dict):
                self.server.daemon.receive(notification_from_wire(body))
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            return


class ContextDaemonServer(socketserver.ThreadingUDPServer):
    """Loopback-only UDP endpoint for fire-and-forget hook notifications."""

    allow_reuse_address = True

    def __init__(self, daemon: ContextDaemon, port: int = 0) -> None:
        self.daemon = daemon
        super().__init__(("127.0.0.1", port), _NotificationHandler)


def create_context_daemon(checkpoint_path: Path) -> ContextDaemon:
    """Build the standard daemon with the Phase 3 incremental watcher."""
    from .checkpoints import CheckpointStore
    from .synchronizer import ContextSynchronizer
    from .transcript_watcher import TranscriptWatcher

    return ContextDaemon(synchronizer=ContextSynchronizer(TranscriptWatcher(CheckpointStore(checkpoint_path))))
