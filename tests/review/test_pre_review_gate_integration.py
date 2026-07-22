"""WP02 — ``for_review`` gate hook + config/override precedence integration
tests (mission ``review-regression-gate-01KWX6DF``, closes #572 refs #1979
#2283).

Every test below drives the REAL ``move-task --to for_review`` orchestrator
(``_do_move_task``) end-to-end with the REAL WP01 gate engine
(``pre_review_gate.evaluate_pre_review_gate`` / ``derive_test_scope`` /
``run_scoped_tests_at_head`` / ``diff_baseline``) against a REAL throwaway git
repository — never a stubbed/mocked verdict. The only injected seam is the
LIVE gate-coverage authority lookup (``_pre_review_gate_filter_groups`` /
``_pre_review_gate_composite_routing``), which mirrors the SAME override seam
WP01's own ``derive_test_scope`` exposes for its unit tests (see
``tests/review/test_pre_review_gate_engine.py``) — swapping it avoids the
``sys.modules`` staleness trap a throwaway
``tests/architectural/_gate_coverage.py`` fixture would hit (the real repo's
cached module would silently shadow it).

Only the "mission bookkeeping" side (status events, WP frontmatter, coord
write capabilities) is faked, via the SAME Fake-port pattern
``test_move_task_orchestration.py`` already established for this exact
command. The WP's "code" side is a genuine git repository with genuine
passing/failing pytest tests, diffed and run for real.

**Split note (mission doctrine-controlled-transition-gates-01KY51Z7 WP03,
T014).** Every test in this file drives the HOOK end-to-end
(``_do_move_task`` -> ``tasks_move_task._mt_run_pre_review_gate`` ->
``pre_review_gate.evaluate_pre_review_gate``), so it exercises the
``tasks_move_task.py``-facing "hook-binding" surface — WP03 does not own
that file and does not invert it; the thin-alias/erroneous-activation
closure for it is WP09 T040/T045/T046. WP03's owned change here is
STRUCTURAL, not behavioural: the engine now accepts an optional injected
``scope_source`` (default ``None`` preserves this file's exact prior
behaviour byte-for-byte — every test below still passes unmodified,
confirming the port refactor is behaviour-preserving for this surface,
NFR-001). The genuinely NEW port-driven paths this WP adds (the injected-
``ScopeSource`` seam, the #2330 ``DeclaredCommandScopeSource`` closure, and
the ``pre_existing_not_blocked`` baseline-relative guard) are ENGINE-level
concerns and live in ``tests/review/test_pre_review_gate_engine.py``
instead — the WP prompt explicitly sanctions that file (or a sibling under
``tests/review/``) as T015's home, keeping this file's scope to the
runner/hook it already covers.
"""

from __future__ import annotations

import ctypes
import contextlib
import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
import typer

from specify_cli.agent_tasks_ports import (
    CommitArtifactResult,
    CommitStatusResult,
    MissionHandle,
    TasksPorts,
)
from specify_cli.cli.commands.agent import tasks_move_task
from specify_cli.cli.commands.agent.tasks_move_task import _do_move_task, _MoveTaskArgs
from specify_cli.core.commit_guard import GuardCapability
from specify_cli.review import pre_review_gate
from specify_cli.review.baseline import BaselineFailure, BaselineTestResult
from specify_cli.status.models import Lane, StatusEvent, TransitionRequest
from specify_cli.status.store import append_event
from specify_cli.status.reducer import materialize
from specify_cli.status.store import read_events
from specify_cli.workspace.context import ResolvedWorkspace
from tests.mocked_env import setup_mocked_env
from tests.specify_cli.cli.commands.agent.test_tasks_ports import (
    FakeFsReader,
    FakeGitOps,
    FakeRender,
)

# Every scenario builds a real throwaway git repo (subprocess `git init`) to
# drive the REAL gate engine — the same category `tests/review/test_baseline.py`
# / `test_artifacts.py` / `test_cycle.py` already use for their own real-git
# fixtures. The handful of pure/precedence-only tests below still carry their
# own `@pytest.mark.fast`.
pytestmark = [pytest.mark.git_repo]

_MISSION = "test-pre-review-gate"

# ---------------------------------------------------------------------------
# Synthetic filter-group / composite-routing fixtures — mirror WP01's own
# ``test_pre_review_gate_engine.py`` shapes closely enough to pin the
# SC-003/SC-004/SC-007 scenarios offline, WITHOUT needing a real
# ``tests/architectural/_gate_coverage.py`` under the throwaway fixture repo
# (see the module docstring for why that would be unreliable).
# ---------------------------------------------------------------------------

_FAKE_GROUPS: dict[str, tuple[str, ...]] = {
    "status": (
        "src/specify_cli/status/**",
        "tests/status/**",
    ),
    "core_misc": (
        "src/specify_cli/status/**",
        "tests/architectural/**",
        "tests/integration/**",
    ),
    "auth_audit_git": (
        "src/specify_cli/git/**",
    ),
    "governance": (
        "src/specify_cli/validators/**",
    ),
}

_FAKE_ROUTING: dict[str, pre_review_gate._CompositeRoute] = {
    "git": (None, None, ("tests/git",)),
    "validators": (None, None, ()),
}

