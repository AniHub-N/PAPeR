#!/usr/bin/env python3
"""
statusline.py — Claude Code status-line command (the ambient counter).

Claude Code renders whatever this prints as the status line at the bottom of the
CLI / extension. It receives session JSON on stdin (we don't need it) and prints
ONE line. This is the persistent, in-editor surface — the "12 deflected · 0
quota" bar from the mockup — with no browser.

Register in settings.json:
    "statusLine": { "type": "command",
                    "command": "python3 <plugin>/sidecar/statusline.py" }

Stdlib only, so it runs under any python3 (no launcher needed). Fails silent:
a status line must never error the session, so on any problem it prints nothing.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    try:
        sys.stdin.read()  # drain the session payload; we don't use it
    except Exception:
        pass
    try:
        from db import store
        conn = store.connect()
        c = store.get_state(conn)["counters"]
        conn.close()
    except Exception:
        return  # print nothing rather than break the status line

    n = c.get("deflected_count", 0)
    cost = c.get("deflected_cost_usd", 0.0)
    reads = c.get("reads_skipped", 0)
    bash = c.get("bash_tokens_saved", 0)

    parts = [f"● {n} deflected · 0 Claude quota"]
    if cost:
        parts.append(f"${cost:.4f} off-quota")
    if reads or bash:
        parts.append(f"{reads} reads · {bash:,} tok saved")
    sys.stdout.write("   ".join(parts))


if __name__ == "__main__":
    main()
