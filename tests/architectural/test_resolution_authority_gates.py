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

* Composite key ``(rel_path, enclosing_qualname, token)`` computed **live** from
  source (Design-P) — the stored comparand is the frozen tool-derived ``token``
  (a ``code_tokens_by_line`` string), never a raw AST line number. It survives
  benign line drift, unlike a raw ``file:line`` key: inserting a blank line above
  a pinned site changes neither the enclosing qualname nor the guarded code
  token, so the ratchet stays GREEN; only a genuine content edit reds it.
* Concrete integer floors (canonicalizer ``>= 45``; coord-authority a hard-coded
  literal ``>= 9``) so a broken scanner returning zero rows cannot pass
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
``(rel_path, enclosing_qualname, token)`` composite key required by NFR-001 is
absent from both and is implemented here from scratch (AST ancestor traversal +
the shared ``code_tokens_by_line`` tokenizer). The Design-P reference is
``tests/architectural/test_no_worktree_name_guess.py`` (frozen composite keys +
line-drift theater); its keys are NOT modified by this mission.
"""

from __future__ import annotations

import ast
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tests.architectural._ratchet_keys import code_tokens_by_line

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
# read-surface-ssot-closeout WP05 (FR-001/NFR-001, SHRINK-ONLY): routing
# ``implement.implement``'s detect-feature-context ``feature_dir`` read onto
# ``placement_seam(...).read_dir(SPEC)`` removed the direct
# ``primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))``
# fallback-cascade anchor that call site's meta.json-existence check used to
# fall back to — draining the live census 45 → 44 (a genuine routing shrink,
# not a re-pin; the seam's internal anchor is not scanned as a caller-site).
CANONICALIZER_FLOOR = 44
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
# tasks-py-degod WP09 (FR-011, SHRINK-ONLY): the WP01-WP08 tasks.py de-god rewires
# drained THREE write-census sites — move_task's two coord-aware resolves (WP06
# thin-orchestrator rewrite) and list_dependents' probe (WP08 fold-to-primary) —
# shrinking the honest live write census 12 -> 9. Two surviving sites (list_tasks,
# validate_workflow) were re-pinned for line drift, not drained. Floor lowered
# 12 -> 9 to the re-measured live count.
# tasks-py-degod-wave2 WP09 (arch-closure sweep, SHRINK-ONLY): the wave-2 WP04
# render-seam unification routed list_tasks' and validate_workflow's inline
# ``print(json.dumps(...))`` emission through ``Render.json_envelope``, removing
# the ``dumps`` write-indicator token from both bodies — their surviving
# kind-blind STATUS-partition probes are READ-classified now, draining the live
# write census 9 -> 7 (workflow.py implement x2 + review x2, implement.py
# implement, and the 2 by-design coord-owned writes). Floor lowered 9 -> 7 to
# the re-measured live count; allowlist entries drained in the same commit
# (resolution_gate_allowlist.yaml header).
# read-surface-ssot-closeout WP04+WP05 COMBINED DRAIN (SHRINK-ONLY): all 5
# drainable coord_authority sites routed (4 workflow.py + implement.py); only the
# 2 by-design coord-owned writes remained afterward (live write census 2).
# read-surface-ssot-closeout WP11 (FR-003 predicate-widen, GENUINE GAIN, not a
# re-pin): re-measured via scan_coord_authority_call_sites AFTER widening
# ``_COORD_WRITE_BY_DESIGN`` to cover ``agent_tasks_ports.py`` (``feature_write_dir``)
# and ``lanes/recovery.py`` (``reconcile_status``) — two legitimate coord-owned
# write helpers the predicate previously missed (write indicator one hop outside
# the function-granularity trace) and that WP07/WP08 therefore never routed or
# even saw. Both are allowlisted (resolution_gate_allowlist.yaml). Live write
# census: 2 -> 4. Floor raised 2 -> 4 to the honest re-measured count (the two
# new sites were UNSEEN before, not un-routed — this is a visibility fix, not a
# regression to route away).
COORD_AUTHORITY_WRITE_FLOOR = 4

# tasks-py-degod WP09 — coord-authority write-floor margin gate (anti-masking).
# The floor must track the honest live write census: setting it materially BELOW
# the live count would let a body of un-routed kind-blind writes pass unseen. The
# margin bounds the permitted gap ``live - floor`` — a small headroom absorbs
# benign upstream growth of by-design coord writes without needing a re-pin, while
# a floor dropped far below live (masking un-routed writes) fails the gate.
COORD_AUTHORITY_WRITE_FLOOR_MARGIN = 2

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
# tasks-py-degod WP02 (C-002): the TasksPorts co-design adds ONE new DIRECT
# primitive anchor — ``RealFsReader.primary_anchor_dir`` co-locates
# ``primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))`` inside
# the adapter (the intra-function fold C-002 mandates). Live routed census 42 → 43;
# floor recomputed 43 − MARGIN(4) = 39. Honest before/after, not a re-pin.
ROUTED_CANONICALIZER_FLOOR = 39


# --------------------------------------------------------------------------- #
# IC-01 — composite-key allowlist machinery (NET-NEW, NFR-001).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class GateAllowlistKey:
    """Composite Design-P allowlist key surviving benign line drift (NFR-001).

    ``rel_path`` is the repo-relative source path (disambiguates qualname
    collisions such as the two ``implement`` / two ``review`` write sites in
    ``workflow.py``). ``enclosing_qualname`` is the dotted chain of enclosing
    ``def`` / ``class`` names (e.g. ``MissionStatus._find_meta_path``), or
    ``"<module>"`` for a call at file scope. ``token`` is the FROZEN
    tool-derived ``code_tokens_by_line`` string of the call's line — the
    authoritative content comparand, NOT a raw AST line number. The triple is
    hashable and equality-comparable, so it doubles as the serialization key. No
    line number ever enters the key (SC-001): a raw ``file:line`` key reds on
    benign drift; this content-addressed key does not.
    """

    rel_path: str
    enclosing_qualname: str
    token: str


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

    Design-P: each entry carries ``file:``, ``qualname:``, ``token:`` (the FROZEN
    tool-derived comparand — read verbatim, NEVER re-derived at load) plus a
    non-authoritative ``line:`` locator and a **mandatory** ``rationale:``. The
    key is the ``(file, qualname, token)`` triple; ``line:`` is NOT part of it and
    is loaded separately by :func:`load_allowlist_locators` for messages only. An
    entry missing/empty ``rationale`` or missing ``file``/``token`` raises
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
            rel_path = _require_str(entry, "file", context)
            qualname = _require_str(entry, "qualname", context)
            token = _require_str(entry, "token", context)
            _require_str(entry, "rationale", context)
            # ``line:`` is a non-authoritative locator: it must be an int when
            # present (diagnostics), but it never enters the key.
            line = entry.get("line")
            if line is not None and not isinstance(line, int):
                raise AllowlistEntryError(
                    f"{context} ({qualname!r}) has a non-integer line locator {line!r}"
                )
            keys.append(GateAllowlistKey(rel_path, qualname, token))
        out[gate_name] = keys
    return out


def load_allowlist_locators(path: Path) -> dict[GateAllowlistKey, int]:
    """Return ``{key: line}`` for entries carrying a ``line:`` locator.

    The locator is diagnostics-only (jump-to / staleness message ergonomics); it
    is NEVER compared, set-membership-tested, or counted (Design-P line demotion,
    contract rule 3).
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    locators: dict[GateAllowlistKey, int] = {}
    for gate_name in ("canonicalizer", "coord_authority"):
        for entry in raw.get(gate_name) or []:
            if not isinstance(entry, dict):
                continue
            line = entry.get("line")
            file = entry.get("file")
            qualname = entry.get("qualname")
            token = entry.get("token")
            if (
                isinstance(line, int)
                and isinstance(file, str)
                and isinstance(qualname, str)
                and isinstance(token, str)
            ):
                locators[GateAllowlistKey(file, qualname, token)] = line
    return locators


