"""FR-005 snapshot-first liveness + model-reader tests (WP05, T018-T021).

This WP's ``owned_files`` (``core/stale_detection.py``, ``task_utils/support.py``,
``status/wp_metadata.py``) sanction exactly ONE new test file (``create_intent``),
so the new-behavior coverage for all four subtasks is consolidated here rather
than spread across per-module test files this WP does not own.

Central proof (T021, this file's namesake): ``check_wp_staleness``'s
claim-liveness decision is driven by the reduced event-sourced snapshot, not
frontmatter, once the FR-005 phase-1 dual-write flag
(``specify_cli.status.emit._phase1_snapshot_authority_active``) resolves ON — a live
snapshot PID under EMPTY frontmatter reads live (SC-002/AC-2 live side), and
mutating ONLY the snapshot's PID (never the frontmatter/args) flips it stale
(SC-002/AC-2 dead side). Both polarities are made deterministic by
monkeypatching the ``core.process_liveness`` seam on the PID VALUE itself, so
the assertions prove the *snapshot* value is what drives the outcome, not a
constant stub (T021 edge-case guidance).

Also covers:
    - T018: stale_detection resolves claim-liveness from the snapshot
      (flag-gated), zero regression when the flag is off / feature_dir is
      omitted.
    - T019: ``WorkPackage.{shell_pid,agent,assignee}`` resolve from the
      snapshot (flag-gated); the ``## Activity Log`` render folds
      event-sourced notes with no content loss (SC-004).
    - T020: ``WPMetadata`` (via ``read_wp_frontmatter``) resolves its runtime
      fields from the snapshot (flag-gated); ``agent_profile`` stays
      frontmatter-canonical always.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from specify_cli.core.stale_detection import LIVE_CLAIM_PROCESS_REASON, check_wp_staleness
from specify_cli.status.emit import (
    build_claim_policy_metadata,
    emit_inner_state_changed,
    emit_status_transition,
)
from specify_cli.status.models import WPInnerStateDelta
from specify_cli.status.wp_metadata import read_wp_frontmatter
from specify_cli.task_utils.support import WorkPackage, activity_entries, split_frontmatter

from tests.status.conftest import seed_wp_to_planned

pytestmark = pytest.mark.git_repo

MISSION_SLUG = "wp05-liveness-test"
WP_ID = "WP01"


# ── Shared helpers / fixtures ────────────────────────────────────────────


def _init_git_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=repo, check=True, capture_output=True)


def _make_old_commit(repo: Path, branch: str = "kitty/mission-feature-lane-a") -> None:
    """Create a feature branch with a commit well past any staleness threshold."""
    subprocess.run(["git", "checkout", "-b", branch], cwd=repo, check=True, capture_output=True)
    (repo / "feature.txt").write_text("Old work")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)

    old_timestamp = str(int((datetime.now(UTC) - timedelta(hours=12)).timestamp()))
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = f"@{old_timestamp}"
    env["GIT_COMMITTER_DATE"] = f"@{old_timestamp}"
    subprocess.run(["git", "commit", "-m", "Old work"], cwd=repo, check=True, capture_output=True, env=env)


@pytest.fixture
def worktree_path(tmp_path: Path) -> Path:
    """A real git worktree with a commit well past any staleness threshold.

    Without live-claim suppression, ``check_wp_staleness`` would report this
    worktree stale at any reasonable threshold — the fixture exists so the
    liveness-suppression path is the only thing that can make a test assert
    "not stale".
    """
    repo = tmp_path / "worktree"
    _init_git_repo(repo)
    _make_old_commit(repo)
    return repo


@pytest.fixture
def feature_dir_phase1(tmp_path: Path) -> Path:
    """A kitty-specs feature dir with the FR-005 phase-1 flag resolved ON."""
    fd = tmp_path / "kitty-specs" / MISSION_SLUG
    fd.mkdir(parents=True)
    (fd / "meta.json").write_text('{"status_phase": 1}', encoding="utf-8")
    return fd


def _claim(
    feature_dir: Path,
    wp_id: str,
    shell_pid: int,
    shell_pid_created_at: str,
    agent: str = "claude",
) -> None:
    """Seed genesis -> planned -> claimed with a policy_metadata-carried shell_pid.

    Mirrors the real claim-write path (WP03's backfill reconstructs exactly
    this shape) via the production ``emit_status_transition`` pipeline — no
    private read/write path is stubbed (T021 edge-case guidance).
    """
    seed_wp_to_planned(feature_dir, wp_id, slug=MISSION_SLUG)
    emit_status_transition(
        feature_dir=feature_dir,
        mission_slug=MISSION_SLUG,
        wp_id=wp_id,
        to_lane="claimed",
        actor=agent,
        policy_metadata=build_claim_policy_metadata(shell_pid, shell_pid_created_at, agent),
    )


def _annotate(feature_dir: Path, wp_id: str, delta: WPInnerStateDelta, actor: str = "claude") -> None:
    """Persist an ``InnerStateChanged`` mutating ONLY the given delta's slots.

    Never touches any WP markdown file — used to prove a liveness/render flip
    is driven by the snapshot alone, not a frontmatter side-effect.
    """
    emit_inner_state_changed(feature_dir, wp_id, delta, actor=actor, mission_slug=MISSION_SLUG)


def _write_wp_file(
    feature_dir: Path,
    wp_id: str,
    *,
    agent_profile: str = "python-pedro",
    extra_frontmatter: str = "",
    body: str = "# WP\n",
) -> Path:
    """Write a WP markdown file with an EMPTY runtime frontmatter (no agent/
    assignee/shell_pid) — proves the snapshot, not a stale frontmatter value,
    is what the flag-on readers surface.
    """
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    wp_file = tasks_dir / f"{wp_id}.md"
    wp_file.write_text(
        f"---\nwork_package_id: {wp_id}\ntitle: Test WP\nagent_profile: {agent_profile}\n{extra_frontmatter}---\n{body}",
        encoding="utf-8",
    )
    return wp_file


def _load_work_package(wp_file: Path, feature: str = MISSION_SLUG) -> WorkPackage:
    """Build a ``WorkPackage`` the same way ``locate_work_package`` does, without
    the full mission-resolver plumbing this test does not need."""
    text = wp_file.read_text(encoding="utf-8")
    frontmatter, body, padding = split_frontmatter(text)
    return WorkPackage(
        feature=feature,
        path=wp_file,
        current_lane="planned",
        relative_subpath=Path(wp_file.name),
        frontmatter=frontmatter,
        body=body,
        padding=padding,
    )


# ── T018 / T021: snapshot-first claim liveness (two-sided) ──────────────


class TestSnapshotFirstClaimLiveness:
    """T018 (stale_detection reads snapshot claim-liveness) + T021 (two-sided proof)."""

    def test_live_snapshot_pid_suppresses_stale_despite_empty_frontmatter(
        self,
        worktree_path: Path,
        feature_dir_phase1: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SC-002/AC-2 (live side): empty frontmatter + a live snapshot PID -> not stale."""
        live_pid = 555001
        # The claim carries a baseline (FR-005), so liveness routes through
        # ``is_claiming_process_alive`` (not ``is_process_alive``) -- patch
        # both at the pid-value level so the assertion is deterministic and
        # genuinely tied to which pid the snapshot resolved.
        monkeypatch.setattr("specify_cli.core.stale_detection.is_process_alive", lambda pid: pid == live_pid)
        monkeypatch.setattr(
            "specify_cli.core.stale_detection.is_claiming_process_alive",
            lambda pid, baseline: pid == live_pid,  # noqa: ARG005 — baseline unused by design
        )
        _claim(feature_dir_phase1, WP_ID, live_pid, "2026-01-01T00:00:00Z")

        result = check_wp_staleness(
            WP_ID,
            worktree_path,
            threshold_minutes=10,
            shell_pid=None,  # empty frontmatter
            shell_pid_baseline=None,
            feature_dir=feature_dir_phase1,
        )

        assert result.is_stale is False
        assert result.stale.reason == LIVE_CLAIM_PROCESS_REASON

    def test_dead_snapshot_pid_flips_stale_args_never_change(
        self,
        worktree_path: Path,
        feature_dir_phase1: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SC-002/AC-2 (dead side): mutating ONLY the snapshot's PID flips staleness.

        The ``shell_pid``/``shell_pid_baseline`` arguments passed to
        ``check_wp_staleness`` are IDENTICAL (empty) on both calls below — the
        only thing that changes between the "live" and "dead" assertions is
        an ``InnerStateChanged`` annotation against the event log. This is
        the structural proof that the flip is snapshot-driven, not a
        frontmatter passthrough (guards against one-sided test theatre).
        """
        live_pid = 555002
        dead_pid = 555999
        monkeypatch.setattr("specify_cli.core.stale_detection.is_process_alive", lambda pid: pid == live_pid)
        monkeypatch.setattr(
            "specify_cli.core.stale_detection.is_claiming_process_alive",
            lambda pid, baseline: pid == live_pid,  # noqa: ARG005 — baseline unused by design
        )
        _claim(feature_dir_phase1, WP_ID, live_pid, "2026-01-01T00:00:00Z")

        def _check() -> bool:
            # bool() wrap: follow_imports=skip (specify_cli.* boundary) erases
            # `.is_stale`'s real `-> bool` signature at this call site; type-only,
            # no behavior change (mirrors stale_detection.py's own pattern).
            return bool(
                check_wp_staleness(
                    WP_ID,
                    worktree_path,
                    threshold_minutes=10,
                    shell_pid=None,
                    shell_pid_baseline=None,
                    feature_dir=feature_dir_phase1,
                ).is_stale
            )

        assert _check() is False  # live side re-confirmed

        _annotate(feature_dir_phase1, WP_ID, WPInnerStateDelta(shell_pid=dead_pid))

        assert _check() is True  # dead side: flipped by the snapshot mutation alone

    def test_baseline_mismatch_in_snapshot_treats_claim_as_not_alive(
        self,
        worktree_path: Path,
        feature_dir_phase1: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Recycled-PID edge case: a live PID with a MISMATCHED snapshot baseline
        is not alive (FR-004 PID-reuse guard), proving the baseline -- not just
        the PID -- is sourced from the snapshot."""
        live_pid = 555003
        good_baseline = "2026-01-01T00:00:00Z"

        def _fake_is_claiming_process_alive(pid: int, baseline: str | None) -> bool:
            return pid == live_pid and baseline == good_baseline

        monkeypatch.setattr(
            "specify_cli.core.stale_detection.is_claiming_process_alive",
            _fake_is_claiming_process_alive,
        )
        monkeypatch.setattr("specify_cli.core.stale_detection.is_process_alive", lambda pid: False)
        _claim(feature_dir_phase1, WP_ID, live_pid, good_baseline)

        def _check() -> bool:
            # bool() wrap: see the identically-named helper above.
            return bool(
                check_wp_staleness(
                    WP_ID,
                    worktree_path,
                    threshold_minutes=10,
                    shell_pid=None,
                    shell_pid_baseline=None,
                    feature_dir=feature_dir_phase1,
                ).is_stale
            )

        assert _check() is False  # matching baseline -> alive

        # Mutate ONLY the snapshot's baseline (PID unchanged) to a recycled value.
        _annotate(feature_dir_phase1, WP_ID, WPInnerStateDelta(shell_pid_created_at="recycled-baseline"))

        assert _check() is True  # mismatched baseline -> not alive -> stale

    def test_resume_refreshed_snapshot_pid_stays_live(
        self,
        worktree_path: Path,
        feature_dir_phase1: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """NFR-004: a resumed WP whose snapshot PID was refreshed via an
        ``InnerStateChanged`` delta after resume stays live — closes the
        false-stale resume window (US3)."""
        original_pid = 555004
        refreshed_pid = 555005
        monkeypatch.setattr(
            "specify_cli.core.stale_detection.is_process_alive",
            lambda pid: pid == refreshed_pid,
        )
        monkeypatch.setattr(
            "specify_cli.core.stale_detection.is_claiming_process_alive",
            lambda pid, baseline: pid == refreshed_pid,  # noqa: ARG005 — baseline unused by design
        )
        _claim(feature_dir_phase1, WP_ID, original_pid, "2026-01-01T00:00:00Z")

        # Resume: the agent's shell restarts and re-annotates a fresh live PID.
        _annotate(feature_dir_phase1, WP_ID, WPInnerStateDelta(shell_pid=refreshed_pid))

        result = check_wp_staleness(
            WP_ID,
            worktree_path,
            threshold_minutes=10,
            shell_pid=None,
            shell_pid_baseline=None,
            feature_dir=feature_dir_phase1,
        )

        assert result.is_stale is False
        assert result.stale.reason == LIVE_CLAIM_PROCESS_REASON

    def test_flag_off_falls_back_to_frontmatter_zero_regression(
        self,
        worktree_path: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Flag OFF (no meta.json / no status_phase=1): today's frontmatter-sourced
        behavior is unchanged even though a feature_dir is supplied."""
        feature_dir = tmp_path / "kitty-specs" / "no-phase1-mission"
        feature_dir.mkdir(parents=True)
        # A snapshot claim exists, but since the flag is off it must be ignored.
        _claim(feature_dir, WP_ID, 555006, "2026-01-01T00:00:00Z")
        monkeypatch.setattr("specify_cli.core.stale_detection.is_process_alive", lambda pid: pid == 424242)

        result = check_wp_staleness(
            WP_ID,
            worktree_path,
            threshold_minutes=10,
            shell_pid="424242",  # frontmatter-sourced, must win (flag off)
            shell_pid_baseline=None,
            feature_dir=feature_dir,
        )

        assert result.is_stale is False
        assert result.stale.reason == LIVE_CLAIM_PROCESS_REASON

    def test_omitting_feature_dir_preserves_legacy_call_signature(self, worktree_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Every pre-WP05 call site (no ``feature_dir`` argument at all) sees
        byte-identical behavior."""
        monkeypatch.setattr("specify_cli.core.stale_detection.is_process_alive", lambda pid: True)

        result = check_wp_staleness(WP_ID, worktree_path, threshold_minutes=10, shell_pid="4242")

        assert result.is_stale is False
        assert result.stale.reason == LIVE_CLAIM_PROCESS_REASON


# ── T019: WorkPackage model readers + Activity Log render ───────────────


class TestWorkPackageSnapshotReaders:
    def test_properties_resolve_from_snapshot_when_flag_on(self, feature_dir_phase1: Path) -> None:
        wp_file = _write_wp_file(feature_dir_phase1, WP_ID)
        _claim(
            feature_dir_phase1,
            WP_ID,
            777001,
            "2026-01-01T00:00:00Z",
            agent="claude:opus:python-pedro:implementer",
        )

        wp = _load_work_package(wp_file)

        assert wp.shell_pid == "777001"
        assert wp.agent == "claude:opus:python-pedro:implementer"
        # `assignee` is only set via a dedicated annotation (not the claim
        # transition) -- absent here, so the snapshot's authoritative "no
        # value yet" (None) wins, NOT a frontmatter fallback (C-001).
        assert wp.assignee is None

    def test_properties_reflect_reassignment_annotation(self, feature_dir_phase1: Path) -> None:
        wp_file = _write_wp_file(feature_dir_phase1, WP_ID)
        _claim(feature_dir_phase1, WP_ID, 777002, "2026-01-01T00:00:00Z", agent="claude")
        _annotate(feature_dir_phase1, WP_ID, WPInnerStateDelta(assignee="pedro"))

        wp = _load_work_package(wp_file)

        assert wp.assignee == "pedro"

    def test_properties_fall_back_to_frontmatter_when_flag_off(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "no-phase1-mission-2"
        wp_file = _write_wp_file(
            feature_dir,
            WP_ID,
            extra_frontmatter=('agent: "claude"\nassignee: "pedro"\nshell_pid: "424242"\n'),
        )
        # No meta.json under feature_dir -> flag off.

        wp = _load_work_package(wp_file, feature="no-phase1-mission-2")

        assert wp.shell_pid == "424242"
        assert wp.agent == "claude"
        assert wp.assignee == "pedro"

    def test_activity_entries_folds_snapshot_notes_with_no_content_loss(self, feature_dir_phase1: Path) -> None:
        """SC-004: the event-sourced ``notes`` annotation folds INTO the
        rendered rows, and every legacy body-parsed entry still appears
        (no content loss) — behind the FR-005 flag."""
        _claim(feature_dir_phase1, WP_ID, 777003, "2026-01-01T00:00:00Z")
        _annotate(feature_dir_phase1, WP_ID, WPInnerStateDelta(note="Event-sourced note"))

        legacy_body = "# WP01\n\n## Activity Log\n\n- 2025-01-01T00:00:00Z – claude – shell_pid=111 – lane=in_progress – Legacy body note\n"

        entries = activity_entries(legacy_body, feature_dir=feature_dir_phase1, wp_id=WP_ID)
        notes = [entry["note"] for entry in entries]

        assert "Legacy body note" in notes  # migration-window fallback preserved
        assert "Event-sourced note" in notes  # event-sourced fold (SC-004)

    def test_activity_entries_unchanged_when_feature_dir_wp_id_omitted(self) -> None:
        """Every call site that predates this WP (no kwargs) sees byte-identical output."""
        body = "## Activity Log\n\n- 2025-01-01T00:00:00Z – claude – shell_pid=111 – lane=in_progress – Legacy body note\n"

        entries = activity_entries(body)

        assert entries == [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "agent": "claude",
                "lane": "in_progress",
                "note": "Legacy body note",
                "shell_pid": "111",
            }
        ]


# ── T020: WPMetadata runtime-field coercion ──────────────────────────────


class TestWPMetadataSnapshotCoercion:
    def test_read_wp_frontmatter_resolves_runtime_fields_from_snapshot_when_flag_on(self, feature_dir_phase1: Path) -> None:
        wp_file = _write_wp_file(feature_dir_phase1, WP_ID, agent_profile="python-pedro")
        _claim(
            feature_dir_phase1,
            WP_ID,
            888001,
            "2026-01-01T00:00:00Z",
            agent="claude:opus:python-pedro:implementer",
        )

        metadata, _body = read_wp_frontmatter(wp_file)

        assert metadata.shell_pid == 888001
        assert metadata.shell_pid_created_at == "2026-01-01T00:00:00Z"
        assert metadata.agent == "claude:opus:python-pedro:implementer"
        # Authored/static field -- unaffected by the flag (field-authority table).
        assert metadata.agent_profile == "python-pedro"

    def test_read_wp_frontmatter_falls_back_to_frontmatter_when_flag_off(self, tmp_path: Path) -> None:
        feature_dir = tmp_path / "kitty-specs" / "no-phase1-mission-3"
        wp_file = _write_wp_file(
            feature_dir,
            WP_ID,
            extra_frontmatter='agent: "claude"\nshell_pid: "999999"\n',
        )
        # No meta.json -> flag off.

        metadata, _body = read_wp_frontmatter(wp_file)

        assert metadata.shell_pid == 999999
        assert metadata.agent == "claude"

    def test_read_wp_frontmatter_empty_snapshot_entry_yields_none_not_frontmatter(self, feature_dir_phase1: Path) -> None:
        """Flag ON but the WP was never claimed (no snapshot entry): the
        runtime fields resolve to None, never a stale/legacy frontmatter
        value smuggled in via the on-disk file (C-001)."""
        wp_file = _write_wp_file(
            feature_dir_phase1,
            WP_ID,
            extra_frontmatter='agent: "stale-frontmatter-value"\nshell_pid: "111111"\n',
        )

        metadata, _body = read_wp_frontmatter(wp_file)

        assert metadata.shell_pid is None
        assert metadata.agent is None
