"""WP10 retirement controls for automatic shared-store convergence."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli.cli.commands import sync as sync_cmd


pytestmark = pytest.mark.fast


def test_retired_auto_convergence_is_guidance_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sync_cmd,
        "_open_event_sync_runtime",
        lambda: pytest.fail("retired convergence opened a legacy runtime"),
    )

    sync_cmd._auto_converge_legacy_on_enable()

    output = capsys.readouterr().out
    assert "Automatic legacy convergence is retired" in output
    assert "project-store-preview" in output


def test_opt_in_never_invokes_legacy_convergence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    routing = SimpleNamespace(
        repo_root=tmp_path,
        repo_slug="repo",
        project_slug="project",
        project_uuid="44444444-4444-4444-8444-444444444444",
    )
    monkeypatch.setattr(sync_cmd, "is_saas_sync_enabled", lambda: True)
    monkeypatch.setattr(sync_cmd, "_require_daemon_owner_coherence", lambda _name: None)
    monkeypatch.setattr(
        sync_cmd,
        "enforce_teamspace_mission_state_ready",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(sync_cmd, "_require_active_checkout", lambda: routing)
    monkeypatch.setattr(
        sync_cmd,
        "_auto_converge_legacy_on_enable",
        lambda: pytest.fail("opt-in invoked retired legacy convergence"),
    )
    monkeypatch.setattr(
        "specify_cli.sync.routing.enable_checkout_sync",
        lambda *_args, **_kwargs: routing,
    )

    sync_cmd.opt_in(checkout_only=True)


def test_retired_auto_convergence_does_not_import_legacy_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "specify_cli.sync.migrate_journal.converge_legacy_runtime",
        lambda *_args, **_kwargs: pytest.fail("legacy engine was invoked"),
    )

    sync_cmd._auto_converge_legacy_on_enable()


def test_retired_auto_convergence_never_opens_project_or_source_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sync_cmd,
        "_open_project_dispatch_runtime",
        lambda: pytest.fail("retired compatibility seam opened a project store"),
    )
    monkeypatch.setattr(
        sync_cmd,
        "_open_event_sync_runtime",
        lambda: pytest.fail("retired compatibility seam opened a legacy store"),
    )

    sync_cmd._auto_converge_legacy_on_enable()
