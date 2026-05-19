"""Unit tests for :mod:`specify_cli.sync.preflight`.

Covers the contract in
``kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-boundary-preflight.md``:

- ``collect_foreground_identity`` returns concrete values when auth is
  configured and ``None`` only on ``server_url`` / ``team_or_user`` when
  unauthenticated.
- ``run_preflight`` is read-only and composes the existing daemon-owner
  and queue-detection helpers.
- ``PreflightResult.ok`` matches the data-model invariant exactly.
- Refusal output (``render``) stays within the NFR-004 25-line budget.
- ``to_dict`` is JSON-serialisable.
- ``run_preflight`` completes within the NFR-003 100 ms budget on a
  coherent host.

Cross-platform isolation (C-008): tests patch ``pathlib.Path.home()`` to
redirect the operator's home into ``tmp_path``. ``Path.home()`` resolves
``USERPROFILE`` on Windows and ``HOME`` on POSIX, so the same fixtures
run on Linux, macOS, and Windows 10+. Tests also set ``HOME``,
``USERPROFILE``, and ``LOCALAPPDATA`` to ``tmp_path`` for any helper that
still reads the environment directly.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

# Public surface under test
from specify_cli.sync.preflight import (
    ForegroundIdentity,
    MismatchField,
    OwnerMismatch,
    PreflightResult,
    collect_foreground_identity,
    run_preflight,
)

# Existing modules the preflight composes.
from specify_cli.sync.owner import (
    DaemonOwnerRecord,
    owner_record_path,
    write_owner_record,
)


# ---------------------------------------------------------------------------
# Cross-platform home isolation (C-008)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _scoped_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin ``Path.home()`` (and env equivalents) to ``tmp_path``.

    Patching ``pathlib.Path.home`` works on every platform because both
    POSIX (``HOME``) and Windows (``USERPROFILE``) resolve through the
    same classmethod. We also set the env vars so any helper that reads
    the environment directly still lands under ``tmp_path``.
    """
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    return tmp_path


@pytest.fixture
def patched_legacy_counts(monkeypatch: pytest.MonkeyPatch):
    """Return a setter that overrides ``detect_legacy_rows_for_scope``."""

    def _set(counts: dict[str, int]) -> None:
        from specify_cli.sync import queue as queue_mod

        def fake(scope: str) -> dict[str, int]:
            del scope
            return dict(counts)

        monkeypatch.setattr(queue_mod, "detect_legacy_rows_for_scope", fake)

    return _set


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_foreground(
    *,
    package_version: str = "3.2.0",
    executable_path: Path | None = None,
    source_path: Path | None = None,
    server_url: str | None = "https://spec-kitty-dev.fly.dev",
    team_or_user: str | None = "tester@example.com/t-private",
    queue_db_path: Path | None = None,
    pid: int | None = None,
) -> ForegroundIdentity:
    """Build a stable :class:`ForegroundIdentity` for tests."""
    return ForegroundIdentity(
        package_version=package_version,
        executable_path=executable_path or Path(sys.executable).resolve(),
        source_path=source_path or Path(__file__).resolve().parents[2],
        server_url=server_url,
        team_or_user=team_or_user,
        queue_db_path=queue_db_path or Path.home() / ".spec-kitty" / "queues" / "queue-test.db",
        pid=pid if pid is not None else os.getpid(),
    )


def _write_record(**overrides: Any) -> DaemonOwnerRecord:
    """Write a :class:`DaemonOwnerRecord` to disk and return it."""
    foreground = _make_foreground()
    defaults: dict[str, Any] = dict(
        pid=os.getpid(),
        port=9400,
        token="deadbeefcafebabe",
        package_version=foreground.package_version,
        executable_path=str(foreground.executable_path),
        source_checkout_path=str(foreground.source_path),
        server_url=foreground.server_url or "",
        auth_principal="tester@example.com",
        auth_team="t-private",
        auth_scope="https://spec-kitty-dev.fly.dev|tester@example.com|t-private",
        queue_db_path=str(foreground.queue_db_path),
        started_at="2026-05-18T08:00:00+00:00",
    )
    defaults.update(overrides)
    record = DaemonOwnerRecord(**defaults)
    write_owner_record(record)
    return record


