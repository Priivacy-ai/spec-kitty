"""Red-first reproduction of #3425 — un-migrated machines stay in
``LayoutMode.LEGACY`` after #3293, so the event journal silently captures
nothing.

Open P0: https://github.com/Priivacy-ai/spec-kitty/issues/3425

Root cause (verified against the issue's own mechanism section):

* ``LayoutGenerationAuthority._initial_state()``
  (``src/specify_cli/sync/layout_generation.py:130-135``) defaults to
  ``LayoutMode.LEGACY`` when ``.layout-generation.json`` is absent — the
  state of any runtime root that has never run the WP10 migration.
* ``_require_project_destination()``
  (``src/specify_cli/event_journal/journal.py:117-119``) then raises
  ``LegacyQueueMigrationRequiredError: live payload queues are selected by
  ProjectSyncStore; legacy paths are WP10 migration inputs`` — the same
  fail-closed shape backs ``default_queue_db_path()``
  (``src/specify_cli/sync/queue.py:195-196``), which every setup-plan
  queue-write call site resolves through.
* ``src/specify_cli/sync/emitter.py:2115`` catches the raised error and
  prints ``Warning: event journal capture failed: ...`` to stderr only —
  the command itself reports no error. The event is never journaled.

On an un-migrated machine this is a silent-success shape: no error surfaces
to the caller, and the absence of captured data is visible only to someone
reading stderr. These three tests drive the real ``setup_plan`` entry point
(``specify_cli.cli.commands.agent.mission.setup_plan``) end to end and prove
the silent-failure / cascading-refusal consequences:

1. ``test_authenticated_setup_plan_lands_in_scoped`` — an authenticated,
   un-migrated host cannot resolve ``default_queue_db_path()`` at all; it
   raises ``LegacyQueueMigrationRequiredError`` before any queue write is
   attempted.
2. ``test_setup_plan_refuses_on_daemon_owner_mismatch`` — the boundary
   preflight (daemon-owner mismatch refusal) never gets a chance to run: the
   FR-011 auth-refusal gate fires first with "SaaS sync cannot be
   guaranteed", because scope resolution on an un-migrated host cannot
   confirm authentication, masking the boundary-preflight diagnostic this
   test expects.
3. ``test_setup_plan_authenticated_coherent_succeeds`` — even a fully
   coherent, authenticated host is refused with exit code 2 by the same
   auth gate, because the underlying scope/layout resolution the gate
   depends on is broken by the ``LayoutMode.LEGACY`` default.

Desired post-fix outcome (either maintainer resolution turns this green, per
the issue's own suggested direction): either default un-migrated roots to a
layout mode that still journals, or make the capture failure loud at the
command surface instead of a swallowed stderr warning. This test pins the
conformance contract (setup-plan must not silently produce zero SaaS
capture / must not spuriously refuse a coherent host), not the chosen
mechanism.
"""

from __future__ import annotations

import contextlib
import pathlib
import sqlite3
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import typer

pytestmark = pytest.mark.regression

MODULE = "specify_cli.cli.commands.agent.mission"


# ---------------------------------------------------------------------------
# Helpers (extracted verbatim from tests/runtime/test_setup_plan_sync_evidence.py
# — only what these three tests need; the source file's other passing tests
# keep their own copies undisturbed)
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


# ---------------------------------------------------------------------------
# Test A — authenticated setup-plan cannot land queue writes on a LEGACY host
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
        #
        # RED today (#3425): on an un-migrated host this raises
        # LegacyQueueMigrationRequiredError instead of returning a path —
        # LayoutMode.LEGACY makes default_queue_db_path() fail closed.
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

        # Drive a real enqueue through the same default-path resolution
        # setup-plan's body queue uses, to produce a row we can count.
        from specify_cli.sync.namespace import NamespaceRef

        body_queue = OfflineBodyUploadQueue()
        assert body_queue.db_path == expected_scoped_path

        body_queue.enqueue(
            namespace=NamespaceRef(
                project_uuid="550e8400-e29b-41d4-a716-446655440000",
                mission_slug=mission_slug,
                target_branch="main",
                mission_type="software-dev",
                manifest_version="1",
            ),
            artifact_path="spec.md",
            content_hash="cafebabe" * 8,
            content_body="# Test Feature\n",
            size_bytes=15,
        )

        # Scoped DB should have rows; legacy must be untouched.
        scoped_rows = _table_row_count(expected_scoped_path, "body_upload_queue")
        legacy_body_rows = _table_row_count(legacy_path, "body_upload_queue")
        legacy_event_rows = _table_row_count(legacy_path, "queue")

        assert scoped_rows > 0, (
            f"Expected scoped body_upload_queue rows > 0, got {scoped_rows}."
        )
        assert legacy_body_rows == 0, (
            f"FR-012 violation: legacy DB at {legacy_path} has "
            f"{legacy_body_rows} body_upload_queue rows."
        )
        assert legacy_event_rows == 0, (
            f"FR-012 violation: legacy DB at {legacy_path} has "
            f"{legacy_event_rows} queue rows."
        )


