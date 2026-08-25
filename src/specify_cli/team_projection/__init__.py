"""The team-projection package's surviving seam: the per-WP team-field allowlist.

The D1 publish pipeline (``team-index.json``, per-mission
``team-snapshot.json``, opt-in public variants, attestation manifest) and the
``spec-kitty team-projection publish`` command were deleted: consumers read the
tracked repository directly at an exact pushed commit instead of a published
gitignored projection. What remains — and what Team Kitty ports when rendering
WP detail from committed state — is :data:`.mission_view.TEAM_WP_ALLOWED_FIELDS`
and its closed-allowlist semantics.
"""

from __future__ import annotations

from .mission_view import (
    TEAM_WP_ALLOWED_FIELDS,
    UnknownWPStateFieldError,
)

__all__ = [
    "TEAM_WP_ALLOWED_FIELDS",
    "UnknownWPStateFieldError",
]
