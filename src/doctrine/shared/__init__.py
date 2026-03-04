"""Shared utilities for the doctrine package.

Provides cross-cutting concerns used by multiple artifact subpackages:

- :class:`~doctrine.shared.schema_utils.SchemaUtilities` — cached JSON Schema loading
- :exc:`~doctrine.shared.exceptions.DoctrineArtifactLoadError` — load failure signal
- :exc:`~doctrine.shared.exceptions.DoctrineResolutionCycleError` — cycle detection signal
"""

from .exceptions import DoctrineArtifactLoadError, DoctrineResolutionCycleError
from .schema_utils import SchemaUtilities

__all__ = [
    "DoctrineArtifactLoadError",
    "DoctrineResolutionCycleError",
    "SchemaUtilities",
]
