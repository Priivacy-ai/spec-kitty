"""Resolution-authority gates: canonicalizer + coord-authority discriminators.

Mission ``single-authority-resolution-gates-01KW1P0F`` / WP01.
Requirements: FR-003, FR-004, NFR-001, NFR-002, NFR-003, NFR-004.

This module is the **single home** for two AST discriminators that make the two
architectural resolution boundaries structural (CI-red on regression):

1. **Canonicalizer gate** (FR-004 / IC-02) — every call to
   :func:`primary_feature_dir_for_mission` must pass a handle that is *provably*
   canonical by **intra-function def-use** (assigned from
   ``_canonicalize_primary_read_handle`` or read from a known-canonical
   ``feature_dir.name`` *in the same function*) — NOT a name-substring heuristic
   — OR be sanctioned in the allowlist with a rationale.

2. **Coord-authority gate** (FR-003 / IC-03) — every mission-artifact **write**
   that resolves its target via the kind-blind
   :func:`resolve_feature_dir_for_mission` must route through the kind-aware
   authority (``commit_for_mission(kind=)`` / ``resolve_planning_read_dir(kind=)``)
   or be allowlisted as a legitimate coord-owned write.

Shared machinery (IC-01, NFR-001/002/003):

* Composite key ``(enclosing_qualname, token_line)`` computed **live** from
  source — survives benign line drift, unlike a raw ``file:line`` key.
* Concrete integer floors (canonicalizer ``>= 45``; coord-authority a hard-coded
  literal ``>= 13``) so a broken scanner returning zero rows cannot pass
  vacuously (NFR-002 rejects ``> 0`` / ``>= 1``).
* Shrink-only governance: a staleness twin-guard fails the build on any
  allowlist entry that no longer matches a live call site, and a baseline scalar
  prevents post-seed inflation (NFR-003).

NFR-004 — both scanners run in the fast ``tests/architectural/`` tier. Parsed
ASTs and per-file parent maps are cached module-wide (``_parsed_trees``), so the
many tests that re-scan the real tree share one parse pass; a single cold scan is
~2 s and warm re-scans are sub-second, keeping the whole module well under the
30 s ceiling on the full ``src/`` tree.

Reference precedents (structural shape only — keys are NET-NEW here):
``tests/architectural/surface_resolution_audit/audit.py`` (raw ``rel:line`` key)
and ``test_protection_resolver_call_sites.py`` (bare-module frozenset). The
``(enclosing_qualname, token_line)`` composite key required by NFR-001 is absent
from both and is implemented here from scratch (AST ancestor traversal).
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architectural

# --------------------------------------------------------------------------- #
# Source-tree roots (repo-root independent).
# this file: <root>/tests/architectural/test_resolution_authority_gates.py
# --------------------------------------------------------------------------- #
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
SRC_ROOT = _REPO_ROOT / "src"
ALLOWLIST_PATH = _THIS.parent / "resolution_gate_allowlist.yaml"

# Call targets the two discriminators scan for.
CANONICALIZER_PRIMITIVE = "primary_feature_dir_for_mission"
COORD_BLIND_RESOLVER = "resolve_feature_dir_for_mission"

# The canonical fold the handle arg must flow from (intra-function def-use).
CANONICAL_FOLD_SEAM = "_canonicalize_primary_read_handle"
# T031/FR-011: the bare-human-slug fold seam — handle provably composed after
# assignment from this function (``_canonicalize_bare_modern_handle``).
BARE_MODERN_FOLD_SEAM = "_canonicalize_bare_modern_handle"

# The kind-aware authorities a flagged coord write must route through instead.
COORD_KIND_AWARE_AUTHORITY = "commit_for_mission(kind=) / resolve_planning_read_dir(kind=)"

# Concrete integer floors (NFR-002). These are the live census counts measured
# on the current ``src/`` tree, NOT ``> 0`` placeholders. If the scanners are
# correct and the tree grows, raise these to the new honest census.
#
# coord-read-residuals WP01 (FR-010 floor honesty): the #2186 identity routing
# added SEVEN new DIRECT ``primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))``
# anchors (NOT the ``resolve_planning_read_dir`` seam — so the census DOES move):
#   1. next_cmd._pair_previous_lifecycle_record
#   2. next_cmd._write_issuance_lifecycle_record
#   3. next_cmd._handle_answer_flow
#   4. implement.implement (json-output identity, was :1394)
#   5. workflow sparse-checkout preflight (was :1282)
#   6. workflow get_mission_type leg (own anchor, was :1644)
#   7. workflow review-prompt metadata (was :2739)
# Census: total 38 → 45, routed 35 → 42 (measured before/after on the merged base).
CANONICALIZER_FLOOR = 45
# WP07 re-pin: WP06 routing reduced the live write-classified coord census from 17 to 14;
# 3 sites were removed (list_dependents, review at one former line, one list_tasks variant).
# REBASE (2026-06-27): concurrent mission #1057 inserted a check_pre30_layout boundary
# guard into list_dependents, re-introducing a kind-blind resolve probe there; the honest
# merged-tree live write census is now 15 (the 14 prior + #1057's list_dependents probe).
# coord-read-residuals WP01 (2026-06-27): the #2186 identity routing converted two
# coord-aware resolve_feature_dir_for_mission write-census sites (workflow.py preflight
# `implement` + `review` review-prompt) to the PRIMARY anchor, shrinking the live write
# census 15 -> 13 (a genuine routing shrink, not a re-pin).
# retire-standalone-tasks-cli WP04 (FR-001/FR-007): deleting the standalone
# scripts/tasks surface removed its sole write-census site (tasks_cli.py
# `_prepare_merge_metadata`) and its allowlist entry, shrinking the live write
# census 13 -> 12 (a deletion-driven shrink, not a re-pin).
COORD_AUTHORITY_WRITE_FLOOR = 12

# WP07 / SC-004 — routed-count floor (the anti-mass-allowlist machine guard).
# The number of canonicalizer call sites that are *routed* (def-use-canonical,
# i.e. NOT relying on an allowlist sanction) must stay at or above the SC-004
# census of genuinely-bare sites that WP02-WP07 routed. After T031 teaches the
# discriminator the bare-modern fold, 4 formerly-allowlisted sites auto-route:
# live routed count is 35 (38 total sites minus the 3 permanent sanctions).
# Floor = 35 − MARGIN(4) = 31. Both bounds are asserted in test_routed_count_floor:
#   live − MARGIN <= floor < live  (lower: prevents loose ratchet; upper: anti-vacuous).
# The floor is the concrete census integer, NOT ``len(scanned)`` — a tautological
# ``>= len(routed)`` would pass under mass-allowlisting, which is exactly what
# this guard exists to catch.
ROUTED_CANONICALIZER_FLOOR_MARGIN = 4
# WP07 recomputed: post-T031 live routed = 35; floor = 35 − MARGIN(4) = 31.
# coord-read-residuals WP01 (FR-010): the 7 new identity anchors routed through the
# DIRECT primitive (not the seam) raised the live routed census 35 → 42; floor
# recomputed 42 − MARGIN(4) = 38. This is a REAL gain (not a re-pinned integer):
# 7 identity reads that previously resolved off coord-aware resolvers now provably
# anchor on PRIMARY via the canonical fold, and the gate counts them.
ROUTED_CANONICALIZER_FLOOR = 38


# --------------------------------------------------------------------------- #
# IC-01 — composite-key allowlist machinery (NET-NEW, NFR-001).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GateAllowlistKey:
    """Composite allowlist key surviving benign line drift (NFR-001).

    ``enclosing_qualname`` is the dotted chain of enclosing ``def`` / ``class``
    names (e.g. ``MissionStatus._find_meta_path``), or ``"<module>"`` for a call
    at file scope. ``token_line`` is the 1-based line of the call token. The pair
    is hashable and equality-comparable, so it doubles as the serialization key.
    """

    enclosing_qualname: str
    token_line: int


class AllowlistEntryError(ValueError):
    """Raised when a YAML allowlist entry is malformed (missing rationale)."""


def _require_str(mapping: dict[str, object], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AllowlistEntryError(
            f"allowlist entry {context} is missing a non-empty {key!r} field "
            f"(got {value!r}); every entry needs an explicit rationale — no silent drift"
        )
    return value


def load_allowlist(path: Path) -> dict[str, list[GateAllowlistKey]]:
    """Load the governance YAML into ``{gate_name: [GateAllowlistKey, ...]}``.

    The YAML groups entries by gate name (``"canonicalizer"`` / ``"coord_authority"``);
    each entry carries ``qualname:``, ``line:`` and a **mandatory** ``rationale:``.
    An entry missing or carrying an empty ``rationale`` raises
    :class:`AllowlistEntryError` — the loader refuses to silently accept drift.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, list[GateAllowlistKey]] = {}
    for gate_name in ("canonicalizer", "coord_authority"):
        entries = raw.get(gate_name) or []
        keys: list[GateAllowlistKey] = []
        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise AllowlistEntryError(
                    f"{gate_name}[{idx}] is not a mapping (got {entry!r})"
                )
            context = f"{gate_name}[{idx}]"
            qualname = _require_str(entry, "qualname", context)
            _require_str(entry, "rationale", context)
            line = entry.get("line")
            if not isinstance(line, int):
                raise AllowlistEntryError(
                    f"{context} ({qualname!r}) has a non-integer line {line!r}"
                )
            keys.append(GateAllowlistKey(qualname, line))
        out[gate_name] = keys
    return out


