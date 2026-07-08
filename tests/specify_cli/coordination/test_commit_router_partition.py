"""Partition-aware ``commit_for_mission`` seam (WP01 / FR-007 / C-006).

``commit_for_mission`` resolved ONE placement for the WHOLE file batch via a
single ``resolve_placement_only(kind=kind)`` call (``commit_router.py:152``).
Any caller that passes a mixed-partition batch under one ``kind`` misrouted
every file to that kind's partition — the root of #2404: ``spec_commit_cmd.py``
(``kind=SPEC``) and ``mission_finalize.py`` (``kind=TASKS_INDEX``) both commit
COORD artifacts (``acceptance-matrix.json`` / ``issue-matrix.md`` / ``status.*``)
to the PRIMARY branch, so ``accept`` reads a stale coord copy.

This module pins the fix at the SEAM (contracts/partition-aware-commit-seam.md):

* RED-1 — a batch mixing a PRIMARY file (``tasks.md``) and a COORD file
  (``acceptance-matrix.json``) under ``kind=TASKS_INDEX`` must land each file on
  its OWN partition's ref (INV-C1). Proven RED against the pre-fix single-call
  code (both files land on the PRIMARY ref).
* RED-2 — a batch containing a ``None``-classified file (unrecognised path, e.g.
  ``gap-analysis.md``) under ``kind=SPEC`` must still commit — via the
  caller-``kind`` fallback — never dropped, never coerced into the wrong
  partition. This is the regression guard for a naive per-file rewrite that
  filters ``kind_f is not None`` and silently drops the unclassified file.
* Fast path — a genuinely single-partition batch (the common case: every real
  caller today) commits via ONE ``resolve_placement_only`` call and ONE
  ``safe_commit`` call, byte-identical to the pre-fix code path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mission_runtime import (
    CommitTarget,
    MissionArtifactKind,
    MissionTopology,
    is_primary_artifact_kind,
    kind_for_mission_file,
)
from specify_cli.coordination import commit_router
from specify_cli.git.protection_policy import ProtectionPolicy

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_PRIMARY_REF = "main"
_COORD_REF = "kitty/mission-001-demo-coord-A1B2C3D4"


class _FakeCommitResult:
    sha = "deadbeef1234"


def _call_paths(call: dict[str, object]) -> tuple[Path, ...]:
    """Type-narrow a recorded ``safe_commit`` call's ``paths`` kwarg."""
    paths = call["paths"]
    assert isinstance(paths, tuple)
    return paths


def _call_target(call: dict[str, object]) -> CommitTarget:
    """Type-narrow a recorded ``safe_commit`` call's ``target`` kwarg."""
    target = call["target"]
    assert isinstance(target, CommitTarget)
    return target


def _make_policy(*, protected: bool) -> ProtectionPolicy:
    branches: frozenset[str] = frozenset({_PRIMARY_REF}) if protected else frozenset()
    return ProtectionPolicy(protected_branches=branches, operator_hatch_active=False)


def _fake_resolve_placement_only(
    _repo_root: Path, _mission_slug: str, *, kind: MissionArtifactKind
) -> CommitTarget:
    """Kind-aware placement stub: PRIMARY kinds -> main, everything else -> coord ref."""
    if is_primary_artifact_kind(kind):
        return CommitTarget(ref=_PRIMARY_REF)
    return CommitTarget(ref=_COORD_REF)


def _install_common_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    coord_worktree: Path,
) -> list[dict[str, object]]:
    """Wire the router's placement/topology/materialiser/safe_commit seams.

    Returns the list ``safe_commit`` calls are recorded into (kwargs dicts).
    """
    monkeypatch.setattr(commit_router, "resolve_placement_only", _fake_resolve_placement_only)
    monkeypatch.setattr(commit_router, "resolve_topology", lambda *_a, **_kw: MissionTopology.COORD)
    monkeypatch.setattr(commit_router, "_resolve_primary_target_branch", lambda *_a, **_kw: _PRIMARY_REF)

    def _fake_materialise(
        repo_root: Path,
        _mission_slug: str,
        _placement: object,
        files: tuple[Path, ...],
        *,
        kind: MissionArtifactKind,
        primary_paths_created_this_invocation: frozenset[Path] | None = None,
    ) -> tuple[Path, tuple[Path, ...]]:
        staged: list[Path] = []
        for src in files:
            dst = coord_worktree / src.relative_to(repo_root)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            staged.append(dst)
        return coord_worktree, tuple(staged)

    monkeypatch.setattr(commit_router, "_materialise_coord_worktree", _fake_materialise)

    safe_commit_calls: list[dict[str, object]] = []

    def _fake_safe_commit(**kwargs: object) -> _FakeCommitResult:
        safe_commit_calls.append(kwargs)
        return _FakeCommitResult()

    monkeypatch.setattr(commit_router, "safe_commit", _fake_safe_commit)
    return safe_commit_calls


