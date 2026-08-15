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

from tests.architectural.test_doctrine_census import EXEMPT_MANAGEMENT_SURFACE


pytestmark = [pytest.mark.architectural]


_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME_ROOT = _REPO_ROOT / "src" / "specify_cli"
_EXEMPT_SUBPACKAGE = _RUNTIME_ROOT / "doctrine"

# The absolute-``doctrine`` matcher literals, hoisted per Sonar S1192 (they recur
# across the module-level ratchet, the lazy ratchet, and the laundering scan).
_DOCTRINE_ROOT_MODULE = "doctrine"
_DOCTRINE_SUBMODULE_PREFIX = "doctrine."


def _is_doctrine_module(name: str) -> bool:
    """True for an absolute ``doctrine`` / ``doctrine.<sub>`` dotted module name."""
    return name == _DOCTRINE_ROOT_MODULE or name.startswith(_DOCTRINE_SUBMODULE_PREFIX)


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
            if _is_doctrine_module(node.module or ""):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _is_doctrine_module(alias.name):
                    return True
    return False


def _iter_runtime_python_files() -> list[Path]:
    """Yield every ``*.py`` file under ``src/specify_cli/``."""
    return sorted(_RUNTIME_ROOT.rglob("*.py"))


def _rel_to_repo(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def test_actual_repo_relative_key_matches_static_posix_oracle() -> None:
    """Windows ``Path`` output must match the independent POSIX inventory form."""
    actual = _rel_to_repo(_REPO_ROOT / "src" / "specify_cli" / "doctrine" / "config.py")
    expected = "src/specify_cli/doctrine/config.py"
    assert actual == expected, f"actual={actual!r}, expected={expected!r}"


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


# ===========================================================================
# WP04 — Sibling lazy-import ratchet + source-side laundering guard
# ===========================================================================
#
# The module-level ratchet above walks only ``tree.body`` and so is blind to the
# *lazy* reach-through: a direct ``from doctrine…`` import nested inside a
# function/class body. Confirmed on-branch: 0 module-level vs 29 lazy files. This
# section adds the sibling ratchet (FR-006 / SC-003) plus the SOURCE-side
# re-export-laundering guard (C-005 / FR-004). The two ratchets stay separate:
# the module-level baseline above remains EMPTY; lazy files are pinned here.
#
# Mechanism (T017): a **parent-tracking recursive descent** — NOT bare
# ``ast.walk``, which flattens the tree and loses the enclosing-block context
# needed to (a) skip ``if TYPE_CHECKING:`` imports (erased at runtime; not a real
# reach-through) and (b) tell a module-level import (owned by the ratchet above)
# from a lazy nested one. The visitor tracks ``(nesting_depth, TYPE_CHECKING
# depth)`` and flags only depth>0, non-TYPE_CHECKING doctrine imports.
#
# Known limits (T020):
#   * Bare ``import doctrine`` (path/metadata introspection, e.g.
#     tool_surface/bundles/codex.py reading ``doctrine.__file__``) IS matched by
#     the descent — it is a level-0 absolute ``doctrine`` name — so a file that
#     only does metadata introspection still appears in the lazy baseline. It is
#     classified INTERNAL-METADATA in WP01's census (FR-006 exempt at the
#     disposition layer), but the ratchet's job is only "does not regrow", so it
#     is pinned like any other baseline entry and migrates out with its file.
#   * Aliased imports (``import doctrine.x as dx`` / ``from doctrine.x import y as
#     z``) are matched on the *source* module path, not the local alias, so an
#     alias cannot hide a reach-through.
#   * Dynamic imports (``importlib.import_module("doctrine.x")``) are invisible to
#     a static AST scan. Zero exist today; the "cannot silently regrow" guarantee
#     is therefore bounded to *static* imports (C3 "Known limit").


_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "doctrine_boundary"


#: Lazy-import baseline seeded from WP01's live-tree census (the 29 true
#: function-body doctrine importers on-branch, 2026-08-10). This is an
#: ONLY-SHRINK frozenset: a new lazy importer (not listed) fails
#: ``test_runtime_has_no_new_lazy_doctrine_imports`` in the "grow" direction; a
#: migrated file still listed fails it in the "stale" direction. WP05–WP07 shrink
#: it as they route each call site through the charter facades.
_LAZY_BASELINE_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Post-merge reconciliation (01KZPDSR): every WP05/06/07-migrated file has
        # been evicted. The remaining entries still perform a *sanctioned* direct
        # doctrine import that this mission deliberately did not route through a
        # charter facade:
        #   - ``_doctrine_asset.py`` / ``_doctrine_collect.py`` / ``doctrine.py``:
        #     the sole-door ``doctrine.service`` construction sites (already wrapped
        #     + test-locked) and the TICKETED-BASELINE paths ``drg.override_policy``
        #     / ``drg.migration.hand_authored_overlay`` (doorless management internals).
        #   - ``bundles/codex.py``: bare ``import doctrine`` for package-metadata
        #     introspection (``doctrine.__file__``), not a symbol reach-through.
        "src/specify_cli/cli/commands/_doctrine_asset.py",
        "src/specify_cli/cli/commands/_doctrine_collect.py",
        "src/specify_cli/cli/commands/doctrine.py",
        "src/specify_cli/tool_surface/bundles/codex.py",
    }
)


