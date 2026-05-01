"""Diff-aware review compliance for bulk-edit occurrence maps.

Implements FR-007 and FR-008: when a mission is marked ``change_mode: bulk_edit``
and a work package reaches review, the review gate inspects the WP's diff and
rejects it when

  * any changed file maps (by path heuristic) to a category whose action is
    ``do_not_change``, unless an explicit exception grants a different action
    for that file, **or**

  * any changed file cannot be classified against the occurrence map's
    categories at all (unclassified occurrence surface touched).

Classification is deliberately path-based, not AST-based. Spec constraint
C-001 excludes language-aware occurrence classification. Path heuristics
are imperfect — a ``.py`` file can carry code symbols, import paths, path
literals, and log labels all at once — so we classify each file to a single
primary category based on its filesystem location and file extension. This
is sufficient to catch the most common silent-breakage class: whole-file
modifications inside a surface marked ``do_not_change`` (serialized-key
YAMLs, CLI command modules, test fixtures, user-facing docs, etc.).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from specify_cli.bulk_edit.occurrence_map import OccurrenceMap

# ---------------------------------------------------------------------------
# Path-to-category heuristics
# ---------------------------------------------------------------------------

# Ordered list — first match wins. Patterns are compiled against the POSIX
# path string (forward slashes, relative to the repo root). More specific
# patterns come first so that, e.g., ``tests/cli/commands/foo.py`` classifies
# as ``tests_fixtures`` rather than ``cli_commands``.
_PATH_RULES: list[tuple[str, list[str]]] = [
    (
        "tests_fixtures",
        [
            r"(^|/)tests?/",
            r"(^|/)testing/",
            r"(^|/)fixtures?/",
            r"(^|/)__snapshots__/",
            r"(^|/)__tests__/",
            r"(^|/)conftest\.py$",
            r"_test\.py$",
            r"\.test\.(ts|tsx|js|jsx)$",
            r"(^|/)test_[^/]+\.py$",
        ],
    ),
    (
        "cli_commands",
        [
            r"(^|/)cli/commands/",
            r"(^|/)commands/[^/]+\.py$",
            r"(^|/)bin/[^/]+$",
        ],
    ),
    (
        "user_facing_strings",
        [
            r"\.md$",
            r"(^|/)docs?/",
            r"(^|/)README(\.[^/]+)?$",
            r"(^|/)CHANGELOG(\.[^/]+)?$",
            r"\.rst$",
            r"\.txt$",
            r"(^|/)LICENSE(\.[^/]+)?$",
        ],
    ),
    (
        "serialized_keys",
        [
            r"\.ya?ml$",
            r"\.json$",
            r"\.toml$",
            r"\.ini$",
            r"\.cfg$",
        ],
    ),
    (
        "code_symbols",
        [
            r"\.py$",
            r"\.pyi$",
            r"\.ts$",
            r"\.tsx$",
            r"\.js$",
            r"\.jsx$",
            r"\.mjs$",
            r"\.cjs$",
            r"\.go$",
            r"\.rs$",
            r"\.java$",
            r"\.rb$",
            r"\.kt$",
            r"\.swift$",
            r"\.c$",
            r"\.cc$",
            r"\.cpp$",
            r"\.h$",
            r"\.hpp$",
        ],
    ),
]


_COMPILED_RULES: list[tuple[str, list[re.Pattern[str]]]] = [(category, [re.compile(p) for p in patterns]) for category, patterns in _PATH_RULES]


def classify_path(path: str) -> str | None:
    """Return the primary occurrence category for *path*, or ``None``.

    *path* may be absolute or relative; only the normalised POSIX form is
    used for matching. Returns ``None`` when no pattern matches — such files
    are treated as *unclassified* and block review per FR-008.
    """
    posix = Path(path).as_posix()
    for category, patterns in _COMPILED_RULES:
        for pattern in patterns:
            if pattern.search(posix):
                return category
    return None


# ---------------------------------------------------------------------------
# Exception handling
# ---------------------------------------------------------------------------


def _exception_for(path: str, omap: OccurrenceMap) -> dict[str, str] | None:
    """Return the first exception whose glob matches *path*, if any."""
    posix = Path(path).as_posix()
    for exception in omap.exceptions:
        pattern = exception.get("path", "")
        if not pattern:
            continue
        # Support both plain glob (``CHANGELOG.md``) and directory-style
        # globs (``src/**/*.py``). fnmatch understands ``*`` and ``?`` but
        # not ``**``, so we also try a recursive-glob fallback when the
        # pattern contains ``**``.
        if fnmatch(posix, pattern):
            return exception
        if "**" in pattern and _fnmatch_recursive(posix, pattern):
            return exception
    return None


def _fnmatch_recursive(path: str, pattern: str) -> bool:
    """fnmatch with ``**`` expanded to match any number of path components."""
    # Turn the pattern into a regex:
    #   ``**`` -> ``.*``
    #   ``*``  -> ``[^/]*``
    #   ``?``  -> ``[^/]``
    placeholder = "\x00DOUBLESTAR\x00"
    regex = pattern.replace("**", placeholder).replace(".", r"\.").replace("*", "[^/]*").replace("?", "[^/]").replace(placeholder, ".*")
    return re.fullmatch(regex, path) is not None


# ---------------------------------------------------------------------------
# Compliance check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileAssessment:
    """Per-file classification and verdict."""

    path: str
    category: str | None  # None => unclassified
    source: str  # "path-heuristic" | "exception"
    action: str | None  # None => no action defined in map
    violation: bool  # True when this file blocks approval
    reason: str  # Human-readable rationale


@dataclass(frozen=True)
class DiffCheckResult:
    """Aggregate verdict across all files in a WP diff."""

    passed: bool
    assessments: list[FileAssessment] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def assess_file(path: str, omap: OccurrenceMap) -> FileAssessment:
    """Classify a single file and determine whether it violates the map."""
    # 1) Exceptions take precedence over path heuristics.
    exception = _exception_for(path, omap)
    if exception is not None:
        action = exception.get("action")
        reason = exception.get("reason", "matched exception")
        if action == "do_not_change":
            return FileAssessment(
                path=path,
                category=None,
                source="exception",
                action=action,
                violation=True,
                reason=f"Exception '{exception.get('path', '?')}' marks this file do_not_change: {reason}",
            )
        return FileAssessment(
            path=path,
            category=None,
            source="exception",
            action=action,
            violation=False,
            reason=f"Exception '{exception.get('path', '?')}' allows {action!r}: {reason}",
        )

    # 2) Path heuristic classification.
    category = classify_path(path)
    if category is None:
        return FileAssessment(
            path=path,
            category=None,
            source="path-heuristic",
            action=None,
            violation=True,
            reason=(
                "File path does not match any standard occurrence category "
                "(FR-008: unclassified surface touched). Add an exception "
                "in occurrence_map.yaml if this file is expected."
            ),
        )

    # 3) The classified category must appear in the map.
    category_entry = omap.categories.get(category)
    if category_entry is None:
        return FileAssessment(
            path=path,
            category=category,
            source="path-heuristic",
            action=None,
            violation=True,
            reason=(f"File classified as '{category}' but that category is not present in the occurrence map (FR-008)."),
        )

    action = category_entry.get("action")
    if action == "do_not_change":
        return FileAssessment(
            path=path,
            category=category,
            source="path-heuristic",
            action=action,
            violation=True,
            reason=(
                f"File classified as '{category}' which is marked "
                f"do_not_change (FR-007). Update the occurrence map or add "
                "an exception if this file is legitimately out of scope."
            ),
        )

    return FileAssessment(
        path=path,
        category=category,
        source="path-heuristic",
        action=action,
        violation=False,
        reason=(f"Category '{category}' action '{action}' permits modification."),
    )


def check_diff_compliance(
    changed_files: list[str],
    omap: OccurrenceMap,
) -> DiffCheckResult:
    """Assess every changed file and aggregate the verdict.

    *changed_files* is a list of repo-relative path strings obtained from
    ``git diff --name-only``. The function is pure — no I/O — so it can be
    unit-tested directly.
    """
    assessments = [assess_file(p, omap) for p in changed_files]
    violations = [a for a in assessments if a.violation]
    errors = [f"{a.path}: {a.reason}" for a in violations]

    manual_review_files = [a for a in assessments if a.action == "manual_review"]
    warnings = [f"{a.path}: category '{a.category}' requires manual_review — document justification" for a in manual_review_files]

    return DiffCheckResult(
        passed=len(violations) == 0,
        assessments=assessments,
        errors=errors,
        warnings=warnings,
    )
