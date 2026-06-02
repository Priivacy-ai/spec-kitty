"""Runtime → Charter → Doctrine boundary ratchet.

The user's stated layering target is::

    runtime  →  charter  →  doctrine

The runtime layer (``src/specify_cli/``) MUST reach doctrine artifacts
only through the charter proxy. Direct ``from doctrine.*`` /
``import doctrine`` statements are reserved for:

1. The charter layer itself (``src/charter/``) — the legitimate proxy.
2. The ``src/specify_cli/doctrine/`` subpackage — the *pack-management*
   surface explicitly designed as the doctrine-management surface
   (it owns the org-pack registry, snapshot, validator, and the org
   charter loader; its very purpose is to manipulate doctrine packs).
3. An explicit baseline allowlist captured from the snapshot
   ``docs/development/runtime-charter-doctrine-boundary.md`` at
   commit ``1099feae`` (the boundary audit). Each allowlisted file is
   a known violation that Mission B's WP02 + WP03 will migrate away
   from one PR at a time; the allowlist must shrink, never grow.

This is the **ratchet test** for the boundary. It must be GREEN today
(the baseline matches the current 13 known violators). It will FAIL
loudly when:

- a new runtime file (outside the allowlist and outside
  ``src/specify_cli/doctrine/``) introduces a direct ``from doctrine.*``
  import — the failure message names the offender and points at
  ``docs/development/runtime-charter-doctrine-boundary.md`` for the
  migration recipe;
- an allowlisted file has had its direct import removed (a migration
  landed) but the allowlist entry was not removed — the test fails so
  the maintainer remembers to shrink the allowlist.

See also: ``docs/development/mission-b-proposed-scope.md`` WP01.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = [pytest.mark.architectural]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_ROOT = _REPO_ROOT / "src" / "specify_cli"
_EXEMPT_SUBPACKAGE = _RUNTIME_ROOT / "doctrine"


# Baseline allowlist captured from the boundary audit (snapshot 2026-05-17).
#
# WP07 migration status (mission charter-mediated-doctrine-selection-01KRTZCA):
# All 13 baseline-allowlist files have been migrated from direct
# `from doctrine.*` imports to `from charter.<facade>` imports. The
# `bulk_edit/occurrence_map.py` SchemaUtilities consumer was migrated to
# `from kernel.schema_utils import SchemaUtilities` per the kernel
# promotion path documented in contracts/charter-facade-modules.md.
#
# The allowlist is now EMPTY — every direct doctrine import in
# `src/specify_cli/` (outside the `doctrine/` pack-management subpackage)
# is a violation. Per C-004 the allowlist may grow to at most 2
# documented exceptions if a future migration is genuinely lossy; each
# such addition MUST include a one-line rationale immediately above the
# entry, and must be paired with a tracker ticket for follow-up removal.
_BASELINE_ALLOWLIST: frozenset[str] = frozenset()


def _is_exempt_subpackage(path: Path) -> bool:
    """True when ``path`` lives inside ``src/specify_cli/doctrine/``.

    The pack-management subpackage is the doctrine-management surface
    by design (org-pack registry, snapshot, validator). The boundary
    rule does not apply to it.
    """
    try:
        path.relative_to(_EXEMPT_SUBPACKAGE)
    except ValueError:
        return False
    return True


def _module_imports_doctrine_directly(tree: ast.Module) -> bool:
    """Return True iff ``tree`` has a *module-level* ``from doctrine.*`` / ``import doctrine``.

    We match both forms at module top level (matching the audit's
    ``rg "^from doctrine|^import doctrine"`` definition that produced
    the 13-file baseline):

        from doctrine.X import Y          # ImportFrom whose module starts with "doctrine"
        from doctrine import Z            # ImportFrom whose module == "doctrine"
        import doctrine                   # Import naming "doctrine" / "doctrine.X"
        import doctrine.X                 # Import naming "doctrine.X"

    Lazy / nested imports inside functions are intentionally NOT
    counted here — they live in a separate (and equally undesirable)
    pattern that a follow-up ratchet should address. Including them
    in this ratchet would mix two failure modes and obscure the
    headline boundary count.
    """
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "doctrine" or module.startswith("doctrine."):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "doctrine" or alias.name.startswith("doctrine."):
                    return True
    return False


def _iter_runtime_python_files() -> list[Path]:
    """Yield every ``*.py`` file under ``src/specify_cli/``."""
    return sorted(_RUNTIME_ROOT.rglob("*.py"))


def _rel_to_repo(path: Path) -> str:
    return str(path.relative_to(_REPO_ROOT))


def _format_boundary_failure(
    *,
    new_violators: list[str],
    stale_allowlist_entries: list[str],
) -> str:
    parts: list[str] = []
    if new_violators:
        bullets = "\n  - ".join(sorted(new_violators))
        parts.append(
            "Runtime → Charter → Doctrine boundary violation. The following\n"
            "files under src/specify_cli/ introduce a direct\n"
            "`from doctrine.*` / `import doctrine` import outside the\n"
            "allowlist and outside the src/specify_cli/doctrine/ pack-management\n"
            "subpackage:\n"
            f"  - {bullets}\n"
            "\n"
            "Fix: route the access through the charter proxy. The intended\n"
            "facade modules are:\n"
            "  - charter.profiles       (agent profiles, role capabilities)\n"
            "  - charter.mission_steps  (mission step contract repository)\n"
            "  - charter.drg            (DRG models, loader, merge, queries)\n"
            "  - charter.primitives     (mission primitive execution)\n"
            "  - charter.resolution     (ResolutionResult / ResolutionTier)\n"
            "  - charter.versioning    (bundle versioning helpers)\n"
            "See docs/development/runtime-charter-doctrine-boundary.md for the\n"
            "Phase-2 facade plan and the Phase-3 migration recipe."
        )
    if stale_allowlist_entries:
        bullets = "\n  - ".join(sorted(stale_allowlist_entries))
        parts.append(
            "Stale boundary allowlist entries. The following files are listed\n"
            "in `_BASELINE_ALLOWLIST` but no longer perform a direct\n"
            "`from doctrine.*` / `import doctrine` import (a migration likely\n"
            "landed without shrinking the allowlist):\n"
            f"  - {bullets}\n"
            "\n"
            "Fix: remove those entries from `_BASELINE_ALLOWLIST` in this file\n"
            "so the ratchet correctly captures the smaller surface."
        )
    return "\n\n".join(parts)


def test_runtime_has_no_new_direct_doctrine_imports() -> None:
    """Pin the runtime → charter → doctrine boundary as a one-way ratchet.

    Must be GREEN today against the 13-file baseline captured in the
    boundary audit. Any new direct ``from doctrine.*`` import in a
    non-allowlisted runtime file MUST trip this test; the failure
    message names the offender and points at the migration recipe.
    Removing an allowlist entry without removing the matching import is
    also a violation, so the ratchet stays honest in both directions.
    """
    actual_violators: set[str] = set()
    for path in _iter_runtime_python_files():
        if _is_exempt_subpackage(path):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        if _module_imports_doctrine_directly(tree):
            actual_violators.add(_rel_to_repo(path))

    new_violators = sorted(actual_violators - _BASELINE_ALLOWLIST)
    stale_allowlist_entries = sorted(_BASELINE_ALLOWLIST - actual_violators)

    assert not new_violators and not stale_allowlist_entries, (
        _format_boundary_failure(
            new_violators=new_violators,
            stale_allowlist_entries=stale_allowlist_entries,
        )
    )
