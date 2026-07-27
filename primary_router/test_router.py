import pytest

from primary_router.models import Route
from primary_router.router import route


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("What is OAuth?", Route.SIDE_LLM),
        ("What is JWT?", Route.SIDE_LLM),
        ("Explain Docker.", Route.SIDE_LLM),
        ("Explain Kubernetes.", Route.SIDE_LLM),
        ("What is Redis?", Route.SIDE_LLM),
        ("How does TCP work?", Route.SIDE_LLM),
        ("Difference between HTTP and HTTPS.", Route.SIDE_LLM),
        ("Explain REST APIs.", Route.SIDE_LLM),
        ("What is GraphQL?", Route.SIDE_LLM),
        ("How does Git work?", Route.SIDE_LLM),
        ("Teach me BFS.", Route.SIDE_LLM),
        ("Teach me DFS.", Route.SIDE_LLM),
        ("Explain Dijkstra's algorithm.", Route.SIDE_LLM),
        ("What is dynamic programming?", Route.SIDE_LLM),
        ("Explain binary search.", Route.SIDE_LLM),
        ("What is a hash map?", Route.SIDE_LLM),
        ("How does a compiler work?", Route.SIDE_LLM),
        ("What is a mutex?", Route.SIDE_LLM),
        ("Explain multithreading.", Route.SIDE_LLM),
        ("What is dependency injection?", Route.SIDE_LLM),
        ("Explain CAP theorem.", Route.SIDE_LLM),
        ("What is Kubernetes?", Route.SIDE_LLM),
    ],
)
def test_general_knowledge_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Write a React component.", Route.CLAUDE),
        ("Write a Python decorator.", Route.CLAUDE),
        ("Generate a regex.", Route.CLAUDE),
        ("Write SQL.", Route.CLAUDE),
        ("Implement quicksort.", Route.CLAUDE),
        ("Implement merge sort.", Route.CLAUDE),
        ("Implement BFS.", Route.CLAUDE),
        ("Implement Dijkstra.", Route.CLAUDE),
        ("Generate Dockerfile.", Route.CLAUDE),
        ("Create Flask API.", Route.CLAUDE),
        ("Write FastAPI example.", Route.CLAUDE),
        ("Create Trie.", Route.CLAUDE),
        ("Write linked list.", Route.CLAUDE),
        ("Generate JWT.", Route.CLAUDE),
        ("Create CSS navbar.", Route.CLAUDE),
        ("Generate SQL.", Route.CLAUDE),
        ("Write unit tests.", Route.CLAUDE),
        ("Create login page.", Route.CLAUDE),
    ],
)
def test_generic_code_generation_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Fix src/auth.py", Route.CLAUDE),
        ("Edit app.py", Route.CLAUDE),
        ("Modify Dockerfile", Route.CLAUDE),
        ("Rename auth.py", Route.CLAUDE),
        ("Move utils.py", Route.CLAUDE),
        ("Update requirements.txt", Route.CLAUDE),
        ("Refactor models/user.py", Route.CLAUDE),
    ],
)
def test_file_operations_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Search UserService", Route.CLAUDE),
        ("Find LoginController", Route.CLAUDE),
        ("Open AuthMiddleware", Route.CLAUDE),
        ("Locate config.py", Route.CLAUDE),
        ("Search JWT usage", Route.CLAUDE),
        ("Find TODOs", Route.CLAUDE),
        ("List all routes", Route.CLAUDE),
    ],
)
def test_repository_search_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Fix this traceback.", Route.CLAUDE),
        ("Debug this exception.", Route.CLAUDE),
        ("Help with this stack trace.", Route.CLAUDE),
        ("Resolve this runtime error.", Route.CLAUDE),
        ("Fix compiler error.", Route.CLAUDE),
    ],
)
def test_stack_trace_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Implement auth.", Route.CLAUDE),
        ("Implement login.", Route.CLAUDE),
        ("Create middleware.", Route.CLAUDE),
        ("Rename UserService.", Route.CLAUDE),
        ("Update the API.", Route.CLAUDE),
        ("Refactor repository.", Route.CLAUDE),
        ("Move business logic.", Route.CLAUDE),
        ("Split this module.", Route.CLAUDE),
        ("Review this code.", Route.CLAUDE),
        ("Search LoginController.", Route.CLAUDE),
        ("Move utils.py.", Route.CLAUDE),
        ("Update requirements.txt.", Route.CLAUDE),
    ],
)
def test_project_editing_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Can you fix my authentication?", Route.CLAUDE),
        ("Can you rename this variable?", Route.CLAUDE),
        ("Can you debug this?", Route.CLAUDE),
        ("Can you clean this code?", Route.CLAUDE),
        ("Can you update my API?", Route.CLAUDE),
        ("Can you remove dead code?", Route.CLAUDE),
    ],
)
def test_natural_language_edit_requests(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Can you explain OAuth?", Route.SIDE_LLM),
        ("Can you teach me Redis?", Route.SIDE_LLM),
        ("Explain WebSockets.", Route.SIDE_LLM),
        ("Explain React hooks.", Route.SIDE_LLM),
        ("Compare Flask vs FastAPI.", Route.SIDE_LLM),
        ("Explain Docker Compose.", Route.SIDE_LLM),
    ],
)
def test_explanation_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Implement OAuth.", Route.CLAUDE),
        ("Implement auth.", Route.CLAUDE),
        ("Create login.", Route.CLAUDE),
        ("Create API.", Route.CLAUDE),
        ("Write middleware.", Route.CLAUDE),
        ("Generate authentication.", Route.CLAUDE),
        ("Implement Redis cache.", Route.CLAUDE),
        ("Implement OAuth authentication.", Route.CLAUDE),
    ],
)
def test_ambiguous_generation_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


def test_mixed_explanation_and_implementation_prompts():
    result = route("What is OAuth and implement it")
    assert result.route == Route.CLAUDE, (
        f"Expected {Route.CLAUDE.value} for mixed explanation/implementation prompt, "
        f"got {result.route.value} with scores {result.claude_score}/{result.side_score} "
        f"and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Explain OAuth and implement it.", Route.CLAUDE),
        ("Tell me where JWT is configured and fix it.", Route.CLAUDE),
        ("Summarize AuthService then refactor it.", Route.CLAUDE),
    ],
)
def test_mixed_explanation_and_action_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for mixed prompt {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Where is auth.ts?", Route.SIDE_LLM),
        ("Which files use PostHog?", Route.SIDE_LLM),
        ("List all routes.", Route.SIDE_LLM),
        ("Show me the routing layer.", Route.SIDE_LLM),
        ("Show me auth.ts.", Route.SIDE_LLM),
    ],
)
def test_code_lookup_and_inspection_prompts(prompt, expected):
    result = route(prompt)
    assert result.route == expected, (
        f"Expected {expected.value} for lookup prompt {prompt!r}, got {result.route.value} "
        f"with scores {result.claude_score}/{result.side_score} and rules {result.fired_rules}"
    )


def test_router_returns_actionable_debug_metadata():
    result = route("Refactor LoginController")
    assert 0.0 <= result.confidence <= 1.0
    assert result.fired_rules
    assert result.route in {Route.CLAUDE, Route.SIDE_LLM}