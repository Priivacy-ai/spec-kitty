"""Regression coverage for the local auth session hot path (WP04)."""

from __future__ import annotations

import asyncio
import json
import sys
import time
import types
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from specify_cli.auth import session_hot_path
from specify_cli.auth.secure_storage.file_fallback import FileFallbackStorage
from specify_cli.auth.session import StoredSession, Team
from specify_cli.auth.session_hot_path import (
    handoff_path_for_store,
    invalidate_session_hot_path,
    load_session_hot_path,
    publish_session_hot_path,
)
import specify_cli.auth.token_manager as token_manager_module
from specify_cli.auth.token_manager import TokenManager


class _CountingFastFileStorage(FileFallbackStorage):
    """File storage with production behavior, low KDF cost, and read counting."""

    _scrypt_n = 2**10
    _scrypt_r = 8
    _scrypt_p = 1

    durable_read_count = 0

    def read(self) -> StoredSession | None:
        type(self).durable_read_count += 1
        return super().read()


def _private_teamspace() -> Team:
    return Team(
        id="t-private",
        name="Private",
        role="owner",
        is_private_teamspace=True,
    )


def _make_session(*, access_expires_in: int = 900) -> StoredSession:
    now = datetime.now(UTC)
    return StoredSession(
        user_id="user_seed",
        email="seed@example.com",
        name="Seed User",
        teams=[_private_teamspace()],
        default_team_id="t-private",
        access_token="at_seed_v1",
        refresh_token="rt_seed_v1",
        session_id="sess_seed",
        issued_at=now,
        access_token_expires_at=now + timedelta(seconds=access_expires_in),
        refresh_token_expires_at=now + timedelta(days=30),
        scope="openid offline_access",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def _reset_read_count() -> None:
    _CountingFastFileStorage.durable_read_count = 0


def _new_process_auth_check(store_dir: Path) -> bool:
    storage = _CountingFastFileStorage(base_dir=store_dir)
    tm = TokenManager(storage)
    tm.load_from_storage_sync()
    return tm.is_authenticated


def _new_process_load_only(store_dir: Path) -> bool:
    storage = _CountingFastFileStorage(base_dir=store_dir)
    tm = TokenManager(storage)
    tm.load_from_storage_sync()
    return tm._session is None and tm._hot_path_summary is not None


def test_many_short_lived_loads_defer_baseline_8_durable_reads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Baseline 8 process-start loads read storage 8 times; hot path reads 0."""
    process_count = 8
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())

    monkeypatch.setenv("SPEC_KITTY_DISABLE_SESSION_HOT_PATH", "1")
    _reset_read_count()
    assert all(_new_process_auth_check(store_dir) for _ in range(process_count))
    baseline_durable_reads = _CountingFastFileStorage.durable_read_count

    assert baseline_durable_reads == 8, (
        "Mandatory baseline: before the hot path, each short-lived session load "
        "performs one encrypted durable session read."
    )

    monkeypatch.delenv("SPEC_KITTY_DISABLE_SESSION_HOT_PATH", raising=False)
    _reset_read_count()
    assert all(_new_process_load_only(store_dir) for _ in range(process_count))
    hot_path_durable_reads = _CountingFastFileStorage.durable_read_count

    assert hot_path_durable_reads == 0
    assert hot_path_durable_reads < baseline_durable_reads


def test_is_authenticated_materializes_fresh_summary_before_true(
    tmp_path: Path,
) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())

    _reset_read_count()
    tm = TokenManager(storage)
    tm.load_from_storage_sync()
    assert tm._session is None
    assert tm._hot_path_summary is not None
    assert _CountingFastFileStorage.durable_read_count == 0

    assert tm.is_authenticated is True

    assert tm.get_current_session() is not None
    assert _CountingFastFileStorage.durable_read_count == 1


def test_deleted_durable_session_after_summary_is_not_authenticated(
    tmp_path: Path,
) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())

    tm = TokenManager(storage)
    tm.load_from_storage_sync()
    assert tm._session is None
    assert tm._hot_path_summary is not None

    storage.delete()

    assert tm.is_authenticated is False
    assert tm.get_current_session() is None


def test_missing_handoff_falls_back_to_encrypted_storage(tmp_path: Path) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())
    invalidate_session_hot_path(store_dir)

    _reset_read_count()
    assert _new_process_auth_check(store_dir) is True

    assert _CountingFastFileStorage.durable_read_count == 1
    assert handoff_path_for_store(store_dir).exists()


def test_stale_handoff_falls_back_to_encrypted_storage(tmp_path: Path) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())
    handoff_path_for_store(store_dir).write_text(
        '{"schema_version": 1, "generated_at": 0, "max_age_seconds": 30, '
        '"durable_fingerprint": {}, "refresh_token_expires_at": null}',
        encoding="utf-8",
    )

    _reset_read_count()
    assert _new_process_auth_check(store_dir) is True

    assert _CountingFastFileStorage.durable_read_count == 1


def test_stale_in_process_summary_returns_durable_auth_result(
    tmp_path: Path,
) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())

    _reset_read_count()
    tm = TokenManager(storage)
    tm.load_from_storage_sync()
    assert tm._session is None
    assert tm._hot_path_summary is not None
    assert _CountingFastFileStorage.durable_read_count == 0

    tm._hot_path_summary = replace(
        tm._hot_path_summary,
        not_after_monotonic=time.monotonic() - 1,
    )

    assert tm.is_authenticated is True
    assert tm._session is not None
    assert _CountingFastFileStorage.durable_read_count == 1


def test_durable_fingerprint_oserror_is_hot_path_miss(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())

    def raise_deleted_durable_file(_cred_file: Path) -> dict[str, int]:
        raise OSError("session deleted during hot-path load")

    monkeypatch.setattr(
        session_hot_path,
        "_durable_fingerprint",
        raise_deleted_durable_file,
    )

    assert load_session_hot_path(store_dir) is None


def test_naive_refresh_expiry_is_hot_path_miss(tmp_path: Path) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())
    payload = {
        "schema_version": 1,
        "generated_at": time.time(),
        "max_age_seconds": 30,
        "durable_fingerprint": session_hot_path._durable_fingerprint(
            store_dir / "session.json"
        ),
        "refresh_token_expires_at": "2026-01-01T00:00:00",
    }
    handoff_path_for_store(store_dir).write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    assert load_session_hot_path(store_dir) is None


def test_publish_fingerprint_oserror_is_best_effort_miss(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store_dir = tmp_path / "auth"
    store_dir.mkdir()
    (store_dir / "session.json").write_text("{}", encoding="utf-8")

    def raise_deleted_durable_file(_cred_file: Path) -> dict[str, int]:
        raise OSError("session deleted during hot-path publish")

    monkeypatch.setattr(
        session_hot_path,
        "_durable_fingerprint",
        raise_deleted_durable_file,
    )

    publish_session_hot_path(store_dir, _make_session())

    assert not handoff_path_for_store(store_dir).exists()


def test_non_path_like_storage_store_path_bypasses_hot_path() -> None:
    session = _make_session()
    storage = Mock()
    storage.store_path = Mock()
    storage.read.return_value = session

    tm = TokenManager(storage)
    tm.load_from_storage_sync()

    assert tm.is_authenticated is True
    assert tm.get_current_session() is session
    storage.read.assert_called_once_with()


def test_publish_failure_does_not_clear_loaded_durable_session(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    session = _make_session()
    storage.write(session)
    invalidate_session_hot_path(store_dir)

    def raise_publish_failure(_store_dir: Path, _session: StoredSession) -> None:
        raise OSError("cannot write derived hot-path handoff")

    monkeypatch.setattr(
        token_manager_module,
        "publish_session_hot_path",
        raise_publish_failure,
    )

    tm = TokenManager(storage)
    tm.load_from_storage_sync()

    assert tm.get_current_session() == session
    assert tm.is_authenticated is True


def test_clear_session_invalidates_handoff(tmp_path: Path) -> None:
    store_dir = tmp_path / "auth"
    storage = _CountingFastFileStorage(base_dir=store_dir)
    storage.write(_make_session())
    assert handoff_path_for_store(store_dir).exists()

    tm = TokenManager(storage)
    tm.load_from_storage_sync()
    tm.clear_session()

    assert not handoff_path_for_store(store_dir).exists()
    assert storage.read() is None


async def test_hot_path_materializes_before_refresh_and_preserves_single_flight(
    auth_store_root: Path,
    monkeypatch,
) -> None:
    class _CountingRefreshFlow:
        call_count = 0

        async def refresh(self, session: StoredSession) -> StoredSession:
            type(self).call_count += 1
            await asyncio.sleep(0.01)
            now = datetime.now(UTC)
            return StoredSession(
                user_id=session.user_id,
                email=session.email,
                name=session.name,
                teams=session.teams,
                default_team_id=session.default_team_id,
                access_token="at_rotated_v2",
                refresh_token="rt_rotated_v2",
                session_id=session.session_id,
                issued_at=now,
                access_token_expires_at=now + timedelta(seconds=900),
                refresh_token_expires_at=session.refresh_token_expires_at,
                scope=session.scope,
                storage_backend=session.storage_backend,
                last_used_at=now,
                auth_method=session.auth_method,
            )

    flows_pkg = types.ModuleType("specify_cli.auth.flows")
    flows_pkg.__path__ = []
    refresh_module = types.ModuleType("specify_cli.auth.flows.refresh")
    refresh_module.TokenRefreshFlow = _CountingRefreshFlow  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "specify_cli.auth.flows", flows_pkg)
    monkeypatch.setitem(sys.modules, "specify_cli.auth.flows.refresh", refresh_module)

    FileFallbackStorage(base_dir=auth_store_root).write(
        _make_session(access_expires_in=-1)
    )
    tm_a = TokenManager(FileFallbackStorage(base_dir=auth_store_root))
    tm_b = TokenManager(FileFallbackStorage(base_dir=auth_store_root))
    tm_a.load_from_storage_sync()
    tm_b.load_from_storage_sync()

    tokens = await asyncio.gather(tm_a.get_access_token(), tm_b.get_access_token())

    assert sorted(tokens) == ["at_rotated_v2", "at_rotated_v2"]
    assert _CountingRefreshFlow.call_count == 1
