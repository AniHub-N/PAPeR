from dataclasses import dataclass
from enum import Enum

try:
    from .models import Route
except ImportError:  # pragma: no cover - supports direct script execution
    from models import Route


class RuleKind(str, Enum):
    SINGLE = "single"
    COMPOUND = "compound"


@dataclass(frozen=True, slots=True)
class Rule:
    name: str
    route: Route
    weight: int
    requires: tuple[str, ...] = ()
    kind: RuleKind = RuleKind.SINGLE


RULES = [
    Rule(name="filepath", route=Route.CLAUDE, weight=10, requires=("has_filepath",)),
    Rule(name="stacktrace", route=Route.CLAUDE, weight=12, requires=("has_stacktrace",)),
    Rule(name="codeblock", route=Route.CLAUDE, weight=8, requires=("has_codeblock",)),
    Rule(name="repo_reference", route=Route.CLAUDE, weight=7, requires=("has_repo_reference",)),
    Rule(name="workspace_reference", route=Route.CLAUDE, weight=6, requires=("has_workspace_reference",)),
    Rule(name="line_number", route=Route.CLAUDE, weight=7, requires=("has_line_number",)),
    Rule(name="symbol_reference", route=Route.CLAUDE, weight=7, requires=("has_symbol_reference",)),
    Rule(name="contextual_reference", route=Route.CLAUDE, weight=5, requires=("has_contextual_reference",)),
    Rule(name="project_context", route=Route.CLAUDE, weight=6, requires=("has_project_context",)),
    Rule(name="debug_intent", route=Route.CLAUDE, weight=8, requires=("is_debug_intent",)),
    Rule(name="search_intent", route=Route.CLAUDE, weight=7, requires=("is_search_intent",)),
    Rule(name="edit_intent", route=Route.CLAUDE, weight=6, requires=("is_edit_intent",)),
    Rule(name="refactor_intent", route=Route.CLAUDE, weight=7, requires=("is_refactor_intent",)),
    Rule(name="project_edit_request", route=Route.CLAUDE, weight=8, requires=("is_project_edit_request",)),
    Rule(name="project_generation_request", route=Route.CLAUDE, weight=7, requires=("is_project_generation_request",)),
    Rule(name="mixed_action_request", route=Route.CLAUDE, weight=10, requires=("is_mixed_action_request",)),
    Rule(name="explanation_intent", route=Route.SIDE_LLM, weight=8, requires=("is_explanation_intent",)),
    Rule(name="comparison_intent", route=Route.SIDE_LLM, weight=6, requires=("is_comparison_intent",)),
    Rule(name="question_intent", route=Route.SIDE_LLM, weight=6, requires=("is_question_intent",)),
    Rule(name="claude_generation_candidate", route=Route.CLAUDE, weight=5, requires=("is_claude_generation_candidate",)),
    Rule(name="actionable_code_request", route=Route.CLAUDE, weight=6, requires=("is_actionable_code_request",)),
    Rule(name="knowledge", route=Route.SIDE_LLM, weight=4, requires=("mentions_knowledge", "is_general_knowledge_query")),
    Rule(name="general_knowledge", route=Route.SIDE_LLM, weight=4, requires=("is_general_knowledge_query",)),
]


COMPOUND_RULES = [
    Rule(
        name="project_generation",
        route=Route.CLAUDE,
        weight=8,
        requires=("is_generation", "has_project_context"),
        kind=RuleKind.COMPOUND,
    ),
    Rule(
        name="symbol_lookup",
        route=Route.CLAUDE,
        weight=6,
        requires=("is_question_intent", "has_symbol_reference"),
        kind=RuleKind.COMPOUND,
    ),
    Rule(
        name="project_debug",
        route=Route.CLAUDE,
        weight=7,
        requires=("is_debug_intent", "has_filepath"),
        kind=RuleKind.COMPOUND,
    ),
    Rule(
        name="project_edit",
        route=Route.CLAUDE,
        weight=6,
        requires=("is_edit_intent", "has_contextual_reference"),
        kind=RuleKind.COMPOUND,
    ),
    Rule(
        name="tech_question",
        route=Route.SIDE_LLM,
        weight=4,
        requires=("is_question_intent", "mentions_knowledge"),
        kind=RuleKind.COMPOUND,
    ),
    Rule(
        name="implementation_question",
        route=Route.SIDE_LLM,
        weight=3,
        requires=("is_question_intent", "has_implementation_hint"),
        kind=RuleKind.COMPOUND,
    ),
]