def load_baseline(path: Path, gate_name: str) -> int:
    """Return the recorded pre-sweep baseline scalar for *gate_name*."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    value = raw.get(f"{gate_name}_baseline")
    if not isinstance(value, int):
        raise AllowlistEntryError(
            f"{gate_name}_baseline scalar missing or non-integer in {path.name}"
        )
    return value


# --------------------------------------------------------------------------- #
# AST ancestor traversal — derive the composite key live from source.
# --------------------------------------------------------------------------- #
def _parent_map(tree: ast.Module) -> dict[int, ast.AST]:
    """Map ``id(child) -> parent`` for every node in *tree* (single pass)."""
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _qualname_from_parents(parents: dict[int, ast.AST], target: ast.AST) -> str:
    """Dotted enclosing ``def``/``class`` chain, or ``"<module>"`` at file scope.

    Nested functions yield a dotted chain (``outer.inner``); a lambda contributes
    ``<lambda>`` per Python's ``__qualname__`` convention.
    """
    chain: list[str] = []
    cur: ast.AST | None = target
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            chain.append(cur.name)
        elif isinstance(cur, ast.Lambda):
            chain.append("<lambda>")
    return ".".join(reversed(chain)) if chain else "<module>"


def derive_live_key(node: ast.expr | ast.stmt, tree: ast.Module) -> GateAllowlistKey:
    """Composite ``(enclosing_qualname, token_line)`` for *node* within *tree*.

    Convenience wrapper that rebuilds the parent map per call. The bulk scanners
    build the map once and call :func:`_qualname_from_parents` directly. *node*
    must be a positioned node (``ast.expr`` / ``ast.stmt`` carry ``lineno``).
    """
    parents = _parent_map(tree)
    return GateAllowlistKey(_qualname_from_parents(parents, node), node.lineno)


def _enclosing_function(
    parents: dict[int, ast.AST], target: ast.AST
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the DIRECT enclosing ``ast.FunctionDef`` of *target*, or ``None``."""
    cur: ast.AST | None = target
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


def staleness_twin_guard(
    allowlist_keys: set[GateAllowlistKey], live_keys: set[GateAllowlistKey]
) -> list[GateAllowlistKey]:
    """Return allowlist keys with no matching live call site (NFR-003).

    A non-empty result is a stale-entry failure: the allowlist sanctions a site
    that no longer exists, so it must be removed (shrink-only governance).
    """
    return sorted(
        allowlist_keys - live_keys, key=lambda k: (k.enclosing_qualname, k.token_line)
    )


# --------------------------------------------------------------------------- #
# Shared file iteration (parse each file at most once — NFR-004).
# --------------------------------------------------------------------------- #
def _iter_source_files(src_root: Path) -> list[Path]:
    return [
        p
        for p in sorted(src_root.rglob("*.py"))
        if "__pycache__" not in p.parts
    ]


# Module-wide cache of parsed (tree, parent_map) per file, keyed by resolved
# src root. The many tests that re-scan the real tree share one parse pass
# (NFR-004). Scratch ``tmp_path`` trees get distinct keys and are not retained
# across test functions in any way that affects the real-tree gates.
_parsed_trees: dict[str, list[tuple[str, ast.Module, dict[int, ast.AST]]]] = {}


