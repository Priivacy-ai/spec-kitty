"""WP01 session reaper proof (#1842, FR-001/FR-002/FR-004/FR-006, NFR-001/NFR-002).

Drives the reaper's pure, importable helpers directly — ``capture_reaper_
snapshot`` / ``reap_session_delta`` / ``sweep_tmp_residue`` /
``assert_no_leaked_test_residue`` — against a disposable ``temp_repo``
fixture (never the real REPO_ROOT), plus the actual ``pytest_sessionstart`` /
``pytest_sessionfinish`` hook functions (via duck-typed session/config test
doubles) for the controller-gate and end-to-end wiring proof.

Mutation-checkable both directions per FR-006 / SC-002:
  * a seeded ``test-feature-*`` dir + branch + git-unregistered
    ``.worktrees/`` husk are reaped;
  * a pre-existing tracked mission + real branch + registered worktree are
    NOT touched.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from runtime.next._tmp_namespace import prompt_tmp_dir
from tests import conftest as root_conftest
from tests.utils import run

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]


# ---------------------------------------------------------------------------
# Test doubles for pytest.Session / pytest.Config (controller-gate proof)
# ---------------------------------------------------------------------------


class _FakePluginManager:
    def get_plugin(self, name: str) -> object | None:
        return None


class _FakeNodeManager:
    def __init__(self, testrunuid: str) -> None:
        self.testrunuid = testrunuid


class _FakeDSession:
    def __init__(self, testrunuid: str) -> None:
        self.nodemanager = _FakeNodeManager(testrunuid)


class _TogglablePluginManager:
    """``get_plugin('dsession')`` returns the dsession only after ``activate()``.

    Mirrors the real xdist ordering: the ``NodeManager`` (and its
    ``testrunuid``) is not available at our ``pytest_sessionstart``, only later
    (by ``pytest_sessionfinish``).
    """

    def __init__(self, dsession: _FakeDSession) -> None:
        self._dsession = dsession
        self._active = False

    def activate(self) -> None:
        self._active = True

    def get_plugin(self, name: str) -> object | None:
        if name == "dsession" and self._active:
            return self._dsession
        return None


class _FakeConfig:
    def __init__(
        self,
        *,
        workerinput: dict[str, str] | None,
        pluginmanager: object | None = None,
    ) -> None:
        self.workerinput = workerinput
        # Default double has no ``dsession`` plugin (``get_plugin`` -> ``None``),
        # so ``_xdist_testrunuid`` resolves to ``None`` and only the process's
        # own ``serial-<pid>`` home is targeted. An xdist proof supplies a
        # ``_TogglablePluginManager`` instead.
        self.pluginmanager = pluginmanager if pluginmanager is not None else _FakePluginManager()

    def getoption(self, name: str, default: object | None = None) -> object | None:
        # No ``--testrunuid`` was passed in these doubles.
        return default


class _FakeSession:
    def __init__(self, config: _FakeConfig) -> None:
        self.config = config
        self.exitstatus = 0


def _controller_session() -> _FakeSession:
    return _FakeSession(_FakeConfig(workerinput=None))


def _worker_session() -> _FakeSession:
    return _FakeSession(_FakeConfig(workerinput={"testrunuid": "fake-run", "workerid": "gw0"}))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _fake_tmp_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``tempfile.gettempdir()`` for the duration of a test.

    This mission is precisely about not leaking test residue into the real
    system temp dir, so every test that exercises the temp-dir sweep (or the
    snapshot code path that reads it) gets its own disposable stand-in
    instead of touching the real, shared ``/tmp``.
    """
    fake_root = tmp_path / "fake-system-tmp"
    fake_root.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(fake_root))
    return fake_root


class _FakeAtexit:
    """Records ``register`` calls; a drop-in for the ``atexit`` module.

    Only ``root_conftest``'s own ``atexit`` reference is swapped for this, so
    the real, global ``atexit`` other code (pytest-asyncio, the runtime) relies
    on is untouched. ``register`` mirrors the real ``(func, *args, **kwargs)``
    signature and return value.
    """

    def __init__(self) -> None:
        self.registered: list[Callable[[], None]] = []

    def register(
        self, func: Callable[[], None], *args: object, **kwargs: object
    ) -> Callable[[], None]:
        self.registered.append(func)
        return func