def _spawn_then_reap_pid() -> int:
    """Spawn a subprocess, wait for it to exit, return its dead PID."""
    proc = subprocess.Popen(  # noqa: S603 — controlled command
        [sys.executable, "-c", "import sys; sys.exit(0)"],
    )
    proc.wait(timeout=5)
    return proc.pid


def _render_to_text(result: PreflightResult) -> str:
    """Render *result* to a captured string buffer."""
    buf = io.StringIO()
    console = Console(file=buf, width=120, force_terminal=False, color_system=None)
    result.render(console)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests: collect_foreground_identity
# ---------------------------------------------------------------------------


def test_collect_foreground_identity_returns_paths_and_pid(tmp_path: Path) -> None:
    identity = collect_foreground_identity(repo_root=tmp_path)
    assert isinstance(identity, ForegroundIdentity)
    assert isinstance(identity.executable_path, Path)
    assert identity.executable_path.is_absolute()
    assert isinstance(identity.source_path, Path)
    assert identity.source_path.is_absolute()
    assert isinstance(identity.queue_db_path, Path)
    assert identity.pid == os.getpid()
    assert isinstance(identity.package_version, str)


def test_collect_foreground_identity_none_when_unauthenticated(tmp_path: Path) -> None:
    """No credentials on disk → ``server_url`` and ``team_or_user`` are None."""
    identity = collect_foreground_identity(repo_root=tmp_path)
    # Tmp HOME means no credentials and no active session → unauthenticated.
    assert identity.server_url is None
    assert identity.team_or_user is None


# ---------------------------------------------------------------------------
# Tests: run_preflight — happy path
# ---------------------------------------------------------------------------


def test_run_preflight_ok_on_coherent_host(
    tmp_path: Path, patched_legacy_counts
) -> None:
    """No owner record, empty legacy queue, authed foreground → ok=True."""
    patched_legacy_counts({})
    foreground = _make_foreground()
    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)
    assert result.ok is True
    assert result.mismatches == ()
    assert result.orphan_records == ()
    assert result.legacy_event_rows == 0
    assert result.legacy_body_upload_rows == 0
    assert result.auth_present is True


