from dataclasses import dataclass
from enum import Enum


class Route(Enum):
    CLAUDE = "claude"
    SIDE_LLM = "side_llm"


@dataclass
class PromptFeatures:
    has_code_block: bool = False
    has_stacktrace: bool = False
    has_filepath: bool = False
    has_repo_reference: bool = False
    has_edit_words: bool = False
    has_debug_words: bool = False
    has_question_words: bool = False
    has_code_keywords: bool = False