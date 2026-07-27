from __future__ import annotations

from preferences.events.emitter import EventEmitter
from preferences.events.models import Event
from preferences.models import EventType


class EventExtractor:
    """
    Extract preference events from an interaction.

    Initially rule-based.
    """

    def __init__(self) -> None:
        self.emitter = EventEmitter()

    def extract(
        self,
        user_message: str,
        assistant_response: str,
    ) -> list[Event]:

        events: list[Event] = []

        message = user_message.lower()

        if "shorter" in message:
            events.append(
                self.emitter.emit(
                    EventType.REQUESTED_CONCISE_RESPONSE,
                    source="chat",
                )
            )

        if "more detail" in message:
            events.append(
                self.emitter.emit(
                    EventType.REQUESTED_DETAILED_RESPONSE,
                    source="chat",
                )
            )

        if "example" in message:
            events.append(
                self.emitter.emit(
                    EventType.REQUESTED_EXAMPLES,
                    source="chat",
                )
            )

        return events