"""Gate 3 (FR-003/FR-007, WP09): no module outside ``src/charter/**`` or
``src/doctrine/**`` imports ``doctrine.resolver`` directly.

Mission ``charter-sole-door-bypass-closure-01KZ3WAA``, WP09 / T039. Third of the
three mission-wide durability gates this work package ships.

**This gate is a forward-looking regression guard, NOT proof of a closure.**
The WP09 prompt is explicit about this, and so is the post-tasks squad
correction that produced it: an earlier draft claimed "WP05 closed the one real
consumer", which is false — *nothing* outside ``src/charter/**`` ever imported
``doctrine.resolver``. There was no violation to close, so this module must not
be read, cited, or summarised as evidence that this mission eliminated a bypass.
What it does is make the currently-clean state *durable*: the moment a future
consumer starts reaching around
:class:`charter.resolver.DoctrineService` into ``doctrine.resolver``'s tier
functions, this test reds.

Why the boundary matters
------------------------
``doctrine/resolver.py`` owns the 5-tier resolution chain (OVERRIDE > LEGACY >
GLOBAL_MISSION > GLOBAL > PACKAGE_DEFAULT) plus ``resolve_mission``. The mission
contract (``contracts/charter-doctrine-service-contract.md``) pins that every
tier and the mission-config resolution "remains reachable ONLY via a method on
[``charter.resolver.DoctrineService``] from outside ``src/charter/**``".
``doctrine/resolver.py``'s functions are the implementation those methods
delegate to. A direct import from a consumer re-opens exactly the second,
ungated resolution path FR-003 exists to prevent — ``charter/resolver.py``'s own
comment marks its import as "the ONLY import of ``doctrine.resolver``'s tier
functions".

Consumers that need the resolution *types* (``ResolutionResult`` /
``ResolutionTier``) already have a sanctioned route: the
``charter.resolution`` facade, which re-exports them by identity (proven by
``test_charter_facades_reexport_doctrine.py``). ``specify_cli/runtime/resolver.py``
is the live example, and its module docstring records why identity-preserving
re-export matters (~30 CI failures when a duplicate enum existed). So the
zero-tolerance stance costs a consumer nothing.

Zero-tolerance, no exclusions
-----------------------------
There is no allow-list (C-002) and none is expected: the live census outside the
two owning layers is empty. Adding an entry here to green a new violation is a
policy change, not a fix — route the consumer through
``charter.resolver.DoctrineService`` or the ``charter.resolution`` facade
instead.

Why this is not a duplicate of ``test_runtime_charter_doctrine_boundary.py``
----------------------------------------------------------------------------
That gate is deliberately narrower on all three axes, and the WP09 prompt
directs not re-asserting what an adjacent gate already proves:

* **Scope** — it audits ``src/runtime/**`` (plus ``src/specify_cli/doctrine/``);
  this one audits *all* of ``src/`` outside the two owning layers.
* **Depth** — its ``_module_imports_doctrine_directly`` inspects **module-level**
  imports only (its own docstring says so). This gate walks every scope, so a
  function-local or ``try``/``except``-nested import is caught. spec.md FR-001
  notes that same module-level-only limitation is why the "boundary ratchet"
  concern at the ``tasks_status_cmd.py`` sites was a red herring — the real
  violations in this codebase are function-local.
* **Tolerance** — it carries a shrink-only allow-list of pre-existing sites;
  this gate has none.
* **Target** — it bans ``doctrine.*`` broadly for runtime modules; this one bans
  the single ``doctrine.resolver`` module for everyone, including
  ``specify_cli`` modules that the other gate does not audit at all.

A5 fix: ``from package import module`` also binds the guarded module
------------------------------------------------------------------------
Adversarial-review injection probes measured this gate at a 4/9 real catch
rate. The dominant miss: ``from doctrine import resolver`` — in all three
spellings (plain, aliased, function-local) — fully evaded the ban. For an
``ast.ImportFrom`` the detector tested only ``node.module`` (``"doctrine"``);
it never tried ``node.module + "." + alias.name``. But ``from doctrine import
resolver`` binds the IDENTICAL module object as ``import doctrine.resolver``,
and ``resolver.resolve_template(...)`` then re-opens the exact ungated second
resolution path this gate exists to forbid. :func:`scan_file_resolver_imports`
now extends its candidate dotted-name list with the package-qualified form for
every ``ImportFrom`` name, closing all three spellings in one change (see
:func:`test_injected_from_package_import_module_is_flagged` and
:func:`test_injected_aliased_from_package_import_is_flagged`).
"""

