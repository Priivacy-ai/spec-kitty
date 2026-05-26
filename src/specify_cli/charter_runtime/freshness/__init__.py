"""Charter freshness computation — public API.

Detects whether the canonical charter source, the synced bundle, and the
synthesized project DRG are mutually fresh, or whether downstream artifacts
have drifted from upstream changes.

Used by ``spec-kitty charter status --json`` to surface a ``freshness``
sub-payload (FR-005) and to surface the ``built_in_only`` synthesis state
(FR-009).

Zero LLM calls. All logic is filesystem stat + SHA-256 hash comparison +
YAML field inspection.
"""

from specify_cli.charter_runtime.freshness.computer import (
    CharterFreshness,
    FreshnessSubState,
    compute_freshness,
)

__all__ = [
    "CharterFreshness",
    "FreshnessSubState",
    "compute_freshness",
]
