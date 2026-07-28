# PAPeR — Project Overview

> Whole-project overview and internals. For the fast-loop router's own module
> docs, see [README.md](README.md).

A companion that sits **next to Claude Code** and does three things:

1. **Deflects** non-coding questions ("what is OAuth?") to a cheap model you bring
   your own key for — so they don't burn your Claude quota.
2. **Trims** wasted tokens on the coding path (planned: skip re-reading unchanged
   files, compress noisy command output).
3. **Learns** how you like to work over time and turns that into better rules,
   preferences, and reports.

Nothing here replaces Claude Code. It plugs into Claude Code's own **hook system**
and reads Claude Code's own **session transcript**. We just add a thin layer on
top.

---

## The big picture: two loops

**Fast loop** — runs on every message, must feel instant:

```
your prompt
   │
   ▼
classifier  ──►  looks like a coding task?  ──►  hand off to Claude Code (normal)
(scoring        │
 router)        └►  looks like a plain question?
                        │
                        ▼
                 answer_pipeline  ── gather CLAUDE.md + preferences + transcript ──►  side_model
                                                                                        │
                                                                                        ▼
                                                                          your OWN cheap model (off-quota)
```

**Slow loop** — runs after a session ends, not time-sensitive:

```
session transcript  ──►  reflect on what happened  ──►  update rules / preferences / reports
```

The **only** thing connecting the two loops is a file Claude Code already writes:
`~/.claude/projects/<project>/<session-id>.jsonl`. We never write it, only read it.

---

## Rough structure

```
PAPeR/
├── primary_router/          # the fast loop
│   ├── router.py            # scoring engine: task -> Claude, question -> side model
│   ├── features.py          # pure signal extraction (file paths, question words, …)
│   ├── rules.py             # the weighted rule catalog
│   ├── models.py / patterns.py
│   │
│   ├── transcript.py        # ← reads Claude Code's session log into a short recap
│   ├── side_model.py        # ← the actual API call to YOUR cheap model
│   └── answer_pipeline.py   # ← glue: gather grounding, make ONE call
│
├── preferences/             # learns how you like code & answers (skeleton, WIP)
│   ├── manager.py           # the one entry point: .build() and .learn()
│   ├── events/              # turn a message into little facts ("user said 'shorter'")
│   ├── inference/           # detectors that tally facts into preferences
│   ├── pipeline/            # merge sources → one resolved object
│   └── storage/             # remember preferences across sessions
│
├── README.md                # fast-loop router module docs
└── README2.md               # this file — whole-project overview
```

---

## Internals — how a deflected question is answered

This is the part most likely to matter to you as a teammate. Three small,
independently-replaceable modules do the work:

### 1. `transcript.py` — "what just happened"
Claude Code logs the whole session to a JSONL file. This module reads it and
boils it down to a small recap so the cheap model isn't answering blind:
- keeps the last ~20 user/assistant turns, char-capped;
- keeps **one-line summaries of recent tool activity** (`⚙ Edit: auth.py`,
  `⚙ Bash: pytest -q`) and **error results** (`✖ error: Exit code 1 …`);
- throws away the noise — Claude's private "thinking" and the huge bodies of
  successful file reads;
- if you've `/compact`-ed, it grabs Claude Code's **own** summary for free
  instead of re-reading thousands of old lines.

### 2. `side_model.py` — "the off-quota call"
The single call to a cheap model. The key idea: **you bring your own API key**,
so the cost lands in *your* separate billing pool, not your Claude subscription.
That's the whole off-quota mechanism.
- Provider-agnostic: `SIDECAR_VENDOR` picks an adapter (Gemini today; OpenAI /
  others are one small function each).
- `SIDECAR_API_KEY` is always **your** key.
- `build_prompt(...)` assembles context stable-part-first, question-last.
- `answer(...)` makes the call and returns `(text, usage)`.

### 3. `answer_pipeline.py` — "the glue / the API hit"
Ties it together. Given a question it gathers the grounding stack and makes one
`side_model.answer()` call:

```
question
  + CLAUDE.md          (project rules, read from disk)
  + user preferences   (how you like answers/code — from the preferences module)
  + transcript tail    (what just happened — from transcript.py)
  ─────────────────────────────────────────────────────────────
  → side_model.answer() → one call to your cheap model → answer
```

**Fail-open by design:** every grounding source is best-effort. Missing
CLAUDE.md, un-importable preferences, unreadable transcript → we still send the
question with whatever we gathered. The only hard error is the model call itself
(no key / no network).

### The grounding stack (what gets sent)
```
CLAUDE.md   +   user preferences   +   transcript tail   +   [project map]   +   [fetched files]
  built            built                  built                 TODO                TODO
```

---

## What's built vs. what's left (for teammates)

| Piece | Status | Notes |
|---|---|---|
| Scoring router (`primary_router/`) | ✅ working | task vs. question, explainable weights |
| `transcript.py` | ✅ working | recap + free-summary harvest, tested on real logs |
| `side_model.py` | ✅ working (Gemini) | needs a live key test; more providers = more adapters |
| `answer_pipeline.py` | ✅ working | verify offline with `--dry-run` |
| `preferences/` | 🟡 skeleton | architecture done; **empty stubs** in `sources/`, `storage/drivers/`; only 3 event phrases wired; needs pydantic |
| Project map (`project-map.md`) | ⬜ not built | one-time synthesized summary of the repo |
| Retrieval Toolbox | ⬜ not built | our own glob/grep/git-log wrapper to fetch relevant files |
| Classifier hook (Phase 1 + Phase 2 wiring) | ⬜ not built | wrap the pipeline in a `UserPromptSubmit` hook |
| Task-path optimization (Read-dedup, rtk) | ⬜ not built | fast-loop token trimming |
| Slow loop (Tier 1 / Tier 2 reflectors) | ⬜ not built | session reports, auto-updates to rules |
| Savings counter | ⬜ not built | per-action, verified — never a self-reported aggregate |

**Immediate next steps:** finish the `preferences/` stubs (or install pydantic),
build the project map + Retrieval Toolbox to fill the last two grounding slots,
then wrap `answer_pipeline.answer_question()` in the `UserPromptSubmit` hook.

---

## Plugging in your API key

The side model is **bring-your-own-key** — deflected questions are billed to
*your* key, not your Claude subscription. Setup is one file:

```bash
cd PAPeR
cp .env.example .env          # .env is gitignored — your key never gets committed
# then edit .env and paste your key after SIDECAR_API_KEY=
```

`.env` (at the repo root) is picked up automatically by every script — no
`export` needed. It holds:

| Variable | Meaning |
|---|---|
| `SIDECAR_VENDOR` | which provider gets the question (default `gemini`) |
| `SIDECAR_API_KEY` | **your own** key for that provider (Gemini: https://aistudio.google.com/apikey) |
| `SIDECAR_MODEL` | optional model-id override (e.g. `gemini-2.5-flash`) |
| `SIDECAR_TIMEOUT` | optional request timeout, seconds (default 15) |

Precedence: a real shell `export`/CI variable always wins over `.env`, so CI can
override without touching the file.

## Try it

```bash
# 1) With your key in .env, make a real off-quota call:
cd primary_router
python3 answer_pipeline.py "What is OAuth?"

# 2) See EXACTLY what would be sent to the model — no key needed:
python3 answer_pipeline.py --dry-run "How does the router decide task vs question?"

# 3) Just the transcript recap:
python3 transcript.py            # newest session for this project
```
