"""Inline meta.json read ratchet — the FIRST gate over raw ``json.loads``/``json.load``
reads of ``meta.json`` files that bypass the canonical
:func:`specify_cli.mission_metadata.load_meta` family.

Mission ``read-surface-ssot-closeout-01KWZV91`` / WP16.
Requirements: FR-006, NFR-002, SC-002 (IC-06).
Contract: ``kitty-specs/read-surface-ssot-closeout-01KWZV91/contracts/meta-read-ratchet.md``.

Thread B (WP05/06/07 + WP12-15) routed every non-migration, non-charter caller of
inline meta.json JSON parsing onto ``mission_metadata.load_meta`` /
``load_meta_strict`` / ``load_meta_or_empty``. This module stands up the
structural (CI-red on regression) gate that keeps the drained class from
regrowing. **Non-vacuous** — modeled on
``test_resolution_authority_gates.py`` + ``resolution_gate_allowlist.yaml``, this
gate implements the SAME four mechanics (not a weaker shape):

1. **Integer floor** — ``INLINE_META_READ_FLOOR`` is the live post-drain census;
   the live inline-read count MUST be ``<= floor`` (a shrink-only CEILING, unlike
   the canonicalizer's growth-oriented floor: fewer inline reads is progress).
2. **Margin** — ``FLOOR_MARGIN`` bounds how far ABOVE the live count the floor may
   be pinned (``floor - live <= margin``); a floor pinned far above live would
   mask a future regression that grows the inline-read count back up toward it.
3. **Routed-count floor (anti-mass-allow-list)** — mirrors
   ``ROUTED_CANONICALIZER_FLOOR``: the number of call sites routed through
   ``load_meta`` / ``load_meta_strict`` / ``load_meta_or_empty`` has its own
   floor and can only rise. This is independent of the allow-list, so "draining"
   the inline-read floor by mass-allow-listing sites (instead of routing them)
   manufactures zero routed evidence and is structurally distinguishable.
4. **Composite-key allow-list with stale-entry detection** — each deferred site
   is a ``{key, rationale, issue}`` entry; ``allowlist_keys - live_keys``
   non-empty fails the build (a routed-away entry must be evicted, never left
   masking a drained site).

The scanner excludes ``mission_metadata.py`` (the canonical reader's own
implementation, whose internal ``json.loads`` calls ARE the authority, not a
violation of it) and the ``task_utils`` path-signature adapter (a thin,
behavior-preserving wrapper around the canonical reader — see
``task_utils/support.py::load_meta`` docstring).
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tests.architectural._ratchet_keys import code_tokens_by_line

pytestmark = pytest.mark.architectural

# --------------------------------------------------------------------------- #
# Source-tree roots (repo-root independent).
# this file: <root>/tests/architectural/test_inline_meta_read_gate.py
# --------------------------------------------------------------------------- #
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parents[2]
SRC_ROOT = _REPO_ROOT / "src"
ALLOWLIST_PATH = _THIS.parent / "inline_meta_read_allowlist.yaml"

# SC-005 / NFR-004 control fixtures. They live under ``tests/architectural/_fixtures/``
# and NOT under ``src/`` on purpose: ``scan_inline_meta_reads`` walks ``SRC_ROOT``, so
# the positive twin's fully-inlined read placed there would raise the live inline census
# and red ``test_inline_meta_read_floor`` — the floor the control exists to prove.
FIXTURES_DIR = _THIS.parent / "_fixtures"
UNREACHABILITY_CONTROL_REL = "tests/architectural/_fixtures/unreachability_control.py"
UNREACHABILITY_TWIN_REL = "tests/architectural/_fixtures/unreachability_control_twin.py"

# Per contract: the canonical reader's own internals, and the task_utils
# path-signature adapter, are excluded from the INLINE-READ scan.
EXCLUDED_REL_PATHS: frozenset[str] = frozenset(
    {
        "src/specify_cli/mission_metadata.py",
        "src/specify_cli/task_utils/support.py",
    }
)

# The variable-name heuristic half of the scanner (contract rule: var names
# ``meta_path|meta_file|meta_json|target_meta_path``).
META_PATH_VAR_NAMES: frozenset[str] = frozenset(
    {"meta_path", "meta_file", "meta_json", "target_meta_path"}
)

# The canonical reader family a routed call site targets.
#
# ``load_meta_fail_closed`` joined this family in mission
# ``doctrine-charter-split-unification`` (FR-007 / #3140): it is the ONE public
# fail-closed reader, a thin typed-contract wrapper that DELEGATES to the
# canonical ``load_meta`` parser. Routing a caller onto it is therefore routing
# THROUGH the canonical authority, not away from it. Omitting it here made this
# floor read FR-007's routing as a drain (120 -> 103) and fail.
#
# ``_load_meta_fail_closed`` and ``_require_meta`` joined this family in the
# PR #3175 landing pass (2026-08-04), fixing a THIRD recurrence of the same
# census/floor mismatch. Commit 60b0bf2a2 ("landing fold: route 13
# authority-bucket sites through the fail-closed wrapper") introduced these two
# module-private helpers in ``src/specify_cli/mission_metadata.py`` and
# collapsed 13 literal call sites onto them, mechanically dropping the routed
# census 120 -> 110 without adding the new delegating names here. Verified
# delegation chain (not an independent reader): ``mission_metadata._require_meta``
# calls ``mission_metadata._load_meta_fail_closed``, which calls
# ``core.paths.load_meta_fail_closed`` (via a deferred import — see that
# function's own docstring), which calls ``mission_metadata.load_meta`` (the
# canonical parser) directly. Every call site that moved onto ``_require_meta``/
# ``_load_meta_fail_closed`` still reaches ``load_meta``; it lost census credit
# only because the scanner matches callee *names*, not the transitive call
# graph. Adding the two names here is the fix this gate's structure supports.
#
# AMENDED by mission ``meta-fail-closed-3162-01KZ7FSQ`` / WP06 (FR-006). This
# paragraph used to end "it does no call-graph resolution, so a full transitive walk
# would be a larger structural change than this landing fold warrants", and that
# became false. Two things are now true, and they are different:
#
# * The ROUTED census above still does **no** call-graph resolution at all. It
#   matches callee names, which is why delegating wrappers must be enrolled in
#   :data:`ROUTED_CALLEES` by hand.
# * The INLINE scanner now carries **one** bounded intra-module hop
#   (:data:`_MAX_PARSE_HELPER_HOPS` == 1): from a ``json.loads`` whose argument is the
#   unbound parameter of a private, module-level, single-parameter function, to that
#   function's call sites **in the same file**. It does not recurse, does not cross a
#   module boundary, and does not build a call graph.
#
# A full transitive walk remains **out of scope** — it is a larger structural change
# than this gate's shape warrants, and the ``git show``/``show_blob``-fed reads it
# would still not reach need a different detector entirely (FR-007 deferral).
ROUTED_CALLEES: frozenset[str] = frozenset(
    {
        "load_meta",
        "load_meta_strict",
        "load_meta_or_empty",
        "load_meta_fail_closed",
        "_load_meta_fail_closed",
        "_require_meta",
    }
)

# --------------------------------------------------------------------------- #
# Concrete integer floors (NFR-002). Live census measured on this tree via
# scan_inline_meta_reads(SRC_ROOT) / scan_routed_load_meta_calls(SRC_ROOT) — NOT
# ``<= huge`` / ``>= 0`` placeholders (NFR-002 rejects vacuous bounds).
#
# WP16 (mission read-surface-ssot-closeout-01KWZV91): post Thread-B drain
# (WP05/06/07 + WP12-15), the live inline-read census is exactly the 5 known
# deferred files (7 call sites) allow-listed below — 3 migrations that must
# tolerate legacy/malformed meta.json shapes the canonical reader would reject,
# plus 2 ``src/charter/`` sites that would otherwise introduce a cross-package
# dependency on ``specify_cli.mission_metadata`` (Shared Package Boundary ADR).
#
# RE-DERIVED and CONFIRMED 7 by mission ``meta-fail-closed-3162-01KZ7FSQ`` / WP06
# (FR-008), in the same commit as the scanner widening it is coupled to. Measured on
# this tree over 1 199 ``*.py`` files under ``src/``: live inline == 7. Two changes
# landed together and neither moved it. (a) The ``read_bytes`` arm of
# :func:`_extract_read_base` matches 0 additional sites here. (b) The one-hop
# parse-helper anchor (:data:`_MAX_PARSE_HELPER_HOPS`) was built to reach
# ``specify_cli.git.ref_advance._meta_change_is_vcs_lock_only``'s delegated parse —
# but WP05 had already ROUTED that site onto ``core.paths.load_meta_fail_closed``, so
# the widened scanner finds nothing there to flag and the census holds at 7 rather
# than rising to 8. Measured directly: the SAME widened predicate over the
# pre-WP05 measurement baseline ``96494e5ec`` reports 8, naming
# ``ref_advance.py:247 (_meta_change_is_vcs_lock_only)`` as the 8th. This is the
# CEILING ratchet's intended reading: the widening proved the shape is now reachable,
# and the routing means there is nothing left in it. NO allow-list entry was written
# and ``inline_meta_read_baseline`` stays 7 (FR-007): the remaining bypass shapes are
# ``git show``/``show_blob``-fed and are invisible to the scanner, so an entry for one
# would be stale on arrival at ANY baseline and red under
# :func:`test_allowlist_entries_are_still_live`.
INLINE_META_READ_FLOOR = 7

# This is a CEILING-type ratchet (fewer inline reads is progress, unlike the
# canonicalizer's growth-oriented floor) so the margin bounds the gap the OTHER
# direction: the floor may not be pinned more than MARGIN calls ABOVE the live
# count (which would mask a future regression that grows the count back toward
# it). At INLINE_META_READ_FLOOR == live == 7 today, the gap is 0.
#
# RE-DERIVED against the same measured live count by WP06 (FR-008), and left at 2:
# gap == INLINE_META_READ_FLOOR - live == 7 - 7 == 0, which is admissible under any
# non-negative margin, so the measurement constrains the margin from below at 0 and
# does not force a value. 2 is kept as the standing headroom rather than tightened to
# 0, because a 0 margin would convert every legitimate one-site drain into a required
# same-commit floor edit. The gap is the number that must stay small, and it is 0.
FLOOR_MARGIN = 2

# WP16 SC-004-equivalent anti-mass-allow-list guard: the number of call sites
# routed through load_meta/load_meta_strict/load_meta_or_empty has its own
# floor and can only rise. Live routed census on this tree is 120 (includes
# mission_metadata.py's own internal call sites — e.g. load_meta_strict/
# load_meta_or_empty delegating to load_meta, and the module's many other
# public helpers reading meta.json through the one canonical primitive; those
# ARE genuine routed-usage evidence, not the read implementation itself, which
# is why mission_metadata.py is excluded from the INLINE scan but NOT from this
# routed-usage census — plus the import-history SCAN's own load_meta_or_empty
# call, #2262). Floor (117) sits 3 below the live count (within MARGIN(4)) and
# strictly below it, so the anti-vacuity check proves the census is not merely
# equal to a hand-entered value.
#
# Raised 117 -> 120 by mission runtime-state-birth-cutover-all-paths-01KYH654:
# the live census rose 120 -> 123 because this mission routed NEW reads through
# the canonical primitive instead of adding inline ones — the ratchet moving in
# its intended direction. The companion INLINE_META_READ_FLOOR was deliberately
# NOT touched: routing ``status.cutover_eligibility`` through ``load_meta``
# drained the inline census back under its existing ceiling on its own.
#
# Raised 120 -> 123 by mission doctrine-charter-split-unification (FR-007 /
# #3140): ``load_meta_fail_closed`` joined ROUTED_CALLEES (see its comment
# above) and WP08/WP09 routed the census's unwrapped/divergent readers onto it,
# so the live count rose 123 -> 126. The ratchet again moved in its intended
# direction — these sites did not stop routing through the canonical authority,
# they moved onto its typed fail-closed contract.
#
# Lowered -> 117 by "landing fold: collapse 7 duplicated meta-guard blocks
# in doc_state.py into one helper" (commit 190932c2d, PR #3155 landing pass):
# that fold legitimately consolidated 7 duplicated inline
# ``load_meta_fail_closed(...)`` call sites in doc_state.py into ONE shared
# ``_require_meta()`` helper that itself calls ``load_meta_fail_closed`` once.
# Routing COVERAGE is unchanged — all 7 original call sites still ultimately
# route through the canonical reader, just via one shared helper instead of 7
# duplicated inline calls — but this test counts literal source-text
# occurrences of routed calls, so deduplication mechanically dropped the live
# count toward 120 (the value this fold's floor was pinned against). This is
# the CEILING-ratchet's inverse case (cf. INLINE_META_READ_FLOOR above): a
# legitimate drop from good deduplication, not a coverage regression. The
# floor was set to 117 to preserve the established 3-below-live gap
# (mechanic 2) and keep the anti-vacuity check
# (``len(routed) > ROUTED_LOAD_META_FLOOR``) strictly satisfied.
#
# NOTE ON THIS COMMENT'S OWN HISTORY: the paragraph above and the one before it
# previously carried internally-inconsistent numbers (a "120 -> 123" header
# followed by "rose 123 -> 126" body text, then a "123 -> 120" drop claim
# immediately followed by "floor is set to 117 (not 120)") that did not
# reconcile with each other or with any measured tree. This is corrected here
# rather than re-derived a further time: trust the dated entries below, which
# are each backed by a command actually run against a real tree, not narrative
# arithmetic.
#
# DROPPED 120 -> 110 by commit 60b0bf2a2 ("landing fold: route 13
# authority-bucket sites through the fail-closed wrapper", PR #3175 landing
# pass, pre-existing on main): that fold introduced the module-private
# delegating helpers ``mission_metadata._load_meta_fail_closed`` and
# ``mission_metadata._require_meta`` and moved 13 literal
# ``load_meta_fail_closed(...)`` call sites onto them, collapsing the visible
# text down to 3 direct calls plus the helpers' own internal delegation. Every
# one of those 13 sites still reaches ``load_meta`` (verified delegation
# chain: ``_require_meta`` -> ``_load_meta_fail_closed`` ->
# ``core.paths.load_meta_fail_closed`` -> ``mission_metadata.load_meta``), but
# neither helper name was added to :data:`ROUTED_CALLEES`, so the census
# mechanically dropped even though routing coverage did not regress — this is
# the SAME shape as the PR #3155 drop two paragraphs above (the THIRD
# recurrence of this exact census/floor mismatch). ``ROUTED_LOAD_META_FLOOR``
# (117) was left unmoved across this drop, which is what turned it into a
# false-red CI failure: measured directly via
# ``PWHEADLESS=1 uv run pytest tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor``
# on 2026-08-04, live == 110 < 117.
#
# FIXED 2026-08-04 (PR #3175 landing pass, this fold): added
# ``_load_meta_fail_closed`` and ``_require_meta`` to :data:`ROUTED_CALLEES`
# (see that constant's comment) so the census counts calls that reach the
# canonical reader through these verified delegating wrappers, not just literal
# calls to the four previously-named callees. Re-measured via
# ``uv run python -c "from tests.architectural.test_inline_meta_read_gate import
# scan_routed_load_meta_calls, SRC_ROOT; print(len(scan_routed_load_meta_calls(SRC_ROOT)))"``
# on the same tree: live == 129 (110 + 12 newly-counted call sites in
# ``mission_metadata.py`` + 7 in ``doc_analysis/doc_state.py``, whose OWN
# locally-defined ``_require_meta`` also delegates to ``load_meta_fail_closed``
# — same name, same delegating shape, independently verified). Floor raised
# 117 -> 126 to restore the established 3-below-live gap (mechanic 2) against
# the corrected 129, strictly satisfying the anti-vacuity check.
#
# FIXED 2026-08-05 (PR #3211 landing pass, F3): the 10 landing folds already
# applied to this tree grew the routed census further -- measured directly
# via ``PWHEADLESS=1 uv run pytest
# tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor``,
# live == 131 > 126 + margin(4). No delegation-chain regression; genuine
# growth in routed call sites. Floor raised 126 -> 128 to restore the
# established 3-below-live gap (mechanic 2) against the corrected 131,
# strictly satisfying the anti-vacuity check (same convention as the two
# prior entries above).
# RAISED 126 -> 127 on 2026-08-06 by mission ``meta-fail-closed-3162-01KZ7FSQ`` /
# WP06 (FR-008), applying the SAME rule as the 2026-08-04 entry above — restore the
# established 3-below-live gap — to a freshly MEASURED live count, not to a copied
# number. WP05 spent this mission's single allocated net routed call, routing
# ``specify_cli.git.ref_advance._meta_change_is_vcs_lock_only`` (``ref_advance.py:260``)
# onto ``specify_cli.core.paths.load_meta_fail_closed`` (the call at
# ``ref_advance.py:299``), which took live routed 129 -> 130. Measured on this tree
# over 1 199 ``*.py`` files under ``src/`` via
# ``PYTHONPATH=<tree>/src .venv/bin/python scripts/verify_meta_routing_manifest_3162.py``:
# live == 130. Arithmetic: 130 - 3 = 127. Resulting band ``[FLOOR+1, FLOOR+MARGIN]``
# == ``[128, 131]``. Three clauses of :func:`test_routed_load_meta_floor` at the new
# floor: 130 >= 127; 130 > 127 (STRICT — the anti-vacuity clause, and the reason the
# bound is two-sided rather than a one-way ratchet, so a FOLD that collapses two
# routed calls into one reds this gate from BELOW); 130 - 127 == 3 <= 4.
#
# WHY THIS MOVED AT ALL, since the gate was green without it: at live 130 with the
# old floor 126 and margin 4, all three clauses still passed (130 >= 126; 130 > 126;
# 130 - 126 == 4 <= 4) — the gap had merely drifted out to exactly the margin, one
# routed call away from a false red. A floor left at 126 is a floor that was never
# re-derived; leaving it there is indistinguishable, from the outside, from skipping
# the measurement. The recurring failure this gate has logged three times above is
# precisely a floor that stopped tracking its live count.
# RE-DERIVED 126 -> 131 on 2026-08-06 when mission ``meta-fail-closed-3162-01KZ7FSQ``
# rebased onto ``upstream/main`` d0ed802cc. BOTH provenance entries above are retained
# because both are true of their own tree, and NEITHER floor is correct here:
#
#   * PR #3211 measured live 131 on ITS tree and set floor 128.
#   * WP06 measured live 130 on the mission's pre-rebase tree and set floor 127.
#
# The two trees routed LARGELY DISJOINT site sets — upstream's ``resolution.py`` carried
# 0 ``load_meta_fail_closed(`` calls where the mission's carried 3, yet upstream's total
# (133) exceeded the mission's (130) — so the merged count is neither number. Measured on
# the merged tree with the gate's own scanner, the imported ``specify_cli.__file__``
# printed as the control: live == **134**, which is upstream's 133 plus the mission's
# single allocated net routed call (WP05's ``ref_advance._meta_change_is_vcs_lock_only``).
# Arithmetic, same 3-below-live rule as every entry above: 134 - 3 = 131. Band
# ``[FLOOR+1, FLOOR+MARGIN]`` == ``[132, 135]``. Three clauses at the new floor:
# 134 >= 131; 134 > 131 (STRICT anti-vacuity, so a FOLD reds this gate from BELOW);
# 134 - 131 == 3 <= 4.
#
# NOTE ON WHY THIS IS A FIX, NOT A BUMP: ``upstream/main`` d0ed802cc was measured RED on
# this very gate before the rebase — live 133 against floor 128 fails
# ``(133 - 128) <= 4``. Routing landed upstream without the floor being re-derived. This
# re-derivation clears that red as a side effect; it is a contract crossing re-pinned with
# its measurement, not a ceiling raised to make a test pass.
ROUTED_LOAD_META_FLOOR_MARGIN = 4
ROUTED_LOAD_META_FLOOR = 131


# --------------------------------------------------------------------------- #
# Composite-key allow-list machinery (mechanic 4).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class InlineMetaReadKey:
    """Composite Design-P allow-list key surviving benign line drift.

    ``rel_path`` is the repo-relative source path, ``enclosing_qualname`` is the
    dotted chain of enclosing ``def``/``class`` names (or ``"<module>"`` at file
    scope), and ``token`` is the FROZEN tool-derived ``code_tokens_by_line``
    string of the call's line — the authoritative content comparand, never a raw
    line number.
    """

    rel_path: str
    enclosing_qualname: str
    token: str


class AllowlistEntryError(ValueError):
    """Raised when a YAML allow-list entry is malformed (missing a required field)."""


def _require_str(mapping: dict[str, object], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AllowlistEntryError(
            f"allow-list entry {context} is missing a non-empty {key!r} field "
            f"(got {value!r}); every deferred site needs an explicit {key} — no silent drift"
        )
    return value


def load_allowlist(path: Path) -> list[InlineMetaReadKey]:
    """Load the governance YAML's ``inline_meta_read`` entries.

    Each entry carries ``file:``, ``qualname:``, ``token:`` (the composite key),
    plus mandatory ``rationale:`` and ``issue:`` fields (contract rule 4 — every
    deferred entry is a ``{key, rationale, issue}`` triple) and an optional,
    non-authoritative ``line:`` locator. A missing/empty ``rationale``, ``issue``,
    or ``token`` raises :class:`AllowlistEntryError`.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = raw.get("inline_meta_read") or []
    keys: list[InlineMetaReadKey] = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise AllowlistEntryError(f"inline_meta_read[{idx}] is not a mapping (got {entry!r})")
        context = f"inline_meta_read[{idx}]"
        rel_path = _require_str(entry, "file", context)
        qualname = _require_str(entry, "qualname", context)
        token = _require_str(entry, "token", context)
        _require_str(entry, "rationale", context)
        _require_str(entry, "issue", context)
        line = entry.get("line")
        if line is not None and not isinstance(line, int):
            raise AllowlistEntryError(f"{context} ({qualname!r}) has a non-integer line locator {line!r}")
        keys.append(InlineMetaReadKey(rel_path, qualname, token))
    return keys


