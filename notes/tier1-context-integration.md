# Integration note — context/ package + Tier-1 reflector

Status: ported + working stub on `anirudh/possible`. Written so piyush and the
rest of the team stay aligned. Nothing here is committed until we agree.

## TL;DR

- piyush's `phase1-only` work (the incremental transcript watcher/parser +
  session memory) belongs to the **slow loop**, feeding **Tier-1**. It does NOT
  compete with our fast-loop answering hook — that resolves the "two hook
  philosophies" question. We run **both**, in **different loops**.
- We **cherry-picked the `context/` package** onto our branch (did NOT merge
  `phase1-only`, which deletes the sidecar, store, retrieval, and our in-hook
  off-quota answering).
- Built a working **Tier-1 runner** on top of it:
  `transcript -> events -> session memory -> mechanical checks -> one LLM call
  vs rulebook -> session report + 5-6 points -> store -> (Tier-2 later).`

## What was added

| File | Purpose |
|------|---------|
| `primary_router/context/` | ported package: `transcript_watcher`, `transcript_parser`, `session_memory`, `daemon`, `checkpoints`, `runtime`, `events`, `synchronizer` |
| `primary_router/models.py` | + `HookPayload`, `HookNotification` (deps the package needs) |
| `sidecar/tier1.py` | the Tier-1 reflector (full pipeline; CLI + stdin + `--dry-run`) |
| `sidecar/rulebook.md` | the judgment instructions Tier-1 sends as the system prompt |
| `sidecar/tier1_hook.py` | `Stop`/`SessionEnd` hook that spawns Tier-1 **detached** (never delays session end) |
| `db/store.py` | + `reports` table, `log_report()`, `recent_reports()` (Tier-2 reads these) |
| `primary_router/side_model.py` | `answer(..., max_tokens=)` — Tier-1 needs a bigger output budget (see gotcha) |
| `hooks/hooks.json` | registered `claude_done_hook` + `tier1_hook` on `Stop` |

## The Tier-1 pipeline (implemented)

```
full session transcript (JSONL)
  -> TranscriptParser.parse(all lines)        typed events
  -> SessionMemory.apply(each) -> snapshot     current task / recent files /
                                               errors / commands / arch notes
  -> mechanical_stats(events)                  prompts, reads, RE-READS(waste),
                                               edits, commands, errors  [no LLM]
  -> one LLM call: system = rulebook.md,       health_score + report[5-10] +
                   grounded on CLAUDE.md          points_for_tier2[5-6]
  -> store.log_report()                        read later by Tier-2 (phase 2)
```

Verified end-to-end against a real transcript: produces a health score, a 5-10
bullet report, and 5-6 durable points; persists to `reports`; the detached Stop
hook returns instantly and the report lands ~10s later.

## Decisions taken (change if you disagree)

1. **Full-transcript parse, not the live tail (approach B).** Tier-1 reads the
   WHOLE JSONL through the same `parser.parse()` (it accepts any lines), so it
   works even if the in-session daemon never ran. The live daemon (approach A,
   where `session_memory` is built incrementally during the session) is a valid
   optimization we can add later — it doesn't change Tier-1's interface.
2. **Fast loop keeps OUR answering hook; slow loop uses the daemon/parser.**
   Do not promote `phase1-only`'s routing-only `classifier_hook` — it drops the
   synchronous off-quota answer. Its role, if any, is thin daemon-notify.
3. **Detached execution.** Tier-1 makes an LLM call (seconds), so `tier1_hook`
   spawns it with `start_new_session=True` and returns. Session end never waits.

## Gotcha fixed: thinking tokens

Gemini 2.5-flash draws "thinking" tokens from `maxOutputTokens`. At the default
1024 the reflection JSON got truncated (979 thinking + 41 output). Tier-1 now
calls `side_model.answer(..., max_tokens=4096)`. Fast-loop answers still use the
1024 default.

## Open for the team

- **`/commands` trigger:** we can also expose Tier-1 as a manual `/reflect`
  slash command in addition to the automatic `Stop` hook. Cheap to add.
- **Tier-2 (phase 2) is next:** it reads `store.recent_reports(limit=6)` (the
  summaries, NOT raw transcripts), aggregates the 5-6-point lists, and writes
  CLAUDE.md/Skills with a changelog. The reports table is ready for it.
- **Rulebook is v1:** `sidecar/rulebook.md` is plain instructions — tune the
  signals (re-reads, repeated errors, convention drift) as we learn what matters.