# ---------------------------------------------------------------------------
# WP04 (mvp-cli-sync-boundary-completion-01KRX11M) — preflight integration
# ---------------------------------------------------------------------------
#
# These two tests cover the boundary-preflight / positive-path halves of
# T019 + T020 from the WP04 spec, but on an un-migrated (LayoutMode.LEGACY)
# host they never reach their real assertion — the #3425 auth-gate cascade
# (see module docstring) refuses first.
#
# Cross-platform isolation (C-008): we patch ``pathlib.Path.home`` and
# the HOME / USERPROFILE env vars together. Bare ``monkeypatch.setenv``
# is insufficient on Windows where ``Path.home()`` resolves through
# ``USERPROFILE`` via a classmethod-level mechanism that does not read
# the env on every call.


class TestSetupPlanPreflightIntegration:
    """WP04 T019: setup-plan refuses on boundary failure before any enqueue."""

    def test_setup_plan_refuses_on_daemon_owner_mismatch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """A daemon owner record with a mismatched ``package_version``
        must cause ``setup-plan`` to refuse with exit code 2 — and no
        scoped / legacy queue rows may exist after refusal.

        RED today (#3425): the FR-011 auth-refusal gate fires first
        ("SaaS sync cannot be guaranteed") instead of the boundary
        preflight's daemon-owner-mismatch "Refusing" banner, because
        scope resolution on this un-migrated host cannot confirm the
        credentials this test wrote.
        """
        _scope_home_classmethod(monkeypatch, tmp_path)
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

        # Authenticate so the FR-011 auth refusal does NOT short-circuit;
        # this isolates the boundary preflight as the load-bearing gate.
        _write_credentials(
            tmp_path,
            username="auth@example.com",
            server_url="https://test.example.com",
            team_slug="team-alpha",
        )

        # Write a daemon owner record with a mismatched package_version
        # so the boundary preflight surfaces a ``daemon_package_version``
        # mismatch against whatever ``_get_package_version()`` resolves
        # in the foreground.
        _write_daemon_owner_record(
            package_version="0.0.0-mismatched-sentinel-version",
            server_url="https://test.example.com",
            auth_principal="auth@example.com",
            auth_team="team-alpha",
        )

        from specify_cli.cli.commands.agent.mission import setup_plan

        mission_slug = "wp04-mismatch-test"
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
        assert exit_code == 2, (
            f"Expected exit 2 on daemon-owner mismatch, got {exit_code!r}."
        )

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        # Refusal banner + mismatch row should appear in the diagnostic.
        assert "Refusing" in combined, (
            f"Expected refusal banner in output, got:\n{combined!r}"
        )

        # No queue writes — neither scoped nor legacy DB rows exist.
        assert _table_row_count(expected_scoped, "body_upload_queue") == 0
        assert _table_row_count(expected_scoped, "queue") == 0
        assert _table_row_count(legacy_path, "body_upload_queue") == 0
        assert _table_row_count(legacy_path, "queue") == 0

    def test_setup_plan_authenticated_coherent_succeeds(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Positive case: coherent host (no owner record, no legacy rows,
        valid auth) — ``setup-plan`` runs through the preflight and
        reaches the queue-write call sites successfully.

        RED today (#3425): even a fully coherent, authenticated host is
        refused with exit code 2 by the FR-011 auth gate, because scope
        resolution depends on the same LayoutMode.LEGACY-broken chain.
        """
        _scope_home_classmethod(monkeypatch, tmp_path)
        monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

        _write_credentials(
            tmp_path,
            username="auth@example.com",
            server_url="https://test.example.com",
            team_slug="team-alpha",
        )

        # No daemon owner record on disk and no legacy queue rows means
        # the preflight is structurally ok and the auth check passes.

        from specify_cli.cli.commands.agent.mission import setup_plan

        mission_slug = "wp04-coherent-test"
        feature_dir = _build_minimal_repo(tmp_path, mission_slug)

        patches = _patches_for_setup_plan(tmp_path, feature_dir)
        # Additionally suppress the dossier helper so we don't depend
        # on its full call graph; the preflight ran BEFORE it would
        # be called, and that's what we're proving.
        patches[f"{MODULE}.logger"] = patch(f"{MODULE}.logger")
        for p in patches.values():
            p.start()
        try:
            # The function may still raise typer.Exit for downstream
            # reasons (no real plan template installed in tmp_path);
            # we only care that the boundary preflight DID NOT refuse.
            try:
                setup_plan(feature=mission_slug, json_output=True)
            except (typer.Exit, SystemExit) as exc:
                # Exit 2 means preflight refused; that must not happen
                # here. Any other exit code is acceptable for the
                # purposes of this test (we just want past the gate).
                code = getattr(exc, "exit_code", None) or getattr(exc, "code", None)
                assert code != 2, (
                    "Coherent host should pass preflight; got exit 2 "
                    "(preflight refusal) instead."
                )
        finally:
            for p in patches.values():
                p.stop()
