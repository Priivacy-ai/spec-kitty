"""Dirty-path classifier for review handoff.

Partitions ``git status --porcelain`` file paths into two buckets:

- **blocking**: files owned by the current WP that must be committed before
  moving to ``for_review``.
- **benign**: files that change for legitimate concurrent-agent reasons
  (status artifacts, other WPs' task files, generated metadata) and should
  NOT block the review handoff.

Usage::

    from specify_cli.review.dirty_classifier import classify_dirty_paths

    blocking, benign = classify_dirty_paths(
        dirty_paths=["src/foo.py", "kitty-specs/066-foo/status.events.jsonl"],
        wp_id="WP01",
        mission_slug="066-foo",
    )
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Benign filename / suffix patterns
# ---------------------------------------------------------------------------
# A path is benign if its basename (or any component) matches one of these
# exact names, OR if the path starts with the given prefix.
_BENIGN_EXACT_NAMES: frozenset[str] = frozenset(
    [
        "status.events.jsonl",
        "status.json",
        "meta.json",
        "lanes.json",
    ]
)

_BENIGN_PATH_PREFIXES: tuple[str, ...] = (
    ".kittify/",
    ".kittify" + "\\",  # Windows paths — defensive
)

# Matches `kitty-specs/<any-mission>/tasks/WP<digits>-<rest>.md`
# Capture group 1 is the WP identifier (e.g. "WP01", "WP10").
_WP_TASK_PATTERN: re.Pattern[str] = re.compile(
    r"kitty-specs/[^/]+/tasks/(WP\d+)-.+\.md$"
)

# Also match tasks.md at the root of a mission directory (benign — auto-updated
# by mark-status and committed atomically).
_ROOT_TASKS_MD_PATTERN: re.Pattern[str] = re.compile(
    r"kitty-specs/[^/]+/tasks\.md$"
)


def _is_benign(path: str, wp_id: str) -> bool:
    """Return True if *path* is a benign (non-blocking) dirty file.

    A path is benign when it satisfies any of the following:

    1. Its basename is a known status/metadata artifact.
    2. It lives under ``.kittify/``.
    3. It matches the pattern for *another* WP's task file.
    4. It matches the root-level ``tasks.md`` summary file.
    """
    # Normalise separators for cross-platform safety
    normalised = path.replace("\\", "/").strip()
    basename = normalised.rsplit("/", 1)[-1] if "/" in normalised else normalised

    # 1. Known status/metadata artifact filenames
    if basename in _BENIGN_EXACT_NAMES:
        return True

    # 2. .kittify/ prefix
    if normalised.startswith(".kittify/") or normalised == ".kittify":
        return True

    # 3. Another WP's task file
    match = _WP_TASK_PATTERN.search(normalised)
    if match:
        # Benign iff the WP in the filename differs from the current WP
        return match.group(1) != wp_id

    # 4. Root-level tasks.md (auto-updated by mark-status)
    if _ROOT_TASKS_MD_PATTERN.search(normalised):
        return True

    return False


def classify_dirty_paths(
    dirty_paths: list[str],
    wp_id: str,
    mission_slug: str,
    wp_slug: str | None = None,
) -> tuple[list[str], list[str]]:
    """Classify dirty paths as blocking or benign.

    Args:
        dirty_paths: Paths from ``git status --porcelain`` (the file-path
            portion, **after** stripping the two-character status prefix).
        wp_id: Current WP ID (e.g. ``"WP01"``).
        mission_slug: Mission slug (e.g. ``"066-review-loop-stabilization"``).
        wp_slug: Optional WP slug for task-file matching
            (e.g. ``"WP01-persisted-review-artifact-model"``).  When
            provided, a path that matches ``tasks/{wp_slug}.md`` is treated as
            blocking.  Not strictly necessary because the regex already handles
            the ``WP<id>`` prefix, but accepted for API completeness.

    Returns:
        A tuple ``(blocking, benign)`` — two lists of path strings.  Each
        input path appears in exactly one of the two lists.
    """
    blocking: list[str] = []
    benign: list[str] = []

    for path in dirty_paths:
        if not path:
            continue
        if _is_benign(path, wp_id):
            benign.append(path)
        else:
            blocking.append(path)

    return blocking, benign
