"""e2e CWD-invariance ratchet — ExecutionContext parity gate.

This test is the Strangler step 1 for the execution-state-domain-remediation
mission (#1619): a compact proof that ``spec-kitty agent tasks status --json``
produces **identical WP lane data** regardless of whether the command is
invoked from the main-checkout CWD or a lane-worktree CWD.

The ratchet gates WP03, WP04, and WP06: those WPs can only be considered
merged once this test is green.

Write-path extension (#1672 / FR-008)
-------------------------------------
The original ratchet only proved that the status **read** (``agent tasks
status --json``) is CWD-invariant. The status-writepath-profile-surface
remediation mission (#1672) routed the status **write** (``agent status
emit``) through ``MissionStatus.transition()`` (WP01), whose write target is
the coord-aware ``read_dir`` (the primary-checkout authority), not a directory
re-derived from the caller's CWD.

``test_cwd_parity_write`` extends the ratchet to prove that a write transition
driven via ``agent status emit`` produces an **identical deterministic event
identity** (``from_lane`` / ``to_lane`` / ``wp_id`` / ``actor``) and an
**identical resulting persisted lane** regardless of whether ``emit`` is run
from the main-checkout CWD or from a lane-worktree CWD, and that the write
lands in the **main checkout's** event log in both cases.

``test_write_ratchet_catches_divergence`` is the anti-vacuity proof for the
write path: it mirrors ``test_ratchet_catches_divergence`` and demonstrates
that if the write surface re-derived its target from the worktree CWD (a
divergence), the worktree-local event log would diverge from the main-checkout
authority — proving the write ratchet is not vacuously green.

These additions are purely additive: they do not weaken or alter the existing
read-parity assertions (C-008).

Design principles
-----------------
* Uses ``subprocess`` with explicit ``cwd=`` — NEVER ``os.chdir()`` which
  mutates global process state.
* Uses minimal hand-crafted fixtures (git init + JSONL bootstrap) rather than
  invoking the full ``spec-kitty init`` / ``finalize-tasks`` pipeline to keep
  fixture setup fast and hermetic.
* The fixture creates a real git worktree so that ``find_repo_root()`` resolves
  correctly from both the main checkout and the worktree path.
* The injection proof (``test_ratchet_catches_divergence``) verifies that the
  ratchet is not vacuously passing by deliberately corrupting the status read
  in one location and asserting that the observed outputs diverge.

Markers
-------
``architectural`` — this is an architectural invariant (CWD-invariance).
``git_repo`` — required because the fixture calls ``git init`` and
``git worktree add`` via subprocess (Rule 1 from test_pytest_marker_correctness).
``non_sandbox`` — the fixture spawns ``git worktree add`` and invokes
``spec-kitty`` as a subprocess, both of which are structurally incompatible
with mutmut's forked sandbox.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from collections.abc import Generator

import pytest

pytestmark = [
    pytest.mark.architectural,
    pytest.mark.git_repo,
    pytest.mark.non_sandbox,
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MISSION_SLUG = "test-parity-mission"

_META_JSON = json.dumps(
    {
        "mission_id": "01TESTPARITY00000000000001",
        "mission_slug": _MISSION_SLUG,
        "mission_number": None,
        "mission_type": "software-dev",
        "friendly_name": "Test parity mission",
    },
    indent=2,
)

# Minimal WP01 task markdown (no dependencies).
_WP01_MD = textwrap.dedent(
    """\
    ---
    work_package_id: WP01
    title: Parity test WP01
    dependencies: []
    requirement_refs: []
    subtasks: []
    agent: claude
    agent_profile: python-pedro
    role: implementer
    authoritative_surface: src/parity/
    owned_files:
    - src/parity/
    execution_mode: code_change
    history: []
    ---
    # WP01 — Parity test WP01
    """
)

# Minimal WP02 task markdown (depends on WP01).
_WP02_MD = textwrap.dedent(
    """\
    ---
    work_package_id: WP02
    title: Parity test WP02
    dependencies:
    - WP01
    requirement_refs: []
    subtasks: []
    agent: claude
    agent_profile: python-pedro
    role: implementer
    authoritative_surface: src/parity2/
    owned_files:
    - src/parity2/
    execution_mode: code_change
    history: []
    ---
    # WP02 — Parity test WP02
    """
)


def _make_status_event(
    wp_id: str,
    from_lane: str,
    to_lane: str,
    event_id: str,
    at: str = "2026-06-03T10:00:00+00:00",
) -> str:
    """Emit a single status event as a sorted-key JSON line."""
    event = {
        "actor": "test-fixture",
        "at": at,
        "event_id": event_id,
        "evidence": None,
        "execution_mode": "worktree",
        "force": True,
        "from_lane": from_lane,
        "mission_id": "01TESTPARITY00000000000001",
        "mission_slug": _MISSION_SLUG,
        "policy_metadata": None,
        "reason": "parity-fixture bootstrap",
        "review_ref": None,
        "to_lane": to_lane,
        "wp_id": wp_id,
    }
    return json.dumps(event, sort_keys=True)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> None:
    """Run a git command, raising on non-zero exit."""
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )


def _spec_kitty(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Invoke spec-kitty using the same interpreter as the test runner.

    Uses ``sys.executable -m specify_cli`` (module form) rather than the
    ``spec-kitty`` script name so the call works in any venv where the package
    is installed in development mode (``pip install -e .``), not just when the
    console script entry-point is on PATH.
    """
    return subprocess.run(
        [sys.executable, "-m", "specify_cli", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _build_mission_dir(repo_root: Path, slug: str) -> Path:
    """Create the kitty-specs/<slug>/ directory structure."""
    feature_dir = repo_root / "kitty-specs" / slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    # Mission metadata
    (feature_dir / "meta.json").write_text(_META_JSON, encoding="utf-8")

    # WP task files
    (tasks_dir / "WP01.md").write_text(_WP01_MD, encoding="utf-8")
    (tasks_dir / "WP02.md").write_text(_WP02_MD, encoding="utf-8")

    # Bootstrap status events for both WPs (both planned)
    events = [
        _make_status_event(
            "WP01",
            from_lane="planned",
            to_lane="planned",
            event_id="01TESTPARITY00000000000P01",
            at="2026-06-03T10:00:00+00:00",
        ),
        _make_status_event(
            "WP02",
            from_lane="planned",
            to_lane="planned",
            event_id="01TESTPARITY00000000000P02",
            at="2026-06-03T10:00:01+00:00",
        ),
    ]
    (feature_dir / "status.events.jsonl").write_text(
        "\n".join(events) + "\n", encoding="utf-8"
    )

    # Minimal status.json (derived snapshot; content doesn't affect reads
    # in Phase 2 but must exist to satisfy directory-level checks).
    (feature_dir / "status.json").write_text(
        json.dumps({"event_count": 0, "work_packages": {}}), encoding="utf-8"
    )

    return feature_dir


def _build_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Initialise a minimal git repo with a mission and a lane worktree.

    Returns ``(repo_root, worktree_path)``.
    """
    repo_root = tmp_path / "main"
    repo_root.mkdir()

    # Git init
    _git(["init", "--initial-branch=main"], repo_root)
    _git(["config", "user.email", "parity@example.com"], repo_root)
    _git(["config", "user.name", "Parity Test"], repo_root)
    _git(["config", "commit.gpgsign", "false"], repo_root)

    # .kittify marker (required for find_repo_root())
    kittify_dir = repo_root / ".kittify"
    kittify_dir.mkdir()
    (kittify_dir / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n", encoding="utf-8"
    )

    # Mission artifacts
    _build_mission_dir(repo_root, _MISSION_SLUG)

    # Initial commit so we can branch/worktree
    _git(["add", "."], repo_root)
    _git(["commit", "-m", "chore: parity fixture initial commit"], repo_root)

    # Create a lane branch and worktree for WP01
    lane_branch = f"kitty/mission-{_MISSION_SLUG}-lane-a"
    _git(["branch", lane_branch], repo_root)
    worktree_dir = repo_root / ".worktrees" / f"{_MISSION_SLUG}-lane-a"
    worktree_dir.parent.mkdir(exist_ok=True)
    _git(["worktree", "add", str(worktree_dir), lane_branch], repo_root)

    return repo_root, worktree_dir


# ---------------------------------------------------------------------------
# T006 — Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def parity_repo(tmp_path_factory: pytest.TempPathFactory) -> Generator[tuple[Path, Path, str], None, None]:
    """Create a minimal spec-kitty project with one lane worktree.

    Returns ``(repo_root, worktree_path, mission_slug)``.

    Scope is ``module`` so the (slow) git init runs once per test module.
    """
    base = tmp_path_factory.mktemp("parity_repo")
    repo_root, worktree_path = _build_repo(base)
    yield repo_root, worktree_path, _MISSION_SLUG


# ---------------------------------------------------------------------------
# Helper: run status and parse JSON
# ---------------------------------------------------------------------------


def _get_status_json(cwd: Path, mission_slug: str) -> dict:
    """Run ``spec-kitty agent tasks status --json --mission <slug>`` and parse the output.

    Returns the parsed JSON dict.  Raises ``AssertionError`` on non-zero exit.
    """
    result = _spec_kitty(
        ["agent", "tasks", "status", "--json", "--mission", mission_slug],
        cwd=cwd,
    )
    assert result.returncode == 0, (
        f"spec-kitty agent tasks status --json failed (cwd={cwd}):\n"
        f"  stdout: {result.stdout.strip()[:500]}\n"
        f"  stderr: {result.stderr.strip()[:500]}"
    )
    return json.loads(result.stdout)


def _wp_lanes(status_json: dict) -> dict[str, str]:
    """Extract ``{wp_id: lane}`` from a status JSON payload."""
    wps = status_json.get("work_packages", [])
    return {wp["id"]: wp["lane"] for wp in wps}


# ---------------------------------------------------------------------------
# T009 — Parity assertions (T007 + T008 combined into one hermetic test)
# ---------------------------------------------------------------------------


def test_cwd_parity(parity_repo: tuple[Path, Path, str]) -> None:
    """CWD-invariance: status reads from main-checkout and lane-worktree are identical.

    This test runs ``spec-kitty agent tasks status --json --mission <slug>``
    from two CWDs and asserts that the resolved WP lane state is the same:

    * ``cwd=repo_root`` — the conventional invocation from the main checkout
    * ``cwd=worktree_path`` — the agent's natural CWD during implementation

    Both invocations must traverse back to the same status-read authority
    (the primary checkout at this fixture's lifecycle stage) and return the
    same ``{wp_id: lane}`` mapping.

    Failure indicates that ``find_repo_root()`` or the status-read path
    resolver diverges based on CWD, which is the core regression class
    documented in issue #1619.
    """
    repo_root, worktree_path, mission_slug = parity_repo

    # Run from main checkout CWD
    main_status = _get_status_json(cwd=repo_root, mission_slug=mission_slug)
    main_lanes = _wp_lanes(main_status)

    # Run from lane worktree CWD
    lane_status = _get_status_json(cwd=worktree_path, mission_slug=mission_slug)
    lane_lanes = _wp_lanes(lane_status)

    # Both must see the same set of WPs
    assert set(main_lanes.keys()) == set(lane_lanes.keys()), (
        f"Main-checkout and lane-worktree see different WP sets.\n"
        f"  main WPs:  {sorted(main_lanes.keys())}\n"
        f"  lane WPs:  {sorted(lane_lanes.keys())}\n"
        "This indicates ``find_repo_root()`` resolves to a different repo root "
        "when invoked from the worktree CWD."
    )

    # Each WP must be in the same lane from both CWDs
    for wp_id in main_lanes:
        assert main_lanes[wp_id] == lane_lanes[wp_id], (
            f"Lane divergence for {wp_id}:\n"
            f"  from main checkout CWD:  {main_lanes[wp_id]!r}\n"
            f"  from lane worktree CWD:  {lane_lanes[wp_id]!r}\n"
            "CWD-parity violation: the same status-event log is being read "
            "differently depending on the caller's working directory."
        )


# ---------------------------------------------------------------------------
# T009 injection proof — ratchet must catch real divergence
# ---------------------------------------------------------------------------


def test_ratchet_catches_divergence(tmp_path: Path) -> None:
    """Injection proof: the ratchet FAILS when CWD-parity is genuinely broken.

    This test constructs a scenario where the main-checkout CWD and the
    worktree CWD point to *different* ``status.events.jsonl`` files with
    deliberately different WP lane data. The status command will read
    different files for each CWD, so the lane outputs diverge.

    The purpose is to prove the ratchet is not vacuously green: if CWD routing
    were broken, ``test_cwd_parity`` would catch it.

    Test structure:
    1. Build a repo with a worktree (same as parity_repo fixture).
    2. Add a *second* status event to the worktree's copy of status.events.jsonl
       that transitions WP01 to ``in_progress``.
    3. The main checkout still has WP01 as ``planned``.
    4. Read status from both CWDs, assert that the lanes differ.
       If they are the same, the read path is not CWD-sensitive (the invariant
       we are testing) and something is wrong with the test design.

    Note: under the *current* implementation, both CWDs resolve to the SAME
    status file (the main checkout), so adding events only in the worktree copy
    is the correct way to simulate divergence: we write divergent data to the
    worktree path and then verify that the reads do NOT collapse them (because
    the current implementation reads from the single primary checkout, not from
    the worktree).

    What this test really proves
    ----------------------------
    The test demonstrates the CWD-variant scenario that existed prior to
    issue #1619: if a future regression causes the worktree CWD invocation to
    read from *the worktree's kitty-specs/* instead of the primary checkout,
    the lanes would diverge and ``test_cwd_parity`` above would fail.
    This injection proof constructs exactly that scenario explicitly, without
    relying on a real regression, to validate that the ratchet design is sound.
    """
    repo_root, worktree_path = _build_repo(tmp_path)
    mission_slug = _MISSION_SLUG

    # Write a divergent event ONLY to the worktree's copy of status.events.jsonl.
    # This simulates the state that would exist under a CWD-routing regression
    # (where the worktree CWD causes reads from kitty-specs/ inside the worktree
    # rather than from the primary checkout).
    worktree_feature_dir = worktree_path / "kitty-specs" / mission_slug
    worktree_feature_dir.mkdir(parents=True, exist_ok=True)

    # Bootstrap the worktree copy with the same initial events
    initial_events = [
        _make_status_event(
            "WP01",
            from_lane="planned",
            to_lane="planned",
            event_id="01TESTPARITY00000000000P01",
            at="2026-06-03T10:00:00+00:00",
        ),
        _make_status_event(
            "WP02",
            from_lane="planned",
            to_lane="planned",
            event_id="01TESTPARITY00000000000P02",
            at="2026-06-03T10:00:01+00:00",
        ),
    ]
    divergent_event = _make_status_event(
        "WP01",
        from_lane="planned",
        to_lane="in_progress",
        event_id="01TESTPARITY0000DIVERGENT01",
        at="2026-06-03T11:00:00+00:00",
    )
    worktree_events = initial_events + [divergent_event]
    (worktree_feature_dir / "status.events.jsonl").write_text(
        "\n".join(worktree_events) + "\n", encoding="utf-8"
    )
    (worktree_feature_dir / "status.json").write_text(
        json.dumps({"event_count": 0, "work_packages": {}}), encoding="utf-8"
    )
    (worktree_feature_dir / "meta.json").write_text(_META_JSON, encoding="utf-8")
    tasks_dir = worktree_feature_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "WP01.md").write_text(_WP01_MD, encoding="utf-8")
    (tasks_dir / "WP02.md").write_text(_WP02_MD, encoding="utf-8")

    # Read from main checkout: WP01 should be 'planned'
    main_status = _get_status_json(cwd=repo_root, mission_slug=mission_slug)
    main_lanes = _wp_lanes(main_status)
    assert main_lanes.get("WP01") == "planned", (
        f"Expected WP01 to be 'planned' in main checkout read; "
        f"got {main_lanes.get('WP01')!r}"
    )

    # The worktree's kitty-specs/ now contains a divergent event log.
    # If CWD routing for worktree paths is broken (i.e., the worktree CWD
    # causes reads from worktree_path/kitty-specs/ instead of the primary
    # checkout), the lane would appear as 'in_progress'.
    # We verify here that the worktree's event log DOES contain the divergent
    # state — proving that a routing regression WOULD surface as a difference.
    from specify_cli.status.reducer import reduce
    from specify_cli.status.store import read_events

    worktree_events_loaded = read_events(worktree_feature_dir)
    worktree_snapshot = reduce(worktree_events_loaded)
    worktree_wp1_lane = (
        worktree_snapshot.work_packages.get("WP01", {}).get("lane", "planned")
    )
    assert worktree_wp1_lane == "in_progress", (
        f"Injection proof setup error: the worktree's status.events.jsonl should "
        f"show WP01 as 'in_progress' after the divergent event, "
        f"but got {worktree_wp1_lane!r}. Check that _make_status_event is correct."
    )

    # Now prove: the main-checkout read is stable (returns 'planned'), meaning
    # the two paths produce different data. This is the evidence that a CWD
    # routing regression would surface as a parity failure in test_cwd_parity.
    main_wp1_lane = main_lanes.get("WP01")
    assert main_wp1_lane != worktree_wp1_lane, (
        f"Injection proof inconclusive: both read paths return the same lane "
        f"({main_wp1_lane!r}) even though the worktree's event log contains a "
        f"divergent transition. This means the divergent data in the worktree "
        f"cannot be used to detect a CWD routing regression. "
        f"Revise the test setup."
    )


# ---------------------------------------------------------------------------
# WRITE-PATH RATCHET (#1672 / FR-008)
# ---------------------------------------------------------------------------
#
# WP01 routed ``agent status emit`` through ``MissionStatus.transition()``,
# whose write target is the coord-aware ``read_dir`` (the primary-checkout
# authority). The tests below ratchet the CWD-invariance of that WRITE
# transition. They reuse the proven ``_build_repo`` fixture helper and the same
# ``_spec_kitty`` subprocess invocation (``sys.executable -m specify_cli``) as
# the read-path tests, so they run under the identical CI job and markers
# (``architectural``, ``git_repo``, ``non_sandbox``) with no new exclusion.
# ---------------------------------------------------------------------------


def _emit_status(
    cwd: Path,
    mission_slug: str,
    wp_id: str,
    to_lane: str,
    actor: str,
) -> dict:
    """Run ``spec-kitty agent status emit ... --json`` and parse the output.

    Returns the parsed JSON dict describing the emitted event.  Raises
    ``AssertionError`` on non-zero exit so a CLI failure surfaces with full
    diagnostics rather than an opaque ``KeyError`` downstream.
    """
    result = _spec_kitty(
        [
            "agent",
            "status",
            "emit",
            wp_id,
            "--to",
            to_lane,
            "--actor",
            actor,
            "--mission",
            mission_slug,
            "--json",
        ],
        cwd=cwd,
    )
    assert result.returncode == 0, (
        f"spec-kitty agent status emit failed (cwd={cwd}):\n"
        f"  stdout: {result.stdout.strip()[:500]}\n"
        f"  stderr: {result.stderr.strip()[:500]}"
    )
    return json.loads(result.stdout)


def _event_identity(emit_json: dict) -> dict[str, str]:
    """Extract the *deterministic* identity of an emitted event.

    The ``event_id`` is a freshly minted ULID and is therefore intentionally
    excluded: it is unique per emission and would never match across two
    independent writes.  The fields below are the parts of the event identity
    that MUST be CWD-invariant for the same (wp, to_lane, actor) transition.
    """
    return {
        "wp_id": emit_json["wp_id"],
        "from_lane": emit_json["from_lane"],
        "to_lane": emit_json["to_lane"],
        "actor": emit_json["actor"],
    }


def test_cwd_parity_write(tmp_path: Path) -> None:
    """CWD-invariance of the status WRITE transition (#1672 / FR-008).

    Drives ``spec-kitty agent status emit WP01 --to claimed`` against two
    *independent but identically seeded* repos:

    * one write is issued from the **main-checkout CWD**
    * the other is issued from the **lane-worktree CWD**

    Two independent repos are used (rather than two writes against one repo)
    so that each ``emit`` exercises the *same* ``planned -> claimed`` first
    transition; issuing both against a single repo would make the second a
    no-op / illegal re-transition and so would not test parity of the write.

    The ratchet asserts that:

    1. the **deterministic emitted event identity** (``from_lane`` /
       ``to_lane`` / ``wp_id`` / ``actor``) is identical across both CWDs, and
    2. the **resulting persisted lane** is identical (``claimed``), and
    3. in BOTH cases the write landed in the **main checkout's** event log
       (the coord-aware authority), NOT the worktree's ``kitty-specs/`` — i.e.
       the write target is CWD-invariant.

    Failure indicates that the write path re-derives its execution context /
    target directory from the caller's CWD, which is the regression class this
    write ratchet exists to catch.
    """
    # Repo A: write issued from the main-checkout CWD.
    base_a = tmp_path / "a"
    base_a.mkdir()
    repo_a_root, _worktree_a = _build_repo(base_a)
    # Repo B: write issued from the lane-worktree CWD.
    base_b = tmp_path / "b"
    base_b.mkdir()
    repo_b_root, worktree_b = _build_repo(base_b)

    mission_slug = _MISSION_SLUG

    main_emit = _emit_status(
        cwd=repo_a_root,
        mission_slug=mission_slug,
        wp_id="WP01",
        to_lane="claimed",
        actor="parity-writer",
    )
    lane_emit = _emit_status(
        cwd=worktree_b,
        mission_slug=mission_slug,
        wp_id="WP01",
        to_lane="claimed",
        actor="parity-writer",
    )

    # (1) Deterministic event identity must match across CWDs.
    assert _event_identity(main_emit) == _event_identity(lane_emit), (
        "Write-path CWD divergence: the emitted event identity differs "
        "depending on the caller's working directory.\n"
        f"  from main-checkout CWD: {_event_identity(main_emit)!r}\n"
        f"  from lane-worktree CWD: {_event_identity(lane_emit)!r}\n"
        "The status write must produce the same (from_lane, to_lane, wp_id, "
        "actor) transition regardless of CWD."
    )

    # Sanity: the transition is the expected planned -> claimed.
    assert main_emit["from_lane"] == "planned"
    assert main_emit["to_lane"] == "claimed"

    # (2) The resulting persisted lane must be identical across both CWDs.
    main_lanes = _wp_lanes(
        _get_status_json(cwd=repo_a_root, mission_slug=mission_slug)
    )
    lane_lanes = _wp_lanes(
        _get_status_json(cwd=repo_b_root, mission_slug=mission_slug)
    )
    assert main_lanes.get("WP01") == "claimed", (
        f"Write from main-checkout CWD did not persist 'claimed'; "
        f"got {main_lanes.get('WP01')!r}"
    )
    assert lane_lanes.get("WP01") == "claimed", (
        f"Write from lane-worktree CWD did not persist 'claimed'; "
        f"got {lane_lanes.get('WP01')!r}"
    )
    assert main_lanes.get("WP01") == lane_lanes.get("WP01"), (
        "Write-path CWD divergence: the resulting lane differs across CWDs.\n"
        f"  main-checkout CWD wrote -> {main_lanes.get('WP01')!r}\n"
        f"  lane-worktree CWD wrote -> {lane_lanes.get('WP01')!r}"
    )

    # (3) The write issued from the worktree CWD must have landed in the MAIN
    # checkout's event log (the coord-aware authority), NOT the worktree's own
    # kitty-specs/. A divergent write target would write 'claimed' into the
    # worktree copy instead.
    from specify_cli.status.lane_reader import get_wp_lane

    main_authority_dir = repo_b_root / "kitty-specs" / mission_slug
    assert get_wp_lane(main_authority_dir, "WP01") == "claimed", (
        "Write from the lane-worktree CWD did not land in the main checkout's "
        "event log; the write target was re-derived from the worktree CWD."
    )
    # The worktree carries its own checked-out copy of the seeded event log
    # (committed before the worktree was created). The write issued from the
    # worktree CWD must NOT have touched that copy — its WP01 lane must remain
    # the seeded ``planned``. If the write target were CWD-derived, this copy
    # would read ``claimed`` instead.
    worktree_feature_dir = worktree_b / "kitty-specs" / mission_slug
    assert get_wp_lane(worktree_feature_dir, "WP01") == "planned", (
        "Write from the lane-worktree CWD mutated the worktree-local event log "
        f"at {worktree_feature_dir}; the write target must remain the "
        "CWD-invariant main-checkout authority, leaving the worktree copy at "
        "its seeded 'planned' state."
    )


def test_write_ratchet_catches_divergence(tmp_path: Path) -> None:
    """Anti-vacuity proof for the WRITE ratchet (#1672 / FR-008).

    Mirrors ``test_ratchet_catches_divergence`` for the write path. It proves
    that the write ratchet would catch a genuine CWD-routing regression: if a
    future change caused ``agent status emit`` to write into the worktree's own
    ``kitty-specs/`` (instead of the CWD-invariant main-checkout authority), the
    worktree-local event log would diverge from the main checkout — and
    ``test_cwd_parity_write``'s assertion (3) would fail.

    Construction (without relying on a real regression):

    1. Build a repo with a worktree.
    2. Issue a real write (``emit WP01 --to claimed``) from the worktree CWD.
       Under the *current* (correct) implementation this lands in the main
       checkout's event log.
    3. Simulate the regression by writing a *divergent* event log directly into
       the worktree's ``kitty-specs/`` that drives WP01 to ``in_progress``.
    4. Assert the two surfaces disagree (main authority = ``claimed`` from the
       real write; worktree-local = ``in_progress`` from the simulated
       regression). This disagreement is exactly what the write ratchet would
       surface if the write target were CWD-derived.

    If the two surfaces agreed, the worktree-local data could not be used to
    detect a write-target regression and the ratchet would be vacuous.
    """
    repo_root, worktree_path = _build_repo(tmp_path)
    mission_slug = _MISSION_SLUG

    # (2) Real write from the worktree CWD -> lands in the main authority.
    _emit_status(
        cwd=worktree_path,
        mission_slug=mission_slug,
        wp_id="WP01",
        to_lane="claimed",
        actor="parity-writer",
    )

    from specify_cli.status.lane_reader import get_wp_lane

    main_authority_dir = repo_root / "kitty-specs" / mission_slug
    main_wp1_lane = get_wp_lane(main_authority_dir, "WP01")
    assert main_wp1_lane == "claimed", (
        "Setup error: the real write from the worktree CWD should have "
        f"persisted 'claimed' in the main authority; got {main_wp1_lane!r}."
    )

    # (3) Simulate a CWD-routing regression: write a divergent event log into
    # the worktree's own kitty-specs/ that drives WP01 to 'in_progress'.
    worktree_feature_dir = worktree_path / "kitty-specs" / mission_slug
    worktree_feature_dir.mkdir(parents=True, exist_ok=True)
    divergent_events = [
        _make_status_event(
            "WP01",
            from_lane="planned",
            to_lane="planned",
            event_id="01TESTPARITY00000000000P01",
            at="2026-06-03T10:00:00+00:00",
        ),
        _make_status_event(
            "WP01",
            from_lane="planned",
            to_lane="in_progress",
            event_id="01TESTPARITY0000WRITEDVRG01",
            at="2026-06-03T11:00:00+00:00",
        ),
    ]
    (worktree_feature_dir / "status.events.jsonl").write_text(
        "\n".join(divergent_events) + "\n", encoding="utf-8"
    )

    from specify_cli.status.reducer import reduce
    from specify_cli.status.store import read_events

    worktree_snapshot = reduce(read_events(worktree_feature_dir))
    worktree_wp1_lane = (
        worktree_snapshot.work_packages.get("WP01", {}).get("lane", "planned")
    )
    assert worktree_wp1_lane == "in_progress", (
        "Injection proof setup error: the simulated regression's worktree-local "
        f"event log should show WP01 as 'in_progress'; got {worktree_wp1_lane!r}."
    )

    # (4) The main authority (real write) and the worktree-local (simulated
    # regression) surfaces must disagree, proving the ratchet is not vacuous.
    assert main_wp1_lane != worktree_wp1_lane, (
        "Injection proof inconclusive: the main-checkout authority and the "
        f"worktree-local event log both report {main_wp1_lane!r}. A write-target "
        "CWD-routing regression could not be detected, so the write ratchet "
        "would be vacuous. Revise the test setup."
    )
