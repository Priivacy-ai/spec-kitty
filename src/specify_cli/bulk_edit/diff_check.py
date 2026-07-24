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
from specify_cli.coordination.coherence import is_toolchain_generated_churn

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


_COMPILED_RULES: list[tuple[str, list[re.Pattern[str]]]] = [
    (category, [re.compile(p) for p in patterns]) for category, patterns in _PATH_RULES
]


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


def _glob_match(posix: str, pattern: str) -> bool:
    """Return ``True`` if *pattern* (``*``/``?``/``**``) matches *posix*.

    Shared by :func:`_path_matches` and :func:`_exception_for`, which both
    need "plain fnmatch, with a ``**`` recursive fallback" glob semantics —
    this is the single place that logic lives so the two call sites cannot
    drift apart.
    """
    if fnmatch(posix, pattern):
        return True
    return "**" in pattern and _fnmatch_recursive(posix, pattern)


def _move_for(path: str, omap: OccurrenceMap) -> tuple[str, str] | None:
    """Return ``(role, reason)`` when *path* participates in a declared move.

    ``role`` is ``"move-source"`` or ``"move-destination"``. A declared
    structural move (IC-10, #1815) is an explicit, reviewer-approved relocation;
    its source and destination paths are expected to change, so they are not
    subject to the ``do_not_change`` path heuristic. Source/destination paths
    are matched as path globs (``*``/``**`` supported) or as a directory
    prefix when the declared path is a directory (no glob, trailing-slash or
    bare directory form), so ``to: src/auth`` covers ``src/auth/login.py``.
    """
    posix = Path(path).as_posix()
    for move in omap.moves:
        for source in move.sources:
            if _path_matches(posix, source):
                return ("move-source", move.reason or "declared move source")
        if _path_matches(posix, move.destination):
            return ("move-destination", move.reason or "declared move destination")
    return None


def _path_matches(posix: str, declared: str) -> bool:
    """Match *posix* against a declared move path (glob or directory prefix)."""
    declared = declared.strip()
    if not declared:
        return False
    normalized = Path(declared).as_posix().rstrip("/")
    if "*" in normalized or "?" in normalized:
        return _glob_match(posix, normalized)
    if posix == normalized:
        return True
    # Directory-prefix match: ``src/auth`` covers ``src/auth/login.py``.
    return posix.startswith(f"{normalized}/")


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
        if _glob_match(posix, pattern):
            # `omap.exceptions` is declared `list[dict[str, str]]` on
            # OccurrenceMap, but mypy resolves it as `Any` when this module is
            # type-checked as a standalone narrow-file target (the
            # `specify_cli.*` / `follow_imports = "skip"` override in
            # pyproject.toml treats non-explicitly-listed sibling modules —
            # including occurrence_map.py — as untyped in that mode). An
            # annotated local (not `cast()`, which mypy flags as redundant
            # once whole-package checking resolves the real type) narrows
            # explicitly so the declared return type holds under both
            # invocation shapes.
            matched: dict[str, str] = exception
            return matched
    return None


def _fnmatch_recursive(path: str, pattern: str) -> bool:
    """fnmatch with ``**`` expanded to match any number of path components."""
    # Turn the pattern into a regex:
    #   ``**`` -> ``.*``
    #   ``*``  -> ``[^/]*``
    #   ``?``  -> ``[^/]``
    placeholder = "\x00DOUBLESTAR\x00"
    regex = (
        pattern.replace("**", placeholder)
        .replace(".", r"\.")
        .replace("*", "[^/]*")
        .replace("?", "[^/]")
        .replace(placeholder, ".*")
    )
    return re.fullmatch(regex, path) is not None


# ---------------------------------------------------------------------------
# Runtime-state gate exemption (FR-007, C-004)
# ---------------------------------------------------------------------------

# IC-07e retirement (WP15, C-010): the former named-tuple runtime-state
# allowlist mechanism is gone. Its basenames split into two genuinely
# different concerns:
#
# * ``status.events.jsonl`` / ``status.json`` / ``issue-matrix.md`` /
#   ``acceptance-matrix.json`` are COORD-partition mission artifacts —
#   toolchain-generated churn a dirty-state gate must ignore. That
#   classification already has ONE canonical owner,
#   :func:`specify_cli.coordination.coherence.is_toolchain_generated_churn`
#   (FR-012); duplicating its basenames here was exactly the "ninth list" the
#   registry (WP10) forbids, so this exemption now delegates to it instead of
#   restating the basenames.
# * ``review-cycle-*.md`` / ``notes.md`` are the running mission's own
#   human-authored review/handoff commentary — NOT toolchain churn (the owner
#   deliberately has no opinion on them: neither has a ``MissionArtifactKind``,
#   and empirically ``is_toolchain_generated_churn`` returns ``False`` for
#   both). Routing them onto the owner would either pollute its boundary with
#   a review-commentary kind it has no business knowing about, or silently
#   drop the exemption and reintroduce a false block (a C-010 regression).
#   This is a genuine, justified must-keep (plan.md L233-235) — NOT a silent
#   survivor: it is registered as an explicit ``justified-survivor`` row,
#   ``tests/architectural/tool_artifact_enrolment/registry/
#   _is_review_lifecycle_basename.md``, so it stays visible to any audit of
#   unowned filename exemptions.


