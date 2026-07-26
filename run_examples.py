from pathlib import Path

from primary_router.router import route


def main() -> None:
    examples_path = Path(__file__).with_name("test_examples.txt")
    prompts = [line.strip() for line in examples_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    for prompt in prompts:
        result = route(prompt)
        print(f"PROMPT: {prompt}")
        print(f"ROUTE: {result.route.value}")
        print(f"CLAUDE: {result.claude_score} | SIDE: {result.side_score} | CONFIDENCE: {result.confidence}")
        print(f"FIRED RULES: {', '.join(result.fired_rules) or 'none'}")
        print("-" * 80)


if __name__ == "__main__":
    main()
