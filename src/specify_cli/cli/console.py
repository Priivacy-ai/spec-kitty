"""Canonical CLI output seam.

Every CLI-originated line of output routes through the single :data:`console`
(stdout) / :data:`err_console` (stderr) instances exported here. This is the
*one* place that owns Spec Kitty's terminal-output policy — no command module
constructs its own ``rich.console.Console`` (see
``tests/architectural/test_cli_console_single_seam.py``).

Two invariants motivate the seam (GitHub #2632):

* **Machine output is always plain.** ``--json`` payloads are emitted with
  :meth:`CliConsole.emit_json` / :meth:`CliConsole.print_json`, which bypass
  Rich's syntax highlighter entirely. So a caller that pipes ``--json`` to
  ``jq`` — or runs under a ``FORCE_COLOR`` harness (the Claude Code harness
  exports ``FORCE_COLOR=3``) — never gets ANSI escapes spliced into the JSON,
  which would otherwise raise ``json.loads`` ``Expecting value``.

* **Determinism is a property of the object, not the environment.** Human
  output stays styled and terminal-aware, but tests obtain colourless,
  substring-stable output by calling :meth:`CliConsole.set_plain` on this one
  shared instance — never by mutating ``os.environ`` (env mutation leaks into
  subprocesses and sibling tests). Because every module imports the *same*
  singleton, one ``set_plain`` call neutralises colour everywhere at once.
"""

from __future__ import annotations

import json as _json
from typing import IO, Any

from rich.console import Console

__all__ = ["CliConsole", "console", "err_console"]


class CliConsole(Console):
    """A :class:`rich.console.Console` whose ``--json`` output is always plain.

    Drop-in for every ``rich`` call site (``print``/``rule``/``status`` and
    ``Live(console=...)``/``Progress(console=...)`` all work unchanged because
    this *is* a ``Console``). Only the machine-output path is specialised.
    """

    def _write_plain(self, payload: str) -> None:
        out: IO[str] = self.file
        out.write(payload if payload.endswith("\n") else payload + "\n")
        out.flush()

    def emit_json(
        self,
        payload: Any,
        *,
        indent: int | str | None = 2,
        sort_keys: bool = False,
        default: Any = None,
    ) -> None:
        """Emit *payload* as plain, un-styled JSON — the preferred ``--json`` sink."""
        self._write_plain(
            _json.dumps(
                payload,
                indent=indent,
                sort_keys=sort_keys,
                default=default,
                ensure_ascii=False,
            )
        )

    def print_json(
        self,
        json: str | None = None,
        *,
        data: Any = None,
        indent: int | str | None = 2,
        sort_keys: bool = False,
        default: Any = None,
        **_ignored: Any,
    ) -> None:
        """Plain-JSON override of ``Console.print_json`` (no syntax highlighting).

        Accepts the same call shapes as Rich — a pre-serialised ``json`` string
        or a ``data=`` object — but never colourises, so every existing
        ``console.print_json(json.dumps(...))`` call site becomes ``--json``-safe
        simply by routing through this seam. ``highlight``/``ensure_ascii`` and
        other Rich-only kwargs are accepted and ignored.
        """
        if json is not None:
            self._write_plain(json)
            return
        self.emit_json(data, indent=indent, sort_keys=sort_keys, default=default)

    def set_plain(self, plain: bool = True) -> None:
        """Toggle colourless rendering on THIS instance, in place.

        Mutates the shared singleton so every ``from ... import console`` holder
        observes it — the test-determinism seam. Colour only; width/wrapping are
        left to Rich's per-invocation env detection (golden ``--help`` fixtures
        depend on ``COLUMNS``).
        """
        self.no_color = plain
        self._color_system = None if plain else self._detect_color_system()


console = CliConsole()
err_console = CliConsole(stderr=True)
