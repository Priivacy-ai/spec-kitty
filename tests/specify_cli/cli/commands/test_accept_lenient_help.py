"""``accept --help`` must independently discover the path-convention link (#3730).

FR-006/SC-003: the strict-mode failure text now points an operator at
``accept --lenient`` (see ``tests/agent/test_validators_unit.py``'s
``test_format_errors_names_lenient_before_mkdir_and_drops_unconditional_claim``),
but an operator who reaches for ``--help`` first, without ever seeing the
failure text, needs the same discovery path. This test drives the real
``--lenient`` ``typer.Option`` help string through a standalone Typer runner
(same technique as ``test_implement_bulk_edit_flag.py``) so a regression that
narrows the help text back to generic "skip strict metadata validation"
wording is caught here, independent of the failure-text test.
"""

from __future__ import annotations

import typer
from typer.testing import CliRunner

import pytest

from specify_cli.cli.commands.accept import accept

pytestmark = [pytest.mark.unit, pytest.mark.fast]


def test_accept_help_mentions_path_conventions_for_lenient_flag() -> None:
    helper = typer.Typer()
    helper.command(name="accept")(accept)

    runner = CliRunner(env={"COLUMNS": "200", "TERM": "dumb"})
    result = runner.invoke(helper, ["accept", "--help"], terminal_width=200)

    assert result.exit_code == 0, f"help invocation failed: {result.output}"
    normalized_help = " ".join(result.output.lower().split())
    assert "--lenient" in normalized_help
    # Scoped to "path-convention" (not bare "path"): an unscoped substring
    # check could be satisfied by an unrelated, future "--path"-ish option's
    # help text and silently mask a --lenient regression.
    assert "path-convention" in normalized_help, (
        "The --lenient help string must mention path-convention enforcement "
        "so --help is an independent discovery path to the same information "
        "as the strict-mode failure text; current output:\n" + result.output
    )
