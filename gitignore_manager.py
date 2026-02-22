"""Compatibility shim for legacy imports in tests/scripts.

This module re-exports `specify_cli.gitignore_manager` at repository root so
legacy `import gitignore_manager` statements remain importable.
"""

from specify_cli.gitignore_manager import *  # noqa: F401,F403