_CONSUMER_TEST_BODY = (
    "from pathlib import Path\n\n\n"
    "def test_consumer_reads_shared_contract():\n"
    "    foo = Path(__file__).resolve().parents[2] / 'src' / 'specify_cli' / 'git' / 'foo.py'\n"
    "    assert 'VALUE = 1' in foo.read_text()\n"
)

_ALWAYS_RED_TEST_BODY = (
    "from pathlib import Path\n\n\n"
    "def test_consumer_always_red():\n"
    "    foo = Path(__file__).resolve().parents[2] / 'src' / 'specify_cli' / 'git' / 'foo.py'\n"
    "    assert 'VALUE = 999' in foo.read_text()  # never true -- pre-existing red\n"
)

# Pre-merge finding 2 (#572/#1979/#2283): a genuinely-failing override-scope
# target, standalone (no dependency on the git/foo.py consumer fixture) --
# used to prove the FR-004 override tier's NEW_FAILURES/block/force branch,
# which previously had zero coverage (only the passing-target
# ``no_new_failures`` branch of the override tier was ever exercised).
_ALWAYS_RED_OVERRIDE_TEST_BODY = (
    "def test_override_target_genuinely_fails():\n"
    "    assert False, 'genuine failure for the override-scope block/force test'\n"
)


# ---------------------------------------------------------------------------
# Fixture-repo builders (real git, real pytest — no mocking of the gate)
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)


def _git_commit_all(path: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", message], cwd=path, check=True)


def _write_file(repo: Path, relative_path: str, content: str) -> None:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _build_base_repo(tmp_path: Path, *, extra_base_files: dict[str, str] | None = None) -> Path:
    """A real git repo: ``main`` carries the base state; ``wip-lane`` (checked
    out from it, no extra commits yet) is where callers add the WP's own
    changes, mirroring a lane worktree branched off its target branch."""
    repo = tmp_path / "fixture-repo"
    _init_git_repo(repo)
    _write_file(repo, "README.md", "base\n")
    for rel_path, content in (extra_base_files or {}).items():
        _write_file(repo, rel_path, content)
    _git_commit_all(repo, "base commit")
    subprocess.run(["git", "checkout", "-q", "-b", "wip-lane"], cwd=repo, check=True)
    return repo


def _probe_failure_nodeid(repo: Path, *, test_target: str = "tests/git") -> str:
    """One-off REAL subprocess pytest probe learning the exact JUnit-derived
    failure identity for the fixture's known-broken consumer test, so
    baseline fixtures can key on the SAME identity ``diff_baseline`` uses --
    without hardcoding pytest/junit-xml's classname format."""
    result = pre_review_gate.run_scoped_tests_at_head([test_target], repo_root=repo)
    assert result.ran, result.error
    assert len(result.current_failures) == 1, result.current_failures
    return result.current_failures[0].test


# ---------------------------------------------------------------------------
# Mission-bookkeeping fixtures (faked — same pattern as
# test_move_task_orchestration.py)
# ---------------------------------------------------------------------------


def _build_wp_file(
    tmp_path: Path, mission_slug: str, wp_id: str, *, extra_frontmatter: str = "",
) -> tuple[Path, Path]:
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".kittify").mkdir(exist_ok=True)
    wp_file = tasks_dir / f"{wp_id}-test.md"
    wp_file.write_text(
        f"---\n"
        f"work_package_id: {wp_id}\n"
        f"title: Test {wp_id}\n"
        f"execution_mode: code_change\n"
        f"agent: testbot\n"
        f"owned_files:\n  - src/{wp_id.lower()}/**\n"
        f"authoritative_surface: src/{wp_id.lower()}/\n"
        f"{extra_frontmatter}"
        f"---\n\n# {wp_id}\n\n## Activity Log\n",
        encoding="utf-8",
    )
    return feature_dir, wp_file


def _seed_wp_event(feature_dir: Path, wp_id: str, to_lane: str) -> None:
    append_event(
        feature_dir,
        StatusEvent(
            event_id=f"test-{wp_id}-{to_lane}",
            mission_slug=feature_dir.name,
            wp_id=wp_id,
            from_lane=Lane.PLANNED,
            to_lane=Lane(to_lane),
            at="2026-01-01T00:00:00+00:00",
            actor="test",
            force=True,
            execution_mode="worktree",
        ),
    )


