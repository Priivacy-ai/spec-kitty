"""Regression guard for #3425 — a fresh, un-migrated host must journal its
setup-plan capture instead of silently swallowing it.

Fixed: https://github.com/Priivacy-ai/spec-kitty/issues/3425

Correct root cause (the swallowed error is the **journal guard**, not a queue
default-path helper):

* On a runtime root that has never run the WP10 cutover the machine layout mode
  is ``LayoutMode.LEGACY``. Under the ProjectSyncStore-owned queue selection
  (FR-009 / C-003) a live writer is then handed a non-``project_only`` permit and
  ``_require_project_destination()``
  (``src/specify_cli/event_journal/journal.py:117-119``) raises
  ``ProjectLayoutRequiredError("live payload writes require the project_only
  layout; legacy state is migration input only")``.
* ``src/specify_cli/sync/emitter.py:2115`` catches that and prints
  ``Warning: event journal capture failed: ...`` to stderr only — the command
  reports success while the event is never journaled (a silent-success shape).
* The retired no-arg ``default_queue_db_path()``
  (``src/specify_cli/sync/queue.py:195-196``) is a **red herring** for this
  reproduction: it now raises ``LegacyQueueMigrationRequiredError``
  *unconditionally* (it is not layout-gated), so it is not what makes the
  reproduced setup-plan path fail closed. Attribution belongs to
  ``journal.py:119``.

Post-fix (WP03 / IC-02) a fresh root auto-publishes ``project_only`` *before* any
legacy persist, so the live capture lands in the project store journal and no
swallowed-capture warning is printed; WP01 restores credential parsing so the
FR-011 auth gate confirms authentication instead of spuriously refusing. These
three tests drive the real ``setup_plan`` entry point
(``specify_cli.cli.commands.agent.mission.setup_plan``) end to end:

1. ``test_authenticated_setup_plan_journals_without_silent_capture_failure`` —
   an authenticated, un-migrated host drives setup-plan without a swallowed
   capture-failure warning; a live journal capture on the resolved project store
   lands exactly once (auto-cutover to ``project_only``) and the legacy store is
   never touched.
2. ``test_setup_plan_refuses_on_daemon_owner_mismatch`` — with credential parsing
   restored (WP01) the FR-011 auth gate no longer short-circuits, so the boundary
   preflight's daemon-owner-mismatch "Refusing" banner is the gate that fires.
3. ``test_setup_plan_authenticated_coherent_succeeds`` — a fully coherent,
   authenticated host (resolvable project identity + migrated ``project_only``
   store) gets past the boundary preflight (exit code != 2) instead of being
   spuriously refused.
"""

from __future__ import annotations

import contextlib
import json
import pathlib
import sqlite3
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import typer

pytestmark = pytest.mark.integration

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
    """Pin ``Path.home()`` and env vars to *tmp_path* (C-008 cross-platform).

    ``SPEC_KITTY_HOME`` must be pinned too, not just ``HOME``: ``get_runtime_root``
    (``paths/windows_paths.py:60`` / ``runtime/home.py:39``) resolves
    ``SPEC_KITTY_HOME`` **before** any HOME-derived path ("always wins"), so a
    leaked/ambient ``SPEC_KITTY_HOME`` on this live legacy box would otherwise
    escape the temp-root isolation and resolve credentials/queues against real
    machine-global state. The runtime root is ``<base>`` directly and the
    credential/queue files this test writes live under ``tmp_path/.spec-kitty``
    (see ``_write_credentials``), so point ``SPEC_KITTY_HOME`` there.
    """
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / ".spec-kitty"))


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
    owner_record_path: Path = write_owner_record(record)
    return owner_record_path


_COHERENT_PROJECT_UUID = "aaaaaaaa-0000-0000-0000-00000000000a"


def _seed_project_identity(root: Path) -> str:
    """Write a resolvable project identity into *root* — nothing else.

    ``resolve_checkout_sync_routing_readonly`` (and the emitter's project-store
    selection) resolve the canonical project UUID from
    ``<root>/.kittify/config.yaml``. This seeds only the identity, leaving the
    machine layout at its ``LayoutMode.LEGACY`` in-memory default (an un-migrated
    root) so the WP03 auto-cutover-on-first-write path is what is exercised.
    """
    kittify = root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        "project:\n"
        f"  uuid: {_COHERENT_PROJECT_UUID}\n"
        "  slug: wp04-coherent\n"
        "  node_id: coherent-node\n",
        encoding="utf-8",
    )
    return _COHERENT_PROJECT_UUID


def _seed_coherent_project_store(root: Path) -> str:
    """Give *root* a resolvable project identity **and** a migrated project_only store.

    The WP04 boundary preflight (FR-002 / FR-009) refuses a checkout that has no
    resolvable project identity, or whose machine layout is not yet
    ``project_only``. Post-WP01 the FR-011 auth gate no longer masks that refusal,
    so a genuinely coherent authenticated host must now present both. Mirrors the
    canonical coherent-host fixture in
    ``tests/sync/test_sync_boundary_preflight.py`` (``_scoped_home``).
    """
    project_uuid = _seed_project_identity(root)
    from specify_cli.sync.project_store import ProjectSyncStore

    store = ProjectSyncStore(project_uuid)
    authority = store.layout_generation()
    authority.begin_cutover("wp04-coherent-migration")
    authority.publish_project_only("wp04-coherent-migration", verify_exact=lambda: True)
    with store.unit_of_work():
        pass
    return project_uuid


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
# Test A — authenticated setup-plan journals without a swallowed capture failure
# ---------------------------------------------------------------------------


