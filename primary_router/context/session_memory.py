"""Bounded, in-memory working context for one Claude Code session."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock

from .events import (
    AssistantMessage,
    CommandRun,
    DesignDecision,
    ErrorObserved,
    FileEdit,
    FileRead,
    TranscriptEvent,
    UserPrompt,
)


@dataclass(frozen=True, slots=True)
class SessionMemorySnapshot:
    current_task: str
    recent_files: tuple[str, ...]
    architecture_notes: tuple[str, ...]
    recent_errors: tuple[str, ...]
    recent_commands: tuple[str, ...]
    rolling_summary: str


@dataclass
class SessionMemory:
    """Current high-signal session state; it is not a transcript archive."""

    max_items: int = 12
    current_task: str = ""
    recent_files: list[str] = field(default_factory=list)
    architecture_notes: list[str] = field(default_factory=list)
    recent_errors: list[str] = field(default_factory=list)
    recent_commands: list[str] = field(default_factory=list)
    rolling_summary: str = ""
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def apply(self, event: TranscriptEvent) -> None:
        with self._lock:
            if isinstance(event, UserPrompt):
                self.current_task = event.text
            elif isinstance(event, (FileRead, FileEdit)) and event.file_path:
                self._remember(self.recent_files, event.file_path)
            elif isinstance(event, CommandRun) and event.command:
                self._remember(self.recent_commands, event.command)
            elif isinstance(event, ErrorObserved) and event.text:
                self._remember(self.recent_errors, event.text)
            elif isinstance(event, DesignDecision) and event.text:
                self._remember(self.architecture_notes, event.text)
            elif isinstance(event, AssistantMessage) and event.text and "architecture" in event.text.lower():
                self._remember(self.architecture_notes, event.text)
            self.rolling_summary = self._render_summary()

    def snapshot(self) -> SessionMemorySnapshot:
        with self._lock:
            return SessionMemorySnapshot(
                current_task=self.current_task,
                recent_files=tuple(self.recent_files),
                architecture_notes=tuple(self.architecture_notes),
                recent_errors=tuple(self.recent_errors),
                recent_commands=tuple(self.recent_commands),
                rolling_summary=self.rolling_summary,
            )

    def _remember(self, values: list[str], value: str) -> None:
        value = " ".join(value.split())
        if not value:
            return
        if value in values:
            values.remove(value)
        values.append(value)
        del values[:-self.max_items]

    def _render_summary(self) -> str:
        parts: list[str] = []
        if self.current_task:
            parts.append(f"Current task: {self.current_task}")
        if self.recent_files:
            parts.append("Recent files: " + ", ".join(self.recent_files[-3:]))
        if self.recent_errors:
            parts.append("Recent errors: " + " | ".join(self.recent_errors[-2:]))
        if self.architecture_notes:
            parts.append("Architecture notes: " + " | ".join(self.architecture_notes[-2:]))
        return "\n".join(parts)