def _write_config_yaml(main_repo_root: Path, *, block: bool = False, test_command: str | None = None) -> None:
    lines = ["review:"]
    if block:
        lines.append("  fail_on_pre_review_regression: true")
    if test_command:
        lines.append(f'  pre_review_test_command: "{test_command}"')
    (main_repo_root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _seed_baseline(
    feature_dir: Path, wp_slug: str, *, failed: int, failures: tuple[BaselineFailure, ...] = (),
) -> None:
    baseline = BaselineTestResult(
        wp_id="WP01",
        captured_at="2026-01-01T00:00:00Z",
        base_branch="main",
        base_commit="deadbeef",
        test_runner="pytest",
        total=10,
        passed=10 - failed,
        failed=failed,
        skipped=0,
        failures=failures,
    )
    baseline.save(feature_dir / "tasks" / wp_slug / "baseline-tests.json")


def _fixture_workspace(repo: Path, *, wp_id: str = "WP01") -> ResolvedWorkspace:
    """A real ``lane_workspace`` resolution pointing at ``repo`` (the WP's
    "code" side), injected via ``setup_mocked_env``'s ``workspace_resolution``
    so ``resolve_workspace_for_wp`` never runs its own (heavier, lanes.json-
    dependent) resolution logic in these tests."""
    return ResolvedWorkspace(
        mission_slug=_MISSION,
        wp_id=wp_id,
        execution_mode="code_change",
        mode_source="frontmatter",
        resolution_kind="lane_workspace",
        workspace_name="wip-lane",
        worktree_path=repo,
        branch_name="wip-lane",
        lane_id="lane-a",
        lane_wp_ids=[wp_id],
        context=None,
    )


@dataclass
class _RecordingCoordRouter:
    """Records the FULL ``TransitionRequest`` (unlike the shared
    ``FakeCoordCommitRouter``, which only records ``(mission_slug,
    capability)``) so tests can inspect ``policy_metadata`` — the FR-004
    transition-evidence surface this WP writes to."""

    write_dir: Path
    status_calls: list[TransitionRequest] = field(default_factory=list)

    def feature_write_dir(self, mission: MissionHandle) -> Path:
        return self.write_dir

    def commit_status(
        self, request: TransitionRequest, *, capability: GuardCapability,
    ) -> CommitStatusResult:
        self.status_calls.append(request)
        return CommitStatusResult(event=None, skipped=False)

    def commit_artifact(
        self, mission: MissionHandle, paths: object, message: str, *, kind: object, policy: object,
    ) -> CommitArtifactResult:
        raise AssertionError(
            "commit_artifact should never be called for the auto_commit=False moves in this suite"
        )


def _fake_ports(feature_dir: Path) -> tuple[TasksPorts, _RecordingCoordRouter]:
    router = _RecordingCoordRouter(write_dir=feature_dir)
    ports = TasksPorts(fs=FakeFsReader(), coord=router, git=FakeGitOps(), render=FakeRender())
    return ports, router


def _run_move(
    main_repo_root: Path,
    *,
    ports: TasksPorts,
    force: bool = False,
    json_output: bool = True,
    target_branch: str = "main",
    workspace_resolution: Any = None,
) -> None:
    with setup_mocked_env(
        main_repo_root,
        mission_slug=_MISSION,
        target_branch=target_branch,
        workspace_resolution=workspace_resolution,
        extra_patches={
            "_validate_ready_for_review": (True, []),
            "_check_unchecked_subtasks": [],
        },
    ):
        _do_move_task(
            _MoveTaskArgs(
                task_id="WP01",
                to="for_review",
                mission=_MISSION,
                agent=None,
                assignee=None,
                shell_pid=None,
                note=None,
                review_feedback_file=None,
                approval_ref=None,
                reviewer=None,
                self_review_fallback=False,
                intended_reviewer=None,
                reviewer_failure_reason=None,
                done_override_reason=None,
                force=force,
                tracker_ref=None,
                skip_review_artifact_check=False,
                auto_commit=False,
                json_output=json_output,
            ),
            ports=ports,
        )


def _gate_metadata(request: TransitionRequest) -> dict[str, Any]:
    assert request.policy_metadata is not None
    metadata = request.policy_metadata["pre_review_gate"]
    assert isinstance(metadata, dict)
    return metadata


# ---------------------------------------------------------------------------
# T006 — new-failure surfaced, red-first (SC-001)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_new_failure_surfaced_by_the_real_gate_red_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SC-001 / red-first (mandatory): a consuming-shard test that genuinely
    fails at head but not at base is surfaced (warn) by the REAL gate.
    Live-evidence artifact: with the hook DISABLED the same breakage reaches
    ``for_review`` completely silently (the pre-WP02 gap #572 describes);
    with the hook enabled (default) it is caught and the surfaced output
    contains the failing test's nodeid.
    """
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_filter_groups", lambda: _FAKE_GROUPS)
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_composite_routing", lambda: _FAKE_ROUTING)

    repo = _build_base_repo(
        tmp_path,
        extra_base_files={
            "src/specify_cli/git/foo.py": "VALUE = 1\n",
            "tests/git/test_consumer.py": _CONSUMER_TEST_BODY,
        },
    )
    _write_file(repo, "src/specify_cli/git/foo.py", "VALUE = 2\n")
    _git_commit_all(repo, "wip: bump VALUE without updating the consumer")
    failing_nodeid = _probe_failure_nodeid(repo)

    # --- RED-FIRST: hook disabled -> the breakage reaches for_review silently ---
    feature_dir_off, _wp_off = _build_wp_file(tmp_path / "hook-off", _MISSION, "WP01")
    _seed_wp_event(feature_dir_off, "WP01", "in_progress")
    _seed_baseline(feature_dir_off, "WP01-test", failed=0)
    ports_off, router_off = _fake_ports(feature_dir_off)
    with pytest.MonkeyPatch.context() as disabled:
        disabled.setattr(tasks_move_task, "_mt_run_pre_review_gate", lambda st: None)
        _run_move(
            tmp_path / "hook-off", ports=ports_off, workspace_resolution=_fixture_workspace(repo),
        )
    assert len(router_off.status_calls) == 1
    assert router_off.status_calls[0].policy_metadata is None

    # --- CAUGHT: hook enabled (default) -> the same breakage is surfaced ---
    feature_dir_on, _wp_on = _build_wp_file(tmp_path / "hook-on", _MISSION, "WP01")
    _seed_wp_event(feature_dir_on, "WP01", "in_progress")
    _seed_baseline(feature_dir_on, "WP01-test", failed=0)
    ports_on, router_on = _fake_ports(feature_dir_on)
    _run_move(tmp_path / "hook-on", ports=ports_on, workspace_resolution=_fixture_workspace(repo))

    assert len(router_on.status_calls) == 1  # warn-default: transition still proceeds
    metadata = _gate_metadata(router_on.status_calls[0])
    assert metadata["outcome"] == "new_failures"
    assert failing_nodeid in metadata["new_failure_nodeids"]
    assert metadata["blocked"] is False
    assert metadata["block_enabled"] is False


# ---------------------------------------------------------------------------
# T006 — pre-existing base failure does not block (SC-002)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_pre_existing_failure_does_not_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-002: a failure already red on the base branch never blocks the
    WP, even with the opt-in block enabled — the baseline diff (WP01's
    ``diff_baseline``, reused unchanged) excludes it from ``new_failures``."""
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_filter_groups", lambda: _FAKE_GROUPS)
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_composite_routing", lambda: _FAKE_ROUTING)

    repo = _build_base_repo(
        tmp_path,
        extra_base_files={
            "src/specify_cli/git/foo.py": "VALUE = 1\n",
            "tests/git/test_consumer.py": _ALWAYS_RED_TEST_BODY,
        },
    )
    _write_file(repo, "src/specify_cli/git/foo.py", "VALUE = 2\n")
    _git_commit_all(repo, "wip: unrelated bump")
    pre_existing_nodeid = _probe_failure_nodeid(repo)

    feature_dir, _wp = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _seed_baseline(
        feature_dir,
        "WP01-test",
        failed=1,
        failures=(BaselineFailure(test=pre_existing_nodeid, error="pre-existing", file="tests/git/test_consumer.py:1"),),
    )
    _write_config_yaml(tmp_path, block=True)  # block ON — must still never fire here
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports, workspace_resolution=_fixture_workspace(repo))

    assert len(router.status_calls) == 1  # never blocked
    metadata = _gate_metadata(router.status_calls[0])
    assert metadata["outcome"] == "no_new_failures"
    assert metadata["new_failure_count"] == 0
    assert metadata["pre_existing_failure_count"] == 1
    assert metadata["blocked"] is False


# ---------------------------------------------------------------------------
# T006 — bounded scope: status/emit.py -> status shard, not core_misc (SC-003/SC-004)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_bounded_scope_status_shard_excludes_core_misc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_filter_groups", lambda: _FAKE_GROUPS)
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_composite_routing", lambda: _FAKE_ROUTING)

    repo = _build_base_repo(
        tmp_path,
        extra_base_files={"tests/status/test_trivial.py": "def test_trivial():\n    assert True\n"},
    )
    _write_file(repo, "src/specify_cli/status/emit.py", "STATUS = 1\n")
    _git_commit_all(repo, "wip: touch status/emit.py")

    feature_dir, _wp = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _seed_baseline(feature_dir, "WP01-test", failed=0)
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports, workspace_resolution=_fixture_workspace(repo))

    metadata = _gate_metadata(router.status_calls[0])
    assert "status" in metadata["matched_shard_groups"]
    assert "core_misc" not in metadata["matched_shard_groups"]
    assert metadata["outcome"] == "no_new_failures"


