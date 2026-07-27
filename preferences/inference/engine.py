"""
Preference inference engine.

Runs all registered detectors and collects candidate preferences.
"""

from __future__ import annotations

from collections.abc import Iterable

from preferences.inference.detectors.base import BasePreferenceDetector
from preferences.models import (
    Observation,
    PreferenceCandidate,
)


class PreferenceInferenceEngine:
    """
    Executes all preference detectors.
    """

    def __init__(
        self,
        detectors: Iterable[BasePreferenceDetector],
    ) -> None:
        self._detectors = list(detectors)

    @property
    def detectors(self) -> tuple[BasePreferenceDetector, ...]:
        """Registered detectors."""
        return tuple(self._detectors)

    def register(
        self,
        detector: BasePreferenceDetector,
    ) -> None:
        """
        Register a detector.

        Useful for plugins or dynamically loaded detectors.
        """
        self._detectors.append(detector)

    def detect(
        self,
        observations: list[Observation],
    ) -> list[PreferenceCandidate]:
        """
        Run every detector.

        Returns all candidate preferences.
        """

        candidates: list[PreferenceCandidate] = []

        for detector in self._detectors:

            detector_candidates = detector.detect(
                observations
            )

            candidates.extend(detector_candidates)

        return candidates