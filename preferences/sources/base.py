from __future__ import annotations

from abc import ABC, abstractmethod

from preferences.models import PreferenceCollection


class PreferenceSource(ABC):
    """
    Base class for all preference sources.
    """

    @abstractmethod
    def load(self) -> PreferenceCollection:
        """Load preferences from the source."""
        raise NotImplementedError