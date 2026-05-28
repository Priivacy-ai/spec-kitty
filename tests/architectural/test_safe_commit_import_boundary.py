"""Architectural guardrail (T039): forbid direct ``safe_commit`` imports
from transactional workflow modules.

After WP06, modules that emit status transitions or commit workflow
artifacts must route through :class:`BookkeepingTransaction`.  A future
contributor could regress the #1348 fix by importing ``safe_commit``
directly from one of these modules; this AST-based test catches the
regression at CI time.

Spec source: FR-022, contracts/bookkeeping_transaction.md.

### Pragmatic exclusions

Two workflow modules — ``cli/commands/implement.py`` and
``cli/commands/agent/workflow.py``, ``cli/commands/agent/mission.py`` —
retain ``safe_commit`` imports for the **legacy mission fallback** path
that WP08 introduced.  The rule on those modules is therefore narrower:
we verify the *transaction* path is the default, but we do not forbid
the import outright.  The forbidden list below names the modules whose
direct import would be a clear regression today; WP08 fallbacks live
behind explicit ``_is_legacy_mission`` checks and are documented in the
WP08 commit message.

See ``contracts/bookkeeping_transaction.md`` (C-009) and
``architecture/3.x/adr/`` for the boundary rationale.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Forbidden direct importers — modules that MUST go through
# BookkeepingTransaction with no exceptions.
# ---------------------------------------------------------------------------
#
# ``status/emit.py`` is the prime example: it is the canonical pure-helper
# layer for building + appending events.  Any commit from this module
# would bypass the transaction's pre-flight policy gate and surgical
# truncate rollback — exactly the failure mode #1348 exposed.
FORBIDDEN_DIRECT_IMPORT_MODULES: tuple[str, ...] = (
    "src/specify_cli/status/emit.py",
)


# ---------------------------------------------------------------------------
# Modules that legitimately import ``safe_commit`` for the WP08 legacy
# fallback path. Listed here for documentation; not enforced.
# ---------------------------------------------------------------------------
#
# If WP08's legacy fallback ever moves entirely behind
# BookkeepingTransaction.acquire() (which already handles legacy missions
# via ``_resolve_legacy_lane_destination``), these can be added to
# FORBIDDEN_DIRECT_IMPORT_MODULES above.
DOCUMENTED_LEGACY_EXCEPTIONS: tuple[str, ...] = (
    "src/specify_cli/cli/commands/implement.py",
    "src/specify_cli/cli/commands/agent/workflow.py",
    "src/specify_cli/cli/commands/agent/mission.py",
)


def _module_imports_safe_commit(path: Path) -> bool:
    """Return True iff ``path`` contains a top-level
    ``from specify_cli.git[.commit_helpers] import safe_commit`` statement.

    Accepts both forms of the import path because the package re-exports
    ``safe_commit`` via ``specify_cli.git.__init__``.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        # Module forms to watch:
        #   from specify_cli.git import safe_commit
        #   from specify_cli.git.commit_helpers import safe_commit
        if node.module in {"specify_cli.git", "specify_cli.git.commit_helpers"}:
            for alias in node.names:
                if alias.name == "safe_commit":
                    return True
    return False


@pytest.mark.parametrize("forbidden", FORBIDDEN_DIRECT_IMPORT_MODULES)
def test_forbidden_modules_do_not_import_safe_commit_directly(forbidden: str) -> None:
    """Each listed module must NOT directly import ``safe_commit``.

    Workflow modules go through :class:`BookkeepingTransaction` which
    runs the pre-flight policy gate and surgical truncate rollback.
    Importing ``safe_commit`` directly bypasses both guarantees.
    """
    path = _REPO_ROOT / forbidden
    if not path.exists():
        pytest.skip(f"{forbidden} does not exist (file may have been renamed)")
    assert not _module_imports_safe_commit(path), (
        f"{forbidden} directly imports safe_commit. "
        f"Workflow modules MUST go through BookkeepingTransaction. "
        f"See contracts/bookkeeping_transaction.md."
    )


@pytest.mark.parametrize("legacy_path", DOCUMENTED_LEGACY_EXCEPTIONS)
def test_documented_legacy_modules_still_exist(legacy_path: str) -> None:
    """Sanity check: the documented legacy fallback modules still exist.

    If one of these modules disappears (e.g. gets refactored or absorbed
    into the transaction layer), this test fires so the maintainer can
    review whether the exclusion is still required.
    """
    path = _REPO_ROOT / legacy_path
    assert path.exists(), (
        f"{legacy_path} no longer exists. Review whether it can be added "
        f"to FORBIDDEN_DIRECT_IMPORT_MODULES."
    )
