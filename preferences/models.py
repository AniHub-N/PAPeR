"""
Core models for the Preferences subsystem.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================
# ENUMS
# ============================================================


class PreferenceSource(str, Enum):
    """Where a preference originated."""

    USER = "user"
    INFERRED = "inferred"
    ENVIRONMENT = "environment"
    DEFAULT = "default"


class PreferenceCategory(str, Enum):
    """High-level preference categories."""

    COMMUNICATION = "communication"
    CODING_STYLE = "coding_style"
    ARCHITECTURE = "architecture"
    WORKFLOW = "workflow"


# ============================================================
# EVENT TYPES
# ============================================================


class EventType(str, Enum):
    """
    Events emitted by PAPeR that can be analysed to infer
    user preferences.
    """

    # ---------------- Communication ---------------- #

    REQUESTED_CONCISE_RESPONSE = "requested_concise_response"

    REQUESTED_DETAILED_RESPONSE = "requested_detailed_response"

    REQUESTED_EXAMPLES = "requested_examples"

    REQUESTED_DIAGRAM = "requested_diagram"

    # ---------------- Coding Style ---------------- #

    REMOVED_COMMENTS = "removed_comments"

    ACCEPTED_COMMENTS = "accepted_comments"

    CONVERTED_TO_SNAKE_CASE = "converted_to_snake_case"

    CONVERTED_TO_CAMEL_CASE = "converted_to_camel_case"

    ACCEPTED_TYPE_HINTS = "accepted_type_hints"

    REMOVED_TYPE_HINTS = "removed_type_hints"

    # ---------------- Workflow ---------------- #

    ACCEPTED_REFACTOR = "accepted_refactor"

    REJECTED_REFACTOR = "rejected_refactor"

    ACCEPTED_TESTS = "accepted_tests"

    REMOVED_TESTS = "removed_tests"

    # ---------------- Architecture ---------------- #

    CHOSE_FUNCTIONAL = "chose_functional"

    CHOSE_OOP = "chose_oop"

    ACCEPTED_DI = "accepted_dependency_injection"

    REJECTED_DI = "rejected_dependency_injection"


# ============================================================
# PREFERENCE ENUMS
# ============================================================


class ExplanationDepth(str, Enum):
    CONCISE = "concise"
    NORMAL = "normal"
    DETAILED = "detailed"


class ExamplePreference(str, Enum):
    NEVER = "never"
    WHEN_HELPFUL = "when_helpful"
    ALWAYS = "always"


class CommentStyle(str, Enum):
    NONE = "none"
    MINIMAL = "minimal"
    DETAILED = "detailed"


class NamingStyle(str, Enum):
    PROJECT = "project"
    PYTHONIC = "pythonic"
    CAMEL_CASE = "camel_case"
    SNAKE_CASE = "snake_case"


class ArchitectureStyle(str, Enum):
    FUNCTIONAL = "functional"
    OBJECT_ORIENTED = "object_oriented"
    HYBRID = "hybrid"


class RefactorPreference(str, Enum):
    NEVER = "never"
    ASK = "ask"
    ALWAYS = "always"


# ============================================================
# OBSERVATIONS
# ============================================================


class Observation(BaseModel):
    """
    A single observed user behaviour.
    """

    event: EventType

    source: str

    metadata: dict[str, Any] = Field(default_factory=dict)

    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# PREFERENCES
# ============================================================


class Preference(BaseModel):
    """
    A resolved preference.
    """

    key: str

    value: Any

    source: PreferenceSource

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
    )


class PreferenceCollection(BaseModel):
    """
    Collection of resolved preferences.
    """

    preferences: dict[str, Preference] = Field(
        default_factory=dict,
    )

    def get(
        self,
        key: str,
    ) -> Preference | None:
        return self.preferences.get(key)

    def set(
        self,
        preference: Preference,
    ) -> None:
        self.preferences[preference.key] = preference

    def exists(
        self,
        key: str,
    ) -> bool:
        return key in self.preferences

    def items(self):
        return self.preferences.items()

    def values(self):
        return self.preferences.values()


# ============================================================
# INFERENCE
# ============================================================


class Evidence(BaseModel):
    """
    Supporting evidence for an inferred preference.
    """

    detector: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    observations: int

    explanation: str


class PreferenceCandidate(BaseModel):
    """
    Candidate preference proposed by the inference engine.
    """

    key: str

    value: Any

    evidence: Evidence

    source: PreferenceSource = PreferenceSource.INFERRED


class PreferenceKey(str, Enum):
    COMMUNICATION_EXPLANATION_DEPTH = "communication.explanation_depth"
    COMMUNICATION_EXAMPLES = "communication.examples"

    CODING_COMMENTS = "coding_style.comments"
    CODING_NAMING = "coding_style.naming"

    ARCHITECTURE_STYLE = "architecture.style"

    WORKFLOW_REFACTOR = "workflow.refactor"