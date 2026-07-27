"""
Preference loading pipeline.

Responsible for collecting preferences from all configured sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from preferences.models import PreferenceCollection
from preferences.sources.base import PreferenceSource


@dataclass(slots=True)
class LoadedPreferences:
    """
    Raw preferences loaded from each source.

    These have NOT been resolved.
    """

    defaults: PreferenceCollection
    user: PreferenceCollection
    inferred: PreferenceCollection
    environment: PreferenceCollection


class PreferenceLoader:
    """
    Loads preferences from every configured source.
    """

    def __init__(
        self,
        *,
        defaults: PreferenceSource,
        user: PreferenceSource,
        inferred: PreferenceSource,
        environment: PreferenceSource,
    ) -> None:

        self.defaults = defaults
        self.user = user
        self.inferred = inferred
        self.environment = environment

    def load(self) -> LoadedPreferences:
        """
        Load preferences from all sources.

        Returns
        -------
        LoadedPreferences
            Unresolved preferences grouped by source.
        """

        return LoadedPreferences(
            defaults=self.defaults.load(),
            user=self.user.load(),
            inferred=self.inferred.load(),
            environment=self.environment.load(),
        )