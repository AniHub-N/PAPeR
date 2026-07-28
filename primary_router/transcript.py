"""
transcript.py — Module 2 (grounding, trivial tier): the session-transcript tail.

Claude Code already writes the full live session to a JSONL transcript. We only
READ it — nothing custom writes it. This module turns that raw JSONL into a
compact, plain-text conversation tail suitable for grounding the side model in
Phase 2.

Two harvest strategies, both shipped in v1:

  v1    recent tail — the last N human/assistant *text* turns, char-capped.
        Tool noise (thinking, tool_use, tool_result) is dropped.

  v1.5  free summaries — when /compact or an auto-compaction runs, Claude Code
        writes its OWN summary of everything so far back into the transcript, as
        a `user` record flagged `isCompactSummary: true`. That summary already
        compresses the whole earlier session, for free. We anchor on the LAST
        such summary and only tail the turns that came after it. A long session
        then costs us "summary + short tail" instead of a giant raw dump.

Transcript location:
  Claude Code passes `transcript_path` in the hook stdin JSON — Phase 2 should
  use that directly (see `from_hook_input`). For standalone testing we also
  resolve it from cwd:
      ~/.claude/projects/<slug>/<session-id>.jsonl   (slug = cwd, '/' -> '-')
"""

import json
import os
from pathlib import Path

# Default budgets. Tail is char-capped so one deflected question never ships a
# runaway context to the (user-billed) side model.
MAX_CHARS = 6000        # overall cap on the assembled tail
MAX_MESSAGES = 20       # keep at most this many recent turns
MAX_MSG_CHARS = 1200    # per-message cap so one pasted blob can't eat the budget
MAX_TOOL_CHARS = 240    # per tool line (name+arg, or an error head)
SUMMARY_BUDGET_FRAC = 0.5   # at most this fraction of MAX_CHARS goes to the summary


# ---------------------------------------------------------------------------
# Locating the transcript
# ---------------------------------------------------------------------------

def project_dir(cwd=None):
    """~/.claude/projects/<slug> for the given cwd (default: current dir)."""
    cwd = os.path.abspath(cwd or os.getcwd())
    slug = cwd.replace(os.sep, "-")
    return Path.home() / ".claude" / "projects" / slug


def _has_conversation(path):
    """True if the JSONL holds at least one user/assistant turn.

    The VS Code / Desktop surfaces write SEVERAL .jsonl files per session — the
    conversation itself, plus sidecar files that only hold queue-operation /
    system / ai-title records. The sidecar files are often the most-recently
    modified, so 'newest by mtime' alone can land on a file with no turns at all
    (observed empirically). We use this to skip those."""
    try:
        for rec in _iter_records(path):
            if rec.get("type") in ("user", "assistant"):
                return True
    except OSError:
        pass
    return False


def latest_transcript(cwd=None):
    """Most-recently-modified .jsonl that actually CONTAINS a conversation.

    Convenience for standalone testing / hook fallback. Prefers the newest file
    with real user/assistant turns over a newer queue-only sidecar; falls back
    to plain-newest only if none contain conversation."""
    d = project_dir(cwd)
    if not d.is_dir():
        return None
    files = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        if _has_conversation(f):
            return f
    return files[0] if files else None


def from_hook_input(hook_json):
    """Pull the transcript path out of a Claude Code hook stdin payload.

    Claude Code includes `transcript_path` (and `cwd`, `session_id`) in the JSON
    it pipes to every hook. We honor that path ONLY if it actually contains
    conversation — on VS Code/Desktop the passed path can point at a queue-only
    sidecar, in which case we fall back to the newest conversation-bearing file
    for the same project (see _has_conversation)."""
    path = hook_json.get("transcript_path")
    if path and Path(path).is_file() and _has_conversation(Path(path)):
        return Path(path)
    return latest_transcript(hook_json.get("cwd"))


# ---------------------------------------------------------------------------
# Parsing records
# ---------------------------------------------------------------------------

def _iter_records(path):
    """Yield parsed JSON objects from the transcript, skipping unparseable lines.

    The transcript is append-only JSONL; a partially-flushed last line while a
    session is live is normal, so we swallow decode errors rather than fail."""
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _is_compact_summary(rec):
    return bool(rec.get("isCompactSummary"))


def _text_of(rec):
    """Extract human-readable text from a user/assistant record.

    content is either a plain string or a list of blocks. We keep only the
    conversational text: user text (+ plain-string content) and assistant text.
    thinking / tool_use / tool_result blocks are dropped — that's the noise the
    tail exists to avoid shipping."""
    msg = rec.get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(p for p in parts if p).strip()


