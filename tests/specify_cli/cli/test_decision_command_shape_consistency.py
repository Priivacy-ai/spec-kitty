"""Regression tests for FR-007 (#774): the canonical shape of
``spec-kitty agent decision`` must stay consistent across the CLI surface,
its rendered help, and every documentation/skill/template reference.

The canonical shape is:

    spec-kitty agent decision { open | resolve | defer | cancel | verify }

Three invariants, all already correct on ``main`` (verified during
planning of mission ``release-3-2-0a5-tranche-1``, research note R6):

1. **CLI shape**: introspection of the agent app shows the ``decision``
   subgroup exposes exactly the five canonical *visible* subcommands.
2. **Help shape**: ``spec-kitty agent decision --help`` lists those five.
3. **Docs/skills/templates**: no surviving non-canonical phrasing exists
   anywhere under ``docs/``, ``.agents/skills/``, the rendered skill
   snapshots, or the mission templates.

The non-canonical regex is anchored on the ``spec-kitty`` prefix so that
prose like "decision documentation requirement" or "decisions about ..."
does not produce false positives.

Note on the ``widen`` subcommand: ``decision_app`` registers a sixth
subcommand named ``widen`` with ``hidden=True``. The contract specifies
the *visible* surface, so we filter to non-hidden subcommands when
asserting set equality.
"""

from __future__ import annotations

import re
from pathlib import Path

import click
from click.testing import CliRunner
from typer.main import get_command

from specify_cli import app as _typer_app


cli: click.Group = get_command(_typer_app)  # type: ignore[assignment]

# Repository root: this file lives at
#   <repo>/tests/specify_cli/cli/test_decision_command_shape_consistency.py
# so parents[3] points to <repo>.
REPO_ROOT = Path(__file__).resolve().parents[3]

EXPECTED_SUBCOMMANDS = {"open", "resolve", "defer", "cancel", "verify"}

# Non-canonical decision-command shapes that must NOT appear anywhere.
# Two alternations, both anchored on the ``spec-kitty`` prefix:
#   1. ``spec-kitty [agent] decisions ...`` (plural) or ``spec-kitty
#      [agent] decision-...`` (kebabed legacy form).
#   2. ``spec-kitty decision <verb>`` where <verb> is anything other than
#      the five canonical subcommands — i.e. a missing ``agent`` segment.
NON_CANONICAL_RE = re.compile(
    r"spec-kitty\s+(?:agent\s+)?(?:decisions\b|decision-)"
    r"|"
    r"spec-kitty\s+decision\b(?!\s+(?:open|resolve|defer|cancel|verify))",
)

SCAN_ROOTS = (
    "docs",
    ".agents/skills",
    "tests/specify_cli/skills/__snapshots__",
    "src/specify_cli/missions",
)


def _visible_subcommand_names(group: click.Group) -> set[str]:
    """Return the names of subcommands that are NOT hidden."""
    return {name for name, cmd in group.commands.items() if not getattr(cmd, "hidden", False)}


def test_agent_decision_subgroup_has_canonical_visible_subcommands() -> None:
    agent_grp = cli.commands.get("agent")
    assert isinstance(agent_grp, click.Group), "spec-kitty agent group missing from CLI"
    decision_grp = agent_grp.commands.get("decision")
    assert isinstance(decision_grp, click.Group), "spec-kitty agent decision subgroup missing from CLI"
    visible = _visible_subcommand_names(decision_grp)
    assert visible == EXPECTED_SUBCOMMANDS, (
        f"FR-007 regression: visible decision subcommands drifted.\n  expected: {sorted(EXPECTED_SUBCOMMANDS)}\n  actual:   {sorted(visible)}"
    )


def test_help_output_lists_canonical_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["agent", "decision", "--help"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    for sub in EXPECTED_SUBCOMMANDS:
        assert sub in result.output, f"FR-007 regression: subcommand {sub!r} missing from `agent decision --help`:\n{result.output}"


def test_no_non_canonical_decision_command_shape_in_repo_text() -> None:
    offenders: list[tuple[str, str]] = []
    for rel in SCAN_ROOTS:
        root = REPO_ROOT / rel
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for match in NON_CANONICAL_RE.finditer(text):
                offenders.append((str(path.relative_to(REPO_ROOT)), match.group(0)))
    assert not offenders, "FR-007 regression: non-canonical decision command shape found:\n  " + "\n  ".join(f"{p}: {m!r}" for p, m in offenders)
