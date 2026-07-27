"""
Repository responsible for loading and saving preferences.

This is the ONLY layer allowed to read or write preference files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from preferences.models import (
    Preference,
    PreferenceCollection,
    PreferenceSource,
)


class PreferenceRepository:
    """
    Handles persistence of preference collections.

    Storage format is YAML.
    """

    def __init__(
        self,
        defaults_path: Path,
        user_path: Path,
        inferred_path: Path,
    ):
        self.defaults_path = defaults_path
        self.user_path = user_path
        self.inferred_path = inferred_path

    # ==========================================================
    # Public API
    # ==========================================================

    def load_defaults(self) -> PreferenceCollection:
        return self._load(
            self.defaults_path,
            PreferenceSource.DEFAULT,
        )

    def load_user(self) -> PreferenceCollection:
        return self._load(
            self.user_path,
            PreferenceSource.USER,
        )

    def load_inferred(self) -> PreferenceCollection:
        return self._load(
            self.inferred_path,
            PreferenceSource.INFERRED,
        )

    def save_user(
        self,
        preferences: PreferenceCollection,
    ) -> None:
        self._save(
            self.user_path,
            preferences,
        )

    def save_inferred(
        self,
        preferences: PreferenceCollection,
    ) -> None:
        self._save(
            self.inferred_path,
            preferences,
        )

    # ==========================================================
    # Internal helpers
    # ==========================================================

    def _load(
        self,
        path: Path,
        source: PreferenceSource,
    ) -> PreferenceCollection:

        if not path.exists():
            return PreferenceCollection()

        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        collection = PreferenceCollection()

        flattened = self._flatten(raw)

        for key, value in flattened.items():

            collection.set(
                Preference(
                    key=key,
                    value=value,
                    source=source,
                )
            )

        return collection

    def _save(
        self,
        path: Path,
        preferences: PreferenceCollection,
    ) -> None:

        nested = {}

        for key, pref in preferences.items():
            self._insert(
                nested,
                key,
                pref.value,
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                nested,
                f,
                sort_keys=False,
                allow_unicode=True,
            )

    # ==========================================================
    # YAML helpers
    # ==========================================================

    def _flatten(
        self,
        data: dict[str, Any],
        prefix: str = "",
    ) -> dict[str, Any]:

        result = {}

        for key, value in data.items():

            full = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                result.update(
                    self._flatten(value, full)
                )
            else:
                result[full] = value

        return result

    def _insert(
        self,
        target: dict[str, Any],
        dotted_key: str,
        value: Any,
    ) -> None:

        parts = dotted_key.split(".")

        current = target

        for part in parts[:-1]:

            current = current.setdefault(part, {})

        current[parts[-1]] = value