from __future__ import annotations

import ast
import functools
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.architectural._sole_door_scan import (
    REPO_ROOT,
    SRC_ROOT,
    iter_source_files,
    rel_to_repo,
)

pytestmark = pytest.mark.architectural

#: The guarded module. ``doctrine.resolver`` itself and its submodules.
GUARDED_MODULE = "doctrine.resolver"

#: The two layers entitled to import it: the charter layer (which owns the sole
#: door and its facades) and the doctrine layer (which owns the module).
#: Directory-prefix keyed, never per-file and never per-line.
OWNING_LAYER_PREFIXES = ("src/charter/", "src/doctrine/")

#: The sanctioned route for a consumer that needs the resolution *types*.
FACADE_MODULE = "charter.resolution"


@dataclass(frozen=True)
class ResolverImportSite:
    """One direct import of ``doctrine.resolver`` outside the owning layers."""

    rel_path: str
    qualname: str
    lineno: int
    statement: str

    def describe(self) -> str:
        return f"{self.rel_path}:{self.lineno} ({self.qualname}) {self.statement}"


def _targets_guarded_module(dotted: str) -> bool:
    """True for ``doctrine.resolver`` itself or anything beneath it."""
    return dotted == GUARDED_MODULE or dotted.startswith(f"{GUARDED_MODULE}.")


def _qualname_map(tree: ast.Module) -> dict[int, str]:
    """``id(node) -> enclosing dotted qualname`` for every node in *tree*.

    Built by descent rather than by line lookup so a nested ``def``/``class``
    inside a ``try`` block still resolves to its true qualname.
    """
    out: dict[int, str] = {}

    def _walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                child_prefix = f"{prefix}.{child.name}" if prefix else child.name
                out[id(child)] = child_prefix
                _walk(child, child_prefix)
            else:
                out[id(child)] = prefix or "<module>"
                _walk(child, prefix)

    _walk(tree, "")
    return out


def scan_file_resolver_imports(path: Path, rel_path: str) -> list[ResolverImportSite]:
    """Every direct ``doctrine.resolver`` import in one file, at any scope.

    Walks the whole AST, so ``from doctrine.resolver import X`` and
    ``import doctrine.resolver`` are caught at module level, inside a function
    body, and inside a nested ``try``/``except`` — the three scopes the real
    imports in this codebase actually use. Relative imports (``level > 0``) are
    skipped: they can never name the absolute ``doctrine.resolver`` module.
    """
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    qualnames = _qualname_map(tree)
    lines = source.splitlines()
    found: list[ResolverImportSite] = []
    for node in ast.walk(tree):
        dotted_names: list[str] = []
        if isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                dotted_names.append(node.module)
                # A5 fix: ``from doctrine import resolver`` binds the
                # identical module object as ``import doctrine.resolver`` —
                # node.module alone ("doctrine") never matches the guarded
                # "doctrine.resolver" target, so the imported NAME must also
                # be tried as a dotted extension of the package it came from.
                dotted_names.extend(
                    f"{node.module}.{alias.name}" for alias in node.names
                )
        elif isinstance(node, ast.Import):
            dotted_names.extend(alias.name for alias in node.names)
        else:
            continue
        if not any(_targets_guarded_module(name) for name in dotted_names):
            continue
        statement = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
        found.append(
            ResolverImportSite(
                rel_path,
                qualnames.get(id(node), "<module>"),
                node.lineno,
                statement,
            )
        )
    return found


def in_owning_layer(rel_path: str) -> bool:
    return rel_path.startswith(OWNING_LAYER_PREFIXES)


@functools.cache
def resolver_import_census() -> tuple[tuple[ResolverImportSite, ...], ...]:
    """``(outside_owning_layers, inside_owning_layers)`` import censuses.

    Memoised for the test session; a pure function of an unchanging tree.
    """
    outside: list[ResolverImportSite] = []
    inside: list[ResolverImportSite] = []
    for path in iter_source_files(SRC_ROOT):
        rel_path = rel_to_repo(path)
        bucket = inside if in_owning_layer(rel_path) else outside
        bucket.extend(scan_file_resolver_imports(path, rel_path))
    return tuple(outside), tuple(inside)