def load_occurrence_counts(path: Path) -> dict[GateAllowlistKey, int]:
    """Return ``{key: count}`` for entries carrying an explicit ``count:``.

    Speculative surface (zero real users today — recorded deliberately for a
    future within-function collision drain): an entry MAY declare ``count: N`` to
    require exactly ``N`` live occurrences of an identical token in one function.
    Entries WITHOUT ``count:`` default to 1-covers-any (set membership), so this
    map is empty for the current allowlist.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    counts: dict[GateAllowlistKey, int] = {}
    for gate_name in ("canonicalizer", "coord_authority"):
        for entry in raw.get(gate_name) or []:
            if not isinstance(entry, dict):
                continue
            count = entry.get("count")
            file = entry.get("file")
            qualname = entry.get("qualname")
            token = entry.get("token")
            if (
                isinstance(count, int)
                and isinstance(file, str)
                and isinstance(qualname, str)
                and isinstance(token, str)
            ):
                counts[GateAllowlistKey(file, qualname, token)] = count
    return counts


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


def derive_live_key(
    node: ast.expr | ast.stmt,
    tree: ast.Module,
    source: str,
    rel_path: str = "<derived>",
) -> GateAllowlistKey:
    """Composite ``(rel_path, enclosing_qualname, token)`` for *node* within *tree*.

    Convenience wrapper that rebuilds the parent map per call. The bulk scanners
    build the map + token map once and call :func:`_qualname_from_parents`
    directly. *node* must be a positioned node (``ast.expr`` / ``ast.stmt`` carry
    ``lineno``). ``node.lineno`` is used ONLY to index the token map — it never
    enters the returned key (SC-001). *rel_path* defaults to a synthetic sentinel
    for unit tests that parse an in-memory source with no real file.
    """
    parents = _parent_map(tree)
    token = code_tokens_by_line(source).get(node.lineno, "")
    return GateAllowlistKey(rel_path, _qualname_from_parents(parents, node), token)


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
    whose frozen token no longer matches any live call site, so the entry must be
    evicted or re-approved (shrink-only governance, contract rule 6).
    """
    return sorted(
        allowlist_keys - live_keys,
        key=lambda k: (k.rel_path, k.enclosing_qualname, k.token),
    )


