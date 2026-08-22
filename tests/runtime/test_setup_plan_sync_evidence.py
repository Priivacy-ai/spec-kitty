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
from typing import Any
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration]

import typer


MODULE = "specify_cli.cli.commands.agent.mission"


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
        '{"mission_slug": "' + mission_slug + '"}', encoding="utf-8"
    )

    return feature_dir


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
    """FR-011 evidence: SAAS-enabled + unauthenticated => exit + no DB writes."""

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

        # Diagnostic must include the FR-011 phrase.
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "SaaS sync cannot be guaranteed" in combined, (
            f"Expected FR-011 phrase in diagnostic, got:\n{combined!r}"
        )

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

        from specify_cli.cli.commands.agent.mission import setup_plan

        mission_slug = "wp04-orphan-test"
        feature_dir = _build_minimal_repo(tmp_path, mission_slug)
        expected_scoped = _scoped_db_path_for(
            "https://test.example.com", "auth@example.com", "team-alpha"
        )
        from specify_cli.sync.queue import _legacy_queue_db_path
        legacy_path = _legacy_queue_db_path()

        patches = _patches_for_setup_plan(tmp_path, feature_dir)
        for p in patches.values():
            p.start()
        try:
            with pytest.raises((typer.Exit, SystemExit)) as exc_info:
                setup_plan(feature=mission_slug, json_output=False)
        finally:
            for p in patches.values():
                p.stop()

        exit_code = getattr(exc_info.value, "exit_code", None) or getattr(
            exc_info.value, "code", None
        )
        assert exit_code == 2

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
        """FR-008 preservation: with no auth + mismatched daemon record,
        the auth-absent refusal must fire first (not the boundary
        refusal). The FR-011 diagnostic identifies which gate triggered."""
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

        from specify_cli.cli.commands.agent.mission import setup_plan

        mission_slug = "wp04-auth-order-test"
        _build_minimal_repo(tmp_path, mission_slug)

        with pytest.raises((typer.Exit, SystemExit)) as exc_info:
            setup_plan(feature=mission_slug, json_output=False)

        exit_code = getattr(exc_info.value, "exit_code", None) or getattr(
            exc_info.value, "code", None
        )
        assert exit_code == 2, (
            f"Expected exit 2 (auth refusal), got {exit_code!r}."
        )

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        # FR-011 diagnostic must appear — proves auth gate fired first.
        assert "SaaS sync cannot be guaranteed" in combined, (
            f"Expected FR-011 phrase (auth gate fired first), got:\n{combined!r}"
        )


# ---------------------------------------------------------------------------
# WP04 T020 — regression: setup-plan never writes to legacy queue
# ---------------------------------------------------------------------------


class TestSetupPlanNeverWritesLegacyQueue:
    """T020 regression: authenticated ``setup-plan`` writes scoped only."""



# ---------------------------------------------------------------------------
# Module sanity
# ---------------------------------------------------------------------------
