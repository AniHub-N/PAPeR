"""
User preference source.

Loads preferences explicitly configured by the user.
"""

from __future__ import annotations

from preferences.models import PreferenceCollection
from preferences.storage.repository import PreferenceRepository


class UserPreferenceSource:
    """
    Source for user-defined preferences.

    These have the highest priority during resolution.
    """

    def __init__(
        self,
        repository: PreferenceRepository,
    ) -> None:
        self.repository = repository

    def load(self) -> PreferenceCollection:
        """
        Load user preferences.

        Returns:
            PreferenceCollection
        """
        return self.repository.load_user()