#: SOURCE-side laundering baseline. Each entry is a ``src/specify_cli/doctrine/*``
#: module that re-exports doctrine-origin symbols through its own ``__all__`` — a
#: first-party re-export "laundering" conduit. ``config.py`` re-exports the
#: shared org-pack-config contract; WP05 closes the conduit, which forces the
#: stale-entry eviction below. A consumer-side check is impossible: ``from
#: specify_cli.doctrine.config import load_pack_registry`` (laundered) and ``…
#: import assert_pack_local_paths_exist`` (genuine first-party) are byte-identical
#: import syntax, so the rule must be enforced at the SOURCE module's ``__all__``.
# WP05 (01KZPDSR / C-005, FR-004) CLOSED the ``config.py`` conduit: the
# doctrine-origin org-pack-config symbols are no longer listed in
# ``config.__all__``, so the module launders nothing and the baseline is empty.
# The module-level bindings survive for in-surface + management-surface-test
# consumers, but ``__all__`` is the enforced surface (a consumer-side check is
# impossible — see the note above), so an empty baseline is the closed state.
_LAUNDERING_BASELINE: dict[str, frozenset[str]] = {}


def _doctrine_import_path(node: ast.AST) -> str | None:
    """Absolute ``doctrine[.…]`` module-path for a level-0 import node, else None.

    Matches the same forms as the census: ``from doctrine.X import Y`` /
    ``from doctrine import Z`` (``ImportFrom`` with ``level == 0``) and
    ``import doctrine`` / ``import doctrine.X`` (``Import``). Relative imports
    (``level > 0``) never name the top-level ``doctrine`` package and are skipped.
    """
    if isinstance(node, ast.ImportFrom):
        if node.level != 0:
            return None
        module = node.module or ""
        return module if _is_doctrine_module(module) else None
    if isinstance(node, ast.Import):
        for alias in node.names:
            if _is_doctrine_module(alias.name):
                return alias.name
    return None


def _is_type_checking_guard(test: ast.expr) -> bool:
    """True for ``if TYPE_CHECKING:`` / ``if typing.TYPE_CHECKING:`` guards."""
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


