"""
High-level service for preference inference.
"""

from __future__ import annotations

from collections.abc import Iterable

from preferences.inference.engine import PreferenceInferenceEngine
from preferences.inference.observation_builder import ObservationBuilder
from preferences.inference.updater import PreferenceUpdater
from preferences.models import (
    PreferenceCandidate,
    PreferenceCollection,
)


class PreferenceInferenceService:
    """
    Coordinates the complete preference inference pipeline.
    """

    def __init__(
        self,
        engine: PreferenceInferenceEngine,
        updater: PreferenceUpdater,
        builder: ObservationBuilder | None = None,
    ) -> None:

        self.engine = engine
        self.updater = updater
        self.builder = builder or ObservationBuilder()

    def infer(
        self,
        events: Iterable[dict],
    ) -> list[PreferenceCandidate]:
        """
        Infer preference candidates from raw events.
        """

        observations = self.builder.build(events)

        return self.engine.detect(observations)

    def learn(
        self,
        events: Iterable[dict],
        preferences: PreferenceCollection,
    ) -> PreferenceCollection:
        """
        Learn preferences from raw events.
        """

        candidates = self.infer(events)

        return self.updater.update(
            preferences,
            candidates,
        )