# ---------------------------------------------------------------------------
# T006 — empty-cone composite: no_coverage warn, not a clean pass (SC-007)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_empty_cone_composite_is_no_coverage_not_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_filter_groups", lambda: _FAKE_GROUPS)
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_composite_routing", lambda: _FAKE_ROUTING)

    repo = _build_base_repo(tmp_path)
    _write_file(repo, "src/specify_cli/validators/schema.py", "SCHEMA = 1\n")
    _git_commit_all(repo, "wip: touch validators/schema.py")

    feature_dir, _wp = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _write_config_yaml(tmp_path, block=True)  # block ON — must still never fire on no_coverage
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports, workspace_resolution=_fixture_workspace(repo))

    assert len(router.status_calls) == 1  # never blocked
    metadata = _gate_metadata(router.status_calls[0])
    assert metadata["outcome"] == "no_coverage"
    assert metadata["blocked"] is False


# ---------------------------------------------------------------------------
# #2534 — consumer repo (no live gate-coverage authority) degrades calmly
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_consumer_repo_missing_gate_authority_degrades_to_calm_warn(
    tmp_path: Path,
) -> None:
    """Authority-load failure degrades to a non-blocking ``no_coverage`` warn.

    Deliberately does NOT monkeypatch
    ``_pre_review_gate_filter_groups``/``_pre_review_gate_composite_routing``
    (unlike every other test in this file) so the REAL
    ``pre_review_gate.GateAuthoritiesUnavailable`` path fires through the REAL
    ``move-task --to for_review`` entry point when the gate-coverage authority
    cannot be loaded for the fixture repo.

    MIGRATED (T042 / #2534, mission ``doctrine-controlled-transition-gates-01KY51Z7``
    WP09): the pre-inversion ``is_consumer_repo`` split — a bespoke, calmly-worded
    ``_PRE_REVIEW_CONSUMER_REPO_REASON`` that scrubbed the internal
    ``tests.architectural._gate_coverage`` module name — is RETIRED. Under the
    inverted, doctrine-resolved gate, activation is the SOLE impl selector, so a
    consumer repo simply never activates the Spec-Kitty handler; every remaining
    authority-load failure now folds into the SAME generic per-handler fail-open
    warn (``tasks_move_task._mt_dispatch_one_gate``). The invariant this test
    still guards — a non-blocking ``no_coverage`` warn, never a crash or a block —
    is unchanged; only the bespoke consumer-facing wording is gone.
    """
    repo = _build_base_repo(tmp_path, extra_base_files={"src/wp01/foo.py": "VALUE = 1\n"})
    _write_file(repo, "src/wp01/foo.py", "VALUE = 2\n")
    _git_commit_all(repo, "wip: touch owned file")

    feature_dir, _wp = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _seed_baseline(feature_dir, "WP01-test", failed=0)
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports, workspace_resolution=_fixture_workspace(repo))

    assert len(router.status_calls) == 1  # never blocked
    metadata = _gate_metadata(router.status_calls[0])
    assert metadata["outcome"] == "no_coverage"
    assert metadata["blocked"] is False
    reason = metadata["reason"] or ""
    assert reason.startswith("gate authorities unavailable — unverified:")


