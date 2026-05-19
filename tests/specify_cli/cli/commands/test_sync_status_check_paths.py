"""WP02 (#1123) + WP02 cycle 1 (B-1): canonical paths render verbatim AND
parse cleanly under the cross-repo canary parser contract.

These tests pin the behavior documented in
``contracts/sync-status-check-rendering.md`` AND the cross-repo contract
with the sibling canary parser at
``spec-kitty-end-to-end-testing/src/spec_kitty_e2e/identity_boundary/
status_parser.py``:

* Non-TTY capture (the canary read path) must surface every canonical
  path field byte-identical to its ``--json`` value.
* Long paths (> 100 chars) must not be ellipsised in the text form.
* A narrow ``Console`` width must not truncate path rows -- they
  render outside the width-bound Rich ``Table``.
* The ``--json`` contract is unchanged: every path field present in
  the text form appears with the same value under ``--json``.
* The parser-compat shape: each section header (``Foreground:``,
  ``Active queue:``, ``Legacy queue:``, ``Daemon owner record:``) is
  followed by indented ``Key  Value`` rows; queue sections expose
  their path under literal key ``Path`` so the canary's
  ``_row(section, "Path")`` finds it.

The fixture stubs out network and live-process probes so the test only
exercises the rendering surface.
"""

from __future__ import annotations

import json
import re
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
# Canary parser replica (in-tree, no sibling repo dependency)
# ---------------------------------------------------------------------------
#
# This replicates the exact lex/section-walk logic from the sibling
# canary parser at ``spec-kitty-end-to-end-testing/src/spec_kitty_e2e/
# identity_boundary/status_parser.py`` so the parser-compat test does
# not need the sibling repo on disk. The contract this test pins is:
#
#   * The line-oriented stream from ``sync status --check`` is composed
#     of section-header rows (ending with ``:``) and key/value rows.
#   * Key/value rows match the regex
#     ``^\\s*(?P<key>\\S.*?)\\s{2,}(?P<value>.+?)\\s*$``.
#   * Section-rows have leading whitespace; the section ends at the next
#     unindented row.
#   * Queue sections (``Active queue:``, ``Legacy queue:``) expose their
#     canonical path under literal child key ``Path``.

_PARSER_KEY_VALUE_RE = re.compile(
    r"^\s*(?P<key>\S.*?)\s{2,}(?P<value>.+?)\s*$"
)


def _parser_split_rows(stdout: str) -> list[tuple[str, str]]:
    """Replica of the sibling parser's ``_split_rows`` lexer."""
    rows: list[tuple[str, str]] = []
    for raw in stdout.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        match = _PARSER_KEY_VALUE_RE.match(line)
        if match is None:
            stripped = line.strip()
            if stripped.endswith(":"):
                rows.append((line, ""))
            continue
        key = match.group("key").rstrip(":")
        leading_ws = len(line) - len(line.lstrip(" "))
        rows.append((" " * leading_ws + key, match.group("value").strip()))
    return rows


def _parser_find_section_rows(
    rows: list[tuple[str, str]], header: str
) -> list[tuple[str, str]]:
    """Replica of the sibling parser's ``_find_section_rows`` walker."""
    out: list[tuple[str, str]] = []
    in_section = False
    for key, value in rows:
        stripped = key.strip()
        is_indented = key.startswith(" ")
        if not in_section:
            if stripped == header:
                in_section = True
            continue
        if is_indented:
            out.append((stripped, value))
            continue
        break
    return out


def _parser_row_value(section: list[tuple[str, str]], key: str) -> str | None:
    for k, v in section:
        if k == key:
            return v
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Section-scoped path rows: (parser-section-header, parser-row-key,
# corresponding JSON dotted path).
_SECTION_PATH_MATRIX: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("Foreground:", "Executable path", ("foreground", "executable_path")),
    ("Foreground:", "Source path", ("foreground", "source_path")),
    ("Foreground:", "Queue DB path", ("foreground", "queue_db_path")),
    ("Active queue:", "Path", ("active_queue", "path")),
    ("Legacy queue:", "Path", ("legacy_queue", "path")),
)


