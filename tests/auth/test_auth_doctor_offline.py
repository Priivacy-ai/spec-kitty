"""Tests for ``spec-kitty auth doctor`` offline + read-only invariants (WP06 / T028).

Two invariants per ``contracts/auth-doctor.md`` and the WP06 charter:

1. **C-007** — default invocation makes ZERO outbound (non-127.0.0.1)
   network calls. We patch ``httpx.AsyncClient`` and
   ``urllib.request.urlopen`` with mocks that fail the test if invoked
   against any non-localhost host.
2. **FR-015** — default invocation makes ZERO state mutations: no
   ``Path.unlink``, no ``psutil.terminate``/``psutil.kill``, no
   ``force_release``, no ``storage.delete``.

Both invariants are verified against ``doctor_impl(json_output=True,
reset=False, unstick_lock=False)`` (the default, read-only path).
"""

from __future__ import annotations

import urllib.request
from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest

from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands import _auth_doctor
from specify_cli.cli.commands._auth_doctor import doctor_impl
from specify_cli.sync.daemon import SyncDaemonStatus


def _make_session() -> StoredSession:
    now = datetime.now(UTC)
    return StoredSession(
        user_id="user-abc",
        email="rob@example.com",
        name="Rob",
        teams=[Team(id="t1", name="Personal", role="owner", is_private_teamspace=True)],
        default_team_id="t1",
        access_token="access-xyz",
        refresh_token="refresh-xyz",
        session_id="session-xyz",
        issued_at=now,
        access_token_expires_at=now + timedelta(minutes=15),
        refresh_token_expires_at=now + timedelta(days=30),
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


class _FakeStorage:
    def __init__(self, session: StoredSession | None) -> None:
        self._session = session

    def read(self) -> StoredSession | None:
        return self._session

    def write(self, session: StoredSession) -> None:
        self._session = session

    def delete(self) -> None:
        # The doctor must NEVER call delete on the default path.
        raise AssertionError("storage.delete called on read-only path")


class _FakeTokenManager:
    def __init__(self, session: StoredSession | None) -> None:
        self._session = session
        self._storage = _FakeStorage(session)

    def get_current_session(self) -> StoredSession | None:
        return self._session


def _patch_doctor_state(
    monkeypatch: pytest.MonkeyPatch, *, lock_path: Path
) -> None:
    """Wire ``_auth_doctor``'s upstream calls to deterministic fakes."""
    session = _make_session()
    monkeypatch.setattr(
        _auth_doctor,
        "get_token_manager",
        lambda: _FakeTokenManager(session),
    )
    monkeypatch.setattr(_auth_doctor, "_refresh_lock_path", lambda: lock_path)

    class _FakeStateFile:
        def exists(self) -> bool:
            return False

    monkeypatch.setattr(_auth_doctor, "DAEMON_STATE_FILE", _FakeStateFile())
    monkeypatch.setattr(
        _auth_doctor, "get_sync_daemon_status", lambda: SyncDaemonStatus(healthy=False)
    )
    # Empty orphan list — no need to scan ports for this offline test.
    monkeypatch.setattr(_auth_doctor, "enumerate_orphans", lambda: [])
    import sys

    fake_rollout = type(sys)("specify_cli.saas.rollout")
    fake_rollout.is_saas_sync_enabled = lambda: False  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "specify_cli.saas.rollout", fake_rollout)


# ---------------------------------------------------------------------------
# C-007: no outbound HTTP
# ---------------------------------------------------------------------------


