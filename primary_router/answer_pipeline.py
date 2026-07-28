"""
answer_pipeline.py — the "API hit": assemble grounding, make ONE side-model call.

This is the function Phase 2 runs after the classifier has decided a prompt is a
question worth deflecting off the user's Claude quota. It is the single seam
where all the grounding pieces come together:

    question
      + CLAUDE.md            (project rules — read from disk)
      + user preferences     (how the user likes answers/code — see note below)
      + transcript tail      (what just happened — transcript.build_tail)
      --------------------------------------------------------------
      -> side_model.answer() -> one call to the user's OWN cheap model -> answer

Not wired in yet (deliberately — those modules aren't built): the Retrieval
Toolbox (glob/grep/git-log fetch) and project-map.md. When they exist they drop
straight into the `project_map=` / `fetched=` slots that side_model already
exposes. Nothing here needs to change to accept them.

Design rule (from CLAUDE.md): FAIL OPEN. Every grounding source is best-effort —
if CLAUDE.md is missing, preferences can't import, or the transcript is
unreadable, we still send the question with whatever context we DID gather rather
than crash. The only hard failure is the model call itself (no key / network),
which surfaces as SideModelError for Phase 2 to log.
"""

import os
from pathlib import Path

import side_model
import transcript

# ---------------------------------------------------------------------------
# CLAUDE.md
# ---------------------------------------------------------------------------

def load_claude_md(cwd=None, max_chars=8000):
    """Find and read the project's CLAUDE.md (best-effort).

    Resolution order:
      1. $CLAUDE_MD_PATH if set (explicit override, e.g. from the plugin).
      2. Walk up from cwd looking for CLAUDE.md / claude.md.
    Returns "" if none found — we ground on what we have."""
    override = os.environ.get("CLAUDE_MD_PATH")
    if override and Path(override).is_file():
        return _read_clip(Path(override), max_chars)

    here = Path(cwd or os.getcwd()).resolve()
    for folder in (here, *here.parents):
        for name in ("CLAUDE.md", "claude.md"):
            candidate = folder / name
            if candidate.is_file():
                return _read_clip(candidate, max_chars)
    return ""


def _read_clip(path, max_chars):
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n…[CLAUDE.md truncated]"
    return text


# ---------------------------------------------------------------------------
# User preferences
# ---------------------------------------------------------------------------
#
# The preferences/ subsystem (teammate's work) is still a skeleton: some sources
# and storage drivers are empty stubs, and it depends on pydantic which may not
# be installed. So we integrate DEFENSIVELY — try to use the real resolved
# preferences, and fall back to these baked-in defaults if anything is missing.
# When the subsystem is finished, the try-branch starts working with zero changes
# here (or a caller can pass an already-built object into gather_context).

_DEFAULT_PREFERENCES = {
    "communication.explanation_depth": "normal",
    "communication.examples": "when_helpful",
    "coding_style.comments": "minimal",
    "coding_style.naming": "project",
    "architecture.style": "hybrid",
    "workflow.refactor": "ask",
}


def load_preferences():
    """Return a flat {dotted_key: value} dict of resolved user preferences.

    Best-effort: uses the real preferences subsystem if it imports and builds;
    otherwise returns baked-in defaults so the side model still gets a
    'this is how the user likes things' block."""
    try:
        # Only the typed defaults object is cleanly buildable today; the full
        # PreferenceManager needs sources/storage that are still stubs.
        from preferences.pipeline.builder import ResolvedPreferences
        resolved = ResolvedPreferences()  # sensible typed defaults
        return _flatten(resolved.model_dump())
    except Exception:
        return dict(_DEFAULT_PREFERENCES)


def _flatten(nested, prefix=""):
    flat = {}
    for key, value in nested.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_flatten(value, dotted))
        else:
            flat[dotted] = value
    return flat


def format_preferences(prefs):
    """Render a preferences dict as compact 'key: value' lines for the prompt."""
    if not prefs:
        return ""
    return "\n".join(f"- {k}: {v}" for k, v in sorted(prefs.items()))


# ---------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------

def gather_context(*, question="", hook_json=None, cwd=None, preferences=None):
    """Collect the grounding stack for a deflected question (all best-effort).

    Returns a dict with keys: claude_md, preferences, transcript_tail, fetched —
    the exact kwargs side_model.answer() expects."""
    hook_json = hook_json or {}
    cwd = cwd or hook_json.get("cwd")

    claude_md = load_claude_md(cwd)

    prefs = preferences if preferences is not None else load_preferences()
    preferences_text = format_preferences(prefs)

    try:
        path = transcript.from_hook_input(hook_json) if hook_json \
            else transcript.latest_transcript(cwd)
        transcript_tail = transcript.build_tail(path) if path else ""
    except Exception:
        transcript_tail = ""

    # Retrieval Toolbox: for locate/symbol questions, grep the repo so the side
    # model can answer "it's in side_model.py:40" instead of guessing. No-op
    # (returns "") for questions with no symbol-like terms.
    try:
        import retrieval
        fetched = retrieval.fetch(question, cwd) if question and cwd else ""
    except Exception:
        fetched = ""

    return {
        "claude_md": claude_md,
        "preferences": preferences_text,
        "transcript_tail": transcript_tail,
        "fetched": fetched,
    }


def answer_question(question, *, hook_json=None, cwd=None, preferences=None):
    """Full pipeline: gather grounding, make one side-model call.

    Returns (answer_text, usage_dict). Raises side_model.SideModelError only on a
    genuine model-call failure (missing key, network, bad vendor)."""
    context = gather_context(question=question, hook_json=hook_json, cwd=cwd,
                             preferences=preferences)
    return side_model.answer(question, **context)


# ---------------------------------------------------------------------------
# Standalone test harness
# ---------------------------------------------------------------------------
#   python3 answer_pipeline.py --dry-run "your question"   # assemble only, no key
#   SIDECAR_API_KEY=... python3 answer_pipeline.py "your question"  # live call

if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    dry_run = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]
    question = " ".join(argv) or "What is OAuth? Answer in two sentences."

    context = gather_context(question=question, cwd=os.getcwd())

    if dry_run:
        # Show EXACTLY what would be sent — no key needed. This is how to verify
        # grounding assembly offline (Build-and-Test-Order step 4).
        prompt = side_model.build_prompt(question, **context)
        print(prompt)
        print("\n" + "=" * 70, file=sys.stderr)
        print(f"[dry-run] would send {len(prompt)} chars to vendor="
              f"{side_model.VENDOR}", file=sys.stderr)
        for k, v in context.items():
            print(f"[dry-run]   {k}: {len(v)} chars", file=sys.stderr)
        sys.exit(0)

    try:
        text, usage = answer_question(question, cwd=os.getcwd())
        print(text)
        print(f"\n[answer] vendor={side_model.VENDOR} usage={usage}",
              file=sys.stderr)
    except side_model.SideModelError as e:
        print(f"[answer_pipeline error] {e}", file=sys.stderr)
        sys.exit(1)