def _extract_section_path(
    stdout: str, header: str, key: str
) -> str | None:
    """Pull a single ``(section, key)`` value out of the rendered text.

    Uses the canary parser's exact walk semantics so this test fails iff
    the cross-repo contract would fail.
    """
    rows = _parser_split_rows(stdout)
    section = _parser_find_section_rows(rows, header)
    return _parser_row_value(section, key)


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
    every canonical file path verbatim under its parser-attributed section
    header, so a downstream consumer can pull a path from the rendered
    output and ``stat()`` it on disk.
    """
    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code in (0, 2), result.stdout

    for header, key, _ in _SECTION_PATH_MATRIX:
        value = _extract_section_path(result.stdout, header, key)
        assert value is not None, (
            f"missing parser-attributed path: {header!r} / {key!r}\n"
            f"STDOUT:\n{result.stdout}"
        )
        assert value, f"empty value for {header!r} / {key!r}"
        assert "…" not in value, (
            f"ellipsis in {header!r} / {key!r}: {value!r}"
        )


def test_long_path_renders_without_ellipsis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seed a > 100-char queue DB path; the rendered text must contain it verbatim.

    Patches ``compute_foreground_identity`` and ``build_boundary_failure_set``
    so the renderer sees a long synthetic path. The canonical ``--json``
    form already emits the full path; this test pins the text-form parity
    AND the parser-compat attribution (the long path must surface under
    ``Active queue:`` / ``Path``, not some other key/section).
    """
    long_path = (
        "/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/"
        "spec-kitty-extremely-long-path-for-regression-test/"
        "nested/level/queue.db"
    )
    assert len(long_path) > 100

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

    # Parser-attributed: the long path appears under Foreground/Queue DB
    # path AND Active queue/Path.
    fg_qdb = _extract_section_path(
        result.stdout, "Foreground:", "Queue DB path"
    )
    assert fg_qdb == long_path, (
        f"Foreground/Queue DB path mismatch: {fg_qdb!r}\n"
        f"STDOUT:\n{result.stdout}"
    )
    active_path = _extract_section_path(
        result.stdout, "Active queue:", "Path"
    )
    assert active_path == long_path, (
        f"Active queue/Path mismatch: {active_path!r}\n"
        f"STDOUT:\n{result.stdout}"
    )
    assert long_path in result.stdout, (
        f"long path not present verbatim in stdout:\n"
        f"long_path={long_path!r}\n\nSTDOUT:\n{result.stdout}"
    )
    # Sanity: no ellipsis in the boundary section itself. The earlier
    # ``Spec Kitty Sync Status`` summary Rich Table is a separate
    # surface that may still ellipsise unrelated fields (e.g.
    # ``Config File`` under non-TTY capture); WP02 does not widen
    # that table. We slice the stdout to just the Identity Boundary
    # block before asserting no ``…``.
    boundary_start = result.stdout.index("Identity Boundary")
    boundary_block = result.stdout[boundary_start:]
    assert "…" not in boundary_block, (
        f"unexpected ellipsis in Identity Boundary block:\n{boundary_block}"
    )

    _ = real_compute


