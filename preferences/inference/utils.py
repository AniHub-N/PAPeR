"""
Shared utilities for preference inference.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from preferences.models import (
    Evidence,
    Observation,
    PreferenceCandidate,
)

# ============================================================
# Constants
# ============================================================

MIN_OBSERVATIONS = 5


# ============================================================
# Observation Helpers
# ============================================================


def count_events(
    observations: list[Observation],
) -> Counter[str]:
    """
    Count occurrences of each observation event.
    """

    return Counter(
        observation.event
        for observation in observations
    )


def count_by_metadata(
    observations: list[Observation],
    key: str,
) -> Counter[Any]:
    """
    Count occurrences of a metadata field.

    Example:
        metadata["language"]
        metadata["framework"]
    """

    counter: Counter[Any] = Counter()

    for observation in observations:

        if key in observation.metadata:
            counter[observation.metadata[key]] += 1

    return counter


# ============================================================
# Confidence Helpers
# ============================================================


def has_enough_observations(
    observations: int,
    threshold: int = MIN_OBSERVATIONS,
) -> bool:
    """
    Returns True if enough observations exist
    to infer a preference.
    """

    return observations >= threshold


def confidence(
    positive: int,
    total: int,
) -> float:
    """
    Calculate inference confidence.

    Returns
    -------
    float
        Value between 0.0 and 1.0.
    """

    if total <= 0:
        return 0.0

    return round(positive / total, 2)


# ============================================================
# Candidate Builder
# ============================================================


def candidate(
    *,
    key: str,
    value: Any,
    detector: str,
    positive: int,
    total: int,
    explanation: str,
) -> PreferenceCandidate:
    """
    Build a PreferenceCandidate with populated evidence.
    """

    return PreferenceCandidate(
        key=key,
        value=value,
        evidence=Evidence(
            detector=detector,
            confidence=confidence(
                positive,
                total,
            ),
            observations=total,
            explanation=explanation,
        ),
    )