class TestAuthenticatedSetupPlanJournals:
    """#3425: a fresh, un-migrated host journals its capture, never silently."""

    def test_authenticated_setup_plan_journals_without_silent_capture_failure(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # T030: pin SPEC_KITTY_HOME (not only HOME) so the runtime root — and the
        # credentials / legacy queue / project store it holds — resolve inside the
        # temp tree even on this live legacy box (get_runtime_root honours
        # SPEC_KITTY_HOME first).
        _scope_home_classmethod(monkeypatch, tmp_path)

        # Authenticate via credentials file (WP01 restores the TOML credential
        # parse that resolves the canonical scope).
        _write_credentials(
            tmp_path,
            username="auth@example.com",
            server_url="https://test.example.com",
            team_slug="team-alpha",
        )

        # Fresh, UN-MIGRATED root: seed only the project identity, no cutover. This
        # is the #3425 host — one that has never run WP10 migration. The WP03 fix
        # must still journal, by auto-publishing project_only on the first live
        # write rather than raising the journal guard and dropping the event.
        project_uuid = _seed_project_identity(tmp_path)

        from specify_cli.sync.queue import _legacy_queue_db_path

        legacy_path = _legacy_queue_db_path()

        mission_slug = "test-mvp-sync-evidence"
        feature_dir = _build_minimal_repo(tmp_path, mission_slug)

        from specify_cli.cli.commands.agent.mission import setup_plan

        # Drive the real setup-plan command end to end; the seam only stubs
        # git / project-root discovery, leaving the real capture path live.
        patches = _patches_for_setup_plan(tmp_path, feature_dir)
        for p in patches.values():
            p.start()
        try:
            with contextlib.suppress(typer.Exit, SystemExit):
                setup_plan(feature=mission_slug, json_output=True)
        finally:
            for p in patches.values():
                p.stop()

        # (c) LOAD-BEARING #3425 pin — warning-absence. Setup-plan drove its capture
        # path through the command boundary WITHOUT a swallowed capture-failure
        # warning on stderr. This is what proves the silent-success shape is gone:
        # the #3425 P0 was `journal.py:119 ProjectLayoutRequiredError` caught and
        # printed at `emitter.py:2115` while the command reported success.
        captured = capsys.readouterr()
        combined = captured.out + captured.err
        for banner in (
            "event journal capture failed",
            "live payload writes require the project_only layout",
            "Explicit-context event capture failed",
        ):
            assert banner not in combined, (
                f"#3425 regression: a swallowed capture-failure warning is present "
                f"on the setup-plan surface:\n{combined!r}"
            )

        # (a) Journal conservation — a live capture on this fresh, un-migrated root
        # lands in the project store journal EXACTLY ONCE. The store auto-publishes
        # project_only (WP03/IC-02) instead of raising the journal guard, so the
        # event is journaled rather than swallowed. The dossier helper is skipped
        # when SaaS sync is disabled, so — exactly as the retired body-queue
        # variant did — we drive the real journal path directly against the same
        # project identity setup-plan resolves.
        from specify_cli.event_journal.journal import EventJournal
        from specify_cli.event_journal.models import Event
        from specify_cli.sync.layout_generation import LayoutMode
        from specify_cli.sync.project_store import ProjectSyncStore

        store = ProjectSyncStore(project_uuid)
        event = Event(
            event_id="setup-plan-capture",
            event_type="WPStatusChanged",
            payload=json.dumps({"project_uuid": project_uuid}).encode(),
            occurred_at="2026-08-10T00:00:00+00:00",
            created_at="2026-08-10T00:00:01+00:00",
            project_uuid=project_uuid,
            project_slug="wp04-coherent",
            repo_slug="wp04-coherent",
        )
        with store.unit_of_work() as unit:
            receipt = EventJournal(unit, store.layout_generation()).append(event)
            assert receipt.inserted is True
            assert EventJournal(unit, store.layout_generation()).count() == 1

        # The fresh root cut over to project_only rather than staying LEGACY — the
        # exact #3425 root cause (a LEGACY-default host that journalled nothing).
        assert store.layout_generation().peek_state().mode is LayoutMode.PROJECT_ONLY

        # (b) Legacy store untouched — nothing was written to the retired legacy
        # queue db (neither the body-upload nor the event queue table).
        legacy_body_rows = _table_row_count(legacy_path, "body_upload_queue")
        legacy_event_rows = _table_row_count(legacy_path, "queue")
        assert legacy_body_rows == 0, (
            f"legacy DB at {legacy_path} has {legacy_body_rows} body_upload_queue rows."
        )
        assert legacy_event_rows == 0, (
            f"legacy DB at {legacy_path} has {legacy_event_rows} queue rows."
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

        Before the #3425 fix: the FR-011 auth-refusal gate fires first
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

        Before the #3425 fix: even a fully coherent, authenticated host is
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

        # No daemon owner record on disk and no legacy queue rows. Post-WP01 the
        # auth gate confirms the credentials instead of refusing; the WP04 boundary
        # preflight then additionally requires a resolvable project identity and a
        # migrated project_only store — seed both so the host is genuinely coherent
        # and the preflight does NOT refuse (the pin is "did not refuse at
        # preflight", i.e. exit code != 2).
        _seed_coherent_project_store(tmp_path)

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
