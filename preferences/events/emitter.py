from __future__ import annotations

from preferences.events.models import Event
from preferences.models import EventType


class EventEmitter:
    """
    Helper for constructing events.
    """

    def emit(
        self,
        event: EventType,
        *,
        source: str,
        **metadata,
    ) -> Event:

        return Event(
            event=event,
            source=source,
            metadata=metadata,
        )