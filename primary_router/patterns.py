import re

STACKTRACE = re.compile(
    r"(traceback|exception|panic:|segmentation fault|stack trace|error:)",
    re.IGNORECASE,
)

FILEPATH = re.compile(
    r"(?<!\w)(?:[A-Za-z]:)?(?:[./\\\w.-]+[\\/])+[\w.-]+\.(?:py|js|ts|tsx|jsx|go|rs|cpp|c|cs|java|kt|php|rb|swift|sql|json|yaml|yml|toml|md)\b",
    re.IGNORECASE,
)

CODEBLOCK = re.compile(r"```[\s\S]*?```", re.MULTILINE)

REPO_REFERENCE = re.compile(
    r"\b(repo|repository|project|workspace|codebase|branch|commit|pull request|pr)\b",
    re.IGNORECASE,
)

WORKSPACE_REFERENCE = re.compile(
    r"\b(workspace|project|codebase|repository|repo|current repo)\b",
    re.IGNORECASE,
)

LINE_NUMBER = re.compile(r"\b(line\s+\d+|L\d+)\b", re.IGNORECASE)

CAMEL_CASE_SYMBOL = re.compile(r"\b(?:[A-Z][a-z0-9]+){2,}\b")

CONTEXTUAL_REFERENCE = re.compile(r"\b(this|current|existing|our|my|that)\b", re.IGNORECASE)

MARKDOWN_REFERENCE = re.compile(r"\b(readme|docs?|documentation)\b", re.IGNORECASE)

QUESTION_START = {
    "what",
    "why",
    "how",
    "where",
    "when",
    "which",
    "who",
    "explain",
    "describe",
    "compare",
    "difference",
    "teach",
    "can",
}

EXPLANATION_START = {"explain", "describe", "tell", "summarize"}

EDITING_TASKS = {"edit", "modify", "refactor", "rename", "move", "delete", "fix", "update", "remove"}
SEARCHING_TASKS = {"search", "find", "locate", "open", "inspect", "look"}
DEBUGGING_TASKS = {"debug", "trace", "investigate", "diagnose"}
REFACTORING_TASKS = {"refactor", "rewrite", "clean"}
GENERATION_TASKS = {"write", "generate", "create", "implement", "build", "add", "make"}

PROGRAMMING_LANGUAGES = {
    "python",
    "java",
    "javascript",
    "typescript",
    "cpp",
    "c++",
    "go",
    "rust",
    "c",
    "csharp",
    "php",
    "ruby",
    "swift",
    "kotlin",
    "scala",
}

FRAMEWORKS = {
    "react",
    "nextjs",
    "next",
    "vue",
    "angular",
    "django",
    "flask",
    "fastapi",
    "spring",
    "express",
    "pytest",
}

DATABASES = {"sql", "mysql", "postgres", "postgresql", "sqlite", "mongodb", "redis", "elasticsearch"}
ALGORITHMS = {"bfs", "dfs", "dijkstra", "quicksort", "merge sort", "binary tree", "linked list", "dynamic programming", "regex"}
CLOUD_TERMS = {"aws", "azure", "gcp", "docker", "kubernetes", "terraform", "serverless", "lambda", "s3"}
AUTH_TERMS = {"oauth", "jwt", "openid", "sso", "session", "authorization"}

KNOWLEDGE_TERMS = PROGRAMMING_LANGUAGES | FRAMEWORKS | DATABASES | ALGORITHMS | CLOUD_TERMS | AUTH_TERMS

PROJECT_CONCEPTS = {
    "auth",
    "authentication",
    "login",
    "signup",
    "service",
    "middleware",
    "cache",
    "module",
    "class",
    "function",
    "method",
    "model",
    "schema",
    "migration",
    "test",
    "tests",
    "route",
    "endpoint",
    "api",
}

PROJECT_OBJECT_TERMS = {
    "auth",
    "authentication",
    "login",
    "middleware",
    "service",
    "cache",
    "module",
    "class",
    "function",
    "method",
    "model",
    "schema",
    "migration",
    "route",
    "endpoint",
    "api",
    "repository",
    "controller",
}

NON_PROJECT_SYMBOLS = {
    "HTTP",
    "HTTPS",
    "OAuth",
    "JWT",
    "REST",
    "API",
    "URL",
    "URI",
    "CLI",
    "UI",
    "DOM",
    "HTML",
    "CSS",
    "SQL",
    "JSON",
    "XML",
    "TCP",
    "UDP",
    "WebSocket",
    "WebSockets",
}
