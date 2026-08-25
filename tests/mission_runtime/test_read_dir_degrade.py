"""Tests for the read-side degrade companion ``resolve_read_dir_or_degrade`` (WP04, FR-006, #3462).

Companion to ``tests/mission_runtime/test_write_target_degrade.py``. These are red-first:
the module + the two consumer migrations do not exist yet.

Invariants pinned here (contracts/read-dir-degrade.md):
- INV-R1: each migrated site's degrade/success behavior is unchanged (per-site parity):
  * ``retrospective/generator.py::_load_traces`` degrades to an empty trace list (ZERO_EVIDENCE).
  * ``core/worktree_topology.py`` degrades ``status_feature_dir`` to ``feature_dir`` (DEGRADE_TO_FEATURE_DIR).
- INV-R2 (#1848): a resolution error whose type is NOT in the caller's ``caught`` set propagates
  verbatim — the helper never swallows an excluded exception. ``status/aggregate.py`` is NOT
  migrated and still surfaces ``COORDINATION_BRANCH_DELETED``.
- INV-R3: the degrade path logs at WARNING.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from mission_runtime.artifacts import MissionArtifactKind
from mission_runtime.read_dir_degrade import (
    ReadDegradeStrategy,
    ReadDirDecision,
    resolve_read_dir_or_degrade,
)
from specify_cli.coordination.surface_resolver import CoordinationBranchDeleted
from specify_cli.missions._read_path_resolver import StatusReadPathNotFound

# Pure-logic, tmp_path-only tests with no subprocess/git overhead -- same tier as the
# sibling ``tests/mission_runtime/test_write_target_degrade.py``.
pytestmark = [pytest.mark.fast]


def _coord_deleted(repo_root: Path, mission_slug: str) -> CoordinationBranchDeleted:
    return CoordinationBranchDeleted(
        repo_root=repo_root,
        mission_slug=mission_slug,
        mid8="01HXYZ00",
        coordination_branch=f"kitty/mission-{mission_slug}-coord",
        coord_candidate=repo_root / "coord-candidate",
        primary_candidate=repo_root / "primary-candidate",
    )


def _status_read_not_found(repo_root: Path, mission_slug: str) -> StatusReadPathNotFound:
    return StatusReadPathNotFound(
        repo_root=repo_root,
        mission_slug=mission_slug,
        mid8="01HXYZ00",
        coord_candidate=repo_root / "coord-candidate",
        primary_candidate=repo_root / "primary-candidate",
    )


class _FakeSeam:
    """Stand-in for ``PlacementSeam`` whose ``read_dir`` returns a fixed dir or raises."""

    def __init__(self, *, returns: Path | None = None, raises: BaseException | None = None) -> None:
        self._returns = returns
        self._raises = raises

    def read_dir(self, kind: MissionArtifactKind) -> Path:  # noqa: ARG002 - mirror the real signature
        if self._raises is not None:
            raise self._raises
        assert self._returns is not None
        return self._returns


def _patch_seam(monkeypatch: pytest.MonkeyPatch, seam: _FakeSeam) -> None:
    monkeypatch.setattr(
        "mission_runtime.read_dir_degrade.placement_seam",
        lambda repo_root, mission_slug: seam,
    )


class TestResolutionSucceeds:
    def test_returns_resolved_dir_not_degraded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        resolved = tmp_path / "resolved-surface"
        _patch_seam(monkeypatch, _FakeSeam(returns=resolved))

        decision = resolve_read_dir_or_degrade(
            tmp_path,
            "some-mission",
            MissionArtifactKind.STATUS_STATE,
            strategy=ReadDegradeStrategy.DEGRADE_TO_FEATURE_DIR,
            caught=(CoordinationBranchDeleted,),
            degrade_target=tmp_path / "feature-dir",
        )

        assert isinstance(decision, ReadDirDecision)
        assert decision.read_dir == resolved
        assert decision.degraded is False
        assert decision.strategy is ReadDegradeStrategy.DEGRADE_TO_FEATURE_DIR


class TestInvR1GeneratorZeroEvidence:
    """INV-R1: retrospective ``_load_traces`` degrades to zero trace evidence."""

    def test_helper_degrades_to_target_on_coord_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sentinel = tmp_path / "empty-trace-dir"
        _patch_seam(
            monkeypatch, _FakeSeam(raises=_coord_deleted(tmp_path, "retro-mission"))
        )

        decision = resolve_read_dir_or_degrade(
            tmp_path,
            "retro-mission",
            MissionArtifactKind.TRACER_FILE,
            strategy=ReadDegradeStrategy.ZERO_EVIDENCE,
            caught=(CoordinationBranchDeleted, StatusReadPathNotFound),
            degrade_target=sentinel,
        )

        assert decision.read_dir == sentinel
        assert decision.degraded is True

    def test_helper_degrades_on_plain_status_read_path_not_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The generator caught ``(CoordinationBranchDeleted, StatusReadPathNotFound)``;
        a plain ``StatusReadPathNotFound`` (NOT the coord-deleted subclass) must still
        degrade — proving byte-identical parity with the pre-migration except tuple.
        """
        sentinel = tmp_path / "empty-trace-dir"
        _patch_seam(
            monkeypatch, _FakeSeam(raises=_status_read_not_found(tmp_path, "retro-mission"))
        )

        decision = resolve_read_dir_or_degrade(
            tmp_path,
            "retro-mission",
            MissionArtifactKind.TRACER_FILE,
            strategy=ReadDegradeStrategy.ZERO_EVIDENCE,
            caught=(CoordinationBranchDeleted, StatusReadPathNotFound),
            degrade_target=sentinel,
        )

        assert decision.degraded is True
        assert decision.read_dir == sentinel

    def test_real_load_traces_returns_empty_on_coord_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end parity: the migrated ``_load_traces`` returns ``[]`` when the
        tracer surface raises ``CoordinationBranchDeleted`` (the pre-migration contract)."""
        from specify_cli.retrospective.generator import _load_traces

        feature_dir = tmp_path / "kitty-specs" / "retro-mission"
        feature_dir.mkdir(parents=True)
        _patch_seam(
            monkeypatch, _FakeSeam(raises=_coord_deleted(tmp_path, "retro-mission"))
        )

        assert _load_traces(tmp_path, feature_dir) == []


class TestInvR1TopologyDegradeToFeatureDir:
    """INV-R1: worktree_topology degrades ``status_feature_dir`` to ``feature_dir``."""

    def test_helper_returns_feature_dir_on_coord_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        feature_dir = tmp_path / "kitty-specs" / "topo-mission"
        feature_dir.mkdir(parents=True)
        _patch_seam(
            monkeypatch, _FakeSeam(raises=_coord_deleted(tmp_path, "topo-mission"))
        )

        decision = resolve_read_dir_or_degrade(
            tmp_path,
            "topo-mission",
            MissionArtifactKind.STATUS_STATE,
            strategy=ReadDegradeStrategy.DEGRADE_TO_FEATURE_DIR,
            caught=(CoordinationBranchDeleted,),
            degrade_target=feature_dir,
        )

        assert decision.read_dir == feature_dir
        assert decision.degraded is True


class TestInvR2PropagatesExcludedException:
    """INV-R2 (#1848): a type NOT in ``caught`` propagates verbatim (never swallowed)."""

    def test_coord_deleted_propagates_when_excluded_from_caught(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        raised = _coord_deleted(tmp_path, "excluded-mission")
        _patch_seam(monkeypatch, _FakeSeam(raises=raised))

        with pytest.raises(CoordinationBranchDeleted) as exc_info:
            resolve_read_dir_or_degrade(
                tmp_path,
                "excluded-mission",
                MissionArtifactKind.STATUS_STATE,
                # ``caught`` deliberately EXCLUDES CoordinationBranchDeleted (and its base):
                strategy=ReadDegradeStrategy.DEGRADE_TO_FEATURE_DIR,
                caught=(FileNotFoundError,),
                degrade_target=tmp_path / "feature-dir",
            )

        assert exc_info.value is raised
        assert exc_info.value.error_code == "COORDINATION_BRANCH_DELETED"

    def test_fail_closed_reraises_caught_exception_verbatim(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        raised = _coord_deleted(tmp_path, "fail-closed-mission")
        _patch_seam(monkeypatch, _FakeSeam(raises=raised))

        with pytest.raises(CoordinationBranchDeleted) as exc_info:
            resolve_read_dir_or_degrade(
                tmp_path,
                "fail-closed-mission",
                MissionArtifactKind.STATUS_STATE,
                strategy=ReadDegradeStrategy.FAIL_CLOSED,
                caught=(CoordinationBranchDeleted,),
                degrade_target=None,
            )

        assert exc_info.value is raised

    def test_aggregate_site_not_migrated_still_surfaces_distinct_error(self) -> None:
        """Pin: ``status/aggregate.py`` is bespoke/allowlisted — NOT routed through the
        helper — and still re-raises ``CoordinationBranchDeleted`` verbatim (#1848 ordering)."""
        aggregate_src = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "specify_cli"
            / "status"
            / "aggregate.py"
        ).read_text(encoding="utf-8")
        # Bespoke handler intact:
        assert "except CoordinationBranchDeleted:" in aggregate_src
        assert "COORDINATION_BRANCH_DELETED" in aggregate_src
        # NOT migrated onto the read-side companion:
        assert "resolve_read_dir_or_degrade" not in aggregate_src


class TestInvR3DegradeLogsWarning:
    def test_degrade_path_logs_at_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        _patch_seam(
            monkeypatch, _FakeSeam(raises=_coord_deleted(tmp_path, "warn-mission"))
        )

        with caplog.at_level(logging.WARNING, logger="mission_runtime.read_dir_degrade"):
            resolve_read_dir_or_degrade(
                tmp_path,
                "warn-mission",
                MissionArtifactKind.TRACER_FILE,
                strategy=ReadDegradeStrategy.ZERO_EVIDENCE,
                caught=(CoordinationBranchDeleted,),
                degrade_target=tmp_path / "empty",
            )

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "degrade path must log at WARNING"
        assert any("warn-mission" in r.getMessage() for r in warnings)


class TestDegradeTargetRequired:
    def test_degrade_without_target_raises_value_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _patch_seam(
            monkeypatch, _FakeSeam(raises=_coord_deleted(tmp_path, "no-target-mission"))
        )

        with pytest.raises(ValueError, match="degrade_target"):
            resolve_read_dir_or_degrade(
                tmp_path,
                "no-target-mission",
                MissionArtifactKind.TRACER_FILE,
                strategy=ReadDegradeStrategy.ZERO_EVIDENCE,
                caught=(CoordinationBranchDeleted,),
                degrade_target=None,
            )
