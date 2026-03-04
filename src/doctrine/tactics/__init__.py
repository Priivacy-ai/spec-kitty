"""
Tactics domain model - public API.

This package provides the Tactic domain entity, supporting models,
and TacticRepository for loading, querying, and saving tactic YAML files.
"""

from doctrine.artifact_kinds import ArtifactKind
from doctrine.tactics.models import (
    Tactic,
    TacticReference,
    TacticStep,
)
from doctrine.tactics.repository import TacticRepository

__all__ = [
    "ArtifactKind",
    "Tactic",
    "TacticReference",
    "TacticRepository",
    "TacticStep",
]
