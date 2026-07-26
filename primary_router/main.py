try:
    from .router import PromptRouter
except ImportError:  # pragma: no cover - supports direct script execution
    from router import PromptRouter


def main() -> None:
    router = PromptRouter()
    while True:
        prompt = input("> ").strip()
        if prompt.lower() in {"quit", "exit"}:
            break
        result = router.route(prompt)
        print(result)


if __name__ == "__main__":
    main()