def test_run_preflight_is_read_only(
    tmp_path: Path, patched_legacy_counts, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preflight must not touch ``write_owner_record`` or HTTP libraries."""
    patched_legacy_counts({})

    from specify_cli.sync import preflight as preflight_mod

    def boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("preflight must not write owner record")

    # `write_owner_record` is not imported by preflight, but the mismatch
    # path that compares records must not need it; assert defensively.
    from specify_cli.sync import owner as owner_mod

    monkeypatch.setattr(owner_mod, "write_owner_record", boom, raising=False)
    monkeypatch.setattr(preflight_mod, "_count_legacy_rows_for_scope", lambda fg: (0, 0))

    foreground = _make_foreground()
    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)
    assert result.ok is True


def test_run_preflight_is_read_only_on_default_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: ``run_preflight(foreground=None)`` must not migrate legacy rows.

    Cycle-2 reviewer reproduction: the previous implementation called
    ``default_queue_db_path()`` while collecting the foreground identity.
    That helper invokes ``_migrate_legacy_queue_to_scope`` as a side
    effect whenever an auth scope exists, which (a) violates T003's
    read-only contract and (b) erases the legacy rows the preflight is
    supposed to *report on*.

    This test creates authenticated credentials plus a legacy queue
    holding one ``queue`` row for the active scope and asserts that
    after ``run_preflight(foreground=None)`` runs:

    - the legacy DB row count is unchanged (still 1);
    - no scoped queue DB file was created;
    - the preflight surfaces the legacy row in ``legacy_event_rows`` /
      ``legacy_rows_for_scope``.
    """
    import sqlite3
    import time

    # Cross-platform home isolation per C-008. Set HOME early so all
    # ``Path.home()``-relative helpers (credentials, legacy DB, scoped
    # DB dir) anchor in tmp_path.
    spec_kitty_dir = tmp_path / ".spec-kitty"
    spec_kitty_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write authenticated credentials so the scope resolver finds
    #    an auth scope. The TOML schema matches
    #    ``read_queue_scope_from_credentials``: [user]/[server] tables.
    credentials = spec_kitty_dir / "credentials"
    credentials.write_text(
        "[user]\n"
        'username = "tester@example.com"\n'
        'team_slug = "t-private"\n'
        "[server]\n"
        'url = "https://spec-kitty-dev.fly.dev"\n',
        encoding="utf-8",
    )

    # 2. Seed the legacy queue DB at ~/.spec-kitty/queue.db with one row.
    #    We write the minimal schema by hand (UNIQUE event_id) so the
    #    test does not depend on the live ``OfflineQueue._init_db``
    #    surface.
    legacy_db = spec_kitty_dir / "queue.db"
    conn = sqlite3.connect(legacy_db)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                retry_count INTEGER DEFAULT 0,
                coalesce_key TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO queue (event_id, event_type, data, timestamp) VALUES (?,?,?,?)",
            ("evt-legacy-1", "test_event", "{}", int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()

    # Sanity: legacy DB has exactly one row before the preflight runs.
    def _legacy_count() -> int:
        c = sqlite3.connect(legacy_db)
        try:
            return int(c.execute("SELECT COUNT(*) FROM queue").fetchone()[0])
        finally:
            c.close()

    assert _legacy_count() == 1

    # 3. Run preflight with foreground=None so the code path that
    #    collected foreground identity (and historically triggered
    #    migration) is exercised.
    result = run_preflight(repo_root=tmp_path, foreground=None, require_auth=True)

    # 4a. Legacy DB row count MUST be unchanged.
    assert _legacy_count() == 1, (
        "run_preflight() must not migrate legacy rows on the default code path"
    )

    # 4b. No scoped queue DB file should have been created.
    scoped_queue_dir = spec_kitty_dir / "queues"
    if scoped_queue_dir.exists():
        scoped_dbs = list(scoped_queue_dir.glob("queue-*.db"))
        assert scoped_dbs == [], (
            f"run_preflight() must not create a scoped DB on the default path; "
            f"found: {scoped_dbs!r}"
        )

    # 4c. The preflight should report the legacy row so the operator can
    #     act on it. We do not assert on ``ok`` here — that depends on
    #     the live ``detect_legacy_rows_for_scope`` reading the legacy
    #     DB; the contract under test is the read-only guarantee.
    assert result.legacy_event_rows >= 1
    assert result.legacy_rows_for_scope >= 1


# ---------------------------------------------------------------------------
# Tests: per-field mismatches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field_name,record_kwargs,foreground_kwargs",
    [
        (
            "daemon_package_version",
            {"package_version": "3.2.0rc10"},
            {"package_version": "3.2.0rc11"},
        ),
        (
            # Both sides must point at *existing* files so the daemon
            # record is not flagged as orphan (which would short-circuit
            # the mismatch comparison entirely). __file__ is guaranteed
            # to exist for the duration of the test process.
            "daemon_executable_path",
            {"executable_path": __file__},
            {},
        ),
        (
            "daemon_source_path",
            {"source_checkout_path": str(Path(__file__).parent)},
            {},
        ),
        (
            "daemon_server_url",
            {"server_url": "https://other.example.com"},
            {},
        ),
        (
            "daemon_team_or_user",
            {"auth_principal": "other@example.com", "auth_team": "t-other"},
            {},
        ),
        (
            "daemon_queue_db_path",
            {"queue_db_path": "/var/lib/other/queue.db"},
            {},
        ),
    ],
)
def test_run_preflight_refuses_on_per_field_mismatch(
    tmp_path: Path,
    patched_legacy_counts,
    field_name: str,
    record_kwargs: dict[str, Any],
    foreground_kwargs: dict[str, Any],
) -> None:
    """Each canonical field surfaces its own mismatch entry."""
    patched_legacy_counts({})
    _write_record(**record_kwargs)
    foreground = _make_foreground(**foreground_kwargs)

    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)
    assert result.ok is False
    fields = [m.field for m in result.mismatches]
    assert field_name in fields, (
        f"Expected {field_name!r} in mismatches; got {fields!r}"
    )


