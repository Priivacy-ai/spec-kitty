"""Deterministic, colourless rendering for the ``agent`` CLI test package.

The ``agent`` command surface renders every human / ``--json`` line through the
single canonical CLI console seam (:mod:`specify_cli.cli.console`): the
stdout ``console`` and stderr ``err_console`` singletons. Every module-level
``console`` in ``agent/tasks.py``, ``agent/tests.py``, the extracted
``agent/mission_*`` seams, and ``selector_resolution._err_console`` *is* one of
those two shared instances (they import the seam, they no longer construct their
own ``Console``).

Rich honours ``FORCE_COLOR`` **above** ``NO_COLOR`` and colourises at render
time, which would otherwise leak ANSI escapes into the golden ``--help``
fixtures and the ``--json`` envelopes (``json.loads`` chokes on ``\x1b[...``).
Because determinism is now a property of the *object*, one ``set_plain(True)``
call on each shared singleton neutralises colour across the whole surface at
once — no per-module ``monkeypatch.setattr`` enumeration and no ``os.environ``
mutation (env writes leak into subprocesses and sibling tests).

Contract-preserving: this only disables colour. Width is left to Rich's
per-invocation env detection (the golden ``--help`` tests own their ``COLUMNS``
via ``HELP_ENV``; others pass ``terminal_width`` to ``CliRunner``), and command
names, flag names, JSON keys, exit codes, and message text are untouched — a
genuine surface change still fails loudly.

The top-level ``tests/conftest.py`` already applies this seam toggle globally;
this package-local fixture keeps the ``agent`` surface self-documenting and
robust even in isolation.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _portable_cli_render_env() -> Iterator[None]:
    """Render the shared CLI console seam colourlessly for every ``agent`` test."""
    from specify_cli.cli.console import console, err_console

    console.set_plain(True)
    err_console.set_plain(True)
    try:
        yield
    finally:
        console.set_plain(False)
        err_console.set_plain(False)
