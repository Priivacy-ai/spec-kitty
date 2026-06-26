"""Shared path constants for Spec Kitty repository layout."""

from __future__ import annotations

KITTY_SPECS_DIR = "kitty-specs"
KITTIFY_DIR = ".kittify"
WORKTREES_DIR = ".worktrees"

# Canonical filename for retrospective records — the single source of truth for
# the name "retrospective.yaml" (FR-010 / Sonar S1192).  All path-composition
# sites MUST import and use this constant; bare string literals are forbidden.
RETROSPECTIVE_FILENAME = "retrospective.yaml"

# Built-in mission-type identifiers.  These are the four canonical values that
# ship with spec-kitty; they are the same strings defined in
# ``m_3_2_0rc35_activate_builtin_mission_types._BUILTIN_MISSION_TYPES`` and
# compared at the CLI comparison sites.  All callers MUST import from here
# rather than embedding inline literals.
MISSION_TYPE_SOFTWARE_DEV = "software-dev"
MISSION_TYPE_DOCUMENTATION = "documentation"
MISSION_TYPE_RESEARCH = "research"

__all__ = [
    "KITTY_SPECS_DIR",
    "KITTIFY_DIR",
    "RETROSPECTIVE_FILENAME",
    "WORKTREES_DIR",
    "MISSION_TYPE_SOFTWARE_DEV",
    "MISSION_TYPE_DOCUMENTATION",
    "MISSION_TYPE_RESEARCH",
]
