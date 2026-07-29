"""Typed domain events extracted from Claude Code transcript records."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptEvent:
    session_id: str
    byte_start: int
    byte_end: int
    timestamp: str = ""


@dataclass(frozen=True, slots=True)
class UserPrompt(TranscriptEvent):
    text: str = ""


@dataclass(frozen=True, slots=True)
class AssistantMessage(TranscriptEvent):
    text: str = ""


@dataclass(frozen=True, slots=True)
class ToolUse(TranscriptEvent):
    tool_name: str = ""
    arguments: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class FileRead(ToolUse):
    file_path: str = ""


@dataclass(frozen=True, slots=True)
class FileEdit(ToolUse):
    file_path: str = ""


@dataclass(frozen=True, slots=True)
class CommandRun(ToolUse):
    command: str = ""


@dataclass(frozen=True, slots=True)
class ErrorObserved(TranscriptEvent):
    text: str = ""
    tool_name: str = ""


@dataclass(frozen=True, slots=True)
class DesignDecision(TranscriptEvent):
    text: str = ""