def _parsed_source(src_root: Path) -> list[tuple[str, ast.Module, dict[int, ast.AST]]]:
    """Return ``[(rel_path, tree, parent_map), ...]`` for *src_root*, cached."""
    cache_key = str(src_root.resolve())
    cached = _parsed_trees.get(cache_key)
    if cached is not None:
        return cached
    parsed: list[tuple[str, ast.Module, dict[int, ast.AST]]] = []
    for path in _iter_source_files(src_root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        parsed.append((_rel(path), tree, _parent_map(tree)))
    _parsed_trees[cache_key] = parsed
    return parsed


def _callee_name(call: ast.Call) -> str | None:
    """Return the callee identifier for bare-name OR attribute call forms."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _rel(path: Path) -> str:
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


# --------------------------------------------------------------------------- #
# T002 — canonicalizer def-use discriminator (FR-004 / IC-02).
# --------------------------------------------------------------------------- #
def _canonicalizer_handle_arg(call: ast.Call) -> ast.expr | None:
    """The handle (slug) argument of a ``primary_feature_dir_for_mission`` call.

    Positional form: ``primary_feature_dir_for_mission(repo_root, handle)`` — the
    handle is ``args[1]``. Keyword form (e.g. ``tasks.py``): a ``mission_slug=`` /
    ``feature_dir_name=`` / ``dir_name=`` / ``handle=`` kwarg.
    """
    if len(call.args) >= 2:
        return call.args[1]
    for kw in call.keywords:
        if kw.arg in ("mission_slug", "feature_dir_name", "dir_name", "handle"):
            return kw.value
    return None


def _names_assigned_from_fold(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    """Local names assigned from a canonical fold seam call.

    Recognizes both the primary-read fold (``_canonicalize_primary_read_handle``)
    and the bare-modern fold (``_canonicalize_bare_modern_handle`` — T031/FR-011):
    a handle assigned from either seam is provably composed and qualifies as
    intra-function def-use canonical.

    Intra-function only: ``ast.walk`` stays within the SAME function body, so a
    ``canonical`` variable assigned in a *caller's* scope never canonicalizes a
    callee's raw-handle call (FR-004 def-use is intra-function).
    """
    out: set[str] = set()
    for node in ast.walk(fn):
        value: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value, targets = node.value, list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value, targets = node.value, [node.target]
        if isinstance(value, ast.Call) and _callee_name(value) in (
            CANONICAL_FOLD_SEAM,
            BARE_MODERN_FOLD_SEAM,
        ):
            for tgt in targets:
                if isinstance(tgt, ast.Name):
                    out.add(tgt.id)
    return out


def is_def_use_canonical(
    handle_arg: ast.expr | None,
    enclosing_fn: ast.FunctionDef | ast.AsyncFunctionDef | None,
) -> bool:
    """True when *handle_arg* is provably canonical by intra-function def-use.

    Canonical iff the handle is (a) a direct ``_canonicalize_primary_read_handle``
    call, (b) a ``<x>.name`` attribute read (a resolver-returned ``Path.name`` —
    already a composed dir name), or (c) a local name assigned from the fold seam
    earlier in the SAME function. Everything else is a violation (no
    name-substring heuristic — a variable literally named ``canonical`` that was
    never folded is NOT trusted).
    """
    if handle_arg is None or enclosing_fn is None:
        return False
    if isinstance(handle_arg, ast.Call) and _callee_name(handle_arg) == CANONICAL_FOLD_SEAM:
        return True
    if isinstance(handle_arg, ast.Attribute) and handle_arg.attr == "name":
        return True
    if isinstance(handle_arg, ast.Name):
        return handle_arg.id in _names_assigned_from_fold(enclosing_fn)
    return False


@dataclass(frozen=True)
class CanonicalizerSite:
    """One discovered ``primary_feature_dir_for_mission`` call site."""

    rel_path: str
    key: GateAllowlistKey
    is_canonical: bool


def scan_canonicalizer_call_sites(src_root: Path) -> list[CanonicalizerSite]:
    """AST-walk ``src/**/*.py`` for every ``primary_feature_dir_for_mission`` call.

    Handles bare-name and attribute call forms; classifies each by intra-function
    def-use. Method calls whose callee is a dotted attribute of a *different*
    object (``self.resolver.primary_feature_dir_for_mission(...)``) still match by
    attribute name — that is intentional: the primitive is the call target
    regardless of how it is reached.
    """
    sites: list[CanonicalizerSite] = []
    for rel, tree, parents in _parsed_source(src_root):
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _callee_name(node) != CANONICALIZER_PRIMITIVE:
                continue
            qualname = _qualname_from_parents(parents, node)
            fn = _enclosing_function(parents, node)
            arg = _canonicalizer_handle_arg(node)
            sites.append(
                CanonicalizerSite(
                    rel_path=rel,
                    key=GateAllowlistKey(qualname, node.lineno),
                    is_canonical=is_def_use_canonical(arg, fn),
                )
            )
    return sites


def check_canonicalizer_gate(
    src_root: Path, allowlist: set[GateAllowlistKey]
) -> list[str]:
    """Return violation strings for non-canonical, non-allowlisted call sites.

    Each violation names ``file:qualname:line`` and the sanctioned seam
    (``_canonicalize_primary_read_handle``) the developer must route through.
    """
    violations: list[str] = []
    for site in scan_canonicalizer_call_sites(src_root):
        if site.is_canonical or site.key in allowlist:
            continue
        violations.append(
            f"{site.rel_path}:{site.key.enclosing_qualname}:{site.key.token_line} "
            f"passes a non-canonical handle to {CANONICALIZER_PRIMITIVE} — route it "
            f"through {CANONICAL_FOLD_SEAM} (the canonical read fold) or allowlist "
            f"it with an already-canonical rationale"
        )
    return sorted(violations)


# --------------------------------------------------------------------------- #
# T003 — coord-authority write-vs-read discriminator (FR-003 / IC-03).
# --------------------------------------------------------------------------- #
# WRITE PREDICATE (documented per IC-03): a ``resolve_feature_dir_for_mission``
# call site is classified a WRITE when the SAME enclosing function also contains
# at least one call whose callee is a write indicator — i.e. it mutates the
# filesystem at the resolved dir. The indicator set below is the explicit
# predicate; there is no name proxy for "write", so it is enumerated. A call to
# ``open(...)`` counts as a write only when a mode argument contains ``w``/``a``/
# ``x`` (mode ``"r"`` is a read and is NOT flagged). Any ``commit*`` call counts.
#
# This is deliberately conservative-broad at the FUNCTION granularity (Phase 1
# does not trace the resolved dir through local-variable assignments); the
# allowlist sanctions the legitimate ambiguous cases.
_WRITE_INDICATOR_NAMES: frozenset[str] = frozenset(
    {
        "write_text",
        "write_bytes",
        "mkdir",
        "makedirs",
        "rename",
        "replace",
        "unlink",
        "touch",
        "dump",
        "dumps",
        "copy",
        "copy2",
        "copyfile",
        "move",
        "rmtree",
    }
)

# Coord-owned write helpers that RETURN the resolved dir to a caller which then
# writes it (the write indicator lives in the caller, not the same function).
# These are legitimate kind-blind coord-owned writes by design (IC-03): the coord
# status authority is at the CALLER level, not the commit level. They are
# classified WRITE-by-design here so the allowlist sanction is meaningful and
# tested, rather than silently passing as a "read".
_COORD_WRITE_BY_DESIGN: frozenset[str] = frozenset(
    {
        "src/specify_cli/decisions/emit.py",
        "src/specify_cli/widen/state.py",
    }
)


def _is_write_indicator_call(call: ast.Call) -> bool:
    name = _callee_name(call)
    if name is None:
        return False
    if name in _WRITE_INDICATOR_NAMES or name.startswith("commit"):
        return True
    if name == "open":
        return _open_is_write(call)
    return False


def _open_is_write(call: ast.Call) -> bool:
    """True when an ``open(...)`` call carries a write mode (``w``/``a``/``x``)."""
    mode_candidates: list[ast.expr] = list(call.args[1:])
    mode_candidates.extend(kw.value for kw in call.keywords if kw.arg == "mode")
    for cand in mode_candidates:
        if (
            isinstance(cand, ast.Constant)
            and isinstance(cand.value, str)
            and any(flag in cand.value for flag in ("w", "a", "x", "+"))
        ):
            return True
    return False


def _function_has_write_indicator(
    fn: ast.FunctionDef | ast.AsyncFunctionDef | None,
) -> bool:
    if fn is None:
        return False
    return any(
        isinstance(node, ast.Call) and _is_write_indicator_call(node)
        for node in ast.walk(fn)
    )


@dataclass(frozen=True)
class CoordAuthoritySite:
    """One discovered ``resolve_feature_dir_for_mission`` call site."""

    rel_path: str
    key: GateAllowlistKey
    is_write: bool


def scan_coord_authority_call_sites(src_root: Path) -> list[CoordAuthoritySite]:
    """AST-walk ``src/**/*.py`` for every ``resolve_feature_dir_for_mission`` call.

    The ``is_write`` flag applies the documented write predicate: the enclosing
    function contains a write indicator, OR the call site lives in a
    coord-owned-write-by-design module (``decisions/emit.py`` / ``widen/state.py``).
    """
    sites: list[CoordAuthoritySite] = []
    for rel, tree, parents in _parsed_source(src_root):
        by_design = rel in _COORD_WRITE_BY_DESIGN
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _callee_name(node) != COORD_BLIND_RESOLVER:
                continue
            qualname = _qualname_from_parents(parents, node)
            fn = _enclosing_function(parents, node)
            is_write = by_design or _function_has_write_indicator(fn)
            sites.append(
                CoordAuthoritySite(
                    rel_path=rel,
                    key=GateAllowlistKey(qualname, node.lineno),
                    is_write=is_write,
                )
            )
    return sites


def check_coord_authority_gate(
    src_root: Path, allowlist: set[GateAllowlistKey]
) -> list[str]:
    """Return violation strings for unsanctioned mission-artifact write sites.

    A write-classified call to the kind-blind ``resolve_feature_dir_for_mission``
    that is not allowlisted is a violation; each names ``file:qualname:line`` and
    the kind-aware authority to use instead.
    """
    violations: list[str] = []
    for site in scan_coord_authority_call_sites(src_root):
        if not site.is_write or site.key in allowlist:
            continue
        violations.append(
            f"{site.rel_path}:{site.key.enclosing_qualname}:{site.key.token_line} "
            f"resolves a mission-artifact WRITE target via the kind-blind "
            f"{COORD_BLIND_RESOLVER} — route it through {COORD_KIND_AWARE_AUTHORITY} "
            f"or allowlist it as a legitimate coord-owned write"
        )
    return sorted(violations)


# --------------------------------------------------------------------------- #
# Live key sets (for the staleness twin-guard).
# --------------------------------------------------------------------------- #
def _live_canonicalizer_keys(src_root: Path) -> set[GateAllowlistKey]:
    return {site.key for site in scan_canonicalizer_call_sites(src_root)}


def _live_coord_authority_keys(src_root: Path) -> set[GateAllowlistKey]:
    return {site.key for site in scan_coord_authority_call_sites(src_root)}


# =========================================================================== #
# TESTS
# =========================================================================== #


# --- T001: composite-key machinery -----------------------------------------
def test_allowlist_key_is_hashable_and_value_keyed() -> None:
    """``GateAllowlistKey`` compares/hashes by the ``(qualname, line)`` pair."""
    a = GateAllowlistKey("MarkStatusCmd.run", 100)
    b = GateAllowlistKey("MarkStatusCmd.run", 100)
    c = GateAllowlistKey("MarkStatusCmd.run", 101)
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert {a, b} == {a}


def test_loader_rejects_entry_without_rationale(tmp_path: Path) -> None:
    """The loader fails closed on a missing/empty ``rationale`` (no silent drift)."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "canonicalizer:\n  - qualname: foo.bar\n    line: 10\n", encoding="utf-8"
    )
    with pytest.raises(AllowlistEntryError, match="rationale"):
        load_allowlist(bad)

    empty_rationale = tmp_path / "empty.yaml"
    empty_rationale.write_text(
        "canonicalizer:\n  - qualname: foo.bar\n    line: 10\n    rationale: '  '\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="rationale"):
        load_allowlist(empty_rationale)


def test_derive_live_key_module_scope() -> None:
    """A call at file scope derives ``"<module>"`` as the enclosing qualname."""
    tree = ast.parse("primary_feature_dir_for_mission(repo, slug)\n")
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    key = derive_live_key(call, tree)
    assert key.enclosing_qualname == "<module>"
    assert key.token_line == 1


def test_derive_live_key_nested_function_chain() -> None:
    """Nested functions and class methods produce a dotted qualname chain."""
    src = (
        "class A:\n"
        "    def run(self):\n"
        "        def inner():\n"
        "            primary_feature_dir_for_mission(r, s)\n"
        "        return inner\n"
    )
    tree = ast.parse(src)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    key = derive_live_key(call, tree)
    assert key.enclosing_qualname == "A.run.inner"


def test_derive_live_key_distinguishes_same_method_name_in_two_classes() -> None:
    """A method named ``run`` in two classes derives distinct qualnames."""
    src = (
        "class A:\n"
        "    def run(self):\n"
        "        primary_feature_dir_for_mission(r, s)\n"
        "class B:\n"
        "    def run(self):\n"
        "        primary_feature_dir_for_mission(r, s)\n"
    )
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    keys = {derive_live_key(c, tree).enclosing_qualname for c in calls}
    assert keys == {"A.run", "B.run"}


def test_staleness_twin_guard_empty_when_all_live() -> None:
    """The twin-guard returns ``[]`` when every allowlist key is live."""
    live = {GateAllowlistKey("a.b", 1), GateAllowlistKey("c.d", 2)}
    assert staleness_twin_guard({GateAllowlistKey("a.b", 1)}, live) == []


def test_staleness_twin_guard_flags_stale_entry() -> None:
    """The twin-guard returns the allowlist keys with no live match."""
    live = {GateAllowlistKey("a.b", 1)}
    stale = staleness_twin_guard({GateAllowlistKey("nonexistent", 99999)}, live)
    assert stale == [GateAllowlistKey("nonexistent", 99999)]


# --- T002: canonicalizer discriminator (unit) ------------------------------
def _single_call(src: str) -> tuple[ast.Call, ast.FunctionDef | ast.AsyncFunctionDef | None]:
    tree = ast.parse(src)
    parents = _parent_map(tree)
    call = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _callee_name(n) == CANONICALIZER_PRIMITIVE
    )
    return call, _enclosing_function(parents, call)


