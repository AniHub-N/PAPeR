# Primary Router

Primary Router is a deterministic prompt router that sends work to Claude Code or to a secondary LLM based on weighted, explainable evidence.

## Architecture

The project is organized around a small set of focused modules:

- [primary_router/models.py](primary_router/models.py): shared domain models for routes and extracted features.
- [primary_router/patterns.py](primary_router/patterns.py): regexes and keyword dictionaries used for feature extraction.
- [primary_router/features.py](primary_router/features.py): pure feature extraction only; it never makes routing decisions.
- [primary_router/rules.py](primary_router/rules.py): the unified rule catalog for single-feature and compound rules.
- [primary_router/router.py](primary_router/router.py): a generic scoring engine that evaluates rules and returns a routing decision.
- [primary_router/test_router.py](primary_router/test_router.py): regression and behavior tests.

## Feature Extraction

Feature extraction is intentionally narrow and deterministic. It looks for signals such as:

- file paths
- stack traces
- repository or workspace references
- line numbers
- CamelCase symbols
- markdown code blocks
- contextual references such as "this", "current", or "existing"
- intent cues such as questions, explanations, generation, editing, debugging, searching, and refactoring
- programming-language and framework terminology

The extractor only reports evidence and does not make routing decisions.

## Rule Engine

Rules are expressed through a single data model:

- each rule has a name, route, weight, and required features
- single-feature rules fire when one feature is present
- compound rules fire when multiple features are present together
- the router scores Claude and side-LLM evidence independently and uses the higher score to decide

## Adding New Rules

1. Add a new feature to [primary_router/features.py](primary_router/features.py) if it is a new signal.
2. Add a corresponding field to [primary_router/models.py](primary_router/models.py) if it represents a meaningful concept.
3. Add a rule to [primary_router/rules.py](primary_router/rules.py) with the appropriate weight and route.
4. Add or update tests in [primary_router/test_router.py](primary_router/test_router.py).

## Tuning Weights

Weights are intentionally simple and explicit. Increase a rule's weight when you want stronger evidence for that route, and lower it when the signal is noisy. Because routing is deterministic, it is easy to understand and tune.

## Testing

Run the test suite with:

```bash
pytest -q
```