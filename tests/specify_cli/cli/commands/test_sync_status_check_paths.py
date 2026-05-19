"""WP02 (#1123): canonical file paths render verbatim in ``sync status --check``.

These tests pin the behavior documented in
``contracts/sync-status-check-rendering.md``:

* Non-TTY capture (the canary read path) must surface every canonical
  path field byte-identical to its ``--json`` value.
* Long paths (> 100 chars) must not be ellipsised in the text form.
* A narrow ``Console`` width must not truncate path rows -- they
  render outside the width-bound Rich ``Table``.
* The ``--json`` contract is unchanged: every path field present in
  the text form appears with the same value under ``--json``.

The fixture stubs out network and live-process probes so the test only
exercises the rendering surface.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from rich.console import Console
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_cmd
from specify_cli.cli.commands.sync import app
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR

pytestmark = pytest.mark.fast


runner = CliRunner()


# ---------------------------------------------------------------------------
# Shared fixtures (mirror tests/sync/test_sync_status_boundary_check.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _scoped_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin HOME / LOCALAPPDATA to ``tmp_path`` so all global state is scoped."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.delenv(SAAS_SYNC_ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(autouse=True)
def _isolate_external_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub out network / heavy probes used inside ``sync status``."""
    monkeypatch.setattr(
        "specify_cli.cli.commands.sync._check_server_connection",
        lambda url: ("[green]Connected[/green]", "Server reachable."),
    )
    tm = MagicMock()
    tm.is_authenticated = True
    tm.get_current_session.return_value = None
    monkeypatch.setattr("specify_cli.auth.get_token_manager", lambda: tm)

    from specify_cli.sync.daemon import DaemonSingletonReport, SyncDaemonStatus

    monkeypatch.setattr(
        "specify_cli.sync.daemon.scan_sync_daemons",
        lambda: DaemonSingletonReport(
            state_pid=None,
            state_file_present=False,
            orphan_processes=(),
        ),
    )
    monkeypatch.setattr(
        "specify_cli.sync.daemon.get_sync_daemon_status",
        lambda: SyncDaemonStatus(
            healthy=True,
            url=None,
            port=None,
            sync_running=False,
            last_sync=None,
            consecutive_failures=0,
            websocket_status="Disconnected",
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Path-row labels emitted by ``_print_boundary_paths`` mapped to the
# canonical JSON path that holds their value.
_PATH_LABEL_TO_JSON_KEY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Foreground Executable path", ("foreground", "executable_path")),
    ("Foreground Source path", ("foreground", "source_path")),
    ("Foreground Queue DB path", ("foreground", "queue_db_path")),
    ("Active queue path", ("active_queue", "path")),
    ("Legacy queue path", ("legacy_queue", "path")),
)


def _extract_path_lines(stdout: str) -> dict[str, str]:
    """Pull ``label: value`` pairs out of the text rendering for the path rows."""
    extracted: dict[str, str] = {}
    for raw in stdout.splitlines():
        line = raw.rstrip()
        for label, _ in _PATH_LABEL_TO_JSON_KEY:
            needle = f"  {label}: "
            if needle in line:
                # Slice from the start of the needle so leading Rich
                # framing (if any) is dropped; everything after the
                # ``: `` is the rendered path verbatim.
                start = line.index(needle) + len(needle)
                extracted[label] = line[start:]
                break
    return extracted


def _read_json_path(payload: dict[str, Any], dotted: tuple[str, ...]) -> str:
    cur: Any = payload
    for part in dotted:
        cur = cur[part]
    assert isinstance(cur, str), f"expected string at {'.'.join(dotted)}, got {cur!r}"
    return cur


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_non_tty_capture_shows_every_path_verbatim() -> None:
    """Under ``CliRunner`` (forces non-TTY) every path row must appear in stdout.

    This is the canary-harness read path. ``sync status --check`` must emit
    every canonical file path verbatim, so a downstream consumer can pull
    a path from the rendered output and ``stat()`` it on disk.
    """
    result = runner.invoke(app, ["status", "--check"])
    # Exit code may be 0 or 2 depending on the boundary failure set; the
    # rendering contract holds either way.
    assert result.exit_code in (0, 2), result.stdout

    extracted = _extract_path_lines(result.stdout)
    expected_labels = {label for label, _ in _PATH_LABEL_TO_JSON_KEY}
    missing = expected_labels - set(extracted)
    assert not missing, f"missing path rows: {missing}\nSTDOUT:\n{result.stdout}"

    # Each captured value must be non-empty (a path or ``<absent>``); critically,
    # it must not be truncated by Rich's ellipsis.
    for label, value in extracted.items():
        assert value, f"empty value for {label!r}"
        assert "…" not in value, (
            f"ellipsis in {label!r}: {value!r}"
        )


def test_long_path_renders_without_ellipsis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seed a > 100-char queue DB path; the rendered text must contain it verbatim.

    Patches ``compute_foreground_identity`` and ``build_boundary_failure_set``
    so the renderer sees a long synthetic path. The canonical ``--json``
    form already emits the full path; this test pins the text-form parity.
    """
    long_path = (
        "/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/"
        "spec-kitty-extremely-long-path-for-regression-test/"
        "nested/level/queue.db"
    )
    assert len(long_path) > 100

    # Patch the foreground identity dict used elsewhere in the function.
    real_compute = sync_cmd.compute_foreground_identity if hasattr(
        sync_cmd, "compute_foreground_identity"
    ) else None
    from specify_cli.sync import owner as owner_mod

    real_compute_fn = owner_mod.compute_foreground_identity
    identity = real_compute_fn()
    identity_with_long = dict(identity)
    identity_with_long["queue_db_path"] = long_path
    monkeypatch.setattr(
        "specify_cli.sync.owner.compute_foreground_identity",
        lambda: identity_with_long,
    )

    # Patch the structured failure-set's foreground so the rendered
    # ``Foreground queue DB path`` / ``Active queue path`` rows hold the
    # long path verbatim.
    from specify_cli.sync.preflight import build_boundary_failure_set

    real_fs = build_boundary_failure_set(repo_root=Path.cwd())

    class _LongFG:
        package_version = real_fs.foreground.package_version
        executable_path = real_fs.foreground.executable_path
        source_path = real_fs.foreground.source_path
        server_url = real_fs.foreground.server_url
        team_or_user = real_fs.foreground.team_or_user
        queue_db_path = long_path
        pid = real_fs.foreground.pid

    class _LongFS:
        foreground = _LongFG()
        daemon_record = real_fs.daemon_record
        daemon_status = real_fs.daemon_status
        mismatches = real_fs.mismatches
        orphan_records = real_fs.orphan_records
        legacy_event_rows = real_fs.legacy_event_rows
        legacy_body_upload_rows = real_fs.legacy_body_upload_rows
        legacy_rows_for_scope = real_fs.legacy_rows_for_scope
        ok = real_fs.ok

    monkeypatch.setattr(
        "specify_cli.sync.preflight.build_boundary_failure_set",
        lambda repo_root=None: _LongFS(),
    )

    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code in (0, 2), result.stdout
    # The contract is scoped to the canonical boundary path rows that
    # WP02 owns. Other surfaces (the early "Sync Status" summary
    # table) may still ellipsise unrelated fields; WP02 does not
    # widen those. Inspect only the lines emitted by
    # ``_print_boundary_paths`` and the corresponding ``Active queue
    # path`` / ``Foreground queue DB path`` lines.
    extracted = _extract_path_lines(result.stdout)
    for label, value in extracted.items():
        assert "…" not in value, (
            f"ellipsis in boundary path row {label!r}: {value!r}\n"
            f"FULL STDOUT:\n{result.stdout}"
        )
    # And specifically the long path must be present verbatim under
    # the Foreground/Active queue path rows.
    assert extracted["Foreground Queue DB path"] == long_path, extracted
    assert extracted["Active queue path"] == long_path, extracted
    assert long_path in result.stdout, (
        f"long path not present verbatim in stdout:\n"
        f"long_path={long_path!r}\n\nSTDOUT:\n{result.stdout}"
    )

    # Silence unused-name warning when the conditional binding above
    # is skipped on environments lacking ``compute_foreground_identity``
    # as a module-level alias.
    _ = real_compute


def test_narrow_console_does_not_wrap_path_rows() -> None:
    """A 40-column Console must still print path rows on a single line.

    The path renderer is supposed to bypass the width-bound Table entirely.
    We exercise the helper directly with a synthetic narrow Console and
    assert each path row is exactly one physical line.
    """
    from io import StringIO

    long_path = "/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/" + ("x" * 80)
    narrow_buf = StringIO()
    narrow = Console(
        file=narrow_buf,
        width=40,
        force_terminal=False,
        legacy_windows=False,
        color_system=None,
    )
    sync_cmd._print_boundary_paths(
        narrow,
        [
            ("Active queue path", long_path),
            ("Foreground source path", long_path),
        ],
    )
    rendered = narrow_buf.getvalue()
    # Path lines must not be folded across the 40-column width: the
    # entire long_path must appear on a single physical line.
    for line in rendered.splitlines():
        if "Active queue path:" in line:
            assert long_path in line, (
                f"Active queue path was wrapped:\nLINE:{line!r}\nALL:{rendered!r}"
            )
        if "Foreground source path:" in line:
            assert long_path in line, (
                f"Foreground source path was wrapped:\n"
                f"LINE:{line!r}\nALL:{rendered!r}"
            )
    assert "…" not in rendered, f"ellipsis present in narrow output:\n{rendered}"


def test_text_form_paths_match_json_form_byte_for_byte() -> None:
    """``--json`` and text emit byte-identical values for every path field."""
    json_result = runner.invoke(app, ["status", "--check", "--json"])
    assert json_result.exit_code in (0, 2), json_result.stdout
    payload = json.loads(json_result.stdout.strip())

    text_result = runner.invoke(app, ["status", "--check"])
    assert text_result.exit_code in (0, 2), text_result.stdout
    extracted = _extract_path_lines(text_result.stdout)

    for label, dotted in _PATH_LABEL_TO_JSON_KEY:
        # Only assert for paths that are concrete strings in JSON --
        # daemon paths may be ``null`` when no owner record is present,
        # and in that case the text form emits ``<absent>``. The matrix
        # under ``_PATH_LABEL_TO_JSON_KEY`` is the foreground + queue
        # fields which are always strings in the JSON contract.
        json_value = _read_json_path(payload, dotted)
        text_value = extracted[label]
        assert json_value == text_value, (
            f"JSON/text mismatch for {label}:\n"
            f"  json={json_value!r}\n  text={text_value!r}\n"
            f"FULL STDOUT:\n{text_result.stdout}"
        )
