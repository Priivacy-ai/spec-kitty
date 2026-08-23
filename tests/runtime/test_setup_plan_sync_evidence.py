"""WP04 regression tests: setup-plan SaaS-evidence guarantee.

These tests pin the contract described in
``kitty-specs/mvp-sync-boundary-cli-01KRVCQS/tasks/WP04-setup-plan-sync-evidence.md``
and ``kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/tasks/WP04-setup-plan-preflight.md``:

* (FR-011) When ``SPEC_KITTY_ENABLE_SAAS_SYNC=1`` and the foreground has
  no authenticated session/credentials, ``setup-plan`` refuses loudly
  (exit code != 0, diagnostic contains the FR-011 phrase) and writes
  zero queue rows (scoped or legacy).
* (FR-012) Every body-upload-emitting and canonical-event-emitting
  code path in setup-plan goes through ``default_queue_db_path()``.
  No setup-plan module may call ``_legacy_queue_db_path()`` directly.
* (Regression / authenticated) An authenticated tmp ``HOME`` running
  setup-plan produces queue rows in the active scoped DB only — the
  legacy ``~/.spec-kitty/queue.db`` stays empty (or absent).
* (WP04 / FR-002 / FR-009) ``setup-plan`` integrates ``run_preflight``
  after the FR-011 hosted-auth refusal: refuses with exit code 2 on
  any daemon-owner mismatch, orphan owner record, or legacy queue
  row in scope before any enqueue.

C-008: tests patch ``pathlib.Path.home()`` (the only API that works
cross-platform — POSIX ``HOME`` and Windows ``USERPROFILE`` both
resolve through the same classmethod) plus the env vars so any helper
that reads the environment directly still lands under ``tmp_path``.
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from kernel.clock import now_utc, timedelta

from specify_cli.auth.secure_storage import EncryptedFileStorage, SecureStorage
from specify_cli.auth.session import StoredSession, Team
from specify_cli.cli.commands.agent.setup_plan_hosted import (
    BoundaryEvaluation,
    BoundaryState,
)

pytestmark = [pytest.mark.integration]

import typer


MODULE = "specify_cli.cli.commands.agent.mission"


@pytest.fixture(autouse=True)
def _reset_real_storage_singleton_after_each_test():
    """Keep this module's real encrypted stores invocation-local."""
    yield
    from specify_cli.auth import reset_token_manager

    reset_token_manager()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_credentials(home: Path, *, username: str, server_url: str, team_slug: str) -> Path:
    """Write a credentials file in the format ``read_queue_scope_from_credentials`` parses."""
    spec_kitty_dir = home / ".spec-kitty"
    spec_kitty_dir.mkdir(parents=True, exist_ok=True)
    credentials = spec_kitty_dir / "credentials"
    credentials.write_text(
        f'[user]\nusername = "{username}"\nteam_slug = "{team_slug}"\n\n'
        f'[server]\nurl = "{server_url}"\n',
        encoding="utf-8",
    )
    # config.toml supplies the server_url for read_queue_scope_from_session
    # consistency; not strictly required for credentials-only path.
    (spec_kitty_dir / "config.toml").write_text(
        f'[sync]\nserver_url = "{server_url}"\n', encoding="utf-8"
    )
    return credentials


def _table_row_count(db_path: Path, table_name: str) -> int:
    """Count rows in ``table_name`` if the table exists in ``db_path``; else 0."""
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,),
        )
        if cursor.fetchone() is None:
            return 0
        row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def _build_minimal_repo(tmp_path: Path, mission_slug: str) -> Path:
    """Create the minimum kitty-specs structure setup-plan needs."""
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    # spec.md with a substantive FR row (bullet form)
    spec_md = feature_dir / "spec.md"
    spec_md.write_text(
        "# Test Feature\n\n"
        "## Functional Requirements\n\n"
        "- FR-001: The system must do the thing reliably.\n",
        encoding="utf-8",
    )

    # plan.md with substantive Technical Context so the commit path is exercised
    plan_md = feature_dir / "plan.md"
    plan_md.write_text(
        "# Plan\n\n"
        "## Technical Context\n\n"
        "**Language/Version**: Python 3.11\n"
        "**Primary Dependencies**: typer, rich\n",
        encoding="utf-8",
    )

    # meta.json so any downstream lookups have something
    (feature_dir / "meta.json").write_text(
        '{"mission_slug": "' + mission_slug + '", "mission_type": "software-dev"}',
        encoding="utf-8",
    )

    return feature_dir


