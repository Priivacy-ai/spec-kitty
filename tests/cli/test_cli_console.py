"""Unit tests for the canonical CLI-output seam (``specify_cli.cli.console``).

Covers the two invariants the seam exists to guarantee (GitHub #2632, ADR
2026-07-14-1): ``--json`` output is plain by construction, and colour is a
property of the *object* (``set_plain``) — never the environment. Every test
forces colour ON at the instance level (``force_terminal=True``) so a failure
means the seam leaked ANSI, not that the ambient env happened to be plain.
"""

from __future__ import annotations

import io
import json

import pytest
from rich.console import Console

from specify_cli.cli.console import CliConsole, console, err_console

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_ESC = "\x1b["


def _forced() -> tuple[CliConsole, io.StringIO]:
    """A colour-forced CliConsole writing to an in-memory buffer."""
    buf = io.StringIO()
    return CliConsole(file=buf, force_terminal=True), buf


# ── emit_json ────────────────────────────────────────────────────


def test_emit_json_is_plain_under_forced_colour() -> None:
    c, buf = _forced()
    c.emit_json({"id": "software-dev", "n": 42})
    out = buf.getvalue()
    assert _ESC not in out
    assert json.loads(out) == {"id": "software-dev", "n": 42}


def test_emit_json_honours_indent_and_sort_keys() -> None:
    c, buf = _forced()
    c.emit_json({"b": 1, "a": 2}, indent=None, sort_keys=True)
    out = buf.getvalue().strip()
    assert out == '{"a": 2, "b": 1}'


def test_emit_json_uses_default_serialiser() -> None:
    c, buf = _forced()
    c.emit_json({"p": object()}, default=lambda _o: "coerced")
    assert json.loads(buf.getvalue())["p"] == "coerced"


# ── print_json (Rich-compatible call shapes) ─────────────────────


def test_print_json_from_serialised_string_is_plain() -> None:
    c, buf = _forced()
    c.print_json(json.dumps({"k": "v", "n": 1}))
    out = buf.getvalue()
    assert _ESC not in out
    assert json.loads(out) == {"k": "v", "n": 1}


def test_print_json_from_data_kwarg_is_plain() -> None:
    c, buf = _forced()
    c.print_json(data={"k": "v"})
    out = buf.getvalue()
    assert _ESC not in out
    assert json.loads(out) == {"k": "v"}


def test_print_json_accepts_and_ignores_rich_only_kwargs() -> None:
    c, buf = _forced()
    # Rich's print_json takes highlight=/ensure_ascii=; the seam must accept
    # them (call-shape compat) without styling the output.
    c.print_json(json.dumps({"k": "v"}), highlight=True, ensure_ascii=True)
    assert _ESC not in buf.getvalue()


# ── set_plain (object-level determinism, no env) ─────────────────


def test_set_plain_true_strips_colour_from_human_output() -> None:
    c, buf = _forced()
    c.print("[red]delivered[/red] [green]1[/green]")
    assert _ESC in buf.getvalue()  # colour is on by default under force_terminal

    buf.truncate(0)
    buf.seek(0)
    c.set_plain(True)
    c.print("[red]delivered[/red] [green]1[/green]")
    plain = buf.getvalue()
    assert _ESC not in plain
    assert "delivered 1" in plain  # substring is contiguous again


def test_set_plain_false_restores_colour() -> None:
    c, buf = _forced()
    c.set_plain(True)
    c.set_plain(False)
    c.print("[green]ok[/green]")
    assert _ESC in buf.getvalue()


def test_set_plain_does_not_change_width() -> None:
    c, _buf = _forced()
    width_before = c.width
    c.set_plain(True)
    assert c.width == width_before  # colour only; wrapping/width untouched


# ── non-vacuity: prove a vanilla Console DOES corrupt ────────────


def test_vanilla_console_print_json_would_leak_ansi() -> None:
    """The bug the seam fixes: stock Rich colourises JSON under forced colour."""
    buf = io.StringIO()
    Console(file=buf, force_terminal=True).print_json(json.dumps({"id": "x"}))
    out = buf.getvalue()
    assert _ESC in out  # stock Rich leaks ANSI ...
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)  # ... which corrupts json.loads


# ── module singletons ────────────────────────────────────────────


def test_module_singletons_are_seam_instances() -> None:
    assert isinstance(console, CliConsole)
    assert isinstance(err_console, CliConsole)
    assert isinstance(console, Console)  # drop-in for Live/Progress/console: Console


def test_err_console_targets_stderr() -> None:
    assert err_console.stderr is True
    assert console.stderr is False