@pytest.fixture(autouse=True)
def _captured_atexit(monkeypatch: pytest.MonkeyPatch) -> list[Callable[[], None]]:
    """Capture ``root_conftest``'s ``atexit.register`` calls, not the global one.

    ``pytest_sessionstart`` registers the N1 test-HOME reaper via
    ``atexit.register``; without this capture, every unit test that drives
    ``pytest_sessionstart`` would leak a real interpreter-exit handler pointing
    at a disposable ``tmp_path``. Autouse so no test leaks one, and returned so
    the LIFO-registration proofs can inspect what was registered. Scoped to
    ``root_conftest.atexit`` so genuine atexit registrations from other
    subsystems during the test still go to the real module.
    """
    fake = _FakeAtexit()
    monkeypatch.setattr(root_conftest, "atexit", fake)
    return fake.registered


# ---------------------------------------------------------------------------
# Git seeding helpers
# ---------------------------------------------------------------------------


def _seed_mission_dir(repo_root: Path, name: str, *, commit: bool) -> Path:
    mission_dir = repo_root / "kitty-specs" / name
    mission_dir.mkdir(parents=True)
    (mission_dir / "spec.md").write_text("seeded\n", encoding="utf-8")
    if commit:
        run(["git", "add", "kitty-specs"], cwd=repo_root)
        run(["git", "commit", "-m", f"seed {name}"], cwd=repo_root)
    return mission_dir


def _seed_branch(repo_root: Path, name: str) -> None:
    run(["git", "branch", name], cwd=repo_root)


def _seed_registered_worktree(repo_root: Path, dir_name: str, branch: str) -> Path:
    worktree_dir = repo_root / ".worktrees" / dir_name
    worktree_dir.parent.mkdir(exist_ok=True)
    run(["git", "worktree", "add", str(worktree_dir), "-b", branch], cwd=repo_root)
    return worktree_dir


def _seed_unregistered_worktree_husk(repo_root: Path, dir_name: str) -> Path:
    """A ``.worktrees/*`` directory ``git worktree add`` never created/registered."""
    husk_dir = repo_root / ".worktrees" / dir_name
    husk_dir.mkdir(parents=True)
    (husk_dir / "not-a-real-worktree.txt").write_text("husk\n", encoding="utf-8")
    return husk_dir


def _branch_exists(repo_root: Path, name: str) -> bool:
    result = run(["git", "branch", "--list", name], cwd=repo_root)
    return bool(result.stdout.strip())


def _worktree_is_registered(repo_root: Path, worktree_dir: Path) -> bool:
    result = run(["git", "worktree", "list", "--porcelain"], cwd=repo_root)
    resolved = str(worktree_dir.resolve())
    return any(line == f"worktree {resolved}" for line in result.stdout.splitlines())


# ---------------------------------------------------------------------------
# T006/T007/NFR-002 — snapshot-delta reaps new residue, preserves pre-existing
# ---------------------------------------------------------------------------


def test_snapshot_delta_reaps_new_and_preserves_preexisting(
    temp_repo: Path, _fake_tmp_root: Path
) -> None:
    repo = temp_repo

    # Pre-existing (before baseline): a real tracked mission, a real branch,
    # a REGISTERED worktree (with its own matching branch).
    _seed_mission_dir(repo, "test-feature-existing", commit=True)
    _seed_branch(repo, "kitty/mission-test-feature-existing")
    existing_worktree = _seed_registered_worktree(
        repo, "test-feature-existing-wt", "kitty/mission-test-feature-existing-wt"
    )

    baseline = root_conftest.capture_reaper_snapshot(repo)

    # New residue (after baseline) — the reaper's actual target.
    _seed_mission_dir(repo, "test-feature-new", commit=False)
    _seed_branch(repo, "kitty/mission-test-feature-new")
    new_husk = _seed_unregistered_worktree_husk(repo, "test-feature-new-husk")

    result = root_conftest.reap_session_delta(repo, baseline)

    assert result.removed_mission_dirs == ("test-feature-new",)
    assert result.removed_branches == ("kitty/mission-test-feature-new",)
    assert result.removed_worktree_dirs == ("test-feature-new-husk",)

    # New residue is actually gone from disk / git (self-heal happened).
    assert not (repo / "kitty-specs" / "test-feature-new").exists()
    assert not _branch_exists(repo, "kitty/mission-test-feature-new")
    assert not new_husk.exists()

    # Pre-existing entries are untouched (NFR-002) — both directions proven.
    assert (repo / "kitty-specs" / "test-feature-existing").exists()
    assert _branch_exists(repo, "kitty/mission-test-feature-existing")
    assert existing_worktree.exists()
    assert _worktree_is_registered(repo, existing_worktree)