def format_staleness_failure(
    stale: list[GateAllowlistKey], live_keys: set[GateAllowlistKey]
) -> str:
    """Build the evict-or-re-approve message with the nearest live token (NFR-003).

    For each stale key the message lists the live tokens for the SAME
    ``(rel_path, qualname)`` so a legitimate site edit is a copy-paste freshen,
    not archaeology (contract rule 6 / token-churn ergonomics). If no live site
    shares the qualname, the site was removed and the entry must be evicted.
    """
    lines: list[str] = []
    for key in stale:
        siblings = sorted(
            lk.token
            for lk in live_keys
            if lk.rel_path == key.rel_path and lk.enclosing_qualname == key.enclosing_qualname
        )
        if siblings:
            hint = "nearest live token(s) for this qualname — re-approve with one:\n      " + (
                "\n      ".join(repr(t) for t in siblings)
            )
        else:
            hint = "no live site shares this qualname — the site was removed; EVICT the entry"
        lines.append(
            f"  STALE {key.rel_path}:{key.enclosing_qualname} token={key.token!r}\n    {hint}"
        )
    return "\n".join(lines)


def occurrence_count_violations(
    site_keys: list[GateAllowlistKey], count_map: dict[GateAllowlistKey, int]
) -> list[str]:
    """Return violations where a ``count:``-qualified entry's live count is wrong.

    Speculative within-function collision surface (zero real users today): only
    entries carrying an explicit ``count: N`` are checked, and only against the
    number of live sites producing that exact key. An entry without ``count:``
    imposes no occurrence constraint (default 1-covers-any via set membership).
    """
    counts = Counter(site_keys)
    violations: list[str] = []
    for key, required in count_map.items():
        actual = counts.get(key, 0)
        if actual != required:
            violations.append(
                f"{key.rel_path}:{key.enclosing_qualname} token={key.token!r} "
                f"declares count {required} but {actual} live occurrence(s) exist"
            )
    return sorted(violations)


# --------------------------------------------------------------------------- #
# Shared file iteration (parse each file at most once — NFR-004).
# --------------------------------------------------------------------------- #
def _iter_source_files(src_root: Path) -> list[Path]:
    return [
        p
        for p in sorted(src_root.rglob("*.py"))
        if "__pycache__" not in p.parts
    ]


# Module-wide cache of parsed (tree, parent_map, token_map) per file, keyed by
# resolved src root. The many tests that re-scan the real tree share one parse
# pass (NFR-004). Scratch ``tmp_path`` trees get distinct keys and are not
# retained across test functions in any way that affects the real-tree gates.
# ``token_map`` (``code_tokens_by_line``) supplies the Design-P frozen comparand
# so scanners never re-read source per site.
_ParsedFile = tuple[str, ast.Module, dict[int, ast.AST], dict[int, str]]
_parsed_trees: dict[str, list[_ParsedFile]] = {}


def _parsed_source(src_root: Path) -> list[_ParsedFile]:
    """Return ``[(rel_path, tree, parent_map, token_map), ...]``, cached."""
    cache_key = str(src_root.resolve())
    cached = _parsed_trees.get(cache_key)
    if cached is not None:
        return cached
    parsed: list[_ParsedFile] = []
    for path in _iter_source_files(src_root):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        parsed.append((_rel(path), tree, _parent_map(tree), code_tokens_by_line(source)))
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
    """One discovered ``primary_feature_dir_for_mission`` call site.

    ``lineno`` is the LIVE scan line — a diagnostics locator for violation
    messages ONLY; it is deliberately NOT part of ``key`` (SC-001).
    """

    rel_path: str
    key: GateAllowlistKey
    lineno: int
    is_canonical: bool


def scan_canonicalizer_call_sites(src_root: Path) -> list[CanonicalizerSite]:
    """AST-walk ``src/**/*.py`` for every ``primary_feature_dir_for_mission`` call.

    Handles bare-name and attribute call forms; classifies each by intra-function
    def-use. Method calls whose callee is a dotted attribute of a *different*
    object (``self.resolver.primary_feature_dir_for_mission(...)``) still match by
    attribute name — that is intentional: the primitive is the call target
    regardless of how it is reached. The composite key's ``token`` is the frozen
    ``code_tokens_by_line`` string; ``node.lineno`` indexes the token map only.
    """
    sites: list[CanonicalizerSite] = []
    for rel, tree, parents, token_map in _parsed_source(src_root):
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
                    key=GateAllowlistKey(rel, qualname, token_map.get(node.lineno, "")),
                    lineno=node.lineno,
                    is_canonical=is_def_use_canonical(arg, fn),
                )
            )
    return sites


