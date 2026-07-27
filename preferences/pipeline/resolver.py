"""
Preference resolution pipeline.

Combines preferences from multiple sources into a single resolved collection.
"""

from __future__ import annotations

from preferences.models import PreferenceCollection


class PreferenceResolver:
    """
    Resolves preferences according to source priority.

    Priority (highest → lowest):

        User
        Environment
        Inferred
        Defaults
    """

    def resolve(
        self,
        *,
        defaults: PreferenceCollection,
        inferred: PreferenceCollection,
        environment: PreferenceCollection,
        user: PreferenceCollection,
    ) -> PreferenceCollection:
        """
        Merge all preference collections into a single resolved collection.
        """

        resolved = PreferenceCollection()

        # Lowest priority first
        self._merge(resolved, defaults)
        self._merge(resolved, inferred)
        self._merge(resolved, environment)
        self._merge(resolved, user)

        return resolved

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    @staticmethod
    def _merge(
        target: PreferenceCollection,
        source: PreferenceCollection,
    ) -> None:
        """
        Copy all preferences from source into target.

        Existing keys are overwritten because the caller
        guarantees merge order.
        """

        for key, preference in source.items():
            target.set(preference)