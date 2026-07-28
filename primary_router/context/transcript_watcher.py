"""Tail-like incremental watcher for append-only Claude Code JSONL transcripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from .checkpoints import CheckpointStore, TranscriptCheckpoint
from .runtime import SessionRuntime


@dataclass(frozen=True, slots=True)
class TranscriptLine:
    byte_start: int
    byte_end: int
    text: str


@dataclass(frozen=True, slots=True)
class WatchBatch:
    session_id: str
    start_offset: int
    end_offset: int
    lines: tuple[TranscriptLine, ...]


class TranscriptWatcher:
    """Reads only bytes appended after a session's stored checkpoint.

    A first observation starts at EOF, matching ``tail -f`` semantics. This is
    intentional: the watcher never replays an existing transcript just because
    PAPeR starts during an already-running Claude session.
    """

    def __init__(self, checkpoints: CheckpointStore) -> None:
        self.checkpoints = checkpoints
        self._lock = RLock()

    def __call__(self, runtime: SessionRuntime) -> None:
        batch = self.read(runtime)
        runtime.transcript_offset = batch.end_offset
        runtime.pending_transcript_lines.extend(batch.lines)

    def read(self, runtime: SessionRuntime) -> WatchBatch:
        with self._lock:
            return self._read(runtime)

    def _read(self, runtime: SessionRuntime) -> WatchBatch:
        path = Path(runtime.transcript_path)
        if not path.is_file():
            return WatchBatch(runtime.session_id, runtime.transcript_offset, runtime.transcript_offset, ())

        stat = path.stat()
        checkpoint = self.checkpoints.get(runtime.session_id)
        identity = (stat.st_dev, stat.st_ino)

        if checkpoint is None:
            # First contact tails from EOF; no historical rescan.
            self._save(runtime, path, stat.st_size, identity)
            return WatchBatch(runtime.session_id, stat.st_size, stat.st_size, ())

        offset = checkpoint.offset
        same_file = checkpoint.transcript_path == str(path) and (checkpoint.device, checkpoint.inode) == identity
        if not same_file or stat.st_size < offset:
            # A replacement is a new transcript. Start at its beginning once;
            # the old transcript is never reread.
            offset = 0

        with path.open("rb") as transcript:
            transcript.seek(offset)
            payload = transcript.read()

        complete_size = 0
        lines: list[TranscriptLine] = []
        cursor = offset
        for raw_line in payload.splitlines(keepends=True):
            if not raw_line.endswith((b"\n", b"\r")):
                break
            end = cursor + len(raw_line)
            lines.append(TranscriptLine(cursor, end, raw_line.decode("utf-8", errors="replace").rstrip("\r\n")))
            cursor = end
            complete_size += len(raw_line)

        end_offset = offset + complete_size
        self._save(runtime, path, end_offset, identity)
        return WatchBatch(runtime.session_id, offset, end_offset, tuple(lines))

    def _save(self, runtime: SessionRuntime, path: Path, offset: int, identity: tuple[int, int]) -> None:
        self.checkpoints.put(TranscriptCheckpoint(
            session_id=runtime.session_id,
            transcript_path=str(path),
            offset=offset,
            device=identity[0],
            inode=identity[1],
        ))