def check_resolver_import_gate(sites: tuple[ResolverImportSite, ...]) -> list[str]:
    """Violations — zero-tolerance, no allow-list of any kind (C-002)."""
    return [
        f"{site.describe()} imports {GUARDED_MODULE} directly from outside "
        f"src/charter/** and src/doctrine/** — reach the 5 resolver tiers "
        f"through a charter.resolver.DoctrineService method, or import the "
        f"resolution types from the {FACADE_MODULE} facade"
        for site in sites
    ]


# =========================================================================== #
# Anti-vacuity: the walker really scans the tree and really sees real imports
# =========================================================================== #


def test_scan_reaches_a_broad_slice_of_src() -> None:
    """The ``rglob`` walk must not silently narrow to a subtree."""
    scanned = {rel_to_repo(p) for p in iter_source_files(SRC_ROOT)}
    representative = {
        "src/charter/resolver.py",
        "src/charter/resolution.py",
        "src/specify_cli/runtime/resolver.py",
        "src/specify_cli/charter_runtime/lint/checks/org_layer.py",
    }
    assert not representative - scanned, sorted(representative - scanned)
    assert len(scanned) > 200


def test_detector_finds_the_real_sanctioned_imports() -> None:
    """The owning layers DO import ``doctrine.resolver`` — the detector sees them.

    Without this, a detector that silently matched nothing at all would make the
    zero-violation assertion below meaningless. ``charter/resolver.py`` carries
    the mission's one sanctioned tier-function import and ``charter/resolution.py``
    the facade type re-export, so both must appear in the inside-layer census.
    """
    _, inside = resolver_import_census()
    inside_files = {site.rel_path for site in inside}
    assert "src/charter/resolver.py" in inside_files, sorted(inside_files)
    assert "src/charter/resolution.py" in inside_files, sorted(inside_files)


def test_the_facade_route_preserves_class_identity() -> None:
    """The sanctioned alternative really is a re-export, not a duplicate.

    A zero-tolerance ban is only reasonable if consumers have a working route.
    This pins that ``charter.resolution``'s types ARE ``doctrine.resolver``'s
    types — the property ``specify_cli/runtime/resolver.py`` depends on.
    """
    import charter.resolution as facade
    import doctrine.resolver as owner

    assert facade.ResolutionTier is owner.ResolutionTier
    assert facade.ResolutionResult is owner.ResolutionResult


def test_the_documented_consumer_uses_the_facade_not_the_owner() -> None:
    """``specify_cli/runtime/resolver.py`` must stay on the facade route.

    A live, concrete example that the sanctioned route is actually in use —
    so this gate is guarding a real convention, not a hypothetical one.
    """
    rel = "src/specify_cli/runtime/resolver.py"
    path = REPO_ROOT / rel
    assert scan_file_resolver_imports(path, rel) == []
    assert f"from {FACADE_MODULE} import" in path.read_text(encoding="utf-8")


# =========================================================================== #
# The gate
# =========================================================================== #


def test_no_direct_doctrine_resolver_import_outside_the_owning_layers() -> None:
    """Zero-tolerance forward-looking guard — no allow-list (C-002).

    Reminder for anyone citing this test: it proves the boundary is *currently*
    clean and stays clean, NOT that this mission closed a violation here. There
    was never one to close (see module docstring).
    """
    outside, _ = resolver_import_census()
    violations = check_resolver_import_gate(outside)
    assert violations == [], "\n".join(violations)


# =========================================================================== #
# NFR-003 self-mutation proofs — function-local and nested scope injection.
# =========================================================================== #


def _scratch(tmp_path: Path, rel_path: str, source: str) -> list[ResolverImportSite]:
    module = tmp_path / Path(rel_path).name
    module.write_text(source, encoding="utf-8")
    return scan_file_resolver_imports(module, rel_path)