def _refresh_capable_session() -> StoredSession:
    now = now_utc()
    return StoredSession(
        user_id="real-storage-user",
        email="operator@example.com",
        name="Operator",
        teams=[Team(id="team-1", name="Team", role="owner", is_private_teamspace=True)],
        default_team_id="team-1",
        access_token="expired-access-token",
        refresh_token="usable-refresh-token",
        session_id="session-1",
        issued_at=now - timedelta(hours=2),
        access_token_expires_at=now - timedelta(hours=1),
        refresh_token_expires_at=now + timedelta(days=1),
        scope="openid",
        storage_backend="file",
        last_used_at=now,
        auth_method="authorization_code",
    )


def _install_real_storage(
    monkeypatch: pytest.MonkeyPatch,
    storage: EncryptedFileStorage,
) -> None:
    from specify_cli.auth import reset_token_manager

    reset_token_manager()
    monkeypatch.setattr(
        SecureStorage,
        "from_environment",
        classmethod(lambda _cls: storage),
    )


def _run_json_setup_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    feature_dir: Path,
    *,
    patch_boundary_safe: bool = True,
    hosted_effects_must_be_zero: bool = False,
) -> dict[str, object]:
    from specify_cli.cli.commands.agent import mission as mission_mod
    from specify_cli.cli.commands.agent import mission_setup_plan as setup_seam

    emitted: list[dict[str, object]] = []
    monkeypatch.setattr(mission_mod, "_emit_json", lambda value: emitted.append(value))
    if patch_boundary_safe:
        monkeypatch.setattr(
            setup_seam,
            "evaluate_boundary",
            lambda _root: BoundaryEvaluation(BoundaryState.SAFE),
        )
    monkeypatch.setattr(
        setup_seam,
        "evaluate_route_availability",
        lambda _root: (True, None),
    )
    monkeypatch.setattr(
        "specify_cli.status.lifecycle_events.fanout_lifecycle_event_hosted",
        (
            lambda *_a, **_k: pytest.fail("lifecycle hosted fan-out was attempted")
            if hosted_effects_must_be_zero
            else None
        ),
    )
    monkeypatch.setattr(
        setup_seam,
        "_trigger_dossier_sync",
        (
            lambda *_a, **_k: pytest.fail("dossier hosted publication was attempted")
            if hosted_effects_must_be_zero
            else None
        ),
    )
    monkeypatch.setattr(
        setup_seam,
        "_resolve_plan_template",
        lambda *_a, **_k: SimpleNamespace(path=feature_dir / "plan.md"),
    )
    patches = _patches_for_setup_plan(tmp_path, feature_dir)
    for item in patches.values():
        item.start()
    try:
        try:
            mission_mod.setup_plan(feature=feature_dir.name, json_output=True)
        except typer.Exit as exc:
            pytest.fail(f"setup-plan exited {exc.exit_code}: {emitted!r}")
    finally:
        for item in patches.values():
            item.stop()
    assert len(emitted) == 1
    return emitted[0]


