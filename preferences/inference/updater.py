"""
Updates inferred preferences from inference candidates.
"""

from __future__ import annotations

from preferences.models import (
    Preference,
    PreferenceCandidate,
    PreferenceCollection,
    PreferenceSource,
)


class PreferenceUpdater:
    """
    Applies inferred preference candidates to a preference collection.
    """

    def __init__(
        self,
        minimum_confidence: float = 0.70,
    ) -> None:
        self.minimum_confidence = minimum_confidence

    def update(
        self,
        collection: PreferenceCollection,
        candidates: list[PreferenceCandidate],
    ) -> PreferenceCollection:
        """
        Apply candidates to an existing preference collection.
        """

        for candidate in candidates:

            if candidate.evidence.confidence < self.minimum_confidence:
                continue

            preference = Preference(
                key=candidate.key,
                value=candidate.value,
                source=PreferenceSource.INFERRED,
                confidence=candidate.evidence.confidence,
            )

            collection.set(preference)

        return collection