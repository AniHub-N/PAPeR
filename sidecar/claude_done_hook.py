#!/usr/bin/env python3
"""
claude_done_hook.py — Stop hook: fires when Claude finishes a response.

Bumps a counter in the store; the floating PAPeR window watches it and blinks
"Claude has responded" — so while you're working in another app with PAPeR
pinned on top, you get a glanceable signal that your Claude turn is done.

Stdlib only (just sqlite3 via store), so it runs under any python3 — no launcher
needed. Fails silent and always exits 0: a Stop hook must never disrupt the
session.

Register in settings.json:
    "Stop": [ { "hooks": [
        { "type": "command", "command": "python3 <PAPER>/sidecar/claude_done_hook.py" }
    ] } ]
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    try:
        sys.stdin.read()  # drain the Stop payload; we don't need it
    except Exception:
        pass
    try:
        from db import store
        conn = store.connect()
        store.mark_claude_done(conn)
        conn.close()
    except Exception:
        pass  # never break the session


if __name__ == "__main__":
    main()
