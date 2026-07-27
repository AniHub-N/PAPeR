"""
Coding style preference detector.

Infers coding style preferences from observed behaviour.
"""

from __future__ import annotations

from preferences.inference.detectors.base import BasePreferenceDetector
from preferences.inference.utils import (
    candidate,
    count_events,
    has_enough_observations,
)
from preferences.models import (
    Observation,
    PreferenceCandidate,
)


class CodingStyleDetector(BasePreferenceDetector):
    """
    Detect coding style preferences.

    Current signals:

    - removed_comments
    - accepted_comments
    - converted_to_snake_case
    - converted_to_camel_case
    """

    @property
    def name(self) -> str:
        return "coding_style"

    def detect(
        self,
        observations: list[Observation],
    ) -> list[PreferenceCandidate]:

        candidates: list[PreferenceCandidate] = []

        counter = count_events(observations)

        # --------------------------------------------------
        # Comment Style
        # --------------------------------------------------

        removed = counter["removed_comments"]
        accepted = counter["accepted_comments"]

        total = removed + accepted

        if has_enough_observations(total):

            if removed > accepted:

                candidates.append(
                    candidate(
                        key="coding_style.comments",
                        value="minimal",
                        detector=self.name,
                        positive=removed,
                        total=total,
                        explanation=(
                            f"User removed generated comments "
                            f"{removed}/{total} times."
                        ),
                    )
                )

            elif accepted > removed:

                candidates.append(
                    candidate(
                        key="coding_style.comments",
                        value="detailed",
                        detector=self.name,
                        positive=accepted,
                        total=total,
                        explanation=(
                            f"User kept generated comments "
                            f"{accepted}/{total} times."
                        ),
                    )
                )

        # --------------------------------------------------
        # Naming Style
        # --------------------------------------------------

        snake = counter["converted_to_snake_case"]
        camel = counter["converted_to_camel_case"]

        total = snake + camel

        if has_enough_observations(total):

            if snake > camel:

                candidates.append(
                    candidate(
                        key="coding_style.naming",
                        value="snake_case",
                        detector=self.name,
                        positive=snake,
                        total=total,
                        explanation="User consistently converted identifiers to snake_case.",
                    )
                )

            elif camel > snake:

                candidates.append(
                    candidate(
                        key="coding_style.naming",
                        value="camel_case",
                        detector=self.name,
                        positive=camel,
                        total=total,
                        explanation="User consistently converted identifiers to camelCase.",
                    )
                )

        return candidates