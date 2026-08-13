"""Raw-text duplicate-key detector + repair planner for mission artifacts.

The canonical frontmatter boundary (:mod:`specify_cli.frontmatter`) fails
**closed** on duplicate keys — ruamel raises ``DuplicateKeyError`` before a
caller ever sees the mapping (``frontmatter.py:83,122-127``). That is correct
for the read path but means the boundary CANNOT be used to *detect* the legacy
dual-key ``review_feedback`` artifacts (#3372): loading them raises. This module
is the net-new RAW-TEXT scanner FR-008 needs — it inspects the frontmatter block
as lines, never parsing it through the failing boundary, so a malformed dual-key
artifact is discoverable.

Repair policy is **keep-last-non-empty**: the legacy shape is
``review_feedback: ''`` followed by a real path, so the last non-empty value is
the recorded state and the empty duplicate is the noise. Repair is
NON-DESTRUCTIVE (the recorded value is preserved — NFR-002) and the planner
REFUSES (raising :class:`DuplicateKeyRepairError`) any shape it cannot heal to
valid YAML, so the batch-atomic caller aborts the whole run rather than writing
a half-repaired corpus (NFR-004).

This module is diagnostic + planning only: it never writes to disk. The mutating
half reuses the ADR 2026-05-10-1 repair framework in
:mod:`specify_cli.migration.mission_state`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

# Opening/closing frontmatter fence. Mirrors the ``content.startswith("---")``
# opening probe and the ``line.strip() == "---"`` closing probe used by the
# canonical boundary (``frontmatter.py``) so this scanner and the read path
# agree on where the frontmatter block begins and ends.
_FRONTMATTER_FENCE = "---"

# A top-level (column-0) ``key:`` line. Leading-whitespace keys are nested and
# are deliberately NOT scanned: removing a nested duplicate would require
# block-aware surgery this keep-last-non-empty planner does not attempt.
_TOP_LEVEL_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):(.*)$")

# Scalar values treated as "empty" for the keep-last-non-empty policy.
_EMPTY_SCALARS = frozenset({"", "''", '""'})


class DuplicateKeyRepairError(Exception):
    """Raised when a duplicate-key artifact cannot be safely repaired.

    Propagated by the batch caller so an un-repairable artifact aborts the
    entire repair run (NFR-004) instead of leaving a half-repaired corpus.
    """


@dataclass(frozen=True)
class KeyOccurrence:
    """One column-0 occurrence of a frontmatter key."""

    line_index: int  # 0-based index into the file's ``split("\n")`` lines
    value: str  # stripped inline scalar value ("" when the value is off-line)
    is_empty: bool


@dataclass(frozen=True)
class DuplicateKeyFinding:
    """A single artifact carrying one duplicated top-level frontmatter key."""

    path: Path
    key: str
    line_numbers: tuple[int, ...]  # 1-based line numbers of every occurrence


@dataclass(frozen=True)
class ArtifactRepairPlan:
    """A validated, non-destructive repair for one artifact (batch-atomic input)."""

    path: Path
    original_text: str
    repaired_text: str
    removed_line_numbers: tuple[int, ...]  # 1-based
    keys: tuple[str, ...]


def _frontmatter_closing_index(lines: list[str]) -> int | None:
    """Return the index of the closing fence, or ``None`` when absent.

    Matches the canonical boundary: the document must *open* with ``---`` and
    the closing fence is the first subsequent line that is exactly ``---``.
    """
    if not lines or not lines[0].startswith(_FRONTMATTER_FENCE):
        return None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FRONTMATTER_FENCE:
            return idx
    return None


def _scan_occurrences(lines: list[str], closing_idx: int) -> dict[str, list[KeyOccurrence]]:
    """Collect every column-0 ``key:`` occurrence inside the frontmatter block."""
    seen: dict[str, list[KeyOccurrence]] = {}
    for idx in range(1, closing_idx):
        match = _TOP_LEVEL_KEY_RE.match(lines[idx])
        if match is None:
            continue
        key = match.group(1)
        value = match.group(2).strip()
        seen.setdefault(key, []).append(
            KeyOccurrence(line_index=idx, value=value, is_empty=value in _EMPTY_SCALARS)
        )
    return seen


def _duplicates(seen: dict[str, list[KeyOccurrence]]) -> dict[str, list[KeyOccurrence]]:
    """Filter to keys that occur more than once (dict insertion order preserved)."""
    return {key: occurrences for key, occurrences in seen.items() if len(occurrences) > 1}


def find_duplicate_keys_in_text(text: str) -> dict[str, list[KeyOccurrence]]:
    """Return duplicated top-level frontmatter keys for one artifact's *text*.

    Empty mapping when the file has no frontmatter or no duplicate keys.
    """
    lines = text.split("\n")
    closing_idx = _frontmatter_closing_index(lines)
    if closing_idx is None:
        return {}
    return _duplicates(_scan_occurrences(lines, closing_idx))


def scan_artifact(path: Path) -> list[DuplicateKeyFinding]:
    """Return one :class:`DuplicateKeyFinding` per duplicated key in *path*."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    duplicates = find_duplicate_keys_in_text(text)
    return [
        DuplicateKeyFinding(
            path=path,
            key=key,
            line_numbers=tuple(occurrence.line_index + 1 for occurrence in occurrences),
        )
        for key, occurrences in sorted(duplicates.items())
    ]


