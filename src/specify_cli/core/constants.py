"""Shared path constants for Spec Kitty repository layout."""

from __future__ import annotations

KITTY_SPECS_DIR = "kitty-specs"
KITTIFY_DIR = ".kittify"
WORKTREES_DIR = ".worktrees"

# Canonical filename for retrospective records — the single source of truth for
# the name "retrospective.yaml" (FR-010 / Sonar S1192).  All path-composition
# sites MUST import and use this constant; bare string literals are forbidden.
RETROSPECTIVE_FILENAME = "retrospective.yaml"

# Canonical filename for the repo-global charter-lint decay report, written to
# ``<repo_root>/.kittify/lint-report.json`` by the lint engine and read back by
# the dashboard tile and the dossier stager.  All path-composition sites MUST
# use ``core.paths.lint_report_path`` / this constant; bare literals are
# forbidden (#2628 SSOT fold).
LINT_REPORT_FILENAME = "lint-report.json"

# Named scalar aliases for individual built-in mission-type identifiers, used at
# the CLI comparison sites.  The canonical *roster* (the full built-in set) is
# ``doctrine.missions.mission_type_repository.builtin_mission_type_ids`` (#2669) —
# these are per-type named constants for readability, not a competing roster.
# All callers MUST import a name from here rather than embedding inline literals.
MISSION_TYPE_SOFTWARE_DEV = "software-dev"
MISSION_TYPE_DOCUMENTATION = "documentation"
MISSION_TYPE_RESEARCH = "research"

__all__ = [
    "KITTY_SPECS_DIR",
    "KITTIFY_DIR",
    "RETROSPECTIVE_FILENAME",
    "LINT_REPORT_FILENAME",
    "WORKTREES_DIR",
    "MISSION_TYPE_SOFTWARE_DEV",
    "MISSION_TYPE_DOCUMENTATION",
    "MISSION_TYPE_RESEARCH",
]
