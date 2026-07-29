"""
store.py — thin SQLite wrapper (stdlib sqlite3, zero deps).

The seam between the hooks (which WRITE events) and the sidecar UI (which READS
them). Everything the frontend shows comes from here.

Two event tables:
  deflections  — one row per question answered off-quota by the side model,
                 with the REAL token usage returned by the provider.
  savings      — one row per verified per-action saving (a skipped duplicate
                 read, a compressed Bash output). Per-action by design — we sum
                 verified deltas, we never invent an aggregate. (See CLAUDE.md
                 "Measurement Honesty".)

DB location: $SIDECAR_DB, else <repo>/paper.db (gitignored).
"""

import os
import sqlite3
from pathlib import Path


def db_path():
    override = os.environ.get("SIDECAR_DB")
    if override:
        return Path(override)
    # repo root = parent of this file's parent (db/ -> repo)
    return Path(__file__).resolve().parent.parent / "paper.db"


def connect(path=None):
    conn = sqlite3.connect(str(path or db_path()))
    conn.row_factory = sqlite3.Row
    init(conn)
    return conn


def init(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS deflections (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            TEXT DEFAULT CURRENT_TIMESTAMP,
            session_id    TEXT,
            question      TEXT NOT NULL,
            answer        TEXT NOT NULL,
            provider      TEXT,
            model         TEXT,
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd      REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS savings (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT DEFAULT CURRENT_TIMESTAMP,
            kind       TEXT NOT NULL,          -- 'read_dedup' | 'rtk_compress'
            raw_units  INTEGER NOT NULL,       -- what WOULD have been sent
            sent_units INTEGER NOT NULL,       -- what was actually sent
            unit       TEXT NOT NULL           -- 'tokens' | 'reads'
        );
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS reports (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            TEXT DEFAULT CURRENT_TIMESTAMP,
            session_id    TEXT,
            health_score  INTEGER,
            report_json   TEXT,   -- full Tier-1 output (bullets + points + stats)
            points_json   TEXT    -- just the 5-6 points, for Tier-2 to aggregate
        );
        """
    )
    # Migrate older DBs that predate the session_id column.
    try:
        conn.execute("ALTER TABLE deflections ADD COLUMN session_id TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.commit()


def _meta_get(conn, key, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def _meta_set(conn, key, value):
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )
    conn.commit()


def _meta_int(conn, key, default=0):
    v = _meta_get(conn, key)
    return int(v) if v is not None and str(v).lstrip("-").isdigit() else default


def mark_claude_done(conn):
    """Bump a counter each time Claude finishes a response (Stop hook calls this).
    The UI watches this counter to blink a 'Claude responded' signal."""
    n = _meta_int(conn, "claude_done_seq") + 1
    _meta_set(conn, "claude_done_seq", n)
    return n


def mark_claude_ack(conn):
    """Acknowledge the latest Claude response: set the ack watermark to the
    current done counter. The classifier hook calls this on every new user
    prompt — sending anything means the user is active again, so the
    'Claude responded' banner should clear. The UI shows the banner only while
    claude_done_seq > claude_done_ack."""
    _meta_set(conn, "claude_done_ack", _meta_int(conn, "claude_done_seq"))


def set_enabled(conn, on):
    """Turn PAPeR deflection on/off (the UI toggle writes this; the classifier
    hook reads it and passes everything through to Claude when off)."""
    _meta_set(conn, "paper_enabled", "1" if on else "0")
    return bool(on)


def is_enabled(conn):
    """Default ON. Only an explicit '0' disables."""
    return _meta_get(conn, "paper_enabled", "1") != "0"


# ---------------------------------------------------------------------------
# Writers — called by the hooks / Phase 2
# ---------------------------------------------------------------------------

def log_deflection(conn, *, question, answer, provider="", model="",
                   input_tokens=0, output_tokens=0, cost_usd=0.0, session_id=""):
    conn.execute(
        "INSERT INTO deflections "
        "(session_id, question, answer, provider, model, input_tokens, output_tokens, cost_usd) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (session_id, question, answer, provider, model, input_tokens, output_tokens, cost_usd),
    )
    conn.commit()


def deflections_for_session(conn, session_id, *, limit=100):
    """Off-quota questions asked during one session — Tier-1 folds these into the
    session report so a side-model-only session still documents what happened."""
    if not session_id:
        return []
    rows = conn.execute(
        "SELECT question, answer, model, input_tokens, output_tokens "
        "FROM deflections WHERE session_id=? ORDER BY id LIMIT ?",
        (session_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def log_saving(conn, *, kind, raw_units, sent_units, unit):
    conn.execute(
        "INSERT INTO savings (kind, raw_units, sent_units, unit) VALUES (?,?,?,?)",
        (kind, raw_units, sent_units, unit),
    )
    conn.commit()


def log_report(conn, *, session_id, health_score, report_json, points_json):
    """Persist one Tier-1 session report. Tier-2 later reads recent_reports()
    (the summaries, not raw transcripts) to update CLAUDE.md/Skills."""
    conn.execute(
        "INSERT INTO reports (session_id, health_score, report_json, points_json) "
        "VALUES (?,?,?,?)",
        (session_id, int(health_score or 0), report_json, points_json),
    )
    conn.commit()


def recent_reports(conn, *, limit=6):
    """Most-recent Tier-1 reports, newest first — the input Tier-2 aggregates."""
    rows = conn.execute(
        "SELECT id, ts, session_id, health_score, report_json, points_json "
        "FROM reports ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Reader — the /state payload for the UI
# ---------------------------------------------------------------------------

def get_state(conn, *, recent=20):
    rows = conn.execute(
        "SELECT id, ts, question, answer, provider, model, input_tokens, "
        "output_tokens, cost_usd FROM deflections ORDER BY id DESC LIMIT ?",
        (recent,),
    ).fetchall()
    deflections = [dict(r) for r in rows]

    dcount = conn.execute("SELECT COUNT(*) FROM deflections").fetchone()[0]
    dcost = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM deflections"
    ).fetchone()[0]

    reads_skipped = conn.execute(
        "SELECT COUNT(*) FROM savings WHERE kind='read_dedup'"
    ).fetchone()[0]
    bash_tokens_saved = conn.execute(
        "SELECT COALESCE(SUM(raw_units - sent_units), 0) "
        "FROM savings WHERE kind='rtk_compress'"
    ).fetchone()[0]

    reports_count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]

    return {
        "claude_done_seq": _meta_int(conn, "claude_done_seq"),
        "claude_done_ack": _meta_int(conn, "claude_done_ack"),
        "reports_count": reports_count,
        "enabled": is_enabled(conn),
        "provider": {
            "vendor": os.environ.get("SIDECAR_VENDOR", "gemini"),
            "model": os.environ.get("SIDECAR_MODEL", ""),
            "has_key": bool(os.environ.get("SIDECAR_API_KEY")),
        },
        "counters": {
            "deflected_count": dcount,
            "deflected_cost_usd": round(dcost, 6),
            "quota_tokens": 0,  # always 0 — deflected questions are OFF-quota
            "reads_skipped": reads_skipped,
            "bash_tokens_saved": bash_tokens_saved,
        },
        "deflections": deflections,
    }


# ---------------------------------------------------------------------------
# Demo seed — lets the UI render with NO live session (frontend dev + demo)
# ---------------------------------------------------------------------------

def seed_demo(conn):
    conn.executescript("DELETE FROM deflections; DELETE FROM savings;")
    samples = [
        ("what's the difference between useMemo and useCallback",
         "useMemo caches a computed value; useCallback caches a function "
         "reference. Use useCallback when passing stable callbacks to memoized "
         "children, useMemo for expensive derived values.",
         "gemini", "gemini-2.5-flash", 512, 96, 0.0006),
        ("what is OAuth",
         "OAuth is an authorization framework that lets an app access a user's "
         "resources on another service without handling their password, by "
         "exchanging scoped access tokens.",
         "gemini", "gemini-2.5-flash", 480, 84, 0.0006),
        ("explain the difference between TCP and UDP",
         "TCP is connection-oriented and reliable (ordering, retransmission); "
         "UDP is connectionless and fast but best-effort. Use TCP for "
         "correctness, UDP for low-latency streaming.",
         "gemini", "gemini-2.5-flash", 505, 102, 0.0006),
    ]
    for q, a, prov, model, itok, otok, cost in samples:
        log_deflection(conn, question=q, answer=a, provider=prov, model=model,
                       input_tokens=itok, output_tokens=otok, cost_usd=cost)

    # verified per-action savings (demo values)
    for _ in range(128):
        log_saving(conn, kind="read_dedup", raw_units=320, sent_units=0, unit="reads")
    log_saving(conn, kind="rtk_compress", raw_units=52000, sent_units=10800, unit="tokens")


if __name__ == "__main__":
    import json
    import sys

    conn = connect()
    if "--demo" in sys.argv:
        seed_demo(conn)
        print("[store] seeded demo data into", db_path())
    print(json.dumps(get_state(conn), indent=2))
