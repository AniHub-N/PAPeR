from router import PromptRouter

router = PromptRouter()

while True:

    prompt = input("> ")

    if prompt.lower() == "quit":
        break

    route = router.route(prompt)

    print(route.value)