class _LazyDoctrineVisitor(ast.NodeVisitor):
    """Parent-tracking descent flagging nested (lazy) non-TYPE_CHECKING imports.

    Tracks ``(nesting_depth, type_checking_depth)`` so it can:

    * skip any doctrine import that lives under an ``if TYPE_CHECKING:`` guard
      (it is erased at runtime — not a real reach-through), and
    * distinguish a *module-level* import (``nesting_depth == 0`` — owned by the
      module-level ratchet, whose baseline stays empty) from a *lazy* import
      nested inside a function/class body (``nesting_depth > 0``).

    Only a level-0 absolute ``doctrine`` import at ``nesting_depth > 0`` outside a
    ``TYPE_CHECKING`` block sets :attr:`has_lazy_import`.
    """

    def __init__(self) -> None:
        self.has_lazy_import = False
        self._nesting_depth = 0
        self._type_checking_depth = 0

    def _record(self, node: ast.AST) -> None:
        if self._type_checking_depth or self._nesting_depth == 0:
            return
        if _doctrine_import_path(node) is not None:
            self.has_lazy_import = True

    def visit_Import(self, node: ast.Import) -> None:
        self._record(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self._record(node)

    def visit_If(self, node: ast.If) -> None:
        guarded = _is_type_checking_guard(node.test)
        if guarded:
            self._type_checking_depth += 1
        for child in node.body:
            self.visit(child)
        if guarded:
            self._type_checking_depth -= 1
        for child in node.orelse:
            self.visit(child)

    def _visit_scope(self, node: ast.AST) -> None:
        self._nesting_depth += 1
        self.generic_visit(node)
        self._nesting_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_scope(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scope(node)


def _file_has_lazy_doctrine_import(path: Path) -> bool:
    """True iff ``path`` performs a lazy (nested, non-TYPE_CHECKING) doctrine import."""
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return False
    visitor = _LazyDoctrineVisitor()
    visitor.visit(tree)
    return visitor.has_lazy_import


def _lazy_doctrine_violators() -> set[str]:
    """Runtime files (outside the exempt management surface) with a lazy import."""
    violators: set[str] = set()
    for path in _iter_runtime_python_files():
        if _is_exempt_subpackage(path):
            continue
        if _file_has_lazy_doctrine_import(path):
            violators.add(_rel_to_repo(path))
    return violators


def _format_lazy_ratchet_failure(
    *, new_violators: list[str], stale_allowlist_entries: list[str]
) -> str:
    parts: list[str] = []
    if new_violators:
        bullets = "\n  - ".join(new_violators)
        parts.append(
            "Lazy (function-body) doctrine reach-through. The following files under\n"
            "src/specify_cli/ introduce a NEW nested `from doctrine.*` / `import\n"
            "doctrine` import (outside `if TYPE_CHECKING:` and outside the\n"
            "src/specify_cli/doctrine/ management surface) that is not in the\n"
            "lazy baseline:\n"
            f"  - {bullets}\n"
            "\n"
            "Fix: route the access through the charter proxy (charter.profiles,\n"
            "charter.drg, charter.missions, charter.model_routing, charter.assets,\n"
            "…). A lazy import is not exempt from the boundary. See\n"
            "docs/development/runtime-charter-doctrine-boundary.md."
        )
    if stale_allowlist_entries:
        bullets = "\n  - ".join(stale_allowlist_entries)
        parts.append(
            "Stale lazy-import baseline entries. The following files are listed in\n"
            "`_LAZY_BASELINE_ALLOWLIST` but no longer perform a lazy doctrine import\n"
            "(a migration landed):\n"
            f"  - {bullets}\n"
            "\n"
            "Fix: remove those entries from `_LAZY_BASELINE_ALLOWLIST` so the ratchet\n"
            "shrinks with the migration (only-shrink invariant)."
        )
    return "\n\n".join(parts)


def _declared_all(tree: ast.Module) -> set[str] | None:
    """Return the string members of a module-level ``__all__`` literal, else None."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            continue
        value = node.value
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            return {
                elt.value
                for elt in value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
    return None


def _doctrine_origin_names(tree: ast.Module) -> set[str]:
    """Local names bound by a direct ``from doctrine…`` / ``import doctrine`` import.

    Block context is irrelevant to laundering — a doctrine-origin name that
    appears in ``__all__`` is laundering regardless of where it was imported — so
    a flat ``ast.walk`` is correct here (unlike the reach-through ratchet, which
    needs the enclosing-block context). The bound *local* name (``asname`` when
    aliased) is what could appear in ``__all__``.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level != 0 or not _is_doctrine_module(node.module or ""):
                continue
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if _is_doctrine_module(alias.name):
                    names.add(alias.asname or alias.name.split(".")[0])
    return names


def _laundered_symbols(tree: ast.Module) -> set[str]:
    """Doctrine-origin symbols a module re-exports through its own ``__all__``."""
    declared = _declared_all(tree)
    if not declared:
        return set()
    return declared & _doctrine_origin_names(tree)


def _source_side_laundering() -> dict[str, frozenset[str]]:
    """Map each management-surface module → the doctrine symbols it launders."""
    result: dict[str, frozenset[str]] = {}
    for path in sorted(_EXEMPT_SUBPACKAGE.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        laundered = _laundered_symbols(tree)
        if laundered:
            result[_rel_to_repo(path)] = frozenset(laundered)
    return result


def test_exempt_surface_matches_wp01_manifest() -> None:
    """The lazy ratchet's exempt root is exactly WP01's enumerated management surface.

    Binds this file's exemption to a single source (WP01's ``EXEMPT_MANAGEMENT_SURFACE``)
    so the two cannot drift.
    """
    assert {_rel_to_repo(_EXEMPT_SUBPACKAGE)} == set(EXEMPT_MANAGEMENT_SURFACE)


def test_lazy_detector_skips_type_checking_fixture() -> None:
    """Fixture proof (T020): a ``TYPE_CHECKING`` doctrine import is NOT flagged."""
    assert _file_has_lazy_doctrine_import(_FIXTURES_DIR / "type_checking_import.py") is False


def test_lazy_detector_flags_nested_function_fixture() -> None:
    """Fixture proof (T020): a nested-function doctrine import IS flagged."""
    assert _file_has_lazy_doctrine_import(_FIXTURES_DIR / "nested_function_import.py") is True


def test_lazy_ratchet_arithmetic_is_bidirectional() -> None:
    """Gate efficacy: prove both failure directions without mutating the tree.

    A new violator (present, not baselined) is caught by ``actual - baseline``; a
    stale entry (baselined, migrated away) is caught by ``baseline - actual``.
    """
    baseline = frozenset({"a.py", "b.py"})
    grown = {"a.py", "b.py", "c.py"}
    assert sorted(grown - baseline) == ["c.py"]
    assert not (baseline - grown)
    shrunk = {"a.py"}
    assert not (shrunk - baseline)
    assert sorted(baseline - shrunk) == ["b.py"]


def test_runtime_has_no_new_lazy_doctrine_imports() -> None:
    """Pin the LAZY doctrine reach-through as an only-shrink ratchet (FR-006 / SC-003).

    Must be GREEN today against the 29-file lazy baseline captured from WP01's
    live-tree census. A new nested ``from doctrine.*`` import in a non-baselined
    runtime file trips the "grow" direction; removing a baseline entry without
    migrating the file (or migrating without shrinking the baseline) trips the
    "stale" direction — so WP05–WP07 provably shrink the surface.
    """
    actual_violators = _lazy_doctrine_violators()

    new_violators = sorted(actual_violators - _LAZY_BASELINE_ALLOWLIST)
    stale_allowlist_entries = sorted(_LAZY_BASELINE_ALLOWLIST - actual_violators)

    assert not new_violators and not stale_allowlist_entries, (
        _format_lazy_ratchet_failure(
            new_violators=new_violators,
            stale_allowlist_entries=stale_allowlist_entries,
        )
    )


def test_source_side_no_new_doctrine_laundering() -> None:
    """Pin the SOURCE-side re-export-laundering surface (C-005 / FR-004).

    No ``src/specify_cli/doctrine/*`` module may add a doctrine-origin symbol to
    its ``__all__`` beyond the documented baseline (currently ``config.py``). A
    new laundering module/symbol trips the "grow" direction; when WP05 closes the
    ``config.py`` conduit, the "stale" direction forces the baseline eviction.
    """
    actual = _source_side_laundering()

    new_launderers = {
        path: sorted(symbols - _LAUNDERING_BASELINE.get(path, frozenset()))
        for path, symbols in actual.items()
        if symbols - _LAUNDERING_BASELINE.get(path, frozenset())
    }
    stale_baseline = {
        path: sorted(_LAUNDERING_BASELINE[path] - actual.get(path, frozenset()))
        for path in _LAUNDERING_BASELINE
        if _LAUNDERING_BASELINE[path] - actual.get(path, frozenset())
    }

    assert not new_launderers and not stale_baseline, (
        "Source-side doctrine re-export laundering drift.\n\n"
        f"New/extra laundered symbols (a src/specify_cli/doctrine/* module lists a\n"
        f"doctrine-origin name in its __all__ beyond the baseline): {new_launderers}\n\n"
        f"Stale baseline entries (a conduit was closed — shrink _LAUNDERING_BASELINE): "
        f"{stale_baseline}\n\n"
        "Fix: the management surface is inbound-only. Do not re-export doctrine\n"
        "objects through a first-party __all__; route callers through the charter\n"
        "facade instead. See contracts/public-api-contract.md C4."
    )


def test_config_conduit_is_closed() -> None:
    """Closure-proof (WP05, 01KZPDSR / C-005): ``config.py`` launders nothing.

    Inverts the pre-WP05 ``…is_still_a_conduit`` sanity-pin: once WP05 dropped the
    doctrine-origin org-pack-config symbols from ``config.__all__``, the module
    must no longer appear in the source-side laundering map, and the baseline that
    seeded it must be empty. Re-introducing a doctrine-origin symbol into
    ``config.__all__`` (re-opening the conduit) reds this guard.
    """
    actual = _source_side_laundering()
    assert "src/specify_cli/doctrine/config.py" not in actual
    assert _LAUNDERING_BASELINE == {}
