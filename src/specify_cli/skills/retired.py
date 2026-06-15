"""Retired Spec Kitty skill package names."""

from __future__ import annotations

RETIRED_STANDALONE_SKILL_NAMES = frozenset({
    "spec-kitty.advise",
})

RETIRED_CANONICAL_SKILL_NAMES = frozenset({
    "debugger-debbie",
    "paula-patterns",
}) | RETIRED_STANDALONE_SKILL_NAMES
