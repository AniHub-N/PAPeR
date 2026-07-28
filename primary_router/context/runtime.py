"""Per-session runtime metadata owned by the Context Daemon."""

from dataclasses import dataclass, field
from time import time


@dataclass(slots=True)
class SessionRuntime:
    """Mutable runtime state for one active Claude Code session.

    Transcript offsets and session memory are deliberately introduced by later
    phases. The daemon owns this object now, so those additions do not change
    the hook-to-daemon contract.
    """

    session_id: str
    transcript_path: str
    cwd: str
    last_hook_event: str = ""
    last_prompt: str = ""
    last_activity_at: float = field(default_factory=time)
    synchronization_requested: bool = True
    transcript_offset: int = 0
    pending_transcript_lines: list[str] = field(default_factory=list)

    def update(self, *, transcript_path: str, cwd: str, hook_event_name: str, prompt: str) -> None:
        if transcript_path:
            self.transcript_path = transcript_path
        if cwd:
            self.cwd = cwd
        self.last_hook_event = hook_event_name
        self.last_prompt = prompt
        self.last_activity_at = time()
        self.synchronization_requested = True
