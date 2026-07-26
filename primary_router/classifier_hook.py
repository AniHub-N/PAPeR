#!/usr/bin/env python3
"""
classifier_hook.py — UserPromptSubmit hook (Module 1), PHASE 1.

This is the near-instant, deterministic hot path that Claude Code runs on EVERY
prompt submission. It must return in milliseconds and never wait on any network
or LLM call.

Contract (Claude Code hooks):
    stdin  : JSON  { "prompt": ..., "session_id": ..., "cwd": ..., ... }
    stdout : JSON  {"decision": "block", "reason": "..."}  -> Claude never sees
             the prompt (this is how a question is deflected off-quota).
    exit 0 with NO output                                  -> prompt passes
             through to Claude untouched.

Flow:
    classify(prompt)  (delegated to scoring_router — the scoring lives there,
                       this module only does the hook plumbing)
      -> task / ambiguous / hard-override : exit 0, no output   (default to task)
      -> question                         : block with a placeholder, return NOW

FAIL OPEN everywhere: any error / timeout / bad input -> pass the prompt
through. Never block the user's session on a classifier fault.

Design note: kept as a small module separate from scoring_router.py so either
piece can be swapped independently — replace the scorer without touching the
hook plumbing, or vice versa.
"""

import json
import signal
import sys

from scoring_router import ScoringRouter
from models import Route

# Hot-path guard: the hook must never hang the prompt.
HARD_TIMEOUT_SEC = 2

# One shared router instance (stateless, cheap).
_router = ScoringRouter()


def pass_through():
    """exit 0 with no output -> prompt flows to Claude untouched."""
    sys.exit(0)


def block(reason: str):
    """Deflect: Claude never sees the prompt. Flush stdout before exiting."""
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    sys.stdout.flush()
    sys.exit(0)


def _on_timeout(signum, frame):
    pass_through()


def main():
    # POSIX hot-path guard — force a pass-through if anything hangs.
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _on_timeout)
        signal.alarm(HARD_TIMEOUT_SEC)

    raw = sys.stdin.read()
    data = json.loads(raw or "{}")
    prompt = data.get("prompt", "")

    decision = _router.classify(prompt)

    if decision.route == Route.SIDE_LLM:
        # ---- QUESTION branch: deflect off-quota. Return the placeholder NOW. ----
        #
        # PHASE 2 HANDOFF — NOT IMPLEMENTED (see claude.md, Module 1).
        # This is exactly where Phase 1 will fire-and-forget the detached Phase 2
        # worker BEFORE calling block(), e.g.:
        #     subprocess.Popen(
        #         [sys.executable, "phase2_worker.py"],
        #         start_new_session=True,               # setsid -> survives the hook
        #         stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL,  # never inherit
        #         close_fds=True,
        #     )
        # ...with genuinely no wait()/join(). Deliberately a no-op for now:
        # do not touch Phase 2. See the stdio-detach caveat in claude.md.
        #
        block("Thinking — answer will appear shortly")

    # TASK / AMBIGUOUS / hard-override -> always default to task.
    pass_through()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # FAIL OPEN — never block the user's prompt on a classifier error.
        pass_through()
