from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from preferences.models import EventType


class Event(BaseModel):
    """
    Raw event emitted by PAPeR.
    """

    event: EventType

    source: str

    metadata: dict[str, Any] = Field(default_factory=dict)

    timestamp: datetime = Field(default_factory=datetime.utcnow)