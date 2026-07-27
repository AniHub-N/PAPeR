"""
side_model.py — Module 3: the grounded side-model call.

BRING-YOUR-OWN-KEY BY DESIGN. The side model is a provider the USER supplies —
their own API key, their own billing pool — so a deflected question is answered
entirely OFF the user's Claude subscription quota. That separate-pool trade is
the product; the specific model is not the point.

Provider-agnostic: the vendor toggle (SIDECAR_VENDOR) selects an adapter, and
SIDECAR_API_KEY is ALWAYS the user's own key. Adding a provider = writing one
small adapter function and registering it in PROVIDERS; nothing else changes.
Raw HTTP (stdlib urllib) — no per-provider SDK dependency.

v1 provider: Gemini (Google Generative Language REST API).

Config (all env):
    SIDECAR_VENDOR   provider name (default "gemini")
    SIDECAR_API_KEY  the user's own key for that provider (required)
    SIDECAR_MODEL    optional model-id override for the chosen provider
    SIDECAR_TIMEOUT  seconds, default 15
"""

import json
import os
import urllib.error
import urllib.request

VENDOR = os.environ.get("SIDECAR_VENDOR", "gemini")
API_KEY = os.environ.get("SIDECAR_API_KEY")       # user's OWN key, always
MODEL = os.environ.get("SIDECAR_MODEL")           # optional per-provider override
TIMEOUT = float(os.environ.get("SIDECAR_TIMEOUT", "15"))

SYSTEM_INSTRUCTION = (
    "You are a fast assistant answering a developer's question about their "
    "project, using the provided project context. Be concise and concrete. "
    "If the context is insufficient to answer, say so plainly rather than guessing."
)


class SideModelError(RuntimeError):
    """Any failure in the side-model call. Phase 2 logs this; it never crashes the hook."""


# ---------------------------------------------------------------------------
# Provider adapters: (system, prompt) -> (text, usage_dict).
# One function per provider. Register it in PROVIDERS below.
# ---------------------------------------------------------------------------

def _gemini(system, prompt, *, api_key, model, timeout):
    # Cheap/fast tier. CONFIRM the exact current model id and override via
    # SIDECAR_MODEL if needed (e.g. gemini-2.0-flash).
    model = model or "gemini-2.5-flash"
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.2},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise SideModelError(f"gemini HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise SideModelError(f"gemini connection error: {e.reason}") from e

    candidates = payload.get("candidates") or [{}]
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    return text, payload.get("usageMetadata", {})


PROVIDERS = {
    "gemini": _gemini,
    # "openai": _openai,        # add later — one small adapter
    # "anthropic": _anthropic,  # add later — user's OWN console key, NEVER the Claude Code login
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_prompt(question, *, claude_md="", project_map="", preferences="",
                 transcript_tail="", fetched=""):
    """Assemble grounding + question into one prompt string.

    Ordered stable-context-first, question-last, so the volatile part (the
    question) sits at the end. Kept separate from answer() so callers can inspect
    exactly what would be sent (dry runs / auditing) without making a call."""
    blocks = []
    if claude_md:
        blocks.append(f"# CLAUDE.md\n{claude_md}")
    if project_map:
        blocks.append(f"# Project map\n{project_map}")
    if preferences:
        blocks.append(f"# User preferences\n{preferences}")
    if transcript_tail:
        blocks.append(f"# Recent conversation\n{transcript_tail}")
    if fetched:
        blocks.append(f"# Relevant files\n{fetched}")
    blocks.append(f"# Question\n{question}")
    return "\n\n".join(blocks)


def answer(question, *, claude_md="", project_map="", preferences="",
           transcript_tail="", fetched="", system=SYSTEM_INSTRUCTION):
    """Assemble grounding + question into one prompt and make a single side-model
    call. Returns (answer_text, usage_dict). Raises SideModelError on any failure."""
    if not API_KEY:
        raise SideModelError("SIDECAR_API_KEY is not set — bring your own key.")
    provider = PROVIDERS.get(VENDOR)
    if provider is None:
        raise SideModelError(
            f"Unknown SIDECAR_VENDOR={VENDOR!r}; known: {sorted(PROVIDERS)}"
        )

    prompt = build_prompt(
        question, claude_md=claude_md, project_map=project_map,
        preferences=preferences, transcript_tail=transcript_tail, fetched=fetched,
    )
    return provider(system, prompt, api_key=API_KEY, model=MODEL, timeout=TIMEOUT)


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "What is OAuth? Answer in two sentences."
    try:
        text, usage = answer(q)
        print(text)
        print("\n[vendor]", VENDOR, "[usage]", usage)
    except SideModelError as e:
        print(f"[side_model error] {e}", file=sys.stderr)
        sys.exit(1)
