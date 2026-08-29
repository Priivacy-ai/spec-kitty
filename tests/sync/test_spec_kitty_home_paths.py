"""SPEC_KITTY_HOME rerouting for sync global state (WP02 / issue #2171).

Every sync state surface must resolve under ``get_runtime_root().base``:

* with ``SPEC_KITTY_HOME`` set, all paths land under that root verbatim
  (the env path is *not* suffixed with ``.spec-kitty``);
* with it unset, POSIX paths are byte-identical to the legacy
  ``~/.spec-kitty/...`` layout (NFR-001).

Covers FR-001 (config), FR-004/FR-005 (queues + active scope), FR-006
(daemon), FR-007 (clock), plus the POSIX flat daemon layout (research.md D3).

The legacy lazy ``SPEC_KITTY_DIR`` module-attribute shim (research.md D5) was
retired in #3569 — it duplicated ``get_runtime_root()`` with no production
readers — so it is no longer covered here.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from specify_cli.sync import daemon
from specify_cli.sync.clock import LamportClock
from specify_cli.sync.config import SyncConfig
from specify_cli.sync.queue import (
    LegacyQueueMigrationRequiredError,
    _active_scope_path,
    _legacy_queue_db_path,
    _scoped_queue_dir,
    build_queue_scope,
    default_queue_db_path,
    scope_db_path,
)
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore

if TYPE_CHECKING:
    from specify_cli.auth.token_manager import StoredSession


from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]


def _configure_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, env_set: bool) -> Path:
    """Point HOME / SPEC_KITTY_HOME at throwaway dirs; return the expected base.

    The home dir always differs from the env root so the env-set scenarios also
    prove ``SPEC_KITTY_HOME`` wins over ``Path.home()``.
    """
    home_dir = tmp_path / "home"
    home_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setenv("USERPROFILE", str(home_dir))
    if env_set:
        env_root = tmp_path / "env-root"
        env_root.mkdir(exist_ok=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(env_root))
        return env_root
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    return home_dir / ".spec-kitty"


class _FakeTokenManager:
    """Token manager that reports no authenticated session."""

    def __init__(self, session: StoredSession | None = None) -> None:
        self._session = session

    def get_current_session(self) -> StoredSession | None:
        return self._session


def _patch_no_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "specify_cli.auth.get_token_manager",
        lambda: _FakeTokenManager(None),
    )


def test_unset_base_is_byte_identical_to_legacy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With SPEC_KITTY_HOME unset, the POSIX base equals ``~/.spec-kitty``."""
    base = _configure_root(monkeypatch, tmp_path, env_set=False)
    assert base == Path.home() / ".spec-kitty"


@pytest.mark.parametrize("env_set", [False, True])
def test_sync_config_file_under_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_set: bool) -> None:
    base = _configure_root(monkeypatch, tmp_path, env_set=env_set)
    cfg = SyncConfig()
    assert cfg.config_dir == base
    assert cfg.config_file == base / "config.toml"


@pytest.mark.parametrize("env_set", [False, True])
def test_active_scope_path_under_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_set: bool) -> None:
    base = _configure_root(monkeypatch, tmp_path, env_set=env_set)
    assert _active_scope_path() == base / "active_queue_scope"


@pytest.mark.parametrize("env_set", [False, True])
def test_default_queue_db_path_unauthenticated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_set: bool) -> None:
    """No session cannot turn the legacy migration input into a live queue."""
    base = _configure_root(monkeypatch, tmp_path, env_set=env_set)
    _patch_no_session(monkeypatch)
    expected = base / "queue.db"
    assert _legacy_queue_db_path() == expected
    with pytest.raises(LegacyQueueMigrationRequiredError):
        default_queue_db_path()
    assert not expected.exists()


@pytest.mark.parametrize("env_set", [False, True])
def test_default_queue_db_path_authenticated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_set: bool) -> None:
    """Credentials cannot select a live queue; project identity owns its store."""
    base = _configure_root(monkeypatch, tmp_path, env_set=env_set)
    _patch_no_session(monkeypatch)
    base.mkdir(parents=True, exist_ok=True)
    (base / "credentials").write_text(
        """
[user]
username = "tester@example.com"
team_slug = "team-red"

[server]
url = "https://test.example.com"
""".strip()
    )

    legacy_scoped = scope_db_path(
        build_queue_scope(
            server_url="https://test.example.com",
            username="tester@example.com",
            team_slug="team-red",
        )
    )
    with pytest.raises(LegacyQueueMigrationRequiredError):
        default_queue_db_path()
    assert legacy_scoped.parent == base / "queues"
    assert _scoped_queue_dir() == base / "queues"
    assert not legacy_scoped.exists()

    project_uuid = "aaaaaaaa-0000-0000-0000-000000000001"
    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("home-path-test")
        authority.publish_project_only("home-path-test", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        row = unit.execute("SELECT project_uuid FROM project_store_metadata WHERE singleton = 1").fetchone()
    assert row == (project_uuid,)
    assert store.database_path.parent == base / "projects" / project_uuid / "sync"
    assert store.database_path != legacy_scoped


@pytest.mark.parametrize("env_set", [False, True])
def test_daemon_sync_root_under_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_set: bool) -> None:
    """POSIX sync root keeps the flat ``base/sync`` suffix (research.md D3)."""
    base = _configure_root(monkeypatch, tmp_path, env_set=env_set)
    assert daemon._sync_root() == base / "sync"


@pytest.mark.parametrize("env_set", [False, True])
def test_daemon_root_is_flat_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_set: bool) -> None:
    """POSIX daemon root is the flat base, NOT ``base/daemon`` (research.md D3)."""
    base = _configure_root(monkeypatch, tmp_path, env_set=env_set)
    assert daemon._daemon_root() == base


def test_daemon_module_getattr_rejects_unknown_attr() -> None:
    # Variable (not a constant) so this exercises the module __getattr__ shim
    # without tripping ruff B009.
    missing = "NOT_A_REAL_ATTRIBUTE"
    with pytest.raises(AttributeError):
        getattr(daemon, missing)


@pytest.mark.parametrize("env_set", [False, True])
def test_lamport_clock_default_under_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, env_set: bool) -> None:
    base = _configure_root(monkeypatch, tmp_path, env_set=env_set)
    expected = base / "clock.json"
    # default_factory on a freshly constructed clock
    assert LamportClock()._storage_path == expected
    # and the load() default (no file present yet)
    assert LamportClock.load()._storage_path == expected
