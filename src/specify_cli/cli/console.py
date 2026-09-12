"""Canonical CLI output seam.

Every CLI-originated line of output routes through the single :data:`console`
(stdout) / :data:`err_console` (stderr) instances exported here. This is the
*one* place that owns Spec Kitty's terminal-output policy — no command module
constructs its own ``rich.console.Console`` (see
``tests/architectural/test_cli_console_single_seam.py``).

Three invariants motivate the seam (GitHub #2632 / #701):

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

* **Human text never carries terminal-control bytes.** String renderables are
  sanitized before Rich markup parsing; nested Rich renderables are sanitized at
  the segment boundary without removing their styles. Machine JSON bypasses both
  hooks through :meth:`CliConsole.emit_json` / :meth:`CliConsole.print_json`.
"""

from __future__ import annotations

import json as _json
import re
import weakref
from collections.abc import Iterable
from typing import IO, Any, ClassVar

from rich.console import Console, ConsoleOptions, RenderableType
from rich.segment import Segment
from rich.text import Text

__all__ = ["CliConsole", "console", "err_console", "sanitize_terminal_text"]


_CSI_SEQUENCE = re.compile(r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]")
_OSC_SEQUENCE = re.compile(r"(?:\x1b\]|\x9d)[^\x07\x1b\x9c]*(?:\x07|\x1b\\|\x9c)?")
_UNSAFE_TERMINAL_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f\x9b\x9d]")


def sanitize_terminal_text(text: str) -> str:
    """Make untrusted display text inert before it reaches Rich markup parsing.

    CSI and OSC control sequences are removed as complete sequences. Remaining
    C0 controls are stripped except tab and newline, so a bare escape byte
    cannot introduce a terminal sequence after rendering.
    """
    without_terminal_sequences = _OSC_SEQUENCE.sub("", _CSI_SEQUENCE.sub("", text))
    return "".join(character for character in without_terminal_sequences if character in "\t\n" or ord(character) >= 0x20)


class CliConsole(Console):
    """A :class:`rich.console.Console` whose ``--json`` output is always plain.

    Drop-in for every ``rich`` call site (``print``/``rule``/``status`` and
    ``Live(console=...)``/``Progress(console=...)`` all work unchanged because
    this *is* a ``Console``). Only the machine-output path is specialised.
    """

    # Every live instance — the shared singletons AND the deliberately-distinct
    # specials (fixed-width / stderr consoles). ``set_all_plain`` reaches all of
    # them so the test seam neutralises colour across the WHOLE CLI surface with
    # one call, not just the two singletons.
    _instances: ClassVar[weakref.WeakSet[CliConsole]] = weakref.WeakSet()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        CliConsole._instances.add(self)

    def render_str(self, text: str, **kwargs: Any) -> Text:
        """Sanitize human-readable strings before Rich markup parsing."""
        return super().render_str(sanitize_terminal_text(text), **kwargs)

    def render(
        self,
        renderable: RenderableType,
        options: ConsoleOptions | None = None,
    ) -> Iterable[Segment]:
        """Sanitize rendered text in nested Rich objects without dropping styles."""
        for segment in super().render(renderable, options):
            if segment.text and _UNSAFE_TERMINAL_CONTROL.search(segment.text):
                segment = Segment(
                    sanitize_terminal_text(segment.text),
                    segment.style,
                    segment.control,
                )
            yield segment

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

    @classmethod
    def set_all_plain(cls, plain: bool = True) -> None:
        """Toggle plain rendering on EVERY live CliConsole instance.

        Covers the shared singletons and the deliberately-distinct specials
        (glossary/list fixed-width consoles, the stderr consoles) in one call.
        The test-determinism seam uses this so a single toggle neutralises
        colour across the whole CLI surface — object-level, never ``os.environ``.
        """
        for instance in list(cls._instances):
            instance.set_plain(plain)


console = CliConsole()
err_console = CliConsole(stderr=True)
