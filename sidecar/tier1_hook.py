#!/usr/bin/env python3
"""
tier1_hook.py — Stop / SessionEnd hook that launches Tier-1 in the BACKGROUND.

Tier-1 reads the whole transcript and makes one LLM call (seconds). That must
NEVER delay the end of a session, so this hook spawns tier1.py fully detached and
returns immediately. Fail-open: any error exits 0 and disturbs nothing.

Register alongside the existing Stop hook (claude_done_hook.py) — Claude Code
runs multiple hooks on the same event.
"""

import json
import os
import subprocess
import sys


def main():
    data = json.loads(sys.stdin.read() or "{}")
    tp = data.get("transcript_path", "")
    if not tp:
        return

    here = os.path.dirname(os.path.abspath(__file__))
    launcher = os.path.join(os.path.dirname(here), "bin", "paper-py")
    tier1 = os.path.join(here, "tier1.py")
    payload = json.dumps({
        "transcript_path": tp,
        "session_id": data.get("session_id", ""),
        "cwd": data.get("cwd", ""),
    }).encode("utf-8")

    # start_new_session detaches from Claude Code's process group so session end
    # doesn't wait on (or kill) the reflector.
    proc = subprocess.Popen(
        [launcher, tier1],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        proc.stdin.write(payload)
        proc.stdin.close()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