def test_canonicalizer_flags_raw_handle() -> None:
    """A raw, never-folded handle is classified a violation."""
    call, fn = _single_call(
        "def f(repo, raw_slug):\n"
        "    return primary_feature_dir_for_mission(repo, raw_slug)\n"
    )
    assert is_def_use_canonical(_canonicalizer_handle_arg(call), fn) is False


def test_canonicalizer_accepts_fold_assigned_handle() -> None:
    """A handle assigned from the fold seam earlier in the same fn is canonical."""
    call, fn = _single_call(
        "def f(repo, handle):\n"
        "    canon = _canonicalize_primary_read_handle(repo, handle)\n"
        "    return primary_feature_dir_for_mission(repo, canon)\n"
    )
    assert is_def_use_canonical(_canonicalizer_handle_arg(call), fn) is True


def test_canonicalizer_accepts_dir_name_attribute() -> None:
    """``feature_dir.name`` as the handle is canonical (a composed dir name)."""
    call, fn = _single_call(
        "def f(repo, feature_dir):\n"
        "    return primary_feature_dir_for_mission(repo, feature_dir.name)\n"
    )
    assert is_def_use_canonical(_canonicalizer_handle_arg(call), fn) is True


def test_canonicalizer_accepts_bare_modern_fold_assigned_handle() -> None:
    """T034/T031: a handle assigned from the bare-modern fold seam is canonical.

    Exercises the new ``BARE_MODERN_FOLD_SEAM`` branch in
    ``_names_assigned_from_fold``: when ``canonical = _canonicalize_bare_modern_handle(...)``
    precedes a ``primary_feature_dir_for_mission(repo, canonical)`` call in the
    SAME function, the def-use discriminator classifies it as canonical — the
    same guarantee as the primary-read fold (C-005: behavior-preserving;
    the handle is provably composed in both cases).
    """
    call, fn = _single_call(
        "def f(repo, handle):\n"
        "    canonical = _canonicalize_bare_modern_handle(repo, handle)\n"
        "    return primary_feature_dir_for_mission(repo, canonical)\n"
    )
    assert is_def_use_canonical(_canonicalizer_handle_arg(call), fn) is True


