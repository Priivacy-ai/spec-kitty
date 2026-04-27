"""Fixture: intentionally bad adapter that contains logic — used by test_compat_shims.py."""

# adapter:no-logic

from specify_cli.core.version_checker import get_cli_version

__all__ = ["get_cli_version"]


def _sneaky_helper() -> str:
    return "oops"
