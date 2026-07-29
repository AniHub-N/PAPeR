#!/usr/bin/env python3
"""
tier1.py — the Slow-loop Tier-1 reflector (Module 6).

Runs AFTER a session (on the Stop / SessionEnd hook, in the background). It does
NOT touch the fast loop and never blocks a live session.

Pipeline (uses the ported context/ package):

    full session transcript (JSONL)
      -> TranscriptParser            -> typed events
      -> SessionMemory               -> distilled high-signal state
      -> mechanical checks (no LLM)  -> countable facts
      -> ONE LLM call vs rulebook.md -> session report + 5-6 points
      -> store.log_report()          -> read later by Tier-2 (phase 2)

Split, per CLAUDE.md: the countable things (re-reads, edits, errors, length) are
mechanical; only the judgment (why it happened, how to phrase a lesson) goes to
the model, using the rulebook as instructions rather than logic.

Full-transcript by design: Tier-1 reads the WHOLE JSONL through the same parser
the live daemon uses (parser.parse accepts any lines), so it works whether or not
the in-session daemon was running — approach (B) from the integration note.

Entry points:
    echo '{"transcript_path": "...", "session_id": "..."}' | python3 sidecar/tier1.py
    python3 sidecar/tier1.py <transcript.jsonl>        # standalone / testing
    python3 sidecar/tier1.py <transcript.jsonl> --dry-run   # facts only, no LLM

FAIL-SAFE: any error exits 0 without raising — a failed reflection must never
disrupt the end of a session.
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "primary_router"))

# load .env so the reflector uses the same provider/key config as the hooks
try:
    from primary_router.side_model import _load_dotenv
    _load_dotenv()
except Exception:
    pass

RULEBOOK = Path(__file__).resolve().parent / "rulebook.md"


# ---------------------------------------------------------------------------
# 1. Full-transcript parse -> typed events -> distilled session memory
# ---------------------------------------------------------------------------

def build_memory(transcript_path, session_id="", cwd=None):
    """Read the ENTIRE transcript for the session that just ended and fold it
    into a SessionMemory snapshot + the raw event list (best-effort).

    We trust SessionEnd's transcript_path: each Claude Code session is its own
    <session-id>.jsonl, so this IS the right file. We deliberately do NOT fall
    back to another file — an empty transcript means the session had no Claude
    turns (e.g. it was all off-quota deflected questions), which the report
    should state honestly rather than reflecting on a different session."""
    from context.transcript_parser import TranscriptParser
    from context.transcript_watcher import TranscriptLine
    from context.session_memory import SessionMemory

    p = Path(transcript_path)
    lines = []
    if p.is_file():
        with p.open("r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                raw = raw.strip()
                if raw:
                    lines.append(TranscriptLine(0, 0, raw))

    events = TranscriptParser().parse(session_id or "session", lines)
    mem = SessionMemory()
    for ev in events:
        mem.apply(ev)
    return events, mem.snapshot()


# ---------------------------------------------------------------------------
# 2. Mechanical checks — countable, no LLM (CLAUDE.md: mechanical vs judgment)
# ---------------------------------------------------------------------------

def load_deflections(session_id):
    """Off-quota questions asked to the side model during this session. These
    live in PAPeR's own DB (not Claude's transcript), so a session that only
    used the side model would otherwise look empty."""
    try:
        from db import store
        conn = store.connect()
        try:
            return store.deflections_for_session(conn, session_id)
        finally:
            conn.close()
    except Exception:
        return []


def mechanical_stats(events):
    from context.events import (
        UserPrompt, AssistantMessage, FileRead, FileEdit, CommandRun, ErrorObserved,
    )
    reads = [e.file_path for e in events if isinstance(e, FileRead) and e.file_path]
    read_counts = Counter(reads)
    rereads = {f: n for f, n in read_counts.items() if n > 1}
    return {
        "user_prompts": sum(isinstance(e, UserPrompt) for e in events),
        "assistant_msgs": sum(isinstance(e, AssistantMessage) for e in events),
        "files_read": len(reads),
        "distinct_files_read": len(read_counts),
        "reread_files": rereads,          # {file: times_read} for files read >1x
        "reread_waste": sum(n - 1 for n in rereads.values()),  # redundant reads
        "files_edited": sum(isinstance(e, FileEdit) for e in events),
        "commands_run": sum(isinstance(e, CommandRun) for e in events),
        "errors_observed": sum(isinstance(e, ErrorObserved) for e in events),
        "total_events": len(events),
    }


# ---------------------------------------------------------------------------
# 3. One LLM call against the rulebook -> report + 5-6 points
# ---------------------------------------------------------------------------

def _facts_prompt(stats, snap, cwd, deflections=()):
    reread = ", ".join(f"{f} (x{n})" for f, n in stats["reread_files"].items()) or "none"
    dq = "\n".join(f"  - {d['question']}" for d in deflections) or "  none"
    return (
        "SESSION FACTS (mechanical):\n"
        f"- user prompts to Claude: {stats['user_prompts']}\n"
        f"- off-quota questions to the side model: {len(deflections)}\n"
        f"- files read: {stats['files_read']} "
        f"(distinct {stats['distinct_files_read']}, redundant re-reads {stats['reread_waste']})\n"
        f"- re-read files: {reread}\n"
        f"- files edited: {stats['files_edited']}\n"
        f"- commands run: {stats['commands_run']}\n"
        f"- errors observed: {stats['errors_observed']}\n\n"
        "OFF-QUOTA QUESTIONS THIS SESSION (answered by the side model):\n"
        f"{dq}\n"
        "(If the user repeatedly asked about the same thing, that is a strong "
        "signal it should be documented in CLAUDE.md — call it out.)\n\n"
        "DISTILLED SESSION MEMORY:\n"
        f"- current task: {snap.current_task or '(unknown)'}\n"
        f"- recent files: {', '.join(snap.recent_files) or 'none'}\n"
        f"- recent errors: {' | '.join(snap.recent_errors) or 'none'}\n"
        f"- recent commands: {' | '.join(snap.recent_commands) or 'none'}\n"
        f"- architecture notes: {' | '.join(snap.architecture_notes) or 'none'}\n\n"
        "Judge this session per your instructions and return the STRICT JSON now."
    )


def _parse_json(text):
    """Pull the JSON object out of a model reply (tolerates code fences / prose)."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[t.find("{"):] if "{" in t else t
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b != -1 and b > a:
        try:
            return json.loads(t[a:b + 1])
        except json.JSONDecodeError:
            pass
    return None


def reflect(stats, snap, cwd, deflections=()):
    """Make the single grounded LLM call. Returns (result_dict, usage)."""
    import side_model
    from answer_pipeline import load_claude_md

    system = RULEBOOK.read_text(encoding="utf-8") if RULEBOOK.is_file() else \
        "Summarize the session and return JSON {health_score, report, points_for_tier2}."
    text, usage = side_model.answer(
        _facts_prompt(stats, snap, cwd, deflections),
        claude_md=load_claude_md(cwd),
        system=system,
        max_tokens=4096,   # room for thinking + the full JSON report
    )
    parsed = _parse_json(text) or {
        "health_score": None, "report": [text.strip()[:500]], "points_for_tier2": [],
    }
    return parsed, usage


# ---------------------------------------------------------------------------
# 4. Persist for Tier-2
# ---------------------------------------------------------------------------

def write_report_file(session_id, result, stats, deflections=()):
    """Write a human-readable session report to reports/ so it's visible on disk
    (this is 'the file going through' — the DB feeds the next aggregation step,
    humans read this). Also refreshes reports/latest.md for quick access."""
    try:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        reports_dir = REPO / "reports"
        reports_dir.mkdir(exist_ok=True)
        sid = (session_id or "session")[:12]
        path = reports_dir / f"session-{stamp}-{sid}.md"

        rr = "none"
        if stats["reread_files"]:
            rr = ", ".join(f"{f} (x{n})" for f, n in stats["reread_files"].items())
        summary_lines = [f"- {b}" for b in result.get("report", [])] or ["- (none)"]
        point_lines = [f"- {p}" for p in result.get("points_for_tier2", [])] or ["- (none)"]

        lines = [
            f"# PAPeR session report — {stamp}",
            f"Session: {session_id or '(unknown)'}",
            f"Health score: {result.get('health_score', '—')}/100",
            "",
            "## Summary",
            *summary_lines,
            "",
            "## Suggested rules to remember (candidate CLAUDE.md / Skill updates)",
            *point_lines,
        ]
        if deflections:
            lines += [
                "",
                f"## Off-quota questions this session ({len(deflections)}, 0 Claude quota)",
                *[f"- {d['question']}" for d in deflections],
            ]
        lines += [
            "",
            "## Activity stats",
            f"- prompts to Claude: {stats['user_prompts']}",
            f"- off-quota questions (side model): {stats.get('off_quota_questions', 0)}",
            f"- files read: {stats['files_read']} "
            f"(distinct {stats['distinct_files_read']}, redundant re-reads {stats['reread_waste']})",
            f"- re-read files: {rr}",
            f"- files edited: {stats['files_edited']}",
            f"- commands run: {stats['commands_run']}",
            f"- errors observed: {stats['errors_observed']}",
            "",
        ]
        body = "\n".join(lines)
        path.write_text(body, encoding="utf-8")
        (reports_dir / "latest.md").write_text(body, encoding="utf-8")  # quick access
        return path
    except Exception as exc:
        sys.stderr.write(f"[tier1] report file skipped: {exc}\n")
        return None


def persist(session_id, result, stats):
    try:
        from db import store
        conn = store.connect()
        try:
            full = dict(result)
            full["stats"] = stats
            store.log_report(
                conn,
                session_id=session_id or "",
                health_score=result.get("health_score") or 0,
                report_json=json.dumps(full, ensure_ascii=False),
                points_json=json.dumps(result.get("points_for_tier2", []), ensure_ascii=False),
            )
        finally:
            conn.close()
    except Exception as exc:
        sys.stderr.write(f"[tier1] persist skipped: {exc}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(transcript_path, session_id="", cwd=None, dry_run=False):
    cwd = cwd or os.getcwd()
    events, snap = build_memory(transcript_path, session_id, cwd=cwd)
    stats = mechanical_stats(events)
    deflections = load_deflections(session_id)
    stats["off_quota_questions"] = len(deflections)

    if dry_run:
        print(json.dumps({"stats": stats, "off_quota": [d["question"] for d in deflections],
                          "memory": {
            "current_task": snap.current_task,
            "recent_files": list(snap.recent_files),
            "recent_errors": list(snap.recent_errors),
            "recent_commands": list(snap.recent_commands),
            "architecture_notes": list(snap.architecture_notes),
        }}, indent=2))
        return

    # Truly empty only if there were NO Claude turns AND no off-quota questions.
    if stats["total_events"] == 0 and not deflections:
        result = {
            "health_score": None,
            "report": ["No activity in this session — nothing to reflect on."],
            "points_for_tier2": [],
        }
        persist(session_id, result, stats)
        path = write_report_file(session_id, result, stats, deflections)
        print(json.dumps({"report": result, "report_file": str(path) if path else None,
                          "usage": {}}, indent=2, ensure_ascii=False))
        return

    result, usage = reflect(stats, snap, cwd, deflections)
    persist(session_id, result, stats)
    path = write_report_file(session_id, result, stats, deflections)
    print(json.dumps({"report": result, "report_file": str(path) if path else None,
                      "usage": usage}, indent=2, ensure_ascii=False))


def main():
    argv = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv

    if argv:  # standalone: path as arg 1
        run(argv[0], session_id=argv[1] if len(argv) > 1 else "", dry_run=dry)
        return

    # hook mode: JSON on stdin (Stop / SessionEnd payload)
    data = json.loads(sys.stdin.read() or "{}")
    tp = data.get("transcript_path", "")
    if not tp:
        return
    run(tp, session_id=data.get("session_id", ""), cwd=data.get("cwd"), dry_run=dry)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:      # FAIL-SAFE: never disrupt session end
        sys.stderr.write(f"[tier1] error (ignored): {exc}\n")
        sys.exit(0)