def detect_duplicate_key_artifacts(scan_dir: Path) -> list[DuplicateKeyFinding]:
    """Scan ``scan_dir/**/*.md`` and return every dual-key artifact finding.

    Deterministic: findings are ordered by path then key.
    """
    if not scan_dir.exists():
        return []
    findings: list[DuplicateKeyFinding] = []
    for path in sorted(scan_dir.glob("**/*.md")):
        if not path.is_file():
            continue
        findings.extend(scan_artifact(path))
    return findings


def _choose_survivor(occurrences: list[KeyOccurrence]) -> KeyOccurrence:
    """Keep-last-non-empty: the last non-empty occurrence, else the last one."""
    non_empty = [occurrence for occurrence in occurrences if not occurrence.is_empty]
    return non_empty[-1] if non_empty else occurrences[-1]


def _removal_is_safe(lines: list[str], idx: int, closing_idx: int) -> bool:
    """True when the key line at *idx* can be dropped without orphaning content.

    A line with an inline scalar value is self-contained and always safe. A key
    with an *empty* inline value may open a nested block (its value hangs on the
    following indented / list lines); dropping such a line would orphan that
    block, so it is safe to remove only when the next frontmatter line is itself
    a top-level key (nothing hangs beneath it) or the block has ended.
    """
    match = _TOP_LEVEL_KEY_RE.match(lines[idx])
    if match is None:
        return False
    if match.group(2).strip():
        return True
    next_idx = idx + 1
    if next_idx >= closing_idx:
        return True
    return _TOP_LEVEL_KEY_RE.match(lines[next_idx]) is not None


def _assert_repaired_frontmatter_valid(
    path: Path, repaired_lines: list[str], original_closing_idx: int, removed: set[int]
) -> None:
    """Re-parse the repaired frontmatter with duplicate keys forbidden.

    Guarantees the planned output is valid YAML *and* free of residual duplicate
    keys before the batch caller writes anything. Raises
    :class:`DuplicateKeyRepairError` otherwise (aborting the whole batch).
    """
    new_closing_idx = original_closing_idx - len(removed)
    body = "\n".join(repaired_lines[1:new_closing_idx])
    yaml = YAML()
    yaml.allow_duplicate_keys = False
    try:
        yaml.load(body)
    except Exception as exc:  # ruamel raises subclasses of YAMLError / DuplicateKeyError
        raise DuplicateKeyRepairError(
            f"{path}: repaired frontmatter is still invalid YAML: {exc}"
        ) from exc


def plan_artifact_repair(path: Path, text: str) -> ArtifactRepairPlan | None:
    """Plan a non-destructive, validated repair for one artifact.

    Returns ``None`` when the artifact has no frontmatter or no duplicate keys.
    Raises :class:`DuplicateKeyRepairError` when the artifact cannot be safely
    healed (a non-scalar duplicate occurrence, or a repaired body that still
    fails to parse) — the signal the batch caller uses to abort all-or-nothing.
    """
    lines = text.split("\n")
    closing_idx = _frontmatter_closing_index(lines)
    if closing_idx is None:
        return None
    duplicates = _duplicates(_scan_occurrences(lines, closing_idx))
    if not duplicates:
        return None

    remove: set[int] = set()
    for key, occurrences in duplicates.items():
        survivor = _choose_survivor(occurrences)
        for occurrence in occurrences:
            if occurrence.line_index == survivor.line_index:
                continue
            if not _removal_is_safe(lines, occurrence.line_index, closing_idx):
                raise DuplicateKeyRepairError(
                    f"{path}: cannot safely repair duplicate key {key!r} at line "
                    f"{occurrence.line_index + 1} (non-scalar occurrence)."
                )
            remove.add(occurrence.line_index)

    repaired_lines = [line for index, line in enumerate(lines) if index not in remove]
    _assert_repaired_frontmatter_valid(path, repaired_lines, closing_idx, remove)
    return ArtifactRepairPlan(
        path=path,
        original_text=text,
        repaired_text="\n".join(repaired_lines),
        removed_line_numbers=tuple(sorted(index + 1 for index in remove)),
        keys=tuple(sorted(duplicates)),
    )


# ``__all__`` lists only the cross-module surface (imported by
# ``migration.mission_state`` + ``status.doctor`` + the ``_mission_state_doctor``
# CLI). ``find_duplicate_keys_in_text`` / ``scan_artifact`` / ``KeyOccurrence``
# are module-internal helpers (and test seams); leaving them out of ``__all__``
# keeps the symbol-level dead-code gate green while they remain importable.
__all__ = [
    "ArtifactRepairPlan",
    "DuplicateKeyFinding",
    "DuplicateKeyRepairError",
    "detect_duplicate_key_artifacts",
    "plan_artifact_repair",
]
