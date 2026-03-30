"""Schema version gate for the Spec Kitty CLI.

``check_schema_version`` is called as a typer callback before every command
dispatch.  It refuses operation when the project schema is incompatible with
this CLI build (too old → upgrade project; too new → upgrade CLI).

Exempted commands that always pass through:
  - ``upgrade``  (fixes the problem)
  - ``init``     (creates the project, no existing metadata yet)
  - ``--version`` / ``--help``  (handled by typer's eager options before our callback)
"""

from __future__ import annotations

from pathlib import Path

import typer

from .schema_version import (
    REQUIRED_SCHEMA_VERSION,
    check_compatibility,
    get_project_schema_version,
)

# Commands that are allowed to run even when the schema version is incompatible.
_EXEMPT_COMMANDS: frozenset[str] = frozenset({"upgrade", "init"})


def check_schema_version(
    repo_root: Path,
    invoked_subcommand: str | None = None,
) -> None:
    """Verify the project schema version before executing any CLI command.

    Behaviour:
    - If ``.kittify/`` does not exist: skip (uninitialized project, let ``init``
      handle it).
    - If the invoked subcommand is in ``_EXEMPT_COMMANDS``: skip.
    - Otherwise: read schema version, call ``check_compatibility``, and raise
      ``SystemExit(1)`` with an actionable message when incompatible.

    Args:
        repo_root: Root of the project (parent of ``.kittify/``).
        invoked_subcommand: The subcommand name typer will dispatch to, or
            ``None`` when running without a subcommand (shows help).

    Raises:
        SystemExit: With exit code 1 when the schema version is incompatible.
    """
    # Uninitialized project — no .kittify/ yet.  Let `init` run freely.
    kittify_dir = repo_root / ".kittify"
    if not kittify_dir.exists():
        return

    # Exempt upgrade / init so users can always fix or bootstrap the project.
    if invoked_subcommand in _EXEMPT_COMMANDS:
        return

    # Gate disabled when REQUIRED_SCHEMA_VERSION is None (pre-release development).
    if REQUIRED_SCHEMA_VERSION is None:
        return

    project_version = get_project_schema_version(repo_root)
    result = check_compatibility(project_version, REQUIRED_SCHEMA_VERSION)

    if not result.is_compatible:
        # Use typer.echo so output respects --no-color and goes to stderr-friendly
        # channel; then raise SystemExit directly (no typer.Abort) for clarity.
        typer.echo(f"Error: {result.message}", err=True)
        raise SystemExit(result.exit_code)