def test_canonicalizer_bare_modern_fold_does_not_canonicalize_raw_param() -> None:
    """T031: the bare-modern fold in a CALLEE does not canonicalize the caller's raw param.

    A handle variable named ``canonical`` that arrived as a raw function parameter
    (never folded IN the callee's own body) is NOT trusted — even if the caller
    passed something folded. FR-004 def-use is strictly intra-function.
    """
    src = (
        "def caller(repo, handle):\n"
        "    canonical = _canonicalize_bare_modern_handle(repo, handle)\n"
        "    return callee(repo, canonical)\n"
        "def callee(repo, canonical):\n"
        "    return primary_feature_dir_for_mission(repo, canonical)\n"
    )
    tree = ast.parse(src)
    parents = _parent_map(tree)
    call = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _callee_name(n) == CANONICALIZER_PRIMITIVE
    )
    fn = _enclosing_function(parents, call)
    # ``canonical`` in ``callee`` is a bare parameter — never folded IN callee.
    assert is_def_use_canonical(_canonicalizer_handle_arg(call), fn) is False


def test_canonicalizer_def_use_is_intra_function_only() -> None:
    """A ``canonical`` var folded in a DIFFERENT function does not canonicalize."""
    src = (
        "def caller(repo, handle):\n"
        "    canon = _canonicalize_primary_read_handle(repo, handle)\n"
        "    return callee(repo, canon)\n"
        "def callee(repo, canon):\n"
        "    return primary_feature_dir_for_mission(repo, canon)\n"
    )
    tree = ast.parse(src)
    parents = _parent_map(tree)
    call = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _callee_name(n) == CANONICALIZER_PRIMITIVE
    )
    fn = _enclosing_function(parents, call)
    # ``canon`` in ``callee`` is a bare parameter — never folded IN callee.
    assert is_def_use_canonical(_canonicalizer_handle_arg(call), fn) is False


def test_canonicalizer_detects_keyword_arg_form() -> None:
    """The keyword-arg call form is detected and classified."""
    call, fn = _single_call(
        "def f(r, slug):\n"
        "    return primary_feature_dir_for_mission(r, mission_slug=slug)\n"
    )
    arg = _canonicalizer_handle_arg(call)
    assert arg is not None
    assert is_def_use_canonical(arg, fn) is False


def test_canonicalizer_attribute_callee_not_mismatched() -> None:
    """An attribute-form callee on another object is matched by the primitive name."""
    sites = scan_canonicalizer_call_sites(SRC_ROOT)
    # No spurious classification crash; every site has a valid qualname.
    assert all(s.key.enclosing_qualname for s in sites)


