"""Regression tests for FR-006 (#790): the legacy ``--feature`` alias must
stay hidden from every leaf command's ``--help`` output.

These tests lock down two complementary invariants that are already correct
on ``main`` (verified during planning of mission
``release-3-2-0a5-tranche-1``, research note R5):

1. **Introspection invariant**: every parameter whose CLI flag is
   ``--feature`` must carry ``hidden=True`` so Click/Typer suppresses it
   from rendered help.

2. **Surface invariant**: the rendered ``--help`` text of every leaf
   command must NOT contain the substring ``--feature``. This catches
   help text drift even if Click ever changes how it formats hidden
   parameters.

If either assertion fails, the alias has leaked back into the user-visible
surface — the exact regression #790 closed.
"""

from __future__ import annotations

import re

import click
from click.testing import CliRunner
from typer.main import get_command

from specify_cli import app as _typer_app


# ---------------------------------------------------------------------------
# Resolve the underlying Click command tree.
# ---------------------------------------------------------------------------
# ``specify_cli`` exposes a Typer app. Sibling tests (e.g.
# ``test_doctrine_cli_removed.py``) import that Typer app directly and let
# Typer's CliRunner handle the conversion. For introspection we want the
# Click command tree, which Typer can give us via ``get_command``.
cli: click.Group = get_command(_typer_app)  # type: ignore[assignment]


FEATURE_TOKEN_RE = re.compile(r"--feature\b")


def _walk_leaf_commands(group: click.Group, prefix: tuple[str, ...] = ()):
    """Yield (path_tuple, command) for every leaf command under ``group``."""
    for name, cmd in group.commands.items():
        path = prefix + (name,)
        if isinstance(cmd, click.Group):
            yield from _walk_leaf_commands(cmd, path)
        else:
            yield path, cmd


def _param_declares_feature_flag(param: click.Parameter) -> bool:
    """Return True iff the param's CLI surface declares ``--feature``.

    We deliberately match on declared option strings (``param.opts`` and
    ``param.secondary_opts``) rather than ``param.name``. The Python-side
    parameter happens to be named ``feature`` on several mission commands
    that bind it exclusively to ``--mission`` — those are not what FR-006
    is policing.
    """
    declared = list(getattr(param, "opts", []) or []) + list(getattr(param, "secondary_opts", []) or [])
    return "--feature" in declared


def test_every_feature_flag_is_hidden() -> None:
    """Every ``--feature`` flag on every leaf command must carry hidden=True.

    Defensively reads ``hidden`` via ``getattr`` so a future Click/Typer
    upgrade that renames or restructures the attribute fails loudly here
    rather than silently letting an alias re-surface.
    """
    offenders: list[str] = []
    for path, cmd in _walk_leaf_commands(cli):
        for param in cmd.params:
            if _param_declares_feature_flag(param) and not getattr(param, "hidden", False):
                offenders.append(" ".join(path))
    assert not offenders, "FR-006 regression: --feature flag is visible on these commands (must be hidden=True):\n  " + "\n  ".join(offenders)


def test_help_output_never_mentions_feature_alias() -> None:
    """``--help`` text for every leaf command must not contain ``--feature``.

    This is the user-visible contract: regardless of Click's internal
    representation, the alias must never appear in rendered help.
    """
    runner = CliRunner()
    offenders: list[tuple[str, str]] = []
    for path, _cmd in _walk_leaf_commands(cli):
        result = runner.invoke(cli, list(path) + ["--help"], catch_exceptions=False)
        if FEATURE_TOKEN_RE.search(result.output):
            offenders.append((" ".join(path), result.output))
    assert not offenders, "FR-006 regression: '--feature' token appears in --help output of:\n  " + "\n  ".join(name for name, _ in offenders)