def load_baseline(path: Path) -> int:
    """Return the recorded pre-sweep baseline scalar (shrink-only governance)."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    value = raw.get("inline_meta_read_baseline")
    if not isinstance(value, int):
        raise AllowlistEntryError(f"inline_meta_read_baseline scalar missing or non-integer in {path.name}")
    return value


def staleness_twin_guard(
    allowlist_keys: set[InlineMetaReadKey], live_keys: set[InlineMetaReadKey]
) -> list[InlineMetaReadKey]:
    """Return allow-list keys with no matching live call site (mechanic 4).

    A non-empty result is a stale-entry failure: the allow-list sanctions a site
    whose frozen token no longer matches any live call site — the entry must be
    evicted (routed away) or re-approved, never left silently masking.
    """
    return sorted(
        allowlist_keys - live_keys, key=lambda k: (k.rel_path, k.enclosing_qualname, k.token)
    )


# --------------------------------------------------------------------------- #
# AST helpers — parent map / qualname / enclosing function.
# --------------------------------------------------------------------------- #
def _parent_map(tree: ast.Module) -> dict[int, ast.AST]:
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _qualname_from_parents(parents: dict[int, ast.AST], target: ast.AST) -> str:
    chain: list[str] = []
    cur: ast.AST | None = target
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            chain.append(cur.name)
        elif isinstance(cur, ast.Lambda):
            chain.append("<lambda>")
    return ".".join(reversed(chain)) if chain else "<module>"


def _enclosing_function(
    parents: dict[int, ast.AST], target: ast.AST
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    cur: ast.AST | None = target
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


def _callee_name(call: ast.Call) -> str | None:
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


def _iter_source_files(src_root: Path) -> list[Path]:
    return [p for p in sorted(src_root.rglob("*.py")) if "__pycache__" not in p.parts]


# --------------------------------------------------------------------------- #
# T045 — inline meta-read scanner.
# --------------------------------------------------------------------------- #
def _module_is_json(expr: ast.expr) -> bool:
    """True for a bare ``json`` name or a common alias (``import json as _json``)."""
    return isinstance(expr, ast.Name) and expr.id in ("json", "_json")


@dataclass(frozen=True)
class _JsonImportBindings:
    """This file's own local name bindings for the ``json`` module and its
    ``loads``/``load`` callables, resolved from its real ``import``/``from ... import``
    statements (module- or function-scoped, with optional ``as`` aliases).

    Closes evasion vector 2: a hardcoded ``json``/``_json`` attribute-access match
    (:func:`_module_is_json`) never sees ``from json import loads`` (a bare ``loads(...)``
    call) or an arbitrarily-aliased module import (``import json as j``). Resolving
    through the file's actual bindings instead of a literal string match catches both.
    """

    module_names: frozenset[str]
    loads_names: frozenset[str]
    load_names: frozenset[str]


def _collect_json_import_bindings(tree: ast.Module) -> _JsonImportBindings:
    """Scan *tree* for ``json`` imports and return their local name bindings.

    Covers ``import json`` / ``import json as X`` (recorded in ``module_names``) and
    ``from json import loads [as Y]`` / ``from json import load [as Z]`` (recorded in
    ``loads_names`` / ``load_names``). Walks the whole tree (not just module level) so
    a function-local ``import json as _json`` (a real pattern already in this codebase)
    is resolved too.
    """
    module_names: set[str] = set()
    loads_names: set[str] = set()
    load_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "json":
                    module_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "json":
            for alias in node.names:
                if alias.name == "loads":
                    loads_names.add(alias.asname or alias.name)
                elif alias.name == "load":
                    load_names.add(alias.asname or alias.name)
    return _JsonImportBindings(
        module_names=frozenset(module_names),
        loads_names=frozenset(loads_names),
        load_names=frozenset(load_names),
    )


def _is_json_loads_call(call: ast.Call, bindings: _JsonImportBindings | None = None) -> bool:
    """True for ``json.loads(...)`` (hardcoded ``json``/``_json`` fallback, or any real
    import binding in *bindings*) or a bare ``loads(...)`` bound via
    ``from json import loads``.
    """
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr == "loads":
        if _module_is_json(func.value):
            return True
        if bindings is not None and isinstance(func.value, ast.Name):
            return func.value.id in bindings.module_names
    if bindings is not None and isinstance(func, ast.Name):
        return func.id in bindings.loads_names
    return False


def _is_json_load_call(call: ast.Call, bindings: _JsonImportBindings | None = None) -> bool:
    """True for ``json.load(...)`` (hardcoded fallback or a real import binding) or a
    bare ``load(...)`` bound via ``from json import load``.
    """
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr == "load":
        if _module_is_json(func.value):
            return True
        if bindings is not None and isinstance(func.value, ast.Name):
            return func.value.id in bindings.module_names
    if bindings is not None and isinstance(func, ast.Name):
        return func.id in bindings.load_names
    return False


def _assigned_value(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> ast.expr | None:
    """Return the RHS (or ``with ... as name:`` context expr) of *name*'s binding in *fn*.

    One binding lookup (intra-function; not a full interprocedural data-flow
    analysis). Chaining multiple lookups to follow a ``Name = Name`` reassignment
    chain is :func:`_follow_assignment_chain`'s job, not this function's.
    """
    for node in ast.walk(fn):
        value, targets = _binding_candidate(node)
        for tgt in targets:
            if isinstance(tgt, ast.Name) and tgt.id == name:
                return value
    return None


# Cap on same-function ``Name = Name`` reassignment-chain hops
# (:func:`_follow_assignment_chain`) followed to reach a binding's ultimate source
# expression. Closes evasion vector 3 (``y = x`` indirection was previously
# unresolved past one hop) while staying intra-function/finite: this is def-use
# tracing local to one function, not a full interprocedural data-flow analysis, so
# a bound of 5 is a defense against pathological/circular chains rather than a
# claim of completeness -- a legitimate chain longer than 5 hops stays unresolved,
# same class of limitation the pre-existing one-hop resolution already carried.
_MAX_ASSIGNMENT_HOPS = 5


def _follow_assignment_chain(
    fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str, hops_remaining: int
) -> ast.expr | None:
    """Follow *name*'s most recent same-scope binding through further bare ``Name``
    bindings (``y = x``) up to *hops_remaining* hops.

    Returns the first non-``Name`` RHS expression reached, or ``None`` when *name*
    is unbound in *fn* or the hop budget is exhausted first -- a pathologically
    long or circular chain is treated as unresolved, never followed indefinitely.
    """
    if hops_remaining <= 0:
        return None
    bound = _assigned_value(fn, name)
    if bound is None:
        return None
    if isinstance(bound, ast.Name):
        return _follow_assignment_chain(fn, bound.id, hops_remaining - 1)
    return bound


def _binding_candidate(node: ast.AST) -> tuple[ast.expr | None, list[ast.expr]]:
    """Extract ``(value, targets)`` from an assignment-shaped node, or ``(None, [])``."""
    if isinstance(node, ast.Assign):
        return node.value, list(node.targets)
    if isinstance(node, ast.AnnAssign) and node.value is not None:
        return node.value, [node.target]
    if isinstance(node, ast.With):
        for item in node.items:
            if item.optional_vars is not None:
                return item.context_expr, [item.optional_vars]
    return None, []


# The bound-method read calls whose receiver IS the path expression.
# ``read_bytes`` joined ``read_text``/``open`` in mission
# ``meta-fail-closed-3162-01KZ7FSQ`` / WP06 (FR-006): ``json.loads`` accepts
# ``bytes`` as readily as ``str``, so ``json.loads(meta_path.read_bytes())`` was a
# bypass of exactly the same class as the ``read_text`` form the gate already caught.
# It adds 0 sites over ``src/`` on the tree where it landed, which is why its
# falsifiable control is the runtime-generated 1 -> 2 pair in
# ``test_read_bytes_scan_level_pin_moves_one_to_two`` rather than a live-census move.
_READ_METHOD_NAMES: frozenset[str] = frozenset({"read_text", "read_bytes", "open"})


def _extract_read_base(expr: ast.expr) -> ast.expr | None:
    """Return the path expression a read call reads from.

    Recognises ``X.read_text(...)``, ``X.read_bytes(...)``, ``X.open(...)`` and the
    builtin ``open(X, ...)``.
    """
    if not isinstance(expr, ast.Call):
        return None
    func = expr.func
    if isinstance(func, ast.Attribute) and func.attr in _READ_METHOD_NAMES:
        return func.value
    if isinstance(func, ast.Name) and func.id == "open" and expr.args:
        return expr.args[0]
    return None


def _read_source_base(
    arg: ast.expr, fn: ast.FunctionDef | ast.AsyncFunctionDef | None
) -> ast.expr | None:
    """Resolve *arg* (the sole positional arg to ``json.loads``/``json.load``) to its path base.

    Handles the inline forms (``X.read_text(...)``, ``open(X, ...)``, ``X.open(...)``)
    directly, and a bare ``Name`` resolved through up to :data:`_MAX_ASSIGNMENT_HOPS`
    intra-function reassignment hops (assignment, ``with ... as name:`` binding, or a
    ``Name = Name`` chain) to that form (e.g. ``meta_text = meta_path.read_text(...)``
    then ``json.loads(meta_text)``; ``with meta_json.open() as f: json.load(f)``; or the
    vector-3 two-hop shape ``y = x`` then ``json.loads(y.read_text())``).
    """
    resolved = arg
    if isinstance(resolved, ast.Name) and fn is not None:
        bound = _follow_assignment_chain(fn, resolved.id, _MAX_ASSIGNMENT_HOPS)
        if bound is not None:
            resolved = bound
    return _extract_read_base(resolved)


def _is_meta_json_join(expr: ast.expr) -> bool:
    """True for an inline ``<dir> / "meta.json"`` path join."""
    return (
        isinstance(expr, ast.BinOp)
        and isinstance(expr.op, ast.Div)
        and isinstance(expr.right, ast.Constant)
        and expr.right.value == "meta.json"
    )


def is_meta_path_expr(
    expr: ast.expr,
    fn: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
    hops: int = _MAX_ASSIGNMENT_HOPS,
) -> bool:
    """True when *expr* is a meta.json path.

    Either a canonical variable name (``meta_path``/``meta_file``/``meta_json``/
    ``target_meta_path`` -- kept as a direct match for parameters and other names
    with no in-scope binding to resolve), a direct ``<dir> / "meta.json"`` join, or
    -- when *fn* is supplied -- a bare, arbitrarily-named ``Name`` resolved
    structurally through up to *hops* same-function reassignment hops
    (:func:`_follow_assignment_chain`) to a join expression (evasion-vector-1 fix:
    the assignment-hop no longer requires the variable to be spelled one of the
    four canonical names). *fn* is optional and omitted by the unit tests that
    exercise the two-clause test in isolation; the real scanner always supplies it.
    """
    if isinstance(expr, ast.Name):
        if expr.id in META_PATH_VAR_NAMES:
            return True
        if fn is not None and hops > 0:
            bound = _follow_assignment_chain(fn, expr.id, hops)
            if bound is not None:
                return _is_meta_json_join(bound)
        return False
    return _is_meta_json_join(expr)


# --------------------------------------------------------------------------- #
# WP06 (FR-006) — the private same-module parse-helper anchor hop.
#
# EXACTLY ONE HOP, and the bound is enforced in code below, not merely described:
# from a ``json.loads``/``json.load`` whose sole argument is the UNBOUND parameter of
# a PRIVATE (``_``-prefixed), MODULE-LEVEL, SINGLE-PARAMETER function in the SAME
# file, to that function's call sites in that same file — where clauses 2 and 3 are
# then applied to the passed argument. A call site whose own argument is itself such
# a parameter is NOT followed further; the hop never recurses and never leaves the
# module. Research control ``C2b`` measured this shape at 0 sites before the hop
# existed: splitting a read and its parse across a helper hid the read, because
# ``json.loads``' argument was a parameter and ``_follow_assignment_chain`` is
# intra-function.
#
# The reported site is the CALL SITE, never the helper's ``json.loads`` line —
# allow-list keys are ``(file, qualname, token)``, so anchoring on the helper would
# point every such entry at the wrong function.
#
# ATTRIBUTION — which clause actually holds false positives at zero. Measured on the
# pre-WP05 baseline ``96494e5ec`` (1 199 ``*.py`` files under ``src/``, exclusions
# applied), because that is the only tree where this hop still has something to accept.
# Two populations, stated separately because they are not interchangeable and a bare
# "candidates" count is ambiguous between them:
#
#   (a) call sites REACHED BY THIS HOP: 9 candidates (5 helper hops fired)
#       -> 6 rejected at clause 2, 2 rejected at clause 3, 1 ACCEPTED, namely
#          ``ref_advance.py:247 (_meta_change_is_vcs_lock_only)``. 9 == 6+2+1.
#       On branch head the same probe reads 8 -> 6 / 2 / 0: WP05 routed the one.
#   (b) the WHOLE ``json.loads``/``json.load`` population under the direct predicate:
#       150 candidates -> 92 at clause 2, 51 at clause 3, 7 accepted. 150 == 92+51+7.
#
# **Clause 2 is the load-bearing guard under both populations** (6 of 8 rejections in
# (a); 92 of 143 in (b)), and 0 false positives were produced over ``src/``. The
# consequence is the point, not the arithmetic: widening clause 2 further would unlock
# the bulk of these candidates with proportionally little clause-3 protection behind
# it, so it is the clause to leave alone.
#
# TWO EARLIER FIGURES ARE REFUTED, and the second one was carried in this mission's own
# WP06 prompt: "31 candidates, 30 rejected at clause 3" reproduces under no definition,
# and neither does "19 candidates -> 17 at clause 2 -> exactly 1 at clause 3". Under (a)
# clause 3 rejects **2**, not 1; under (b) it rejects **51**. Any restatement of "clause
# 3 rejects exactly one" is wrong. Cite population (a) or (b) explicitly or not at all.
_MAX_PARSE_HELPER_HOPS = 1


def _sole_parameter_name(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Return *fn*'s one parameter name when *fn* is private and single-parameter.

    ``None`` for a public name, for any arity other than exactly one positional
    parameter, and for ``*args``/``**kwargs``/positional-only/keyword-only shapes.
    """
    if not fn.name.startswith("_"):
        return None
    args = fn.args
    if args.vararg is not None or args.kwarg is not None:
        return None
    if args.posonlyargs or args.kwonlyargs or len(args.args) != 1:
        return None
    return args.args[0].arg


