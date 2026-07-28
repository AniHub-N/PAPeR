"""Durable, per-session checkpoints for incremental transcript reads."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock


@dataclass(frozen=True, slots=True)
class TranscriptCheckpoint:
    session_id: str
    transcript_path: str
    offset: int
    device: int
    inode: int


class CheckpointStore:
    """Small JSON checkpoint store with atomic replacement on each update."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()

    def get(self, session_id: str) -> TranscriptCheckpoint | None:
        with self._lock:
            records = self._read()
            data = records.get(session_id)
            return TranscriptCheckpoint(**data) if isinstance(data, dict) else None

    def put(self, checkpoint: TranscriptCheckpoint) -> None:
        with self._lock:
            records = self._read()
            records[checkpoint.session_id] = asdict(checkpoint)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(json.dumps(records, sort_keys=True), encoding="utf-8")
            temporary.replace(self.path)

    def _read(self) -> dict[str, object]:
        try:
            content = self.path.read_text(encoding="utf-8")
            loaded = json.loads(content)
            return loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