def test_run_preflight_accepts_daemon_executable_symlink(
    tmp_path: Path, patched_legacy_counts
) -> None:
    """Regression: pipx-installed CLIs may record symlinked ``sys.executable``."""
    patched_legacy_counts({})
    symlink = tmp_path / Path(sys.executable).name
    try:
        symlink.symlink_to(Path(sys.executable))
    except OSError as exc:
        pytest.skip(f"symlink unavailable on this platform: {exc}")

    _write_record(executable_path=str(symlink))
    foreground = _make_foreground(executable_path=Path(sys.executable).resolve())

    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)

    assert result.ok is True
    assert [m.field for m in result.mismatches] == []


def test_canonical_mismatch_field_names_are_exact() -> None:
    """The :class:`MismatchField` Literal carries exactly six canonical names."""
    import typing

    # typing.get_args resolves the literal members.
    members = set(typing.get_args(MismatchField))
    assert members == {
        "daemon_package_version",
        "daemon_executable_path",
        "daemon_source_path",
        "daemon_server_url",
        "daemon_team_or_user",
        "daemon_queue_db_path",
    }


# ---------------------------------------------------------------------------
# Tests: orphan record refusal
# ---------------------------------------------------------------------------


def test_run_preflight_refuses_on_orphan_record(
    tmp_path: Path, patched_legacy_counts
) -> None:
    """Owner record with a dead PID becomes an orphan → ok=False."""
    patched_legacy_counts({})
    dead_pid = _spawn_then_reap_pid()
    _write_record(pid=dead_pid)
    foreground = _make_foreground()

    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)

    assert result.ok is False
    assert len(result.orphan_records) >= 1
    # Orphan records do not generate field-level mismatches.
    assert result.mismatches == ()


# ---------------------------------------------------------------------------
# Tests: legacy rows refusal
# ---------------------------------------------------------------------------


def test_run_preflight_refuses_on_legacy_event_rows(
    tmp_path: Path, patched_legacy_counts
) -> None:
    patched_legacy_counts({"sync_events": 3})
    foreground = _make_foreground()
    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)
    assert result.ok is False
    assert result.legacy_event_rows == 3
    assert result.legacy_body_upload_rows == 0
    assert result.legacy_rows_for_scope == 3


def test_run_preflight_refuses_on_legacy_body_upload_rows(
    tmp_path: Path, patched_legacy_counts
) -> None:
    """Body-upload rows trigger refusal independently of event rows."""
    patched_legacy_counts({"body_upload_queue": 2})
    foreground = _make_foreground()
    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)
    assert result.ok is False
    assert result.legacy_event_rows == 0
    assert result.legacy_body_upload_rows == 2
    assert result.legacy_rows_for_scope == 2


# ---------------------------------------------------------------------------
# Tests: auth-required refusal
# ---------------------------------------------------------------------------


def test_run_preflight_refuses_when_auth_required_and_absent(
    tmp_path: Path, patched_legacy_counts
) -> None:
    """``require_auth=True`` + no auth on foreground → ok=False."""
    patched_legacy_counts({})
    foreground = _make_foreground(server_url=None, team_or_user=None)
    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)
    assert result.ok is False
    assert result.auth_present is False
    assert result.auth_required is True


