import re

# markdown code blocks
CODE_BLOCK = re.compile(r"```[\s\S]*?```")

# common stack traces
STACKTRACE = re.compile(
    r"(traceback|exception|error:|panic:|segmentation fault|stack trace)",
    re.IGNORECASE,
)

# src/main.py
FILEPATH = re.compile(
    r"((\w+[/\\])+)?[\w\-]+\.(py|ts|tsx|js|jsx|java|go|rs|cpp|c|cs|php|rb|swift|kt)",
    re.IGNORECASE,
)

QUESTION_WORDS = re.compile(
    r"\b(what|why|how|when|where|who|which|explain)\b",
    re.IGNORECASE,
)

EDIT_WORDS = re.compile(
    r"\b(fix|implement|refactor|rewrite|modify|update|add|remove|create|build)\b",
    re.IGNORECASE,
)

DEBUG_WORDS = re.compile(
    r"\b(debug|bug|issue|crash|fails|broken|doesn't work|not working|error)\b",
    re.IGNORECASE,
)

REPO_WORDS = re.compile(
    r"\b(repo|repository|project|codebase|folder|directory|file|module|class|function|branch|commit|pr)\b",
    re.IGNORECASE,
)

CODE_KEYWORDS = re.compile(
    r"\b(def|class|import|return|public|private|const|let|var|fn|struct|async|await|SELECT|INSERT|UPDATE)\b",
    re.IGNORECASE,
)