def test_new_registered_worktree_is_not_reaped_only_husk_is(
    temp_repo: Path, _fake_tmp_root: Path
) -> None:
    """FR-001: only git-unregistered husks are reaped, never a real worktree.

    A worktree created via a genuine ``git worktree add`` during the session
    (e.g. another lane's in-flight work) is registered, so even though it is
    new (post-baseline) it must survive — the reaper's worktree cleanup is
    scoped to husks ``git worktree prune`` cannot see, not to "any new
    worktree".
    """
    repo = temp_repo
    baseline = root_conftest.capture_reaper_snapshot(repo)

    real_new_worktree = _seed_registered_worktree(
        repo, "test-feature-real-new", "kitty/mission-test-feature-real-new"
    )
    husk = _seed_unregistered_worktree_husk(repo, "test-feature-husk-new")

    result = root_conftest.reap_session_delta(repo, baseline)

    assert result.removed_worktree_dirs == ("test-feature-husk-new",)
    assert real_new_worktree.exists()
    assert _worktree_is_registered(repo, real_new_worktree)
    assert not husk.exists()


# ---------------------------------------------------------------------------
# T009 — reap-then-assert pollution check
# ---------------------------------------------------------------------------


def test_assert_no_leaked_test_residue_reds_on_leak() -> None:
    leaked = root_conftest.ReapResult(
        removed_mission_dirs=("test-feature-new",),
        removed_branches=(),
        removed_worktree_dirs=(),
    )
    with pytest.raises(AssertionError, match="test-feature-new"):
        root_conftest.assert_no_leaked_test_residue(leaked)


def test_assert_no_leaked_test_residue_green_when_empty() -> None:
    clean = root_conftest.ReapResult(
        removed_mission_dirs=(), removed_branches=(), removed_worktree_dirs=()
    )
    root_conftest.assert_no_leaked_test_residue(clean)  # must not raise


# ---------------------------------------------------------------------------
# T008 — temp-dir sweep (prompt delta) + N1 test-home reap (by name, atexit)
# ---------------------------------------------------------------------------


def test_sweep_tmp_residue_delta_sweeps_prompt_only_and_leaves_home(
    temp_repo: Path, _fake_tmp_root: Path
) -> None:
    """``sweep_tmp_residue`` (pytest_sessionfinish path) touches PROMPTS, not HOME.

    Decoupling regression guard: the sweep must delta-sweep the WP02 prompt
    namespace but must NEVER remove the isolated ``spec-kitty-test-homes/
    <run_uid>/`` HOME — that removal moved to an ``atexit`` handler so the
    sync/runtime shutdown callbacks (which reopen ``<HOME>/.spec-kitty/
    queue.db`` after ``pytest_sessionfinish``) don't hit a deleted DB.
    """
    homes_root = _fake_tmp_root / "spec-kitty-test-homes"
    this_run_uid_dir = homes_root / "serial-12345"
    (this_run_uid_dir / "master").mkdir(parents=True)
    (this_run_uid_dir / "master" / "queue.db").write_text("db\n", encoding="utf-8")

    prompt_dir = prompt_tmp_dir(temp_repo)
    (prompt_dir / "preexisting.md").write_text("old\n", encoding="utf-8")

    baseline = root_conftest.capture_reaper_snapshot(temp_repo)

    # This run's prompt file, written DURING the session (after the baseline).
    (prompt_dir / "this-run.md").write_text("new\n", encoding="utf-8")

    root_conftest.sweep_tmp_residue(temp_repo, baseline)

    # Prompt residue: delta-swept (this run's gone, pre-existing kept).
    assert (prompt_dir / "preexisting.md").exists()
    assert not (prompt_dir / "this-run.md").exists()
    # HOME is deliberately untouched by the sessionfinish sweep.
    assert this_run_uid_dir.exists()