def _unbound_helper_parameter(
    arg: ast.expr, fn: ast.FunctionDef | ast.AsyncFunctionDef | None, parents: dict[int, ast.AST]
) -> str | None:
    """Return *fn*'s sole parameter name when *arg* is exactly that, still unbound.

    ``None`` unless every bound holds: *fn* is a module-level ``def`` (not nested, not
    a method), private, single-parameter; *arg* is a bare ``Name`` naming that
    parameter; and the parameter is never rebound in *fn*'s body (a rebinding means
    something other than the caller's argument reaches the parse).
    """
    if fn is None or not isinstance(arg, ast.Name):
        return None
    if not isinstance(parents.get(id(fn)), ast.Module):
        return None
    param = _sole_parameter_name(fn)
    if param is None or arg.id != param:
        return None
    if _assigned_value(fn, param) is not None:
        return None
    return param


def _same_module_call_sites(
    tree: ast.Module, parents: dict[int, ast.AST], helper_name: str
) -> list[tuple[ast.Call, ast.FunctionDef | ast.AsyncFunctionDef | None]]:
    """Return ``(call, enclosing_fn)`` for every same-module call of *helper_name* with args."""
    return [
        (node, _enclosing_function(parents, node))
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and node.args and _callee_name(node) == helper_name
    ]


