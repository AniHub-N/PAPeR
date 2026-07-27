# PAPeR

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
└── README.md
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

## Try it

```bash
cd primary_router

# See EXACTLY what would be sent to the model — no key needed:
python3 answer_pipeline.py --dry-run "How does the router decide task vs question?"

# Make a real off-quota call with your own key:
SIDECAR_API_KEY=your-gemini-key python3 answer_pipeline.py "What is OAuth?"

# Just the transcript recap:
python3 transcript.py            # newest session for this project
```

---
---

# Primary Router

*(module-level detail for `primary_router/` — the fast-loop classifier)*

Primary Router is a deterministic prompt router that sends work to Claude Code or to a secondary LLM based on weighted, explainable evidence.

## Architecture

The project is organized around a small set of focused modules:

- [primary_router/models.py](primary_router/models.py): shared domain models for routes and extracted features.
- [primary_router/patterns.py](primary_router/patterns.py): regexes and keyword dictionaries used for feature extraction.
- [primary_router/features.py](primary_router/features.py): pure feature extraction only; it never makes routing decisions.
- [primary_router/rules.py](primary_router/rules.py): the unified rule catalog for single-feature and compound rules.
- [primary_router/router.py](primary_router/router.py): a generic scoring engine that evaluates rules and returns a routing decision.
- [primary_router/test_router.py](primary_router/test_router.py): regression and behavior tests.

## Feature Extraction

Feature extraction is intentionally narrow and deterministic. It looks for signals such as:

- file paths
- stack traces
- repository or workspace references
- line numbers
- CamelCase symbols
- markdown code blocks
- contextual references such as "this", "current", or "existing"
- intent cues such as questions, explanations, generation, editing, debugging, searching, and refactoring
- programming-language and framework terminology

The extractor only reports evidence and does not make routing decisions.

## Rule Engine

Rules are expressed through a single data model:

- each rule has a name, route, weight, and required features
- single-feature rules fire when one feature is present
- compound rules fire when multiple features are present together
- the router scores Claude and side-LLM evidence independently and uses the higher score to decide

## Adding New Rules

1. Add a new feature to [primary_router/features.py](primary_router/features.py) if it is a new signal.
2. Add a corresponding field to [primary_router/models.py](primary_router/models.py) if it represents a meaningful concept.
3. Add a rule to [primary_router/rules.py](primary_router/rules.py) with the appropriate weight and route.
4. Add or update tests in [primary_router/test_router.py](primary_router/test_router.py).

## Tuning Weights

Weights are intentionally simple and explicit. Increase a rule's weight when you want stronger evidence for that route, and lower it when the signal is noisy. Because routing is deterministic, it is easy to understand and tune.

## Testing

Run the test suite with:

```bash
pytest -q
```
