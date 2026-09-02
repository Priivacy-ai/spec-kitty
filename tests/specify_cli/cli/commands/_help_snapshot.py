"""Width-invariant ``--help`` snapshot helpers for CLI golden tests.

Typer renders ``--help`` through Rich, and Rich sizes that output to the
*ambient* terminal. Under an interactive TTY it honours ``COLUMNS``; but with no
TTY — exactly the case under :class:`typer.testing.CliRunner` and on CI — Rich
takes its 80-column fallback and effectively **ignores ``COLUMNS`` on the help
path** (``rich.console.Console.size`` only consults ``COLUMNS`` after terminal
detection, and the ``TERM=dumb`` branch short-circuits to ``80×25``). That made
the golden ``--help`` snapshots environment-fragile: a developer's 100-column
local run and CI's 80-column run wrapped long option descriptions at different
points, so byte/line snapshots that were green locally went red on CI.

:func:`force_wide_help_console` removes the ambient terminal from the equation
entirely. It pins Typer's help console to a fixed, very wide, colourless size so
**no line ever wraps** and the rendered help is byte-identical on every machine,
regardless of ``COLUMNS`` or whether stdout is a TTY. The key is setting *both*
console dimensions: :pyattr:`rich.console.Console.size` early-returns the
explicit size only when width AND height are set, bypassing the TTY / ``COLUMNS``
/ ``TERM=dumb`` detection paths that width-alone leaves in play. Colour is
disabled through Typer's public module globals (read at console-construction
time) so no ANSI styling leaks in either.

:func:`normalize_help` then strips box-drawing characters and collapses internal
whitespace so each usage/option entry becomes a single logical line — the
canonical, width-invariant snapshot form the golden fixtures encode.
"""

from __future__ import annotations

import re

import pytest
import typer.rich_utils as _rich_utils
from rich.console import Console

# Far wider than any help line the CLI can produce, so Rich never wraps an
# option description. The exact value is irrelevant to the normalized snapshot
# (trailing padding is collapsed away); it only has to exceed the widest row.
_HELP_CONSOLE_WIDTH = 10_000
# A concrete height is what makes the pin deterministic: Rich returns an
# explicit size unchanged only when BOTH dimensions are set (see module docstring).
_HELP_CONSOLE_HEIGHT = 100

_BOX_DRAWING = re.compile(r"[│┌┐└┘╭╮╰╯─]")
_INTERNAL_WHITESPACE = re.compile(r"\s+")


def force_wide_help_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin Typer's help console to a fixed wide, colourless size.

    Makes ``--help`` rendering wrap-free and byte-identical on any machine —
    with ``COLUMNS`` set or unset, under a TTY or not — so the golden snapshots
    are genuinely width-invariant rather than merely pinned to one width.
    """
    # ``_get_rich_console`` reads these module globals at call time; forcing them
    # to a fixed, colour-free configuration keeps ANSI out of the snapshot.
    monkeypatch.setattr(_rich_utils, "COLOR_SYSTEM", None)
    monkeypatch.setattr(_rich_utils, "FORCE_TERMINAL", False)

    original_get_console = _rich_utils._get_rich_console

    def _fixed_width_console(stderr: bool = False) -> Console:
        console = original_get_console(stderr=stderr)
        # Setting both dimensions triggers Rich's explicit-size early return,
        # bypassing TTY / COLUMNS / TERM=dumb detection entirely.
        console.size = (_HELP_CONSOLE_WIDTH, _HELP_CONSOLE_HEIGHT)
        return console

    monkeypatch.setattr(_rich_utils, "_get_rich_console", _fixed_width_console)


def normalize_help(text: str) -> list[str]:
    """Return help *text* as box-free, whitespace-collapsed logical lines.

    Combined with :func:`force_wide_help_console` (which guarantees no wrapping),
    every option/usage entry collapses to exactly one line, so the snapshot is
    stable across terminal widths while still failing on any usage / description
    / flag / help-text drift.
    """
    out: list[str] = []
    for line in text.splitlines():
        cleaned = _INTERNAL_WHITESPACE.sub(" ", _BOX_DRAWING.sub("", line)).strip()
        if cleaned:
            out.append(cleaned)
    return out