# --- T003: coord-authority discriminator (unit) ----------------------------
def _coord_call_is_write(src: str) -> bool:
    tree = ast.parse(src)
    parents = _parent_map(tree)
    call = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _callee_name(n) == COORD_BLIND_RESOLVER
    )
    return _function_has_write_indicator(_enclosing_function(parents, call))


def test_coord_authority_flags_write_in_same_function() -> None:
    """A resolve + ``.write_text`` in the same fn classifies as a write."""
    assert _coord_call_is_write(
        "def f(ctx):\n"
        "    d = resolve_feature_dir_for_mission(ctx, slug)\n"
        "    (d / 'x.txt').write_text('y')\n"
    )


def test_coord_authority_pure_read_probe_not_write() -> None:
    """A read-only existence probe is NOT classified as a write."""
    assert not _coord_call_is_write(
        "def f(ctx):\n"
        "    if resolve_feature_dir_for_mission(ctx, slug).exists():\n"
        "        return True\n"
        "    return False\n"
    )


def test_coord_authority_open_read_mode_not_write() -> None:
    """``open(p, 'r')`` is a read; it does not flag the function as a write."""
    assert not _coord_call_is_write(
        "def f(ctx):\n"
        "    d = resolve_feature_dir_for_mission(ctx, slug)\n"
        "    open(d / 'm.json', 'r').read()\n"
    )


def test_coord_authority_open_write_mode_is_write() -> None:
    """``open(p, 'w')`` flags the enclosing function as a write."""
    assert _coord_call_is_write(
        "def f(ctx):\n"
        "    d = resolve_feature_dir_for_mission(ctx, slug)\n"
        "    open(d / 'm.json', 'w').write('x')\n"
    )


def test_coord_authority_by_design_modules_classified_write() -> None:
    """``decisions/emit.py`` and ``widen/state.py`` are write-by-design sites."""
    sites = scan_coord_authority_call_sites(SRC_ROOT)
    by_design = {s.rel_path for s in sites if s.is_write and s.rel_path in _COORD_WRITE_BY_DESIGN}
    assert "src/specify_cli/decisions/emit.py" in by_design
    assert "src/specify_cli/widen/state.py" in by_design


# --- T004: seeded allowlist is green ---------------------------------------
def test_canonicalizer_gate_green_against_seeded_allowlist() -> None:
    """With the seeded baseline, the canonicalizer gate reports zero violations."""
    allowlist = set(load_allowlist(ALLOWLIST_PATH)["canonicalizer"])
    violations = check_canonicalizer_gate(SRC_ROOT, allowlist)
    assert violations == [], "\n".join(violations)


def test_coord_authority_gate_green_against_seeded_allowlist() -> None:
    """With the seeded baseline, the coord-authority gate reports zero violations."""
    allowlist = set(load_allowlist(ALLOWLIST_PATH)["coord_authority"])
    violations = check_coord_authority_gate(SRC_ROOT, allowlist)
    assert violations == [], "\n".join(violations)


def test_c001_bare_probe_is_pinned_in_allowlist() -> None:
    """C-001 merge-blocker: the ``:454`` bare probe is sanctioned, never fixed.

    Its enclosing qualname is ``_canonicalize_bare_modern_handle`` (def ``:418``),
    NOT ``_canonicalize_primary_read_handle``.
    """
    keys = set(load_allowlist(ALLOWLIST_PATH)["canonicalizer"])
    # Line is matched against the live tree — check YAML agrees with what exists in src.
    live = _live_canonicalizer_keys(SRC_ROOT)
    c001_matches = {k for k in keys if k.enclosing_qualname == "_canonicalize_bare_modern_handle"}
    assert c001_matches, (
        "C-001: _read_path_resolver.py _canonicalize_bare_modern_handle must stay in "
        "the canonicalizer allowlist with the FR-011 rationale — folding canonicalization "
        "into the primitive would recurse. Removing this entry is a merge-blocker regression."
    )
    pinned = next(iter(c001_matches))
    assert pinned in live, (
        f"the C-001 pin ({pinned}) must match a live call site — re-pin the line number"
    )


def test_canonicalizer_permanent_allowlist_is_exactly_3() -> None:
    """T032: canonicalizer allowlist == exactly 3 permanent raw-param sanctions after WP07.

    The 4 bare-modern-fold entries (``resolve_handle_to_read_path:950/972/1023``,
    ``_stored_topology_best_effort:1208``) are auto-classified canonical by the
    T031 discriminator and MUST NOT appear in the allowlist. Exactly 3 permanent
    sanctions remain — all legitimate raw-parameter sites that the def-use
    discriminator cannot auto-detect:

    * ``_canonicalize_bare_modern_handle`` — C-001 bare probe (would recurse if folded)
    * ``read_primary_meta`` — seam-internal first-probe (raw bare param by design)
    * ``MissionStatus._find_meta_path`` — handle from ``resolve_bare_modern_mission_dir_name``
      (already-canonical by provenance, not a detectable fold assignment)

    ``len == 3`` (not just ``<= baseline``) catches a regression where one of the
    4 auto-routed entries was re-added to the allowlist instead of being removed.
    """
    keys = load_allowlist(ALLOWLIST_PATH)["canonicalizer"]
    assert len(keys) == 3, (
        f"canonicalizer allowlist must have exactly 3 permanent entries after WP07 "
        f"(got {len(keys)}); the 4 bare-modern-fold entries must be auto-classified "
        "by T031, not sanctioned in the allowlist"
    )
    expected_qualnames = frozenset({
        "_canonicalize_bare_modern_handle",
        "read_primary_meta",
        "MissionStatus._find_meta_path",
    })
    actual_qualnames = frozenset(k.enclosing_qualname for k in keys)
    assert actual_qualnames == expected_qualnames, (
        f"wrong permanent entries — expected {set(expected_qualnames)}, "
        f"got {set(actual_qualnames)}"
    )


def test_coord_by_design_writes_in_allowlist() -> None:
    """``decisions/emit.py`` and ``widen/state.py`` are sanctioned by design."""
    sites = {
        (s.rel_path, s.key)
        for s in scan_coord_authority_call_sites(SRC_ROOT)
        if s.rel_path in _COORD_WRITE_BY_DESIGN
    }
    allowlist = set(load_allowlist(ALLOWLIST_PATH)["coord_authority"])
    for rel_path, key in sites:
        assert key in allowlist, f"{rel_path}:{key} must be allowlisted by design"


