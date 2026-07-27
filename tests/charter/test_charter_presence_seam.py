"""Canonical charter-presence resolution: census + parity (WP04, T022/T023).

charter-preflight-remediation (mission ``charter-preflight-remediation-01KYG9WK``):
the freshness gate (``specify_cli.charter_runtime.freshness.computer``) reads
``charter.yaml`` as the authoritative, resolving charter source (R-001).
Ten operator-reachable diagnostics used to disagree, keying some or all of
their answer off the retired ``charter.md`` instead -- so a legacy-bundle
project (``charter.md`` present, ``charter.yaml`` absent) saw the gate block
while every diagnostic reported healthy (the User Story 2 symptom). (Cycle 1
converged nine; cycle 2 found and converged a tenth --
``specify_cli.dashboard.charter_path.resolve_project_charter_path`` -- that
cycle 1's hand-written scan-root list did not reach.)

WP04 converges every one of those diagnostics onto the ONE canonical,
non-mutating seam: :func:`charter.bundle.charter_yaml_present` (a thin
wrapper over the existing :func:`charter.bundle.first_missing_bundle_file`).

This module has two independent jobs:

* **T022** -- pin the resolver census by CRITERION (R-007), not by a
  hand-written list. ``test_no_unrouted_charter_presence_checks_outside_the_seam``
  is the one that must go red if a brand-new hand-rolled
  ``charter.md``/``charter.yaml`` existence check is added anywhere in the
  operator-reachable surface -- WITHOUT anyone updating a list. See its
  docstring and the falsification proof recorded in the WP04 handoff.
* **T023** -- prove every operator-reachable surface agrees with the gate
  across all four fixture shapes (F1-F4, data-model.md), and that the seam
  itself never mutates the project.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from charter.bundle import charter_yaml_present
from charter.context import (
    _project_charter_json_block,
    build_charter_context,
    build_charter_context_include,
)
from specify_cli.charter_runtime.freshness import compute_freshness
from specify_cli.cli.commands.charter._common import _resolve_charter_path
from specify_cli.task_utils import TaskCliError

# This module shells out to the real CLI and initialises real git repos to prove
# the census against live behaviour (WP04 T014/T023), so it is NOT `fast` and it
# DOES need `git_repo`. Marking it `fast` made a `-m fast` inner-loop run pay
# subprocess cost silently, and the missing `git_repo` marker made a
# `-m git_repo` CI run skip this file entirely — the census would not have run.
pytestmark = pytest.mark.git_repo


# ---------------------------------------------------------------------------
# T022 -- criterion-derived census (R-007)
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    candidate = Path(__file__).resolve().parent
    while candidate != candidate.parent:
        if (candidate / "pyproject.toml").exists():
            return candidate
        candidate = candidate.parent
    raise RuntimeError("Could not find repo root (no pyproject.toml found in any parent directory)")


_REPO_ROOT = _repo_root()

#: The operator-reachable charter-presence-resolution surface this census
#: polices: the WHOLE ``src/`` tree.
#:
#: charter-preflight-remediation (WP04 cycle 2): cycle 1's scan was a
#: hand-written list of three paths (``src/charter``, ``.../cli/commands/
#: charter``, ``charter_bundle.py``). That list-shaped boundary is exactly
#: the failure mode this census exists to eliminate everywhere else --
#: R-003's own census missed a real, live, operator-reachable resolver
#: (``specify_cli.dashboard.charter_path.resolve_project_charter_path``)
#: because it sat outside those three paths. Scanning the entire ``src/``
#: tree closes that boundary gap: a brand-new hand-rolled check ANYWHERE
#: under ``src/`` now fails this test without anyone updating a root list
#: (see the falsification proof in the WP04 cycle-2 handoff, which plants
#: a probe under ``src/specify_cli/dashboard/`` -- a directory that was
#: never in cycle 1's root list -- and confirms it goes red).
_SCAN_ROOTS: tuple[Path, ...] = (_REPO_ROOT / "src",)

#: Directories excluded from the ``src/``-wide scan above. Every exclusion
#: here is a DECLARED, REVIEWED exemption with a stated reason -- the same
#: standard the ``_EXEMPT`` table below holds individual call sites to --
#: never an unstated gap in coverage.
_SCAN_EXCLUDE_DIRS: tuple[Path, ...] = (
    # ``src/specify_cli/charter_runtime/`` -- the freshness GATE (R-003
    # site 1) is the convergence TARGET everything else in this file
    # converges onto, not a site required to route through the wrapper it
    # predates (WP04 prompt: "Site 1 is the convergence target, not a site
    # to change"). It also deliberately owns an independent copy of the
    # ``charter.yaml`` filename by design (``charter.bundle``'s own
    # docstring warns against importing the gate's copy into the seam, to
    # avoid inverting the dependency direction) -- scanning it would
    # require exempting the very reference implementation.
    _REPO_ROOT / "src" / "specify_cli" / "charter_runtime",
    # ``src/specify_cli/upgrade/migrations/`` -- migration-local checks are
    # explicitly OUT of FR-004 scope (spec Assumptions clause): they have
    # idempotency-shaped definitions built for a one-time migration, not
    # health reporting.
    _REPO_ROOT / "src" / "specify_cli" / "upgrade" / "migrations",
)


def _is_excluded(path: Path) -> bool:
    return any(excluded == path or excluded in path.parents for excluded in _SCAN_EXCLUDE_DIRS)

#: The ONLY thing this scan hard-codes: the artifact NAMES the mission is
#: about (not call SITES). A Path expression whose text contains one of
#: these is "keyed off a charter artifact" for the purposes of this scan.
_CHARTER_ARTIFACT_MARKERS: tuple[str, ...] = (
    "CHARTER_MD",
    "CHARTER_YAML",  # substring-matches CHARTER_YAML_FILENAME too
    '"charter.md"',
    "'charter.md'",
    '"charter.yaml"',
    "'charter.yaml'",
)


def _iter_surface_files() -> list[Path]:
    files: list[Path] = []
    for root in _SCAN_ROOTS:
        if root.is_file():
            if not _is_excluded(root):
                files.append(root)
        elif root.is_dir():
            files.extend(sorted(p for p in root.rglob("*.py") if not _is_excluded(p)))
    return files


@dataclass(frozen=True)
class _RawCheck:
    """One raw ``<charter-artifact-path>.exists()`` call site."""

    module: str  # repo-relative, posix
    qualname: str  # dotted enclosing function/method path (never a line number)
    check_text: str  # ast.unparse() of the full call, for actionable failures


def _text_has_marker(text: str) -> bool:
    return any(marker in text for marker in _CHARTER_ARTIFACT_MARKERS)


class _QualnameFunctionFinder(ast.NodeVisitor):
    """Collect every function/method body, keyed by its dotted qualname.

    Findings are identified by STABLE symbol names, never by line number
    (WP03 was rejected for keying an exemption on a line number that a
    docstring edit silently moved).
    """

    def __init__(self) -> None:
        self._stack: list[str] = []
        self.functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    def _qualname(self) -> str:
        return ".".join(self._stack) if self._stack else "<module>"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._stack.append(node.name)
        self.functions[self._qualname()] = node
        self.generic_visit(node)
        self._stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._stack.append(node.name)
        self.functions[self._qualname()] = node
        self.generic_visit(node)
        self._stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()


def _local_assignment_texts(func_node: ast.AST) -> dict[str, list[str]]:
    """Map ``name -> [unparsed RHS text, ...]`` for every simple local assign.

    One hop of data-flow, deliberately: ``charter_path = repo_root / ".kittify"
    / "charter" / "charter.md"`` followed by ``if charter_path.exists():`` is
    the ACTUAL shape every real resolver in this mission used pre-fix (see
    ``_common.py::_resolve_charter_path`` before WP04) -- a scan that only
    matches the marker INLINE in the ``.exists()`` expression itself would
    miss the exact bug class this census exists to catch.
    """
    assigns: dict[str, list[str]] = {}
    for node in ast.walk(func_node):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):  # golden-count: cardinality-is-contract
            try:
                assigns.setdefault(node.targets[0].id, []).append(ast.unparse(node.value))
            except Exception:  # pragma: no cover - defensive
                continue
    return assigns


def _find_existence_checks_in_function(
    module_rel: str, qualname: str, func_node: ast.AST
) -> list[_RawCheck]:
    local_assigns = _local_assignment_texts(func_node)
    found: list[_RawCheck] = []
    for node in ast.walk(func_node):
        is_bare_exists_call = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "exists"
            and not node.args
            and not node.keywords
        )
        if not is_bare_exists_call:
            continue
        assert isinstance(node, ast.Call)  # noqa: S101 - narrows for mypy/type-checkers
        receiver = node.func.value  # type: ignore[union-attr]
        try:
            receiver_text = ast.unparse(receiver)
        except Exception:  # pragma: no cover - defensive
            receiver_text = ""
        candidate_texts = [receiver_text]
        # One-hop indirection: `<name>.exists()` where `<name>` was assigned
        # from an expression keying off a charter artifact earlier in the
        # SAME function.
        if isinstance(receiver, ast.Name):
            candidate_texts.extend(local_assigns.get(receiver.id, []))
        if any(_text_has_marker(text) for text in candidate_texts):
            try:
                call_text = ast.unparse(node)
            except Exception:  # pragma: no cover - defensive
                call_text = receiver_text
            found.append(_RawCheck(module=module_rel, qualname=qualname, check_text=call_text))
    return found


def _scan_raw_charter_existence_checks() -> list[_RawCheck]:
    """Find every ``<charter.md|charter.yaml path>.exists()`` call in the surface.

    This is the T022 CRITERION scan (R-007): a PATTERN search (an existence
    check keyed off a charter.md/charter.yaml name, anywhere in the scanned
    surface -- including one hop of local-variable indirection, see
    ``_local_assignment_texts``), not an enumeration of known resolver call
    sites. A brand-new hand-rolled check added anywhere in this surface is
    found automatically.

    Module-level code (outside any function) is also scanned, using the
    module's own top-level assignments as its "local" scope.
    """
    found: list[_RawCheck] = []
    for path in _iter_surface_files():
        module_rel = path.relative_to(_REPO_ROOT).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=module_rel)
        finder = _QualnameFunctionFinder()
        finder.visit(tree)
        # Every function/method body, keyed by stable dotted qualname.
        for qualname, func_node in finder.functions.items():
            found.extend(_find_existence_checks_in_function(module_rel, qualname, func_node))
        # Module-level top-level code (rare for this surface, but scanned
        # for completeness -- e.g. a module-scope existence check).
        module_only_nodes: list[ast.stmt] = [
            stmt
            for stmt in tree.body
            if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        module_wrapper = ast.Module(body=module_only_nodes, type_ignores=[])
        found.extend(_find_existence_checks_in_function(module_rel, "<module>", module_wrapper))
    return found


# ---------------------------------------------------------------------------
# T022 -- the reasoned exemption table.
#
# Every entry is NOT a "known resolver" call site -- it is a raw check the
# R-007 criterion classifies as NOT a presence resolver: it degrades to a
# default/empty/no-op rather than gating an operator-visible presence
# answer, so it is legitimately allowed to keep its own raw check instead of
# routing through charter_yaml_present() / first_missing_bundle_file().
# Adding a member here is itself a deliberate, reviewed act (recorded
# inline) -- it is NOT how a new *resolver* gets "converged"; a new
# resolver must call the seam, never join this table.
# ---------------------------------------------------------------------------

_EXEMPT: frozenset[tuple[str, str]] = frozenset(
    {
        # The canonical seam's OWN implementation -- this IS the check
        # everything else in the surface must route through.
        ("src/charter/bundle.py", "first_missing_bundle_file"),
        ("src/charter/bundle.py", "compute_bundle_content_hash"),
        # Optional DISPLAY content that degrades to "" on a missing file
        # rather than gating any presence answer (R-007 / its own
        # docstring: "the companion file is an optional display surface
        # ... a missing or unreadable charter.md degrades to the empty
        # string rather than raising").
        ("src/charter/context.py", "_compact_section_block"),
        # sync.py:98 -- ensure_charter_bundle_fresh's OWN entry gate for
        # its own (no-op, post-IC-04) mutation attempt. T019 finding:
        # internal-only, not an operator-facing presence answer -- it
        # decides whether sync() has anything to (attempt to) do, not
        # whether the project "has a charter". Deliberately NOT routed
        # (site 6 excluded; the R-003 pinned count is revised 10 -> 9 as
        # a direct consequence -- see the WP04 handoff).
        ("src/charter/sync.py", "ensure_charter_bundle_fresh"),
        # sync.py:224 -- _load_charter_yaml_section degrades to "use an
        # empty config" (its own docstring) on a missing charter.yaml --
        # the textbook not-a-resolver branch under R-007.
        ("src/charter/sync.py", "_load_charter_yaml_section"),
        # Informational per-file listing table for `charter status`
        # (both charter.yaml's AND charter.md's existence/size are shown
        # as display rows for the operator to read); the overall
        # "available" gate for this same payload is answered upstream by
        # _resolve_charter_path (which DOES route through the seam) --
        # this loop reports, it does not gate.
        (
            "src/specify_cli/cli/commands/charter/_status_collectors.py",
            "_collect_charter_sync_status",
        ),
        # The remaining five entries were found by strengthening this
        # scan's local-variable resolution (see ``_local_assignment_texts``)
        # after its first version missed the `charter_path = <expr with
        # marker>; ... charter_path.exists()` indirection shape -- the
        # SAME shape ``_resolve_charter_path`` used pre-WP04. Each is a
        # genuine R-007 non-resolver, not a missed conversion:
        #
        # `render_compact_view`'s own docstring: "the companion `charter.md`
        # is DISPLAY-only and optional ... a missing/unreadable file
        # degrades to an empty anchor set rather than raising" -- the same
        # shape as `_compact_section_block`.
        ("src/charter/compact.py", "render_compact_view"),
        # `_load_references`: "Returns [] when charter.yaml or its catalog
        # section is absent" -- a content read that degrades to an empty
        # list, not a presence gate.
        ("src/charter/context.py", "_load_references"),
        # `_read_compiled_languages`: "Returns None when charter.yaml does
        # not exist ... the caller falls back to interview extraction" --
        # textbook degrade-to-fallback, not a presence gate.
        ("src/charter/language_scope.py", "_read_compiled_languages"),
        # `_project_has_doctrine_overrides`: "Best-effort: any I/O or parse
        # failure collapses to False" -- a governance-content probe
        # ("does the project declare overrides"), not a "does the charter
        # exist" answer.
        ("src/charter/mission_type_profiles.py", "_project_has_doctrine_overrides"),
        # `write_compiled_charter` is a WRITE path (charter generate /
        # synthesize), not a read-only diagnostic: its existence check
        # selects merge-vs-bootstrap-create branching internally and is
        # never surfaced to the operator as a presence ANSWER. This mirrors
        # the ``ensure_charter_bundle_fresh`` (site 6) reasoning above --
        # an internal gate for the function's OWN mutation, not an
        # operator-facing presence report.
        ("src/charter/compiler.py", "write_compiled_charter"),
        # The remaining four entries were found only after widening
        # ``_SCAN_ROOTS`` to the whole ``src/`` tree (WP04 cycle 2) --
        # cycle 1's three-path root list never reached them. Each is a
        # genuine R-007 non-resolver, not a missed conversion:
        #
        # `get_bundle_schema_version`'s own docstring: "Returns: ...None if
        # the file is absent..." -- a content read (bundle schema version
        # integer) that degrades to None, the same shape as
        # `_read_compiled_languages` above. Never surfaced to an operator
        # as a presence answer.
        ("src/doctrine/versioning.py", "get_bundle_schema_version"),
        # `migrate_v1_to_v2` is a WRITE path (v1->v2 bundle migration, with
        # its own `dry_run` flag), not a read-only diagnostic -- the same
        # "internal gate for the function's OWN mutation" reasoning as
        # `write_compiled_charter` above.
        ("src/doctrine/versioning.py", "migrate_v1_to_v2"),
        # `is_spdd_reasons_active`'s two raw checks gate a CACHE key/mtime
        # computation (`cache_key = ... if charter_yaml_path.exists() else
        # ...`), not the activation answer itself -- that answer is
        # computed by `_compute_active` (a separate function, one hop
        # further via a parameter rather than a local assignment, so this
        # scan's one-hop local-variable heuristic does not independently
        # re-find it; documented here rather than silently left
        # unclassified). `_compute_active`'s own pre-existing, unrelated
        # ParserError crash on unparseable charter.yaml is the SAME defect
        # already excluded from `test_all_surfaces_agree_on_presence`'s F4
        # case (see that test's inline comment and the WP04 cycle-1
        # handoff finding 9) -- out of this WP's locality of change.
        ("src/doctrine/spdd_reasons/activation.py", "is_spdd_reasons_active"),
        # `_read_project_selections`'s own docstring: "Missing/malformed
        # YAML degrades to empty lists" -- a best-effort diagnostic content
        # read (the charter's declared `selected_<kind>` doctrine
        # selections), not a presence gate; mirrors `_load_references`
        # above.
        ("src/specify_cli/cli/commands/_doctrine_collect.py", "_read_project_selections"),
    }
)


def test_no_unrouted_charter_presence_checks_outside_the_seam() -> None:
    """T022 -- the criterion-derived census (SC-003).

    Every raw ``<charter.md|charter.yaml path>.exists()`` call found
    anywhere in the operator-reachable surface must be either the
    canonical seam's own implementation, or a documented, R-007-reasoned
    exemption in ``_EXEMPT`` above.

    **The bar this test must meet**: a NEW hand-rolled presence check
    added anywhere else in the surface fails this test WITHOUT anyone
    updating a list -- the scan finds the pattern, not a positive
    enumeration of sites. ``_EXEMPT`` only widens for a deliberate,
    reviewed, R-007-justified reason (recorded inline), never to silence
    an unexplained new site.
    """
    found = _scan_raw_charter_existence_checks()
    offenders = [
        f"{c.module}::{c.qualname} -> {c.check_text}"
        for c in found
        if (c.module, c.qualname) not in _EXEMPT
    ]
    assert not offenders, (
        "Found a charter.md/charter.yaml existence check outside the "
        "canonical seam (charter.bundle.charter_yaml_present) that is not "
        "in the reasoned exemption table:\n  "
        + "\n  ".join(offenders)
        + "\nRoute the site through charter_yaml_present(), or add an "
        "R-007-reasoned exemption entry to _EXEMPT if it genuinely "
        "degrades content rather than gating a presence answer."
    )


def test_seam_exemption_table_is_exactly_pinned() -> None:
    """Growth-visibility pin: the exemption table's SIZE is fixed at 15.

    Widening this table is legitimate -- T019 made one such call (site
    6/sync.py), strengthening this scan's own local-variable resolution
    surfaced five more genuine non-resolvers, and widening ``_SCAN_ROOTS``
    to the whole ``src/`` tree in WP04 cycle 2 surfaced four further
    genuine non-resolvers that cycle 1's three-path root list never
    reached (see the comments in ``_EXEMPT`` above) -- but any change must
    be a deliberate, reviewed diff to this number and the reasoning
    comments, never a silent widening to dodge a red
    ``test_no_unrouted_charter_presence_checks...`` run.
    """
    # golden-count: cardinality-is-contract -- the exemption set's SIZE is the
    # guarantee (NFR-001/SC-007): a member added or removed must be a deliberate,
    # reviewed act, so the number is the assertion, not an incidental count.
    assert len(_EXEMPT) == 15, (  # golden-count: cardinality-is-contract
        f"_EXEMPT changed size to {len(_EXEMPT)} entries. If this is a "
        "deliberate, reviewed R-007 reclassification, update this pin AND "
        "the reasoning comments above in the same diff; do not just widen "
        "the count."
    )


class _SeamCallFinder(ast.NodeVisitor):
    """Find every direct call to ``charter_yaml_present`` in a module."""

    def __init__(self, module_rel: str, out: set[tuple[str, str]]) -> None:
        self._module = module_rel
        self._stack: list[str] = []
        self._out = out

    def _qualname(self) -> str:
        return ".".join(self._stack) if self._stack else "<module>"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._stack.append(node.name)
        self.generic_visit(node)
        self._stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name == "charter_yaml_present":
            self._out.add((self._module, self._qualname()))
        self.generic_visit(node)


def _scan_direct_seam_call_sites() -> set[tuple[str, str]]:
    sites: set[tuple[str, str]] = set()
    for path in _iter_surface_files():
        module_rel = path.relative_to(_REPO_ROOT).as_posix()
        if module_rel == "src/charter/bundle.py":
            continue  # the seam's own definition, not a "caller"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=module_rel)
        _SeamCallFinder(module_rel, sites).visit(tree)
    return sites


def test_direct_seam_adoption_count_is_pinned() -> None:
    """SC-003 output pin: how many sites now call the canonical seam directly.

    charter-preflight-remediation (WP04): this is the scan's OUTPUT, not
    its input -- it is derived by walking the same AST surface as the
    census above, not by hand-listing the 8 sites and asserting against
    that list.

    8 direct ``charter_yaml_present()`` call sites (R-003 sites 2, 3, 4,
    7, 8, 9, 10, plus ``specify_cli.dashboard.charter_path.
    resolve_project_charter_path`` -- the WP04 cycle-2 finding: a real,
    live, operator-reachable resolver R-003's original census missed
    entirely, discovered only once ``_SCAN_ROOTS`` widened to the whole
    ``src/`` tree). The mission's remaining 2 operator-reachable resolvers
    converge WITHOUT their own direct call:

    * site 1 (the freshness gate, computer.py) is the convergence TARGET
      this mission converges everything else onto -- it predates the
      wrapper and is not required to call it (WP04 prompt).
    * site 5 (``_status_collectors.py::_collect_charter_sync_status``)
      converges TRANSITIVELY: it calls ``_resolve_charter_path`` (site 3),
      which is itself gated by the seam -- reaching past that call
      already proves ``charter.yaml`` exists (see the inline T018 comment
      at the call site; also see this module's ``_EXEMPT`` entry for the
      same function, which documents why its OWN former raw check was
      removed rather than converted to a second, redundant seam call).

    8 direct + 1 (gate, native match) + 1 (transitive) = 10 -- the R-003 /
    R-007 pinned operator-reachable count (9 -> 10 after the WP04 cycle-2
    dashboard-resolver discovery, itself following the 10 -> 9 site-6
    exclusion from cycle 1).
    """
    sites = _scan_direct_seam_call_sites()
    # golden-count: cardinality-is-contract -- SC-003 pins the resolver census;
    # the count moving is exactly the drift this test exists to make loud.
    assert len(sites) == 8, (  # golden-count: cardinality-is-contract
        f"Expected 8 direct charter_yaml_present() call sites, found "
        f"{len(sites)}: {sorted(sites)}. If a resolver was added or "
        "removed, update this count AND the reasoning in this test's "
        "docstring deliberately -- do not just change the number."
    )


# ---------------------------------------------------------------------------
# T023 -- one answer across all four fixture shapes, and a non-mutating seam
# ---------------------------------------------------------------------------

_CHARTER_MD_BODY = (
    "# Project Charter\n\n"
    "## Policy Summary\n\n"
    "- Intent: deterministic delivery\n\n"
    "## Regression Vigilance\n\n"
    "Consult docs/context before approving a terminology cutover.\n"
)

_CHARTER_YAML_VALID_BODY = "schema_version: '2.0.0'\n"
_CHARTER_YAML_INVALID_BODY = "not: [valid: yaml: at: all"

_SECTION_SELECTOR = "section:regression-vigilance"


def _f1_no_charter(repo_root: Path) -> Path:
    """F1 -- no charter at all (never initialised)."""
    return repo_root


def _f2_legacy_bundle_without_charter_yaml(repo_root: Path) -> Path:
    """F2 -- legacy bundle, no charter.yaml (the mission's trigger state)."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "charter.md").write_text(_CHARTER_MD_BODY, encoding="utf-8")
    (charter_dir / "governance.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    (charter_dir / "directives.yaml").write_text("schema_version: '1'\n", encoding="utf-8")
    (charter_dir / "metadata.yaml").write_text(
        "charter_hash: sha256:" + "0" * 64 + "\ntimestamp_utc: 2026-01-01T00:00:00+00:00\n",
        encoding="utf-8",
    )
    return repo_root


def _f3_charter_yaml_valid(repo_root: Path) -> Path:
    """F3 -- charter.yaml present and valid."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "charter.md").write_text(_CHARTER_MD_BODY, encoding="utf-8")
    (charter_dir / "charter.yaml").write_text(_CHARTER_YAML_VALID_BODY, encoding="utf-8")
    return repo_root


def _f4_charter_yaml_invalid(repo_root: Path) -> Path:
    """F4 -- charter.yaml present, unparseable."""
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "charter.md").write_text(_CHARTER_MD_BODY, encoding="utf-8")
    (charter_dir / "charter.yaml").write_text(_CHARTER_YAML_INVALID_BODY, encoding="utf-8")
    return repo_root


def _gate_present(repo_root: Path) -> bool:
    """The freshness gate's own presence answer (R-003 site 1)."""
    return compute_freshness(repo_root).charter_source.state != "missing"


def _resolve_charter_path_present(repo_root: Path) -> bool:
    """R-003 site 3, normalised to a boolean (it raises rather than returns)."""
    try:
        _resolve_charter_path(repo_root)
    except TaskCliError:
        return False
    return True


def _include_reports_present(repo_root: Path) -> bool:
    """R-003 site 10, normalised to a boolean (it raises rather than returns).

    Distinguishes "no charter" (raises before rendering) from "charter
    section not found" (a content question, not a presence one) by
    matching the presence-specific message.
    """
    try:
        build_charter_context_include(repo_root, _SECTION_SELECTOR)
    except ValueError as exc:
        return "No charter found" not in str(exc)
    return True


@pytest.mark.parametrize(
    "build_fixture",
    [_f1_no_charter, _f2_legacy_bundle_without_charter_yaml, _f3_charter_yaml_valid, _f4_charter_yaml_invalid],
    ids=["F1-no-charter", "F2-legacy-bundle", "F3-charter-yaml-valid", "F4-charter-yaml-invalid"],
)
def test_all_surfaces_agree_on_presence(build_fixture, tmp_path: Path) -> None:
    """T023 -- every operator-reachable surface answers the SAME presence
    question the gate does, for all four fixture shapes.

    F2 is the regression test for User Story 2 (WP04 prompt): before this
    WP, the diagnostics reported "present" for F2 (keying off charter.md)
    while the gate reported "missing" (keying off charter.yaml). After
    this WP, every surface below agrees with the gate on F2 too.
    """
    repo_root = build_fixture(tmp_path)

    gate = _gate_present(repo_root)
    seam = charter_yaml_present(repo_root)
    resolve_path = _resolve_charter_path_present(repo_root)
    json_block_present = _project_charter_json_block(repo_root)["present"]
    include_present = _include_reports_present(repo_root)

    assert seam == gate, f"seam disagrees with gate: seam={seam} gate={gate}"
    assert resolve_path == gate, f"_resolve_charter_path disagrees with gate: {resolve_path} != {gate}"
    assert json_block_present == gate, (
        f"_project_charter_json_block disagrees with gate: {json_block_present} != {gate}"
    )
    assert include_present == gate, (
        f"build_charter_context_include disagrees with gate: {include_present} != {gate}"
    )

    # build_charter_context (site 2): F4 is deliberately excluded here. An
    # unparseable charter.yaml surfaces a genuinely pre-existing, unrelated
    # defect in doctrine.spdd_reasons.activation (it re-reads charter.yaml
    # with no parse-error handling, downstream of the bootstrap render this
    # call reaches once presence agrees charter.yaml exists) -- reproduced
    # identically on the pre-WP04 baseline (verified via `git stash`), so
    # it is out of this WP's surface (locality of change) and is reported
    # separately in the handoff, not folded into this parity test.
    if build_fixture is not _f4_charter_yaml_invalid:
        result = build_charter_context(repo_root, action="implement", mark_loaded=False)
        assert (result.mode != "missing") == gate, (
            f"build_charter_context disagrees with gate: mode={result.mode!r} gate={gate}"
        )


def test_seam_is_non_mutating(tmp_path_factory: pytest.TempPathFactory) -> None:
    """T023 -- a presence query leaves the fixture byte-identical.

    Snapshots the fixture directory before and after querying every
    presence surface, across all four shapes, and asserts nothing changed.
    """

    def _snapshot(root: Path) -> dict[str, str]:
        # File-integrity mutation check, not a charter content hash -- the
        # repo-wide TID251 ban targets reimplementing charter.hasher's
        # content-hash recipe; this is a directory-snapshot equality check.
        return {
            str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()  # noqa: TID251
            for p in sorted(root.rglob("*"))
            if p.is_file()
        }

    for build_fixture in (
        _f1_no_charter,
        _f2_legacy_bundle_without_charter_yaml,
        _f3_charter_yaml_valid,
        _f4_charter_yaml_invalid,
    ):
        repo_root = build_fixture(tmp_path_factory.mktemp(build_fixture.__name__))
        subprocess.run(["git", "init", "--quiet", str(repo_root)], check=True)

        before = _snapshot(repo_root)
        charter_yaml_present(repo_root)
        _project_charter_json_block(repo_root)
        with contextlib.suppress(ValueError):
            build_charter_context_include(repo_root, _SECTION_SELECTOR)
        after = _snapshot(repo_root)

        assert before == after, (
            f"Presence query mutated the fixture for {build_fixture.__name__}: "
            f"before={before} after={after}"
        )
