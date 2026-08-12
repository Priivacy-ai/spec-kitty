"""AST fixtures for the lazy-import ratchet (mission doctrine-public-api-surface, WP04).

These modules are **never imported or executed** — the ratchet parses them with
``ast.parse`` to prove the parent-tracking descent distinguishes a
``TYPE_CHECKING`` doctrine import (must NOT be flagged) from a nested-function
doctrine import (must be flagged). They deliberately live outside
``src/specify_cli/`` so the live-tree census never counts them.
"""