def test_run_preflight_allows_unauthenticated_when_not_required(
    tmp_path: Path, patched_legacy_counts
) -> None:
    """``require_auth=False`` + no auth → ok=True (everything else clean)."""
    patched_legacy_counts({})
    foreground = _make_foreground(server_url=None, team_or_user=None)
    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=False)
    assert result.ok is True
    assert result.auth_present is False
    assert result.auth_required is False


# ---------------------------------------------------------------------------
# Tests: render / to_dict
# ---------------------------------------------------------------------------


def test_preflight_result_render_noop_when_ok() -> None:
    result = PreflightResult(ok=True, auth_present=True, auth_required=True)
    text = _render_to_text(result)
    assert text == ""


def test_preflight_result_render_within_25_lines() -> None:
    """Worst-case refusal renders in ≤ 25 lines at 80 columns (NFR-004).

    Review cycle 2 tightened this assertion: the test now reproduces the
    reviewer's worst-case scenario (6 mismatched canonical fields + 3
    orphan records + auth absent + legacy rows) using the **real**
    production remediation hints and a normal 80-column terminal. The
    pre-fix render produced 28 lines; the compressed render must stay at
    or under 25.
    """
    from specify_cli.sync.preflight import _REMEDIATION_HINTS

    canonical_fields: tuple[MismatchField, ...] = (
        "daemon_package_version",
        "daemon_executable_path",
        "daemon_source_path",
        "daemon_server_url",
        "daemon_team_or_user",
        "daemon_queue_db_path",
    )
    # IMPORTANT: use the actual production remediation hints (not short
    # placeholder strings) so this test reflects what operators see.
    mismatches = tuple(
        OwnerMismatch(
            field=f,
            foreground_value=f"fg-{f}",
            daemon_value=f"daemon-{f}",
            remediation_hint=_REMEDIATION_HINTS[f],
        )
        for f in canonical_fields
    )

    # Build three throw-away orphan records (the dataclass requires all
    # fields but only the count matters for the render budget).
    orphan = DaemonOwnerRecord(
        pid=99999,
        port=9400,
        token="t",
        package_version="3.2.0",
        executable_path="/bin/python",
        source_checkout_path="/src",
        server_url="https://example.com",
        auth_principal=None,
        auth_team=None,
        auth_scope=None,
        queue_db_path="/tmp/queue.db",
        started_at="2026-05-18T08:00:00+00:00",
    )
    orphans = (orphan, orphan, orphan)

    result = PreflightResult(
        ok=False,
        mismatches=mismatches,
        orphan_records=orphans,
        legacy_event_rows=4,
        legacy_body_upload_rows=1,
        auth_present=False,
        auth_required=True,
    )
    # Render at the standard 80-column width — the NFR-004 budget is
    # specified at a normal operator terminal.
    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=False, color_system=None)
    result.render(console)
    text = buf.getvalue()
    lines = text.splitlines()
    assert len(lines) <= 25, (
        f"render exceeded 25 lines at 80 columns: {len(lines)}\n{text}"
    )
    # And the header line must be present.
    assert any("Sync boundary refused" in ln for ln in lines)


def test_preflight_result_to_dict_is_json_serializable() -> None:
    mismatches = (
        OwnerMismatch(
            field="daemon_package_version",
            foreground_value="3.2.0rc11",
            daemon_value="3.2.0rc10",
            remediation_hint="restart daemon",
        ),
    )
    orphan = DaemonOwnerRecord(
        pid=42,
        port=9400,
        token="secret-token",
        package_version="3.2.0",
        executable_path="/bin/python",
        source_checkout_path="/src",
        server_url="https://example.com",
        auth_principal=None,
        auth_team=None,
        auth_scope=None,
        queue_db_path="/tmp/queue.db",
        started_at="2026-05-18T08:00:00+00:00",
    )
    result = PreflightResult(
        ok=False,
        mismatches=mismatches,
        orphan_records=(orphan,),
        legacy_event_rows=1,
        legacy_body_upload_rows=2,
        auth_present=True,
        auth_required=True,
    )
    payload = result.to_dict()
    # All documented top-level keys.
    for key in (
        "ok",
        "mismatches",
        "orphan_records",
        "legacy_event_rows",
        "legacy_body_upload_rows",
        "legacy_rows_for_scope",
        "auth_present",
        "auth_required",
    ):
        assert key in payload, key
    # Round-trip through json.
    s = json.dumps(payload)
    back = json.loads(s)
    assert back["legacy_rows_for_scope"] == 3
    # Token MUST be redacted in serialised form (defense-in-depth).
    assert back["orphan_records"][0]["token"] == "<redacted>"


