"""CLI command group: ``spec-kitty plugin``.

Provides build and validation commands for Spec Kitty plugin bundles.

Currently supported subcommands:
    build   — Build a plugin bundle for a specific target harness.
              ``spec-kitty plugin build --target claude-code``
"""

from __future__ import annotations

from pathlib import Path

import typer

from specify_cli.cli.commands import HelpOnEmptyTopLevelGroup

plugin_app = typer.Typer(
    name="plugin",
    help="Plugin bundle commands.",
    cls=HelpOnEmptyTopLevelGroup,
    no_args_is_help=True,
)

# Stable label for the supported build target.
_TARGET_CLAUDE_CODE = "claude-code"
_TARGET_CODEX = "codex"


@plugin_app.command("build")
def plugin_build(
    target: str = typer.Option(
        ...,
        "--target",
        help=f"Plugin target ({_TARGET_CLAUDE_CODE}, {_TARGET_CODEX}).",
    ),
    output_dir: Path = typer.Option(
        Path("dist/spec-kitty-plugins"),
        "--output-dir",
        help="Root directory under which the bundle is written.",
    ),
    skip_validate: bool = typer.Option(
        False,
        "--skip-validate",
        help="Skip the 'claude plugin validate --strict' step.",
    ),
) -> None:
    """Build a Spec Kitty plugin bundle for a specific target harness.

    The bundle is written to ``<output-dir>/<target>/`` and includes a
    ``plugin.json`` manifest, rendered command skills, and agent profiles.

    Example::

        spec-kitty plugin build --target claude-code
        spec-kitty plugin build --target claude-code --output-dir /tmp/out
        spec-kitty plugin build --target claude-code --skip-validate
    """
    if target == _TARGET_CLAUDE_CODE:
        from specify_cli.tool_surface.bundles.claude import ClaudeBundleProjector

        bundle_dir = ClaudeBundleProjector(output_dir).build(
            skip_validate=skip_validate
        )
        typer.echo(f"Bundle written to {bundle_dir}")
    elif target == _TARGET_CODEX:
        from specify_cli.tool_surface.bundles.codex import CodexBundleProjector

        bundle_dir = CodexBundleProjector(output_dir).build(
            skip_validate=skip_validate
        )
        typer.echo(f"Bundle written to {bundle_dir}")
    else:
        raise typer.BadParameter(
            f"Unknown target: {target!r}. Supported: {_TARGET_CLAUDE_CODE}, {_TARGET_CODEX}."
        )
