"""Charter-layer activation exceptions."""

from __future__ import annotations

__all__ = ["CharterActivationError"]


class CharterActivationError(RuntimeError):
    """Raised when a requested artifact is not in the activated charter set.

    Carries the artifact identifier, the activated set, and the resolution
    command so callers can surface an actionable error to the operator.
    """