def test_preflight_result_is_frozen() -> None:
    """The dataclass is frozen → hashable and assignment-safe for snapshots."""
    result = PreflightResult(ok=True, auth_present=True, auth_required=True)
    with pytest.raises((AttributeError, Exception)):
        result.ok = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: performance budget (NFR-003)
# ---------------------------------------------------------------------------


def test_run_preflight_performance_budget(
    tmp_path: Path, patched_legacy_counts
) -> None:
    """A coherent-host preflight completes in ≤ 100 ms."""
    patched_legacy_counts({})
    foreground = _make_foreground()
    start = time.perf_counter()
    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert result.ok is True
    # Generous headroom for CI noise; the contract is ≤ 100 ms.
    assert elapsed_ms <= 100, f"preflight took {elapsed_ms:.1f} ms (budget 100 ms)"


# ---------------------------------------------------------------------------
# Tests: missing owner record is benign
# ---------------------------------------------------------------------------


def test_run_preflight_when_owner_record_missing(
    tmp_path: Path, patched_legacy_counts
) -> None:
    """No owner record means no mismatches even when foreground is auth'd."""
    patched_legacy_counts({})
    assert not owner_record_path().exists()
    foreground = _make_foreground()
    result = run_preflight(repo_root=tmp_path, foreground=foreground, require_auth=True)
    assert result.mismatches == ()
    assert result.ok is True


# ---------------------------------------------------------------------------
# Tests: cycle-3 regression — no SaaS round-trip via TokenManager rehydrate
# ---------------------------------------------------------------------------


