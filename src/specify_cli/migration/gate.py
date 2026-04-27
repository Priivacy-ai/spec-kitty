"""Schema version gate for the Spec Kitty CLI.

``check_schema_version`` is called as a typer callback before every command
dispatch.  It delegates to ``compat.planner.plan()`` which decides whether the
project is compatible with this CLI build.

Exempted commands that always pass through:
  - ``upgrade``  (fixes the problem)
  - ``init``     (creates the project, no existing metadata yet)
  - ``--version`` / ``--help``  (handled by typer's eager options before our callback)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

# Commands that are allowed to run even when the schema version is incompatible.
# Kept for backward compatibility (some tests may import _EXEMPT_COMMANDS).
# The compat.safety registry is the authoritative source for exemption logic.
_EXEMPT_COMMANDS: frozenset[str] = frozenset({"upgrade", "init"})


def check_schema_version(
    repo_root: Path,
    invoked_subcommand: str | None = None,
) -> None:
    """Verify the project schema version before executing any CLI command.

    Behaviour:
    - If ``.kittify/`` does not exist: skip (uninitialized project, let ``init``
      handle it).
    - If the invoked subcommand is in ``_EXEMPT_COMMANDS``: skip (defense-in-depth;
      these are also SAFE in the compat.safety registry).
    - Otherwise: build an Invocation and delegate to ``compat.planner.plan()``.
      Block if the decision is BLOCK_PROJECT_MIGRATION, BLOCK_CLI_UPGRADE, or
      BLOCK_PROJECT_CORRUPT.

    Args:
        repo_root: Root of the project (parent of ``.kittify/``).
        invoked_subcommand: The subcommand name typer will dispatch to, or
            ``None`` when running without a subcommand (shows help).

    Raises:
        SystemExit: When the planner returns a blocking decision.
    """
    # Uninitialized project — no .kittify/ yet.  Let `init` run freely.
    kittify_dir = repo_root / ".kittify"
    if not kittify_dir.exists():
        return

    # Exempt upgrade / init so users can always fix or bootstrap the project.
    # Defense-in-depth: the compat.safety registry also marks these as SAFE.
    if invoked_subcommand in _EXEMPT_COMMANDS:
        return

    # Deferred import to avoid circular imports at module load time.
    # compat.planner imports from migration.schema_version (not from gate),
    # so the cycle only occurs if we import at the top level.
    from specify_cli.compat import Decision  # noqa: PLC0415
    from specify_cli.compat import Invocation  # noqa: PLC0415
    from specify_cli.compat import plan as compat_plan  # noqa: PLC0415

    inv = Invocation(
        command_path=(invoked_subcommand,) if invoked_subcommand else (),
        raw_args=tuple(sys.argv[1:]),
        is_help=False,
        is_version=False,
        flag_no_nag="--no-nag" in sys.argv,
        env_ci=bool(os.environ.get("CI")),
        stdout_is_tty=sys.stdout.isatty(),
    )

    # Provide the known repo_root directly so the planner does not walk from cwd.
    _root = repo_root

    def _resolver(_cwd: Path) -> Path | None:
        return _root

    result = compat_plan(inv, project_root_resolver=_resolver)

    if result.decision in {
        Decision.BLOCK_PROJECT_MIGRATION,
        Decision.BLOCK_CLI_UPGRADE,
        Decision.BLOCK_PROJECT_CORRUPT,
    }:
        typer.echo(result.rendered_human, err=True)
        raise SystemExit(int(result.exit_code))
