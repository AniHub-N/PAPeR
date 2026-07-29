"""
retrieval.py — the single-pass Retrieval Toolbox (v1).

For a locate / symbol question ("Where is JWT configured?", "What does
AuthService do?", "Which modules import SearchConsoleClient?"), CLAUDE.md can't
answer — only the actual code can. This module does ONE deterministic pass:

    extract the symbol-like terms from the prompt
      -> grep the repo for them (ripgrep if present, else a Python walk)
      -> cap at 5 files, format the hits
      -> hand back as the side model's `fetched=` grounding.

Deliberately NOT the agentic tool loop in tools/ (that's deferred past v1 per
claude.md): one pass, predictable cost, and we know exactly which files were
sent to the vendor. Fails open — any error returns "".
"""

import os
import re
import subprocess
from pathlib import Path

MAX_FILES = 5
MAX_MATCHES_PER_TERM = 8
MAX_CHARS = 3000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env",
             "dist", "build", ".next", ".mypy_cache", ".pytest_cache"}

# Words that are never useful search terms (question scaffolding).
_STOP = {
    "where", "what", "which", "how", "why", "who", "when", "is", "are", "was",
    "were", "the", "a", "an", "do", "does", "did", "done", "use", "uses",
    "using", "used", "find", "show", "me", "locate", "list", "summarize",
    "summarise", "explain", "describe", "work", "works", "working", "file",
    "files", "module", "modules", "import", "imports", "imported", "initialize",
    "initialise", "implement", "implemented", "implementation", "configure",
    "configured", "config", "this", "that", "these", "those", "subsystem",
    "layer", "of", "in", "to", "and", "or", "we", "our", "my", "project",
    "codebase", "code", "for", "with", "does", "into", "from", "it", "its",
}

# Generic filler — real words, but useless as search terms (would add noise).
_GENERIC = {
    "should", "could", "would", "shall", "will", "drop", "put", "place", "keep",
    "store", "save", "want", "need", "like", "just", "also", "really", "actually",
    "thing", "things", "stuff", "get", "got", "set", "make", "made", "let", "lets",
    "please", "help", "add", "new", "some", "any", "all", "best", "good", "way",
    "ways", "here", "there", "them", "then", "your", "you", "mine", "can", "about",
    "have", "has", "had", "want", "give", "tell", "know", "think", "look", "see",
}

_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")


def extract_terms(prompt, limit=4):
    """Pull the terms worth grepping out of a prompt — two tiers, symbols first.

    Tier 1 (high precision): tokens that look like symbols — CamelCase,
    snake_case, ALLCAPS, or Capitalized proper nouns (JWT, AuthService).
    Tier 2 (grounding fallback): plain lowercase CONTENT words that aren't
    question scaffolding or filler (api, key, env, token, classifier). Without
    this tier, natural questions like 'where do I drop my api key?' extract
    nothing and the model answers with no project facts. Noise is bounded by the
    5-file / 3000-char caps in fetch()."""
    symbols, content, seen = [], [], set()
    for m in _TOKEN.finditer(prompt):
        w = m.group(0)
        lw = w.lower()
        if lw in _STOP or lw in _GENERIC or lw in seen:
            continue
        looks_symbol = (
            w[0].isupper()               # Capitalized / CamelCase / ALLCAPS
            or "_" in w                  # snake_case
            or any(c.isupper() for c in w[1:])  # camelCase
        )
        seen.add(lw)
        if looks_symbol:
            symbols.append(w)
        elif len(lw) >= 3:
            content.append(w)
    return (symbols + content)[:limit]


def _ripgrep(term, cwd):
    """ripgrep hits as [(file, line, text)], or None if rg isn't available."""
    try:
        out = subprocess.run(
            ["rg", "-n", "-i", "--max-count", str(MAX_MATCHES_PER_TERM),
             "--max-columns", "300", "--", term, "."],
            cwd=cwd, capture_output=True, text=True, timeout=4,
        )
    except FileNotFoundError:
        return None
    except (subprocess.SubprocessError, OSError):
        return []
    hits = []
    for line in out.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            hits.append((parts[0], parts[1], parts[2].strip()))
    return hits


def _pygrep(term, cwd):
    """Fallback grep (no ripgrep): walk the tree, skip junk/binary."""
    needle = term.lower()
    hits = []
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            path = Path(root) / name
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            count = 0
            for i, line in enumerate(text.splitlines(), 1):
                if needle in line.lower():
                    rel = os.path.relpath(path, cwd)
                    hits.append((rel, str(i), line.strip()[:300]))
                    count += 1
                    if count >= MAX_MATCHES_PER_TERM:
                        break
    return hits


def fetch(prompt, cwd):
    """Grep the repo for the prompt's symbols. Returns formatted hits ('' if none)."""
    if not prompt or not cwd or not Path(cwd).is_dir():
        return ""
    try:
        terms = extract_terms(prompt)
        if not terms:
            return ""
        by_file = {}
        for term in terms:
            hits = _ripgrep(term, cwd)
            if hits is None:
                hits = _pygrep(term, cwd)
            for f, ln, txt in hits:
                by_file.setdefault(f, []).append(f"{ln}: {txt}")
            if len(by_file) >= MAX_FILES:
                break

        if not by_file:
            return ""
        blocks = []
        for f in list(by_file)[:MAX_FILES]:
            lines = "\n".join(by_file[f][:MAX_MATCHES_PER_TERM])
            blocks.append(f"{f}\n{lines}")
        out = ("searched for: " + ", ".join(terms) + "\n\n"
               + "\n\n".join(blocks))
        return out[:MAX_CHARS]
    except Exception:
        return ""


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "What does SideModelError do?"
    here = str(Path(__file__).resolve().parent.parent)
    print("terms:", extract_terms(q))
    print("-" * 60)
    print(fetch(q, here))