def check_canonicalizer_gate(
    src_root: Path, allowlist: set[GateAllowlistKey]
) -> list[str]:
    """Return violation strings for non-canonical, non-allowlisted call sites.

    Each violation names ``file:line (qualname)`` (the live line locator + the
    frozen token excerpt) and the sanctioned seam
    (``_canonicalize_primary_read_handle``) the developer must route through.
    """
    violations: list[str] = []
    for site in scan_canonicalizer_call_sites(src_root):
        if site.is_canonical or site.key in allowlist:
            continue
        violations.append(
            f"{site.rel_path}:{site.lineno} ({site.key.enclosing_qualname}) "
            f"token={site.key.token!r} passes a non-canonical handle to "
            f"{CANONICALIZER_PRIMITIVE} — route it through {CANONICAL_FOLD_SEAM} "
            f"(the canonical read fold) or allowlist it with an already-canonical "
            f"rationale"
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
#
# read-surface-ssot-closeout WP11 (FR-003 predicate-widen): the original 2-entry
# set MASKED two legitimate coord-owned write helpers that fit the exact same
# shape (resolve, then hand the dir to a caller-level write) but whose write
# indicator call is one hop further away than this FUNCTION-granularity scanner
# traces (Phase 1 does not follow the resolved dir through a return value into
# the caller, nor through a dataclass field into a differently-named emit
# helper):
#   * ``agent_tasks_ports.py:RealCoordCommitRouter.feature_write_dir`` — the
#     method literally returns ``write_dir`` to callers that commit it; WP07/
#     WP08 left this source-unchanged (it was never a routing target).
#   * ``lanes/recovery.py:reconcile_status`` — the resolved ``feature_dir`` is
#     threaded into a ``TransitionRequest`` consumed by
#     ``emit_status_transition_transactional`` (a STATUS-WRITE leg per the
#     KEEP-coord-aware comment at the call site); the write indicator lives in
#     the callee, not a literal ``write_text``/``commit*`` token in this
#     function body.
# Both were previously silently classified READ (predicate blind spot) and
# escaped the gate entirely rather than being either routed or allowlisted.
# Widening the by-design set to file-scope (matching the existing two entries'
# shape) makes them WRITE-classified and forces an explicit allowlist sanction
# (see resolution_gate_allowlist.yaml) instead of leaving them unseen.
_COORD_WRITE_BY_DESIGN: frozenset[str] = frozenset(
    {
        "src/specify_cli/decisions/emit.py",
        "src/specify_cli/widen/state.py",
        "src/specify_cli/agent_tasks_ports.py",
        "src/specify_cli/lanes/recovery.py",
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
    """One discovered ``resolve_feature_dir_for_mission`` call site.

    ``lineno`` is the LIVE scan line — a diagnostics locator for violation
    messages ONLY; it is deliberately NOT part of ``key`` (SC-001).
    """

    rel_path: str
    key: GateAllowlistKey
    lineno: int
    is_write: bool


def scan_coord_authority_call_sites(src_root: Path) -> list[CoordAuthoritySite]:
    """AST-walk ``src/**/*.py`` for every ``resolve_feature_dir_for_mission`` call.

    The ``is_write`` flag applies the documented write predicate: the enclosing
    function contains a write indicator, OR the call site lives in a
    coord-owned-write-by-design module (``decisions/emit.py`` / ``widen/state.py``).
    The composite key's ``token`` is the frozen ``code_tokens_by_line`` string;
    ``node.lineno`` indexes the token map only.
    """
    sites: list[CoordAuthoritySite] = []
    for rel, tree, parents, token_map in _parsed_source(src_root):
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
                    key=GateAllowlistKey(rel, qualname, token_map.get(node.lineno, "")),
                    lineno=node.lineno,
                    is_write=is_write,
                )
            )
    return sites


def check_coord_authority_gate(
    src_root: Path, allowlist: set[GateAllowlistKey]
) -> list[str]:
    """Return violation strings for unsanctioned mission-artifact write sites.

    A write-classified call to the kind-blind ``resolve_feature_dir_for_mission``
    that is not allowlisted is a violation; each names ``file:line (qualname)``
    (the live line locator + the frozen token excerpt) and the kind-aware
    authority to use instead.
    """
    violations: list[str] = []
    for site in scan_coord_authority_call_sites(src_root):
        if not site.is_write or site.key in allowlist:
            continue
        violations.append(
            f"{site.rel_path}:{site.lineno} ({site.key.enclosing_qualname}) "
            f"token={site.key.token!r} resolves a mission-artifact WRITE target via "
            f"the kind-blind {COORD_BLIND_RESOLVER} — route it through "
            f"{COORD_KIND_AWARE_AUTHORITY} or allowlist it as a legitimate "
            f"coord-owned write"
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
    """``GateAllowlistKey`` compares/hashes by the ``(file, qualname, token)`` triple.

    Design-P: the third component is the frozen ``token`` (synthetic here — this
    is a unit test OF the mechanism, not an allowlist entry), NOT a line number.
    Changing only the token yields a distinct key.
    """
    a = GateAllowlistKey("f.py", "MarkStatusCmd.run", "x = 1")
    b = GateAllowlistKey("f.py", "MarkStatusCmd.run", "x = 1")
    c = GateAllowlistKey("f.py", "MarkStatusCmd.run", "x = 2")
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert {a, b} == {a}


def test_loader_rejects_entry_without_rationale(tmp_path: Path) -> None:
    """The loader fails closed on a missing/empty ``rationale`` (no silent drift)."""
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "canonicalizer:\n"
        "  - file: f.py\n    qualname: foo.bar\n    token: x = 1\n    line: 10\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="rationale"):
        load_allowlist(bad)

    empty_rationale = tmp_path / "empty.yaml"
    empty_rationale.write_text(
        "canonicalizer:\n"
        "  - file: f.py\n    qualname: foo.bar\n    token: x = 1\n"
        "    line: 10\n    rationale: '  '\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="rationale"):
        load_allowlist(empty_rationale)


def test_loader_rejects_entry_without_token(tmp_path: Path) -> None:
    """The loader fails closed on a missing/empty ``token`` (Design-P comparand)."""
    bad = tmp_path / "no_token.yaml"
    bad.write_text(
        "canonicalizer:\n"
        "  - file: f.py\n    qualname: foo.bar\n    line: 10\n    rationale: r\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="token"):
        load_allowlist(bad)


def test_derive_live_key_module_scope() -> None:
    """A call at file scope derives ``"<module>"`` and the frozen token."""
    src = "primary_feature_dir_for_mission(repo, slug)\n"
    tree = ast.parse(src)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    key = derive_live_key(call, tree, src)
    assert key.enclosing_qualname == "<module>"
    assert key.token == "primary_feature_dir_for_mission ( repo , slug )"


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
    key = derive_live_key(call, tree, src)
    assert key.enclosing_qualname == "A.run.inner"
    assert key.token == "primary_feature_dir_for_mission ( r , s )"


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
    keys = {derive_live_key(c, tree, src).enclosing_qualname for c in calls}
    assert keys == {"A.run", "B.run"}


def test_staleness_twin_guard_empty_when_all_live() -> None:
    """The twin-guard returns ``[]`` when every allowlist key is live."""
    live = {
        GateAllowlistKey("f.py", "a.b", "t1"),
        GateAllowlistKey("f.py", "c.d", "t2"),
    }
    assert staleness_twin_guard({GateAllowlistKey("f.py", "a.b", "t1")}, live) == []


def test_staleness_twin_guard_flags_stale_entry() -> None:
    """The twin-guard returns the allowlist keys with no live match."""
    live = {GateAllowlistKey("f.py", "a.b", "t1")}
    stale = staleness_twin_guard(
        {GateAllowlistKey("f.py", "nonexistent", "gone")}, live
    )
    assert stale == [GateAllowlistKey("f.py", "nonexistent", "gone")]


def test_staleness_failure_message_prints_nearest_live_token() -> None:
    """The evict-or-re-approve message lists live tokens for the same qualname."""
    live = {
        GateAllowlistKey("f.py", "a.b", "live_token = call ( )"),
        GateAllowlistKey("g.py", "other", "unrelated"),
    }
    stale = [GateAllowlistKey("f.py", "a.b", "old_token = call ( )")]
    msg = format_staleness_failure(stale, live)
    assert "old_token = call ( )" in msg
    assert "live_token = call ( )" in msg  # freshen hint = copy-paste the live token
    # A stale key whose qualname vanished entirely tells the reader to EVICT.
    gone = [GateAllowlistKey("f.py", "removed_fn", "x = 1")]
    assert "EVICT" in format_staleness_failure(gone, live)


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
        f"the C-001 pin ({pinned}) must match a live call site — re-approve the "
        "frozen token (re-run freeze_converter.py or copy the live token)"
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

    # Sanctioned → gate PASSES. The sanction key is TOOL-DERIVED from the live
    # scan (contract rule 2 — no hand-typed token); ``rel_path`` is the tmp path,
    # so it cannot be hard-coded.
    site_key = next(
        s.key
        for s in scan_canonicalizer_call_sites(scratch_src)
        if s.key.enclosing_qualname == "ScratchHandler.run"
    )
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

    # Tool-derived sanction key (contract rule 2 — no hand-typed token).
    site_key = next(
        s.key
        for s in scan_coord_authority_call_sites(scratch_src)
        if s.key.enclosing_qualname == "ScratchWriter.persist"
    )
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


# --- T005 theater TRIAD: drift-green / content-red / new-offender-red -------
# Every leg drives the TOP-LEVEL CI entry point (``check_canonicalizer_gate`` /
# ``check_coord_authority_gate``) against a synthetic source + a loaded allowlist
# (contract rule 4). The allowlisted synthetic site is deliberately
# VIOLATION-CLASS (a raw-handle canonicalizer call / a write-classified coord
# call — the same class the T005 self-mutation tests inject), so the content leg
# reds the ENTRY POINT itself when the token drifts (the frozen key no longer
# matches the live site → the site reports as a violation), never a helper.


@dataclass(frozen=True)
class _TheaterCase:
    """One gate's synthetic-source variants for the drift/content/offender legs."""

    gate: str
    scan: Callable[[Path], Sequence[CanonicalizerSite]] | Callable[[Path], Sequence[CoordAuthoritySite]]
    check: Callable[[Path, set[GateAllowlistKey]], list[str]]
    offender_qual: str  # the allowlisted (violation-class) site
    second_qual: str  # the NEW un-allowlisted offender
    base: str  # violation-class site, unsanctioned → reds
    drift: str  # base + a REAL blank line above the call (same token/qualname)
    edited: str  # base with the call's token content changed
    two_offenders: str  # base + a second, distinct offending call


_CANON_CASE = _TheaterCase(
    gate="canonicalizer",
    scan=scan_canonicalizer_call_sites,
    check=check_canonicalizer_gate,
    offender_qual="R.run",
    second_qual="R.run2",
    base=(
        "class R:\n"
        "    def run(self, repo_root, raw_slug):\n"
        "        return primary_feature_dir_for_mission(repo_root, raw_slug)\n"
    ),
    drift=(
        "class R:\n"
        "    def run(self, repo_root, raw_slug):\n"
        "\n"  # a REAL inserted blank line ABOVE the call → +1 drift
        "        return primary_feature_dir_for_mission(repo_root, raw_slug)\n"
    ),
    edited=(
        "class R:\n"
        "    def run(self, repo_root, raw_slug):\n"
        "        renamed = raw_slug\n"  # still a raw (never-folded) handle → violation-class
        "        return primary_feature_dir_for_mission(repo_root, renamed)\n"
    ),
    two_offenders=(
        "class R:\n"
        "    def run(self, repo_root, raw_slug):\n"
        "        return primary_feature_dir_for_mission(repo_root, raw_slug)\n"
        "    def run2(self, repo_root, other):\n"
        "        return primary_feature_dir_for_mission(repo_root, other)\n"
    ),
)

_COORD_CASE = _TheaterCase(
    gate="coord_authority",
    scan=scan_coord_authority_call_sites,
    check=check_coord_authority_gate,
    offender_qual="W.persist",
    second_qual="W.persist2",
    base=(
        "class W:\n"
        "    def persist(self, ctx, slug):\n"
        "        d = resolve_feature_dir_for_mission(ctx, slug)\n"
        "        (d / 'x.txt').write_text('y')\n"
    ),
    drift=(
        "class W:\n"
        "    def persist(self, ctx, slug):\n"
        "\n"  # a REAL inserted blank line ABOVE the resolve → +1 drift
        "        d = resolve_feature_dir_for_mission(ctx, slug)\n"
        "        (d / 'x.txt').write_text('y')\n"
    ),
    edited=(
        "class W:\n"
        "    def persist(self, ctx, slug, other):\n"
        "        d = resolve_feature_dir_for_mission(ctx, other)\n"  # token changed, still a write
        "        (d / 'x.txt').write_text('y')\n"
    ),
    two_offenders=(
        "class W:\n"
        "    def persist(self, ctx, slug):\n"
        "        d = resolve_feature_dir_for_mission(ctx, slug)\n"
        "        (d / 'x.txt').write_text('y')\n"
        "    def persist2(self, ctx, other):\n"
        "        e = resolve_feature_dir_for_mission(ctx, other)\n"
        "        (e / 'z.txt').write_text('q')\n"
    ),
)

_THEATER_CASES = [
    pytest.param(_CANON_CASE, id="canonicalizer"),
    pytest.param(_COORD_CASE, id="coord_authority"),
]


def _write_theater_scratch(tmp_path: Path, body: str) -> Path:
    """Write *body* to a scratch package and INVALIDATE the parse cache.

    The drift/content/offender legs rewrite the SAME file path across versions so
    the frozen key's ``rel_path`` component matches; the module-wide parse cache
    is keyed by src root, so it must be popped or the second scan returns the
    stale first version (masking the drift).
    """
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "site.py").write_text(body, encoding="utf-8")
    src = tmp_path / "src"
    _parsed_trees.pop(str(src.resolve()), None)
    return src


def _theater_key(case: _TheaterCase, src: Path, qualname: str) -> GateAllowlistKey:
    """Tool-derive (never hand-type) the composite key for *qualname* under *src*."""
    return next(s.key for s in case.scan(src) if s.key.enclosing_qualname == qualname)


@pytest.mark.parametrize("case", _THEATER_CASES)
def test_theater_drift_leg_stays_green(case: _TheaterCase, tmp_path: Path) -> None:
    """Drift leg: +1 line drift over an allowlisted violation-class site → GREEN.

    Freezes the composite key of a violation-class synthetic site, inserts a REAL
    blank line ABOVE the call, and re-drives the CI entry point. The composite key
    is content-addressed (qualname + frozen token), so the pure line shift leaves
    it unchanged and the site stays sanctioned — zero violations.
    """
    base_src = _write_theater_scratch(tmp_path, case.base)
    frozen = _theater_key(case, base_src, case.offender_qual)
    # Sanity: the base site is genuinely violation-class (reds when unsanctioned).
    assert case.check(base_src, set()), f"{case.gate}: base site must be a violation"
    drift_src = _write_theater_scratch(tmp_path, case.drift)
    assert case.check(drift_src, {frozen}) == [], (
        f"{case.gate}: a +1 line drift red the gate — the key is NOT drift-proof "
        "(a stringified-line token would fail here)"
    )


@pytest.mark.parametrize("case", _THEATER_CASES)
def test_theater_content_leg_reds_entry_point(case: _TheaterCase, tmp_path: Path) -> None:
    """Content leg: editing the allowlisted site's token reds the ENTRY POINT.

    The frozen key sanctions the base token. After a genuine content edit the live
    site's token differs, so the frozen key no longer matches → the still
    violation-class site is reported by ``check_*_gate`` itself (assertion target
    is the entry point, never a helper).
    """
    base_src = _write_theater_scratch(tmp_path, case.base)
    frozen = _theater_key(case, base_src, case.offender_qual)
    edited_src = _write_theater_scratch(tmp_path, case.edited)
    violations = case.check(edited_src, {frozen})
    assert violations, f"{case.gate}: token edit must red the gate (staleness)"
    leaf = case.offender_qual.rsplit(".", 1)[-1]
    assert any(leaf in v for v in violations), (
        f"{case.gate}: the reported violation must name the edited site {leaf!r}: {violations}"
    )


@pytest.mark.parametrize("case", _THEATER_CASES)
def test_theater_new_offender_leg_reds(case: _TheaterCase, tmp_path: Path) -> None:
    """New-offender leg: a second un-allowlisted offending call reds the gate.

    With the first site allowlisted (frozen), a distinct second offender in the
    same module produces a different composite key that is NOT sanctioned → the
    entry point reports it by name, while the allowlisted first site stays green.
    """
    base_src = _write_theater_scratch(tmp_path, case.base)
    frozen = _theater_key(case, base_src, case.offender_qual)
    two_src = _write_theater_scratch(tmp_path, case.two_offenders)
    violations = case.check(two_src, {frozen})
    assert violations, f"{case.gate}: a new un-allowlisted offender must red the gate"
    new_leaf = case.second_qual.rsplit(".", 1)[-1]
    first_leaf = case.offender_qual.rsplit(".", 1)[-1]
    assert any(new_leaf in v for v in violations), (
        f"{case.gate}: violation must name the NEW offender {new_leaf!r}: {violations}"
    )
    # The allowlisted first site is NOT re-reported (non-vacuity of the sanction).
    assert not any(
        f"({case.offender_qual})" in v and new_leaf not in v for v in violations
    ), f"{case.gate}: the allowlisted first site {first_leaf!r} must stay green"


# --- T005 within-function collision (speculative ``count:`` surface) --------
def test_within_function_collision_count_is_bidirectional(tmp_path: Path) -> None:
    """``count:`` occurrence semantics are checked BOTH directions (non-vacuous).

    Two byte-identical ``primary_feature_dir_for_mission`` calls in one function
    collapse to a SINGLE composite key (identical rel_path/qualname/token). A
    ``count: N`` qualifier requires exactly ``N`` live occurrences:

      * ``count: 2`` with 2 live sites  → GREEN;
      * ``count: 1`` with 2 live sites  → RED (a green-only assertion is vacuous);
      * ``count: 2`` with 1 live site   → RED.

    NOTE (design tracer): ``count:`` has ZERO real users in the shipped allowlist
    today — it is a deliberate speculative surface for a future within-function
    collision drain. ``test_real_allowlist_declares_no_count_qualifiers`` pins that.
    """
    body = (
        "class R:\n"
        "    def run(self, repo_root, raw_slug):\n"
        "        x = primary_feature_dir_for_mission(repo_root, raw_slug)\n"
        "        x = primary_feature_dir_for_mission(repo_root, raw_slug)\n"
        "        return x\n"
    )
    src = _write_theater_scratch(tmp_path, body)
    site_keys = [s.key for s in scan_canonicalizer_call_sites(src)]
    assert len(site_keys) == 2, "fixture must produce two identical-token sites"
    assert len(set(site_keys)) == 1, "identical token+qualname+file must collapse to one key"
    key = site_keys[0]

    assert occurrence_count_violations(site_keys, {key: 2}) == []  # 2 required, 2 live → green
    assert occurrence_count_violations(site_keys, {key: 1})  # 1 required, 2 live → red
    assert occurrence_count_violations(site_keys[:1], {key: 2})  # 2 required, 1 live → red


def test_real_allowlist_declares_no_count_qualifiers() -> None:
    """Design tracer pin: the shipped allowlist declares no ``count:`` (zero users)."""
    assert load_occurrence_counts(ALLOWLIST_PATH) == {}, (
        "``count:`` is a speculative surface — a real user appeared; wire "
        "occurrence_count_violations into the gate proper before relying on it"
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
    """Concrete floor: >= 4 WRITE-classified coord call sites (NFR-002), floor tight.

    4 is the hard-coded live write-candidate census (NOT ``>= len(scanned)`` —
    that is tautological). Sites that sit in a function carrying a write indicator,
    OR that live in a file listed in ``_COORD_WRITE_BY_DESIGN`` (write-classified
    by design and sanctioned in the allowlist). History: WP08 set this to the
    then-honest census of 17; the single-authority mission's WP06 routing moved 3
    write-classified sites onto the kind-aware seam, so WP07 tightened the floor
    17 → 14. The 2026-06-27 rebase onto upstream/main carried concurrent mission
    #1057, which inserted a ``check_pre30_layout`` boundary guard into
    ``list_dependents`` — re-introducing a kind-blind resolve probe — raising the
    honest census 14 → 15. Further routing then shrank it 15 → 13, and
    retire-standalone-tasks-cli WP04's deletion of the standalone scripts/tasks
    surface shrank it 13 → 12. tasks-py-degod WP01-WP08's de-god rewires of
    ``tasks.py`` drained THREE write-census sites (``move_task`` ×2 via the WP06
    thin-orchestrator rewrite; ``list_dependents`` via the WP08 fold-to-primary),
    shrinking the live census 12 → 9. Then, tasks-py-degod-wave2's WP04
    render-seam unification removed the ``dumps`` write-indicator from
    ``list_tasks`` / ``validate_workflow`` (emission routed through
    ``Render.json_envelope``), re-classifying their surviving STATUS-partition
    probes as reads — census 9 → 7; wave-2 WP09 lowered this floor accordingly
    (SHRINK-ONLY). read-surface-ssot-closeout WP04 (T017/T018) routed all FOUR
    workflow.py write-census sites (``implement`` ×2, ``review`` ×2) through the
    kind-aware placement seam (``_resolve_workflow_read_dir`` /
    ``_resolve_workflow_placement``); WP05 then routed implement.py's
    detect-feature-context read, shrinking the live census 7 → 2 (only the 2
    by-design coord-owned writes — ``decisions/emit.py``, ``widen/state.py`` —
    remained). Finally, WP11 (FR-003 predicate-widen) discovered that the
    write-vs-read predicate had been BLIND to two more legitimate coord-owned
    write helpers (``agent_tasks_ports.py:feature_write_dir``,
    ``lanes/recovery.py:reconcile_status`` — write indicator one hop outside the
    function-granularity trace); widening ``_COORD_WRITE_BY_DESIGN`` surfaces
    both as WRITE-classified for the first time. This is a GENUINE CENSUS GAIN
    (previously-unseen legitimate writes, not un-routed regressions), raising
    the live census 2 → 4; floor raised 2 → 4 to match, and both new sites are
    sanctioned in the allowlist (baseline 2 → 4). The ``coord_authority_baseline``
    scalar caps the allowlist *entry count*, a different quantity from the write
    *site* census (which they happen to equal here).

    Two bounds are asserted (mirroring ``test_routed_count_floor``):
    * lower — ``live >= floor``: the census may not silently drop below the floor;
    * margin — ``live - floor <= MARGIN``: the floor may not sit materially BELOW
      the live count. A floor dropped far below live would let a body of un-routed
      kind-blind writes pass unseen (masking); the margin makes that CI-red.
    """
    writes = [s for s in scan_coord_authority_call_sites(SRC_ROOT) if s.is_write]
    assert len(writes) >= COORD_AUTHORITY_WRITE_FLOOR, (
        f"write-candidate census dropped to {len(writes)}; expected "
        f">= {COORD_AUTHORITY_WRITE_FLOOR}."
    )
    # Margin gate (anti-masking): the floor must track the honest live count. A
    # floor set materially below live would hide un-routed writes — fail it.
    assert len(writes) - COORD_AUTHORITY_WRITE_FLOOR <= COORD_AUTHORITY_WRITE_FLOOR_MARGIN, (
        f"COORD_AUTHORITY_WRITE_FLOOR ({COORD_AUTHORITY_WRITE_FLOOR}) is more than "
        f"COORD_AUTHORITY_WRITE_FLOOR_MARGIN ({COORD_AUTHORITY_WRITE_FLOOR_MARGIN}) "
        f"below the live write census ({len(writes)}); raise the floor to the honest "
        "live count so it cannot mask un-routed kind-blind writes."
    )


# --- T036: NFR-002 non-vacuity — the floor cannot be pinned above a
# plausible regressed census -------------------------------------------------
def test_coord_authority_floor_non_vacuous_against_reverted_by_design_write() -> None:
    """NFR-002 non-vacuity: un-classifying a WP11 by-design write REDS the floor.

    WP11 widened ``_COORD_WRITE_BY_DESIGN`` to surface two previously-unseen
    coord-owned write helpers (``agent_tasks_ports.py:feature_write_dir``,
    ``lanes/recovery.py:reconcile_status``) that the write-vs-read predicate had
    silently classified as reads. ``COORD_AUTHORITY_WRITE_FLOOR`` was raised
    2 -> 4 to match. This test proves that raise has teeth: it is NOT pinned so
    high that a plausible future regression — someone reverting either site's
    by-design classification back to an unflagged READ outside the seam (the
    exact blind spot this WP fixed) — would silently pass CI. Using ONLY the
    real live scan (no source mutation, no allowlist mutation), it simulates
    that regression by re-excluding the two WP11 sites from the write set and
    asserts the resulting count drops below the pinned floor — i.e. the primary
    ``>= COORD_AUTHORITY_WRITE_FLOOR`` assertion in ``test_coord_authority_gate_floor``
    would fire RED for this exact regression shape, not stay vacuously green.
    """
    live_sites = scan_coord_authority_call_sites(SRC_ROOT)
    wp11_surfaced_sites = frozenset(
        {"src/specify_cli/agent_tasks_ports.py", "src/specify_cli/lanes/recovery.py"}
    )
    # Sanity: the two WP11 sites are actually present and write-classified today
    # — otherwise this "regression" simulation would be vacuous (subtracting
    # nothing).
    live_wp11_writes = [
        s for s in live_sites if s.is_write and s.rel_path in wp11_surfaced_sites
    ]
    assert len(live_wp11_writes) == 2, (
        "sanity check failed: expected exactly the 2 WP11-surfaced by-design "
        f"writes live-classified as WRITE, got {len(live_wp11_writes)} "
        f"({[s.rel_path for s in live_wp11_writes]}) — the simulation below "
        "would be vacuous"
    )
    regressed_writes = [
        s for s in live_sites if s.is_write and s.rel_path not in wp11_surfaced_sites
    ]
    assert len(regressed_writes) < COORD_AUTHORITY_WRITE_FLOOR, (
        f"non-vacuity broken: reverting the 2 WP11 by-design sites to unseen "
        f"reads leaves {len(regressed_writes)} write-classified sites, which "
        f"must be < COORD_AUTHORITY_WRITE_FLOOR ({COORD_AUTHORITY_WRITE_FLOOR}) "
        "for the floor test to catch this regression shape. If this fails, the "
        "floor is pinned high enough to mask a silent by-design reversion."
    )


def test_allowlist_no_stale_entries() -> None:
    """NFR-003 twin-guard: every YAML entry matches a live call site (real tree)."""
    keys = load_allowlist(ALLOWLIST_PATH)
    live = _live_canonicalizer_keys(SRC_ROOT) | _live_coord_authority_keys(SRC_ROOT)
    all_allowlist = set(keys["canonicalizer"]) | set(keys["coord_authority"])
    stale = staleness_twin_guard(all_allowlist, live)
    assert stale == [], (
        "stale allowlist entries (frozen token no longer matches a live call site) "
        "— evict or re-approve (shrink-only):\n" + format_staleness_failure(stale, live)
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
