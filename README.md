# PAPeR — Project Overview


PAPeR is a companion that sits **next to Claude Code** and makes it faster, cheaper, and more personalized without replacing it.

It does this through four core capabilities:

1. **Deflects** non-coding questions ("What is OAuth?") to a cheaper model using your own API key, preserving Claude quota.
2. **Optimizes** the coding path by reducing unnecessary context and token usage (planned: read deduplication, command output compression, smarter retrieval).
3. **Learns** your coding and communication preferences across sessions to improve future interactions.
4. **Provides a modular tool execution runtime** that enables LLMs to discover, invoke, and execute tools through a structured interface, making the system extensible and independent of any specific model provider.

The tool runtime consists of a registry for managing available tools, a dispatcher for routing requests, an executor for handling tool calls, a parser for interpreting LLM responses, a prompt builder for exposing tool capabilities, and a runner that orchestrates the interaction between the LLM and the tool system. Together, these components enable iterative tool usage until a final answer is produced.

Nothing here replaces Claude Code. PAPeR plugs into Claude Code's existing hook system and session transcripts, adding lightweight orchestration, retrieval, personalization, and tool execution without modifying Claude Code itself.

---

## The big picture: two loops

**Fast loop** — runs on every message, must feel instant:

```text
your prompt
   │
   ▼
classifier  ──►  looks like a coding task?  ──►  hand off to Claude Code (normal)
(scoring        │
 router)        └►  looks like a plain question?
                     │
                     ▼
              answer_pipeline  ── gather CLAUDE.md + preferences + transcript ──► side_model
                                                                                  │
                                                                                  ▼
                                                                         your OWN cheap model (off-quota)
```

**Slow loop** — runs after a session ends, not time-sensitive:

```text
session transcript ──► reflect on what happened ──► update rules / preferences / reports
```

The **only** thing connecting the two loops is a file Claude Code already writes:
`~/.claude/projects/<project>/<session-id>.jsonl`. We never write it, only read it.

---

## Rough structure

```text
PAPeR/
├── primary_router/          # the fast loop
│   ├── router.py
│   ├── features.py
│   ├── rules.py
│   ├── models.py / patterns.py
│   ├── transcript.py
│   ├── side_model.py
│   └── answer_pipeline.py
│
├── preferences/             # learns user preferences
│
├── tools/                   # modular tool execution runtime
│   ├── base.py
│   ├── models.py
│   ├── registry.py
│   ├── dispatcher.py
│   ├── executor.py
│   ├── parser.py
│   ├── prompt.py
│   ├── runner.py
│   └── implementations/
│
├── README.md
└── README2.md
```

---

## Internals — how a deflected question is answered

This is the part most likely to matter to you as a teammate. Three small, independently replaceable modules do the work:

### 1. `transcript.py` — "what just happened"

Claude Code logs the whole session to a JSONL file. This module reads it and boils it down to a small recap so the cheap model isn't answering blind.

### 2. `side_model.py` — "the off-quota call"

Makes a single request to a cheaper model using **your own API key**, keeping usage outside Claude's quota.

### 3. `answer_pipeline.py` — "the glue"

Builds the complete grounding stack and performs a single model call.

```
question
 + CLAUDE.md
 + user preferences
 + transcript tail
 ───────────────────────► side_model.answer()
```

### 4. `tools/` — "structured tool execution"

The tool runtime enables an LLM to perform actions instead of only generating text.

When the model needs external information, it returns a structured tool call. The runtime parses the request, dispatches it to the appropriate registered tool, executes it, returns a structured result, and feeds that result back into the conversation. This loop continues until the model produces a final answer.

The runtime currently includes:

- Tool Registry
- Tool Dispatcher
- Tool Executor
- Tool Parser
- Prompt Builder
- Tool Runner

Example tools include:

- Echo
- Read File
- Glob
- Grep
- List Directory

The runtime is model-agnostic and can be connected to OpenAI, Anthropic, Ollama, Gemini, or any other LLM capable of producing the expected JSON responses.

---

## The grounding stack

```
CLAUDE.md
+ user preferences
+ transcript tail
+ project map
+ fetched files
```

---

## What's built vs. what's left

| Piece | Status | Notes |
|---|---|---|
| Scoring router (`primary_router/`) | ✅ Working | Task vs. question routing using explainable weights |
| `transcript.py` | ✅ Working | Session recap and transcript summarization |
| `side_model.py` | ✅ Working | Gemini implementation; additional providers can be added |
| `answer_pipeline.py` | ✅ Working | Single-call grounding pipeline |
| **Tool Runtime (`tools/`)** | ✅ Working | Registry, dispatcher, executor, parser, prompt builder, runner, and core filesystem tools with end-to-end execution loop |
| `preferences/` | 🟡 Skeleton | Architecture complete; implementation in progress |
| Project map | ⬜ Not built | Repository summarization |
| Retrieval toolbox | ⬜ Not built | Advanced file retrieval |
| Claude hook integration | ⬜ Not built | Hook into `UserPromptSubmit` |
| Task-path optimisation | ⬜ Not built | Reduce repeated reads and token usage |
| Slow-loop reflection | ⬜ Not built | Session analysis and preference updates |
| Savings counter | ⬜ Not built | Verified token and cost tracking |

---

## Immediate next steps

- Finish the `preferences/` implementation.
- Build the project map and retrieval toolbox.
- Integrate the tool runtime with the retrieval pipeline.
- Connect the runtime to a production LLM.
- Wrap the complete pipeline inside the Claude Code hook system.

---

## Try it

```bash
# Run the runtime tests
python testing.py

# Dry-run the answer pipeline
python3 answer_pipeline.py --dry-run "How does the router decide task vs question?"

# Real off-quota call
SIDECAR_API_KEY=your-gemini-key python3 answer_pipeline.py "What is OAuth?"

# Transcript recap
python3 transcript.py
```
