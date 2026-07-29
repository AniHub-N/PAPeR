"""Convert incremental Claude Code JSONL records into typed domain events."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from .events import (
    AssistantMessage,
    CommandRun,
    DesignDecision,
    ErrorObserved,
    FileEdit,
    FileRead,
    ToolUse,
    TranscriptEvent,
    UserPrompt,
)
from .runtime import SessionRuntime
from .transcript_watcher import TranscriptLine


_DESIGN_DECISION = re.compile(r"\b(decision|architecture|design|trade-?off|we(?:'| wi)ll)\b", re.IGNORECASE)
_READ_TOOLS = {"read"}
_EDIT_TOOLS = {"edit", "write", "notebookedit"}
_COMMAND_TOOLS = {"bash", "shell", "command"}


class TranscriptParser:
    """Parses only completed lines supplied by :class:`TranscriptWatcher`."""

    def drain(self, runtime: SessionRuntime) -> list[TranscriptEvent]:
        lines = tuple(line for line in runtime.pending_transcript_lines if isinstance(line, TranscriptLine))
        runtime.pending_transcript_lines.clear()
        return self.parse(runtime.session_id, lines)

    def parse(self, session_id: str, lines: Iterable[TranscriptLine]) -> list[TranscriptEvent]:
        events: list[TranscriptEvent] = []
        for line in lines:
            try:
                record = json.loads(line.text)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            events.extend(self._parse_record(session_id, line, record))
        return events

    def _parse_record(self, session_id: str, line: TranscriptLine, record: dict[str, object]) -> list[TranscriptEvent]:
        timestamp = str(record.get("timestamp", ""))
        event_kwargs = {
            "session_id": session_id,
            "byte_start": line.byte_start,
            "byte_end": line.byte_end,
            "timestamp": timestamp,
        }
        message = record.get("message")
        if not isinstance(message, dict):
            return []
        content = message.get("content")
        blocks = content if isinstance(content, list) else [{"type": "text", "text": content}] if isinstance(content, str) else []
        events: list[TranscriptEvent] = []
        text_parts: list[str] = []

        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text" and isinstance(block.get("text"), str):
                text_parts.append(block["text"].strip())
            elif block_type == "tool_use":
                events.append(self._tool_event(event_kwargs, block))
            elif block_type == "tool_result" and block.get("is_error"):
                events.append(ErrorObserved(
                    **event_kwargs,
                    text=self._block_text(block),
                    tool_name=str(block.get("tool_name", "")),
                ))

        text = "\n".join(part for part in text_parts if part).strip()
        record_type = record.get("type")
        if text and record_type == "user":
            events.insert(0, UserPrompt(**event_kwargs, text=text))
        elif text and record_type == "assistant":
            events.insert(0, AssistantMessage(**event_kwargs, text=text))
            if _DESIGN_DECISION.search(text):
                events.append(DesignDecision(**event_kwargs, text=text))
        return events

    def _tool_event(self, event_kwargs: dict[str, object], block: dict[str, object]) -> ToolUse:
        tool_name = str(block.get("name", "tool"))
        arguments = block.get("input") if isinstance(block.get("input"), dict) else {}
        normalized = tool_name.lower()
        file_path = str(arguments.get("file_path", arguments.get("path", "")))
        if normalized in _READ_TOOLS:
            return FileRead(**event_kwargs, tool_name=tool_name, arguments=arguments, file_path=file_path)
        if normalized in _EDIT_TOOLS:
            return FileEdit(**event_kwargs, tool_name=tool_name, arguments=arguments, file_path=file_path)
        if normalized in _COMMAND_TOOLS:
            return CommandRun(**event_kwargs, tool_name=tool_name, arguments=arguments, command=str(arguments.get("command", "")))
        return ToolUse(**event_kwargs, tool_name=tool_name, arguments=arguments)

    @staticmethod
    def _block_text(block: dict[str, object]) -> str:
        content = block.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
        return ""
