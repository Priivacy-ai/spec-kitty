"""Unit tests for the WP03 (coord-authority-trio-degod-01KX7094) extraction of
``implement.py``'s git-porcelain/diff and placement decision cores into
``implement_cores.py``.

T020: exercises the pure decision logic directly, injecting a fake
:class:`~specify_cli.cli.commands.implement_cores.GitPort` so no real git
subprocess or repository is needed (the ``unit`` marker's contract). Real-git
integration coverage for the same functions (via the historical, git-param-free
signatures with a default port) already lives in
``tests/specify_cli/cli/commands/test_implement.py`` and
``tests/specify_cli/cli/commands/test_implement_vcs_lock_claim.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.cli.commands.implement_cores import (
    DEFAULT_GIT_PORT,
    GitPort,
    PlanningArtifactStagingPlan,
    _committed_meta_mapping,
    _drop_vcs_lock_only_meta,
    _exclude_coord_owned,
    _feature_dir_status_entries,
    _files_changed_vs_ref,
    _is_vcs_lock_only_meta_diff,
    _parse_meta_mapping,
    _parse_porcelain_entries,
    _placement_coord_filter,
    _PorcelainEntry,
    _resolve_claim_commit_target,
    _status_paths_for_commit,
    detect_structural_planning_changes,
    resolve_planning_artifact_staging,
    resolve_precondition_ref,
)
from specify_cli.core.errors import PlacementResolutionRequired
from mission_runtime import CommitTarget

pytestmark = [pytest.mark.unit]


class _FakeGitPort:
    """In-memory :class:`GitPort` -- no subprocess, no real repository."""

    def __init__(
        self,
        *,
        porcelain: str = "",
        blobs: dict[tuple[str, str], bytes | None] | None = None,
    ) -> None:
        self._porcelain = porcelain
        self._blobs = blobs or {}
        self.status_calls: list[tuple[Path, Path]] = []
        self.show_calls: list[tuple[Path, str, str]] = []

    def status_porcelain(self, repo_root: Path, target: Path) -> str:
        self.status_calls.append((repo_root, target))
        return self._porcelain

    def show_blob(self, repo_root: Path, ref: str, repo_rel_path: str) -> bytes | None:
        self.show_calls.append((repo_root, ref, repo_rel_path))
        return self._blobs.get((ref, repo_rel_path))


def test_default_git_port_conforms_to_protocol() -> None:
    """The concrete default port satisfies the GitPort structural protocol."""
    assert isinstance(DEFAULT_GIT_PORT, GitPort)


class TestDetectStructuralPlanningChanges:
    """Squad-B1 (#2464): the git-executor fires the #1598 fail-closed guard via
    this coord-independent detector BEFORE resolving the coordination filter, so
    a topology fault never preempts the structural-refusal message."""

    def test_deletion_and_rename_are_reported(self) -> None:
        fake = _FakeGitPort(porcelain=" D kitty-specs/m/tasks/WP01.md\nR  a.md -> kitty-specs/m/tasks/WP02.md\n")
        structural = detect_structural_planning_changes(Path("/repo"), Path("kitty-specs/m"), git=fake)
        assert [e.is_structural for e in structural] == [True, True]
        assert {e.path for e in structural} == {
            "kitty-specs/m/tasks/WP01.md",
            "kitty-specs/m/tasks/WP02.md",
        }

    def test_modified_and_untracked_are_not_structural(self) -> None:
        fake = _FakeGitPort(porcelain=" M kitty-specs/m/status.json\n?? kitty-specs/m/new.md\n")
        assert detect_structural_planning_changes(Path("/repo"), Path("kitty-specs/m"), git=fake) == []

    def test_reads_only_git_status_not_the_coordination_filter(self) -> None:
        """The detector's git surface is a single ``status`` call -- it never
        resolves coord/topology, which is what can raise (the ordering fix)."""
        fake = _FakeGitPort(porcelain="")
        detect_structural_planning_changes(Path("/repo"), Path("kitty-specs/m"), git=fake)
        assert len(fake.status_calls) == 1
        assert fake.show_calls == []


# ---------------------------------------------------------------------------
# _parse_porcelain_entries / _feature_dir_status_entries
# ---------------------------------------------------------------------------


class TestParsePorcelainEntries:
    def test_modified_unstaged_tracked_file_not_truncated(self) -> None:
        """Regression anchor (see implement.py history): a leading-space
        status code (" M path") must not lose its first path character."""
        entries = _parse_porcelain_entries(" M kitty-specs/demo/status.json\n")
        assert entries == [_PorcelainEntry(xy=" M", path="kitty-specs/demo/status.json", is_structural=False)]

    def test_untracked_file_is_not_structural(self) -> None:
        entries = _parse_porcelain_entries("?? kitty-specs/demo/new.md\n")
        assert entries == [_PorcelainEntry(xy="??", path="kitty-specs/demo/new.md", is_structural=False)]

    def test_deleted_file_is_structural(self) -> None:
        entries = _parse_porcelain_entries(" D kitty-specs/demo/tasks/WP01.md\n")
        assert entries[0].is_structural is True

    def test_rename_uses_new_path_and_is_structural(self) -> None:
        entries = _parse_porcelain_entries("R  kitty-specs/demo/tasks/WP01.md -> kitty-specs/demo/tasks/WP01-renamed.md\n")
        assert entries == [_PorcelainEntry(xy="R ", path="kitty-specs/demo/tasks/WP01-renamed.md", is_structural=True)]

    def test_blank_and_too_short_lines_are_skipped(self) -> None:
        assert _parse_porcelain_entries("\n  \nXY\n") == []

    def test_multiple_lines(self) -> None:
        raw = " M kitty-specs/demo/status.json\n D kitty-specs/demo/tasks/WP01.md\n?? kitty-specs/demo/new.md\n"
        entries = _parse_porcelain_entries(raw)
        assert [e.path for e in entries] == [
            "kitty-specs/demo/status.json",
            "kitty-specs/demo/tasks/WP01.md",
            "kitty-specs/demo/new.md",
        ]
        assert [e.is_structural for e in entries] == [False, True, False]


class TestFeatureDirStatusEntries:
    def test_delegates_to_injected_git_port(self, tmp_path: Path) -> None:
        fake = _FakeGitPort(porcelain=" M kitty-specs/demo/status.json\n")
        feature_dir = tmp_path / "kitty-specs" / "demo"
        entries = _feature_dir_status_entries(tmp_path, feature_dir, git=fake)
        assert entries == [_PorcelainEntry(xy=" M", path="kitty-specs/demo/status.json", is_structural=False)]
        assert fake.status_calls == [(tmp_path, feature_dir)]

    def test_default_git_param_is_the_module_default(self, tmp_path: Path) -> None:
        """Backward-compat: the historical 2-positional-arg call (no ``git``
        kwarg) must still resolve -- against a real (empty) porcelain read,
        not raise."""
        feature_dir = tmp_path / "kitty-specs" / "demo"
        feature_dir.mkdir(parents=True)
        entries = _feature_dir_status_entries(tmp_path, feature_dir)
        assert entries == []


# ---------------------------------------------------------------------------
# _exclude_coord_owned / _status_paths_for_commit
# ---------------------------------------------------------------------------


class TestExcludeCoordOwned:
    def test_no_coord_branch_keeps_all_paths(self) -> None:
        paths = ["kitty-specs/m/status.json", "kitty-specs/m/tasks.md"]
        assert _exclude_coord_owned(paths, None) == paths

    def test_coord_branch_drops_status_files_only(self) -> None:
        paths = ["kitty-specs/m/status.events.jsonl", "kitty-specs/m/status.json", "kitty-specs/m/tasks.md"]
        kept = _exclude_coord_owned(paths, "kitty/mission-m-AAAA1111")
        assert kept == ["kitty-specs/m/tasks.md"]

    def test_status_paths_for_commit_wraps_exclude(self) -> None:
        entries = [
            _PorcelainEntry(xy=" M", path="kitty-specs/m/status.json", is_structural=False),
            _PorcelainEntry(xy=" M", path="kitty-specs/m/tasks.md", is_structural=False),
        ]
        assert _status_paths_for_commit(entries, "kitty/mission-m-AAAA1111") == ["kitty-specs/m/tasks.md"]
        assert set(_status_paths_for_commit(entries, None)) == {
            "kitty-specs/m/status.json",
            "kitty-specs/m/tasks.md",
        }


# ---------------------------------------------------------------------------
# vcs-lock-only meta.json diff family
# ---------------------------------------------------------------------------


class TestIsVcsLockOnlyMetaDiff:
    @pytest.mark.parametrize(
        ("committed", "working", "expected"),
        [
            (None, {}, False),
            ({}, {}, False),
            ({"vcs": "git"}, {"vcs": "git", "vcs_locked_at": "t0"}, True),
            ({"friendly_name": "a"}, {"friendly_name": "b"}, False),
            (
                {"friendly_name": "a", "vcs": "git"},
                {"friendly_name": "a", "vcs_locked_at": "t0", "vcs": "git"},
                True,
            ),
            (
                {"friendly_name": "a"},
                {"friendly_name": "b", "vcs": "git"},
                False,
            ),
        ],
    )
    def test_truth_table(self, committed: dict[str, str] | None, working: dict[str, str], expected: bool) -> None:
        assert _is_vcs_lock_only_meta_diff(committed, working) is expected


class TestParseMetaMapping:
    def test_valid_object(self) -> None:
        assert _parse_meta_mapping(b'{"vcs": "git"}') == {"vcs": "git"}

    def test_non_object_json_returns_none(self) -> None:
        assert _parse_meta_mapping(b"[1, 2, 3]") is None

    def test_invalid_json_returns_none(self) -> None:
        assert _parse_meta_mapping(b"not json") is None

    def test_bad_encoding_returns_none(self) -> None:
        assert _parse_meta_mapping(b"\xff\xfe\x00") is None


class TestCommittedMetaMapping:
    def test_absent_blob_returns_none(self, tmp_path: Path) -> None:
        fake = _FakeGitPort(blobs={})
        assert _committed_meta_mapping(tmp_path, "kitty-specs/m/meta.json", "HEAD", git=fake) is None

    def test_present_blob_parsed(self, tmp_path: Path) -> None:
        fake = _FakeGitPort(blobs={("HEAD", "kitty-specs/m/meta.json"): b'{"vcs": "git"}'})
        result = _committed_meta_mapping(tmp_path, "kitty-specs/m/meta.json", None, git=fake)
        assert result == {"vcs": "git"}

    def test_ref_none_defaults_to_head(self, tmp_path: Path) -> None:
        fake = _FakeGitPort(blobs={("HEAD", "p"): b"{}"})
        _committed_meta_mapping(tmp_path, "p", None, git=fake)
        assert fake.show_calls == [(tmp_path, "HEAD", "p")]


class TestDropVcsLockOnlyMeta:
    def _meta_repo(self, tmp_path: Path, *, committed: bytes, working: bytes) -> tuple[Path, str]:
        meta_rel = "kitty-specs/m/meta.json"
        meta_path = tmp_path / meta_rel
        meta_path.parent.mkdir(parents=True)
        meta_path.write_bytes(working)
        return tmp_path, meta_rel

    def test_noop_when_auto_commit_true(self, tmp_path: Path) -> None:
        paths = ["kitty-specs/m/meta.json"]
        kept = _drop_vcs_lock_only_meta(tmp_path, paths, None, auto_commit=True, git=_FakeGitPort())
        assert kept == paths

    def test_drops_lock_only_meta_diff(self, tmp_path: Path) -> None:
        repo_root, meta_rel = self._meta_repo(
            tmp_path,
            committed=b'{"friendly_name": "a"}',
            working=b'{"friendly_name": "a", "vcs": "git", "vcs_locked_at": "t0"}',
        )
        fake = _FakeGitPort(blobs={("HEAD", meta_rel): b'{"friendly_name": "a"}'})
        kept = _drop_vcs_lock_only_meta(repo_root, [meta_rel], None, auto_commit=False, git=fake)
        assert kept == []

    def test_keeps_non_lock_meta_diff(self, tmp_path: Path) -> None:
        repo_root, meta_rel = self._meta_repo(
            tmp_path,
            committed=b'{"friendly_name": "a"}',
            working=b'{"friendly_name": "b"}',
        )
        fake = _FakeGitPort(blobs={("HEAD", meta_rel): b'{"friendly_name": "a"}'})
        kept = _drop_vcs_lock_only_meta(repo_root, [meta_rel], None, auto_commit=False, git=fake)
        assert kept == [meta_rel]

    def test_keeps_non_meta_paths_untouched(self, tmp_path: Path) -> None:
        kept = _drop_vcs_lock_only_meta(tmp_path, ["kitty-specs/m/tasks.md"], None, auto_commit=False, git=_FakeGitPort())
        assert kept == ["kitty-specs/m/tasks.md"]

    def test_missing_meta_source_is_kept_defensively(self, tmp_path: Path) -> None:
        kept = _drop_vcs_lock_only_meta(tmp_path, ["kitty-specs/m/meta.json"], None, auto_commit=False, git=_FakeGitPort())
        assert kept == ["kitty-specs/m/meta.json"]


class TestResolvePreconditionRef:
    """T001/T002 -- contracts/resolve-precondition-ref.md is authoritative.

    Single owner of the "compare-against-which-ref" decision, resolved PER
    FILE PATH (not once per staging call): on a coord mission
    ``coord_branch_for_filter`` is a single non-``None`` branch for every
    candidate; only the path distinguishes a PRIMARY ``spec.md`` from a COORD
    ``status.events.jsonl``.
    """

    _COORD_BRANCH = "kitty/mission-m-AAAA1111"

    def test_primary_kind_resolves_to_head(self) -> None:
        assert resolve_precondition_ref("kitty-specs/m/spec.md", self._COORD_BRANCH) == "HEAD"

    def test_meta_json_resolves_to_head_even_on_coord_mission(self) -> None:
        """BLOCKER-2 lock: ``meta.json`` is a PRIMARY-partition kind
        (``kind_for_mission_file`` cannot classify it -- routing it through
        that None-returning lookup would misroute it to coord and
        reintroduce #2533). This is the exact file
        ``_committed_meta_mapping`` exists for."""
        assert resolve_precondition_ref("kitty-specs/m/meta.json", self._COORD_BRANCH) == "HEAD"

    def test_coord_residue_kind_resolves_to_coord_branch(self) -> None:
        assert resolve_precondition_ref("kitty-specs/m/status.events.jsonl", self._COORD_BRANCH) == self._COORD_BRANCH

    def test_no_coord_branch_resolves_to_head_even_for_coord_kind(self) -> None:
        """A flattened/non-coord mission (``coord_branch_for_filter is None``)
        never routes to coord, even for an otherwise-coord-residue path."""
        assert resolve_precondition_ref("kitty-specs/m/spec.md", None) == "HEAD"

    def test_no_coord_branch_resolves_status_events_to_head_too(self) -> None:
        assert resolve_precondition_ref("kitty-specs/m/status.events.jsonl", None) == "HEAD"

    def test_unknown_path_defaults_to_head(self) -> None:
        """Fail-safe direction (NFR-004): an unrecognized path is never routed
        to coord -- everything not explicitly coord-residue defaults primary."""
        assert resolve_precondition_ref("kitty-specs/m/unknown-file.txt", self._COORD_BRANCH) == "HEAD"


class TestFilesChangedVsRef:
    def test_no_ref_returns_all_files(self, tmp_path: Path) -> None:
        files = ["a.txt", "b.txt"]
        assert _files_changed_vs_ref(tmp_path, files, None, git=_FakeGitPort()) == files

    def test_missing_source_file_is_skipped(self, tmp_path: Path) -> None:
        assert _files_changed_vs_ref(tmp_path, ["absent.txt"], "HEAD", git=_FakeGitPort()) == []

    def test_identical_content_is_dropped(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_bytes(b"same")
        fake = _FakeGitPort(blobs={("HEAD", "a.txt"): b"same"})
        assert _files_changed_vs_ref(tmp_path, ["a.txt"], "HEAD", git=fake) == []

    def test_differing_content_is_kept(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_bytes(b"new")
        fake = _FakeGitPort(blobs={("HEAD", "a.txt"): b"old"})
        assert _files_changed_vs_ref(tmp_path, ["a.txt"], "HEAD", git=fake) == ["a.txt"]


# ---------------------------------------------------------------------------
# resolve_planning_artifact_staging (T016 pure staging-decision core)
# ---------------------------------------------------------------------------


class TestResolvePlanningArtifactStaging:
    def test_structural_change_short_circuits(self, tmp_path: Path) -> None:
        fake = _FakeGitPort(porcelain=" D kitty-specs/m/tasks/WP01.md\n")
        plan = resolve_planning_artifact_staging(tmp_path, tmp_path / "kitty-specs" / "m", None, [], auto_commit=True, git=fake)
        assert plan.structural
        assert plan.files_to_commit == []
        assert plan.status_paths_to_commit == []

    def test_no_changes_yields_empty_plan(self, tmp_path: Path) -> None:
        fake = _FakeGitPort(porcelain="")
        plan = resolve_planning_artifact_staging(tmp_path, tmp_path / "kitty-specs" / "m", None, [], auto_commit=True, git=fake)
        assert plan == PlanningArtifactStagingPlan(structural=[], files_to_commit=[], status_paths_to_commit=[])

    def test_extra_file_paths_only_added_under_coord_branch(self, tmp_path: Path) -> None:
        artifact_dir = tmp_path / "kitty-specs" / "m"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "tasks.md").write_bytes(b"# tasks")
        # _files_changed_vs_ref's idempotency filter drops any path that does
        # not exist on disk (defensive -- see its docstring), so the extra
        # path must be materialized for it to survive the coord-branch plan.
        (artifact_dir / "extra.md").write_bytes(b"extra")
        fake = _FakeGitPort(porcelain="")
        no_coord_plan = resolve_planning_artifact_staging(tmp_path, artifact_dir, None, ["kitty-specs/m/extra.md"], auto_commit=True, git=fake)
        assert no_coord_plan.files_to_commit == []

        coord_plan = resolve_planning_artifact_staging(
            tmp_path,
            artifact_dir,
            "kitty/mission-m-AAAA1111",
            ["kitty-specs/m/extra.md"],
            auto_commit=True,
            git=fake,
        )
        assert coord_plan.files_to_commit == ["kitty-specs/m/extra.md"]

    def test_idempotent_when_already_matching_its_partition_ref(self, tmp_path: Path) -> None:
        """Idempotency guard: a discovered-but-already-committed edit
        (content identical to the ref for ITS OWN partition) yields an empty
        plan, not an empty-commit attempt (see _files_changed_vs_ref).

        Re-pinned (WP01 / T004): ``tasks.md`` is a PRIMARY-partition kind
        (``TASKS_INDEX``), so on a coord mission it is compared against
        ``HEAD`` -- never the coordination ref -- even though this staging
        call carries a non-``None`` ``coord_branch_for_filter`` (#2533: the
        pre-fix single-ref comparison wrongly diffed it against coord instead,
        where it is legitimately absent, and flagged it as changed).
        """
        artifact_dir = tmp_path / "kitty-specs" / "m"
        artifact_dir.mkdir(parents=True)
        tasks_path = artifact_dir / "tasks.md"
        tasks_path.write_bytes(b"# tasks")
        coord_ref = "kitty/mission-m-AAAA1111"
        fake = _FakeGitPort(
            porcelain=" M kitty-specs/m/tasks.md\n",
            blobs={("HEAD", "kitty-specs/m/tasks.md"): b"# tasks"},
        )
        plan = resolve_planning_artifact_staging(tmp_path, artifact_dir, coord_ref, [], auto_commit=True, git=fake)
        assert plan.files_to_commit == []

    def test_genuinely_changed_primary_file_is_kept_and_flagged_for_instructions(self, tmp_path: Path) -> None:
        """Re-pinned (WP01 / T004, INV-5): a genuinely-dirty PRIMARY artifact
        (``tasks.md``) is still detected and staged on a coord mission -- the
        fix corrects WHICH ref it compares against (``HEAD``), it must not
        blind the check entirely."""
        artifact_dir = tmp_path / "kitty-specs" / "m"
        artifact_dir.mkdir(parents=True)
        tasks_path = artifact_dir / "tasks.md"
        tasks_path.write_bytes(b"# tasks v2")
        coord_ref = "kitty/mission-m-AAAA1111"
        fake = _FakeGitPort(
            porcelain=" M kitty-specs/m/tasks.md\n",
            blobs={("HEAD", "kitty-specs/m/tasks.md"): b"# tasks v1"},
        )
        plan = resolve_planning_artifact_staging(tmp_path, artifact_dir, coord_ref, [], auto_commit=True, git=fake)
        assert plan.files_to_commit == ["kitty-specs/m/tasks.md"]
        assert plan.status_paths_to_commit == ["kitty-specs/m/tasks.md"]

    def test_dirty_spec_md_still_staged_against_head_on_coord_mission(self, tmp_path: Path) -> None:
        """INV-5 invariant: a genuinely-dirty PRIMARY ``spec.md`` on a coord
        mission is still staged (compared against ``HEAD``, never coord)."""
        artifact_dir = tmp_path / "kitty-specs" / "m"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "spec.md").write_bytes(b"# spec v2")
        coord_ref = "kitty/mission-m-AAAA1111"
        fake = _FakeGitPort(
            porcelain=" M kitty-specs/m/spec.md\n",
            blobs={("HEAD", "kitty-specs/m/spec.md"): b"# spec v1"},
        )
        plan = resolve_planning_artifact_staging(tmp_path, artifact_dir, coord_ref, [], auto_commit=True, git=fake)
        assert plan.files_to_commit == ["kitty-specs/m/spec.md"]

    def test_dirty_coord_kind_file_still_resolves_to_coord_ref(self, tmp_path: Path) -> None:
        """NFR-002 coord non-regression: a genuinely-dirty COORD-partition
        artifact (``issue-matrix.md`` -- not one of the ``COORD_OWNED_STATUS_FILES``
        excluded earlier in the pipeline) is still diffed against and staged
        for the coordination ref, exactly as before the fix."""
        artifact_dir = tmp_path / "kitty-specs" / "m"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "issue-matrix.md").write_bytes(b"# issues v2")
        coord_ref = "kitty/mission-m-AAAA1111"
        fake = _FakeGitPort(
            porcelain=" M kitty-specs/m/issue-matrix.md\n",
            blobs={(coord_ref, "kitty-specs/m/issue-matrix.md"): b"# issues v1"},
        )
        plan = resolve_planning_artifact_staging(tmp_path, artifact_dir, coord_ref, [], auto_commit=True, git=fake)
        assert plan.files_to_commit == ["kitty-specs/m/issue-matrix.md"]
        # A copy identical to coord is the idempotent no-op -- confirms the
        # comparison ref really is coord, not HEAD (which the fake has no
        # blob for and would therefore always read as "changed").
        fake_idempotent = _FakeGitPort(
            porcelain=" M kitty-specs/m/issue-matrix.md\n",
            blobs={(coord_ref, "kitty-specs/m/issue-matrix.md"): b"# issues v2"},
        )
        idempotent_plan = resolve_planning_artifact_staging(tmp_path, artifact_dir, coord_ref, [], auto_commit=True, git=fake_idempotent)
        assert idempotent_plan.files_to_commit == []

    def test_meta_json_on_coord_mission_resolves_to_head(self, tmp_path: Path) -> None:
        """BLOCKER-2 lock, exercised at the staging-core level: a ``meta.json``
        that is clean/committed on the primary (target) branch but naturally
        absent on the (empty) coordination branch must NOT be treated as
        changed and staged -- it is compared against ``HEAD``, where its
        content matches, and drops out of the plan entirely (#2533)."""
        artifact_dir = tmp_path / "kitty-specs" / "m"
        artifact_dir.mkdir(parents=True)
        (artifact_dir / "meta.json").write_bytes(b'{"mission_slug": "m"}')
        coord_ref = "kitty/mission-m-AAAA1111"
        fake = _FakeGitPort(
            porcelain="",
            blobs={("HEAD", "kitty-specs/m/meta.json"): b'{"mission_slug": "m"}'},
        )
        plan = resolve_planning_artifact_staging(
            tmp_path,
            artifact_dir,
            coord_ref,
            ["kitty-specs/m/meta.json"],
            auto_commit=True,
            git=fake,
        )
        assert plan.files_to_commit == []


# ---------------------------------------------------------------------------
# placement family
# ---------------------------------------------------------------------------


class TestResolveClaimCommitTarget:
    def test_none_raises_placement_resolution_required(self) -> None:
        with pytest.raises(PlacementResolutionRequired) as excinfo:
            _resolve_claim_commit_target(None)
        assert excinfo.value.error_code == "PLACEMENT_RESOLUTION_REQUIRED"

    def test_resolved_ref_returned_verbatim(self) -> None:
        target = CommitTarget(ref="kitty/mission-demo-AAAA1111")
        assert _resolve_claim_commit_target(target) is target


class TestPlacementCoordFilter:
    def test_none_placement_ref_returns_none(self, tmp_path: Path) -> None:
        assert _placement_coord_filter(tmp_path, "m", None) is None

    def test_coord_topology_returns_placement_ref(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from mission_runtime import MissionTopology

        import specify_cli.cli.commands.implement_cores as cores_module

        monkeypatch.setattr(cores_module, "resolve_topology", lambda _root, _slug: MissionTopology.COORD)
        target = CommitTarget(ref="kitty/mission-m-AAAA1111")
        assert _placement_coord_filter(tmp_path, "m", target) == "kitty/mission-m-AAAA1111"

    def test_flattened_topology_returns_none(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from mission_runtime import MissionTopology

        import specify_cli.cli.commands.implement_cores as cores_module

        monkeypatch.setattr(cores_module, "resolve_topology", lambda _root, _slug: MissionTopology.SINGLE_BRANCH)
        target = CommitTarget(ref="main")
        assert _placement_coord_filter(tmp_path, "m", target) is None
