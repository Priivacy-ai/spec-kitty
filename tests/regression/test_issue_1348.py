"""Regression tests for issue #1348 (T042, SC-05, SC-06, SC-11).

Issue #1348 had two symptoms:

1. **Planning artifacts land on main.**  Running a workflow command
   (``spec-kitty agent action implement WP01``) from a main checkout
   silently committed the planning artifacts (``status.events.jsonl``,
   ``status.json``, etc.) to ``main``.  Operators were left with a
   surprise commit on a protected branch.

2. **Dangling event log.**  When a tracking commit failed (e.g. a
   pre-commit hook rejected it), the append-only
   ``status.events.jsonl`` had already grown by one event but no commit
   referenced it.  The result was a dirty worktree the operator had to
   manually unwind.

Both symptoms are fixed by the new bookkeeping topology landed in this
mission:

* The pre-flight :class:`WorkflowMutationPolicy` refuses any commit
  whose destination is a protected ref **before** any disk write.
* The surgical-truncate rollback in :meth:`BookkeepingTransaction._rollback`
  restores ``status.events.jsonl`` byte-for-byte on any commit failure.

These tests pin both behaviours by exercising the actual
:class:`BookkeepingTransaction` surface in subprocesses — the same code
path the binary takes when ``spec-kitty implement`` is invoked.

We use subprocess workers (rather than calling into the transaction in
the test process) so that filesystem state and process boundaries match
what an external bug reporter would see.  Each subprocess is a clean
Python invocation against the installed package.

Spec source: FR-019, FR-020, FR-021, SC-05, SC-06, SC-11; ADR
``docs/adr/3.x/`` for the bookkeeping contract rationale.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = [pytest.mark.regression, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Constants for both scenarios
# ---------------------------------------------------------------------------

MISSION_SLUG = "regression-1348"
MID8 = "01J6BUG34"
MISSION_ID = "01J6BUG3400000000000000000"  # 26-char placeholder ULID
COORD_BRANCH = f"kitty/mission-{MISSION_SLUG}-{MID8}"
FEATURE_DIRNAME = f"{MISSION_SLUG}-{MID8}"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    )


def _init_coord_mission(repo: Path) -> None:
    """Construct the minimum post-WP03 mission topology.

    Includes meta.json with coordination_branch so the transaction
    routes to the new-topology path (not the legacy lane fallback).
    """
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "regression@example.invalid")
    _git(repo, "config", "user.name", "Regression-1348")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    _git(repo, "branch", COORD_BRANCH)

    # Mission scaffold with coordination_branch -- triggers new-topology.
    feature_dir = repo / "kitty-specs" / FEATURE_DIRNAME
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": MISSION_ID,
                "mission_slug": MISSION_SLUG,
                "mid8": MID8,
                "mission_type": "software-dev",
                "target_branch": "main",
                "coordination_branch": COORD_BRANCH,
                "created_at": "2026-05-28T00:00:00+00:00",
                "friendly_name": "Issue #1348 regression mission",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed mission scaffold")


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()  # noqa: TID251 — file-integrity checksum of read_bytes(), not charter freshness hashing


def _coord_worktree_path(repo: Path) -> Path:
    return repo / ".worktrees" / f"{FEATURE_DIRNAME}-coord"


def _events_path_under_coord(repo: Path) -> Path:
    return (
        _coord_worktree_path(repo)
        / "kitty-specs"
        / FEATURE_DIRNAME
        / "status.events.jsonl"
    )


# ---------------------------------------------------------------------------
# Subprocess driver — mirrors what ``spec-kitty implement`` does when it
# hands off to BookkeepingTransaction. The driver is intentionally minimal
# (no CLI parsing, no agent dispatch) so the regression test focuses on
# the atomicity contract that #1348 broke and this mission fixed.
# ---------------------------------------------------------------------------

_DRIVER_PROGRAM = textwrap.dedent(
    '''
    """In-process driver replicating the implement → BookkeepingTransaction
    handoff. Stdin-free; reads its config from argv.

    Exits 0 on commit success, non-zero on any failure.
    """
    import sys
    from pathlib import Path

    repo_root = Path(sys.argv[1])
    mission_id = sys.argv[2]
    mission_slug = sys.argv[3]
    mid8 = sys.argv[4]
    destination_ref = sys.argv[5]
    wp_id = sys.argv[6]

    from specify_cli.coordination.transaction import (
        BookkeepingCommitFailed,
        BookkeepingTransaction,
    )
    from specify_cli.status.emit import build_status_event

    event = build_status_event(
        mission_slug=mission_slug,
        mission_id=mission_id,
        wp_id=wp_id,
        from_lane="planned",
        to_lane="claimed",
        actor="implementer-ivan",
    )

    try:
        with BookkeepingTransaction.acquire(
            repo_root=repo_root,
            mission_id=mission_id,
            mission_slug=mission_slug,
            mid8=mid8,
            destination_ref=destination_ref,
            operation=f"regression_1348_implement_{wp_id}",
        ) as txn:
            txn.append_event(event)
            txn.commit(f"status: {wp_id} → claimed")
    except BookkeepingCommitFailed as exc:
        print(f"BookkeepingCommitFailed: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(3)

    print("ok")
    sys.exit(0)
    '''
)


def _run_driver(
    repo: Path,
    *,
    cwd: Path | None = None,
    env_extra: dict[str, str] | None = None,
    wp_id: str = "WP01",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    # Ensure the subprocess can import specify_cli from the editable
    # source tree.  pytest.ini sets ``pythonpath = src`` so the parent
    # process sees it, but child interpreters need it explicitly.
    src_path = str(Path(__file__).resolve().parents[2] / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing}" if existing else src_path
    )
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [
            sys.executable,
            "-c",
            _DRIVER_PROGRAM,
            str(repo),
            MISSION_ID,
            MISSION_SLUG,
            MID8,
            COORD_BRANCH,
            wp_id,
        ],
        cwd=str(cwd) if cwd else str(repo),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def regression_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "regression-repo"
    repo.mkdir()
    _init_coord_mission(repo)
    return repo


# ---------------------------------------------------------------------------
# Scenario A — SC-06: planning artifact does NOT land on main
# ---------------------------------------------------------------------------


def test_issue_1348_planning_artifact_does_not_land_on_main(
    regression_repo: Path,
) -> None:
    """The bookkeeping commit lands on the coordination branch, not on
    ``main``.

    Replicates the first symptom from issue #1348: running an
    implement-style workflow from the main checkout used to silently
    commit planning artifacts to ``main``.  Today's contract: the commit
    must land on the coord branch.
    """
    repo = regression_repo
    main_sha_before = _git(repo, "rev-parse", "main").stdout.strip()
    coord_sha_before = _git(repo, "rev-parse", COORD_BRANCH).stdout.strip()

    result = _run_driver(repo, cwd=repo)

    assert result.returncode == 0, (
        f"driver exited {result.returncode}; stderr={result.stderr!r}"
    )

    # 1. main has NOT advanced (the primary regression assertion).
    main_sha_after = _git(repo, "rev-parse", "main").stdout.strip()
    assert main_sha_before == main_sha_after, (
        f"Issue #1348 regression: main advanced from {main_sha_before} "
        f"to {main_sha_after}. The planning artifact commit landed on main."
    )

    # 2. The coord branch HAS advanced. The bookkeeping commit went there.
    coord_sha_after = _git(repo, "rev-parse", COORD_BRANCH).stdout.strip()
    assert coord_sha_before != coord_sha_after, (
        f"coordination branch {COORD_BRANCH} did not advance — the "
        f"transaction did not commit on the expected ref."
    )


# ---------------------------------------------------------------------------
# Scenario B — SC-05 / SC-06: forced commit failure leaves no dangling event
# ---------------------------------------------------------------------------


def _install_rejecting_pre_commit_hook(
    repo: Path,
    hooks_dir: Path,
) -> None:
    """Install a custom hooks directory whose pre-commit hook rejects every
    commit.  Applies to all worktrees through the shared git config.
    """
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    _git(repo, "config", "core.hooksPath", str(hooks_dir))


def test_issue_1348_dangling_event_log_does_not_occur(
    regression_repo: Path,
    tmp_path: Path,
) -> None:
    """SC-05 / SC-06: a forced commit failure leaves ``status.events.jsonl``
    byte-identical to its pre-emit state.

    Reproduces the second symptom from issue #1348: a rejected
    pre-commit hook used to leave the append-only event log one event
    ahead of HEAD.  Today's contract: the surgical truncate rollback in
    :meth:`BookkeepingTransaction._rollback` restores the file
    byte-for-byte.
    """
    repo = regression_repo

    # Force the BookkeepingTransaction to materialise the coord worktree
    # by running the driver once successfully, then we install the
    # failing hook and re-run with a fresh WP. This ordering matches
    # what a real operator sees: the coord worktree exists, then a
    # later commit fails inside it.
    bootstrap = _run_driver(repo, wp_id="WP00")
    assert bootstrap.returncode == 0, (
        f"bootstrap driver failed: {bootstrap.stderr!r}"
    )

    events_path = _events_path_under_coord(repo)
    assert events_path.exists(), (
        f"event log not materialised at {events_path}"
    )
    sha_before = _sha256(events_path)
    size_before = events_path.stat().st_size

    # Install the rejecting hook now.
    _install_rejecting_pre_commit_hook(repo, tmp_path / "hooks")

    # Drive a second emit — must fail loudly.
    result = _run_driver(repo, wp_id="WP01")
    assert result.returncode != 0, (
        f"forced commit failure expected, but driver succeeded; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "BookkeepingCommitFailed" in result.stderr, (
        f"expected BookkeepingCommitFailed in stderr; got {result.stderr!r}"
    )

    # Critical assertion: the event log is byte-identical.
    sha_after = _sha256(events_path)
    size_after = events_path.stat().st_size
    assert sha_after == sha_before, (
        f"Issue #1348 regression: status.events.jsonl SHA-256 changed "
        f"after a forced commit failure. before={sha_before!r} "
        f"after={sha_after!r} size_before={size_before} "
        f"size_after={size_after}"
    )


# ---------------------------------------------------------------------------
# Scenario C — SC-11: same invariants hold under the legacy fallback
# ---------------------------------------------------------------------------


def _make_legacy_mission(repo: Path) -> tuple[Path, str]:
    """Construct a pre-coord topology mission (no ``coordination_branch``).

    Returns ``(lane_worktree, lane_branch)``.
    """
    legacy_slug = f"{MISSION_SLUG}-legacy"
    legacy_mid8 = "01J6LEGAC"
    feature_dir = repo / "kitty-specs" / f"{legacy_slug}-{legacy_mid8}"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": "01J6LEGAC00000000000000000",
                "mission_slug": legacy_slug,
                "mid8": legacy_mid8,
                "mission_type": "software-dev",
                "target_branch": "main",
                # Legacy: NO coordination_branch
                "created_at": "2026-05-28T00:00:00+00:00",
                "friendly_name": "Issue #1348 legacy regression",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _git(repo, "add", "kitty-specs")
    _git(repo, "commit", "-q", "-m", "seed legacy mission")

    lane_branch = f"kitty/mission-{legacy_slug}-{legacy_mid8}-lane-a"
    _git(repo, "branch", lane_branch, "main")
    lane_worktree = repo / ".worktrees" / f"{legacy_slug}-{legacy_mid8}-lane-a"
    lane_worktree.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", str(lane_worktree), lane_branch)
    return lane_worktree, lane_branch


_LEGACY_DRIVER_PROGRAM = textwrap.dedent(
    '''
    """Legacy-mission driver. Runs in the operator's current cwd which
    must be the legacy lane worktree.
    """
    import sys
    from pathlib import Path

    repo_root = Path(sys.argv[1])
    mission_id = sys.argv[2]
    mission_slug = sys.argv[3]
    mid8 = sys.argv[4]
    destination_ref = sys.argv[5]
    wp_id = sys.argv[6]

    from specify_cli.coordination.transaction import (
        BookkeepingCommitFailed,
        BookkeepingTransaction,
    )
    from specify_cli.status.emit import build_status_event

    event = build_status_event(
        mission_slug=mission_slug,
        mission_id=mission_id,
        wp_id=wp_id,
        from_lane="planned",
        to_lane="claimed",
        actor="implementer-ivan",
    )

    try:
        with BookkeepingTransaction.acquire(
            repo_root=repo_root,
            mission_id=mission_id,
            mission_slug=mission_slug,
            mid8=mid8,
            destination_ref=destination_ref,
            operation=f"legacy_regression_implement_{wp_id}",
        ) as txn:
            txn.append_event(event)
            txn.commit(f"status: {wp_id} → claimed")
    except BookkeepingCommitFailed as exc:
        print(f"BookkeepingCommitFailed: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:  # noqa: BLE001
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(3)

    print("ok")
    sys.exit(0)
    '''
)


def test_issue_1348_legacy_mission_regression(
    regression_repo: Path,
    tmp_path: Path,
) -> None:
    """SC-11: the legacy fallback enforces the same atomicity contract.

    The pre-flight policy gate + surgical truncate rollback apply
    uniformly: a forced commit failure on a legacy mission lane leaves
    its event log byte-identical.
    """
    repo = regression_repo
    lane_worktree, lane_branch = _make_legacy_mission(repo)
    legacy_slug = f"{MISSION_SLUG}-legacy"
    legacy_mid8 = "01J6LEGAC"
    legacy_mid = "01J6LEGAC00000000000000000"

    src_path = str(Path(__file__).resolve().parents[2] / "src")
    legacy_env = os.environ.copy()
    existing = legacy_env.get("PYTHONPATH", "")
    legacy_env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing}" if existing else src_path
    )

    # Bootstrap: succeed once so the event log exists.
    bootstrap = subprocess.run(
        [
            sys.executable,
            "-c",
            _LEGACY_DRIVER_PROGRAM,
            str(repo),
            legacy_mid,
            legacy_slug,
            legacy_mid8,
            lane_branch,
            "WP00",
        ],
        cwd=str(lane_worktree),  # legacy mode requires standing in lane worktree
        env=legacy_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert bootstrap.returncode == 0, (
        f"legacy bootstrap failed: stderr={bootstrap.stderr!r}"
    )

    events_path = (
        lane_worktree
        / "kitty-specs"
        / f"{legacy_slug}-{legacy_mid8}"
        / "status.events.jsonl"
    )
    assert events_path.exists()
    sha_before = _sha256(events_path)

    # Install rejecting hook (applies to all worktrees via core.hooksPath).
    _install_rejecting_pre_commit_hook(repo, tmp_path / "hooks-legacy")

    # Drive the failing commit.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _LEGACY_DRIVER_PROGRAM,
            str(repo),
            legacy_mid,
            legacy_slug,
            legacy_mid8,
            lane_branch,
            "WP01",
        ],
        cwd=str(lane_worktree),
        env=legacy_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, (
        f"forced commit failure expected; driver succeeded. stderr={result.stderr!r}"
    )

    sha_after = _sha256(events_path)
    assert sha_after == sha_before, (
        f"SC-11 violated: legacy event log changed under forced failure. "
        f"before={sha_before!r} after={sha_after!r}"
    )