@dataclass(frozen=True)
class InlineMetaReadSite:
    """One discovered inline ``json.loads``/``json.load`` read of a meta.json path.

    ``lineno`` is a diagnostics locator ONLY — deliberately not part of ``key``.
    """

    rel_path: str
    key: InlineMetaReadKey
    lineno: int


def scan_inline_meta_reads(src_root: Path) -> list[InlineMetaReadSite]:
    """AST-walk ``src/**/*.py`` for inline ``json.loads``/``json.load`` reads of meta.json.

    Excludes :data:`EXCLUDED_REL_PATHS` (the canonical reader's own internals and
    the ``task_utils`` adapter) per the contract.
    """
    sites: list[InlineMetaReadSite] = []
    for path in _iter_source_files(src_root):
        rel = _rel(path)
        if rel in EXCLUDED_REL_PATHS:
            continue
        sites.extend(_scan_file_for_inline_meta_reads(path, rel))
    return sites


def _reads_meta_path(
    arg: ast.expr, fn: ast.FunctionDef | ast.AsyncFunctionDef | None
) -> bool:
    """Clauses 2 and 3 together: *arg* resolves to a read of a meta.json path."""
    base = _read_source_base(arg, fn)
    return base is not None and is_meta_path_expr(base, fn)


def _site_at(
    node: ast.Call, rel: str, parents: dict[int, ast.AST], token_map: dict[int, str]
) -> InlineMetaReadSite:
    return InlineMetaReadSite(
        rel_path=rel,
        key=InlineMetaReadKey(
            rel, _qualname_from_parents(parents, node), token_map.get(node.lineno, "")
        ),
        lineno=node.lineno,
    )


