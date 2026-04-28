"""Module execution compatibility for ``python -m specify_cli.acceptance``."""

from __future__ import annotations


def main() -> None:
    """Preserve the legacy module's import-only execution behavior."""


if __name__ == "__main__":
    main()
