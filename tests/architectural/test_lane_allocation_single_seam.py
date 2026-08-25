"""Structural anti-bypass guard for the M8 lane-allocation + read-degrade seams (FR-007).

Recurrence guard for the #3571 class: a new allocation route that computes a lane
parent ref inline, or a new coord-surface read-degrade ``try/except`` that does not
route through the shared seam, must fail here (naming ``file:line``) rather than
silently re-introducing the bypass.

Three positive, structural checks (never substring / literal-spelling greps):

1. **Allocation single-seam (FR-001/002).** In
   ``src/specify_cli/lanes/worktree_allocator.py`` every value flowing into the
   lane-parent argument of a creation/branch-ensure call
   (``_create_lane_worktree`` arg ``base_branch``; ``_ensure_mission_branch`` arg
   ``mission_branch``) is asserted -- by AST **def-use** -- to originate in a
   :func:`resolve_lane_base_or_refuse` return (``decision.parent_ref`` or an inline
   ``resolve_lane_base_or_refuse(...).parent_ref``). Anchored on the seam SYMBOL and
   the creation-call symbols, NOT on the ``coordination_branch if ... else
   mission_branch`` spelling (which misses a bypass composed from other names).
   ``_ensure_branch_exists`` is deliberately excluded: its ``branch`` argument is the
   topology parent being *ensured to exist* (from ``_read_coordination_branch``), not
   the ref the lane branches from -- the lane still branches from
   ``decision.parent_ref`` via ``_create_lane_worktree`` on that same route, which the
   def-use check pins.

2. **Route coverage (FR-001).** Each of the four ``LaneAllocationRoute`` branches
   reaches the seam (FRESH_COORD / FRESH_LEGACY / REUSE / CRASH_RECOVERY), asserted
   via AST ``route=`` keyword collection against the live enum members -- not a bare
   call count.

3. **Read/degrade family, TREE-WIDE (FR-006/007).** Every coord-surface read-degrade
   ``try/except`` (one catching a coord read-resolution error type) found by walking
   EVERY ``.py`` under ``src/specify_cli/`` and ``src/mission_runtime/`` must be
   dispositioned as exactly one of: **(a)** it routes through
   :func:`resolve_read_dir_or_degrade` (the shared read seam); **(b)** it is a
   family-bespoke entry in ``_READ_DEGRADE_ALLOWLIST`` whose rationale names WHICH
   ``ReadDegradeStrategy`` it fails and WHY (anti-rubber-stamp); or **(c)** it is an
   entry in ``_NOT_READ_DIR_DEGRADE_ALLOWLIST`` -- a coord-catch that is NOT a
   resolve-then-degrade-to-a-directory-via-the-placement-seam shape (it re-raises,
   translates to a typed error, falls back to a non-directory value, or resolves
   through a different door), with a concrete one-line rationale. A coord-catch site
   in NEITHER (a)/(b)/(c) fails here naming ``file:line``. **Tree-wide, not
   registry-scoped:** the check discovers every coord-catch site structurally across
   the two source roots, so a NEW coord-catch introduced ANYWHERE fails until someone
   dispositions it -- this folds the #3462 read-degrade follow-up the earlier
   registry-scoped guard only tracked. Across the tree there are currently ~27
   coord-error catch sites: the five #3462 read-DIR-degrade family members plus the
   two ``agent/status.py`` FAIL_CLOSED pass-throughs live in (b); every other site
   re-raises / translates / degrades to a non-dir value / uses a non-seam resolver
   and lives in (c).

**Deterministic non-vacuity.** Each checker is exercised against synthetic in-test
AST fixtures (a bypassing function is flagged with the right ``file:line`` + rule; a
seam-routed function is clean) before it is run over the live modules and asserted
clean -- so the guard is proven to detect bypasses without depending on a
hand-introduced temp edit.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
_ALLOCATOR = _SRC / "specify_cli" / "lanes" / "worktree_allocator.py"

# --- Allocation seam anchors (symbols, never line numbers or spellings) ---
_SEAM = "resolve_lane_base_or_refuse"
_PARENT_REF_ATTR = "parent_ref"
_ROUTE_ENUM = "LaneAllocationRoute"
_EXPECTED_ROUTES = frozenset({"FRESH_COORD", "FRESH_LEGACY", "REUSE", "CRASH_RECOVERY"})
# creation/branch-ensure call symbol -> (positional index, keyword name) of its
# lane-parent argument (the ref a freshly-created lane actually branches from).
_CREATION_PARENT_ARG: dict[str, tuple[int, str]] = {
    "_create_lane_worktree": (3, "base_branch"),
    "_ensure_mission_branch": (1, "mission_branch"),
}
_RULE_INLINE = "inline parent-ref computation outside resolve_lane_base_or_refuse"

# --- Read-degrade seam anchors ---
_READ_SEAM = "resolve_read_dir_or_degrade"
_COORD_READ_ERRORS = frozenset(
    {"CoordinationBranchDeleted", "CoordAuthorityUnavailable", "StatusReadPathNotFound"}
)
# ReadDegradeStrategy member tokens an allowlist rationale must name to be non-vacuous.
_STRATEGY_TOKENS = ("DEGRADE_TO", "ZERO_EVIDENCE", "FAIL_CLOSED")
_RULE_UNREG = "unregistered read-degrade site"

# The two genuine resolve-then-degrade sites migrated onto the shared read seam.
_MIGRATED_READ_SITES = (
    "specify_cli/retrospective/generator.py",
    "specify_cli/core/worktree_topology.py",
)
# The FR-006 read-DIR-degrade family (documentation of the (b) surface): migrated
# sites + bespoke/pass-through sites. This tuple is NO LONGER the live scan scope —
# the read-degrade check is now TREE-WIDE (it walks every ``.py`` under the two source
# roots; see ``test_tree_wide_read_degrade_sites_are_dispositioned``). It is retained
# as a consistency anchor: every file that owns a family-bespoke ``_READ_DEGRADE_ALLOWLIST``
# entry must appear here (``test_family_allowlist_files_are_registered``), documenting
# which modules are the curated #3462 read-DIR-degrade family versus the many other
# coord-catch sites (re-raise / translate / non-dir / non-seam-resolver) that live in
# ``_NOT_READ_DIR_DEGRADE_ALLOWLIST``.
_READ_DEGRADE_REGISTRY = _MIGRATED_READ_SITES + (
    "specify_cli/status/aggregate.py",
    "specify_cli/cli/commands/agent/status.py",
    "specify_cli/cli/commands/_review_cycle_reconcile_doctor.py",
    "specify_cli/merge/executor.py",
    "specify_cli/review/cycle.py",
)
# Bespoke / pass-through allowlist. Keyed (relpath, enclosing function). Each rationale
# MUST name the failed ReadDegradeStrategy + the concrete reason (anti-rubber-stamp,
# read-dir-degrade.md acceptance criterion). An entry naming no strategy fails the test.
_READ_DEGRADE_ALLOWLIST: dict[tuple[str, str], str] = {
    ("specify_cli/status/aggregate.py", "_resolve_read_dir"): (
        "#1848 bespoke: fails DEGRADE_TO_* and ZERO_EVIDENCE (no single degrade dir "
        "to return) and fails FAIL_CLOSED (must re-wrap StatusReadPathNotFound -> "
        "CoordAuthorityUnavailable while re-raising the CoordinationBranchDeleted "
        "subclass VERBATIM ahead of it -- the ordering the single-strategy helper "
        "cannot express)."
    ),
    ("specify_cli/status/aggregate.py", "_find_meta_path"): (
        "#1848 bespoke: fails DEGRADE_TO_* / ZERO_EVIDENCE -- the except returns a "
        "(meta_path, primary_dir) tuple deferral, not a single read_dir, so the "
        "downstream _resolve_read_dir surfaces the converged fail-closed type "
        "(CoordinationBranchDeleted verbatim, else CoordAuthorityUnavailable) instead "
        "of leaking the raw StatusReadPathNotFound."
    ),
    ("specify_cli/cli/commands/agent/status.py", "_resolve_status_surface"): (
        "FAIL_CLOSED pass-through: the caller owns the typer.Exit(1); routing through "
        "resolve_read_dir_or_degrade's FAIL_CLOSED re-raise removes no try/except and "
        "still needs this handler to convert the typed error into the CLI exit."
    ),
    ("specify_cli/cli/commands/agent/status.py", "_resolve_mission_status_for_repo"): (
        "FAIL_CLOSED pass-through: same as _resolve_status_surface -- the CLI owns the "
        "typer.Exit(1); the seam's FAIL_CLOSED re-raise would remove no try/except."
    ),
    (
        "specify_cli/cli/commands/_review_cycle_reconcile_doctor.py",
        "_resolve_canonical_review_cycle_dir",
    ): (
        "fails DEGRADE_TO_*: the except returns a (dir, coord-branch-class) tuple "
        "carrying a second discriminator (deleted-coord vs live-coord-pre-ADR) that "
        "ReadDirDecision cannot represent, so it is not a resolve-then-degrade-to-one-"
        "dir shape."
    ),
    ("specify_cli/merge/executor.py", "_run_lane_based_merge"): (
        "FAIL_CLOSED pass-through: the caller owns the typer.Exit(1) (renders the "
        "CoordinationBranchDeleted remediation and aborts before any state change). "
        "Routing through resolve_read_dir_or_degrade's FAIL_CLOSED re-raise removes no "
        "try/except — the handler is still needed to convert the typed error into the "
        "CLI exit, identical to the agent/status.py pass-through sites."
    ),
    ("specify_cli/review/cycle.py", "_review_cycle_wp_dir"): (
        "kind-fallback: fails DEGRADE_TO_* and ZERO_EVIDENCE — the except degrades to a "
        "DIFFERENT artifact KIND (REVIEW_CYCLE -> WORK_PACKAGE_TASK, the ADR exception-"
        "absorption rule), not to a caller-supplied degrade_target dir. ReadDirDecision "
        "carries a single resolved read_dir and cannot represent a (dir, kind) "
        "discriminator, so the single-target seam cannot express this fallback."
    ),
}

# --------------------------------------------------------------------------- #
# NOT-a-read-DIR-degrade allowlist (the tree-wide (c) disposition).
# --------------------------------------------------------------------------- #
# Keyed (relpath, enclosing function). These are coord-catch sites the tree-wide walk
# discovers that are NOT resolve-then-degrade-to-a-directory-via-the-placement-seam
# shapes, so routing them through :func:`resolve_read_dir_or_degrade` would be wrong
# (it would remove no try/except, or would change behaviour). Each rationale states
# concretely WHY the site is not a seam candidate: it re-raises the typed error, it
# TRANSLATES to a typed boundary error, it degrades to a NON-directory value (a bool /
# None sentinel / a raw slug string / a write CommitTarget), or it resolves through a
# DIFFERENT door than ``placement_seam.read_dir(kind)``. A site here must NOT also be a
# family-bespoke (b) entry nor a seam-routed (a) function — enforced below.
_NOT_READ_DIR_DEGRADE_ALLOWLIST: dict[tuple[str, str], str] = {
    ("specify_cli/cli/commands/agent/context.py", "_find_feature_directory"): (
        "translate: the read goes through the resolve_handle_to_read_path seam; the "
        "except TRANSLATES StatusReadPathNotFound into a typed ActionContextError "
        "(FEATURE_CONTEXT_UNRESOLVED) and re-raises — no directory fallback."
    ),
    (
        "specify_cli/cli/commands/agent/mission_feature_resolution.py",
        "_find_feature_directory",
    ): (
        "translate: same shape as agent/context.py — resolve_handle_to_read_path "
        "resolves, the except re-raises StatusReadPathNotFound as ActionContextError; "
        "no dir is returned from the handler."
    ),
    ("specify_cli/cli/commands/agent/mission_finalize.py", "_execution_has_begun"): (
        "non-dir fallback: on an unresolvable status surface the gate-signal helper "
        "returns the bool False ('execution not begun'), never a substitute read_dir — "
        "so there is no directory to route through the seam."
    ),
    (
        "specify_cli/cli/commands/agent/mission_finalize.py",
        "_resolve_acceptance_matrix_home",
    ): (
        "non-seam resolver: resolution is via _acceptance_gate_context(...).surface (a "
        "gate-context door that applies topology + MATERIALIZED gating and AH-2 "
        "affirmative-primary), NOT placement_seam.read_dir(kind); routing through the "
        "seam would drop that gating and change behaviour."
    ),
    ("specify_cli/cli/commands/decision.py", "cmd_verify"): (
        "translate: resolve_handle_to_read_path resolves; the except hands the typed "
        "StatusReadPathNotFound/MissionSelectorAmbiguous to _handle_action_context_error "
        "(which raises) — a fail-closed translate, not a directory degrade."
    ),
    (
        "specify_cli/cli/commands/migrate/backfill_provenance.py",
        "_collect_matrix_paths",
    ): (
        "silent whole-corpus skip: this iterates the ENTIRE mission corpus and on an "
        "unroutable mission skips it silently (AM-4 'skip, never archive'), falling back "
        "to the pre-fix primary mission_dir. The seam mandates a per-degrade #1848 "
        "WARNING ('may hide real content') and has no silent-degrade strategy, so routing "
        "would emit a false data-loss warning for every unroutable mission in the corpus. "
        "(Borderline: it does resolve via placement_seam.read_dir(ACCEPTANCE_MATRIX) and "
        "degrade to a dir — flagged for a reviewer migration decision.)"
    ),
    ("specify_cli/cli/commands/mission_type.py", "_resolve_mission_slug"): (
        "non-dir fallback: on the fail-closed coord window the handle canonicalizer "
        "returns the raw slug STRING (not a read_dir), keeping slug resolution "
        "non-raising at this boundary."
    ),
    ("specify_cli/cli/commands/next_cmd.py", "_resolve_mission_slug"): (
        "re-raise: the except re-raises the typed StatusReadPathNotFound verbatim so the "
        "command layer surfaces error_code + candidate paths — deliberately NOT collapsed "
        "into a directory fallback."
    ),
    (
        "specify_cli/coordination/status_transition.py",
        "_canonical_primary_feature_dir",
    ): (
        "non-seam resolver + carried anchor: resolution is via "
        "resolve_status_surface_with_anchor (the surface door, not placement_seam.read_dir), "
        "and the degrade extracts exc.primary_candidate carried BY the typed error rather "
        "than a caller-supplied degrade_target."
    ),
    (
        "specify_cli/coordination/surface_resolver.py",
        "resolve_status_surface_with_anchor",
    ): (
        "this IS the coord surface-resolver door the read seam sits atop; it re-anchors on "
        "exc.primary_candidate from the typed error (not a degrade_target). Routing it "
        "through resolve_read_dir_or_degrade would be circular."
    ),
    ("specify_cli/merge/resolve.py", "_resolve_mission_slug"): (
        "non-dir fallback: on the fail-closed coord window returns the raw slug STRING so "
        "merge --abort's slug resolution stays non-raising to clean up that broken state."
    ),
    (
        "specify_cli/migration/runtime_state_cutover.py",
        "_resolve_primary_home_or_degrade",
    ): (
        "non-dir sentinel: returns None as the DEGRADE signal (a resolver-failure marker "
        "the caller compares for equality), never a substitute read_dir; resolution is via "
        "resolve_artifact_surface(...).path, not the read seam."
    ),
    ("specify_cli/orchestrator_api/commands.py", "_resolve_mission_dir_or_fail"): (
        "fail-closed translate: the except calls _fail (NoReturn typer.Exit) surfacing the "
        "typed error_code + candidate paths on the external envelope — no directory degrade."
    ),
    ("mission_runtime/resolution.py", "_resolve_mission_slug"): (
        "translate: boundary translation of StatusReadPathNotFound/MissionSelectorAmbiguous "
        "into the single consumer-facing ActionContextError (from exc), preserving error_code "
        "— no dir fallback."
    ),
    ("mission_runtime/resolution.py", "resolve_topology"): (
        "non-dir fallback: on an unresolvable/ambiguous handle sets candidate_dir=None to "
        "pass the raw handle through and returns a MissionTopology, not a read_dir."
    ),
    ("mission_runtime/resolution.py", "mission_context_for"): (
        "translate: re-raises StatusReadPathNotFound/MissionSelectorAmbiguous as "
        "ActionContextError (boundary translation) before any read dir is composed."
    ),
    ("mission_runtime/resolution.py", "_resolve_status_surface_dir"): (
        "translate: the coord-read arm (StatusReadPathNotFound) TRANSLATES to "
        "ActionContextError rather than degrading (degrading would hand back the stale "
        "split-brain surface the refusal exists to kill). Its dir-fallback arm catches only "
        "the non-coord FileNotFoundError/ValueError, outside the coord-error family."
    ),
    ("mission_runtime/resolution.py", "resolve_placement_only"): (
        "translate: mirrors _resolve_mission_slug — StatusReadPathNotFound/MissionSelectorAmbiguous "
        "are re-raised as ActionContextError at entry canonicalization, not degraded to a dir."
    ),
    ("mission_runtime/resolution.py", "coord_read_dir_for"): (
        "non-dir sentinel: the documented Path|None projection absorbs the coord-error family "
        "(incl. the CoordinationBranchDeleted subclass) to None ('nothing to reconcile'); "
        "accept-path callers use resolve_artifact_surface directly for loud fail-closed."
    ),
    ("mission_runtime/write_target_degrade.py", "resolve_write_target_or_degrade"): (
        "WRITE-target degrade (sibling seam): resolves resolve_placement_only into a write "
        "CommitTarget and degrades to CommitTarget(ref=degrade_ref) — categorically not a "
        "read DIRECTORY, so the read seam does not apply."
    ),
}


@dataclass(frozen=True)
class Violation:
    """A flagged bypass: ``file:line`` plus the rule it broke (the failure contract)."""

    label: str
    lineno: int
    rule: str

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        return f"{self.label}:{self.lineno} -- {self.rule}"


# --------------------------------------------------------------------------- #
# Shared AST utilities
# --------------------------------------------------------------------------- #
def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _call_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _enclosing_name_map(tree: ast.Module) -> dict[int, str]:
    """Map ``id(node)`` -> nearest enclosing function name for every Try / Call node.

    ``"<module>"`` when a node sits outside any function. A recursive descent that
    tracks the current function so nested definitions attribute correctly.
    """
    mapping: dict[int, str] = {}

    def visit(node: ast.AST, current: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, child.name)
            else:
                if isinstance(child, (ast.Try, ast.Call)):
                    mapping[id(child)] = current
                visit(child, current)

    visit(tree, "<module>")
    return mapping


def _enclosing_func_map(
    tree: ast.Module,
) -> dict[int, ast.FunctionDef | ast.AsyncFunctionDef | None]:
    """Map ``id(node)`` -> nearest enclosing function NODE (``None`` at module scope)."""
    mapping: dict[int, ast.FunctionDef | ast.AsyncFunctionDef | None] = {}

    def visit(node: ast.AST, current: ast.FunctionDef | ast.AsyncFunctionDef | None) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                mapping[id(child)] = current
                visit(child, child)
            else:
                if isinstance(child, (ast.Try, ast.Call)):
                    mapping[id(child)] = current
                visit(child, current)

    visit(tree, None)
    return mapping


# --------------------------------------------------------------------------- #
# Allocation single-seam check (T014) -- positive AST def-use
# --------------------------------------------------------------------------- #
def _is_seam_call(call: ast.Call) -> bool:
    return _call_name(call) == _SEAM


def _is_parent_ref_of_seam(value: ast.expr, seam_bound: set[str]) -> bool:
    """``<seam-bound name>.parent_ref`` or ``resolve_lane_base_or_refuse(...).parent_ref``."""
    if not (isinstance(value, ast.Attribute) and value.attr == _PARENT_REF_ATTR):
        return False
    inner = value.value
    if isinstance(inner, ast.Name) and inner.id in seam_bound:
        return True
    return isinstance(inner, ast.Call) and _is_seam_call(inner)


def _seam_derived_names(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[set[str], set[str]]:
    """Within ``func``: names bound to a seam call, and names bound to its ``parent_ref``.

    Two passes so the second (``x = decision.parent_ref``) sees the full set of
    seam-bound names regardless of source order.
    """
    assigns = [n for n in ast.walk(func) if isinstance(n, ast.Assign)]
    seam_bound: set[str] = set()
    for assign in assigns:
        if isinstance(assign.value, ast.Call) and _is_seam_call(assign.value):
            seam_bound.update(t.id for t in assign.targets if isinstance(t, ast.Name))
    parent_ref_names: set[str] = set()
    for assign in assigns:
        if _is_parent_ref_of_seam(assign.value, seam_bound):
            parent_ref_names.update(t.id for t in assign.targets if isinstance(t, ast.Name))
    return seam_bound, parent_ref_names


def _parent_arg(call: ast.Call, pos: int, kw: str) -> ast.expr | None:
    for keyword in call.keywords:
        if keyword.arg == kw:
            return keyword.value
    if 0 <= pos < len(call.args):
        arg = call.args[pos]
        return None if isinstance(arg, ast.Starred) else arg
    return None


def _is_seam_parent(arg: ast.expr, seam_bound: set[str], parent_ref_names: set[str]) -> bool:
    if _is_parent_ref_of_seam(arg, seam_bound):
        return True
    return isinstance(arg, ast.Name) and arg.id in parent_ref_names


def _allocation_violations(tree: ast.Module, label: str) -> list[Violation]:
    """Flag every creation-call lane-parent argument that does NOT trace to the seam."""
    encl = _enclosing_func_map(tree)
    seam_cache: dict[int, tuple[set[str], set[str]]] = {}
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name is None or name not in _CREATION_PARENT_ARG:
            continue
        pos, kw = _CREATION_PARENT_ARG[name]
        arg = _parent_arg(node, pos, kw)
        if arg is None:
            continue
        func = encl.get(id(node))
        if func is None:
            violations.append(Violation(label, node.lineno, _RULE_INLINE))
            continue
        if id(func) not in seam_cache:
            seam_cache[id(func)] = _seam_derived_names(func)
        seam_bound, parent_ref_names = seam_cache[id(func)]
        if not _is_seam_parent(arg, seam_bound, parent_ref_names):
            violations.append(Violation(label, node.lineno, _RULE_INLINE))
    return violations


def _count_creation_calls(tree: ast.Module) -> int:
    return sum(
        1
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and _call_name(n) in _CREATION_PARENT_ARG
    )


def _route_coverage(tree: ast.Module) -> set[str]:
    """Collect every ``route=LaneAllocationRoute.X`` passed to a seam call."""
    routes: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_seam_call(node)):
            continue
        for keyword in node.keywords:
            if keyword.arg != "route":
                continue
            val = keyword.value
            if (
                isinstance(val, ast.Attribute)
                and isinstance(val.value, ast.Name)
                and val.value.id == _ROUTE_ENUM
            ):
                routes.add(val.attr)
    return routes


def _enum_members(tree: ast.Module, class_name: str) -> set[str]:
    members: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    members.update(t.id for t in stmt.targets if isinstance(t, ast.Name))
    return members


def _defines_symbol(tree: ast.Module, name: str) -> bool:
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and node.name == name
        for node in ast.walk(tree)
    )


# --------------------------------------------------------------------------- #
# Read-degrade family check (T015)
# --------------------------------------------------------------------------- #
def _handler_coord_errors(handler: ast.ExceptHandler) -> set[str]:
    caught_type = handler.type
    if caught_type is None:
        return set()
    parts = caught_type.elts if isinstance(caught_type, ast.Tuple) else [caught_type]
    names: set[str] = set()
    for part in parts:
        if isinstance(part, ast.Name):
            names.add(part.id)
        elif isinstance(part, ast.Attribute):
            names.add(part.attr)
    return names & _COORD_READ_ERRORS


def _routed_funcs(tree: ast.Module) -> set[str]:
    """Function names whose body calls :func:`resolve_read_dir_or_degrade`."""
    name_map = _enclosing_name_map(tree)
    return {
        name_map[id(node)]
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and _call_name(node) == _READ_SEAM
        and id(node) in name_map
    }


def _coord_catch_funcs(tree: ast.Module) -> set[str]:
    """Function names containing a ``try/except`` that catches a coord read-error type."""
    name_map = _enclosing_name_map(tree)
    funcs: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(
            _handler_coord_errors(h) for h in node.handlers
        ):
            funcs.add(name_map.get(id(node), "<module>"))
    return funcs


def _read_degrade_violations(
    tree: ast.Module,
    label: str,
    allowlist_funcs: set[str],
    routed_funcs: set[str],
) -> list[Violation]:
    """Flag coord read-degrade ``try/except`` sites neither seam-routed nor allowlisted."""
    name_map = _enclosing_name_map(tree)
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not any(_handler_coord_errors(h) for h in node.handlers):
            continue
        func = name_map.get(id(node), "<module>")
        if func in routed_funcs or func in allowlist_funcs:
            continue
        violations.append(Violation(label, node.lineno, _RULE_UNREG))
    return violations


def _allowlist_funcs_for(relpath: str) -> set[str]:
    return {fn for (rp, fn) in _READ_DEGRADE_ALLOWLIST if rp == relpath}


def _not_read_dir_funcs_for(relpath: str) -> set[str]:
    return {fn for (rp, fn) in _NOT_READ_DIR_DEGRADE_ALLOWLIST if rp == relpath}


# The two source roots the tree-wide read-degrade sweep walks.
_READ_DEGRADE_ROOTS = ("specify_cli", "mission_runtime")


def _iter_src_py() -> list[tuple[str, Path]]:
    """(relpath-from-src, path) for every ``.py`` under the swept source roots."""
    found: list[tuple[str, Path]] = []
    for root in _READ_DEGRADE_ROOTS:
        for path in sorted((_SRC / root).rglob("*.py")):
            found.append((path.relative_to(_SRC).as_posix(), path))
    return found


def _coord_catch_sites_tree_wide() -> list[tuple[str, str, int]]:
    """Every coord-catch ``try/except`` under the swept roots as (relpath, func, lineno)."""
    sites: list[tuple[str, str, int]] = []
    for relpath, path in _iter_src_py():
        tree = _parse(path)
        name_map = _enclosing_name_map(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Try) and any(
                _handler_coord_errors(h) for h in node.handlers
            ):
                sites.append(
                    (relpath, name_map.get(id(node), "<module>"), node.lineno)
                )
    return sites


def _rationale_names_a_failed_strategy(rationale: str) -> bool:
    return bool(rationale.strip()) and any(tok in rationale for tok in _STRATEGY_TOKENS)


# --------------------------------------------------------------------------- #
# Synthetic fixtures (deterministic non-vacuity, T016)
# --------------------------------------------------------------------------- #
_ALLOC_BYPASS_FIXTURE = '''
def allocate_bypass(repo_root, wt, br, coordination_branch, mission_branch):
    # composes a parent ref inline (NOT the literal spelling the guard is told to
    # ignore) and hands it straight to the creation call -> a bypass.
    parent = coordination_branch or mission_branch
    _create_lane_worktree(repo_root, wt, br, parent)
'''

_ALLOC_CLEAN_FIXTURE = '''
def allocate_clean(repo_root, wt, br, base, coordination_branch, mission_branch, wp_id):
    decision = resolve_lane_base_or_refuse(
        base=base,
        route=LaneAllocationRoute.FRESH_LEGACY,
        coordination_branch=coordination_branch,
        mission_branch=mission_branch,
        wp_id=wp_id,
    )
    _ensure_mission_branch(repo_root, decision.parent_ref, "main")
    _create_lane_worktree(repo_root, wt, br, decision.parent_ref)
'''

_ALLOC_INLINE_SEAM_FIXTURE = '''
def allocate_inline(repo_root, wt, br, base, coordination_branch, mission_branch, wp_id):
    _create_lane_worktree(
        repo_root,
        wt,
        br,
        resolve_lane_base_or_refuse(
            base=base,
            route=LaneAllocationRoute.FRESH_COORD,
            coordination_branch=coordination_branch,
            mission_branch=mission_branch,
            wp_id=wp_id,
        ).parent_ref,
    )
'''

_ROUTE_MISSING_FIXTURE = '''
def only_three_routes(base, wp_id):
    resolve_lane_base_or_refuse(base=base, route=LaneAllocationRoute.REUSE, wp_id=wp_id)
    resolve_lane_base_or_refuse(base=base, route=LaneAllocationRoute.CRASH_RECOVERY, wp_id=wp_id)
    resolve_lane_base_or_refuse(base=base, route=LaneAllocationRoute.FRESH_COORD, wp_id=wp_id)
'''

_READ_BYPASS_FIXTURE = '''
def bypass_read(repo_root, mission_slug, primary_dir):
    from x import CoordinationBranchDeleted
    try:
        resolved = placement_seam(repo_root, mission_slug).read_dir(KIND)
    except CoordinationBranchDeleted:
        return primary_dir
    return resolved
'''

_READ_ROUTED_FIXTURE = '''
def routed_read(repo_root, mission_slug, primary_dir):
    try:
        decision = resolve_read_dir_or_degrade(
            repo_root, mission_slug, KIND,
            strategy=ReadDegradeStrategy.DEGRADE_TO_FEATURE_DIR,
            caught=(CoordinationBranchDeleted,), degrade_target=primary_dir,
        )
    except CoordinationBranchDeleted:
        return primary_dir
    return decision.read_dir
'''


def _fixture_line(source: str, lineno: int) -> str:
    return source.splitlines()[lineno - 1]


# --------------------------------------------------------------------------- #
# Tests -- allocation single-seam
# --------------------------------------------------------------------------- #
def test_allocator_defines_the_anchored_symbols() -> None:
    """Anchor on symbols: a rename of the seam / route enum / creation calls fails loud."""
    tree = _parse(_ALLOCATOR)
    assert _defines_symbol(tree, _SEAM), f"seam symbol {_SEAM!r} missing -- anchor broke"
    assert _defines_symbol(tree, _ROUTE_ENUM), f"{_ROUTE_ENUM!r} enum missing"
    for creation_symbol in _CREATION_PARENT_ARG:
        assert _defines_symbol(tree, creation_symbol), f"{creation_symbol!r} missing"


def test_every_lane_parent_ref_traces_to_the_seam() -> None:
    tree = _parse(_ALLOCATOR)
    # Non-vacuity of the live scan: there must actually be creation calls to check.
    assert _count_creation_calls(tree) >= 2
    violations = _allocation_violations(tree, "worktree_allocator.py")
    assert not violations, "inline parent-ref bypass(es):\n" + "\n".join(
        str(v) for v in violations
    )


def test_all_four_routes_reach_the_seam() -> None:
    tree = _parse(_ALLOCATOR)
    members = _enum_members(tree, _ROUTE_ENUM)
    coverage = _route_coverage(tree)
    assert members == set(_EXPECTED_ROUTES), f"route enum drifted: {members}"
    assert coverage == set(_EXPECTED_ROUTES), (
        f"routes not reaching the seam: {set(_EXPECTED_ROUTES) - coverage}"
    )


def test_allocation_checker_flags_an_inline_parent_ref() -> None:
    """Non-vacuity: the checker flags a synthetic inline bypass at the right file:line."""
    tree = ast.parse(_ALLOC_BYPASS_FIXTURE)
    violations = _allocation_violations(tree, "<synthetic_alloc_bypass>")
    assert len(violations) == 1
    flagged = violations[0]
    assert flagged.rule == _RULE_INLINE
    assert flagged.label == "<synthetic_alloc_bypass>"
    assert "_create_lane_worktree" in _fixture_line(_ALLOC_BYPASS_FIXTURE, flagged.lineno)


def test_allocation_checker_passes_seam_routed_forms() -> None:
    """Non-vacuity guard against a checker that flags everything: both seam forms pass."""
    assert _allocation_violations(ast.parse(_ALLOC_CLEAN_FIXTURE), "<clean>") == []
    assert _allocation_violations(ast.parse(_ALLOC_INLINE_SEAM_FIXTURE), "<inline>") == []


def test_route_coverage_checker_is_non_vacuous() -> None:
    """A route missing from the seam calls is detectable (proper subset of expected)."""
    coverage = _route_coverage(ast.parse(_ROUTE_MISSING_FIXTURE))
    assert coverage == {"REUSE", "CRASH_RECOVERY", "FRESH_COORD"}
    assert coverage < set(_EXPECTED_ROUTES)  # missing FRESH_LEGACY -> would fail live check


# --------------------------------------------------------------------------- #
# Tests -- read-degrade family
# --------------------------------------------------------------------------- #
def test_migrated_read_sites_route_through_the_seam() -> None:
    for relpath in _MIGRATED_READ_SITES:
        tree = _parse(_SRC / relpath)
        assert _READ_SEAM in _routed_funcs_names(tree), (
            f"{relpath} no longer routes through {_READ_SEAM} -- migration regressed"
        )
        # The migration removed the hand-rolled coord-catch degrade; any remaining
        # coord-catch must live in a seam-routed function (never an un-routed bypass).
        stray = _read_degrade_violations(
            tree, relpath, _allowlist_funcs_for(relpath), _routed_funcs(tree)
        )
        assert not stray, "un-routed coord degrade in migrated site:\n" + "\n".join(
            str(v) for v in stray
        )


def _routed_funcs_names(tree: ast.Module) -> set[str]:
    """Whether any function routes through the read seam (helper for the migrated check)."""
    return {_READ_SEAM} if _routed_funcs(tree) else set()


def test_tree_wide_read_degrade_sites_are_dispositioned() -> None:
    """TREE-WIDE (#3462 fold): every coord-catch site under the two source roots must be
    (a) seam-routed, (b) family-allowlisted, or (c) not-a-read-dir-degrade-allowlisted.

    Walks EVERY ``.py`` (not a hardcoded registry), so a NEW coord-catch introduced
    anywhere fails until dispositioned.
    """
    all_violations: list[Violation] = []
    for relpath, path in _iter_src_py():
        tree = _parse(path)
        # (b) family ∪ (c) not-a-read-dir-degrade are both acceptable dispositions.
        allowlisted = _allowlist_funcs_for(relpath) | _not_read_dir_funcs_for(relpath)
        all_violations += _read_degrade_violations(
            tree, relpath, allowlisted, _routed_funcs(tree)
        )
    assert not all_violations, "un-dispositioned coord-catch site(s):\n" + "\n".join(
        str(v) for v in all_violations
    )


def test_tree_wide_walk_visits_many_files_and_finds_known_sites() -> None:
    """Non-vacuity of the walk: it visits >1 file and discovers the known coord-catch sites.

    Also proves the disposition is load-bearing: dropping a real site's allowlist entry
    WOULD flag it as a violation (so the guard genuinely gates, not vacuously passes).
    """
    files = _iter_src_py()
    assert len(files) > 1, "tree-wide walk visited <=1 file -- roots resolved wrong"

    sites = _coord_catch_sites_tree_wide()
    # The census is ~27 coord-catch sites; guard a sane lower bound so a walk that
    # silently stops finding sites (bad root / parse skip) fails loudly.
    assert len(sites) >= 20, f"tree-wide walk found only {len(sites)} coord-catch sites"

    site_keys = {(rp, fn) for (rp, fn, _ln) in sites}
    # A representative site from each disposition kind must be discovered by the walk.
    known = {
        ("specify_cli/status/aggregate.py", "_resolve_read_dir"),  # (b) family
        ("mission_runtime/resolution.py", "coord_read_dir_for"),  # (c) non-dir
        ("specify_cli/cli/commands/next_cmd.py", "_resolve_mission_slug"),  # (c) re-raise
    }
    assert known <= site_keys, f"walk missed known sites: {known - site_keys}"

    # Load-bearing check: pick a real (c) site, strip its disposition, and confirm the
    # per-file checker WOULD flag it. Proves the tree-wide pass is not vacuously green.
    victim_rel, victim_fn = "mission_runtime/resolution.py", "coord_read_dir_for"
    tree = _parse(_SRC / victim_rel)
    remaining = (_allowlist_funcs_for(victim_rel) | _not_read_dir_funcs_for(victim_rel)) - {
        victim_fn
    }
    flagged = _read_degrade_violations(tree, victim_rel, remaining, _routed_funcs(tree))
    assert any(v.rule == _RULE_UNREG for v in flagged), (
        "removing a real site's disposition did NOT flag it -- guard is vacuous"
    )


def test_not_read_dir_degrade_allowlist_entries_point_at_live_sites() -> None:
    """No stale (c) entries: each allowlisted (file, function) still holds a coord-catch site.

    Mirrors ``test_read_degrade_allowlist_entries_point_at_live_sites`` for the family (b).
    """
    for (relpath, func) in _NOT_READ_DIR_DEGRADE_ALLOWLIST:
        tree = _parse(_SRC / relpath)
        assert func in _coord_catch_funcs(tree), (
            f"stale not-read-dir allowlist entry {relpath}:{func} -- "
            "no coord-catch try/except there"
        )


def test_read_degrade_allowlists_are_disjoint_and_not_double_routed() -> None:
    """A site cannot hide in two allowlists, nor be allowlisted AND seam-routed.

    Guards the two-allowlist risk: a genuine family (b) site must not be silently parked
    in the not-a-read-dir (c) list, and a seam-routed function must not also be allowlisted
    (which would let a later un-routing pass unnoticed).
    """
    family_keys = set(_READ_DEGRADE_ALLOWLIST)
    not_dir_keys = set(_NOT_READ_DIR_DEGRADE_ALLOWLIST)
    overlap = family_keys & not_dir_keys
    assert not overlap, f"(b) and (c) allowlists overlap: {overlap}"

    # No allowlisted (b)/(c) function is ALSO seam-routed in its own file (a): routing +
    # allowlisting the same function is contradictory and would mask a future un-routing.
    for (relpath, func) in family_keys | not_dir_keys:
        routed = _routed_funcs(_parse(_SRC / relpath))
        assert func not in routed, (
            f"{relpath}:{func} is both seam-routed (a) and allowlisted -- "
            "remove the allowlist entry"
        )


def test_family_allowlist_files_are_registered() -> None:
    """Every family-bespoke (b) allowlist file is documented in ``_READ_DEGRADE_REGISTRY``."""
    registry = set(_READ_DEGRADE_REGISTRY)
    for (relpath, _func) in _READ_DEGRADE_ALLOWLIST:
        assert relpath in registry, (
            f"{relpath} owns a family allowlist entry but is absent from "
            "_READ_DEGRADE_REGISTRY -- add it to the documented family surface"
        )


def test_read_degrade_allowlist_entries_name_a_failed_strategy() -> None:
    """Anti-rubber-stamp: every allowlist rationale must name a failed strategy + reason."""
    for (relpath, func), rationale in _READ_DEGRADE_ALLOWLIST.items():
        assert _rationale_names_a_failed_strategy(rationale), (
            f"{relpath}:{func} rationale names no ReadDegradeStrategy -- rubber-stamp"
        )
    # Non-vacuity of the predicate itself: a no-strategy rationale WOULD fail the test.
    assert not _rationale_names_a_failed_strategy("this site is genuinely complicated")
    assert not _rationale_names_a_failed_strategy("")


def test_read_degrade_allowlist_entries_point_at_live_sites() -> None:
    """No stale entries: each allowlisted (file, function) still holds a coord-catch site."""
    for (relpath, func) in _READ_DEGRADE_ALLOWLIST:
        tree = _parse(_SRC / relpath)
        assert func in _coord_catch_funcs(tree), (
            f"stale allowlist entry {relpath}:{func} -- no coord-catch try/except there"
        )


def test_read_degrade_checker_flags_an_unregistered_site() -> None:
    """Non-vacuity: a synthetic un-allowlisted degrade is flagged at the right file:line."""
    tree = ast.parse(_READ_BYPASS_FIXTURE)
    violations = _read_degrade_violations(
        tree, "<synthetic_read_bypass>", allowlist_funcs=set(), routed_funcs=_routed_funcs(tree)
    )
    assert len(violations) == 1
    flagged = violations[0]
    assert flagged.rule == _RULE_UNREG
    assert flagged.label == "<synthetic_read_bypass>"
    assert _fixture_line(_READ_BYPASS_FIXTURE, flagged.lineno).strip().startswith("try")


def test_read_degrade_checker_accepts_seam_routed_and_allowlisted() -> None:
    """The escape hatches work: a seam-routed function and an allowlisted function pass."""
    routed_tree = ast.parse(_READ_ROUTED_FIXTURE)
    assert (
        _read_degrade_violations(
            routed_tree, "<routed>", allowlist_funcs=set(), routed_funcs=_routed_funcs(routed_tree)
        )
        == []
    )
    bypass_tree = ast.parse(_READ_BYPASS_FIXTURE)
    assert (
        _read_degrade_violations(
            bypass_tree, "<allowlisted>", allowlist_funcs={"bypass_read"}, routed_funcs=set()
        )
        == []
    )