def test_injected_function_local_import_is_flagged(tmp_path: Path) -> None:
    """A **function-local** direct import is caught, naming the exact site.

    Injected at function-local scope specifically (NFR-003): a module-level-only
    detector would pass this vacuously, which is precisely the limitation the
    adjacent ``test_runtime_charter_doctrine_boundary.py`` has and this gate must
    not.
    """
    sites = _scratch(
        tmp_path,
        "src/specify_cli/regressed_local.py",
        "def resolve(mission):\n"
        "    from doctrine.resolver import resolve_template\n"
        "\n"
        "    return resolve_template(mission)\n",
    )
    assert [s.qualname for s in sites] == ["resolve"], [
        s.describe() for s in sites
    ]
    assert sites[0].qualname == "resolve"
    assert sites[0].lineno == 2
    violations = check_resolver_import_gate(tuple(sites))
    assert violations
    assert "regressed_local.py" in violations[0]
    assert "resolve" in violations[0]


def test_injected_nested_try_except_import_is_flagged(tmp_path: Path) -> None:
    """A direct import nested inside a method's ``try``/``except`` is caught.

    Mirrors the real nesting shape used by ``org_layer.py``'s builder imports —
    two blocks deep inside a method, invisible to a module-level scan.
    """
    sites = _scratch(
        tmp_path,
        "src/specify_cli/regressed_nested.py",
        "class Sneaky:\n"
        "    def resolve(self, mission):\n"
        "        try:\n"
        "            from doctrine.resolver import resolve_mission\n"
        "        except ImportError:\n"
        "            return None\n"
        "        return resolve_mission(mission)\n",
    )
    assert [s.qualname for s in sites] == ["Sneaky.resolve"], [
        s.describe() for s in sites
    ]
    assert sites[0].qualname == "Sneaky.resolve"
    assert check_resolver_import_gate(tuple(sites))


def test_injected_plain_module_import_is_flagged(tmp_path: Path) -> None:
    """``import doctrine.resolver`` (no ``from``) is caught too."""
    sites = _scratch(
        tmp_path,
        "src/specify_cli/regressed_plain.py",
        "def resolve(mission):\n"
        "    import doctrine.resolver\n"
        "\n"
        "    return doctrine.resolver.resolve_mission(mission)\n",
    )
    assert [s.qualname for s in sites] == ["resolve"], [
        s.describe() for s in sites
    ]
    assert check_resolver_import_gate(tuple(sites))


def test_injected_aliased_module_import_is_flagged(tmp_path: Path) -> None:
    """``import doctrine.resolver as dr`` cannot launder the import."""
    sites = _scratch(
        tmp_path,
        "src/specify_cli/regressed_aliased.py",
        "import doctrine.resolver as dr\n"
        "\n"
        "\n"
        "def resolve(mission):\n"
        "    return dr.resolve_mission(mission)\n",
    )
    assert [s.qualname for s in sites] == ["<module>"], [
        s.describe() for s in sites
    ]
    assert sites[0].qualname == "<module>"
    assert check_resolver_import_gate(tuple(sites))


def test_injected_from_package_import_module_is_flagged(tmp_path: Path) -> None:
    """A5 widening: ``from doctrine import resolver`` binds the identical module.

    Measured injection-probe miss on Gate 3 (4/9 catch rate): for an
    ``ast.ImportFrom`` the pre-fold detector tested only ``node.module``
    (``"doctrine"``), never ``node.module + "." + alias.name``. ``from doctrine
    import resolver`` binds the SAME module object as
    ``import doctrine.resolver`` — ``resolver.resolve_template(...)`` then
    re-opens the exact ungated second resolution path this gate exists to
    forbid. Injected at function-local scope (NFR-003).
    """
    sites = _scratch(
        tmp_path,
        "src/specify_cli/regressed_frompkg.py",
        "def resolve(mission):\n"
        "    from doctrine import resolver\n"
        "\n"
        "    return resolver.resolve_template(mission)\n",
    )
    assert [s.qualname for s in sites] == ["resolve"], [
        s.describe() for s in sites
    ]
    violations = check_resolver_import_gate(tuple(sites))
    assert violations, "the gate must bite on a from-package module import"
    assert "regressed_frompkg.py" in violations[0]
    assert "resolve" in violations[0]


