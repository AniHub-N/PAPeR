"""Incremental watcher → parser → Session Memory synchronization chain."""

from .runtime import SessionRuntime
from .transcript_parser import TranscriptParser
from .transcript_watcher import TranscriptWatcher


class ContextSynchronizer:
    def __init__(self, watcher: TranscriptWatcher, parser: TranscriptParser | None = None) -> None:
        self.watcher = watcher
        self.parser = parser or TranscriptParser()

    def __call__(self, runtime: SessionRuntime) -> None:
        self.watcher(runtime)
        for event in self.parser.drain(runtime):
            runtime.session_memory.apply(event)
