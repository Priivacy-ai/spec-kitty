from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from collections.abc import Callable, Iterator

import pytest
import yaml
from filelock import FileLock, Timeout

from tests._support.quarantine import (
    QUARANTINE_MARKER,
    quarantine_opted_in,
    quarantine_skip_mark,
)
from tests._support.wall_clock_assertions import (
    find_wall_clock_assertion_violations,
    find_test_python_paths,
    format_wall_clock_assertion_violations,
)
from tests.branch_contract import IS_2X_BRANCH
from tests.mutmut_env import prepare_mutants_environment_from_cwd
from tests.test_isolation_helpers import get_installed_version
from tests.utils import REPO_ROOT, run, write_wp

# ---------------------------------------------------------------------------
# WP04 — Per-worker HOME and state isolation (master enabler, FR-002)
#
# Every pytest worker (and the serial "master" run) gets its OWN home / config
# / state directory so that parallel workers never share or truncate the real
# ``~/.spec-kitty/queue.db``. The existing intra-worker queue-wipe fixtures
# (``reset_spec_kitty_queue_state`` / ``tests/agent/conftest.py``) keep working;
# they simply operate against the isolated home once ``Path.home`` is patched.
#
# Two layers are required:
#   1. ``pytest_configure`` sets the HOME/XDG env vars *before collection* so
#      that modules which bind a home-derived path at import time (e.g.
#      ``specify_cli.sync.daemon.SPEC_KITTY_DIR = Path.home() / ".spec-kitty"``
#      at module top level, ``daemon.py:94``) resolve into the isolated home.
#   2. An autouse, function-scoped fixture re-asserts the ``Path.home``
#      monkeypatch + env for every test, keyed by worker id, so call-time
#      ``Path.home()`` reads are isolated too. Never session-only: a single
#      shared session home would re-collide every worker and re-introduce the
#      exact hazard this WP removes.
# ---------------------------------------------------------------------------

# Cross-platform home/state env vars (C-005). ``Path.home()`` itself resolves
# ``USERPROFILE`` on Windows and ``HOME`` on POSIX; the XDG vars cover helpers
# that read the environment directly.
_HOME_ENV_VARS = ("HOME", "USERPROFILE")
_XDG_ENV_SUBDIRS = {
    "XDG_CONFIG_HOME": ".config",
    "XDG_DATA_HOME": ".local/share",
    "XDG_STATE_HOME": ".local/state",
    "LOCALAPPDATA": "AppData/Local",
}
_REAL_HOME_ENV_VAR = "SPEC_KITTY_REAL_HOME_FOR_TESTS"
# Stash the resolved per-worker home base on the pytest Config so the autouse
# fixture reuses the *same* directory the import-time env setup pointed at.
_WORKER_HOME_CONFIG_ATTR = "_spec_kitty_worker_home"


def _worker_id(config: pytest.Config) -> str:
    """Return the xdist worker id (e.g. ``gw0``), or ``"master"`` when serial.

    ``config.workerinput`` is present only inside xdist worker subprocesses;
    the controller / serial process has no such attribute.
    """
    workerinput = getattr(config, "workerinput", None)
    if workerinput is None:
        return "master"
    return str(workerinput.get("workerid", "master"))


def _worker_home_base(config: pytest.Config) -> Path:
    """Resolve (and cache on *config*) this worker's isolated home base dir.

    The base is namespaced by the xdist ``testrunuid`` (shared across all
    workers of one run, distinct between runs) or, for non-xdist serial runs, a
    process-scoped run id, and by the worker id, so:
      * two workers in the same run get *distinct* homes (no collision), and
      * successive pytest invocations do not reuse stale serial-home state, and
      * the directory is stable for the lifetime of the process, which lets the
        import-time env setup and the autouse fixture agree on one location.
    """
    cached = getattr(config, _WORKER_HOME_CONFIG_ATTR, None)
    if cached is not None:
        return Path(cached)

    workerinput = getattr(config, "workerinput", None)
    run_uid = f"serial-{os.getpid()}"
    if workerinput is not None:
        run_uid = str(workerinput.get("testrunuid", "serial"))
    base = (
        Path(tempfile.gettempdir())
        / "spec-kitty-test-homes"
        / run_uid
        / _worker_id(config)
    )
    base.mkdir(parents=True, exist_ok=True)
    setattr(config, _WORKER_HOME_CONFIG_ATTR, str(base))
    return base


def _apply_home_env(home_base: Path) -> None:
    """Point the HOME/XDG/AppData env vars at *home_base* (mutates os.environ).

    Used by ``pytest_configure`` (process-wide, before collection) so import-
    time home-derived reads land in the isolated home. The autouse fixture
    re-applies the same mapping via ``monkeypatch`` for per-test safety.
    """
    home_base.mkdir(parents=True, exist_ok=True)
    for var in _HOME_ENV_VARS:
        os.environ[var] = str(home_base)
    for var, subdir in _XDG_ENV_SUBDIRS.items():
        target = home_base / subdir
        target.mkdir(parents=True, exist_ok=True)
        os.environ[var] = str(target)