def _iter_json_parse_calls(tree: ast.Module, bindings: _JsonImportBindings) -> list[ast.Call]:
    """Every ``json.loads``/``json.load`` call in *tree* that has at least one argument."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and node.args
        and (_is_json_loads_call(node, bindings) or _is_json_load_call(node, bindings))
    ]


def _scan_file_for_inline_meta_reads(path: Path, rel: str) -> list[InlineMetaReadSite]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    parents = _parent_map(tree)
    bindings = _collect_json_import_bindings(tree)
    token_map = code_tokens_by_line(source)
    found: list[InlineMetaReadSite] = []
    seen: set[tuple[int, int]] = set()
    for node in _iter_json_parse_calls(tree, bindings):
        fn = _enclosing_function(parents, node)
        if _reads_meta_path(node.args[0], fn):
            anchors: list[ast.Call] = [node]
        else:
            # The ONE hop (:data:`_MAX_PARSE_HELPER_HOPS`), and only when the direct
            # resolution above already failed: this pass is strictly ADDITIVE, so the
            # frozen ``(file, qualname, token)`` keys of already-detected sites cannot
            # drift under it.
            param = _unbound_helper_parameter(node.args[0], fn, parents)
            anchors = (
                []
                if param is None or fn is None
                else [
                    call
                    for call, call_fn in _same_module_call_sites(tree, parents, fn.name)
                    if _reads_meta_path(call.args[0], call_fn)
                ]
            )
        for anchor in anchors:
            if (anchor.lineno, anchor.col_offset) in seen:
                continue
            seen.add((anchor.lineno, anchor.col_offset))
            found.append(_site_at(anchor, rel, parents, token_map))
    return found


def check_inline_meta_read_gate(src_root: Path, allowlist: set[InlineMetaReadKey]) -> list[str]:
    """Return violation strings for un-allowlisted inline meta.json reads."""
    violations: list[str] = []
    for site in scan_inline_meta_reads(src_root):
        if site.key in allowlist:
            continue
        violations.append(
            f"{site.rel_path}:{site.lineno} ({site.key.enclosing_qualname}) "
            f"token={site.key.token!r} reads meta.json inline via json.loads/json.load "
            f"instead of mission_metadata.load_meta (or a load_meta_strict/"
            f"load_meta_or_empty adapter) — route it through the canonical reader "
            f"or allow-list it with a rationale + tracked issue"
        )
    return sorted(violations)


def _live_inline_meta_read_keys(src_root: Path) -> set[InlineMetaReadKey]:
    return {site.key for site in scan_inline_meta_reads(src_root)}


# --------------------------------------------------------------------------- #
# Routed-count census (mechanic 3 — anti-mass-allow-list).
# --------------------------------------------------------------------------- #
def scan_routed_load_meta_calls(src_root: Path) -> list[tuple[str, int]]:
    """Return ``[(rel_path, lineno), ...]`` for every call to the routed reader family.

    Deliberately includes ``mission_metadata.py`` — its many internal call sites
    (``load_meta_strict``/``load_meta_or_empty`` delegating to ``load_meta``, and
    its other public helpers reading meta.json through the one canonical
    primitive) ARE genuine routed-usage evidence, distinct from the reader's own
    JSON-parsing implementation (which is what the INLINE scan excludes).
    """
    sites: list[tuple[str, int]] = []
    for path in _iter_source_files(src_root):
        rel = _rel(path)
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) in ROUTED_CALLEES:
                sites.append((rel, node.lineno))
    return sites


# =========================================================================== #
# TESTS
# =========================================================================== #


# --- unit: composite-key machinery -----------------------------------------
def test_inline_meta_read_key_is_hashable_and_value_keyed() -> None:
    """``InlineMetaReadKey`` compares/hashes by the ``(file, qualname, token)`` triple."""
    a = InlineMetaReadKey("f.py", "Migration.apply", "meta = json . loads ( x )")
    b = InlineMetaReadKey("f.py", "Migration.apply", "meta = json . loads ( x )")
    c = InlineMetaReadKey("f.py", "Migration.apply", "meta = json . loads ( y )")
    assert a == b
    assert hash(a) == hash(b)
    assert a != c
    assert {a, b} == {a}


def test_loader_rejects_entry_without_rationale(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "inline_meta_read:\n"
        "  - file: f.py\n    qualname: foo.bar\n    token: x\n"
        "    line: 10\n    issue: 'https://x/1'\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="rationale"):
        load_allowlist(bad)


def test_loader_rejects_entry_without_issue(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "inline_meta_read:\n"
        "  - file: f.py\n    qualname: foo.bar\n    token: x\n"
        "    line: 10\n    rationale: 'deferred'\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="issue"):
        load_allowlist(bad)


def test_loader_rejects_entry_without_token(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "inline_meta_read:\n"
        "  - file: f.py\n    qualname: foo.bar\n    line: 10\n"
        "    rationale: 'deferred'\n    issue: 'https://x/1'\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="token"):
        load_allowlist(bad)


def test_loader_rejects_non_integer_line(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "inline_meta_read:\n"
        "  - file: f.py\n    qualname: foo.bar\n    token: x\n"
        "    line: not-a-number\n    rationale: 'deferred'\n    issue: 'https://x/1'\n",
        encoding="utf-8",
    )
    with pytest.raises(AllowlistEntryError, match="line locator"):
        load_allowlist(bad)


def test_staleness_twin_guard_flags_stale_entry() -> None:
    live = {InlineMetaReadKey("f.py", "a.b", "t1")}
    stale = staleness_twin_guard({InlineMetaReadKey("f.py", "nonexistent", "gone")}, live)
    assert stale == [InlineMetaReadKey("f.py", "nonexistent", "gone")]


def test_staleness_twin_guard_empty_when_all_live() -> None:
    live = {InlineMetaReadKey("f.py", "a.b", "t1"), InlineMetaReadKey("f.py", "c.d", "t2")}
    assert staleness_twin_guard({InlineMetaReadKey("f.py", "a.b", "t1")}, live) == []


# --- unit: scanner helpers ---------------------------------------------------
def test_is_meta_path_expr_matches_pattern_names() -> None:
    for name in ("meta_path", "meta_file", "meta_json", "target_meta_path"):
        expr = ast.parse(name, mode="eval").body
        assert is_meta_path_expr(expr) is True


def test_is_meta_path_expr_matches_inline_join() -> None:
    expr = ast.parse('feature_dir / "meta.json"', mode="eval").body
    assert is_meta_path_expr(expr) is True


def test_is_meta_path_expr_rejects_unrelated_name() -> None:
    expr = ast.parse("status_path", mode="eval").body
    assert is_meta_path_expr(expr) is False


def test_is_meta_path_expr_rejects_other_join_suffix() -> None:
    expr = ast.parse('feature_dir / "status.json"', mode="eval").body
    assert is_meta_path_expr(expr) is False


def _fn_with_call(src: str) -> tuple[ast.Call, ast.FunctionDef | ast.AsyncFunctionDef | None]:
    tree = ast.parse(src)
    parents = _parent_map(tree)
    call = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and (_is_json_loads_call(n) or _is_json_load_call(n))
    )
    return call, _enclosing_function(parents, call)


def test_read_source_base_direct_read_text() -> None:
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    meta_path = feature_dir / 'meta.json'\n"
        "    return json.loads(meta_path.read_text(encoding='utf-8'))\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_source_base_direct_open_call() -> None:
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    meta_path = feature_dir / 'meta.json'\n"
        "    return json.load(open(meta_path, encoding='utf-8'))\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_source_base_traces_named_assignment() -> None:
    """The ``src/charter/_io.py`` shape: a two-hop ``meta_text = meta_path.read_text()``."""
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    meta_path = feature_dir / 'meta.json'\n"
        "    meta_text = meta_path.read_text(encoding='utf-8')\n"
        "    return json.loads(meta_text)\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_source_base_traces_with_statement_binding() -> None:
    """The migration shape: ``with meta_json.open() as f: json.load(f)``."""
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    meta_json = feature_dir / 'meta.json'\n"
        "    with meta_json.open() as fh:\n"
        "        return json.load(fh)\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_source_base_returns_none_for_unrelated_read() -> None:
    call, fn = _fn_with_call("def f(status_path):\n    return json.loads(status_path.read_text())\n")
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is False


def test_module_is_json_accepts_aliased_import() -> None:
    call, _fn = _fn_with_call(
        "def f(meta_path):\n    return _json.loads(meta_path.read_text())\n"
    )
    assert _is_json_loads_call(call) is True


# --- unit: evasion-vector fixes (#3163) --------------------------------------
def test_is_meta_path_expr_resolves_arbitrary_name_via_assignment() -> None:
    """Vector-1 fix: the assignment-hop is structural, not gated on the fixed
    variable-name vocabulary -- an arbitrarily-named local (``mpath``, not one of
    the four canonical names) still resolves to its join expression."""
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    mpath = feature_dir / 'meta.json'\n"
        "    return json.loads(mpath.read_text(encoding='utf-8'))\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base, fn) is True


def test_is_meta_path_expr_without_fn_context_rejects_arbitrary_name() -> None:
    """Without a supplied *fn*, an arbitrarily-named variable cannot be resolved --
    the two-clause standalone test used directly by the unit tests above is
    unchanged; *fn* is what enables the vector-1 structural resolution."""
    expr = ast.parse("mpath", mode="eval").body
    assert is_meta_path_expr(expr) is False


def test_is_meta_path_expr_resolves_two_hop_reassignment_chain() -> None:
    """Vector-3 fix: ``y = x`` reassignment indirection (a second hop past the
    pre-existing one-hop resolution) still resolves to the join expression."""
    call, fn = _fn_with_call(
        "def f(feature_dir):\n"
        "    x = feature_dir / 'meta.json'\n"
        "    y = x\n"
        "    return json.loads(y.read_text(encoding='utf-8'))\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base, fn) is True


def test_follow_assignment_chain_resolves_at_the_hop_limit() -> None:
    """A reassignment chain that costs exactly :data:`_MAX_ASSIGNMENT_HOPS` lookups
    to unwind (one more than the chain's own rename count -- the final lookup
    reads the base variable's own join expression) still resolves."""
    depth = _MAX_ASSIGNMENT_HOPS - 1
    src_lines = ["def f(feature_dir):", "    v0 = feature_dir / 'meta.json'"]
    for i in range(1, depth + 1):
        src_lines.append(f"    v{i} = v{i - 1}")
    src_lines.append(f"    return v{depth}")
    tree = ast.parse("\n".join(src_lines) + "\n")
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    resolved = _follow_assignment_chain(fn, f"v{depth}", _MAX_ASSIGNMENT_HOPS)
    assert resolved is not None
    assert _is_meta_json_join(resolved) is True


def test_follow_assignment_chain_respects_hop_limit() -> None:
    """A reassignment chain one hop past :data:`_MAX_ASSIGNMENT_HOPS` is honestly
    unresolved (``None``), not silently followed forever -- documents the bound
    named in the fix rather than asserting completeness."""
    src_lines = ["def f(feature_dir):", "    v0 = feature_dir / 'meta.json'"]
    for i in range(1, _MAX_ASSIGNMENT_HOPS + 2):
        src_lines.append(f"    v{i} = v{i - 1}")
    src_lines.append(f"    return v{_MAX_ASSIGNMENT_HOPS + 1}")
    tree = ast.parse("\n".join(src_lines) + "\n")
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    resolved = _follow_assignment_chain(
        fn, f"v{_MAX_ASSIGNMENT_HOPS + 1}", _MAX_ASSIGNMENT_HOPS
    )
    assert resolved is None


def test_collect_json_import_bindings_resolves_all_forms() -> None:
    """Vector-2 fix: ``import json``/``import json as X``/``from json import
    loads``/``from json import load as Y`` all resolve to their real local
    binding names -- not a hardcoded ``json``/``_json`` literal match."""
    tree = ast.parse(
        "import json\n"
        "import json as _json\n"
        "from json import loads\n"
        "from json import load as _load\n"
    )
    bindings = _collect_json_import_bindings(tree)
    assert bindings.module_names == {"json", "_json"}
    assert bindings.loads_names == {"loads"}
    assert bindings.load_names == {"_load"}


def test_is_json_loads_call_resolves_from_import_binding() -> None:
    """A bare ``loads(...)`` call resolves as ``json.loads`` when *bindings*
    records ``from json import loads``."""
    tree = ast.parse("from json import loads\ndef f(x):\n    return loads(x)\n")
    bindings = _collect_json_import_bindings(tree)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert _is_json_loads_call(call, bindings) is True
    assert _is_json_loads_call(call) is False  # no bindings supplied -> unresolved


def test_is_json_loads_call_resolves_arbitrary_module_alias() -> None:
    """``import json as <anything>`` (not just ``json``/``_json``) resolves via
    *bindings*, closing the hardcoded-alias gap."""
    tree = ast.parse(
        "import json as totally_arbitrary_alias\n"
        "def f(x):\n    return totally_arbitrary_alias.loads(x)\n"
    )
    bindings = _collect_json_import_bindings(tree)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert _is_json_loads_call(call, bindings) is True
    assert _is_json_loads_call(call) is False  # unresolved without bindings


# --- scanner-level: the same three vectors, exercised end-to-end ------------
def _write_scratch_reader(tmp_path: Path, pkg_name: str, source: str) -> Path:
    pkg = tmp_path / "src" / pkg_name
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "reader.py").write_text(source, encoding="utf-8")
    return tmp_path / "src"


