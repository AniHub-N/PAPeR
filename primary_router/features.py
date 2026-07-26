from __future__ import annotations

import re

try:
    from . import patterns
    from .models import PromptFeatures
except ImportError:  # pragma: no cover - supports direct script execution
    import patterns
    from models import PromptFeatures


def _first_word(text: str) -> str:
    words = text.split()
    return words[0].lower() if words else ""


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _contains_word(text: str, terms: set[str]) -> bool:
    return any(re.search(rf"(?<!\\w){re.escape(term)}(?!\\w)", text) for term in terms)


def _contains_actionable_verb(text: str) -> bool:
    verbs = patterns.EDITING_TASKS | patterns.SEARCHING_TASKS | patterns.DEBUGGING_TASKS | patterns.REFACTORING_TASKS | patterns.GENERATION_TASKS
    escaped_verbs = "|".join(sorted((re.escape(term) for term in verbs), key=len, reverse=True))
    if re.search(rf"^(?:{escaped_verbs})\b", text):
        return True
    return bool(re.search(rf"\b(?:and|then|,|;)\s+(?:{escaped_verbs})\b", text))


def _extract_intent_and_object(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    if not cleaned:
        return "", ""

    lower = cleaned.lower()
    for prefix in ("can you ", "could you ", "would you ", "please ", "help me "):
        if lower.startswith(prefix):
            rest = cleaned[len(prefix):].strip()
            if not rest:
                return "request", ""
            lower_rest = rest.lower()
            if lower_rest.startswith(("explain ", "teach ", "describe ", "compare ", "difference ")):
                verb = lower_rest.split()[0]
                return verb, rest[len(verb):].strip()
            for verb in sorted(patterns.EDITING_TASKS | patterns.SEARCHING_TASKS | patterns.DEBUGGING_TASKS | patterns.REFACTORING_TASKS, key=len, reverse=True):
                if lower_rest.startswith(verb + " "):
                    return verb, rest[len(verb):].strip()
            for verb in sorted(patterns.GENERATION_TASKS, key=len, reverse=True):
                if lower_rest.startswith(verb + " "):
                    return verb, rest[len(verb):].strip()
            return "request", rest

    for verb in sorted(patterns.GENERATION_TASKS, key=len, reverse=True):
        if lower.startswith(verb + " "):
            return verb, cleaned[len(verb):].strip()

    for verb in sorted(patterns.EDITING_TASKS | patterns.SEARCHING_TASKS | patterns.DEBUGGING_TASKS | patterns.REFACTORING_TASKS, key=len, reverse=True):
        if lower.startswith(verb + " "):
            return verb, cleaned[len(verb):].strip()

    if lower.startswith(("explain ", "teach ", "describe ", "compare ", "difference ")):
        verb = lower.split()[0]
        return verb, cleaned[len(verb):].strip()

    return "", ""


def _looks_like_symbol(value: str) -> bool:
    if not value:
        return False
    normalized = value.strip().strip(".,!?")
    if not normalized:
        return False
    if normalized in patterns.NON_PROJECT_SYMBOLS:
        return False
    if normalized.lower() in {"oauth", "jwt", "redis", "docker", "kubernetes", "react", "flask", "fastapi", "sql", "css", "html", "http", "https"}:
        return False
    if re.fullmatch(r"[A-Z][a-zA-Z0-9]+", normalized):
        return True
    return bool(re.search(r"[A-Z][a-z]+", normalized)) and not normalized.lower().startswith(("http", "https", "react", "docker", "fastapi", "flask"))


def _classify_object(value: str) -> str:
    normalized = value.strip().strip(".,!?")
    if not normalized:
        return "concept"
    lower = normalized.lower()
    if re.search(r"(?:^|\s)(?:\.py|\.js|\.ts|\.tsx|\.jsx|\.go|\.rs|\.cpp|\.c|\.java|\.kt|\.php|\.rb|\.swift|\.sql|\.md)(?:$|\b)", normalized):
        return "path"
    if any(term in lower for term in patterns.PROGRAMMING_LANGUAGES | patterns.FRAMEWORKS | patterns.DATABASES | patterns.ALGORITHMS | patterns.CLOUD_TERMS | {"rest", "graphql", "git", "tcp", "udp", "websocket", "websockets"}):
        return "technology"
    if normalized.lower() in {"oauth", "jwt", "redis", "docker", "kubernetes", "react", "flask", "fastapi", "sql", "css", "html", "http", "https"}:
        return "technology"
    if _contains_word(lower, patterns.PROJECT_OBJECT_TERMS):
        return "project"
    if _looks_like_symbol(normalized):
        return "symbol"
    return "concept"


def extract_features(prompt: str) -> PromptFeatures:
    text = prompt.strip()
    lower = text.lower()
    first_word = _first_word(text)

    features = PromptFeatures()

    features.has_stacktrace = bool(patterns.STACKTRACE.search(text))
    features.has_filepath = bool(patterns.FILEPATH.search(text))
    features.has_codeblock = bool(patterns.CODEBLOCK.search(text))
    features.has_repo_reference = bool(patterns.REPO_REFERENCE.search(text))
    features.has_workspace_reference = bool(patterns.WORKSPACE_REFERENCE.search(text))
    features.has_line_number = bool(patterns.LINE_NUMBER.search(text))
    features.has_symbol_reference = bool(patterns.CAMEL_CASE_SYMBOL.search(text))
    features.has_contextual_reference = bool(patterns.CONTEXTUAL_REFERENCE.search(text))
    features.has_markdown_reference = bool(patterns.MARKDOWN_REFERENCE.search(text))
    features.has_request_phrase = bool(re.search(r"\b(can|could|would|please|help me)\b", lower))
    features.has_explanation_phrase = bool(re.search(r"\b(explain|teach|describe|compare|difference)\b", lower))
    features.has_comparison_phrase = bool(re.search(r"\b(vs|versus|compare|difference between)\b", lower))
    features.mentions_repository_term = bool(patterns.REPO_REFERENCE.search(text))
    has_actionable_verb = _contains_actionable_verb(lower)

    features.is_question = first_word in patterns.QUESTION_START or text.endswith("?")
    features.is_explanation = first_word in patterns.EXPLANATION_START or lower.startswith("explain")
    features.is_generation = first_word in patterns.GENERATION_TASKS
    features.is_editing = first_word in patterns.EDITING_TASKS
    features.is_searching = first_word in patterns.SEARCHING_TASKS
    features.is_debugging = first_word in patterns.DEBUGGING_TASKS
    features.is_refactoring = first_word in patterns.REFACTORING_TASKS

    features.mentions_programming_language = _contains_any(lower, patterns.PROGRAMMING_LANGUAGES)
    features.mentions_framework = _contains_any(lower, patterns.FRAMEWORKS)
    features.mentions_database = _contains_any(lower, patterns.DATABASES)
    features.mentions_algorithm = _contains_any(lower, patterns.ALGORITHMS)
    features.mentions_cloud = _contains_any(lower, patterns.CLOUD_TERMS)
    features.mentions_auth_technology = _contains_any(lower, patterns.AUTH_TERMS)
    features.mentions_knowledge = (
        features.mentions_programming_language
        or features.mentions_framework
        or features.mentions_database
        or features.mentions_algorithm
        or features.mentions_cloud
        or features.mentions_auth_technology
    )
    features.mentions_technology = features.mentions_knowledge or features.mentions_auth_technology

    features.mentions_project_concept = _contains_word(lower, patterns.PROJECT_CONCEPTS)

    intent, obj = _extract_intent_and_object(text)
    features.detected_intent = intent.capitalize() if intent else ""
    features.detected_object = obj.strip()
    features.detected_object_kind = _classify_object(obj)
    features.mentions_project_concept = features.mentions_project_concept or _contains_word(obj.lower(), patterns.PROJECT_OBJECT_TERMS)
    project_object_terms = _contains_word(obj.lower(), patterns.PROJECT_OBJECT_TERMS)
    is_framework_example = bool(features.detected_object) and features.detected_object_kind == "technology" and any(term in obj.lower() for term in patterns.FRAMEWORKS | {"api", "example", "component", "decorator", "css", "navbar", "regex", "sql", "dockerfile", "jwt", "trie"})
    features.has_project_object = bool(features.detected_object) and (
        features.detected_object_kind == "project"
        or project_object_terms
        or (features.detected_object_kind == "symbol" and len(re.findall(r"[A-Za-z]+", obj)) > 1)
    )
    if features.detected_object_kind == "technology" and not project_object_terms:
        features.has_project_object = False
    if is_framework_example:
        features.has_project_object = False

    features.is_project_edit_request = (
        features.has_request_phrase
        and not features.is_explanation_intent
        and not features.is_question
        and (
            features.is_editing
            or features.is_debugging
            or features.is_refactoring
            or features.is_searching
            or features.has_contextual_reference
            or features.has_project_object
            or bool(re.search(r"\b(fix|remove|rename|debug|clean|delete|update|change|refactor|modify|move)\b", lower))
        )
    )
    features.is_project_generation_request = features.is_generation and features.has_project_object
    features.is_side_generation_candidate = False
    features.is_claude_generation_candidate = features.is_generation and (features.has_project_context or features.has_project_object or features.has_filepath or features.is_editing or features.is_debugging or features.is_refactoring or features.is_searching)
    features.is_actionable_code_request = (
        (features.is_generation or features.is_editing or features.is_debugging or features.is_refactoring or features.is_searching)
        or has_actionable_verb
        or (features.is_project_edit_request and not features.is_explanation_intent)
        or (features.is_project_generation_request and not features.is_explanation_intent)
        or (features.is_claude_generation_candidate and not features.is_explanation_intent)
        or (features.is_edit_intent and not features.is_explanation_intent)
        or (features.is_debug_intent and not features.is_explanation_intent)
        or (features.is_refactor_intent and not features.is_explanation_intent)
        or (features.is_search_intent and not features.is_explanation_intent)
    )

    features.is_explanation_intent = features.is_explanation or features.has_explanation_phrase or features.has_comparison_phrase
    features.is_mixed_action_request = (
        has_actionable_verb
        and (
            features.is_explanation_intent
            or features.has_explanation_phrase
            or features.has_comparison_phrase
        )
        and (
            features.is_editing
            or features.is_debugging
            or features.is_refactoring
            or features.is_searching
            or features.is_generation
            or features.is_project_edit_request
            or features.is_project_generation_request
            or features.is_actionable_code_request
        )
    )
    features.is_comparison_intent = features.has_comparison_phrase
    features.is_debug_intent = features.is_debugging or features.has_stacktrace
    features.is_search_intent = (
        features.is_searching
        or features.mentions_repository_term
        or (features.is_question and bool(re.search(r"\b(where|show|list|find|locate|open|inspect|look|which files use|which file uses|what files use|what file uses)\b", lower)))
    )
    features.is_refactor_intent = features.is_refactoring or (features.is_editing and features.has_contextual_reference)
    features.is_edit_intent = features.is_editing or (
        features.has_request_phrase
        and not features.is_explanation_intent
        and (
            features.has_filepath
            or features.has_contextual_reference
            or features.has_project_object
            or features.is_debugging
            or features.is_refactoring
            or features.is_searching
            or bool(re.search(r"\b(fix|remove|rename|debug|clean|delete|update|change|refactor|modify|move)\b", lower))
        )
    )
    features.is_question_intent = (
        features.is_question
        and not features.has_request_phrase
        and not has_actionable_verb
        and not (features.is_explanation_intent or features.is_debug_intent or features.is_search_intent or features.is_edit_intent or features.is_refactor_intent)
    )
    if features.is_generation and not features.has_project_object and not features.has_project_context and not features.has_filepath:
        features.is_question_intent = False

    features.has_implementation_hint = features.is_generation or features.is_editing or features.is_debugging or features.is_refactoring
    features.has_project_context = (
        features.has_filepath
        or features.has_repo_reference
        or features.has_workspace_reference
        or features.has_line_number
        or (features.has_symbol_reference and not (features.is_explanation_intent or features.is_question_intent))
        or features.has_contextual_reference
        or features.has_markdown_reference
        or features.has_stacktrace
    )
    features.is_general_knowledge_query = (
        features.is_question
        and not features.is_actionable_code_request
        and not features.has_project_context
        and not features.has_implementation_hint
        and not features.has_request_phrase
        and not features.is_generation
    )

    return features