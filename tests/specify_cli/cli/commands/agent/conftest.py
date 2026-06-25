"""Shared, environment-portable harness for the ``agent tasks`` CLI tests.

The ``agent tasks`` command surface renders all human/JSON output through two
module-level Rich ``Console`` objects:

* ``specify_cli.cli.commands.agent.tasks.console`` (stdout)
* ``specify_cli.cli.selector_resolution._err_console`` (stderr)

Rich honours ``FORCE_COLOR`` **above** ``NO_COLOR``/``TERM=dumb`` and decides
colour/width from the ambient environment at *render* time. Developer shells
and agent harnesses frequently export ``FORCE_COLOR`` (e.g. the Claude Code
harness sets ``FORCE_COLOR=3``), which leaks ANSI escapes into:

* the golden ``--help`` fixtures (byte-comparison breaks), and
* the ``--json`` error envelopes printed via ``print_json`` on the stderr
  console (``json.loads`` chokes on ``\x1b[...`` syntax-highlight codes).

These tests were captured in CI's plain environment, so they false-RED on any
machine that forces colour even though the *behaviour* is identical. This
autouse fixture makes the harness portable by pinning a deterministic,
colourless render environment for the whole package:

* drop ``FORCE_COLOR`` / ``CLICOLOR_FORCE`` and set ``NO_COLOR=1`` so no Rich
  console anywhere in the call tree colourises, and
* swap the two module-level consoles for fresh, width-100, no-colour instances
  matching the width the committed fixtures were captured at.

It is *contract-preserving*: it only neutralises colour and pins width. It
never touches command names, flag names, JSON keys, exit codes, or message
text, so a genuine surface change (renamed flag/command, dropped key, changed
exit code) still fails loudly.
"""

from __future__ import annotations

import importlib

import pytest
from rich.console import Console


def _portable_console(*, stderr: bool = False) -> Console:
    """A deterministic, colourless console.

    Colour is disabled hard (``color_system=None``); width is left to Rich's
    env detection so each invocation's ``COLUMNS`` / ``terminal_width`` still
    governs wrapping (the golden ``--help`` tests rely on that).
    """
    return Console(
        stderr=stderr,
        no_color=True,
        force_terminal=False,
        color_system=None,
    )


@pytest.fixture(autouse=True)
def _portable_cli_render_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralise ambient colour-forcing for every test in this directory.

    Colour-forcing is the universal portability hazard, so it is dropped
    globally. Terminal *width* is deliberately NOT forced here: individual
    tests own their width (the golden ``--help`` tests pass ``env=HELP_ENV``
    with ``COLUMNS=100``; others pass ``terminal_width=...`` to ``CliRunner``).
    Forcing a global ``COLUMNS`` would clobber those per-test choices.
    """
    # Rich precedence is FORCE_COLOR > NO_COLOR; remove the forcers, then deny.
    for forcing in ("FORCE_COLOR", "CLICOLOR_FORCE"):
        monkeypatch.delenv(forcing, raising=False)
    monkeypatch.setenv("NO_COLOR", "1")

    # The env alone is insufficient: the module-level consoles were constructed
    # at import time (snapshotting the forcing env). Replace them with fresh,
    # colourless instances so output is deterministic regardless of how/when the
    # modules were first imported. Width is left to Rich's env detection so each
    # invocation's COLUMNS / terminal_width still governs wrapping.
    from specify_cli.cli import selector_resolution
    from specify_cli.cli.commands.agent import tasks as tasks_module
    from specify_cli.cli.commands.agent import tests as tests_module

    monkeypatch.setattr(tasks_module, "console", _portable_console(), raising=False)
    monkeypatch.setattr(
        selector_resolution, "_err_console", _portable_console(stderr=True), raising=False
    )
    # The sibling ``agent tests stale-check`` command emits its ``--json`` via its
    # own module-level consoles (``print_json`` colourises); neutralise them too
    # so the whole package is portable, not just the tasks contract files.
    monkeypatch.setattr(tests_module, "console", _portable_console(), raising=False)
    monkeypatch.setattr(
        tests_module, "err_console", _portable_console(stderr=True), raising=False
    )

    # #2056 decomposition: the ``agent mission`` surface no longer renders through a
    # single ``mission.console`` — each extracted seam owns its own module-level
    # ``console = Console()``. Each snapshots the forcing env at import time, so under
    # a ``FORCE_COLOR`` harness (e.g. Claude Code sets ``FORCE_COLOR=3``) Rich
    # syntax-highlight ANSI (notably leading-digit colourising of mission slugs like
    # ``001-demo``) leaks into the human/JSON output and false-REDs plain-substring
    # assertions that pass in CI's plain environment. Neutralise every seam console so
    # the whole package stays FORCE_COLOR-portable (contract-preserving: colour only).
    for _seam_name in (
        "mission",
        "mission_create",
        "mission_check_prerequisites",
        "mission_setup_plan",
        "mission_record_analysis",
        "mission_finalize",
        "mission_accept_merge",
        "mission_branch_context",
        "mission_parsing",
    ):
        _seam_module = importlib.import_module(
            f"specify_cli.cli.commands.agent.{_seam_name}"
        )
        if hasattr(_seam_module, "console"):
            monkeypatch.setattr(
                _seam_module, "console", _portable_console(), raising=False
            )