def test_narrow_console_does_not_wrap_path_rows() -> None:
    """A 40-column Console must still print path rows on a single line.

    The path renderer is supposed to bypass the width-bound Table entirely.
    We exercise the section emitter directly with a synthetic narrow
    Console and assert each path row appears on a single physical line
    (no wrap, no ellipsis).
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
    sync_cmd._print_boundary_section(
        narrow,
        "Active queue:",
        [
            ("Path", long_path),
            ("Event count", "0"),
        ],
    )
    rendered = narrow_buf.getvalue()
    # The long path must appear on a single physical line under the
    # section. We assert by looking for the path verbatim somewhere in
    # the rendered text and confirming the line containing it also
    # starts with the indented ``Path`` key.
    assert long_path in rendered, (
        f"long path absent from narrow rendering:\n{rendered}"
    )
    for line in rendered.splitlines():
        if long_path in line:
            assert line.lstrip().startswith("Path"), (
                f"long path line does not start with 'Path' key:\n"
                f"LINE:{line!r}\nALL:{rendered}"
            )
    assert "…" not in rendered, f"ellipsis present in narrow output:\n{rendered}"


def test_text_form_paths_match_json_form_byte_for_byte() -> None:
    """``--json`` and text emit byte-identical values for every path field."""
    json_result = runner.invoke(app, ["status", "--check", "--json"])
    assert json_result.exit_code in (0, 2), json_result.stdout
    payload = json.loads(json_result.stdout.strip())

    text_result = runner.invoke(app, ["status", "--check"])
    assert text_result.exit_code in (0, 2), text_result.stdout

    for header, key, dotted in _SECTION_PATH_MATRIX:
        json_value = _read_json_path(payload, dotted)
        text_value = _extract_section_path(text_result.stdout, header, key)
        assert text_value is not None, (
            f"missing text-form value for {header!r}/{key!r}\n"
            f"STDOUT:\n{text_result.stdout}"
        )
        assert json_value == text_value, (
            f"JSON/text mismatch for {header}/{key}:\n"
            f"  json={json_value!r}\n  text={text_value!r}\n"
            f"FULL STDOUT:\n{text_result.stdout}"
        )


def test_canary_parser_compat_smoke() -> None:
    """B-1 regression: the rendered text must satisfy the sibling canary parser.

    This replicates the canary parser's required-section + required-Path
    assertions (the contract WP02 cycle 1 fixes). Specifically:

    1. All four section headers (``Foreground:``, ``Daemon owner record:``,
       ``Active queue:``, ``Legacy queue:``) appear unindented in the
       rendered text.
    2. Both queue sections expose a child row with key literally ``Path``.
    3. Each ``Path`` value is non-empty (no empty-string sentinel that
       would trip ``_require_str``).

    Had this test existed in cycle 0, it would have caught the
    ``active_queue.Path missing`` ValueError raised by WP04 canary
    verification.
    """
    result = runner.invoke(app, ["status", "--check"])
    assert result.exit_code in (0, 2), result.stdout

    rows = _parser_split_rows(result.stdout)
    required_headers = {
        "Foreground:",
        "Daemon owner record:",
        "Active queue:",
        "Legacy queue:",
    }
    seen_headers = {key.strip() for key, _ in rows if key.strip() in required_headers}
    missing = required_headers - seen_headers
    assert not missing, (
        f"required section headers missing from --check stdout: {missing}\n"
        f"STDOUT:\n{result.stdout}"
    )

    # Active queue / Path attribution.
    active = _parser_find_section_rows(rows, "Active queue:")
    active_path = _parser_row_value(active, "Path")
    assert active_path is not None and active_path, (
        "Active queue section missing 'Path' child row; canary parser "
        "raises 'missing required string field active_queue.Path'.\n"
        f"STDOUT:\n{result.stdout}"
    )

    # Legacy queue / Path attribution.
    legacy = _parser_find_section_rows(rows, "Legacy queue:")
    legacy_path = _parser_row_value(legacy, "Path")
    assert legacy_path is not None and legacy_path, (
        "Legacy queue section missing 'Path' child row; canary parser "
        "raises 'missing required string field legacy_queue.Path'.\n"
        f"STDOUT:\n{result.stdout}"
    )

    # Event count is also a required parser field per the sibling
    # parser's ``_coerce_int(_row(active, "Event count"), ...)``.
    assert _parser_row_value(active, "Event count") is not None, (
        "Active queue section missing 'Event count' child row"
    )
    assert _parser_row_value(legacy, "Event count") is not None, (
        "Legacy queue section missing 'Event count' child row"
    )