def _clip(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " …[truncated]"


# Priority order for the single most-identifying argument of a tool call.
_TOOL_ARG_KEYS = ("file_path", "command", "pattern", "query", "url", "prompt",
                  "skill", "notebook_path")


def _activity_of(rec):
    """Compact one-liners for recent tool activity — what Claude was just doing.

    tool_use   -> name + its most identifying argument (file / command / …).
    tool_result -> kept ONLY when it errored (build/test failures); successful
    result bodies are dropped, since the tool_use line already says what ran and
    those bodies are large, low-value-per-token file dumps."""
    content = (rec.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    out = []
    for b in content:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "tool_use":
            inp = b.get("input") or {}
            salient = ""
            for k in _TOOL_ARG_KEYS:
                v = inp.get(k)
                if isinstance(v, str) and v.strip():
                    salient = _clip(" ".join(v.split()), 100)
                    break
            name = b.get("name", "tool")
            out.append(f"⚙ {name}: {salient}" if salient else f"⚙ {name}")
        elif b.get("type") == "tool_result" and b.get("is_error"):
            c = b.get("content")
            if isinstance(c, list):
                c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
            c = " ".join(c.split()) if isinstance(c, str) else ""
            out.append("✖ error: " + _clip(c, MAX_TOOL_CHARS))
    return out


def _render_record(rec, max_msg_chars):
    """One transcript record -> a compact block: prose line + any activity lines."""
    role = "User" if rec.get("type") == "user" else "Assistant"
    lines = []
    prose = _text_of(rec)
    if prose:
        lines.append(f"{role}: {_clip(prose, max_msg_chars)}")
    lines.extend(_activity_of(rec))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Building the tail
# ---------------------------------------------------------------------------

def build_tail(path, *, max_chars=MAX_CHARS, max_messages=MAX_MESSAGES,
               max_msg_chars=MAX_MSG_CHARS):
    """Turn a transcript JSONL into a compact plain-text grounding tail.

    Strategy (v1 + v1.5 together):
      1. Scan all records once.
      2. Anchor on the LAST isCompactSummary — everything before it is already
         summarized by Claude Code, so we don't re-read it (v1.5).
      3. Collect user/assistant text turns after that anchor; tail to the last
         `max_messages` (v1).
      4. Budget: the summary gets up to SUMMARY_BUDGET_FRAC of max_chars, the
         recent tail gets the rest; oldest turns drop first if over budget.

    Returns a string ("" if the transcript is missing/empty)."""
    if not path or not Path(path).is_file():
        return ""

    records = list(_iter_records(path))
    if not records:
        return ""

    # (2) find the last compaction summary, if any.
    anchor = -1
    summary_text = ""
    for i, rec in enumerate(records):
        if rec.get("type") == "user" and _is_compact_summary(rec):
            anchor = i
            summary_text = _text_of(rec)

    # (3) conversational turns strictly after the anchor.
    turns = []
    for rec in records[anchor + 1:]:
        if rec.get("type") not in ("user", "assistant"):
            continue
        if _is_compact_summary(rec):
            continue  # defensive; anchor already excludes it
        block = _render_record(rec, max_msg_chars)
        if block:  # skip thinking-only / empty records
            turns.append(block)

    turns = turns[-max_messages:]

    # (4) assemble under budget.
    out = []
    remaining = max_chars

    if summary_text:
        summary_cap = int(max_chars * SUMMARY_BUDGET_FRAC)
        summary_block = "## Earlier in this session (Claude Code summary)\n" + \
            _clip(summary_text, summary_cap)
        out.append(summary_block)
        remaining -= len(summary_block)

    # Add recent turns newest-first into the remaining budget, then re-order.
    kept = []
    for block in reversed(turns):
        if len(block) + 2 > remaining and kept:
            break  # keep what we have; oldest turns are the ones dropped
        kept.append(block)
        remaining -= len(block) + 2
    kept.reverse()

    if kept:
        out.append("## Recent turns & activity\n" + "\n\n".join(kept))

    return "\n\n".join(out).strip()


# ---------------------------------------------------------------------------
# Standalone test harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = latest_transcript()
        if target:
            print(f"[transcript] using latest: {target.name}", file=sys.stderr)

    if not target or not target.is_file():
        print("[transcript] no transcript found — pass a path as arg 1",
              file=sys.stderr)
        sys.exit(1)

    tail = build_tail(target)
    print(tail)
    print(f"\n[transcript] {len(tail)} chars from {target.name}", file=sys.stderr)
