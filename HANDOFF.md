# Project Overview

PAPeR is a companion to Claude Code. Claude remains the coding agent; PAPeR routes conceptual questions to a cheaper secondary LLM and maintains session-aware context for that sidecar. The governing architecture for this milestone is:

```
Claude hook → prompt router → Context Daemon → incremental transcript watcher
→ typed transcript parser → Session Memory → ChromaDB → Retrieval Engine
→ secondary LLM
```

Only the Context Synchronization pipeline is in scope. Project graph, long-term personalization, analytics, savings reports, and behavior databases remain future work.

# Completed Work

| Phase | Commit | Summary |
|---|---|---|
| 1 | `73a06c9` | Stabilized hook routing. `PromptRouter` is canonical; `ScoringRouter` is a compatibility facade. Hook payload/session metadata contracts were added. |
| 2 | `1c81c6f` | Added Context Daemon, per-session runtimes, local UDP hook notification endpoint, and asynchronous hook-to-daemon handoff. |
| 3 | `d797eb9` | Added per-session checkpoint storage and a tail-like watcher with byte offsets, partial-line safety, rotation handling, and daemon polling. |
| 4 | `4ed30ec` | Added typed transcript domain events and an incremental JSONL parser. |
| 5 | `3788c14` | Added bounded Session Memory and wired watcher → parser → memory into the standard daemon factory. |

# Repository State

Relevant source is in `primary_router/`.

- `classifier_hook.py`: Claude Code `UserPromptSubmit` adapter. Uses `PromptRouter`; emits a best-effort UDP notification when `PAPER_CONTEXT_DAEMON_PORT` is configured.
- `router.py`, `features.py`, `patterns.py`, `rules.py`, `models.py`: deterministic existing routing pipeline. Preserve this API.
- `scoring_router.py`: backwards-compatible facade over `PromptRouter`; do not restore a second classifier.
- `context/runtime.py`: `SessionRuntime`, one instance per Claude `session_id`.
- `context/daemon.py`: `ContextDaemon`, UDP server, background poll loop, and `create_context_daemon(checkpoint_path)` factory.
- `context/checkpoints.py`: durable JSON checkpoint store keyed by session ID.
- `context/transcript_watcher.py`: `TranscriptWatcher`, `TranscriptLine`, `WatchBatch`.
- `context/events.py`: typed events: `UserPrompt`, `AssistantMessage`, `ToolUse`, `FileRead`, `FileEdit`, `CommandRun`, `ErrorObserved`, `DesignDecision`.
- `context/transcript_parser.py`: parses only watcher-supplied completed JSONL lines.
- `context/session_memory.py`: `SessionMemory` and `SessionMemorySnapshot`.
- `context/synchronizer.py`: standard watcher → parser → Session Memory chain.

Tests exist in `primary_router/test_*.py` for routing, hook contracts, daemon lifecycle, watcher behavior, parser events, and Session Memory.

# Current Architecture

1. Claude Code invokes `classifier_hook.py` with `prompt`, `session_id`, `transcript_path`, and `cwd`.
2. The hook returns a normal Claude pass-through for tasks or blocks side-LLM questions. It never reads a transcript or calls a model.
3. A UDP notification sends the same metadata to the local daemon without waiting for a response.
4. `ContextDaemon` owns one `SessionRuntime` per session and periodically invokes its synchronizer.
5. `TranscriptWatcher` reads only appended bytes after its persisted checkpoint. First observation starts at EOF; it does not replay an already-existing transcript. Incomplete final JSONL lines remain unread until completed.
6. `TranscriptParser` turns watched JSONL records into typed events.
7. `SessionMemory` consumes those events and maintains current task, recent files, architecture notes, errors, commands, and a deterministic rolling summary.

ChromaDB and retrieval do not yet exist. The side-model pipeline historically present in `answer_pipeline.py`/`side_model.py` must eventually consume Retrieval Engine output only; it must not reread transcripts.

# Phase 6 Specification

## Objective