def test_no_outbound_http(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Default ``auth doctor`` makes ZERO non-127.0.0.1 outbound calls.

    Patches ``httpx.AsyncClient`` and ``urllib.request.urlopen`` to fail
    the test on any non-localhost call. Local 127.0.0.1 probes (orphan
    health check, daemon status) are explicitly allowed by C-007 and
    deliberately disabled by the fixtures above (``enumerate_orphans``
    returns ``[]``; daemon state file does not exist).
    """
    lock_path = tmp_path / "auth" / "refresh.lock"
    _patch_doctor_state(monkeypatch, lock_path=lock_path)

    def _fail_urlopen(url, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Allow only 127.0.0.1 / localhost URLs.
        target = url if isinstance(url, str) else getattr(url, "full_url", "")
        if "127.0.0.1" not in target and "localhost" not in target:
            raise AssertionError(
                f"urllib.request.urlopen called against non-local URL: {target!r}"
            )
        # We don't expect any local calls to fire either in this fixture
        # (orphan list is empty, daemon state is missing) but keep the
        # local branch a no-op so this test stays robust to future edits.
        raise RuntimeError("local urlopen unreachable in this fixture")

    class _FailingHTTPXClient:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            raise AssertionError(
                "httpx.AsyncClient instantiated during default auth doctor "
                "invocation — C-007 violation"
            )

    # urllib patch — fails on any non-127.0.0.1 call.
    monkeypatch.setattr(urllib.request, "urlopen", _fail_urlopen)

    # httpx is the SaaS HTTP client; the doctor's default path must never
    # construct one. We patch the import path used by the auth subsystem.
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FailingHTTPXClient)

    # Default invocation, JSON output to avoid Rich noise.
    exit_code = doctor_impl(
        json_output=True,
        reset=False,
        unstick_lock=False,
        stuck_threshold=60.0,
    )

    # Healthy session, no findings, exit 0.
    assert exit_code == 0


# ---------------------------------------------------------------------------
# FR-015: no state mutation on default path
# ---------------------------------------------------------------------------


def test_no_state_mutation_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """After a default invocation: no files removed, no processes terminated.

    Patches ``Path.unlink`` and the WP01 / WP05 mutating primitives to
    fail-the-test if invoked. ``_storage.delete`` is also wrapped so any
    call would raise.
    """
    lock_path = tmp_path / "auth" / "refresh.lock"
    _patch_doctor_state(monkeypatch, lock_path=lock_path)

    def _fail_unlink(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(
            f"Path.unlink({self!r}) called on default doctor path — "
            "FR-015 violation"
        )

    def _fail_force_release(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(
            "force_release called on default doctor path — FR-015 violation"
        )

    def _fail_sweep_orphans(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(
            "sweep_orphans called on default doctor path — FR-015 violation"
        )

    # psutil terminate/kill on the default path would be FR-015 violations.
    import psutil

    class _FailingProcess:
        def __init__(self, pid: int) -> None:
            self._pid = pid

        def terminate(self) -> None:
            raise AssertionError(
                "psutil.Process.terminate called on default doctor path — "
                "FR-015 violation"
            )

        def kill(self) -> None:
            raise AssertionError(
                "psutil.Process.kill called on default doctor path — "
                "FR-015 violation"
            )

    monkeypatch.setattr(_auth_doctor, "force_release", _fail_force_release)
    monkeypatch.setattr(_auth_doctor, "sweep_orphans", _fail_sweep_orphans)
    monkeypatch.setattr(psutil, "Process", _FailingProcess)
    # Patch Path.unlink at the class level so any descendant call fails.
    monkeypatch.setattr(Path, "unlink", _fail_unlink)

    # Snapshot the auth root before the invocation so we can confirm it's
    # untouched at the file-system level.
    pre_existing_root = lock_path.parent.exists()

    exit_code = doctor_impl(
        json_output=True,
        reset=False,
        unstick_lock=False,
        stuck_threshold=60.0,
    )

    assert exit_code == 0
    # The auth-root directory may have been *created* (mkdir) by upstream
    # code paths but no file should have been deleted by this invocation.
    # We assert the lock file does not exist (it never did) and the
    # parent directory state is unchanged from before.
    assert not lock_path.exists()
    assert lock_path.parent.exists() == pre_existing_root
