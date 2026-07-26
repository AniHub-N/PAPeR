from router import PromptRouter
from models import Route

router = PromptRouter()

TEST_CASES = [

    # ==========================================================
    # GENERAL KNOWLEDGE (Should go to Side LLM)
    # ==========================================================

    ("What is a binary tree?", Route.SIDE_LLM),
    ("Explain BFS.", Route.SIDE_LLM),
    ("Explain DFS.", Route.SIDE_LLM),
    ("What is OAuth?", Route.SIDE_LLM),
    ("How does TCP work?", Route.SIDE_LLM),
    ("Difference between HTTP and HTTPS?", Route.SIDE_LLM),
    ("Explain recursion.", Route.SIDE_LLM),
    ("Explain dynamic programming.", Route.SIDE_LLM),
    ("How does Python's GIL work?", Route.SIDE_LLM),
    ("What is Docker?", Route.SIDE_LLM),
    ("Explain Kubernetes.", Route.SIDE_LLM),
    ("How does Git work?", Route.SIDE_LLM),
    ("What is REST?", Route.SIDE_LLM),
    ("Explain GraphQL.", Route.SIDE_LLM),
    ("What is an AVL tree?", Route.SIDE_LLM),
    ("What is a heap?", Route.SIDE_LLM),
    ("Explain merge sort.", Route.SIDE_LLM),
    ("Explain quicksort.", Route.SIDE_LLM),
    ("What is a hash table?", Route.SIDE_LLM),
    ("Explain JWT.", Route.SIDE_LLM),

    # ==========================================================
    # PROJECT / CODEBASE (Should go to Claude)
    # ==========================================================

    ("Fix auth.py", Route.CLAUDE),
    ("Implement JWT authentication", Route.CLAUDE),
    ("Refactor auth.ts", Route.CLAUDE),
    ("Update src/main.py", Route.CLAUDE),
    ("Debug this traceback", Route.CLAUDE),
    ("Fix the failing unit tests", Route.CLAUDE),
    ("Search the repository for UserService", Route.CLAUDE),
    ("Where is LoginController defined?", Route.CLAUDE),
    ("Update README.md", Route.CLAUDE),
    ("Modify package.json", Route.CLAUDE),
    ("Create a new React component", Route.CLAUDE),
    ("Add logging to api.py", Route.CLAUDE),
    ("Fix bug in server.go", Route.CLAUDE),
    ("Refactor src/api/user.ts", Route.CLAUDE),
    ("Edit docker-compose.yml", Route.CLAUDE),
    ("Implement caching in cache.py", Route.CLAUDE),
    ("Remove duplicate code from utils.py", Route.CLAUDE),
    ("Optimize db/query.sql", Route.CLAUDE),
    ("Search the codebase", Route.CLAUDE),
    ("Open src/index.js", Route.CLAUDE),

    # ==========================================================
    # STACK TRACES
    # ==========================================================

    ("Traceback (most recent call last)...", Route.CLAUDE),
    ("ValueError: invalid literal", Route.CLAUDE),
    ("TypeError: object is not callable", Route.CLAUDE),
    ("Segmentation fault", Route.CLAUDE),
    ("panic: runtime error", Route.CLAUDE),
    ("Exception in thread main", Route.CLAUDE),
    ("NullPointerException", Route.CLAUDE),
    ("Error: Cannot find module", Route.CLAUDE),

    # ==========================================================
    # FILE PATHS
    # ==========================================================

    ("src/main.py", Route.CLAUDE),
    ("backend/api/routes.py", Route.CLAUDE),
    ("frontend/src/App.tsx", Route.CLAUDE),
    ("lib/utils.js", Route.CLAUDE),
    ("main.cpp", Route.CLAUDE),
    ("server.go", Route.CLAUDE),
    ("index.html", Route.CLAUDE),

    # ==========================================================
    # CODE BLOCKS
    # ==========================================================

    (
        """```python
def hello():
    pass
```""",
        Route.CLAUDE,
    ),

    (
        """```javascript
console.log("Hello")
```""",
        Route.CLAUDE,
    ),

    # ==========================================================
    # EDGE CASES
    # ==========================================================

    ("Write a Python quicksort implementation", Route.SIDE_LLM),
    ("Generate a regex for emails", Route.SIDE_LLM),
    ("Write SQL to find duplicates", Route.SIDE_LLM),
    ("How do I reverse a linked list?", Route.SIDE_LLM),
    ("Implement Dijkstra's algorithm from scratch", Route.SIDE_LLM),
    ("Write a React button component", Route.SIDE_LLM),
    ("How do I center a div in CSS?", Route.SIDE_LLM),
]

passed = 0
failed = 0

print("=" * 80)
print("RUNNING ROUTER TESTS")
print("=" * 80)

for i, (prompt, expected) in enumerate(TEST_CASES, start=1):

    result = router.route(prompt)

    if result == expected:
        print(f"[PASS] Test {i:02d}")
        print(f"Prompt   : {prompt}")
        print(f"Route    : {result.value}")
        print("-" * 80)
        passed += 1

    else:
        print(f"[FAIL] Test {i:02d}")
        print(f"Prompt   : {prompt}")
        print(f"Expected : {expected.value}")
        print(f"Got      : {result.value}")
        print("-" * 80)
        failed += 1

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total Tests : {len(TEST_CASES)}")
print(f"Passed      : {passed}")
print(f"Failed      : {failed}")
print(f"Accuracy    : {passed / len(TEST_CASES) * 100:.2f}%")

if failed == 0:
    print("\n🎉 All tests passed!")
else:
    print(f"\n⚠️  {failed} test(s) failed.")