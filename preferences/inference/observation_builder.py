"""
Build structured observations from raw interaction events.
"""

from __future__ import annotations

from collections.abc import Iterable

from preferences.models import Observation

from datetime import datetime


class ObservationBuilder:
    """
    Converts raw interaction events into normalized observations.

    This class performs no inference.

    Its only responsibility is normalization.
    """

    def build(
        self,
        events: Iterable[dict],
    ) -> list[Observation]:

        observations: list[Observation] = []

        for event in events:

            observation = self._convert(event)

            if observation is not None:
                observations.append(observation)

        return observations

    def _convert(
        self,
        event: dict,
    ) -> Observation | None:

        event_type = event.get("type")

        if event_type is None:
            return None

        from preferences.models import EventType

        return Observation(
            event=EventType(event_type),
            source=event.get("source", "unknown"),
            metadata=event.get("metadata", {}),
            timestamp=event.get("timestamp", datetime.utcnow()),
        )