from __future__ import annotations

from collections.abc import Iterable

from preferences.inference.service import PreferenceInferenceService
from preferences.pipeline.builder import PreferenceBuilder
from preferences.pipeline.loader import PreferenceLoader
from preferences.pipeline.resolver import PreferenceResolver
from preferences.storage.repository import PreferenceRepository


class PreferenceManager:
    """
    High-level interface for the Preferences subsystem.

    This is the only class the rest of PAPeR should interact with.
    """

    def __init__(
        self,
        loader: PreferenceLoader,
        resolver: PreferenceResolver,
        builder: PreferenceBuilder,
        repository: PreferenceRepository,
        inference: PreferenceInferenceService,
    ) -> None:

        self.loader = loader
        self.resolver = resolver
        self.builder = builder

        self.repository = repository
        self.inference = inference

    def build(self):
        """
        Build the fully resolved preference object.
        """

        loaded = self.loader.load()

        resolved = self.resolver.resolve(
            defaults=loaded.defaults,
            inferred=loaded.inferred,
            environment=loaded.environment,
            user=loaded.user,
        )

        return self.builder.build(resolved)

    def learn(
        self,
        events: Iterable[dict],
    ) -> None:
        """
        Learn user preferences from interaction events.
        """

        inferred = self.repository.load_inferred()

        updated = self.inference.learn(
            events,
            inferred,
        )

        self.repository.save_inferred(updated)