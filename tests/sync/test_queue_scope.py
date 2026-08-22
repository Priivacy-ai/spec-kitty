"""Behavioral tests for the extracted ``specify_cli.sync.queue_scope`` module.

R3-T1 (m1-contract-drafts/R3.md §2.1a) extracts the scope-resolution half of
``sync/queue.py`` (``build_queue_scope``, ``scope_db_path``,
``read_active_scope``/``write_active_scope``,
``read_queue_scope_from_credentials``, ``read_queue_scope_from_session``,
``default_queue_db_path``, ``_legacy_queue_db_path``,
``detect_legacy_rows_for_scope``, ``LegacyRowCounts``) into a new, small,
retained, pure module with no dependency on anything transport-specific
(no ``OfflineQueue``, no journal writes). This file exercises that module
directly; ``tests/sync/test_credential_scope_signal.py`` continues to cover
the same behaviour reached through ``specify_cli.sync.queue``'s backward-
compatible re-export.

Isolation: every test pins ``SPEC_KITTY_HOME``/``HOME`` (+ platform
equivalents) to a throwaway temp root, per the pattern in
``test_credential_scope_signal.py`` — this dev box's real ``~/.spec-kitty`` is
a live root; pinning only ``HOME`` is insufficient.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast]


@pytest.fixture
def isolated_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    return tmp_path


# ---------------------------------------------------------------------------
# Module identity / no transport dependency
# ---------------------------------------------------------------------------


def test_queue_scope_module_imports_with_no_transport_dependency() -> None:
    """``queue_scope`` must import cleanly with zero references to the
    transport class it was split out of (R3.md §2.1a: "no dependency on
    anything transport-specific").
    """
    import specify_cli.sync.queue_scope as queue_scope

    assert not hasattr(queue_scope, "OfflineQueue")
    assert not hasattr(queue_scope, "OfflineQueueFull")


def test_transport_module_reexports_identical_objects_for_compat() -> None:
    """``specify_cli.sync.queue`` keeps re-exporting the same objects (not
    copies) for the ~50 existing test/production call sites that still import
    scope helpers from the transport module during the R2-pending transition.
    """
    import specify_cli.sync.queue as queue
    import specify_cli.sync.queue_scope as queue_scope

    assert queue.build_queue_scope is queue_scope.build_queue_scope
    assert queue.scope_db_path is queue_scope.scope_db_path
    assert queue.read_active_scope is queue_scope.read_active_scope
    assert queue.read_queue_scope_from_credentials is queue_scope.read_queue_scope_from_credentials
    assert queue.read_queue_scope_from_session is queue_scope.read_queue_scope_from_session
    assert queue.default_queue_db_path is queue_scope.default_queue_db_path
    assert queue._legacy_queue_db_path is queue_scope._legacy_queue_db_path
    assert queue.detect_legacy_rows_for_scope is queue_scope.detect_legacy_rows_for_scope
    assert queue.LegacyRowCounts is queue_scope.LegacyRowCounts


# ---------------------------------------------------------------------------
# build_queue_scope / scope_db_path
# ---------------------------------------------------------------------------


def test_build_queue_scope_is_deterministic_and_case_insensitive() -> None:
    from specify_cli.sync.queue_scope import build_queue_scope

    a = build_queue_scope("https://Example.com", "User@Example.com", "Team-Slug")
    b = build_queue_scope("https://example.com", "user@example.com", "team-slug")
    assert a == b
    assert len(a) == 64  # sha256 hexdigest


def test_scope_db_path_embeds_scope_under_queues_dir(isolated_home: Path) -> None:
    from specify_cli.sync.queue_scope import scope_db_path

    path = scope_db_path("abc123")
    assert path.name == "queue-abc123.db"
    assert path.parent.name == "queues"


# ---------------------------------------------------------------------------
# active-scope read/write roundtrip
# ---------------------------------------------------------------------------


def test_active_scope_roundtrip(isolated_home: Path) -> None:
    from specify_cli.sync.queue_scope import read_active_scope, write_active_scope

    assert read_active_scope() is None
    write_active_scope("some-scope-token")
    assert read_active_scope() == "some-scope-token"


# ---------------------------------------------------------------------------
# read_queue_scope_from_credentials — TOML / JSON forms (mirrors
# test_credential_scope_signal.py, exercised directly against queue_scope)
# ---------------------------------------------------------------------------


def test_read_queue_scope_from_credentials_toml_form(isolated_home: Path) -> None:
    from specify_cli.sync.queue_scope import read_queue_scope_from_credentials

    creds = isolated_home / "credentials"
    creds.write_text(
        '[user]\nusername = "tester@example.com"\nteam_slug = "t-private"\n'
        '[server]\nurl = "https://spec-kitty-dev.fly.dev"\n',
        encoding="utf-8",
    )
    assert (
        read_queue_scope_from_credentials()
        == "https://spec-kitty-dev.fly.dev|tester@example.com|t-private"
    )


def test_read_queue_scope_from_credentials_explicit_json_wins(isolated_home: Path) -> None:
    from specify_cli.sync.queue_scope import read_queue_scope_from_credentials

    creds = isolated_home / "credentials"
    creds.write_text('{"queue_scope": "explicit-token"}', encoding="utf-8")
    assert read_queue_scope_from_credentials() == "explicit-token"


def test_read_queue_scope_from_credentials_absent_yields_none(isolated_home: Path) -> None:
    from specify_cli.sync.queue_scope import read_queue_scope_from_credentials

    assert not (isolated_home / "credentials").exists()
    assert read_queue_scope_from_credentials() is None


def test_read_queue_scope_from_credentials_non_utf8_bytes_yields_none(isolated_home: Path) -> None:
    """A credentials file that is not valid UTF-8 (binary garbage, a
    truncated/corrupted write, or a stray unrelated file at that path) must
    yield ``None``, not raise. The function's own docstring promises
    "Defensive by contract: a missing/corrupt/incomplete file yields None
    rather than raising" — that guarantee must hold for encoding failures
    too, not just TOML-parse/OS/type failures.
    """
    from specify_cli.sync.queue_scope import read_queue_scope_from_credentials

    creds = isolated_home / "credentials"
    creds.write_bytes(b"\xff\xfe\x00\x01garbage-not-utf8\xff\xfe")
    assert read_queue_scope_from_credentials() is None


# ---------------------------------------------------------------------------
# Legacy-path stubs — WP10-migration-only, must raise, never resolve silently
# ---------------------------------------------------------------------------


def test_default_queue_db_path_raises_legacy_migration_required() -> None:
    from specify_cli.sync.queue_scope import (
        LegacyQueueMigrationRequiredError,
        default_queue_db_path,
    )

    with pytest.raises(LegacyQueueMigrationRequiredError):
        default_queue_db_path()


def test_detect_legacy_rows_for_scope_raises_legacy_migration_required() -> None:
    from specify_cli.sync.queue_scope import (
        LegacyQueueMigrationRequiredError,
        detect_legacy_rows_for_scope,
    )

    with pytest.raises(LegacyQueueMigrationRequiredError):
        detect_legacy_rows_for_scope("any-scope")


def test_legacy_queue_db_path_is_under_spec_kitty_home(isolated_home: Path) -> None:
    from specify_cli.sync.queue_scope import _legacy_queue_db_path

    path = _legacy_queue_db_path()
    assert path == isolated_home / "queue.db"
