"""
Scoring-based prompt router (drop-in alternative to router.PromptRouter).

Design — hybrid, three stages, in order:

  1. Hard overrides   A stacktrace, code block, or file path is a *certainty*,
                      not a signal to be weighed. If one is present the prompt
                      goes to Claude immediately and scoring is skipped, so no
                      amount of question-words can deflect a pasted traceback.

  2. Weighted score   Otherwise every cheap signal adds/subtracts points.
                      Positive = task (Claude), negative = question (side LLM).
                      Signals *combine* instead of the first one winning, and
                      "at the start of the prompt" counts for more than "somewhere
                      in the middle."

  3. Bands            The score falls into one of three bands via ASYMMETRIC
                      thresholds. Deflecting to the side model is the risky
                      action (a wrong deflection answers a coding task with the
                      cheap model), so it needs *stronger* evidence than keeping
                      the prompt on Claude. Anything in between is AMBIGUOUS and
                      defaults to task — the "never split, default to task" rule.

The ambiguous band is where a tiny classifier call would go (short timeout,
falls back to task). This module leaves that as an injectable `tiebreaker`
callback so the network piece stays out of the deterministic core.

Reuses the existing compiled regexes in `patterns.py` and the `Route` enum in
`models.py`; a few extra start-anchored / phrase patterns are defined locally so
`patterns.py` is left untouched.

Usage:
    from scoring_router import ScoringRouter
    router = ScoringRouter()
    router.route("What is a binary tree?")      # -> Route.SIDE_LLM
    router.classify("Fix the failing test")     # -> RouteDecision(..., reasons=[...])
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, List, Optional, Tuple

from models import Route
import patterns


# ---------------------------------------------------------------------------
# Extra patterns (start-anchored + phrase-level signals not in patterns.py)
# ---------------------------------------------------------------------------

# Imperative verb as the FIRST word — the strongest task tell ("fix ...", "add ...").
IMPERATIVE_START = re.compile(
    r"^\s*(fix|add|refactor|implement|write|run|debug|deploy|create|build|"
    r"update|modify|remove|rewrite|optimize|edit|open|search|generate|"
    r"install|configure|setup|migrate|rename|delete)\b",
    re.IGNORECASE,
)

# Interrogative as the FIRST word — the strongest question tell.
QUESTION_START = re.compile(
    r"^\s*(what|why|how|when|where|who|which|explain|compare|should|can|"
    r"is|are|does|do|could|would)\b",
    re.IGNORECASE,
)

# Read/exploration verb as the FIRST word — project-navigation intent. These
# ("summarize the analytics subsystem", "show me the routing layer") are exactly
# what the Sidecar answers off-quota using CLAUDE.md + project map + hot files.
NAV_START = re.compile(
    r"^\s*(summarize|show|list|describe|outline|overview|tell|find|locate|walk)\b",
    re.IGNORECASE,
)

# A trailing edit command tacked onto a question ("... and fix it", "then
# refactor it"): the MIXED case. Edit intent wins -> route to task (never split).
# Requires an object pronoun so it does NOT fire on knowledge questions that just
# mention an edit word ("difference between add and remove").
EDIT_TRAILING = re.compile(
    r"\b(fix|implement|refactor|rewrite|modify|update|add|remove|create|build|"
    r"delete|rename|deploy|optimize|migrate|configure)\s+"
    r"(it|them|this|that|these|those)\b",
    re.IGNORECASE,
)

# Knowledge-question phrases that a single keyword misses.
QUESTION_PHRASES = re.compile(
    r"(difference between|pros and cons|can you tell me|what does .+ mean|"
    r"how does .+ work|when should i|what is the best)",
    re.IGNORECASE,
)

# "@filename" style mention — almost always points at a real file.
AT_MENTION = re.compile(r"@[\w\-./]+")

# "this file / function / test / bug ..." — a reference into the live session.
THIS_REFERENCE = re.compile(
    r"\bthis (file|function|test|class|method|module|repo|code|project|bug|error|component)\b",
    re.IGNORECASE,
)

# Trailing question mark.
ENDS_QUESTION = re.compile(r"\?\s*$")


# ---------------------------------------------------------------------------
# Config — weights and thresholds, all tunable in one place
# ---------------------------------------------------------------------------

@dataclass
class RouterConfig:
    # Positive weights push toward TASK (Claude).
    w_imperative_start: int = 3
    w_edit_word: int = 1          # edit word not at the start (weaker)
    w_debug_word: int = 2
    w_code_keyword: int = 2
    w_this_reference: int = 2
    w_at_mention: int = 3

    # Negative weights push toward QUESTION / navigation (side LLM).
    w_question_start: int = 3
    w_nav_start: int = 3          # read/exploration verb at the start
    w_question_word: int = 1      # question word not at the start (weaker)
    w_question_phrase: int = 2
    w_ends_question: int = 1

    # Asymmetric bands: it takes MORE evidence to deflect off-quota than to
    # keep the prompt on Claude. Everything strictly between defaults to task.
    task_threshold: int = 2       # score >= this  -> clear task
    question_threshold: int = -3  # score <= this  -> clear question


class Band(Enum):
    HARD_OVERRIDE = "hard_override"
    CLEAR_TASK = "clear_task"
    CLEAR_QUESTION = "clear_question"
    AMBIGUOUS = "ambiguous"


@dataclass
class RouteDecision:
    """Full result — route plus the why, for logging / tuning / telemetry."""
    route: Route
    band: Band
    score: int
    reasons: List[Tuple[str, int]] = field(default_factory=list)

    def explain(self) -> str:
        parts = ", ".join(f"{name}{delta:+d}" for name, delta in self.reasons)
        return f"{self.route.value} [{self.band.value}] score={self.score} ({parts or 'no signals'})"


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class ScoringRouter:
    """
    Drop-in replacement for router.PromptRouter.

    router.route(prompt) -> Route          (same signature as PromptRouter)
    router.classify(prompt) -> RouteDecision  (route + score + reasons)

    tiebreaker: optional callable invoked ONLY on the ambiguous band. It receives
    the prompt and must return a Route. Leave it None and ambiguous defaults to
    task (Claude). This is the plug point for a tiny classifier model.
    """

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        tiebreaker: Optional[Callable[[str], Route]] = None,
    ):
        self.config = config or RouterConfig()
        self.tiebreaker = tiebreaker

    # -- public API ---------------------------------------------------------

    def route(self, prompt: str) -> Route:
        return self.classify(prompt).route

    def classify(self, prompt: str) -> RouteDecision:
        prompt = prompt or ""

        # Stage 1 — hard overrides: certainties, skip scoring entirely.
        override = self._hard_override(prompt)
        if override is not None:
            name, _ = override
            return RouteDecision(Route.CLAUDE, Band.HARD_OVERRIDE, 0, [(name, 0)])

        # Stage 2 — weighted score.
        score, reasons = self._score(prompt)

        # Stage 3 — bands.
        cfg = self.config
        if score >= cfg.task_threshold:
            return RouteDecision(Route.CLAUDE, Band.CLEAR_TASK, score, reasons)
        if score <= cfg.question_threshold:
            # Mixed guard: a would-be deflection that also carries a trailing
            # edit command ("...and fix it") is a MIXED prompt -> never split,
            # route to task (claude.md rule).
            if EDIT_TRAILING.search(prompt):
                return RouteDecision(
                    Route.CLAUDE, Band.AMBIGUOUS, score, reasons + [("mixed_edit_guard", 0)]
                )
            return RouteDecision(Route.SIDE_LLM, Band.CLEAR_QUESTION, score, reasons)

        # Ambiguous — hand to the tiebreaker if present, else default to task.
        if self.tiebreaker is not None:
            try:
                route = self.tiebreaker(prompt)
            except Exception:
                route = Route.CLAUDE          # fail open -> task
            reasons = reasons + [("tiebreaker", 0)]
            return RouteDecision(route, Band.AMBIGUOUS, score, reasons)

        return RouteDecision(Route.CLAUDE, Band.AMBIGUOUS, score, reasons)

    # -- internals ----------------------------------------------------------

    def _hard_override(self, prompt: str) -> Optional[Tuple[str, int]]:
        if patterns.STACKTRACE.search(prompt):
            return ("stacktrace", 0)
        if patterns.CODE_BLOCK.search(prompt):
            return ("code_block", 0)
        if patterns.FILEPATH.search(prompt):
            return ("filepath", 0)
        return None

    def _score(self, prompt: str) -> Tuple[int, List[Tuple[str, int]]]:
        cfg = self.config
        score = 0
        reasons: List[Tuple[str, int]] = []

        def add(name: str, delta: int):
            nonlocal score
            if delta:
                score += delta
                reasons.append((name, delta))

        # --- task signals (positive) ---
        if IMPERATIVE_START.search(prompt):
            add("imperative_start", cfg.w_imperative_start)
        elif patterns.EDIT_WORDS.search(prompt):
            add("edit_word", cfg.w_edit_word)

        if patterns.DEBUG_WORDS.search(prompt):
            add("debug_word", cfg.w_debug_word)
        if patterns.CODE_KEYWORDS.search(prompt):
            add("code_keyword", cfg.w_code_keyword)
        if THIS_REFERENCE.search(prompt):
            add("this_reference", cfg.w_this_reference)
        if AT_MENTION.search(prompt):
            add("at_mention", cfg.w_at_mention)

        # --- question / navigation signals (negative) ---
        # Only one "opener" signal fires (a prompt starts with one word).
        if QUESTION_START.search(prompt):
            add("question_start", -cfg.w_question_start)
        elif NAV_START.search(prompt):
            add("nav_start", -cfg.w_nav_start)
        elif patterns.QUESTION_WORDS.search(prompt):
            add("question_word", -cfg.w_question_word)

        if QUESTION_PHRASES.search(prompt):
            add("question_phrase", -cfg.w_question_phrase)
        if ENDS_QUESTION.search(prompt):
            add("ends_question", -cfg.w_ends_question)

        return score, reasons


# ---------------------------------------------------------------------------
# Manual test / REPL — shows the full decision breakdown
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    router = ScoringRouter()

    if "--demo" in sys.argv:
        samples = [
            "What is a binary tree?",
            "Difference between HTTP and HTTPS?",
            "How do I reverse a linked list?",
            "Fix the failing unit tests",
            "Implement JWT authentication",
            "Where is LoginController defined?",
            "Search the repository for UserService",
            "Write a Python quicksort implementation",
            "Debug this traceback",
            "src/main.py",
        ]
        for s in samples:
            print(f"{router.classify(s).explain()}")
            print(f"   <- {s}")
        sys.exit(0)

    while True:
        try:
            prompt = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if prompt.lower() == "quit":
            break
        print(router.classify(prompt).explain())
