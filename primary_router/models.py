from dataclasses import dataclass
from enum import Enum


class Route(str, Enum):
    CLAUDE = "claude"
    SIDE_LLM = "side_llm"


@dataclass(slots=True)
class PromptFeatures:
    has_filepath: bool = False
    has_stacktrace: bool = False
    has_codeblock: bool = False
    has_repo_reference: bool = False
    has_workspace_reference: bool = False
    has_line_number: bool = False
    has_symbol_reference: bool = False
    has_contextual_reference: bool = False
    has_markdown_reference: bool = False
    has_request_phrase: bool = False
    has_explanation_phrase: bool = False
    has_comparison_phrase: bool = False
    mentions_repository_term: bool = False
    mentions_project_concept: bool = False
    mentions_technology: bool = False
    has_project_context: bool = False
    has_project_object: bool = False

    is_question: bool = False
    is_explanation: bool = False
    is_generation: bool = False
    is_editing: bool = False
    is_searching: bool = False
    is_debugging: bool = False
    is_refactoring: bool = False

    mentions_programming_language: bool = False
    mentions_framework: bool = False
    mentions_database: bool = False
    mentions_algorithm: bool = False
    mentions_cloud: bool = False
    mentions_auth_technology: bool = False
    mentions_knowledge: bool = False
    has_implementation_hint: bool = False
    is_general_knowledge_query: bool = False
    is_actionable_code_request: bool = False
    is_project_edit_request: bool = False
    is_project_generation_request: bool = False
    is_side_generation_candidate: bool = False
    is_claude_generation_candidate: bool = False
    is_explanation_intent: bool = False
    is_comparison_intent: bool = False
    is_debug_intent: bool = False
    is_search_intent: bool = False
    is_refactor_intent: bool = False
    is_edit_intent: bool = False
    is_question_intent: bool = False
    detected_intent: str = ""
    detected_object: str = ""
    detected_object_kind: str = ""


@dataclass(slots=True)
class RoutingResult:
    route: Route
    claude_score: int
    side_score: int
    confidence: float
    fired_rules: list[str]

    def __repr__(self) -> str:
        return (
            f"RoutingResult(route={self.route.value}, "
            f"claude={self.claude_score}, side={self.side_score}, "
            f"confidence={self.confidence:.2f}, rules={self.fired_rules})"
        )