def test_scan_detects_arbitrary_variable_name(tmp_path: Path) -> None:
    """Vector-1 fix, end-to-end: a meta.json path stored under an arbitrarily
    named variable is flagged by the real scanner, not just the helper units."""
    scratch_src = _write_scratch_reader(
        tmp_path,
        "vector1_pkg",
        "class ArbitraryNameReader:\n"
        "    def load(self, feature_dir):\n"
        "        mpath = feature_dir / 'meta.json'\n"
        "        return json.loads(mpath.read_text(encoding='utf-8'))\n",
    )
    sites = scan_inline_meta_reads(scratch_src)
    assert any(s.key.enclosing_qualname == "ArbitraryNameReader.load" for s in sites)


def test_scan_detects_from_json_import_loads(tmp_path: Path) -> None:
    """Vector-2 fix, end-to-end: ``from json import loads`` (a bare ``loads(...)``
    call) is flagged by the real scanner."""
    scratch_src = _write_scratch_reader(
        tmp_path,
        "vector2_pkg",
        "from json import loads\n"
        "class FromImportReader:\n"
        "    def load(self, feature_dir):\n"
        "        meta_path = feature_dir / 'meta.json'\n"
        "        return loads(meta_path.read_text(encoding='utf-8'))\n",
    )
    sites = scan_inline_meta_reads(scratch_src)
    assert any(s.key.enclosing_qualname == "FromImportReader.load" for s in sites)


def test_scan_detects_aliased_json_module_import(tmp_path: Path) -> None:
    """Vector-2 fix, end-to-end: an arbitrarily-aliased ``import json as X`` (not
    just the hardcoded ``json``/``_json`` fallback) is flagged by the real
    scanner."""
    scratch_src = _write_scratch_reader(
        tmp_path,
        "vector2b_pkg",
        "import json as totally_arbitrary_alias\n"
        "class AliasedImportReader:\n"
        "    def load(self, feature_dir):\n"
        "        meta_path = feature_dir / 'meta.json'\n"
        "        return totally_arbitrary_alias.loads(meta_path.read_text(encoding='utf-8'))\n",
    )
    sites = scan_inline_meta_reads(scratch_src)
    assert any(s.key.enclosing_qualname == "AliasedImportReader.load" for s in sites)


def test_scan_detects_two_hop_reassignment(tmp_path: Path) -> None:
    """Vector-3 fix, end-to-end: a two-hop ``y = x`` reassignment chain is flagged
    by the real scanner."""
    scratch_src = _write_scratch_reader(
        tmp_path,
        "vector3_pkg",
        "class TwoHopReader:\n"
        "    def load(self, feature_dir):\n"
        "        x = feature_dir / 'meta.json'\n"
        "        y = x\n"
        "        return json.loads(y.read_text(encoding='utf-8'))\n",
    )
    sites = scan_inline_meta_reads(scratch_src)
    assert any(s.key.enclosing_qualname == "TwoHopReader.load" for s in sites)


# --- T045: scanner integration on the real tree -----------------------------
def test_scan_excludes_mission_metadata_and_task_utils() -> None:
    """The scan never reports a site inside the two excluded files."""
    sites = scan_inline_meta_reads(SRC_ROOT)
    assert all(site.rel_path not in EXCLUDED_REL_PATHS for site in sites)


def test_scan_routed_load_meta_calls_counts_call_sites(tmp_path: Path) -> None:
    """Unit check: the routed scanner counts call sites, not definitions or imports."""
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "caller.py").write_text(
        "from specify_cli.mission_metadata import load_meta\n"
        "def load_meta():\n"  # a same-named def is NOT a call
        "    pass\n"
        "def user(feature_dir):\n"
        "    a = load_meta(feature_dir)\n"
        "    b = load_meta_strict(feature_dir)\n"
        "    return a, b\n",
        encoding="utf-8",
    )
    routed = scan_routed_load_meta_calls(tmp_path / "src")
    assert len(routed) == 2  # only the two Call nodes, not the def or the import


# --- T046: gate mechanic 1+2 — concrete floor + margin ----------------------
def test_inline_meta_read_floor() -> None:
    """Concrete CEILING: the live inline-read census stays <= INLINE_META_READ_FLOOR.

    ``INLINE_META_READ_FLOOR`` is a shrink-only ceiling (fewer inline reads is
    progress) — the opposite direction from the canonicalizer's growth-oriented
    floor. A broken scanner returning zero rows trivially satisfies ``<=``, which
    is why mechanic 2 (margin) exists: it independently pins the floor close to
    the live count so it cannot be set to an arbitrarily high, masking value.
    """
    count = len(scan_inline_meta_reads(SRC_ROOT))
    assert count <= INLINE_META_READ_FLOOR, (
        f"inline meta-read census grew to {count}; expected <= {INLINE_META_READ_FLOOR}. "
        "A new inline json.loads/json.load read of meta.json regressed the drain — "
        "route it through mission_metadata.load_meta or allow-list it with a rationale."
    )
    assert INLINE_META_READ_FLOOR - count <= FLOOR_MARGIN, (
        f"INLINE_META_READ_FLOOR ({INLINE_META_READ_FLOOR}) sits more than "
        f"FLOOR_MARGIN ({FLOOR_MARGIN}) above the live count ({count}); tighten the "
        "floor to the honest live census so it cannot mask a future regrowth."
    )