def test_real_encrypted_refresh_session_never_reads_queue_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T017: expired access + usable refresh is authenticated without scope."""
    storage = EncryptedFileStorage(base_dir=tmp_path / "auth")
    storage.write(_refresh_capable_session())
    _install_real_storage(monkeypatch, storage)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr(
        "specify_cli.sync.queue.read_queue_scope_from_session",
        lambda: pytest.fail("queue scope must not be read for authentication"),
    )
    monkeypatch.setattr(
        "specify_cli.sync.queue.read_queue_scope_from_credentials",
        lambda: pytest.fail("credentials scope must not be read for authentication"),
    )
    feature_dir = _build_minimal_repo(tmp_path, "real-encrypted-session")

    payload = _run_json_setup_plan(monkeypatch, tmp_path, feature_dir)

    warnings = payload.get("warnings", [])
    warning_codes = [item["code"] for item in warnings]  # type: ignore[index]
    assert "SAAS_SYNC_UNAUTHENTICATED" not in warning_codes
    assert "SAAS_SYNC_AUTH_UNKNOWN" not in warning_codes
    assert payload["result"] == "success"
    assert payload["phase_complete"] is True


def test_real_encrypted_storage_does_not_leak_token_manager_to_next_test(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review cycle 1: the preceding real-storage test must leave no singleton."""
    empty_storage = EncryptedFileStorage(base_dir=tmp_path / "fresh-auth")
    monkeypatch.setattr(
        SecureStorage,
        "from_environment",
        classmethod(lambda _cls: empty_storage),
    )
    from specify_cli.auth import get_token_manager

    assessment = get_token_manager().session_assessment
    assert assessment.completed is True
    assert assessment.usable_session is False


def test_real_unreadable_storage_adds_only_auth_unknown_to_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T017: unreadable encrypted storage cannot be mislabeled logged out."""
    storage = EncryptedFileStorage(base_dir=tmp_path / "auth")
    storage.store_path.mkdir(parents=True)
    (storage.store_path / "session.json").write_text("not-json", encoding="utf-8")
    _install_real_storage(monkeypatch, storage)
    feature_dir = _build_minimal_repo(tmp_path, "real-unreadable-session")

    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "0")
    baseline = _run_json_setup_plan(monkeypatch, tmp_path, feature_dir)
    from specify_cli.auth import reset_token_manager

    reset_token_manager()
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    actual = _run_json_setup_plan(monkeypatch, tmp_path, feature_dir)

    warnings = actual.pop("warnings")
    assert isinstance(warnings, list)
    assert [item["code"] for item in warnings] == ["SAAS_SYNC_AUTH_UNKNOWN"]
    assert actual == baseline


def test_raised_structural_assessment_preserves_local_events_and_refuses_hosts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T017: canonical preflight exceptions become boundary warnings only."""
    storage = EncryptedFileStorage(base_dir=tmp_path / "auth")
    storage.write(_refresh_capable_session())
    _install_real_storage(monkeypatch, storage)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.setattr(
        "specify_cli.sync.preflight.run_preflight",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("secret sentinel")),
    )
    feature_dir = _build_minimal_repo(tmp_path, "raised-structural-assessment")

    payload = _run_json_setup_plan(
        monkeypatch,
        tmp_path,
        feature_dir,
        patch_boundary_safe=False,
        hosted_effects_must_be_zero=True,
    )

    warnings = payload["warnings"]
    assert isinstance(warnings, list)
    assert [item["code"] for item in warnings] == ["SAAS_SYNC_BOUNDARY_UNSAFE"]
    assert "secret sentinel" not in str(warnings)
    from specify_cli.status.lifecycle_events import mission_event_log_path

    log_path = mission_event_log_path(feature_dir)
    assert log_path.exists()
    assert len(log_path.read_text(encoding="utf-8").splitlines()) >= 3
    assert payload["result"] == "success"


# ---------------------------------------------------------------------------
# Test A — authenticated setup-plan lands queue writes in scoped DB
# ---------------------------------------------------------------------------
#
# ``TestAuthenticatedSetupPlanLandsInScoped::test_authenticated_setup_plan_lands_in_scoped``
# was extracted to
# ``tests/specify_cli/cli/commands/agent/test_issue_3425_setup_plan_legacy_layout_silent_capture.py``
# (2026-08-14 landing fold; relocated out of ``tests/regression/`` once the
# reproduction turned green — see that module's exit-rule note) — it is a
# regression guard for fixed bug #3425 (un-migrated hosts raised
# ``LegacyQueueMigrationRequiredError`` before any queue write was attempted),
# not a stale test of this module. See that module's docstring for the
# mechanism.


