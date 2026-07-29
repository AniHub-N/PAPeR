#!/usr/bin/env python3
"""
classifier_hook.py — UserPromptSubmit hook (Module 1).

Runs on EVERY prompt the user submits, in the Claude Code CLI or the VS Code /
JetBrains extension (hooks fire identically on all surfaces).

Contract (Claude Code hooks):
    stdin  : JSON  { "prompt": ..., "session_id": ..., "cwd": ...,
                     "transcript_path": ... }
    stdout : JSON  {"decision": "block", "reason": "<TEXT>"}  -> the prompt never
             reaches Claude, and <TEXT> is shown to the user IN PLACE, right in
             the chat where they typed. This is how a deflected answer appears
             inline — no browser, no second input bar.
    exit 0 with NO output                                     -> the prompt passes
             through to Claude untouched (the coding path).

Flow:
    classify(prompt)                       (scoring lives in scoring_router)
      -> task / ambiguous / hard-override  : exit 0  (default to task -> Claude)
      -> question                          : answer it off-quota via the side
                                             model and block() with the answer.

SYNCHRONOUS BY DESIGN. To make the answer appear in the SAME chat turn, the
side-model call happens inside the hook and its result becomes the block reason.
(This deliberately replaces the old two-phase "instant placeholder + detached
worker" plan: an async answer can't re-enter the same turn without a separate
panel, which defeats the inline UX. See claude.md — this deviation is
intentional.)

FAIL OPEN everywhere: classifier fault, missing key, slow/failed model call, or
timeout -> pass the prompt through to Claude rather than block the user. A
deflection that can't be answered simply becomes a normal Claude turn.
"""

import json
import re
import signal
import sys

# NOTE (branch integration): this uses the teammate's rule-based router
# (router.route + models.Route) which is the maintained classifier on this
# branch. Our scoring_router.py was written against a different patterns.py (on
# main) and is NOT compatible here — it is no longer imported. Reconcile the two
# routers before merging to main.
try:
    from router import route
    from models import Route
except Exception:
    # e.g. Python < 3.10 can't load the router (dataclass slots=True). Fail open:
    # no output, exit 0, the prompt goes to Claude untouched. The bin/paper-py
    # launcher normally guarantees 3.10+, so this is a safety net.
    sys.exit(0)

# Classify must be instant; the model call gets a longer, still-bounded window.
CLASSIFY_TIMEOUT_SEC = 2
ANSWER_TIMEOUT_SEC = 12


# Read-only routing override -------------------------------------------------
# The base router treats "Where is X / Find X / Show me X" as an actionable
# search and sends it to Claude. But those are READ-ONLY locate questions the
# side model should answer off-quota (grounded + Retrieval Toolbox). This
# override deflects a claude-routed prompt IFF it reads as a read-only question
# and does NOT lead with a mutation verb (which would be a real edit for Claude).
_MUTATION_VERBS = {
    "fix", "add", "implement", "refactor", "rename", "move", "delete", "remove",
    "change", "update", "create", "write", "generate", "build", "edit", "modify",
    "replace", "optimize", "migrate", "install", "configure", "setup", "rewrite",
    "patch", "make", "wire", "extract", "split", "merge", "convert",
}
_READONLY_LEADS = {
    "where", "what", "which", "how", "why", "who", "when", "find", "show",
    "locate", "list", "summarize", "summarise", "explain", "describe", "does",
    "do", "is", "are", "can",
}


def _looks_readonly(prompt):
    """True if the prompt is a read-only question (locate/what/why/how), not an
    edit. Keys on the LEADING word so 'Where is JWT configured?' is read-only
    despite containing 'configured'."""
    tokens = re.findall(r"[a-zA-Z]+", prompt.lower())
    if not tokens:
        return False
    if tokens[0] in _MUTATION_VERBS:
        return False  # imperative edit -> stays with Claude
    return tokens[0] in _READONLY_LEADS or prompt.strip().endswith("?")


def pass_through():
    """exit 0, no output -> prompt flows to Claude untouched."""
    sys.exit(0)


