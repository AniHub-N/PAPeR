"""
Base interface for all preference detectors.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from preferences.models import (
    Observation,
    PreferenceCandidate,
)


class BasePreferenceDetector(ABC):
    """
    Base class for all preference detectors.

    A detector analyses a sequence of observations and proposes
    one or more preference candidates.

    It never writes preferences directly.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Human-readable detector name.
        """
        ...

    @abstractmethod
    def detect(
        self,
        observations: list[Observation],
    ) -> list[PreferenceCandidate]:
        """
        Analyse observations and return candidate preferences.

        Parameters
        ----------
        observations
            Sequence of user observations.

        Returns
        -------
        list[PreferenceCandidate]
            Proposed preferences. May be empty.
        """
        ...