"""Compatibility facade for the canonical deterministic prompt router.

This module formerly contained a second router with its own pattern catalogue.
That made the Claude hook disagree with the tested ``PromptRouter`` and the
duplicate implementation had drifted into broken pattern references.  Keep the
public ``ScoringRouter`` API for callers, but route every prompt through the
single authoritative rule engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

try:
    from .models import Route
    from .router import PromptRouter
except ImportError:  # pragma: no cover - supports direct script execution
    from models import Route
    from router import PromptRouter


@dataclass
class RouterConfig:
    """Deprecated compatibility configuration retained for existing callers."""

    w_imperative_start: int = 3
    w_edit_word: int = 1
    w_debug_word: int = 2
    w_code_keyword: int = 2
    w_this_reference: int = 2
    w_at_mention: int = 3
    w_question_start: int = 3
    w_nav_start: int = 3
    w_question_word: int = 1
    w_question_phrase: int = 2
    w_ends_question: int = 1
    task_threshold: int = 2
    question_threshold: int = -3


class Band(Enum):
    HARD_OVERRIDE = "hard_override"
    CLEAR_TASK = "clear_task"
    CLEAR_QUESTION = "clear_question"
    AMBIGUOUS = "ambiguous"


@dataclass
class RouteDecision:
    route: Route
    band: Band
    score: int
    reasons: list[tuple[str, int]] = field(default_factory=list)

    def explain(self) -> str:
        parts = ", ".join(f"{name}{delta:+d}" for name, delta in self.reasons)
        return f"{self.route.value} [{self.band.value}] score={self.score} ({parts or 'no signals'})"


class ScoringRouter:
    """Backward-compatible adapter over :class:`router.PromptRouter`."""

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        tiebreaker: Optional[Callable[[str], Route]] = None,
    ):
        self.config = config or RouterConfig()
        self.tiebreaker = tiebreaker
        self._router = PromptRouter()

    def route(self, prompt: str) -> Route:
        return self.classify(prompt).route

    def classify(self, prompt: str) -> RouteDecision:
        result = self._router.route(prompt or "")
        reasons = [(rule, 0) for rule in result.fired_rules]
        score = result.claude_score - result.side_score

        if any(rule in {"filepath", "stacktrace", "codeblock"} for rule in result.fired_rules):
            return RouteDecision(Route.CLAUDE, Band.HARD_OVERRIDE, score, reasons)

        if result.claude_score == result.side_score and self.tiebreaker is not None:
            try:
                route = self.tiebreaker(prompt)
            except Exception:
                route = Route.CLAUDE
            return RouteDecision(route, Band.AMBIGUOUS, score, reasons + [("tiebreaker", 0)])

        if result.claude_score == result.side_score:
            band = Band.AMBIGUOUS
        elif result.route == Route.SIDE_LLM:
            band = Band.CLEAR_QUESTION
        else:
            band = Band.CLEAR_TASK
        return RouteDecision(result.route, band, score, reasons)