# --- T046: gate mechanic 3 — routed-count floor (anti-mass-allow-list) ------
def test_routed_load_meta_floor() -> None:
    """Concrete floor: routed load_meta*() call sites stay >= ROUTED_LOAD_META_FLOOR.

    Mirrors ``test_routed_count_floor`` in ``test_resolution_authority_gates.py``:
    both bounds are enforced (``live - MARGIN <= floor < live``) so the floor is a
    concrete census integer, never a tautological ``>= len(routed)``.
    """
    routed = scan_routed_load_meta_calls(SRC_ROOT)
    assert len(routed) >= ROUTED_LOAD_META_FLOOR, (
        f"routed load_meta*() census dropped to {len(routed)}; expected "
        f">= {ROUTED_LOAD_META_FLOOR}. A drop means call sites stopped routing "
        "through the canonical reader family."
    )
    assert len(routed) > ROUTED_LOAD_META_FLOOR, (
        "ROUTED_LOAD_META_FLOOR must be a concrete census integer strictly below "
        "the live routed count, not '>= len(routed)' (anti-vacuous)."
    )
    assert len(routed) - ROUTED_LOAD_META_FLOOR <= ROUTED_LOAD_META_FLOOR_MARGIN, (
        f"ROUTED_LOAD_META_FLOOR ({ROUTED_LOAD_META_FLOOR}) is more than "
        f"ROUTED_LOAD_META_FLOOR_MARGIN ({ROUTED_LOAD_META_FLOOR_MARGIN}) below the "
        f"live routed count ({len(routed)}); tighten the floor."
    )


# --- T046: gate mechanic 4 — real-tree allow-list + staleness --------------
def test_inline_meta_read_gate_green_against_seeded_allowlist() -> None:
    """With the seeded allow-list, the gate reports zero violations."""
    allowlist = set(load_allowlist(ALLOWLIST_PATH))
    violations = check_inline_meta_read_gate(SRC_ROOT, allowlist)
    assert violations == [], "\n".join(violations)


def test_allowlist_matches_floor() -> None:
    """The seeded allow-list has exactly ``INLINE_META_READ_FLOOR`` entries.

    Every currently-live inline read is deferred with a rationale — the gate is
    fully accounted for, not merely under the ceiling.
    """
    assert len(load_allowlist(ALLOWLIST_PATH)) == INLINE_META_READ_FLOOR


def test_allowlist_shrink_only() -> None:
    """NFR-003: the seeded allow-list never inflates beyond the pre-sweep baseline."""
    keys = load_allowlist(ALLOWLIST_PATH)
    baseline = load_baseline(ALLOWLIST_PATH)
    assert len(keys) <= baseline, (
        f"inline_meta_read allow-list ({len(keys)}) exceeds baseline ({baseline}) "
        "— entries may only be removed (routed away), never added"
    )