def test_injected_aliased_from_package_import_is_flagged(tmp_path: Path) -> None:
    """The from-package spelling cannot be laundered by an ``as``-alias either.

    Same A5 vector as the plain-spelling sibling test, with
    ``from doctrine import resolver as dr`` — the third of the "all three
    spellings" A5 names (plain, aliased, function-local).
    """
    sites = _scratch(
        tmp_path,
        "src/specify_cli/regressed_frompkg_aliased.py",
        "def resolve(mission):\n"
        "    from doctrine import resolver as dr\n"
        "\n"
        "    return dr.resolve_template(mission)\n",
    )
    assert [s.qualname for s in sites] == ["resolve"], [
        s.describe() for s in sites
    ]
    assert check_resolver_import_gate(tuple(sites))


def test_injected_submodule_import_is_flagged(tmp_path: Path) -> None:
    """A future ``doctrine.resolver.<submodule>`` is inside the ban's scope."""
    sites = _scratch(
        tmp_path,
        "src/specify_cli/regressed_submodule.py",
        "def resolve(mission):\n"
        "    from doctrine.resolver.tiers import OVERRIDE\n"
        "\n"
        "    return OVERRIDE\n",
    )
    assert [s.qualname for s in sites] == ["resolve"], [
        s.describe() for s in sites
    ]
    assert check_resolver_import_gate(tuple(sites))


def test_detector_ignores_the_sanctioned_facade_import(tmp_path: Path) -> None:
    """True negative: importing from ``charter.resolution`` is never flagged."""
    sites = _scratch(
        tmp_path,
        "src/specify_cli/compliant_consumer.py",
        "from charter.resolution import ResolutionResult, ResolutionTier\n"
        "\n"
        "\n"
        "def resolve(service, mission):\n"
        "    return service.resolve_mission(mission)\n",
    )
    assert sites == []


def test_detector_ignores_prose_mentioning_the_module(tmp_path: Path) -> None:
    """True negative: a docstring or comment naming the module is not an import.

    ``charter/template_resolver.py`` and ``specify_cli/runtime/resolver.py`` both
    discuss ``doctrine.resolver`` at length in prose without importing it; a
    grep-shaped gate would flag both. This is that false-positive class,
    reproduced in isolation.
    """
    sites = _scratch(
        tmp_path,
        "src/specify_cli/prose_only.py",
        '"""Deliberately does not use ``doctrine.resolver``.\n'
        "\n"
        "See :func:`doctrine.resolver.resolve_template` for the tier chain we do\n"
        "NOT call; we go through the charter method instead.\n"
        '"""\n'
        "\n"
        "# import doctrine.resolver  <- never do this\n"
        "RESOLVER_DOC = 'doctrine.resolver'\n"
        "\n"
        "\n"
        "def resolve(service, mission):\n"
        "    return service.resolve_mission(mission)\n",
    )
    assert sites == []


def test_detector_ignores_a_similarly_named_module(tmp_path: Path) -> None:
    """True negative: ``doctrine.resolver_utils`` is a different module.

    Guards the prefix check against matching on a shared name stem — the ban is
    ``doctrine.resolver`` and its submodules, not everything starting with those
    characters.
    """
    sites = _scratch(
        tmp_path,
        "src/specify_cli/similar_name.py",
        "def resolve():\n    from doctrine.resolver_utils import helper\n\n    return helper()\n",
    )
    assert sites == []


def test_owning_layer_prefix_is_directory_keyed_not_file_keyed() -> None:
    """The exemption is a directory prefix — it cannot degrade into a file list.

    A per-file exemption would silently sanction a new charter module; a prefix
    covers the layer as a layer, which is the intended boundary.
    """
    assert in_owning_layer("src/charter/resolver.py")
    assert in_owning_layer("src/charter/context_renderers/template_include.py")
    assert in_owning_layer("src/doctrine/resolver.py")
    assert not in_owning_layer("src/specify_cli/runtime/resolver.py")
    assert not in_owning_layer("src/runtime/next/runtime_bridge_io.py")
    # A path that merely *starts* like the charter layer is not in it.
    assert not in_owning_layer("src/charter_runtime/thing.py")


def test_gate_runs_under_fast_tier_budget() -> None:
    """The whole-tree scan stays inside the 30 s fast-tier ceiling.

    Scans directly rather than via the memoised census — timing a cache hit
    would be a vacuous measurement.
    """
    start = time.monotonic()
    for path in iter_source_files(SRC_ROOT):
        scan_file_resolver_imports(path, rel_to_repo(path))
    elapsed = time.monotonic() - start
    assert elapsed < 30.0, f"doctrine.resolver import scan took {elapsed:.2f}s"
