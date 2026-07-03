"""ANSI-escape stripping for render-robust CLI help/usage assertions.

Typer renders ``--help`` and usage errors through Rich. Under CI, Rich detects
the CI environment (``CI`` / ``FORCE_COLOR``) and *force-enables* terminal
styling even when the click ``CliRunner`` captures to a non-TTY buffer. The
captured output then carries SGR colour codes (and Rich may wrap option names),
so a raw ``substring in result.output`` check misses a flag literal that is in
fact present. Stripping the ANSI codes yields the plain text the user reads,
letting an assertion pin the *contract* ("the flag/token is exposed in help")
without coupling to Rich's colour/rendering differences across environments.
"""

from __future__ import annotations

import re

#: Matches CSI SGR sequences (colour/style) emitted by Rich, e.g. ``\x1b[1m``.
_ANSI_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Return ``text`` with ANSI SGR (colour/style) escape codes removed."""
    return _ANSI_SGR_RE.sub("", text)
