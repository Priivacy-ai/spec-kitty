"""WP04 regression tests: setup-plan SaaS-evidence guarantee.

These tests pin the contract described in
``kitty-specs/mvp-sync-boundary-cli-01KRVCQS/tasks/WP04-setup-plan-sync-evidence.md``:

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

NFR-001: every test uses ``monkeypatch.setenv("HOME", str(tmp_path))``
so we never touch the operator's real ``~/.spec-kitty``.
"""

from __future__ import annotations

import ast
import contextlib
import importlib
import json
import sqlite3
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
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


def _queued_event_types(db_path: Path) -> list[str]:
    """Return queued event types from the offline event outbox."""
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = 'queue'"
        )
        if cursor.fetchone() is None:
            return []
        rows = conn.execute("SELECT data FROM queue ORDER BY id ASC").fetchall()
    finally:
        conn.close()
    event_types: list[str] = []
    for (raw,) in rows:
        event_types.append(str(json.loads(raw)["event_type"]))
    return event_types


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


class TestAuthenticatedSetupPlanLandsInScoped:
    """FR-012 evidence: authenticated setup-plan writes scoped, never legacy."""

    def test_authenticated_setup_plan_lands_in_scoped(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # NFR-001: redirect HOME so any queue DB lands under tmp_path.
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

        # Authenticate via credentials file (the credentials path is the
        # documented fallback for ``read_queue_scope_from_credentials``).
        _write_credentials(
            home,
            username="auth@example.com",
            server_url="https://test.example.com",
            team_slug="team-alpha",
        )

        # Eagerly resolve the expected scoped DB path so we can assert on it
        # after setup-plan runs.
        from specify_cli.sync.queue import (
            _legacy_queue_db_path,
            build_queue_scope,
            default_queue_db_path,
            scope_db_path,
        )

        expected_scope = build_queue_scope(
            server_url="https://test.example.com",
            username="auth@example.com",
            team_slug="team-alpha",
        )
        expected_scoped_path = scope_db_path(expected_scope)
        legacy_path = _legacy_queue_db_path()

        # Sanity check: the resolution chain picks scoped for our fake creds
        # before we ever call setup-plan.
        assert default_queue_db_path() == expected_scoped_path
        assert default_queue_db_path() != legacy_path

        # Build minimal project root + mission directory.
        mission_slug = "test-mvp-sync-evidence"
        feature_dir = _build_minimal_repo(tmp_path, mission_slug)

        # Stub out the heavy moving parts so setup-plan executes its real
        # queue-write call site (``trigger_feature_dossier_sync_if_enabled``
        # → ``OfflineBodyUploadQueue()`` → ``default_queue_db_path()``)
        # without needing a real indexer/manifest/git history.
        from specify_cli.sync.body_queue import OfflineBodyUploadQueue
        from specify_cli.cli.commands.agent.mission import setup_plan

        # Surface the body queue the dossier helper instantiated so we can
        # both verify its db_path AND drive a real enqueue against it to
        # prove the row lands in the scoped DB.
        created_queues: list[OfflineBodyUploadQueue] = []

        original_init = OfflineBodyUploadQueue.__init__

        def _record_init(self: OfflineBodyUploadQueue, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            created_queues.append(self)

        patches = {
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
            # Spec must be flagged as committed + substantive without git.
            "specify_cli.missions._substantive.is_committed": patch(
                "specify_cli.missions._substantive.is_committed", return_value=True
            ),
            "specify_cli.missions._substantive.is_substantive": patch(
                "specify_cli.missions._substantive.is_substantive", return_value=True
            ),
            # Plan commit path: stub git-side _commit_to_branch.
            f"{MODULE}._commit_to_branch": patch(
                f"{MODULE}._commit_to_branch"
            ),
            # Record every body-queue creation so we can assert the path.
            "specify_cli.sync.body_queue.OfflineBodyUploadQueue.__init__": patch(
                "specify_cli.sync.body_queue.OfflineBodyUploadQueue.__init__",
                autospec=True,
                side_effect=_record_init,
            ),
        }

        for p in patches.values():
            p.start()
        try:
            with contextlib.suppress(typer.Exit, SystemExit):
                setup_plan(feature=mission_slug, json_output=True)
        finally:
            for p in patches.values():
                p.stop()

        # If the dossier helper ran, it created an OfflineBodyUploadQueue
        # without a db_path argument; that constructor must resolve to the
        # scoped path. Some test environments will skip the dossier helper
        # (SaaS sync disabled / no project UUID), so we additionally exercise
        # the explicit default-path queue instantiation below.
        for q in created_queues:
            assert q.db_path == expected_scoped_path, (
                f"OfflineBodyUploadQueue resolved to {q.db_path!r}, "
                f"expected scoped {expected_scoped_path!r} — FR-012 violation."
            )

        # setup-plan's actual lifecycle emissions must reach the scoped event
        # outbox. This proves canonical evidence crosses the active sync
        # boundary; no manual body upload is inserted by the test.
        scoped_event_types = _queued_event_types(expected_scoped_path)
        scoped_rows = _table_row_count(expected_scoped_path, "queue")
        legacy_body_rows = _table_row_count(legacy_path, "body_upload_queue")
        legacy_event_rows = _table_row_count(legacy_path, "queue")

        assert scoped_rows > 0, (
            f"Expected scoped lifecycle queue rows > 0, got {scoped_rows}."
        )
        assert "SpecifyCompleted" in scoped_event_types
        assert "PlanStarted" in scoped_event_types
        assert "PlanCompleted" in scoped_event_types
        assert legacy_body_rows == 0, (
            f"FR-012 violation: legacy DB at {legacy_path} has "
            f"{legacy_body_rows} body_upload_queue rows."
        )
        assert legacy_event_rows == 0, (
            f"FR-012 violation: legacy DB at {legacy_path} has "
            f"{legacy_event_rows} queue rows."
        )


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

    def test_setup_plan_refuses_daemon_queue_incoherence_with_boundary_diagnostics(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

        _write_credentials(
            home,
            username="auth@example.com",
            server_url="https://test.example.com",
            team_slug="team-alpha",
        )

        from specify_cli.cli.commands.agent.mission import setup_plan
        from specify_cli.sync.owner import (
            DaemonOwnerRecord,
            compute_foreground_identity,
            write_owner_record,
        )

        identity = compute_foreground_identity()
        write_owner_record(
            DaemonOwnerRecord(
                pid=12345,
                port=9400,
                token="secret-token",
                package_version=str(identity["package_version"]),
                executable_path=str(identity["executable_path"]),
                source_checkout_path=str(identity["source_checkout_path"]),
                server_url=str(identity["server_url"]),
                auth_principal=identity.get("auth_principal"),
                auth_team=identity.get("auth_team"),
                auth_scope=identity.get("auth_scope"),
                queue_db_path="/tmp/other-queue.db",
                started_at="2026-05-18T08:00:00+00:00",
            )
        )

        with pytest.raises((typer.Exit, SystemExit)) as exc_info:
            setup_plan(feature="any-mission", json_output=False)

        exit_code = getattr(exc_info.value, "exit_code", None) or getattr(
            exc_info.value, "code", None
        )
        assert exit_code == 2

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        flat = " ".join(combined.split())
        assert "SaaS sync cannot be guaranteed" in flat
        assert "Auth scope:" in flat
        assert "Queue DB:" in flat
        assert "Daemon owner:" in flat
        assert "queue_db_path" in flat


# ---------------------------------------------------------------------------
# Test C — AST regression: no direct _legacy_queue_db_path calls in setup-plan
# ---------------------------------------------------------------------------


class TestNoDirectLegacyDbPathCallsInSetupPlanCode:
    """FR-012 AST regression: setup-plan code path must not call _legacy_queue_db_path."""

    def test_no_direct_legacy_db_path_calls_in_setup_plan_code(self) -> None:
        # Import the module under audit to anchor a real filesystem path.
        from specify_cli.cli.commands.agent import mission as mission_module

        # The setup-plan module list. ``mission.py`` is the entrypoint; any
        # other file added to this list as the audit expands must also be
        # clean of direct ``_legacy_queue_db_path()`` references.
        modules_to_audit: list[Path] = [Path(mission_module.__file__)]

        # The migration helpers inside ``sync/queue.py`` are explicitly exempt
        # — that file is NOT in the setup-plan code path (it is the canonical
        # owner of the legacy→scoped migration). Other callers in
        # ``cli/commands/sync.py`` are out of scope for setup-plan.

        violations: list[tuple[str, int]] = []

        for path in modules_to_audit:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name: str | None = None
                if isinstance(func, ast.Attribute):
                    name = func.attr
                elif isinstance(func, ast.Name):
                    name = func.id
                if name == "_legacy_queue_db_path":
                    violations.append((str(path), node.lineno))

        assert not violations, (
            "FR-012 violation: setup-plan code path calls "
            "_legacy_queue_db_path() directly at: "
            + ", ".join(f"{p}:{ln}" for p, ln in violations)
        )

    def test_audit_comment_block_present_in_setup_plan(self) -> None:
        """The FR-012 audit comment block must be embedded in setup_plan's docstring."""
        from specify_cli.cli.commands.agent.mission import setup_plan

        doc = setup_plan.__doc__ or ""
        assert "WP04 / FR-011 + FR-012 audit" in doc, (
            "setup_plan docstring is missing the WP04 audit block."
        )
        assert "default_queue_db_path()" in doc, (
            "setup_plan docstring audit block must reference default_queue_db_path()."
        )
        assert "2026-05-17" in doc, (
            "setup_plan docstring audit block must reference the 2026-05-17 audit date."
        )


# ---------------------------------------------------------------------------
# Module sanity
# ---------------------------------------------------------------------------


def test_module_is_importable() -> None:
    """Smoke check so the regression file fails loudly if imports break."""
    module = importlib.import_module("specify_cli.cli.commands.agent.mission")
    assert module.setup_plan is not None
