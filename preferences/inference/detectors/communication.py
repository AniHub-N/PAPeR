"""
Communication preference detector.

Infers communication preferences from observed behaviour.
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


class CommunicationDetector(BasePreferenceDetector):
    """
    Detects communication preferences.

    Current signals:

    - requested_concise_response
    - requested_detailed_response
    - requested_examples
    """

    @property
    def name(self) -> str:
        return "communication"

    def detect(
        self,
        observations: list[Observation],
    ) -> list[PreferenceCandidate]:

        candidates: list[PreferenceCandidate] = []

        counter = count_events(observations)

        # --------------------------------------------------
        # Explanation depth
        # --------------------------------------------------

        concise = counter["requested_concise_response"]
        detailed = counter["requested_detailed_response"]

        total = concise + detailed

        if has_enough_observations(total):

            if concise > detailed:

                candidates.append(
                    candidate(
                        key="communication.explanation_depth",
                        value="concise",
                        detector=self.name,
                        positive=concise,
                        total=total,
                        explanation=(
                            f"User requested concise explanations "
                            f"{concise}/{total} times."
                        ),
                    )
                )

            elif detailed > concise:

                candidates.append(
                    candidate(
                        key="communication.explanation_depth",
                        value="detailed",
                        detector=self.name,
                        positive=detailed,
                        total=total,
                        explanation=(
                            f"User requested detailed explanations "
                            f"{detailed}/{total} times."
                        ),
                    )
                )

        # --------------------------------------------------
        # Examples
        # --------------------------------------------------

        examples = counter["requested_examples"]

        if has_enough_observations(examples):

            candidates.append(
                candidate(
                    key="communication.examples",
                    value="always",
                    detector=self.name,
                    positive=examples,
                    total=examples,
                    explanation="User frequently requested examples.",
                )
            )

        return candidates