# ---------------------------------------------------------------------------
# RED-1 — mixed batch misroutes without the fix
# ---------------------------------------------------------------------------


def test_mixed_batch_routes_each_file_to_its_own_partition_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-C1: a mixed-partition batch lands each file on its OWN partition ref.

    Pre-fix: ``commit_for_mission`` resolves ONE placement for the whole batch
    via ``resolve_placement_only(kind=TASKS_INDEX)`` (a PRIMARY kind) -> "main".
    Since the resolved placement equals the primary target branch, ``use_coord``
    is False and BOTH ``tasks.md`` AND ``acceptance-matrix.json`` are committed
    directly to "main" in ONE ``safe_commit`` call -- the coord artifact is
    misrouted to the primary branch (#2404). This assertion is RED against that
    code: it expects TWO ``safe_commit`` calls, one per partition, with
    ``acceptance-matrix.json`` landing on the COORD ref.
    """
    mission_slug = "001-demo"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

    tasks_file = feature_dir / "tasks.md"
    tasks_file.write_text("# Tasks\n", encoding="utf-8")
    matrix_file = feature_dir / "acceptance-matrix.json"
    matrix_file.write_text("{}", encoding="utf-8")

    coord_worktree = tmp_path / ".worktrees" / "coord"
    coord_worktree.mkdir(parents=True)

    safe_commit_calls = _install_common_fakes(monkeypatch, coord_worktree=coord_worktree)
    policy = _make_policy(protected=False)

    result = commit_router.commit_for_mission(
        tmp_path,
        mission_slug,
        (tasks_file, matrix_file),
        "chore: finalize tasks",
        policy,
        kind=MissionArtifactKind.TASKS_INDEX,
    )

    # INV-C1: TWO commits, one per partition -- never one commit smearing both
    # files onto a single ref.
    assert len(safe_commit_calls) == 2, (
        f"expected 2 partition-scoped commits, got {len(safe_commit_calls)}: "
        f"{safe_commit_calls!r}"
    )

    ref_by_filename: dict[str, str] = {}
    for call in safe_commit_calls:
        target = _call_target(call)
        for path in _call_paths(call):
            ref_by_filename[path.name] = target.ref

    assert ref_by_filename["tasks.md"] == _PRIMARY_REF
    assert ref_by_filename["acceptance-matrix.json"] == _COORD_REF, (
        "acceptance-matrix.json (a COORD-partition artifact) must land on the "
        "coordination ref, not the caller's TASKS_INDEX (PRIMARY) ref -- the "
        "exact #2404 mis-route this WP closes at the seam."
    )
    assert result.status == "committed"


# ---------------------------------------------------------------------------
# RED-2 — None-classified file is never dropped
# ---------------------------------------------------------------------------


def test_none_classified_file_falls_back_to_caller_kind_and_still_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ``None``-classified file (unrecognised path) is never dropped/misrouted.

    ``gap-analysis.md`` is not in ``_COORD_RESIDUE_FILENAMES`` /
    ``_COORD_RESIDUE_DIRS`` -- ``kind_for_mission_file`` classifies it ``None``.
    The contract requires the None-fallback to use the CALLER-supplied ``kind``
    (never dropped, never coerced into the other partition). This is the
    regression guard for a naive per-file rewrite that filters
    ``if kind_f is not None`` and silently drops the unclassified file, or that
    routes it to an arbitrary default partition instead of the caller's own.
    """
    mission_slug = "001-demo"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

    spec_file = feature_dir / "spec.md"
    spec_file.write_text("# Spec\n", encoding="utf-8")
    gap_analysis_file = feature_dir / "gap-analysis.md"
    gap_analysis_file.write_text("# Gap analysis\n", encoding="utf-8")

    assert kind_for_mission_file(gap_analysis_file, mission_slug=mission_slug) is None, (
        "test fixture assumption broken: gap-analysis.md must be an unclassified "
        "(kind=None) path for this test to exercise the fallback"
    )

    coord_worktree = tmp_path / ".worktrees" / "coord"
    coord_worktree.mkdir(parents=True)

    safe_commit_calls = _install_common_fakes(monkeypatch, coord_worktree=coord_worktree)
    policy = _make_policy(protected=False)

    result = commit_router.commit_for_mission(
        tmp_path,
        mission_slug,
        (spec_file, gap_analysis_file),
        "chore: spec + gap analysis",
        policy,
        kind=MissionArtifactKind.SPEC,
    )

    # Fast path: both files share ONE partition (SPEC is PRIMARY; the
    # None-classified file falls back to SPEC's own PRIMARY partition) -> ONE
    # safe_commit call, both files present, landing on the caller-kind ref.
    assert len(safe_commit_calls) == 1, (
        f"expected the None-fallback to join the caller-kind's single partition "
        f"group, got {len(safe_commit_calls)} commits: {safe_commit_calls!r}"
    )
    committed_names = {p.name for p in _call_paths(safe_commit_calls[0])}
    assert committed_names == {"spec.md", "gap-analysis.md"}, (
        "gap-analysis.md (kind=None) was dropped or split into a separate commit "
        "instead of falling back to the caller-supplied kind's partition"
    )
    assert _call_target(safe_commit_calls[0]).ref == _PRIMARY_REF
    assert result.status == "committed"


# ---------------------------------------------------------------------------
# Fast path — single-partition batch is unchanged (one resolve, one commit)
# ---------------------------------------------------------------------------


def test_single_partition_batch_keeps_the_fast_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A batch that is ALL one partition commits via exactly one placement + one commit.

    No behavioural change for the overwhelmingly common real-world shape: every
    real caller today submits a self-consistent batch (e.g. spec.md +
    data-model.md, both PRIMARY). ``resolve_placement_only`` must be called
    exactly once, with the caller's own ``kind`` -- not re-derived per file.
    """
    mission_slug = "001-demo"
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True)

    spec_file = feature_dir / "spec.md"
    spec_file.write_text("# Spec\n", encoding="utf-8")
    data_model_file = feature_dir / "data-model.md"
    data_model_file.write_text("# Data model\n", encoding="utf-8")

    resolve_calls: list[MissionArtifactKind] = []

    def _spy_resolve(
        _repo_root: Path, _mission_slug: str, *, kind: MissionArtifactKind
    ) -> CommitTarget:
        resolve_calls.append(kind)
        return CommitTarget(ref=_PRIMARY_REF)

    monkeypatch.setattr(commit_router, "resolve_placement_only", _spy_resolve)
    monkeypatch.setattr(
        commit_router, "resolve_topology", lambda *_a, **_kw: MissionTopology.SINGLE_BRANCH
    )
    monkeypatch.setattr(
        commit_router, "_resolve_primary_target_branch", lambda *_a, **_kw: _PRIMARY_REF
    )

    safe_commit_calls: list[dict[str, object]] = []

    def _fake_safe_commit(**kwargs: object) -> _FakeCommitResult:
        safe_commit_calls.append(kwargs)
        return _FakeCommitResult()

    monkeypatch.setattr(commit_router, "safe_commit", _fake_safe_commit)
    policy = _make_policy(protected=False)

    result = commit_router.commit_for_mission(
        tmp_path,
        mission_slug,
        (spec_file, data_model_file),
        "chore: spec + data model",
        policy,
        kind=MissionArtifactKind.SPEC,
    )

    assert resolve_calls == [MissionArtifactKind.SPEC], (
        "fast path must resolve placement exactly once, with the caller's own kind"
    )
    assert len(safe_commit_calls) == 1
    assert {p.name for p in _call_paths(safe_commit_calls[0])} == {
        "spec.md",
        "data-model.md",
    }
    assert result.status == "committed"
