from primary_router.context.checkpoints import CheckpointStore
from primary_router.context.runtime import SessionRuntime
from primary_router.context.transcript_watcher import TranscriptWatcher


def test_watcher_tails_only_new_complete_jsonl_lines(tmp_path):
    transcript = tmp_path / "session.jsonl"
    transcript.write_bytes(b'{"old": true}\n')
    watcher = TranscriptWatcher(CheckpointStore(tmp_path / "checkpoints.json"))
    runtime = SessionRuntime("session-1", str(transcript), str(tmp_path))

    assert watcher.read(runtime).lines == ()

    transcript.write_bytes(b'{"old": true}\n{"new": 1}\n{"partial"')
    batch = watcher.read(runtime)

    assert [line.text for line in batch.lines] == ['{"new": 1}']
    transcript.write_bytes(b'{"old": true}\n{"new": 1}\n{"partial": 2}\n')
    assert [line.text for line in watcher.read(runtime).lines] == ['{"partial": 2}']


def test_watcher_keeps_independent_offsets_per_session(tmp_path):
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first.write_text("", encoding="utf-8")
    second.write_text("", encoding="utf-8")
    watcher = TranscriptWatcher(CheckpointStore(tmp_path / "checkpoints.json"))
    first_runtime = SessionRuntime("one", str(first), str(tmp_path))
    second_runtime = SessionRuntime("two", str(second), str(tmp_path))

    watcher.read(first_runtime)
    watcher.read(second_runtime)
    first.write_text('{"first": 1}\n', encoding="utf-8")
    second.write_text('{"second": 2}\n', encoding="utf-8")

    assert [line.text for line in watcher.read(first_runtime).lines] == ['{"first": 1}']
    assert [line.text for line in watcher.read(second_runtime).lines] == ['{"second": 2}']
