"""FR-035 integration: ``--feature`` is a hidden deprecated alias.

Authority: ``kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/spec.md``
section FR-035 and ``research.md`` D16.

The legacy ``--feature`` flag must remain accepted as an alias for
``--mission`` but must NOT appear in any command's ``--help`` output.
The companion contract test
``tests/contract/test_terminology_guards.py::test_no_visible_feature_alias_in_cli_commands``
enforces the static-analysis side; this integration suite pins the
runtime side and documents the canonical alias-helper API.
"""

from __future__ import annotations

import re
from pathlib import Path


from specify_cli.missions._legacy_aliases import (
    LEGACY_FEATURE_HELP,
    hidden_feature_option,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src" / "specify_cli" / "cli" / "commands"


def test_hidden_feature_option_returns_typer_option() -> None:
    """The helper produces a Typer option with the canonical alias shape."""
    option = hidden_feature_option()
    # Typer stores option spec on OptionInfo; check its declared flag and
    # hidden-ness via the public attributes we control.
    assert option.hidden is True
    assert "--feature" in option.param_decls
    assert option.help == LEGACY_FEATURE_HELP


def test_hidden_feature_option_help_text_overrides() -> None:
    custom = "(deprecated) Use --mission for charter scope"
    option = hidden_feature_option(help_text=custom)
    assert option.help == custom
    assert option.hidden is True


def _scan_typer_option_blocks(text: str):
    pattern = re.compile(r"typer\.Option\((?:[^()]|\([^()]*\))*\)", re.DOTALL)
    for match in pattern.finditer(text):
        yield match.group(0)


def test_no_unhidden_feature_typer_options_in_commands_tree() -> None:
    """Walk every command file and verify --feature is always hidden=True.

    This is the runtime mirror of the static contract test. We lift the
    static check into the integration suite so a missing ``hidden=True``
    on a brand new command still trips an integration failure even if a
    contributor disabled the contract test selector.
    """
    offenders: list[str] = []
    for path in sorted(COMMANDS_DIR.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for block in _scan_typer_option_blocks(text):
            if '"--feature"' not in block:
                continue
            if "hidden=True" in block:
                continue
            offenders.append(f"{path.relative_to(REPO_ROOT)}: {block[:120]}")

    assert offenders == [], "These typer.Option blocks declare --feature without hidden=True:\n" + "\n".join(offenders)


def test_charter_lint_help_does_not_mention_feature_flag() -> None:
    """The historically-offending command surface must not advertise --feature.

    ``charter.py:charter_lint`` was the load-bearing offender (issue
    flagged by WP04/05/06 reviewers). We snapshot the source line that
    declares the option and assert it carries ``hidden=True`` so a
    future regression is caught at the command-source layer too.
    """
    charter_py = COMMANDS_DIR / "charter.py"
    text = charter_py.read_text(encoding="utf-8")
    feature_blocks = [block for block in _scan_typer_option_blocks(text) if '"--feature"' in block]
    assert feature_blocks, "Expected at least one --feature option block in charter.py"
    for block in feature_blocks:
        assert "hidden=True" in block, f"charter.py declares a --feature typer.Option without hidden=True:\n{block}"


def test_charter_lint_offers_canonical_mission_option() -> None:
    """``charter lint`` must surface the canonical ``--mission`` selector."""
    charter_py = COMMANDS_DIR / "charter.py"
    text = charter_py.read_text(encoding="utf-8")
    # We do not require a specific format, only that `--mission` is
    # declared somewhere within charter_lint's option declarations.
    assert '"--mission"' in text, "charter.py is expected to expose --mission as the canonical alternative to the hidden --feature alias."
