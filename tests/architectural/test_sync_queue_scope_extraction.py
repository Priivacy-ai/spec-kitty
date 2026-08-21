"""Residual-coupling regression guard for the sync.queue transport/scope split.

R3-T1 (m1-contract-drafts/R3.md §2.1a) found that ``sync/target_authority.py``
imports five scope-resolution names from ``sync/queue.py`` at **module level,
unconditionally** — not lazily, not behind ``is_saas_sync_enabled()``.
``target_authority.py`` is itself imported at module level, with no
rollout-flag gate, by ``cli/commands/_auth_login.py`` — the implementation
module ``cli/commands/auth.py``'s ``login`` command lazily imports the instant
the ``login`` command body runs. R2's own criterion ("sender/receiver/history/
body/external paths are physically absent") would delete ``sync/queue.py``
wholesale, which would make ``import specify_cli.sync.target_authority`` raise
``ModuleNotFoundError: No module named 'specify_cli.sync.queue'`` — crashing
every invocation of ``spec-kitty auth login`` for every user.

R3-T1's fix: the scope-resolution primitives live in the new, retained,
transport-independent module ``specify_cli.sync.queue_scope``; the transport
half (``OfflineQueue`` and friends, ``get_max_queue_size``) stays in
``specify_cli.sync.queue`` for R2 to eventually delete. This test is the
regression guard: it fails if any retained caller regresses to importing a
scope-resolution symbol directly from the transport module instead of from
``queue_scope``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "specify_cli"

# The scope-resolution half of sync/queue.py (R3.md §2.1a table) — these names
# must be resolvable from specify_cli.sync.queue_scope, and retained callers
# must import them from there, never from the transport module directly.
_SCOPE_SYMBOLS = frozenset(
    {
        "build_queue_scope",
        "scope_db_path",
        "read_active_scope",
        "write_active_scope",
        "read_queue_scope_from_credentials",
        "read_queue_scope_from_session",
        "default_queue_db_path",
        "_legacy_queue_db_path",
        "detect_legacy_rows_for_scope",
        "LegacyRowCounts",
        "LegacyQueueMigrationRequiredError",
    }
)

# The retained-command chain R3-T1's HANDBACK found: target_authority (module
# level, unconditional) -> _auth_login (module level, unconditional) reached
# from every `spec-kitty auth login` invocation; preflight and
# mission_setup_plan reach the same chain via a gated, deferred import.
_GUARDED_FILES = (
    _SRC / "sync" / "target_authority.py",
    _SRC / "sync" / "preflight.py",
    _SRC / "cli" / "commands" / "agent" / "mission_setup_plan.py",
    _SRC / "cli" / "commands" / "_auth_login.py",
)


def _scope_symbol_imports_from_transport_queue(path: Path) -> list[str]:
    """Return ``"path:lineno:name"`` for every scope symbol imported from the
    transport module ``specify_cli.sync.queue`` anywhere in ``path`` — walking
    the whole AST catches both module-level and function-deferred imports.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "specify_cli.sync.queue":
            for alias in node.names:
                if alias.name in _SCOPE_SYMBOLS:
                    offenders.append(f"{path}:{node.lineno}:{alias.name}")
    return offenders


def test_guarded_files_exist() -> None:
    """Sanity: the census above still names real files (catches a repo-layout drift)."""
    missing = [str(path) for path in _GUARDED_FILES if not path.exists()]
    assert missing == [], f"guarded file(s) no longer exist, update the census: {missing}"


def test_no_guarded_module_imports_scope_symbol_from_transport_queue() -> None:
    offenders = [
        offender for path in _GUARDED_FILES for offender in _scope_symbol_imports_from_transport_queue(path)
    ]
    assert offenders == [], (
        "Import scope-resolution symbols from specify_cli.sync.queue_scope, "
        "never from specify_cli.sync.queue (R3-T1 §2.1a residual-coupling "
        f"fix — a future sync.queue deletion must not crash `auth login`): {offenders}"
    )


def test_target_authority_imports_scope_helpers_from_queue_scope_module() -> None:
    text = (_SRC / "sync" / "target_authority.py").read_text(encoding="utf-8")
    assert "from specify_cli.sync.queue_scope import" in text, (
        "target_authority.py must resolve its scope helpers from the retained "
        "specify_cli.sync.queue_scope module, not the transport-only sync.queue"
    )


def test_auth_login_chain_never_names_transport_queue_module() -> None:
    """`spec-kitty auth login`'s import chain must never even name the
    transport module ``specify_cli.sync.queue`` (the R5' regression this
    census closes) — target_authority is its sole sync dependency.
    """
    text = (_SRC / "cli" / "commands" / "_auth_login.py").read_text(encoding="utf-8")
    assert "specify_cli.sync.queue" not in text.replace("specify_cli.sync.queue_scope", "")