# ---------------------------------------------------------------------------
# T004 — opt-in block: blocks without --force, --force bypasses + is recorded
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_block_mode_blocks_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_filter_groups", lambda: _FAKE_GROUPS)
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_composite_routing", lambda: _FAKE_ROUTING)

    repo = _build_base_repo(
        tmp_path,
        extra_base_files={
            "src/specify_cli/git/foo.py": "VALUE = 1\n",
            "tests/git/test_consumer.py": _CONSUMER_TEST_BODY,
        },
    )
    _write_file(repo, "src/specify_cli/git/foo.py", "VALUE = 2\n")
    _git_commit_all(repo, "wip: bump VALUE without updating the consumer")
    failing_nodeid = _probe_failure_nodeid(repo)

    feature_dir, _wp = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _seed_baseline(feature_dir, "WP01-test", failed=0)
    _write_config_yaml(tmp_path, block=True)
    ports, router = _fake_ports(feature_dir)

    with pytest.raises(typer.Exit) as exc_info:
        _run_move(tmp_path, ports=ports, workspace_resolution=_fixture_workspace(repo))
    assert exc_info.value.exit_code == 1
    assert router.status_calls == []  # blocked BEFORE the transition is committed

    payload = json.loads(capsys.readouterr().out)
    assert failing_nodeid in payload["error"]


@pytest.mark.integration
def test_force_bypasses_block_and_is_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_filter_groups", lambda: _FAKE_GROUPS)
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_composite_routing", lambda: _FAKE_ROUTING)

    repo = _build_base_repo(
        tmp_path,
        extra_base_files={
            "src/specify_cli/git/foo.py": "VALUE = 1\n",
            "tests/git/test_consumer.py": _CONSUMER_TEST_BODY,
        },
    )
    _write_file(repo, "src/specify_cli/git/foo.py", "VALUE = 2\n")
    _git_commit_all(repo, "wip: bump VALUE without updating the consumer")

    feature_dir, _wp = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _seed_baseline(feature_dir, "WP01-test", failed=0)
    _write_config_yaml(tmp_path, block=True)
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports, force=True, workspace_resolution=_fixture_workspace(repo))

    assert len(router.status_calls) == 1  # --force bypassed the block
    metadata = _gate_metadata(router.status_calls[0])
    assert metadata["outcome"] == "new_failures"
    assert metadata["block_enabled"] is True
    assert metadata["blocked"] is False
    assert metadata["force_bypassed"] is True


# ---------------------------------------------------------------------------
# FR-003 — baseline uncomputable degrades to warn, never blocks
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_baseline_uncomputable_degrades_to_warn_never_blocks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_filter_groups", lambda: _FAKE_GROUPS)
    monkeypatch.setattr(tasks_move_task, "_pre_review_gate_composite_routing", lambda: _FAKE_ROUTING)

    repo = _build_base_repo(
        tmp_path,
        extra_base_files={"tests/status/test_trivial.py": "def test_trivial():\n    assert True\n"},
    )
    _write_file(repo, "src/specify_cli/status/emit.py", "STATUS = 1\n")
    _git_commit_all(repo, "wip: touch status/emit.py")

    feature_dir, _wp = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    # Deliberately NO baseline artifact written -> BaselineTestResult.load() is None.
    _write_config_yaml(tmp_path, block=True)
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports, workspace_resolution=_fixture_workspace(repo))

    assert len(router.status_calls) == 1
    metadata = _gate_metadata(router.status_calls[0])
    assert metadata["outcome"] == "unverified_baseline"
    assert metadata["blocked"] is False


# ---------------------------------------------------------------------------
# T005 — override precedence: frontmatter > config > census-derived default
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_scope_override_frontmatter_wins_over_config(tmp_path: Path) -> None:
    (tmp_path / ".kittify").mkdir()
    _write_config_yaml(tmp_path, test_command="tests/config-scope")
    frontmatter = "work_package_id: WP01\npre_review_test_scope: tests/frontmatter-scope\n"

    result = tasks_move_task._mt_pre_review_scope_override(frontmatter, tmp_path)

    assert result == ("tests/frontmatter-scope",)


