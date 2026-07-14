"""Architectural guardrail: one canonical CLI-output console (GitHub #2632).

All CLI-originated output must route through the single
``specify_cli.cli.console`` seam (``CliConsole`` / ``console`` / ``err_console``)
so that (a) ``--json`` output is plain by construction and (b) colour is a
property of the shared object, not the environment (ADR 2026-07-14-1).

No module under ``src/specify_cli/cli/`` may construct a raw
``rich.console.Console(...)`` — only the seam module itself, and only the seam
class ``CliConsole(...)`` may be instantiated elsewhere (for the few
deliberately-special consoles, e.g. a fixed ``width=``). Type annotations
(``console: Console``) are fine — they are not constructions.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLI_ROOT = _REPO_ROOT / "src" / "specify_cli" / "cli"
_SEAM = _CLI_ROOT / "console.py"


def _raw_console_constructions(path: Path) -> list[str]:
    """Return ``path`` sites that call the bare ``Console(...)`` constructor."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Bare ``Console(...)`` — ``CliConsole(...)`` and ``x.Console(...)`` attr
        # calls are not this exact name, so only the raw rich constructor trips.
        if isinstance(func, ast.Name) and func.id == "Console":
            try:
                where = path.relative_to(_REPO_ROOT)
            except ValueError:
                where = path  # planted/tmp file outside the repo (non-vacuity test)
            hits.append(f"{where}:{node.lineno}")
    return hits


def test_cli_layer_constructs_no_raw_console() -> None:
    offenders: list[str] = []
    for path in sorted(_CLI_ROOT.rglob("*.py")):
        if path == _SEAM:
            continue  # the seam owns the one CliConsole(Console) definition
        offenders.extend(_raw_console_constructions(path))

    assert not offenders, (
        "CLI modules must route output through the canonical "
        "specify_cli.cli.console seam (console/err_console/CliConsole), not a "
        "raw rich Console(). Offending constructions:\n" + "\n".join(offenders)
    )


def test_detector_bites_on_a_planted_raw_console(tmp_path: Path) -> None:
    """Non-vacuity: a planted raw ``Console()`` construction must be flagged."""
    planted = tmp_path / "planted.py"
    planted.write_text("console = Console()\n", encoding="utf-8")
    assert _raw_console_constructions(planted)

    clean = tmp_path / "clean.py"
    clean.write_text(
        "from specify_cli.cli.console import console\n"
        "special = CliConsole(width=200)\n"
        "def f(c: Console) -> None: ...\n",
        encoding="utf-8",
    )
    assert not _raw_console_constructions(clean)
