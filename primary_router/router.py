from models import Route
from features import extract_features


class PromptRouter:

    def route(self, prompt: str) -> Route:

        f = extract_features(prompt)

        # Immediate Claude conditions

        if f.has_stacktrace:
            return Route.CLAUDE

        if f.has_filepath:
            return Route.CLAUDE

        if f.has_code_block:
            return Route.CLAUDE

        if f.has_debug_words:
            return Route.CLAUDE

        if f.has_edit_words:
            return Route.CLAUDE

        if f.has_repo_reference:
            return Route.CLAUDE

        if f.has_code_keywords:
            return Route.CLAUDE

        # General knowledge

        if f.has_question_words:
            return Route.SIDE_LLM

        # Safe default

        return Route.CLAUDE