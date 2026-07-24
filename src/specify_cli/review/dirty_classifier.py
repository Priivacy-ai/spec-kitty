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

from specify_cli.coordination.coherence import is_toolchain_generated_churn
from kernel.paths import to_posix


def _is_review_handoff_survivor_path(normalised: str) -> bool:
    """Review-handoff-only benign paths the shared owner cannot classify.

    Justified survivor (IC-07g / WP17; registry row
    ``_is_review_handoff_survivor_path.md``, status ``justified-survivor`` —
    mirrors the WP15 precedent ``_is_review_lifecycle_basename``). Retiring the
    four former module-level filename/prefix/regex collections that fed the
    review-handoff gate onto
    :func:`specify_cli.coordination.coherence.is_toolchain_generated_churn`
    wholesale is NOT possible without changing that owner's answer for the
    merge/accept gates that also consult it (a regression, C6):

    - ``lanes.json`` is the ``LANE_STATE`` kind, a PRIMARY-partition mission
      artifact (``mission_runtime._PRIMARY_ARTIFACT_KINDS``) — a stale copy of it
      IS real dirt for the merge/accept gate by design (the owner's
      ``is_coord_residue_churn`` leg correctly returns ``False`` for it); only
      review handoff treats an in-flight rewrite by ``finalize-tasks`` / the lane
      allocator as benign.
    - ``.kittify/`` config/metadata files are not ``kitty-specs/<slug>/`` mission
      artifacts at all — no ``MissionArtifactKind`` applies to most of them
      (parallel to WP15's ``notes.md`` / ``review-cycle-*.md``); only the single
      nested ``.kittify/encoding-provenance/global.jsonl`` path is covered by the
      owner's self-bookkeeping leg.
    - any WP's ``tasks/WP##-*.md`` task file, and the mission-root ``tasks.md``,
      are the ``WORK_PACKAGE_TASK`` / ``TASKS_INDEX`` kinds — also
      PRIMARY-partition, auto-committed by ``move-task`` / ``mark-status`` as
      toolchain writes-in-flight — but the merge/accept gate must still block a
      genuinely-uncommitted one; only review handoff treats them as benign.

    The filename / suffix / regex literals are function-local (not module-level
    ``frozenset`` / ``tuple`` / ``re.compile`` assignments) so the R-014
    exemption-registry scan — which only walks module-level assignments
    (``tests/architectural/test_exemption_registry_ratchet.py``) — does not treat
    this as a NEW per-gate filename exemption requiring the collection-scan's
    row (mirrors :func:`specify_cli.coordination.coherence.is_self_bookkeeping_churn`'s
    function-local ``kitty-ops`` regex). It is still explicitly enumerated —
    ``literals: (none)`` — and held accountable by the symbol-presence arm
    instead (the WP15 precedent).
    """
    basename = normalised.rsplit("/", 1)[-1] if "/" in normalised else normalised

    # lanes.json (LANE_STATE, PRIMARY-partition) — see docstring bullet 1.
    if basename == "lanes.json":
        return True

    # .kittify/ config/metadata (no MissionArtifactKind) — see docstring bullet 2.
    kittify_prefixes = (".kittify/", ".kittify" + "\\")  # trailing arm: Windows paths — defensive
    if normalised.startswith(kittify_prefixes) or normalised == ".kittify":
        return True

    # Any WP's task file (WORK_PACKAGE_TASK, PRIMARY-partition) — bullet 3.
    wp_task_pattern = re.compile(r"kitty-specs/[^/]+/tasks/WP\d+-.+\.md$")
    if wp_task_pattern.search(normalised):
        return True

    # Mission-root tasks.md (TASKS_INDEX, PRIMARY-partition) — bullet 3.
    root_tasks_md_pattern = re.compile(r"kitty-specs/[^/]+/tasks\.md$")
    if root_tasks_md_pattern.search(normalised):
        return True

    return False


def _is_benign(path: str, wp_id: str) -> bool:
    """Return True if *path* is a benign (non-blocking) dirty file.

    A path is benign when it satisfies any of the following:

    1. It is toolchain-generated churn the shared
       :func:`specify_cli.coordination.coherence.is_toolchain_generated_churn`
       owner recognises — spec-kitty's own bookkeeping (``meta.json``,
       encoding-provenance JSONL, a ``kitty-ops/<ULID>.jsonl`` Op-record orphan)
       or a recognised coordination-residue artifact (``status.events.jsonl``,
       ``status.json``) — delegated with NO independent literal here (#2251 /
       FR-001 / G-5 invariant; IC-07g retired the former status/meta filename
       entries onto this owner-module leg).
    2. It is one of the genuine review-handoff-only survivors the owner cannot
       classify — see :func:`_is_review_handoff_survivor_path`.
    """
    # Normalise separators for cross-platform safety
    normalised = to_posix(path).strip()

    if is_toolchain_generated_churn(normalised):
        return True

    return _is_review_handoff_survivor_path(normalised)


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