@pytest.mark.fast
def test_scope_override_config_wins_when_frontmatter_absent(tmp_path: Path) -> None:
    (tmp_path / ".kittify").mkdir()
    _write_config_yaml(tmp_path, test_command="tests/config-scope tests/config-scope2")
    frontmatter = "work_package_id: WP01\n"

    result = tasks_move_task._mt_pre_review_scope_override(frontmatter, tmp_path)

    assert result == ("tests/config-scope", "tests/config-scope2")


@pytest.mark.fast
def test_scope_override_none_when_neither_set(tmp_path: Path) -> None:
    frontmatter = "work_package_id: WP01\n"

    result = tasks_move_task._mt_pre_review_scope_override(frontmatter, tmp_path)

    assert result is None


@pytest.mark.integration
def test_frontmatter_override_end_to_end_bypasses_auto_derivation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-004 end-to-end: an explicit frontmatter override runs the REAL gate
    against the override target — and bypasses ``derive_test_scope``'s
    auto-derivation entirely. Proven by deliberately NOT patching the
    filter-group/composite-routing seam: if the override didn't bypass
    auto-derivation, ``GateAuthoritiesUnavailable`` would fire (no real
    ``tests/architectural/_gate_coverage.py`` exists under the fixture repo)
    and the outcome would be ``no_coverage``, not ``no_new_failures``.
    """
    repo = _build_base_repo(
        tmp_path,
        extra_base_files={
            "tests/override-target/test_trivial.py": "def test_trivial():\n    assert True\n",
            "src/specify_cli/git/foo.py": "VALUE = 1\n",
        },
    )
    _write_file(repo, "src/specify_cli/git/foo.py", "VALUE = 2\n")
    _git_commit_all(repo, "wip: touch git/foo.py")

    feature_dir, _wp = _build_wp_file(
        tmp_path, _MISSION, "WP01", extra_frontmatter="pre_review_test_scope: tests/override-target\n",
    )
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _seed_baseline(feature_dir, "WP01-test", failed=0)
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports, workspace_resolution=_fixture_workspace(repo))

    metadata = _gate_metadata(router.status_calls[0])
    assert metadata["test_targets"] == ["tests/override-target"]
    assert metadata["outcome"] == "no_new_failures"
    assert metadata["matched_shard_groups"] == []  # derive_test_scope never ran


# ---------------------------------------------------------------------------
# Pre-merge finding 2 (#572/#1979/#2283) — the override tier (FR-004) must
# feed the SAME warn/block/force policy as the auto-derived tier. Before this
# fix, ``_mt_pre_review_gate_with_override_scope`` hand-mirrored
# ``evaluate_pre_review_gate``'s tail instead of reusing it, and only its
# ``no_new_failures`` branch was ever driven by a test — the NEW_FAILURES /
# block / force / UNVERIFIED_BASELINE branches of the copy had ZERO coverage.
# These two tests mirror ``test_block_mode_blocks_without_force`` /
# ``test_force_bypasses_block_and_is_recorded`` above, but through the
# override precedence tier instead of the census-derived auto-scope.
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_override_scope_new_failure_blocks_when_opted_in(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """RED-FIRST (mandatory): a frontmatter ``pre_review_test_scope`` override
    pointing at a genuinely-failing target, with the opt-in block on, MUST
    BLOCK — proving the override tier's ``NEW_FAILURES``/block branch is
    wired through the shared, tested ``pre_review_gate.evaluate_with_scope``
    body rather than a divergence-prone hand-mirrored copy.
    """
    repo = _build_base_repo(tmp_path)
    _write_file(repo, "tests/override-target/test_thing.py", _ALWAYS_RED_OVERRIDE_TEST_BODY)
    _git_commit_all(repo, "wip: add an override-target test that genuinely fails")
    failing_nodeid = _probe_failure_nodeid(repo, test_target="tests/override-target")

    feature_dir, _wp = _build_wp_file(
        tmp_path, _MISSION, "WP01", extra_frontmatter="pre_review_test_scope: tests/override-target\n",
    )
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _seed_baseline(feature_dir, "WP01-test", failed=0)
    _write_config_yaml(tmp_path, block=True)
    ports, router = _fake_ports(feature_dir)

    with pytest.raises(typer.Exit) as exc_info:
        _run_move(tmp_path, ports=ports, workspace_resolution=_fixture_workspace(repo))
    assert exc_info.value.exit_code == 1
    assert router.status_calls == []  # blocked BEFORE the transition is committed

    payload = json.loads(capsys.readouterr().out)
    assert failing_nodeid in payload["error"]


@pytest.mark.integration
def test_override_scope_force_bypasses_block_and_is_recorded(tmp_path: Path) -> None:
    """The override tier's ``--force`` escape mirrors the auto-derived tier's:
    bypasses the block, transition proceeds, and the bypass is recorded in
    the transition evidence (FR-004)."""
    repo = _build_base_repo(tmp_path)
    _write_file(repo, "tests/override-target/test_thing.py", _ALWAYS_RED_OVERRIDE_TEST_BODY)
    _git_commit_all(repo, "wip: add an override-target test that genuinely fails")

    feature_dir, _wp = _build_wp_file(
        tmp_path, _MISSION, "WP01", extra_frontmatter="pre_review_test_scope: tests/override-target\n",
    )
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    _seed_baseline(feature_dir, "WP01-test", failed=0)
    _write_config_yaml(tmp_path, block=True)
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports, force=True, workspace_resolution=_fixture_workspace(repo))

    assert len(router.status_calls) == 1  # --force bypassed the block
    metadata = _gate_metadata(router.status_calls[0])
    assert metadata["outcome"] == "new_failures"
    assert metadata["test_targets"] == ["tests/override-target"]
    assert metadata["matched_shard_groups"] == []  # derive_test_scope never ran (override tier)
    assert metadata["block_enabled"] is True
    assert metadata["blocked"] is False
    assert metadata["force_bypassed"] is True


# ---------------------------------------------------------------------------
# Pre-merge finding 1 (#572/#1979/#2283) — the opt-in block is silently inert
# without a captured baseline (``review.test_command`` unset ->
# ``capture_baseline`` never writes an artifact -> the verdict can only ever
# be ``NO_COVERAGE``/``UNVERIFIED_BASELINE``, never ``NEW_FAILURES`` -> the
# block can NEVER engage). The console-warning path must surface that
# explicitly instead of folding it into the routine dim advisory line.
# ---------------------------------------------------------------------------


def _no_coverage_verdict(reason: str = "excluded scope — unverified") -> pre_review_gate.GateVerdict:
    return pre_review_gate.GateVerdict(
        outcome=pre_review_gate.GateOutcome.NO_COVERAGE,
        scope=pre_review_gate.ScopeResult(
            test_targets=(),
            matched_shard_groups=(),
            matched_composite_dirs=(),
            empty_cone_composite_dirs=(),
            excluded_scope_files=(),
        ),
        reason=reason,
    )


def _unverified_baseline_verdict() -> pre_review_gate.GateVerdict:
    return pre_review_gate.GateVerdict(
        outcome=pre_review_gate.GateOutcome.UNVERIFIED_BASELINE,
        scope=pre_review_gate.ScopeResult(
            test_targets=("tests/git",),
            matched_shard_groups=(),
            matched_composite_dirs=("git",),
            empty_cone_composite_dirs=(),
            excluded_scope_files=(),
        ),
        reason="baseline uncomputable — surfacing all current failures as unverified",
    )


@pytest.mark.fast
def test_console_warning_stays_dim_when_block_disabled() -> None:
    """block_enabled=False: unchanged routine dim advisory -- no behavior
    change for the (default, non-opted-in) common case."""
    line = tasks_move_task._mt_pre_review_gate_console_warning(_no_coverage_verdict(), block_enabled=False)
    assert line == "[dim]Pre-review regression gate: no_coverage — excluded scope — unverified[/dim]"


@pytest.mark.fast
def test_console_warning_surfaces_block_cannot_enforce_on_no_coverage() -> None:
    """block_enabled=True + NO_COVERAGE: explicit, non-dim, names the
    review.test_command prerequisite instead of staying silent."""
    line = tasks_move_task._mt_pre_review_gate_console_warning(_no_coverage_verdict(), block_enabled=True)
    assert "[dim]" not in line
    assert "[yellow]" in line
    assert "review.test_command" in line
    assert "COULD NOT be enforced" in line
    assert "no_coverage" in line


@pytest.mark.fast
def test_console_warning_surfaces_block_cannot_enforce_on_unverified_baseline() -> None:
    """Same escalation for UNVERIFIED_BASELINE — the other verdict shape a
    block can never fire on."""
    line = tasks_move_task._mt_pre_review_gate_console_warning(_unverified_baseline_verdict(), block_enabled=True)
    assert "[dim]" not in line
    assert "review.test_command" in line
    assert "unverified_baseline" in line


@pytest.mark.fast
def test_console_warning_new_failures_unaffected_by_block_enabled() -> None:
    """A genuine NEW_FAILURES verdict's message is untouched by
    block_enabled — this finding is scoped to the two "can't enforce"
    outcomes only; a real verdict needs no prerequisite hint."""
    verdict = pre_review_gate.GateVerdict(
        outcome=pre_review_gate.GateOutcome.NEW_FAILURES,
        scope=pre_review_gate.ScopeResult(
            test_targets=("tests/git",),
            matched_shard_groups=(),
            matched_composite_dirs=("git",),
            empty_cone_composite_dirs=(),
            excluded_scope_files=(),
        ),
        new_failures=(
            BaselineFailure(test="tests/git/test_x.py::test_x", error="boom", file="tests/git/test_x.py:1"),
        ),
    )
    with_block = tasks_move_task._mt_pre_review_gate_console_warning(verdict, block_enabled=True)
    without_block = tasks_move_task._mt_pre_review_gate_console_warning(verdict, block_enabled=False)
    assert with_block == without_block
    assert "review.test_command" not in with_block


# ---------------------------------------------------------------------------
# DoD — existing move-task behavior intact (no regression)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_existing_transition_behavior_intact_when_no_workspace_resolvable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """No regression: with NO lane workspace resolvable (the shape of every
    pre-existing move-task test fixture that predates this WP -- no
    lanes.json, no workspace context), the hook degrades to a cheap
    ``no_coverage`` warn and the transition proceeds EXACTLY as it did
    before -- same event count, same JSON result shape, now carrying only an
    ADDITIVE ``pre_review_gate`` key.
    """
    feature_dir, wp_file = _build_wp_file(tmp_path, _MISSION, "WP01")
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    ports, router = _fake_ports(feature_dir)

    _run_move(tmp_path, ports=ports)  # workspace_resolution=None -> real resolver, no lanes.json

    assert len(router.status_calls) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"] == "success"
    assert payload["new_lane"] == "for_review"
    assert payload["pre_review_gate"]["outcome"] == "no_coverage"
    # Runtime state is event-only after the #2816 cutover; the authored WP
    # artifact remains byte-stable instead of receiving an Activity Log row.
    assert "Moved to for_review" not in wp_file.read_text(encoding="utf-8")


@pytest.mark.integration
def test_scoped_runner_drains_large_output_while_emitting_liveness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A child exceeding pipe capacity cannot deadlock the polling lifecycle."""
    noisy_test = tmp_path / "test_noisy.py"
    noisy_test.write_text(
        "import sys\n"
        "import time\n\n"
        "def test_noisy_failure():\n"
        "    sys.stdout.write('pipe-diagnostic-' * 70000)\n"
        "    sys.stdout.flush()\n"
        "    time.sleep(0.1)\n"
        "    assert False, 'expected noisy failure'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(pre_review_gate, "_HEAD_RUN_HEARTBEAT_INTERVAL", 0.01)
    heartbeats: list[float] = []

    result = pre_review_gate.run_scoped_tests_at_head(
        ["test_noisy.py"],
        repo_root=tmp_path,
        progress_callback=heartbeats.append,
    )

    assert result.ran is True
    assert result.state is pre_review_gate.HeadRunState.COMPLETED
    assert heartbeats
    assert "pipe-diagnostic" in result.stdout
    assert any("test_noisy_failure" in failure.test for failure in result.current_failures)


@pytest.mark.integration
@pytest.mark.skipif(sys.platform != "linux", reason="subreaper SIGKILL harness is Linux-only")
def test_sigkill_recovery_reads_prior_authoritative_lane(tmp_path: Path) -> None:
    """Kill the exact command inside its real gate, then reconcile authority."""
    repo = _build_base_repo(tmp_path)
    fifo_path = tmp_path / "gate-ready.fifo"
    os.mkfifo(fifo_path)
    _write_file(
        repo,
        "test_gate_block.py",
        "import os\n"
        "import time\n\n"
        "def test_hold_real_gate():\n"
        "    with open(os.environ['GATE_READY_FIFO'], 'w', encoding='utf-8') as ready:\n"
        "        ready.write(f'{os.getpid()}\\n')\n"
        "        ready.flush()\n"
        "    time.sleep(30)\n",
    )
    _git_commit_all(repo, "add synchronized gate target")
    feature_dir, wp_path = _build_wp_file(
        tmp_path,
        _MISSION,
        "WP01",
        extra_frontmatter="pre_review_test_scope: test_gate_block.py\n",
    )
    _seed_wp_event(feature_dir, "WP01", "in_progress")
    events_before = read_events(feature_dir)
    wp_before = wp_path.read_bytes()
    command_script = f"""
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner
from specify_cli.cli.commands.agent.tasks import app
from specify_cli.cli.commands.agent import tasks_move_task
from tests.mocked_env import setup_mocked_env
from tests.review import test_pre_review_gate_integration as helpers

root = Path({str(tmp_path)!r})
repo = Path({str(repo)!r})
feature_dir = root / 'kitty-specs' / helpers._MISSION
ports, _router = helpers._fake_ports(feature_dir)
with (
    setup_mocked_env(
        root,
        mission_slug=helpers._MISSION,
        target_branch='main',
        workspace_resolution=helpers._fixture_workspace(repo),
        extra_patches={{
            '_validate_ready_for_review': (True, []),
            '_check_unchecked_subtasks': [],
        }},
    ),
    patch.object(tasks_move_task, '_default_move_task_ports', return_value=ports),
):
    result = CliRunner().invoke(
        app,
        [
            'move-task', 'WP01', '--to', 'for_review',
            '--mission', helpers._MISSION, '--no-auto-commit', '--json',
        ],
    )
raise SystemExit(result.exit_code)
"""
    env = dict(os.environ)
    env["GATE_READY_FIFO"] = str(fifo_path)
    # Become a Linux child subreaper so the runner-owned pytest process is
    # attributed to and reaped by this harness after SIGKILL takes out the
    # command process that originally parented it.
    libc = ctypes.CDLL(None)
    assert libc.prctl(36, 1, 0, 0, 0) == 0
    command = subprocess.Popen(
        [sys.executable, "-c", command_script],
        cwd=Path.cwd(),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    gate_pid: int | None = None
    try:
        with fifo_path.open("r", encoding="utf-8") as ready:
            gate_pid = int(ready.readline().strip())
        os.killpg(command.pid, signal.SIGKILL)
        command.wait(timeout=5)
        os.killpg(gate_pid, signal.SIGKILL)
        reaped_pid, _status = os.waitpid(gate_pid, 0)
        assert reaped_pid == gate_pid
    finally:
        if command.poll() is None:
            command.kill()
            command.wait(timeout=5)
        if gate_pid is not None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(gate_pid, signal.SIGKILL)
            with contextlib.suppress(ChildProcessError):
                os.waitpid(gate_pid, 0)
        assert libc.prctl(36, 0, 0, 0, 0) == 0

    events_after = read_events(feature_dir)
    snapshot = materialize(feature_dir)
    assert events_after == events_before
    assert snapshot.work_packages["WP01"]["lane"] == "in_progress"
    assert snapshot.event_count == len(events_before)
    assert wp_path.read_bytes() == wp_before