# --- T047 self-test 1/3: a new inline meta read is flagged (plant -> RED) --
def test_new_inline_meta_read_is_flagged(tmp_path: Path) -> None:
    """Gate FAILS on an injected inline read, PASSES once sanctioned (INV-C2)."""
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "planted.py").write_text(
        "class PlantedReader:\n"
        "    def load(self, feature_dir):\n"
        "        meta_path = feature_dir / 'meta.json'\n"
        "        return json.loads(meta_path.read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    scratch_src = tmp_path / "src"

    # Planted, un-sanctioned -> RED.
    violations = check_inline_meta_read_gate(scratch_src, set())
    assert violations, "self-test: a newly-planted inline meta read must be flagged"
    assert any("PlantedReader.load" in v for v in violations)

    # Sanctioned (tool-derived key, never hand-typed) -> GREEN.
    site_key = next(
        s.key
        for s in scan_inline_meta_reads(scratch_src)
        if s.key.enclosing_qualname == "PlantedReader.load"
    )
    assert check_inline_meta_read_gate(scratch_src, {site_key}) == []


# --- T047 self-test 2/3: stale-entry twin-guard on the real allow-list -----
def test_allowlist_entries_are_still_live() -> None:
    """NFR-003 twin-guard: every seeded allow-list entry matches a live site.

    Ships as a self-test per the contract's T047 list: a routed-away entry left
    in the allow-list (masking a drain that already happened) must fail here.
    """
    allowlist = set(load_allowlist(ALLOWLIST_PATH))
    live = _live_inline_meta_read_keys(SRC_ROOT)
    stale = staleness_twin_guard(allowlist, live)
    assert stale == [], f"stale inline_meta_read allow-list entries: {stale}"


# --- T047 self-test 3/3: mass-allow-list attempt is structurally caught ----
def test_routed_count_floor_blocks_mass_allowlist(tmp_path: Path) -> None:
    """Allow-listing every site (instead of routing) manufactures zero routed evidence.

    Simulates the "drain the ceiling by mass-allow-listing" attack: sanction
    every discovered inline-read site in a scratch tree with NO corresponding
    ``load_meta*`` calls. The INLINE gate goes green (every site is
    allow-listed), but the routed-count census computed from the SAME tree
    stays at zero — proving the two mechanics are independent, so a floor tying
    the routed census to the drained count (as ``ROUTED_LOAD_META_FLOOR`` does on
    the real tree) trips RED on this shape of regression.
    """
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "reader.py").write_text(
        "class ScratchReader:\n"
        "    def load(self, feature_dir):\n"
        "        meta_path = feature_dir / 'meta.json'\n"
        "        return json.loads(meta_path.read_text(encoding='utf-8'))\n"
        "    def load_other(self, feature_dir):\n"
        "        meta_file = feature_dir / 'meta.json'\n"
        "        return json.loads(meta_file.read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    scratch_src = tmp_path / "src"

    sites = scan_inline_meta_reads(scratch_src)
    assert len(sites) == 2, "fixture must contain two genuine inline meta reads"

    # "Mass allow-list" the drain: sanction every discovered site instead of
    # routing the code onto load_meta*.
    mass_allowlist = {site.key for site in sites}
    assert check_inline_meta_read_gate(scratch_src, mass_allowlist) == [], (
        "sanity: the mass allow-list must make the INLINE gate green"
    )

    # The routed-count census is INDEPENDENT of the allow-list: mass-allow-listing
    # manufactures zero routing evidence in this fixture.
    routed = scan_routed_load_meta_calls(scratch_src)
    required_routed_floor = len(sites)  # one routed call should replace each drained read
    assert len(routed) < required_routed_floor, (
        "self-test invariant broken: a mass allow-list in this fixture must NOT be "
        "accompanied by genuine routed calls"
    )
    # This is exactly the failure shape ROUTED_LOAD_META_FLOOR catches on the real
    # tree: a floor requiring routed growth reds when routing didn't happen.


# --- WP06 / FR-006: ``read_bytes`` joins the recognised read calls -----------
def test_read_source_base_direct_read_bytes() -> None:
    """FR-006: ``read_bytes`` is a read call, exactly like ``read_text``/``open``.

    Unit-level pin on the resolver itself, beside
    :func:`test_read_source_base_direct_read_text` and
    :func:`test_read_source_base_direct_open_call`. Before this WP,
    ``_extract_read_base`` matched only ``read_text``/``open`` and returned ``None``
    here, so the call was rejected at clause 2. Observed RED before the widening
    (``assert None is not None``).
    """
    call, fn = _fn_with_call(
        "def f(mission_dir):\n"
        "    meta_path = mission_dir / 'meta.json'\n"
        "    return json.loads(meta_path.read_bytes())\n"
    )
    base = _read_source_base(call.args[0], fn)
    assert base is not None
    assert is_meta_path_expr(base) is True


def test_read_bytes_scan_level_pin_moves_one_to_two(tmp_path: Path) -> None:
    """Scan-level synthetic pin for the ``read_bytes`` widening: measured **1 -> 2**.

    **No red possible on the live tree — synthetic pin required** (charter ``C-011``
    ATDD-first discipline, paired with this spec's ``C-008``). Adding ``read_bytes``
    to :func:`_extract_read_base` yields **0** new sites over ``src/`` on this tree,
    so no live census moves and no floor can go red. Manufacturing a live red would
    mean committing a new unrouted inline read under ``src/``, which reds
    :func:`test_inline_meta_read_floor` against its shrink-only ceiling — a ``C-008``
    violation dressed up as compliance. The falsifiable control is therefore this
    runtime-generated pair: one module whose read is ``read_text``-fed (counted before
    and after) and one whose read is ``read_bytes``-fed (counted only after the
    widening). Both counts are printed, not merely asserted. Observed RED before the
    widening at ``1 -> 1``.

    Generated at runtime under ``tmp_path`` on purpose: no third fixture file is
    committed under ``_fixtures/`` for this.
    """
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    scratch_src = tmp_path / "src"

    (pkg / "text_fed.py").write_text(
        "import json\n"
        "def read(mission_dir):\n"
        "    meta_path = mission_dir / 'meta.json'\n"
        "    return json.loads(meta_path.read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    before = len(scan_inline_meta_reads(scratch_src))
    print(f"read_bytes pin: read_text-fed module only -> sites: {before}")

    (pkg / "bytes_fed.py").write_text(
        "import json\n"
        "def read(mission_dir):\n"
        "    meta_path = mission_dir / 'meta.json'\n"
        "    return json.loads(meta_path.read_bytes())\n",
        encoding="utf-8",
    )
    after = len(scan_inline_meta_reads(scratch_src))
    print(f"read_bytes pin: + read_bytes-fed module -> sites: {after}")

    assert (before, after) == (1, 2), (
        f"read_bytes widening pin: expected the measured 1 -> 2, got {before} -> {after}"
    )


# --- WP06 / FR-006: the one-hop private same-module parse-helper anchor ------
def _scratch_src_with(tmp_path: Path, name: str, source: str) -> Path:
    """Write ``<tmp_path>/src/scratch_pkg/<name>`` and return the scratch ``src`` root."""
    pkg = tmp_path / "src" / "scratch_pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / name).write_text(source, encoding="utf-8")
    return tmp_path / "src"


_DELEGATED_READ_MODULE = (
    "import json\n"
    "def _parse_meta_object(text):\n"
    "    return json.loads(text)\n"
    "def caller(worktree, path):\n"
    "    meta_path = worktree / path\n"
    "    return _parse_meta_object(meta_path.read_text(encoding='utf-8'))\n"
)


def test_anchor_hop_flags_private_same_module_parse_helper_call_site(tmp_path: Path) -> None:
    """FR-006 widening: the ``C2b`` shape is reached, and reported at the CALL SITE.

    Research control ``C2b`` (``research/3162-census.md:295``) measured **0** sites for
    this exact shape: splitting the parse into a helper hid the read, because
    ``json.loads``' argument is the helper's own unbound parameter and
    ``_follow_assignment_chain`` is intra-function. The widening takes **one hop** from
    that unbound parameter to the helper's call sites in the **same module** and applies
    clause 2 there. The reported site must be the caller's line — allow-list keys are
    ``(file, qualname, token)``, so anchoring on the helper's ``json.loads`` line would
    make every such entry point at the wrong function.

    This is the widening's red-first evidence: observed RED before the change,
    reporting ``[]`` where 1 site is required.
    """
    scratch_src = _scratch_src_with(tmp_path, "delegated.py", _DELEGATED_READ_MODULE)
    sites = scan_inline_meta_reads(scratch_src)
    print(f"anchor-hop pin: private single-param helper shape -> sites: {len(sites)}")
    # A content comparison, deliberately NOT ``len(sites) == 1``: the qualname list
    # pins BOTH that exactly one site is reported AND that it is reported at the CALL
    # SITE rather than at the helper's ``json.loads`` line, which is the property that
    # actually matters here. It also carries no line number, so benign edits to the
    # scratch module above cannot move it (cf. test_ratchet_positional_anchor_ban.py).
    assert [s.key.enclosing_qualname for s in sites] == ["caller"], (
        f"expected the C2b shape to be reached at the CALL SITE exactly once, got {sites}"
    )
    assert "_parse_meta_object" in sites[0].key.token


@pytest.mark.parametrize(
    ("label", "source"),
    [
        (
            "public helper (no leading underscore)",
            _DELEGATED_READ_MODULE.replace("_parse_meta_object", "parse_meta_object"),
        ),
        (
            "helper takes more than one parameter",
            "import json\n"
            "def _parse_meta_object(text, strict):\n"
            "    return json.loads(text)\n"
            "def caller(worktree, path):\n"
            "    meta_path = worktree / path\n"
            "    return _parse_meta_object(meta_path.read_text(encoding='utf-8'), True)\n",
        ),
        (
            "call site passes something that is not a read",
            "import json\n"
            "def _parse_meta_object(text):\n"
            "    return json.loads(text)\n"
            "def caller(result):\n"
            "    meta_path = result.cwd / 'meta.json'\n"
            "    return _parse_meta_object(result.stdout)\n",
        ),
        (
            "call site's read is not of a meta.json path (clause 3)",
            "import json\n"
            "def _parse_meta_object(text):\n"
            "    return json.loads(text)\n"
            "def caller(worktree):\n"
            "    status_path = worktree / 'status.json'\n"
            "    return _parse_meta_object(status_path.read_text(encoding='utf-8'))\n",
        ),
        (
            "helper is a class-level staticmethod, not a module-level def",
            "import json\n"
            "class Reader:\n"
            "    @staticmethod\n"
            "    def _parse_meta_object(text):\n"
            "        return json.loads(text)\n"
            "    def caller(self, worktree, path):\n"
            "        meta_path = worktree / path\n"
            "        return Reader._parse_meta_object(meta_path.read_text(encoding='utf-8'))\n",
        ),
        (
            "helper is a nested def, not a module-level def",
            "import json\n"
            "def outer():\n"
            "    def _parse_meta_object(text):\n"
            "        return json.loads(text)\n"
            "    def caller(worktree, path):\n"
            "        meta_path = worktree / path\n"
            "        return _parse_meta_object(meta_path.read_text(encoding='utf-8'))\n"
            "    return caller\n",
        ),
        (
            "the helper's parameter is rebound before the parse",
            "import json\n"
            "def _parse_meta_object(text):\n"
            "    text = text.strip()\n"
            "    return json.loads(text)\n"
            "def caller(worktree, path):\n"
            "    meta_path = worktree / path\n"
            "    return _parse_meta_object(meta_path.read_text(encoding='utf-8'))\n",
        ),
    ],
)
def test_anchor_hop_is_bounded(tmp_path: Path, label: str, source: str) -> None:
    """The hop is one, private, same-module, single-parameter — and nothing else.

    Each row is a shape the widening must NOT reach. These rows are green before the
    widening too (an unwidened scanner reports 0 for every shape in this family), so
    they are stated as **bounds on the new capability**, not as red-first evidence;
    the red-first evidence for the widening is
    :func:`test_anchor_hop_flags_private_same_module_parse_helper_call_site`.
    """
    scratch_src = _scratch_src_with(tmp_path, "bounded.py", source)
    sites = scan_inline_meta_reads(scratch_src)
    assert sites == [], f"anchor hop must not reach: {label} (got {sites})"


def test_anchor_hop_does_not_cross_module_boundary(tmp_path: Path) -> None:
    """A helper imported from another module is out of the hop's reach (bound: same-module)."""
    scratch_src = _scratch_src_with(
        tmp_path,
        "helper.py",
        "import json\ndef _parse_meta_object(text):\n    return json.loads(text)\n",
    )
    (scratch_src / "scratch_pkg" / "importer.py").write_text(
        "from .helper import _parse_meta_object\n"
        "def caller(worktree, path):\n"
        "    meta_path = worktree / path\n"
        "    return _parse_meta_object(meta_path.read_text(encoding='utf-8'))\n",
        encoding="utf-8",
    )
    sites = scan_inline_meta_reads(scratch_src)
    assert sites == [], f"the hop is intra-module by construction; got {sites}"


# --- WP06 / SC-005 / NFR-004: the control and its positive twin --------------
def _fixture_site_count(rel_path: str) -> int:
    """Sites reported for ONE committed fixture file.

    Scanned by **explicit argument** over :data:`FIXTURES_DIR` and then filtered to the
    fixture's own ``rel_path``: a bare ``len(scan_inline_meta_reads(FIXTURES_DIR))``
    would fold in the pre-existing ``_fixtures/bad_adapter.py`` and
    ``_fixtures/org_packs/**``, making both numbers meaningless.
    """
    return len([s for s in scan_inline_meta_reads(FIXTURES_DIR) if s.rel_path == rel_path])


def test_unreachability_control_is_zero_and_its_twin_is_one() -> None:
    """SC-005 / NFR-004: the negative control is falsifiable, in ONE run.

    A bare ``sites: 0`` is a vacuous negative — a broken scanner prints ``0`` too,
    which is what ``architectural-gate-non-vacuity`` forbids. Both numbers are
    measured and printed here together: the ``git show``-fed control stays
    unreachable at **0** (post-widening: the anchor hop reaches its delegated call
    site and rejects it at clause 2), while its twin, differing only in that the read
    comes from ``meta_path.read_text``, is reported at **1**.

    ``NFR-004``'s denominator, as integers: **1 reached and routed / 4 deferred with a
    control / 0 allowlisted**.
    """
    control = _fixture_site_count(UNREACHABILITY_CONTROL_REL)
    twin = _fixture_site_count(UNREACHABILITY_TWIN_REL)
    print(f"{UNREACHABILITY_CONTROL_REL} -> sites: {control}")
    print(f"{UNREACHABILITY_TWIN_REL} -> sites: {twin}")
    assert (control, twin) == (0, 1), (
        f"expected control 0 / twin 1, got {control} / {twin}; a control without a live "
        "twin is a vacuous negative"
    )


def test_control_fixtures_are_not_under_src() -> None:
    """Risk 5: a fully-inlined read under ``src/`` would red the floor it proves."""
    for rel in (UNREACHABILITY_CONTROL_REL, UNREACHABILITY_TWIN_REL):
        assert (_REPO_ROOT / rel).is_file(), f"missing control fixture {rel}"
        assert not rel.startswith("src/"), f"{rel} must never live under src/"
    live = {site.rel_path for site in scan_inline_meta_reads(SRC_ROOT)}
    assert not any("unreachability_control" in rel for rel in live)


# --- timing (fast-tier budget) ----------------------------------------------
def test_gate_runs_under_fast_tier_budget() -> None:
    """Both scans complete well under the 30 s fast-tier ceiling."""
    start = time.monotonic()
    scan_inline_meta_reads(SRC_ROOT)
    scan_routed_load_meta_calls(SRC_ROOT)
    elapsed = time.monotonic() - start
    assert elapsed < 30.0, f"inline meta-read scans took {elapsed:.2f}s (>30s budget)"
