from __future__ import annotations

try:
    from .features import extract_features
    from .models import Route, RoutingResult
    from .rules import COMPOUND_RULES, RULES
except ImportError:  # pragma: no cover - supports direct script execution
    from features import extract_features
    from models import Route, RoutingResult
    from rules import COMPOUND_RULES, RULES


class PromptRouter:
    def __init__(self) -> None:
        self.rules = RULES + COMPOUND_RULES

    def route(self, prompt: str) -> RoutingResult:
        features = extract_features(prompt)
        claude_score = 0
        side_score = 0
        fired_rules: list[str] = []

        for rule in self.rules:
            if all(getattr(features, feature) for feature in rule.requires):
                fired_rules.append(rule.name)
                if rule.route == Route.CLAUDE:
                    claude_score += rule.weight
                else:
                    side_score += rule.weight

        total_score = claude_score + side_score
        if total_score == 0:
            decision = Route.CLAUDE
            confidence = 0.0
        else:
            winner_score = max(claude_score, side_score)
            margin = abs(claude_score - side_score)
            confidence = round(min(1.0, (winner_score / total_score) * 0.8 + (margin / total_score) * 0.2), 2)
            if claude_score > side_score:
                decision = Route.CLAUDE
            elif side_score > claude_score:
                decision = Route.SIDE_LLM
            else:
                decision = Route.CLAUDE

        return RoutingResult(
            route=decision,
            claude_score=claude_score,
            side_score=side_score,
            confidence=confidence,
            fired_rules=fired_rules,
        )


def route(prompt: str) -> RoutingResult:
    return PromptRouter().route(prompt)