def _is_review_lifecycle_basename(basename: str) -> bool:
    """Return ``True`` for the mission's own review/handoff commentary files.

    A registered survivor mechanism (registry row
    ``_is_review_lifecycle_basename.md``, ``status: justified-survivor``): these
    two patterns are bulk-edit-review-specific domain knowledge that is
    genuinely outside :func:`is_toolchain_generated_churn`'s toolchain-generated-
    write scope, so it is kept here rather than grown onto the owner — see the
    registry row for the full C-010 justification.
    """
    return basename == "notes.md" or _glob_match(basename, "review-cycle-*.md")


def _under_feature_dir(posix: str, feature_dir_rel: str) -> bool:
    """Return ``True`` if *posix* lives under *feature_dir_rel* (repo-root-relative)."""
    anchor = feature_dir_rel.strip("/")
    if not anchor:
        return False
    return posix == anchor or posix.startswith(f"{anchor}/")


def _own_bookkeeping_exemption(path: str, feature_dir_rel: str | None) -> FileAssessment | None:
    """Return an exemption verdict when *path* is the RUNNING mission's own runtime state.

    Anchored to *feature_dir_rel* — the running mission's OWN feature_dir,
    repo-root-relative — so this can only exempt paths under the mission
    currently being reviewed (C-004). ``None`` (no *feature_dir_rel*, the path
    is outside it, or the path is neither toolchain-generated churn nor a
    review-lifecycle file) means "not exempt here"; the caller falls through
    to the ordinary classifier.
    """
    if not feature_dir_rel:
        return None
    posix = Path(path).as_posix()
    if not _under_feature_dir(posix, feature_dir_rel):
        return None
    basename = Path(posix).name
    mission_slug = Path(feature_dir_rel).name or None
    if not is_toolchain_generated_churn(
        path, mission_slug=mission_slug
    ) and not _is_review_lifecycle_basename(basename):
        return None
    return FileAssessment(
        path=path,
        category=None,
        source="runtime-state",
        action=None,
        violation=False,
        reason=(
            f"'{basename}' is the mission's own runtime-state bookkeeping file "
            "(FR-007 allowlist) — exempt from occurrence classification."
        ),
    )


# ---------------------------------------------------------------------------
# Compliance check
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FileAssessment:
    """Per-file classification and verdict."""

    path: str
    category: str | None           # None => unclassified
    source: str                    # "path-heuristic" | "exception" | "move" | "runtime-state"
    action: str | None             # None => no action defined in map
    violation: bool                # True when this file blocks approval
    reason: str                    # Human-readable rationale


@dataclass(frozen=True)
class DiffCheckResult:
    """Aggregate verdict across all files in a WP diff."""

    passed: bool
    assessments: list[FileAssessment] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def assess_file(
    path: str,
    omap: OccurrenceMap,
    feature_dir_rel: str | None = None,
) -> FileAssessment:
    """Classify a single file and determine whether it violates the map.

    *feature_dir_rel* is the RUNNING mission's own ``feature_dir``, expressed
    as a repo-root-relative POSIX path. When provided, it anchors the
    runtime-state gate exemption (FR-007, C-004) so only this mission's own
    bookkeeping files are exempted — never another mission's.
    """
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

    # 2) Declared structural moves (IC-10, #1815). A move source/destination is
    #    a reviewer-approved relocation, so it is exempt from the
    #    do_not_change path heuristic.
    move = _move_for(path, omap)
    if move is not None:
        role, move_reason = move
        return FileAssessment(
            path=path,
            category=None,
            source="move",
            action="move",
            violation=False,
            reason=f"Declared structural {role}: {move_reason}",
        )

    # 3) Runtime-state gate exemption (FR-007, C-004). Fires BEFORE the
    #    path-heuristic classifier, mirroring the move/exception exemptions
    #    above — but only for the RUNNING mission's own bookkeeping files.
    runtime_state = _own_bookkeeping_exemption(path, feature_dir_rel)
    if runtime_state is not None:
        return runtime_state

    # 4) Path heuristic classification.
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

    # 5) The classified category must appear in the map.
    category_entry = omap.categories.get(category)
    if category_entry is None:
        return FileAssessment(
            path=path,
            category=category,
            source="path-heuristic",
            action=None,
            violation=True,
            reason=(
                f"File classified as '{category}' but that category is not "
                "present in the occurrence map (FR-008)."
            ),
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
        reason=(
            f"Category '{category}' action '{action}' permits modification."
        ),
    )


def check_diff_compliance(
    changed_files: list[str],
    omap: OccurrenceMap,
    feature_dir_rel: str | None = None,
) -> DiffCheckResult:
    """Assess every changed file and aggregate the verdict.

    *changed_files* is a list of repo-relative path strings obtained from
    ``git diff --name-only``. *feature_dir_rel* is the running mission's own
    ``feature_dir`` as a repo-root-relative POSIX path — see
    :func:`assess_file` for how it anchors the runtime-state exemption. The
    function is pure — no I/O — so it can be unit-tested directly.
    """
    assessments = [assess_file(p, omap, feature_dir_rel) for p in changed_files]
    violations = [a for a in assessments if a.violation]
    errors = [f"{a.path}: {a.reason}" for a in violations]

    manual_review_files = [
        a for a in assessments if a.action == "manual_review"
    ]
    warnings = [
        f"{a.path}: category '{a.category}' requires manual_review — document justification"
        for a in manual_review_files
    ]

    return DiffCheckResult(
        passed=len(violations) == 0,
        assessments=assessments,
        errors=errors,
        warnings=warnings,
    )