def test_every_allowlist_entry_has_live_match() -> None:
    """No seeded allowlist entry is stale (NFR-003 twin-guard, real tree)."""
    keys = load_allowlist(ALLOWLIST_PATH)
    canon_stale = staleness_twin_guard(
        set(keys["canonicalizer"]), _live_canonicalizer_keys(SRC_ROOT)
    )
    coord_stale = staleness_twin_guard(
        set(keys["coord_authority"]), _live_coord_authority_keys(SRC_ROOT)
    )
    assert canon_stale == [], f"stale canonicalizer entries: {canon_stale}"
    assert coord_stale == [], f"stale coord_authority entries: {coord_stale}"


# --- T005: self-mutation proofs (gate is not vacuous) ----------------------
def test_canonicalizer_self_mutation_injects_violation(tmp_path: Path) -> None:
    """Canonicalizer gate FAILS on an injected raw call, PASSES once sanctioned.

    Injected code (distinct module ``scratch_pkg.handler``, qualname
    ``ScratchHandler.run`` — NOT ``MarkStatusCmd.run`` / ``move_task`` /
    ``_claim_wp_impl``, distinct from any IC-04 fix site)::

        class ScratchHandler:
            def run(self, repo_root, raw_slug):
                return primary_feature_dir_for_mission(repo_root, raw_slug)

    Guard result against an empty allowlist: NON-EMPTY (violation flagged).
    Revert (sanction the site): EMPTY (gate passes).
    """
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    handler = pkg / "handler.py"
    handler.write_text(
        "class ScratchHandler:\n"
        "    def run(self, repo_root, raw_slug):\n"
        "        return primary_feature_dir_for_mission(repo_root, raw_slug)\n",
        encoding="utf-8",
    )
    scratch_src = tmp_path / "src"

    # Injected → gate FAILS (empty allowlist).
    violations = check_canonicalizer_gate(scratch_src, set())
    assert violations, "self-mutation: injected raw call must be flagged"

    # Sanctioned → gate PASSES.
    site_key = GateAllowlistKey("ScratchHandler.run", 3)
    assert check_canonicalizer_gate(scratch_src, {site_key}) == []


def test_coord_authority_self_mutation_injects_violation(tmp_path: Path) -> None:
    """Coord-authority gate FAILS on an injected write, PASSES once sanctioned.

    Injected code (distinct module ``scratch_pkg.writer``, qualname
    ``ScratchWriter.persist`` — distinct from any IC-04 fix site)::

        class ScratchWriter:
            def persist(self, ctx):
                d = resolve_feature_dir_for_mission(ctx, slug)
                (d / "out.txt").write_text("x")

    Guard result against an empty allowlist: NON-EMPTY (write flagged).
    Revert (sanction the site): EMPTY (gate passes).
    """
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    writer = pkg / "writer.py"
    writer.write_text(
        "class ScratchWriter:\n"
        "    def persist(self, ctx):\n"
        "        d = resolve_feature_dir_for_mission(ctx, slug)\n"
        "        (d / 'out.txt').write_text('x')\n",
        encoding="utf-8",
    )
    scratch_src = tmp_path / "src"

    violations = check_coord_authority_gate(scratch_src, set())
    assert violations, "self-mutation: injected write must be flagged"

    site_key = GateAllowlistKey("ScratchWriter.persist", 3)
    assert check_coord_authority_gate(scratch_src, {site_key}) == []


def test_canonicalizer_bare_modern_fold_auto_routes(tmp_path: Path) -> None:
    """T034: gate passes without allowlist when the bare-modern fold is used (T031 branch).

    Self-mutation proof that the new ``BARE_MODERN_FOLD_SEAM`` discriminator
    branch in ``_names_assigned_from_fold`` takes effect in the full gate scan:
    inject a module where ``primary_feature_dir_for_mission`` receives a handle
    that was assigned from ``_canonicalize_bare_modern_handle`` in the same
    function, then verify the gate classifies it as canonical (no violation,
    no allowlist entry required).

    This directly covers the new ``BARE_MODERN_FOLD_SEAM`` branch (NFR-003).
    """
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "bare_modern_router.py").write_text(
        "class BareModernRouter:\n"
        "    def resolve(self, repo_root, handle):\n"
        "        canonical = _canonicalize_bare_modern_handle(repo_root, handle)\n"
        "        return primary_feature_dir_for_mission(repo_root, canonical)\n",
        encoding="utf-8",
    )
    scratch_src = tmp_path / "src"

    # Gate passes with an empty allowlist — the bare-modern fold is auto-classified
    # canonical by the T031 discriminator; no sanction entry is needed.
    violations = check_canonicalizer_gate(scratch_src, set())
    assert violations == [], (
        f"T031/T034: bare-modern fold should auto-classify as canonical; "
        f"got violations: {violations}"
    )


# --- T006: concrete floors + shrink-only twin-guard ------------------------
def test_canonicalizer_gate_floor() -> None:
    """Concrete floor: the canonicalizer scan finds >= 45 real call sites (NFR-002).

    The literal 45 is the live census on the current ``src/`` tree; a broken
    scanner returning zero rows trivially fails this. ``> 0`` / ``>= 1`` are
    explicitly rejected by NFR-002.
    """
    count = len(scan_canonicalizer_call_sites(SRC_ROOT))
    assert count >= CANONICALIZER_FLOOR, (
        f"canonicalizer census dropped to {count}; expected >= {CANONICALIZER_FLOOR}. "
        "A shrinking census likely means the scanner stopped matching call sites."
    )