Add ChromaDB-backed semantic context storage fed asynchronously from the incremental synchronization pipeline.

## Deliverables

- Add a ChromaDB dependency and a configurable embedding strategy.
- Add a semantic selector that accepts typed transcript events and excludes noise such as `pwd`, `ls`, repetitive reads, and successful shell output.
- Create deterministic IDs using session ID, event/source identity, and normalized-content hash.
- Upsert, never blindly insert, session-scoped documents with metadata including `session_id`, event type, byte offset, timestamp, and optional path.
- Add an asynchronous embedding/upsert queue with bounded capacity, graceful shutdown, and failure isolation. Context synchronization must continue when Chroma or embeddings fail.
- Add unit tests for filtering, deterministic IDs, metadata/session isolation, duplicate upserts, and queue behavior.
- Document required environment configuration and local persistence path.

## Likely files

Create `primary_router/retrieval/` containing at least:

- `semantic_selector.py`
- `embeddings.py`
- `chroma_store.py`
- `indexing_queue.py`
- `models.py` if retrieval-specific contracts are needed

Modify:

- `requirements.txt` and `primary_router/requirements.txt`
- `context/synchronizer.py` to publish parsed events to the queue after updating Session Memory
- `context/runtime.py` only if lifecycle ownership of an indexing queue is needed
- package exports and tests

# Design Decisions and Invariants

- The attached architecture diagram governs the design. Do not redesign the system.
- One authoritative routing implementation: `PromptRouter`.
- The hook is hot-path, deterministic, fail-open, and non-blocking.
- The daemon owns transcript synchronization; inference must never reread the transcript.
- Transcript reading is append-only and offset-based. Never rescan the same transcript from byte zero.
- Session isolation is mandatory. All vector metadata and queries must filter by `session_id`.
- Chroma receives only semantic records, never raw transcript dumps.
- Use standard-library concurrency unless a dependency is clearly necessary.
- Keep external services optional: Chroma/indexing errors must not block Claude Code, watcher checkpoints, or Session Memory.
- Existing provider adapters in `side_model.py` should be reused later, not replaced.

# Remaining TODOs

1. Phase 6: ChromaDB, semantic filtering, deterministic upserts, async indexing.
2. Phase 7: Retrieval Engine combining `SessionMemory.snapshot()` and session-filtered Chroma semantic hits into a compact context package.
3. Phase 8: Change the side-model pipeline to accept Retrieval Engine output only; remove all direct transcript reads from its inference path.
4. Restore a usable Python runtime and run the full pytest suite.
5. Add an operational daemon entry point/process manager and actual popup transport when product integration reaches those milestones.

## Important edge cases

- Transcript rotation/truncation is handled as a new file; do not regress this behavior.
- Chroma IDs must stay stable on replay/restart.
- Queue overload must drop/defer indexing safely without losing Session Memory updates.
- Embeddings may fail or be unavailable; record/log the failure without failing the daemon.
- Do not accidentally index text from Claude private thinking blocks or tool-result noise.

# Risks

- No usable local Python interpreter is registered. `venv` points at a missing Python 3.10 executable; `py -0p` reported no registered runtimes.
- `chromadb` and an embedding provider are absent from both requirements files and the virtual environment.
- Tests have been written but not executed because of the Python-runtime issue. Static `git diff --check` passed at each completed phase.
- Unrelated untracked workspace items exist (`Microsoft/`, `venv/`, generated `__pycache__`, root `requirements.txt`). Do not add them to feature commits unintentionally.

# Suggested First Prompt

```
Read HANDOFF.md and SESSION_STATE.json, then implement Phase 6 only. First inspect the current repository and confirm the Python/Chroma dependency situation. Follow the established Context Daemon → watcher → parser → Session Memory architecture. Add semantic filtering, deterministic session-scoped Chroma upserts, and a bounded asynchronous indexing queue. Do not implement retrieval or modify the side-model inference pipeline. Add tests, run them if a Python runtime is available, and commit only the completed Phase 6 subsystem.
```