def block(reason):
    """Deflect: Claude never sees the prompt; `reason` is shown inline to the user."""
    sys.stdout.write(
        json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False)
    )
    sys.stdout.flush()
    sys.exit(0)


def _on_timeout(signum, frame):
    # Anything hanging -> fail open to Claude.
    pass_through()


def _plainify(text):
    """Strip markdown so the inline answer is clean plain text regardless of
    whether the model obeyed the 'no markdown' instruction."""
    text = text.replace("```", "").replace("`", "")
    text = text.replace("**", "").replace("__", "")
    # drop leading heading hashes / bullet stars on each line
    lines = []
    for ln in text.splitlines():
        ln = re.sub(r"^\s*#{1,6}\s+", "", ln)      # # headings
        ln = re.sub(r"^\s*\*\s+", "- ", ln)        # * bullets -> -
        lines.append(ln)
    return "\n".join(lines).strip()


def _attribution(usage, vendor, model):
    """A small honest, per-action footer appended to the inline answer."""
    total = 0
    if isinstance(usage, dict):
        total = (usage.get("totalTokenCount")
                 or usage.get("total_tokens")
                 or 0)
    tag = model or vendor
    return f"\n\n↳ answered off-quota · {tag} · {total} tok · 0 Claude quota"


def _log_deflection(prompt, answer, usage, vendor, model):
    """Best-effort: record the deflection so the counter/report can read it."""
    try:
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from db import store
        conn = store.connect()
        in_tok = out_tok = 0
        if isinstance(usage, dict):
            in_tok = usage.get("promptTokenCount", 0)
            out_tok = usage.get("candidatesTokenCount", 0)
        store.log_deflection(conn, question=prompt, answer=answer,
                             provider=vendor, model=model,
                             input_tokens=in_tok, output_tokens=out_tok)
        conn.close()
    except Exception:
        pass  # counter is a nicety; never let it break the answer


def _paper_enabled():
    """On every prompt: acknowledge any prior 'Claude responded' signal (the user
    is active again) and report whether PAPeR is enabled. Fail-open -> if the DB
    is unavailable, treat PAPeR as ON so behavior is unchanged."""
    try:
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from db import store
        conn = store.connect()
        try:
            store.mark_claude_ack(conn)
            return store.is_enabled(conn)
        finally:
            conn.close()
    except Exception:
        return True


def _deflect(prompt, data):
    """Answer a question off-quota and block() with the answer, inline."""
    import answer_pipeline
    import side_model

    text, usage = answer_pipeline.answer_question(prompt, hook_json=data)
    if not text:
        pass_through()  # empty answer -> let Claude handle it
    text = _plainify(text)
    _log_deflection(prompt, text, usage, side_model.VENDOR, side_model.MODEL)
    block(text + _attribution(usage, side_model.VENDOR, side_model.MODEL))


def main():
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _on_timeout)
        signal.alarm(CLASSIFY_TIMEOUT_SEC)

    data = json.loads(sys.stdin.read() or "{}")
    prompt = data.get("prompt", "")

    # Enable/disable toggle (and 'user is active' ack). When paused, PAPeR does
    # nothing — every prompt goes straight to Claude.
    if not _paper_enabled():
        pass_through()

    decision = route(prompt)

    # Deflect if the router said so, OR if it said Claude but this is really a
    # read-only question (the "Where is X / Find X" locate family).
    deflect = decision.route == Route.SIDE_LLM
    if not deflect and _looks_readonly(prompt):
        deflect = True

    if deflect:
        # QUESTION -> answer off-quota, inline. Extend the guard for the call.
        if hasattr(signal, "SIGALRM"):
            signal.alarm(ANSWER_TIMEOUT_SEC)
        try:
            _deflect(prompt, data)
        except SystemExit:
            raise
        except Exception:
            pass_through()  # any failure -> fall back to Claude

    # TASK / edit / mutation -> default to Claude.
    pass_through()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        pass_through()  # FAIL OPEN — never block on a classifier fault
