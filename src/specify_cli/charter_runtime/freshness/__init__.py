"""Charter freshness computation — public API.

Detects whether the canonical charter source, the synced bundle, and the
synthesized project DRG are mutually fresh, or whether downstream artifacts
have drifted from upstream changes.

Used by ``spec-kitty charter status --json`` to surface a ``freshness``
sub-payload (FR-005) and to surface the ``built_in_only`` synthesis state
(FR-009); also asked by ``spec-kitty next``'s charter preflight
(``charter_runtime.preflight.runner``) on every invocation.

Zero LLM calls. All logic is filesystem stat + SHA-256 hash comparison +
YAML field inspection.

``compute_freshness`` (WP02) is a content-keyed cache seam over
``computer.compute_freshness``: on a cache hit it returns the prior verdict
without re-parsing ``charter.yaml`` / the synthesis manifest; on a miss it
recomputes and persists. The cache is fail-closed and content-only — see
``freshness.cache``'s module docstring for the full contract. Callers get
this transparently; the raw, uncached computation stays available at
``specify_cli.charter_runtime.freshness.computer.compute_freshness``.
"""

from specify_cli.charter_runtime.freshness.cache import (
    compute_freshness_cached as compute_freshness,
)
from specify_cli.charter_runtime.freshness.computer import (
    CharterFreshness,
    FreshnessSubState,
)

__all__ = [
    "CharterFreshness",
    "FreshnessSubState",
    "compute_freshness",
]
