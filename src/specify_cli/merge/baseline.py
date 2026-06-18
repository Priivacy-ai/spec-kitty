"""Post-merge review baseline (``baseline_merge_commit``) record/verify cluster.

This module owns the mission-state-surface concern of the ``baseline_merge_commit``
``meta.json`` field: it is written here at merge time and read by
``spec-kitty review --mode post-merge``. Extracted verbatim from
``cli/commands/merge.py`` as part of the merge.py god-module decomposition
(epic #2026); behavior is byte-identical to the original definitions.

``merge/`` deliberately does NOT import ``cli.commands.merge``, so relocating
this cluster here introduces no import cycle.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from specify_cli.core.git_ops import run_command
from specify_cli.mission_metadata import load_meta, write_meta

logger = logging.getLogger(__name__)

META_JSON = "meta.json"


class BaselineMergeCommitError(RuntimeError):
    """Raised when the post-merge review baseline cannot be recorded or verified.

    Modern lane missions (those whose ``meta.json`` carries a canonical
    ``mission_id``) MUST land ``baseline_merge_commit`` on the target branch.
    When the baseline is missing, the working meta is absent/corrupt, or the
    committed target meta lacks the expected value, downstream
    ``spec-kitty review`` raises ``MISSION_REVIEW_MODE_MISMATCH``. We surface
    that failure loudly at merge time instead of letting an apparently
    successful merge ship a mission that cannot be reviewed post-merge.
    """


def record_baseline_merge_commit(
    feature_dir: Path,
    baseline_commit: str | None,
    *,
    mission_id: str | None = None,
) -> Path | None:
    """Persist the post-merge review baseline in mission meta.json.

    ``baseline_merge_commit`` anchors post-merge review diffs. It should point
    at the target-branch baseline before the mission lands, not at the final
    housekeeping commit produced by merge.

    For **modern lane missions** (``mission_id`` is set — the canonical ULID
    introduced by mission 083), an empty baseline, a missing ``meta.json``, or
    corrupt JSON is a HARD failure: we raise :class:`BaselineMergeCommitError`
    so the merge stops loudly instead of shipping a mission that
    ``spec-kitty review --mode post-merge`` cannot anchor
    (``MISSION_REVIEW_MODE_MISMATCH``).

    For **legacy missions** (no ``mission_id``) the historical soft behavior is
    preserved: the function logs a warning and returns ``None`` so the merge
    proceeds without a baseline.
    """
    is_modern = bool(mission_id and str(mission_id).strip())

    if not baseline_commit or not baseline_commit.strip():
        if is_modern:
            raise BaselineMergeCommitError(
                f"Cannot record baseline_merge_commit for modern mission "
                f"{feature_dir.name}: no target baseline SHA was captured."
            )
        return None

    meta_path = feature_dir / META_JSON
    if not meta_path.exists():
        if is_modern:
            raise BaselineMergeCommitError(
                f"Cannot record baseline_merge_commit for modern mission "
                f"{feature_dir.name}: meta.json is missing."
            )
        logger.warning(
            "Cannot record baseline_merge_commit for %s: meta.json is missing",
            feature_dir.name,
        )
        return None

    try:
        meta = load_meta(feature_dir)
    except ValueError as exc:
        if is_modern:
            raise BaselineMergeCommitError(
                f"Cannot record baseline_merge_commit for modern mission "
                f"{feature_dir.name}: meta.json is invalid ({exc})."
            ) from exc
        logger.warning(
            "Cannot record baseline_merge_commit for %s: %s",
            feature_dir.name,
            exc,
        )
        return None

    if meta is None:
        if is_modern:
            raise BaselineMergeCommitError(
                f"Cannot record baseline_merge_commit for modern mission "
                f"{feature_dir.name}: meta.json could not be loaded."
            )
        return None

    existing = meta.get("baseline_merge_commit")
    if existing and str(existing).strip():
        return None

    meta["baseline_merge_commit"] = baseline_commit.strip()
    write_meta(feature_dir, meta, validate=False)
    return meta_path


def _recorded_baseline_from_working_meta(feature_dir: Path | None) -> str:
    if feature_dir is None:
        return ""
    try:
        working_meta = load_meta(feature_dir)
    except ValueError:
        return ""
    if not isinstance(working_meta, dict):
        return ""
    return str(working_meta.get("baseline_merge_commit") or "").strip()


def _read_committed_meta_json(
    main_repo: Path,
    target_branch: str,
    meta_rel: str,
    mission_slug: str,
) -> dict[str, object]:
    ret, out, err = run_command(
        ["git", "show", f"{target_branch}:{meta_rel}"],
        capture=True,
        check_return=False,
        cwd=main_repo,
    )
    if ret != 0:
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"could not read {meta_rel} from {target_branch} "
            f"({(err or '').strip() or 'git show failed'})."
        )

    try:
        committed_meta = json.loads(out)
    except json.JSONDecodeError as exc:
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"committed {meta_rel} on {target_branch} is not valid JSON ({exc})."
        ) from exc

    if not isinstance(committed_meta, dict):
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"committed {meta_rel} on {target_branch} is not a JSON object."
        )
    return committed_meta


def assert_baseline_merge_commit_on_target(
    main_repo: Path,
    mission_slug: str,
    target_branch: str,
    expected_baseline: str | None,
    *,
    feature_dir: Path | None = None,
    mission_id: str | None = None,
) -> None:
    """Fail the merge if ``baseline_merge_commit`` did not land on *target_branch*.

    Mirrors :func:`_assert_merged_wps_reached_done`: it reads the target
    branch's COMMITTED ``kitty-specs/<slug>/meta.json`` via
    ``git show <target>:<path>`` and asserts ``baseline_merge_commit`` is both
    present and equal to the baseline that was actually RECORDED for this
    mission. This is the post-commit invariant that closes the gap behind
    ``MISSION_REVIEW_MODE_MISMATCH``: it proves the baseline is durable in git
    history (not just in the working tree) before any worktree removal or
    branch cleanup runs.

    The expected baseline is read from the recorded mission ``meta.json`` in
    *feature_dir* (the idempotent value written by
    :func:`record_baseline_merge_commit`) and only falls back to
    *expected_baseline* when that is unavailable. This is deliberate:
    ``target_baseline_sha`` is re-derived from the live target HEAD on every
    invocation, so on ``spec-kitty merge --resume`` — after a prior run already
    landed the mission/bookkeeping commits — the live HEAD has advanced past the
    original baseline. Comparing the committed value against a re-derived HEAD
    would spuriously fail an otherwise-correct resume; comparing it against the
    recorded value does not.

    Only enforced for **modern missions** (``mission_id`` set). Legacy missions
    never carry a baseline and are skipped.
    """
    if not (mission_id and str(mission_id).strip()):
        return

    recorded = _recorded_baseline_from_working_meta(feature_dir)
    expected = recorded or (expected_baseline or "").strip()
    if not expected:
        raise BaselineMergeCommitError(
            f"Cannot verify baseline_merge_commit for modern mission "
            f"{mission_slug}: no recorded baseline SHA was found."
        )

    meta_rel = f"kitty-specs/{mission_slug}/{META_JSON}"
    committed_meta = _read_committed_meta_json(
        main_repo, target_branch, meta_rel, mission_slug
    )
    committed_baseline = str(committed_meta.get("baseline_merge_commit") or "").strip()
    if not committed_baseline:
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"baseline_merge_commit is missing from committed {meta_rel} on "
            f"{target_branch}. Downstream `spec-kitty review --mode post-merge` "
            f"would fail with MISSION_REVIEW_MODE_MISMATCH."
        )

    if committed_baseline != expected:
        raise BaselineMergeCommitError(
            f"Post-merge baseline validation failed for {mission_slug}: "
            f"committed baseline_merge_commit ({committed_baseline}) on "
            f"{target_branch} does not match the captured baseline ({expected})."
        )


__all__ = [
    "BaselineMergeCommitError",
    "record_baseline_merge_commit",
    "assert_baseline_merge_commit_on_target",
]
