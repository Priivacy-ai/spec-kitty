"""Backward-compatibility shim for the ``mission`` CLI subcommand.

The canonical implementation is in ``mission_type.py``. This module
re-exports ``app`` so that the CLI router's ``add_typer(mission_module.app,
name="mission")`` registration continues to work.
"""

from .mission_type import app

__all__ = ["app"]
