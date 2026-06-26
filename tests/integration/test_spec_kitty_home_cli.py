"""CLI-level proof of ``SPEC_KITTY_HOME`` state isolation (issue #2171, inverted).

This mirrors the reproduction from GitHub issue #2171 turned into a *passing*
assertion (``contracts/state-surface-map.md`` → "End-to-end CLI contract"):
with distinct ``HOME`` and ``SPEC_KITTY_HOME``, running ``sync server <url>``
through the real Typer command writes ``config.toml`` **only** under
``SPEC_KITTY_HOME`` — the default ``$HOME/.spec-kitty`` stays clean
(SC-001 / SC-002 / FR-001).

A second case pins backward compatibility: with ``SPEC_KITTY_HOME`` unset the
POSIX default ``~/.spec-kitty`` layout is preserved (SC-003 / NFR-001).

The command under test only writes a local TOML file — no daemon, no real
ports, no network — so this stays a lightweight ``CliRunner`` test and needs no
serial (``-n0``) marker.

Spec IDs: SC-001, SC-002, SC-003, FR-001, NFR-001
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.sync import app
from specify_cli.sync.feature_flags import SAAS_SYNC_ENV_VAR

pytestmark = pytest.mark.integration

runner = CliRunner()

# A syntactically valid HTTPS URL that performs no network I/O when set.
_SYNC_URL = "https://example.invalid"


def test_spec_kitty_home_isolates_sync_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Distinct HOME + SPEC_KITTY_HOME ⇒ config lands ONLY under the latter.

    This is the literal issue #2171 reproduction, inverted into the assertion
    that the fix makes true: ``<SPEC_KITTY_HOME>/config.toml`` exists and
    ``<HOME>/.spec-kitty/config.toml`` does not (FR-001 / SC-001 / SC-002).
    """
    default_home = tmp_path / "default-home"
    isolated_root = tmp_path / "isolated-root"
    default_home.mkdir()
    isolated_root.mkdir()

    monkeypatch.setenv("HOME", str(default_home))
    monkeypatch.setenv("SPEC_KITTY_HOME", str(isolated_root))
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")

    result = runner.invoke(app, ["server", _SYNC_URL])
    assert result.exit_code == 0, result.output

    # FR-001 / SC-001: the sync config landed under SPEC_KITTY_HOME ...
    assert (isolated_root / "config.toml").is_file()
    # ... and NOT under the default home (the inverted #2171 repro / SC-002).
    assert not (default_home / ".spec-kitty" / "config.toml").exists()


@pytest.mark.skipif(
    sys.platform.startswith("win"),
    reason=(
        "POSIX-only default-home fallback (~/.spec-kitty); Windows resolves the "
        "unset default via platformdirs, not Path.home()."
    ),
)
def test_unset_spec_kitty_home_preserves_posix_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-003 / NFR-001: with the variable unset, config lands at ``~/.spec-kitty``.

    Backward compatibility — the byte-identical POSIX layout is preserved when no
    isolation root is selected.
    """
    default_home = tmp_path / "posix-home"
    default_home.mkdir()

    monkeypatch.setenv("HOME", str(default_home))
    monkeypatch.delenv("SPEC_KITTY_HOME", raising=False)
    monkeypatch.setenv(SAAS_SYNC_ENV_VAR, "1")

    result = runner.invoke(app, ["server", _SYNC_URL])
    assert result.exit_code == 0, result.output

    assert (default_home / ".spec-kitty" / "config.toml").is_file()
