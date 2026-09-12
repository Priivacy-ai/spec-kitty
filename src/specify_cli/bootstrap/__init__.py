"""Pre-import bootstrap seams for ``specify_cli``.

Everything under this package runs (or is safe to run) BEFORE the rest of
``specify_cli`` is imported -- see :mod:`specify_cli.bootstrap.env_file` for
the ``.kitty.env`` two-tier loader (FR-004/FR-004a/FR-005;
``contracts/kitty-env-loader.md`` C-LDR-1..7) and its import-purity
constraint (stdlib + :mod:`kernel` only).
"""

from __future__ import annotations

from specify_cli.bootstrap.env_file import load_operator_env_file

__all__ = ["load_operator_env_file"]