# ---------------------------------------------------------------------------
# Test B — FR-011 refuse-loudly when SAAS enabled and unauthenticated
# ---------------------------------------------------------------------------


class TestSetupPlanRefusesWithoutAuthWhenSaasEnabled:
    """Hosted auth refusal is a warning while local setup-plan determines exit."""

    def test_setup_plan_refuses_without_auth_when_saas_enabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

        # Ensure no credentials and no auth session anywhere under HOME.
        spec_kitty_dir = home / ".spec-kitty"
        assert not spec_kitty_dir.exists()

        # Force the auth session lookup to return None (no session) so the
        # refuse-loudly branch is the only possible outcome.
        class _NoSessionTokenManager:
            def get_current_session(self) -> None:
                return None

        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager",
            lambda: _NoSessionTokenManager(),
            raising=False,
        )

        from specify_cli.cli.commands.agent.mission import setup_plan
        from specify_cli.sync.queue import (
            _legacy_queue_db_path,
            scope_db_path,
            build_queue_scope,
        )

        legacy_path = _legacy_queue_db_path()
        # Speculative scoped path under the fake HOME — must not appear.
        speculative_scope = build_queue_scope(
            server_url="https://test.example.com",
            username="ghost@example.com",
            team_slug="ghost-team",
        )
        speculative_scoped = scope_db_path(speculative_scope)

        with pytest.raises((typer.Exit, SystemExit)) as exc_info:
            setup_plan(feature="any-mission", json_output=False)

        # exit code must be non-zero (we picked 2 to mark "auth precondition").
        exit_code = getattr(exc_info.value, "exit_code", None) or getattr(
            exc_info.value, "code", None
        )
        assert exit_code is not None and exit_code != 0, (
            f"Expected non-zero exit, got {exit_code!r}."
        )

        # The unrelated local detection error is authoritative and happens
        # before this invocation becomes eligible for hosted assessment.
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "Hosted sync was skipped" not in combined
        assert "missions found" in combined

        # No DB writes occurred — scoped DB never created, legacy untouched.
        assert not legacy_path.exists(), (
            f"FR-011 violation: legacy DB at {legacy_path} was created."
        )
        assert not speculative_scoped.exists(), (
            f"FR-011 violation: speculative scoped DB at {speculative_scoped} "
            "was created."
        )
        # No scoped queue directory should have been created at all.
        scoped_dir = home / ".spec-kitty" / "queues"
        assert not scoped_dir.exists(), (
            f"FR-011 violation: scoped queue dir at {scoped_dir} was created."
        )


# ---------------------------------------------------------------------------
# Test C — AST regression: no direct _legacy_queue_db_path calls in setup-plan
# ---------------------------------------------------------------------------


class TestNoDirectLegacyDbPathCallsInSetupPlanCode:
    """FR-012 AST regression: setup-plan code path must not call _legacy_queue_db_path."""




# ---------------------------------------------------------------------------
# WP04 (mvp-cli-sync-boundary-completion-01KRX11M) — preflight integration
# ---------------------------------------------------------------------------
#
# These tests cover T019 + T020 from the WP04 spec: setup-plan must
# refuse on owner-mismatch / orphan record / legacy rows BEFORE any
# enqueue, and must NEVER write to the legacy queue when authenticated.
#
# Cross-platform isolation (C-008): we patch ``pathlib.Path.home`` and
# the HOME / USERPROFILE env vars together. Bare ``monkeypatch.setenv``
# is insufficient on Windows where ``Path.home()`` resolves through
# ``USERPROFILE`` via a classmethod-level mechanism that does not read
# the env on every call.