def test_run_preflight_never_calls_rehydrate_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression for review-cycle-3.

    The preflight contract (``contracts/sync-boundary-preflight.md``) says
    the helper does not call SaaS endpoints. A previous implementation
    routed scope resolution through
    ``specify_cli.sync.queue.read_queue_scope_from_session`` →
    ``resolve_private_team_id_for_ingress`` →
    ``TokenManager.rehydrate_membership_if_needed`` → ``GET /api/v1/me``
    whenever the current session lacked a Private Teamspace in memory.
    That violates the contract.

    This test installs an in-memory session WITHOUT a Private Teamspace
    (so the legacy code path would have fired the rehydrate), monkeypatches
    ``TokenManager.rehydrate_membership_if_needed`` to raise, and asserts
    that ``run_preflight`` produces a result without invoking it.

    It also asserts the same property for
    ``resolve_private_team_id_for_ingress`` — both helpers must remain
    untouched on the preflight code path.
    """
    from specify_cli.auth import manager as auth_manager
    from specify_cli.auth import session as session_mod
    from specify_cli.auth.session import StoredSession, Team
    from specify_cli.auth.token_manager import TokenManager
    from datetime import datetime, UTC

    # Build a session whose teams list has NO Private Teamspace. The legacy
    # ``read_queue_scope_from_session`` path would call
    # ``resolve_private_team_id_for_ingress`` here, which would then call
    # ``rehydrate_membership_if_needed`` to fetch ``/api/v1/me``.
    shared_team = Team(
        id="shared-team",
        name="Shared Team",
        role="member",
        is_private_teamspace=False,
    )
    now = datetime.now(UTC)
    session = StoredSession(
        user_id="u-1",
        email="tester@example.com",
        name="Test User",
        teams=[shared_team],  # no Private Teamspace
        default_team_id="shared-team",
        access_token="tok-access",
        refresh_token="tok-refresh",
        session_id="sess-1",
        issued_at=now,
        access_token_expires_at=now,  # value irrelevant; preflight does not refresh
        refresh_token_expires_at=None,
        scope="read",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )

    # Install a TokenManager whose ``get_current_session`` returns our
    # private-team-less session. We bypass disk storage by hand-installing
    # the manager into the process-wide singleton slot used by
    # ``get_token_manager``.
    class _StubStorage:
        store_path = None

        def read(self) -> StoredSession:
            return session

        def write(self, _s: StoredSession) -> None:  # pragma: no cover — defensive
            raise AssertionError("preflight must not write the session")

        def delete(self) -> None:  # pragma: no cover — defensive
            raise AssertionError("preflight must not delete the session")

    tm = TokenManager(_StubStorage())  # type: ignore[arg-type]
    tm._session = session  # noqa: SLF001 — direct injection for test isolation
    monkeypatch.setattr(auth_manager, "_tm", tm, raising=False)

    # Tripwire 1: rehydrate must NEVER be called from preflight.
    def _rehydrate_tripwire(self: TokenManager, *, force: bool = False) -> bool:
        raise AssertionError(
            "TokenManager.rehydrate_membership_if_needed must not be called "
            "during preflight (would issue GET /api/v1/me)"
        )

    monkeypatch.setattr(
        TokenManager,
        "rehydrate_membership_if_needed",
        _rehydrate_tripwire,
    )

    # Tripwire 2: the ingress resolver also embeds the rehydrate step;
    # preflight should not reach it either.
    from specify_cli.sync import _team as team_mod

    def _resolve_tripwire(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "resolve_private_team_id_for_ingress must not be called during "
            "preflight (transitively invokes rehydrate_membership_if_needed)"
        )

    monkeypatch.setattr(
        team_mod,
        "resolve_private_team_id_for_ingress",
        _resolve_tripwire,
    )
    # Also patch the symbol on the queue module, where ``read_queue_scope_from_session``
    # imports it locally (so any future caller that re-introduces that path would trip).
    from specify_cli.sync import queue as queue_mod

    monkeypatch.setattr(
        queue_mod,
        "resolve_private_team_id_for_ingress",
        _resolve_tripwire,
        raising=False,
    )

    # Tripwire 3: never let the legacy helper fire on the preflight path.
    def _read_queue_scope_from_session_tripwire() -> str | None:
        raise AssertionError(
            "read_queue_scope_from_session must not be called during preflight "
            "(transitively invokes rehydrate_membership_if_needed)"
        )

    monkeypatch.setattr(
        queue_mod,
        "read_queue_scope_from_session",
        _read_queue_scope_from_session_tripwire,
    )

    # Keep legacy-rows counting cheap & deterministic.
    def _zero_legacy(scope: str) -> dict[str, int]:
        del scope
        return {}

    monkeypatch.setattr(queue_mod, "detect_legacy_rows_for_scope", _zero_legacy)

    # Reset auth manager singleton back to None after the test so other
    # tests don't see our stub. monkeypatch.setattr above handles the
    # restoration automatically; this is belt-and-braces.
    monkeypatch.setattr(auth_manager, "_tm", tm, raising=False)

    # Execute: run_preflight with foreground=None so the full code path
    # that collects identity (and used to fire the rehydrate) runs.
    result = run_preflight(
        repo_root=tmp_path, foreground=None, require_auth=True
    )

    # The contract under test is "no SaaS round-trip", surfaced as
    # "rehydrate tripwires did not fire". The preflight should still
    # produce a structured result regardless of ok/refusal.
    assert isinstance(result, PreflightResult)

    # And the in-memory session helper itself remains pure — proves we
    # never mutated session state in the process.
    assert session_mod.require_private_team_id(session) is None
    # Sanity: cleanup will restore the singleton; nothing leaked.