def test_reap_test_home_dirs_removes_by_name_and_preserves_other_runs(
    _fake_tmp_root: Path,
) -> None:
    """N1 (FR-002/T008): the run's own ``<run_uid>`` HOME is reaped BY NAME.

    This is the extracted ``atexit`` callback's payload, tested directly.
    Red-first-meaningful: neuter ``reap_test_home_dirs`` to a no-op and the
    first assertion reds (the run's home survives). A concurrent OTHER run's
    home (a different ``<run_uid>``) is preserved — never a blanket root wipe.
    """
    homes_root = _fake_tmp_root / "spec-kitty-test-homes"

    other_run_home = homes_root / "serial-99999"
    (other_run_home / "master").mkdir(parents=True)
    (other_run_home / "master" / "queue.db").write_text("old\n", encoding="utf-8")

    this_run_uid_dir = homes_root / "serial-12345"
    (this_run_uid_dir / "master").mkdir(parents=True)
    (this_run_uid_dir / "master" / "queue.db").write_text("new\n", encoding="utf-8")

    root_conftest.reap_test_home_dirs([this_run_uid_dir])

    assert not this_run_uid_dir.exists()
    assert other_run_home.exists()


def test_reap_test_home_dirs_is_idempotent_when_already_gone(
    _fake_tmp_root: Path,
) -> None:
    """Defensive: reaping an already-removed home is a silent no-op.

    ``atexit`` may fire the handler when the dir is already gone (e.g. a prior
    sweep, or a manual clean); it must not raise at interpreter shutdown.
    """
    missing = _fake_tmp_root / "spec-kitty-test-homes" / "serial-does-not-exist"
    root_conftest.reap_test_home_dirs([missing])  # must not raise


def test_sessionstart_registers_home_reaper_atexit_and_it_reaps_by_name(
    temp_repo: Path,
    _fake_tmp_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    _captured_atexit: list[Callable[[], None]],
) -> None:
    """LIFO safety: the HOME reaper is registered at ``pytest_sessionstart``.

    Registering here — BEFORE the sync/runtime services register their own
    ``atexit`` shutdown callbacks during the tests — makes the HOME removal run
    LAST (``atexit`` is LIFO), so those callbacks complete with HOME intact.
    The captured callback, invoked here, reaps THIS run's home by name and
    preserves a concurrent OTHER run's home.
    """
    monkeypatch.setattr(root_conftest, "REPO_ROOT", temp_repo)

    homes_root = _fake_tmp_root / "spec-kitty-test-homes"
    other_run_home = homes_root / "serial-99999"
    (other_run_home / "master").mkdir(parents=True)

    session = _controller_session()
    root_conftest.pytest_sessionstart(cast(pytest.Session, session))

    # Exactly one handler registered at sessionstart (the HOME reaper).
    assert len(_captured_atexit) == 1

    # sessionstart's _worker_home_base created this run's own <run_uid> home.
    run_home = root_conftest._worker_home_base(cast(pytest.Config, session.config)).parent
    assert run_home.is_dir()

    # Firing the registered atexit callback reaps THIS run's home by name...
    _captured_atexit[0]()
    assert not run_home.exists()
    # ...while a concurrent OTHER run's home is preserved.
    assert other_run_home.exists()


def test_sessionfinish_finalizes_atexit_targets_with_xdist_testrunuid(
    temp_repo: Path,
    _fake_tmp_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    _captured_atexit: list[Callable[[], None]],
) -> None:
    """xdist: the workers' shared ``<testrunuid>`` home is added at sessionfinish.

    Regression guard for the xdist half of the atexit move: the xdist
    ``NodeManager`` that mints ``testrunuid`` is created in DSession's own
    ``pytest_sessionstart`` (order vs ours not guaranteed), so at OUR
    sessionstart only the controller's ``serial-<pid>`` home is resolvable. The
    workers' ``<testrunuid>`` home must be folded into the atexit removal set at
    ``pytest_sessionfinish`` — otherwise it leaks (one hex dir per xdist run).
    """
    monkeypatch.setattr(root_conftest, "REPO_ROOT", temp_repo)

    testrunuid = "1ff643e30c1b4cc9b99f0469d7347eef"
    pm = _TogglablePluginManager(_FakeDSession(testrunuid))
    config = _FakeConfig(workerinput=None, pluginmanager=pm)
    session = _FakeSession(config)

    homes_root = _fake_tmp_root / "spec-kitty-test-homes"
    workers_home = homes_root / testrunuid  # the workers' shared <testrunuid> home
    (workers_home / "gw0").mkdir(parents=True)
    (workers_home / "gw0" / "queue.db").write_text("worker\n", encoding="utf-8")

    # sessionstart: xdist NodeManager not yet available (dsession inactive).
    root_conftest.pytest_sessionstart(cast(pytest.Session, session))
    holder = getattr(config, root_conftest._REAPER_ATEXIT_HOMES_ATTR)
    controller_home = root_conftest._worker_home_base(cast(pytest.Config, config)).parent
    assert controller_home in holder
    assert workers_home not in holder, "testrunuid must not be resolvable yet"

    # By sessionfinish the NodeManager (testrunuid) is available.
    pm.activate()
    root_conftest.pytest_sessionfinish(cast(pytest.Session, session))

    # Both homes are now in the atexit removal set the callback closed over.
    assert controller_home in holder
    assert workers_home in holder

    # Firing the captured atexit callback reaps BOTH the controller's own home
    # AND the workers' shared <testrunuid> home.
    assert len(_captured_atexit) == 1
    _captured_atexit[0]()
    assert not controller_home.exists()
    assert not workers_home.exists()