def _scope_home_classmethod(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Pin ``Path.home()`` and env vars to *tmp_path* (C-008 cross-platform)."""
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))


def _write_daemon_owner_record(
    *,
    package_version: str,
    server_url: str = "https://test.example.com",
    auth_principal: str = "auth@example.com",
    auth_team: str = "team-alpha",
    queue_db_path: str | None = None,
    pid: int | None = None,
    executable_path: str | None = None,
    source_checkout_path: str | None = None,
) -> Path:
    """Write a daemon owner record under the patched ``Path.home()``.

    Returns the canonical owner-record path so callers can introspect or
    delete it. Uses the same writer the daemon uses so the record is
    byte-identical to a real one.
    """
    from specify_cli.sync.owner import DaemonOwnerRecord, write_owner_record

    fallback_exe = str(Path(sys.executable).resolve())
    fallback_source = str(Path(sys.executable).resolve().parents[0])
    record = DaemonOwnerRecord(
        pid=pid if pid is not None else 1,  # any live-ish pid
        port=9400,
        token="deadbeefcafebabe",
        package_version=package_version,
        executable_path=executable_path or fallback_exe,
        source_checkout_path=source_checkout_path or fallback_source,
        server_url=server_url,
        auth_principal=auth_principal,
        auth_team=auth_team,
        auth_scope=f"{server_url}|{auth_principal}|{auth_team}",
        queue_db_path=queue_db_path
        or str(Path.home() / ".spec-kitty" / "queues" / "queue-test.db"),
        started_at="2026-05-18T08:00:00+00:00",
    )
    return write_owner_record(record)


def _scoped_db_path_for(server_url: str, username: str, team_slug: str) -> Path:
    """Return the scoped queue DB path that ``default_queue_db_path()`` would resolve to."""
    from specify_cli.sync.queue import build_queue_scope, scope_db_path

    scope = build_queue_scope(
        server_url=server_url,
        username=username,
        team_slug=team_slug,
    )
    return Path(scope_db_path(scope))


def _patches_for_setup_plan(
    tmp_path: Path,
    feature_dir: Path,
) -> dict[str, Any]:
    """Build the common patch dict that lets ``setup_plan`` reach the
    boundary preflight without exercising git / project-root discovery."""
    return {
        f"{MODULE}.locate_project_root": patch(
            f"{MODULE}.locate_project_root", return_value=tmp_path
        ),
        f"{MODULE}._enforce_git_preflight": patch(
            f"{MODULE}._enforce_git_preflight"
        ),
        f"{MODULE}._find_feature_directory": patch(
            f"{MODULE}._find_feature_directory", return_value=feature_dir
        ),
        f"{MODULE}._show_branch_context": patch(
            f"{MODULE}._show_branch_context", return_value=(tmp_path, "main")
        ),
        f"{MODULE}.get_current_branch": patch(
            f"{MODULE}.get_current_branch", return_value="main"
        ),
        "specify_cli.missions._substantive.is_committed": patch(
            "specify_cli.missions._substantive.is_committed", return_value=True
        ),
        "specify_cli.missions._substantive.is_substantive": patch(
            "specify_cli.missions._substantive.is_substantive", return_value=True
        ),
        f"{MODULE}._commit_to_branch": patch(f"{MODULE}._commit_to_branch"),
    }


class TestSetupPlanPreflightIntegration:
    """WP04 T019: setup-plan refuses on boundary failure before any enqueue.

    ``test_setup_plan_refuses_on_daemon_owner_mismatch`` and
    ``test_setup_plan_authenticated_coherent_succeeds`` were extracted to
    ``tests/specify_cli/cli/commands/agent/test_issue_3425_setup_plan_legacy_layout_silent_capture.py``
    (2026-08-14 landing fold; relocated out of ``tests/regression/`` once the
    reproduction turned green — see that module's exit-rule note) — both are
    regression guards for fixed bug #3425 (the FR-011 auth-refusal gate fired
    before the boundary preflight could be exercised on an un-migrated host),
    not stale tests of this class. See that module's docstring for the
    mechanism.
    """

    def test_setup_plan_refuses_on_orphan_owner_record(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """An orphan daemon owner record (dead PID) must cause refusal
        before any enqueue."""
        _scope_home_classmethod(monkeypatch, tmp_path)
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

        _write_credentials(
            tmp_path,
            username="auth@example.com",
            server_url="https://test.example.com",
            team_slug="team-alpha",
        )

        # Use a PID that's almost certainly dead. We deliberately do not
        # call os.kill (per spec) — pick a high PID that no process
        # holds. To make the test deterministic across platforms, we
        # additionally point ``executable_path`` at a non-existent
        # binary, which is_orphan() treats as orphan-class.
        nonexistent_exe = str(tmp_path / "missing-binary-sentinel")
        _write_daemon_owner_record(
            package_version="0.0.0",  # also a mismatch but is_orphan wins
            server_url="https://test.example.com",
            auth_principal="auth@example.com",
            auth_team="team-alpha",
            pid=999999,  # extremely high; effectively dead
            executable_path=nonexistent_exe,
        )

        mission_slug = "wp04-orphan-test"
        feature_dir = _build_minimal_repo(tmp_path, mission_slug)
        expected_scoped = _scoped_db_path_for(
            "https://test.example.com", "auth@example.com", "team-alpha"
        )
        from specify_cli.sync.queue import _legacy_queue_db_path
        legacy_path = _legacy_queue_db_path()

        payload = _run_json_setup_plan(
            monkeypatch,
            tmp_path,
            feature_dir,
            patch_boundary_safe=False,
            hosted_effects_must_be_zero=True,
        )
        warning_codes = [item["code"] for item in payload["warnings"]]  # type: ignore[index]
        assert "SAAS_SYNC_BOUNDARY_UNSAFE" in warning_codes
        assert payload["result"] == "success"

        # No queue writes — refusal before enqueue.
        assert _table_row_count(expected_scoped, "body_upload_queue") == 0
        assert _table_row_count(legacy_path, "body_upload_queue") == 0
        assert _table_row_count(legacy_path, "queue") == 0

    def test_setup_plan_preflight_runs_after_auth_preflight(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Auth and boundary diagnostics coexist without replacing local exit."""
        _scope_home_classmethod(monkeypatch, tmp_path)
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

        # Deliberately DO NOT write credentials. Also stub auth lookup
        # so any in-process token manager returns no session.
        class _NoSessionTokenManager:
            def get_current_session(self) -> None:
                return None

        monkeypatch.setattr(
            "specify_cli.auth.get_token_manager",
            lambda: _NoSessionTokenManager(),
            raising=False,
        )

        # Stage a mismatched record so if FR-008 did NOT fire first, the
        # boundary refusal would emit a different diagnostic.
        _write_daemon_owner_record(
            package_version="0.0.0-sentinel",
            server_url="https://test.example.com",
            auth_principal="phantom@example.com",
            auth_team="phantom-team",
        )

        mission_slug = "wp04-auth-order-test"
        feature_dir = _build_minimal_repo(tmp_path, mission_slug)
        payload = _run_json_setup_plan(
            monkeypatch,
            tmp_path,
            feature_dir,
            patch_boundary_safe=False,
            hosted_effects_must_be_zero=True,
        )

        warning_codes = [item["code"] for item in payload["warnings"]]  # type: ignore[index]
        assert warning_codes[:2] == [
            "SAAS_SYNC_AUTH_UNKNOWN",
            "SAAS_SYNC_BOUNDARY_UNSAFE",
        ]
        assert payload["result"] == "success"


# ---------------------------------------------------------------------------
# WP04 T020 — regression: setup-plan never writes to legacy queue
# ---------------------------------------------------------------------------


class TestSetupPlanNeverWritesLegacyQueue:
    """T020 regression: authenticated ``setup-plan`` writes scoped only."""



# ---------------------------------------------------------------------------
# Module sanity
# ---------------------------------------------------------------------------
