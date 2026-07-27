"""
Builds the final resolved preference context.

This is the object consumed by the rest of PAPeR.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from preferences.models import PreferenceCollection


# ============================================================
# Context Models
# ============================================================


class CommunicationPreferences(BaseModel):
    explanation_depth: str = "normal"
    examples: str = "when_helpful"


class CodingStylePreferences(BaseModel):
    comments: str = "minimal"
    naming: str = "project"


class ArchitecturePreferences(BaseModel):
    style: str = "hybrid"


class WorkflowPreferences(BaseModel):
    refactor: str = "ask"


class ResolvedPreferences(BaseModel):
    communication: CommunicationPreferences = Field(
        default_factory=CommunicationPreferences
    )

    coding_style: CodingStylePreferences = Field(
        default_factory=CodingStylePreferences
    )

    architecture: ArchitecturePreferences = Field(
        default_factory=ArchitecturePreferences
    )

    workflow: WorkflowPreferences = Field(
        default_factory=WorkflowPreferences
    )


# ============================================================
# Builder
# ============================================================


class PreferenceBuilder:
    """
    Converts a PreferenceCollection into a typed preference object.
    """

    def build(
        self,
        preferences: PreferenceCollection,
    ) -> ResolvedPreferences:

        resolved = ResolvedPreferences()

        self._populate(
            model=resolved,
            preferences=preferences,
        )

        return resolved

    # =========================================================
    # Internal Helpers
    # =========================================================

    def _populate(
        self,
        model: BaseModel,
        preferences: PreferenceCollection,
        prefix: str = "",
    ) -> None:
        """
        Recursively populate a Pydantic model from preferences.

        Example:

            communication.explanation_depth

        becomes

            resolved.communication.explanation_depth
        """

        for field_name in model.model_fields:

            value = getattr(model, field_name)

            dotted_key = (
                f"{prefix}.{field_name}"
                if prefix
                else field_name
            )

            # Nested Pydantic model
            if isinstance(value, BaseModel):
                self._populate(
                    model=value,
                    preferences=preferences,
                    prefix=dotted_key,
                )
                continue

            preference = preferences.get(dotted_key)

            if preference is not None:
                setattr(
                    model,
                    field_name,
                    preference.value,
                )