# ---------------------------------------------------------------------------
# Concurrency-safe test-venv creation (FR-003, FR-004)
# A shared venv at .pytest_cache/spec-kitty-test-venv is created once and
# reused across all pytest invocations.  When contract + architectural gates
# run in parallel both processes may observe the venv as missing at the same
# instant and race to create it.  A file lock serializes the create-or-validate
# phase so only one process builds the venv; the second acquires the lock,
# finds a valid venv, and skips creation entirely.
# ---------------------------------------------------------------------------

_VENV_CACHE_PATH = Path(".pytest_cache/spec-kitty-test-venv")
_VENV_LOCK_PATH = Path(".pytest_cache/spec-kitty-test-venv.lock")
_LOCK_TIMEOUT_S = 60.0


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register pytest-asyncio ini keys for environments without the plugin."""
    parser.addini("asyncio_mode", "pytest-asyncio compatibility option")
    parser.addini(
        "asyncio_default_fixture_loop_scope",
        "pytest-asyncio compatibility option",
    )


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault(_REAL_HOME_ENV_VAR, str(Path.home()))

    # WP04: isolate this worker's home BEFORE collection so modules that bind a
    # home-derived path at import time (e.g. ``daemon.SPEC_KITTY_DIR`` at
    # ``daemon.py:94``) resolve into the per-worker isolated home, never the
    # developer's real ``~/.spec-kitty``. The autouse fixture below re-applies
    # the same mapping per test for call-time reads.
    _apply_home_env(_worker_home_base(config))

    try:
        prepare_mutants_environment_from_cwd()
    except OSError as exc:
        import warnings
        warnings.warn(f"Failed to prepare mutants environment: {exc}", stacklevel=1)

    # HARDCODED: Never open browser windows during tests.
    # Propagates to subprocesses too (e.g. dashboard CLI spawned by tests).
    os.environ["PWHEADLESS"] = "1"

    # Block webbrowser.open() in the test process itself.
    import webbrowser

    webbrowser.open = lambda *args, **kwargs: None  # type: ignore[assignment]
    webbrowser.open_new = lambda *args, **kwargs: None  # type: ignore[assignment]
    webbrowser.open_new_tab = lambda *args, **kwargs: None  # type: ignore[assignment]

    config.addinivalue_line(
        "markers",
        "adversarial: adversarial scenarios for merge and dependency handling",
    )
    config.addinivalue_line(
        "markers",
        "real_worktree_detection: opt out of autouse worktree detection neutralization",
    )
    config.addinivalue_line(
        "markers",
        "architectural: Architectural enforcement tests (layer rules, import-graph invariants)",
    )
    config.addinivalue_line(
        "markers",
        "windows_ci: Tests that require a native win32 environment — auto-skipped on non-Windows",
    )
    # NOTE: the ``quarantine`` marker is registered canonically in pytest.ini
    # (the single marker source of truth, #2034), which is sufficient for
    # ``--strict-markers``. The collection chokepoint below is the enforcement
    # mechanism (env-gated skip); it does not require a second registration here.


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skip_windows = pytest.mark.skip(reason="windows_ci: requires sys.platform == 'win32'")
    # Quarantine chokepoint (single, un-bypassable). Per the flakiness policy a
    # quarantined test is held out of every normal/blocking run so it can never
    # turn main red or block an unrelated PR; the non-blocking quarantine-
    # visibility CI job sets SPEC_KITTY_RUN_QUARANTINE=1 to run it for real.
    apply_quarantine_skip = not quarantine_opted_in(os.environ)
    skip_quarantine = quarantine_skip_mark()
    for item in items:
        if item.get_closest_marker("windows_ci") and sys.platform != "win32":
            item.add_marker(skip_windows)
        if apply_quarantine_skip and item.get_closest_marker(QUARANTINE_MARKER):
            item.add_marker(skip_quarantine)
    _fail_on_wall_clock_assertions(items)


def _fail_on_wall_clock_assertions(items: list[pytest.Item]) -> None:
    del items
    paths = find_test_python_paths(Path(__file__).parent)
    violations = find_wall_clock_assertion_violations(paths)
    if violations:
        raise pytest.UsageError(format_wall_clock_assertion_violations(violations))


@pytest.fixture(autouse=True)
def _isolated_worker_home(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """WP04: redirect the *default* home (HOME/XDG env) into a per-worker temp dir.

    Autouse and function-scoped so it applies to *every* test and is keyed by
    the xdist worker id (``master`` when serial) — never session-only, which
    would let all workers re-collide on a single home and re-introduce the
    real-``~/.spec-kitty`` hazard this WP exists to remove.

    Defined in the ROOT ``tests/conftest.py`` so it is set up before the deeper
    autouse queue-wipe fixture in ``tests/agent/conftest.py``; the queue-wipe
    helpers therefore transitively operate against this isolated home.

    The base directory matches the one ``pytest_configure`` already pointed the
    env vars at, so import-time and call-time home reads agree.

    Precedence (the cycle-1 regression fix): this fixture establishes the worker
    home **only via the HOME/USERPROFILE/XDG env vars** and deliberately does NOT
    hard-patch ``Path.home``. ``Path.home()`` natively resolves ``HOME`` (POSIX)
    / ``USERPROFILE`` (Windows) via ``os.path.expanduser``, so a test that later
    manages its own home — whether through ``monkeypatch.setenv("HOME", ...)`` or
    ``monkeypatch.setattr(Path, "home", ...)`` — cleanly overrides this baseline
    for BOTH ``Path.home()`` and the env vars that production code (e.g.
    ``queue.default_queue_db_path`` → ``Path.home() / ".spec-kitty"``) reads.

    A previously-used ``monkeypatch.setattr(Path, "home", lambda: home_base)``
    pinned ``Path.home()`` to the worker home regardless of any later in-test
    ``setenv("HOME", ...)``, silently winning over ~16 ``tests/sync`` cases that
    set up and assert their own tmp home. Setting only the env source keeps the
    real-``~/.spec-kitty``-untouched guarantee (the env vars are reset per test
    and before collection) while yielding precedence to in-test overrides.
    """
    home_base = _worker_home_base(request.config)
    home_base.mkdir(parents=True, exist_ok=True)

    for var in _HOME_ENV_VARS:
        monkeypatch.setenv(var, str(home_base))
    for var, subdir in _XDG_ENV_SUBDIRS.items():
        target = home_base / subdir
        target.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(var, str(target))

    return home_base


@pytest.fixture(autouse=True)
def _enable_saas_sync_feature_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep legacy sync/auth tests enabled unless a test opts out explicitly."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")


def reset_spec_kitty_queue_state() -> None:
    """Empty the user-scoped spec-kitty queue rows to a clean baseline.

    The sync-boundary preflight added in upstream commit `cc5e1ca9` reads
    `~/.spec-kitty/queue.db` (legacy queue) and the per-scope queue tree
    under `~/.spec-kitty/queues/<scope>/`. When earlier tests in the same
    shard emit events under the shared HOME, those rows accumulate and
    the preflight refuses (exit code 2) on downstream invocations that
    are not themselves testing the queue. This helper is the JUnit-style
    `@After`/`@Before` reset: it brings the on-disk state back to a
    known-empty baseline so the next test can proceed.

    Important: truncates rows (DELETE FROM ...) rather than deleting the
    SQLite file, because other readers may already hold open handles or
    expect the schema to exist. The body-upload sibling table is also
    truncated for the same reason.

    Use via the `clean_spec_kitty_queue` fixture (pre-test wipe + post-
    test wipe) or call directly inside a test's setup when the fixture
    pattern doesn't fit. Idempotent: missing files/tables are silently
    ignored.
    """
    import contextlib
    import shutil
    import sqlite3

    home = Path.home() / ".spec-kitty"
    if not home.exists():
        return

    def _truncate_db(db_path: Path) -> None:
        if not db_path.exists():
            return
        try:
            with sqlite3.connect(db_path) as conn:
                for (table_name,) in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name NOT LIKE 'sqlite_%'"
                ).fetchall():
                    with contextlib.suppress(sqlite3.OperationalError):
                        conn.execute(f"DELETE FROM {table_name}")  # noqa: S608
                conn.commit()
        except sqlite3.DatabaseError:
            # Corrupt / unreadable DB: remove so the next test reconstructs it.
            db_path.unlink(missing_ok=True)

    # Legacy queue DB (pre-cc5e1ca9 single-file layout)
    _truncate_db(home / "queue.db")
    # Per-scope queue DBs introduced in cc5e1ca9 (`~/.spec-kitty/queues/<scope>/`)
    queues_dir = home / "queues"
    if queues_dir.exists():
        for scope_db in queues_dir.rglob("*.db"):
            _truncate_db(scope_db)
    # Daemon owner record (preflight inspects this for D-3 mismatches)
    daemon_dir = home / "daemon"
    if daemon_dir.exists():
        shutil.rmtree(daemon_dir)
    # Active-scope pointer (some preflight readers consult this to scope queries)
    active_scope = home / "active-scope"
    if active_scope.exists():
        active_scope.unlink()


@pytest.fixture
def clean_spec_kitty_queue():
    """Pre-test + post-test cleanup of the user-scoped spec-kitty queue state.

    Mirrors JUnit's `@Before` + `@After` reset pattern. Wipes the queue
    before yielding to the test and again after the test returns, so
    cross-test pollution does not propagate in either direction. Tests
    that touch the queue can declare this fixture explicitly:

        def test_my_thing(clean_spec_kitty_queue):
            ...
    """
    reset_spec_kitty_queue_state()
    yield
    reset_spec_kitty_queue_state()


@pytest.fixture(autouse=True)
def _neutralize_worktree_detection(request, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent worktree detection from failing tests run inside a worktree.

    The ``@require_main_repo`` decorator checks the physical CWD for a
    ``.worktrees`` path component.  When the test suite itself runs inside
    a spec-kitty worktree (e.g. during WP implementation), every CLI
    invocation via ``CliRunner`` inherits that CWD and is incorrectly
    rejected.  Patching ``detect_execution_context`` to always return
    MAIN_REPO makes the tests location-independent.

    Tests that explicitly test worktree detection should use the
    ``@pytest.mark.real_worktree_detection`` marker to opt out.
    """
    if "real_worktree_detection" in {m.name for m in request.node.iter_markers()}:
        return

    from specify_cli.core.context_validation import (
        CurrentContext,
        ExecutionContext,
    )

    def _always_main_repo(cwd=None):
        return CurrentContext(
            location=ExecutionContext.MAIN_REPO,
            cwd=Path.cwd(),
            repo_root=None,
            worktree_name=None,
            worktree_path=None,
        )

    monkeypatch.setattr(
        "specify_cli.core.context_validation.detect_execution_context",
        _always_main_repo,
    )