def test_routed_count_floor() -> None:
    """SC-004 anti-mass-allowlist guard: routed canonicalizer sites stay >= floor.

    WP02-WP07 ROUTED the bare ``primary_feature_dir_for_mission`` call sites
    through ``_canonicalize_primary_read_handle`` or ``_canonicalize_bare_modern_handle``
    (T031 — or a provably-canonical ``feature_dir.name`` read) — they did NOT
    mass-allowlist them. This test proves that: it counts the sites the def-use
    discriminator classifies as *canonical* (routed) and asserts that count stays
    within ``ROUTED_CANONICALIZER_FLOOR_MARGIN`` of the floor AND strictly above it.

    The floor is a CONCRETE integer (``ROUTED_CANONICALIZER_FLOOR == 38``), NOT
    ``>= len(scanned routed sites)``. A tautological ``>= live_routed`` would be
    satisfied even if a future regression allowlisted every site instead of routing
    it (routed → 0, allowlist → 45, gate still green). Hard-coding the census
    makes mass-allowlisting CI-red.

    Live routed count is 42 (45 total minus the 3 permanent sanctions; the 4
    bare-modern-fold sites are auto-classified by T031). The floor 38 is
    ``42 − ROUTED_CANONICALIZER_FLOOR_MARGIN(4)`` — deliberately below live so the
    assertion has teeth, but tight enough to catch a loose ratchet.

    Both bounds are enforced:
    * ``live − MARGIN <= floor < live``  (lower: floor is tight; upper: anti-vacuous)
    """
    sites = scan_canonicalizer_call_sites(SRC_ROOT)
    routed = [s for s in sites if s.is_canonical]
    assert len(routed) >= ROUTED_CANONICALIZER_FLOOR, (
        f"routed (def-use-canonical) canonicalizer census dropped to "
        f"{len(routed)}; expected >= {ROUTED_CANONICALIZER_FLOOR} (SC-004). "
        "A drop below this floor means sites were allowlisted instead of routed "
        "(mass-allowlisting) — route them through the canonical fold seam."
    )
    # Upper bound: the floor is NOT tautological — it must be strictly below live.
    assert len(routed) > ROUTED_CANONICALIZER_FLOOR, (
        "ROUTED_CANONICALIZER_FLOOR must be a concrete census integer strictly "
        "below the live routed count, not ``>= len(routed)`` (NFR-002 anti-vacuous)."
    )
    # Lower bound (T033): the floor is tight — within MARGIN of the live count.
    # This prevents the floor from drifting silently below a meaningful threshold
    # (a floor of 0 would pass the upper check but provide no guard at all).
    assert len(routed) - ROUTED_CANONICALIZER_FLOOR <= ROUTED_CANONICALIZER_FLOOR_MARGIN, (
        f"ROUTED_CANONICALIZER_FLOOR ({ROUTED_CANONICALIZER_FLOOR}) is more than "
        f"ROUTED_CANONICALIZER_FLOOR_MARGIN ({ROUTED_CANONICALIZER_FLOOR_MARGIN}) "
        f"below the live routed count ({len(routed)}); tighten the floor to within "
        "the margin to prevent a loose ratchet."
    )


def test_coord_authority_gate_floor() -> None:
    """Concrete floor: >= 12 WRITE-classified coord call sites (NFR-002).

    12 is the hard-coded live write-candidate census (NOT ``>= len(scanned)`` —
    that is tautological). Sites that sit in a function carrying a write indicator
    (this count INCLUDES the 2 by-design coord-owned writes — ``decisions/emit.py``
    and ``widen/state.py`` — which are write-classified by design and sanctioned in
    the allowlist). History: WP08 set this to the then-honest census of 17; this
    mission's WP06 routing then moved 3 write-classified sites onto the kind-aware
    seam (``list_dependents``/``review`` dependents-warning reads → primary), so
    WP07 tightened the floor 17 → 14. The 2026-06-27 rebase onto upstream/main then
    carried concurrent mission #1057, which inserted a ``check_pre30_layout`` boundary
    guard into ``list_dependents`` — re-introducing a kind-blind resolve probe there —
    raising the honest live census 14 → 15. This mission's WP routing then moved a
    further 2 write-classified sites onto the kind-aware seam, shrinking the live
    census 15 → 13. retire-standalone-tasks-cli WP04 then deleted the standalone
    scripts/tasks surface, removing its sole write-census site
    (``tasks_cli.py::_prepare_merge_metadata``) and shrinking the live census
    13 → 12. The ``coord_authority_baseline`` scalar caps the allowlist *entry
    count*, a different quantity from the write *site* census (which they happen
    to equal here).
    """
    writes = [s for s in scan_coord_authority_call_sites(SRC_ROOT) if s.is_write]
    assert len(writes) >= COORD_AUTHORITY_WRITE_FLOOR, (
        f"write-candidate census dropped to {len(writes)}; expected "
        f">= {COORD_AUTHORITY_WRITE_FLOOR}."
    )


def test_allowlist_no_stale_entries() -> None:
    """NFR-003 twin-guard: every YAML entry matches a live call site (real tree)."""
    keys = load_allowlist(ALLOWLIST_PATH)
    live = _live_canonicalizer_keys(SRC_ROOT) | _live_coord_authority_keys(SRC_ROOT)
    all_allowlist = set(keys["canonicalizer"]) | set(keys["coord_authority"])
    stale = staleness_twin_guard(all_allowlist, live)
    assert stale == [], (
        "stale allowlist entries (no live call site) — remove them (shrink-only):\n"
        + "\n".join(f"  {k.enclosing_qualname}:{k.token_line}" for k in stale)
    )


def test_allowlist_shrink_only() -> None:
    """NFR-003: the seeded allowlist never inflates beyond the pre-sweep baseline.

    Future sweep WPs may only REMOVE entries (as they route sites). Adding an
    entry beyond the recorded baseline fails this guard.
    """
    keys = load_allowlist(ALLOWLIST_PATH)
    canon_baseline = load_baseline(ALLOWLIST_PATH, "canonicalizer")
    coord_baseline = load_baseline(ALLOWLIST_PATH, "coord_authority")
    assert len(keys["canonicalizer"]) <= canon_baseline, (
        f"canonicalizer allowlist ({len(keys['canonicalizer'])}) exceeds baseline "
        f"({canon_baseline}) — entries may only be removed, never added"
    )
    assert len(keys["coord_authority"]) <= coord_baseline, (
        f"coord_authority allowlist ({len(keys['coord_authority'])}) exceeds baseline "
        f"({coord_baseline}) — entries may only be removed, never added"
    )


# --- T007: fast-tier timing (NFR-004) --------------------------------------
def test_gates_run_under_fast_tier_budget() -> None:
    """Both scans complete well under the 30 s fast-tier ceiling (NFR-004).

    A generous 30 s assertion (local run ~0.3 s for both scans) — it guards
    against an accidental O(n^2) regression without being flaky on slow CI.
    """
    start = time.monotonic()
    scan_canonicalizer_call_sites(SRC_ROOT)
    scan_coord_authority_call_sites(SRC_ROOT)
    elapsed = time.monotonic() - start
    assert elapsed < 30.0, f"resolution-authority scans took {elapsed:.2f}s (>30s budget)"