def test_current_run_test_home_dirs_serial_targets_own_run_uid(
    _fake_tmp_root: Path,
) -> None:
    """Serial mode: the derived run-home set is exactly this process's own dir.

    Proves :func:`_current_run_test_home_dirs` keys on the run's uid via
    ``_worker_home_base(config).parent`` (a real ``serial-<pid>`` dir) rather
    than scanning the shared root — so under the real controller path the
    sweep receives the current run's home even though it predates the baseline.
    """
    config = _controller_session().config
    run_homes = root_conftest._current_run_test_home_dirs(cast(pytest.Config, config))

    expected = root_conftest._worker_home_base(cast(pytest.Config, config)).parent
    assert run_homes == frozenset({expected})
    # Serial double has no xdist dsession plugin, so no <testrunuid> dir added.
    assert all(home.parent.name == "spec-kitty-test-homes" for home in run_homes)
    assert expected.name.startswith("serial-")


def test_prompt_tmp_dir_is_the_wp02_shared_helper() -> None:
    """Guards against the reaper drifting onto a hand-copied namespace constant.

    ``getattr`` (rather than a static ``root_conftest.prompt_tmp_dir``
    attribute access) sidesteps mypy's ``--no-implicit-reexport`` strict
    check on a conftest module that is never meant to publicly re-export
    names — the identity check below is a runtime proof, not a public API.
    """
    assert getattr(root_conftest, "prompt_tmp_dir", None) is prompt_tmp_dir


# ---------------------------------------------------------------------------
# NFR-001 — controller gate + end-to-end hook wiring
# ---------------------------------------------------------------------------


def test_controller_gate_worker_never_snapshots_or_reaps(
    temp_repo: Path,
    _fake_tmp_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    _captured_atexit: list[Callable[[], None]],
) -> None:
    """A worker (``workerinput`` set) must never snapshot, register, or reap."""
    monkeypatch.setattr(root_conftest, "REPO_ROOT", temp_repo)
    worker_session = _worker_session()

    root_conftest.pytest_sessionstart(cast(pytest.Session, worker_session))
    assert (
        getattr(worker_session.config, root_conftest._REAPER_SNAPSHOT_ATTR, None) is None
    ), "a worker must never take a reaper snapshot"
    assert _captured_atexit == [], "a worker must never register the HOME reaper"

    leak = _seed_mission_dir(temp_repo, "test-feature-worker-leak", commit=False)

    root_conftest.pytest_sessionfinish(cast(pytest.Session, worker_session))

    # Nothing reaped, no exit-status flip: the worker never touched anything.
    assert leak.exists()
    assert worker_session.exitstatus == 0


def test_pytest_sessionfinish_reds_and_selfheals_on_leak(
    temp_repo: Path, _fake_tmp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(root_conftest, "REPO_ROOT", temp_repo)
    session = _controller_session()

    root_conftest.pytest_sessionstart(cast(pytest.Session, session))
    _seed_mission_dir(temp_repo, "test-feature-leak", commit=False)
    root_conftest.pytest_sessionfinish(cast(pytest.Session, session))

    # Self-healed (the checkout is not left dirty)...
    assert not (temp_repo / "kitty-specs" / "test-feature-leak").exists()
    # ...but surfaced as a red exit status instead of silently masked (T009).
    assert session.exitstatus == 1


def test_pytest_sessionfinish_stays_green_without_leak(
    temp_repo: Path, _fake_tmp_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(root_conftest, "REPO_ROOT", temp_repo)
    session = _controller_session()

    root_conftest.pytest_sessionstart(cast(pytest.Session, session))
    root_conftest.pytest_sessionfinish(cast(pytest.Session, session))

    assert session.exitstatus == 0
