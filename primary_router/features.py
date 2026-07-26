from models import PromptFeatures
import patterns


def extract_features(prompt: str) -> PromptFeatures:

    return PromptFeatures(
        has_code_block=bool(patterns.CODE_BLOCK.search(prompt)),
        has_stacktrace=bool(patterns.STACKTRACE.search(prompt)),
        has_filepath=bool(patterns.FILEPATH.search(prompt)),
        has_repo_reference=bool(patterns.REPO_WORDS.search(prompt)),
        has_edit_words=bool(patterns.EDIT_WORDS.search(prompt)),
        has_debug_words=bool(patterns.DEBUG_WORDS.search(prompt)),
        has_question_words=bool(patterns.QUESTION_WORDS.search(prompt)),
        has_code_keywords=bool(patterns.CODE_KEYWORDS.search(prompt)),
    )