def _venv_python(venv_dir: Path) -> Path:
    candidate = venv_dir / "bin" / "python"
    if candidate.exists():
        return candidate
    return venv_dir / "Scripts" / "python.exe"


def _venv_pip(venv_dir: Path) -> Path:
    candidate = venv_dir / "bin" / "pip"
    if candidate.exists():
        return candidate
    return venv_dir / "Scripts" / "pip.exe"


def _venv_has_required_runtime(venv_dir: Path) -> bool:
    """Return True when the cached venv can run the CLI runtime deps."""
    python = _venv_python(venv_dir)
    if not python.exists():
        return False
    probe = (
        "import importlib.util,sys;"
        "mods=['typer','rich','httpx','yaml'];"
        "missing=[m for m in mods if importlib.util.find_spec(m) is None];"
        "sys.exit(1 if missing else 0)"
    )
    result = subprocess.run(
        [str(python), "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _venv_is_valid(venv_dir: Path, source_version: str) -> bool:
    """Return True when the venv exists, has a working Python, and matches source_version.

    This idempotency check is evaluated *inside* the file-lock zone so that the
    second concurrent process to acquire the lock skips re-creation when the first
    already produced a valid venv.
    """
    marker = venv_dir / "VERSION"
    if not venv_dir.exists():
        return False
    if not marker.exists():
        return False
    if marker.read_text(encoding="utf-8").strip() != source_version:
        return False
    return _venv_has_required_runtime(venv_dir)


def _ensure_test_venv(project_root: Path, source_version: str) -> Path:
    """Create or reuse the shared test venv, serialised across concurrent pytest processes.

    Uses a file lock at ``_VENV_LOCK_PATH`` (relative to *project_root*) so that
    parallel pytest invocations (e.g., contract + architectural gates) cannot race
    and observe a half-created venv.  The lock timeout is ``_LOCK_TIMEOUT_S``
    seconds; if the lock cannot be acquired, an operator-actionable RuntimeError is
    raised that names the lock file and explains how to remove it.

    Implements FR-003 and FR-004.
    """
    venv_path = project_root / _VENV_CACHE_PATH
    lock_path = project_root / _VENV_LOCK_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(lock_path), timeout=_LOCK_TIMEOUT_S):
            if not _venv_is_valid(venv_path, source_version):
                shutil.rmtree(venv_path, ignore_errors=True)
                _create_test_venv(venv_path, source_version)
                (venv_path / "VERSION").write_text(source_version, encoding="utf-8")
    except Timeout:
        raise RuntimeError(
            f"Timed out acquiring {lock_path} after {_LOCK_TIMEOUT_S}s. "
            f"If no test process is currently running, remove the lock file: "
            f"rm {lock_path}"
        ) from None
    return venv_path


def _venv_site_packages(venv_dir: Path) -> Path:
    python = _venv_python(venv_dir)
    result = subprocess.run(
        [
            str(python),
            "-c",
            "import site; print(site.getsitepackages()[0])",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def _seed_offline_test_venv(venv_dir: Path, source_version: str) -> None:
    """Seed a fallback venv without requiring network access."""
    site_packages = _venv_site_packages(venv_dir)
    site_packages.mkdir(parents=True, exist_ok=True)

    host_site_packages = [
        path for path in sys.path if "site-packages" in path and Path(path).exists()
    ]
    if host_site_packages:
        (site_packages / "host-site-packages.pth").write_text(
            "\n".join(host_site_packages) + "\n",
            encoding="utf-8",
        )

    (site_packages / "spec-kitty-src.pth").write_text(
        f"{REPO_ROOT / 'src'}\n",
        encoding="utf-8",
    )

    dist_info_dir = site_packages / f"spec_kitty_cli-{source_version}.dist-info"
    dist_info_dir.mkdir(exist_ok=True)
    (dist_info_dir / "METADATA").write_text(
        "\n".join(
            [
                "Metadata-Version: 2.1",
                "Name: spec-kitty-cli",
                f"Version: {source_version}",
                "Summary: Local offline test install shim",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (dist_info_dir / "top_level.txt").write_text("specify_cli\n", encoding="utf-8")
    (dist_info_dir / "INSTALLER").write_text("offline-shim\n", encoding="utf-8")
    (dist_info_dir / "RECORD").write_text("", encoding="utf-8")


def _create_test_venv(venv_dir: Path, source_version: str) -> None:
    """Create the test venv, with an offline-safe fallback."""
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    pip = _venv_pip(venv_dir)
    try:
        subprocess.run([str(pip), "install", "-e", str(REPO_ROOT)], check=True)
    except subprocess.CalledProcessError:
        # Fallback for offline/dev shells where build deps cannot be downloaded.
        shutil.rmtree(venv_dir, ignore_errors=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        _seed_offline_test_venv(venv_dir, source_version)

    if not _venv_has_required_runtime(venv_dir):
        raise RuntimeError("Test venv is missing runtime dependencies (typer/rich/httpx/yaml).")


@pytest.fixture(scope="session", autouse=True)
def test_venv() -> Path:
    """Create and cache a test venv for isolated CLI execution.

    Delegates to ``_ensure_test_venv`` which serialises venv creation across
    concurrent pytest processes using a file lock (FR-003, FR-004).
    Single-process runs behave identically to pre-WP02.
    """
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        source_version = tomllib.load(f)["project"]["version"]

    venv_dir = _ensure_test_venv(REPO_ROOT, source_version)
    os.environ["SPEC_KITTY_TEST_VENV"] = str(venv_dir)
    return venv_dir


# ---------------------------------------------------------------------------
# Session-scoped build artifacts — shared across ALL packaging/distribution tests
# Builds wheel + sdist ONCE per session instead of per-test.
# ---------------------------------------------------------------------------

def _build_tool_available() -> bool:
    return subprocess.run(
        [sys.executable, "-m", "build", "--help"],
        capture_output=True, text=True,
    ).returncode == 0


@pytest.fixture(scope="session")
def build_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Build wheel + sdist once per session. Shared by all packaging tests."""
    if not _build_tool_available():
        pytest.skip("python -m build not available")

    outdir = tmp_path_factory.mktemp("build")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(outdir)],
        cwd=REPO_ROOT,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"Build failed: {result.stderr}")

    wheels = sorted(outdir.glob("spec_kitty_cli-*.whl"))
    sdists = sorted(outdir.glob("spec_kitty_cli-*.tar.gz"))
    if not wheels or not sdists:
        pytest.skip("Build did not produce expected wheel/sdist artifacts")

    return {"wheel": wheels[-1], "sdist": sdists[-1]}


@pytest.fixture(scope="session")
def installed_wheel_venv(
    build_artifacts: dict[str, Path],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Path]:
    """Install the session wheel into a fresh venv. Shared by all install tests."""
    wheel = build_artifacts["wheel"]
    venv_dir = tmp_path_factory.mktemp("wheel_venv")

    result = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"Failed to create venv: {result.stderr}")

    pip = venv_dir / "bin" / "pip"
    python = venv_dir / "bin" / "python"
    if not pip.exists():
        pip = venv_dir / "Scripts" / "pip.exe"
        python = venv_dir / "Scripts" / "python.exe"
    if not pip.exists():
        pytest.skip("pip not found in venv")

    result = subprocess.run(
        [str(pip), "install", str(wheel)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"Failed to install wheel: {result.stderr}")

    return {"pip": pip, "python": python, "venv_dir": venv_dir, "wheel": wheel}


@pytest.fixture()
def isolated_env() -> dict[str, str]:
    """Create isolated environment blocking host spec-kitty installation.

    Ensures tests use source code exclusively via:
    - PYTHONPATH set to source only (no inheritance)
    - SPEC_KITTY_CLI_VERSION from pyproject.toml
    - SPEC_KITTY_TEST_MODE=1 to enforce test behavior
    - SPEC_KITTY_TEMPLATE_ROOT to source templates

    This fixture guarantees that tests will never accidentally use a
    pip-installed version of spec-kitty-cli from the host system.
    """
    from tests.test_isolation_helpers import get_venv_python  # noqa: F401 (side-effect: ensures venv exists)

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        source_version = tomllib.load(f)["project"]["version"]

    src_path = REPO_ROOT / "src"
    env["PYTHONPATH"] = str(src_path)
    env["SPEC_KITTY_CLI_VERSION"] = source_version
    env["SPEC_KITTY_TEST_MODE"] = "1"
    env["SPEC_KITTY_TEMPLATE_ROOT"] = str(REPO_ROOT)

    return env


@pytest.fixture()
def run_cli(isolated_env: dict[str, str]) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Return a helper that executes the Spec Kitty CLI within a project.

    Uses isolated_env to guarantee tests run against source code, not
    installed packages. This prevents version mismatch errors.
    """
    from tests.test_isolation_helpers import get_venv_python

    def _run_cli(project_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        command = [str(get_venv_python()), "-m", "specify_cli.__init__", *args]
        return subprocess.run(
            command,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            env=isolated_env,
            timeout=60,
        )

    return _run_cli


@pytest.fixture()
def temp_repo(tmp_path: Path) -> Iterator[Path]:
    # WP06 (A3/PP-03): the common "needs a baseline repo" case is served by a
    # build-once bare template cloned per test, which is materially cheaper than
    # ``git init`` + config + commit. The clone is a clean working tree on
    # ``main`` with one baseline commit and a configured commit identity, so
    # downstream fixtures/tests that ``git commit`` on top behave unchanged.
    # Bespoke setups that need unborn/detached/--bare/worktree state keep their
    # own explicit ``git init`` below.
    from tests._support.git_template import clone_template

    repo_dir = clone_template(tmp_path / "repo")
    yield repo_dir


@pytest.fixture()
def feature_repo(temp_repo: Path) -> Path:
    mission_slug = "001-demo-feature"
    feature_dir = temp_repo / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "tasks").mkdir(exist_ok=True)
    (feature_dir / "spec.md").write_text("Spec content", encoding="utf-8")
    (feature_dir / "plan.md").write_text("Plan content", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("- [x] Initial task", encoding="utf-8")
    (feature_dir / "quickstart.md").write_text("Quickstart", encoding="utf-8")
    (feature_dir / "data-model.md").write_text("Data model", encoding="utf-8")
    (feature_dir / "research.md").write_text("Research", encoding="utf-8")
    write_wp(temp_repo, mission_slug, "planned", "WP01")
    # Bootstrap event log with planned status for WP01
    import json
    from datetime import datetime, UTC
    event = {
        "event_id": "01TESTFIXTUREWP01",
        "mission_slug": mission_slug,
        "wp_id": "WP01",
        "from_lane": "planned",
        "to_lane": "planned",
        "actor": "test-fixture",
        "at": datetime.now(UTC).isoformat(),
        "force": True,
        "reason": "fixture bootstrap",
        "evidence": None,
        "review_ref": None,
        "execution_mode": "worktree",
    }
    events_path = feature_dir / "status.events.jsonl"
    events_path.write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")
    run(["git", "add", "."], cwd=temp_repo)
    run(["git", "commit", "-m", "Initial commit"], cwd=temp_repo)
    return temp_repo


@pytest.fixture()
def mission_slug() -> str:
    return "001-demo-feature"


@pytest.fixture()
def merge_repo(temp_repo: Path) -> tuple[Path, Path, str]:
    repo = temp_repo
    (repo / "README.md").write_text("main", encoding="utf-8")
    (repo / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
    run(["git", "add", "README.md", ".gitignore"], cwd=repo)
    run(["git", "commit", "-m", "initial"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    mission_slug = "002-feature"
    run(["git", "checkout", "-b", mission_slug], cwd=repo)
    feature_file = repo / "FEATURE.txt"
    feature_file.write_text("feature work", encoding="utf-8")
    feature_dir = repo / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "meta.json").write_text("{}\n", encoding="utf-8")
    run(["git", "add", "FEATURE.txt", "kitty-specs"], cwd=repo)
    run(["git", "commit", "-m", "feature work"], cwd=repo)

    run(["git", "checkout", "main"], cwd=repo)

    worktree_dir = repo / ".worktrees" / mission_slug
    worktree_dir.parent.mkdir(exist_ok=True)
    run(["git", "worktree", "add", str(worktree_dir), mission_slug], cwd=repo)

    return repo, worktree_dir, mission_slug


@pytest.fixture
def mock_worktree(tmp_path: Path) -> dict[str, Path]:
    """
    Create temporary worktree structure for testing path resolution.

    Creates a minimal spec-kitty project structure with a feature worktree.

    Returns:
        Dictionary with 'repo_root', 'worktree_path', and 'feature_dir' paths
    """
    repo_root = tmp_path
    worktree = repo_root / ".worktrees" / "test-feature"
    worktree.mkdir(parents=True)

    # Create .kittify marker in repo root
    kittify = repo_root / ".kittify"
    kittify.mkdir()

    # Create feature directory in worktree
    feature_dir = worktree / "kitty-specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)

    return {"repo_root": repo_root, "worktree_path": worktree, "feature_dir": feature_dir}


@pytest.fixture
def mock_main_repo(tmp_path: Path) -> Path:
    """
    Create temporary main repository structure for testing.

    Creates a minimal spec-kitty project structure in the main repo
    (not a worktree).

    Returns:
        Path to the temporary repository root
    """
    # Create .kittify marker
    kittify = tmp_path / ".kittify"
    kittify.mkdir()

    # Create specs directory
    specs = tmp_path / "kitty-specs"
    specs.mkdir()

    return tmp_path


@pytest.fixture
def conflicting_wps_repo(tmp_path: Path) -> tuple[Path, list[tuple[Path, str, str]]]:
    """
    Create repo with overlapping WP file changes for conflict testing.

    Returns:
        Tuple of (repo_root, wp_workspaces) where wp_workspaces is a list
        of (worktree_path, wp_id, branch_name) tuples with 3 WPs that
        have overlapping file modifications.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.name", "Test"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)

    # Create initial commit
    (repo / "README.md").write_text("main", encoding="utf-8")
    (repo / "shared.txt").write_text("original", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "init"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    # Create feature with WP tasks
    mission_slug = "017-conflict-test"
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    wp_workspaces = []

    # Create 3 WPs that all modify shared.txt
    for wp_num in [1, 2, 3]:
        wp_id = f"WP{wp_num:02d}"
        branch_name = f"{mission_slug}-{wp_id}"

        # Create WP task file
        wp_file = tasks_dir / f"{wp_id}.md"
        wp_file.write_text(
            f"""---
work_package_id: {wp_id}
title: Test WP {wp_num}
dependencies: []
---

# {wp_id} Content
""",
            encoding="utf-8",
        )

        # Create worktree
        worktree_dir = repo / ".worktrees" / branch_name
        run(["git", "worktree", "add", str(worktree_dir), "-b", branch_name], cwd=repo)

        # Modify shared.txt (this will conflict)
        (worktree_dir / "shared.txt").write_text(f"{wp_id} changes\n", encoding="utf-8")

        # Also modify WP-specific file (no conflict)
        (worktree_dir / f"{wp_id}.txt").write_text(f"{wp_id} specific\n", encoding="utf-8")

        run(["git", "add", "."], cwd=worktree_dir)
        run(["git", "commit", "-m", f"Add {wp_id} changes"], cwd=worktree_dir)

        wp_workspaces.append((worktree_dir, wp_id, branch_name))

    run(["git", "checkout", "main"], cwd=repo)

    return repo, wp_workspaces


@pytest.fixture
def git_stale_workspace(tmp_path: Path) -> dict[str, Path | str]:
    """
    Create main repo + stale lane worktree.

    The main branch will have commits that the lane branch doesn't have,
    simulating a stale workspace that needs syncing.

    Returns:
        Dictionary with 'repo_root', 'main_branch', 'worktree_path', 'mission_slug' keys
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.name", "Test"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)

    # Create initial commit on main
    (repo / "README.md").write_text("initial", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "initial commit"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    # Create lane branch and worktree
    mission_slug = "018-stale-test"
    branch_name = f"kitty/mission-{mission_slug}-lane-a"
    worktree_dir = repo / ".worktrees" / f"{mission_slug}-lane-a"
    run(["git", "worktree", "add", str(worktree_dir), "-b", branch_name], cwd=repo)

    # Make commit in worktree
    (worktree_dir / "WP01.txt").write_text("WP01 work", encoding="utf-8")
    run(["git", "add", "."], cwd=worktree_dir)
    run(["git", "commit", "-m", "WP01 work"], cwd=worktree_dir)

    # Advance main branch (making worktree stale)
    run(["git", "checkout", "main"], cwd=repo)
    (repo / "main_advance.txt").write_text("main advanced", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "advance main"], cwd=repo)

    return {
        "repo_root": repo,
        "main_branch": "main",
        "worktree_path": worktree_dir,
        "mission_slug": mission_slug,
        "branch_name": branch_name,
    }


@pytest.fixture
def dirty_worktree_repo(tmp_path: Path) -> tuple[Path, Path]:
    """
    Add uncommitted changes to a lane worktree.

    Returns:
        Tuple of (repo_root, dirty_worktree_path)
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    run(["git", "init"], cwd=repo)
    run(["git", "config", "user.name", "Test"], cwd=repo)
    run(["git", "config", "user.email", "test@example.com"], cwd=repo)

    # Create initial commit
    (repo / "README.md").write_text("test", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "init"], cwd=repo)
    run(["git", "branch", "-M", "main"], cwd=repo)

    # Create feature with WP tasks
    mission_slug = "019-dirty-test"
    feature_dir = repo / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    wp_file = tasks_dir / "WP01.md"
    wp_file.write_text(
        """---
work_package_id: WP01
title: Test WP
dependencies: []
---

# WP01 Content
""",
        encoding="utf-8",
    )

    # Create worktree
    branch_name = f"kitty/mission-{mission_slug}-lane-a"
    worktree_dir = repo / ".worktrees" / f"{mission_slug}-lane-a"
    run(["git", "worktree", "add", str(worktree_dir), "-b", branch_name], cwd=repo)

    # Make commit
    (worktree_dir / "WP01.txt").write_text("committed", encoding="utf-8")
    run(["git", "add", "."], cwd=worktree_dir)
    run(["git", "commit", "-m", "WP01 commit"], cwd=worktree_dir)

    # Add uncommitted changes
    (worktree_dir / "uncommitted.txt").write_text("dirty changes", encoding="utf-8")

    run(["git", "checkout", "main"], cwd=repo)

    return repo, worktree_dir


# ---------------------------------------------------------------------------
# Fixtures promoted from integration/conftest.py for use in slice directories
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_project(tmp_path: Path) -> Path:
    """Create a temporary Spec Kitty project with git initialized."""
    project = tmp_path / "project"
    project.mkdir()

    shutil.copytree(
        REPO_ROOT / ".kittify",
        project / ".kittify",
        symlinks=True,
    )

    # Copy missions from new location (src/specify_cli/missions/ -> .kittify/missions/)
    missions_src = REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dest = project / ".kittify" / "missions"
    if missions_src.exists() and not missions_dest.exists():
        shutil.copytree(missions_src, missions_dest)

    (project / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

    subprocess.run(["git", "init", "-b", "main"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "Spec Kitty CI"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-m", "Initial project"], cwd=project, check=True)

    # Update metadata.yaml to current version to avoid version mismatch errors
    metadata_file = project / ".kittify" / "metadata.yaml"
    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}

        current_version = get_installed_version()
        if current_version is None:
            with open(REPO_ROOT / "pyproject.toml", "rb") as f:
                pyproject = tomllib.load(f)
            current_version = pyproject["project"]["version"] or "unknown"

        if "spec_kitty" not in metadata:
            metadata["spec_kitty"] = {}
        metadata["spec_kitty"]["version"] = current_version
        metadata["spec_kitty"]["schema_version"] = 3

        with open(metadata_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

    return project


@pytest.fixture()
def clean_project(test_project: Path) -> Path:
    """Return a clean git project with no worktrees."""
    return test_project


@pytest.fixture()
def dirty_project(test_project: Path) -> Path:
    """Return a project containing uncommitted changes."""
    dirty_file = test_project / "dirty.txt"
    dirty_file.write_text("pending changes\n", encoding="utf-8")
    return test_project


@pytest.fixture()
def project_with_worktree(test_project: Path) -> Path:
    """Return a project with simulated active worktree directories."""
    worktree_dir = test_project / ".worktrees" / "001-test-feature"
    worktree_dir.mkdir(parents=True)
    (worktree_dir / "README.md").write_text("feature placeholder\n", encoding="utf-8")
    return test_project


@pytest.fixture()
def dual_branch_repo(tmp_path: Path) -> Path:
    """Create test repo with both main and 2.x branches.

    Returns a repository with:
    - main branch (initial commit)
    - 2.x branch (branched from main)
    - .kittify/ structure initialized
    - Git configured for tests
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    shutil.copytree(
        REPO_ROOT / ".kittify",
        repo / ".kittify",
        symlinks=True,
    )

    missions_src = REPO_ROOT / "src" / "specify_cli" / "missions"
    missions_dest = repo / ".kittify" / "missions"
    if missions_src.exists() and not missions_dest.exists():
        shutil.copytree(missions_src, missions_dest)

    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    (repo / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    subprocess.run(["git", "branch", "2.x"], cwd=repo, check=True, capture_output=True)

    metadata_file = repo / ".kittify" / "metadata.yaml"
    if metadata_file.exists():
        with open(metadata_file, encoding="utf-8") as f:
            metadata = yaml.safe_load(f) or {}

        current_version = get_installed_version()
        if current_version is None:
            with open(REPO_ROOT / "pyproject.toml", "rb") as f:
                pyproject = tomllib.load(f)
            current_version = pyproject["project"]["version"] or "unknown"

        if "spec_kitty" not in metadata:
            metadata["spec_kitty"] = {}
        metadata["spec_kitty"]["version"] = current_version

        with open(metadata_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)

    return repo


# ---------------------------------------------------------------------------
# T027 — shared seed fixture (for tests outside tests/status/)
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_to_planned() -> Callable[[Path, str, str], None]:
    """Return the shared WP seed callable for tests outside tests/status/.

    Usage::

        def test_something(tmp_path, seed_to_planned):
            feature_dir = tmp_path / "kitty-specs" / "099-mission"
            feature_dir.mkdir(parents=True)
            seed_to_planned(feature_dir, "WP01")
            seed_to_planned(feature_dir, "WP02", slug="099-mission")

    Delegates to ``tests.status.conftest.seed_wp_to_planned``. Writes directly
    to the event log (no emit pipeline) so no fan-out or git transaction is
    triggered.
    """
    from tests.status.conftest import seed_wp_to_planned

    return seed_wp_to_planned
