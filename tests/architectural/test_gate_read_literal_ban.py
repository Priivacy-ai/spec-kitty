"""Architectural literal-ban ratchet (FR-010 / C-005): the gate-read+write seam.

Mission ``gate-read-surface-completion-01KVW9B0`` folded every planning-lifecycle
gate command onto ONE kind-aware read seam (``resolve_planning_read_dir`` /
``_planning_read_dir``) and re-pointed every write-branch resolver onto the
PRIMARY-anchored ``meta.json`` lookup (``primary_feature_dir_for_mission``,
mirroring ``resolve_merge_target_branch``). This ratchet makes the consolidation
*permanent* and FR-004 / FR-009(e) *enforceable* — without it those FRs are
documentation and a future command silently re-reads the coordination worktree
(read regression) or re-commits a planning artifact to the protected repo primary
``main`` (write regression).

The contract (``contracts/gate-read-seam.md`` §"Ratchet contract") defines TWO arms.

READ arm — FAIL if any enumerated gate-command entry function:

* directly joins ``<feature_dir>/{spec,plan,tasks,research,data-model}.md`` where
  ``<feature_dir>`` is bound from a TOPOLOGY-ROUTED resolver
  (``_find_feature_directory`` / ``resolve_handle_to_read_path`` /
  ``resolve_feature_dir_for_mission``) — i.e. the planning read resolves to the
  coordination worktree under coord topology. The driver bug (#2107): ``setup_plan``
  read ``coord/spec.md`` (absent since #2106) and blocked ``SPEC_FILE_MISSING``.
* (DIR-READ arm — closeout N+1, debbie §3) joins a BARE PRIMARY-partition subdir
  (``tasks`` / ``research`` / ``checklists``) onto a topology-routed dir. The accept
  gate's ``_iter_work_packages`` did ``feature_path / "tasks"`` off the coord-aware
  resolver and read the materialized ``-coord`` husk (no ``tasks/`` dir), raising
  ``AcceptanceError: ... has no tasks directory`` for a coord mission whose WP tasks
  live (correctly) only on PRIMARY. This arm is scoped to the accept-gate package
  (``acceptance/``); the implement/review/merge command surface carries the same
  shape as a SEPARATE tracked residual (``_DIR_READ_KNOWN_RESIDUALS``).

WRITE arm (G-6) — FAIL if any enumerated write-branch resolver
(``get_feature_target_branch`` / ``resolve_target_branch`` / the ``finalize-tasks``
commit-branch resolution) anchors its ``meta.json`` lookup to
``candidate_feature_dir_for_mission`` (→ coord → fallback protected repo primary
``main``) instead of ``primary_feature_dir_for_mission`` / the kind-aware write seam.

ALLOWED (never flagged): the read seam itself (``_planning_read_dir`` /
``resolve_planning_read_dir`` results), the write seam
(``primary_feature_dir_for_mission`` / ``resolve_merge_target_branch``), STATUS reads
off ``status_feature_dir``, STATUS/coord commit destinations, and the
self-bookkeeping allowlist (``meta.json``, provenance). The write arm flags ONLY a
write-BRANCH ``meta.json`` resolution anchored to the candidate dir — NOT every
legitimate topology-aware status read.

Non-vacuity is proven by a MANDATORY runnable synthetic-AST self-test (both arms: a
violating snippet is FLAGGED, a clean snippet PASSES) and a PINNED enumerated
surface/resolver set (a new un-scanned gate command or write-branch resolver FAILS
the pin test) — not a recorded manual mutation log (DIRECTIVE_041: a rotting proof
is not a gate).

Strictness mirrors ``tests/architectural/test_topology_resolution_boundary.py``:
``pytestmark = pytest.mark.architectural``; ``_REPO_ROOT = parents[2]``; AST scans
(so comments/docstrings that merely *mention* an idiom never trip the scan);
pinned surface sets carrying per-entry contract citations.

Spec source: spec.md FR-009/FR-010, C-005; plan.md IC-07; research.md Decision 5;
contracts/gate-read-seam.md §"Ratchet contract"; mission
``gate-read-surface-completion-01KVW9B0``.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.architectural._ratchet_keys import composite_key

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"


# ---------------------------------------------------------------------------
# Pinned vocabulary (the seam contract, encoded).
# ---------------------------------------------------------------------------

# The planning-artifact basenames the READ arm fences. Direct joins of these
# onto a topology-routed dir in a gate entry function are the C-005 prohibition.
_PLANNING_ARTIFACT_LITERALS: frozenset[str] = frozenset(
    {"spec.md", "plan.md", "tasks.md", "research.md", "data-model.md"}
)

# The PRIMARY-partition SUBDIRECTORY basenames the READ arm fences as a BARE-DIR
# read. Closeout N+1 (debbie §3): ``_iter_work_packages`` joined ``tasks/`` (the
# WORK_PACKAGE_TASK partition) onto a topology-routed dir and read the coord husk
# (no tasks/ dir). Unlike the ``.md`` literals this is a bare directory read, so
# the ``.md`` scanner alone never saw it. ``research`` and ``checklists`` are the
# other PRIMARY-partition subtrees the accept-gate encoding normalizer scans, so
# they are fenced the same way (all three are PRIMARY-partition kinds — a topology
# read of any of them off a coord-aware dir lands on the husk).
_PLANNING_DIR_LITERALS: frozenset[str] = frozenset(
    {"tasks", "research", "checklists"}
)

# TOPOLOGY-ROUTED read resolvers (the coord-aware ones). A planning-artifact join
# onto a dir bound from one of these is a READ-arm violation: under coordination
# topology they select the coordination worktree, whose mission dir lacks the
# (PRIMARY-partition) planning artifact since #2106.
#
# Closeout (#2107 residual): ``resolve_feature_dir_for_slug`` and
# ``candidate_feature_dir_for_mission`` are added here — both delegate to the
# coord-aware ``_resolve_mission_read_path`` primitive, so a planning join off
# either is the same coord/primary divergence. The ``research`` (Phase 0) command
# bound ``feature_dir = resolve_feature_dir_for_slug`` and validated
# ``coord/plan.md`` — the third N+1 the manual denylist missed (paula closeout).
_TOPOLOGY_ROUTED_READ_RESOLVERS: frozenset[str] = frozenset(
    {
        "_find_feature_directory",
        "resolve_handle_to_read_path",
        "resolve_feature_dir_for_mission",
        "resolve_feature_dir_for_slug",
        "candidate_feature_dir_for_mission",
    }
)

# The kind-aware READ seam (+ the topology-blind PRIMARY constructor). A planning
# join onto a dir bound from one of these is the SANCTIONED shape — never flagged.
_SANCTIONED_READ_SEAM_FUNCS: frozenset[str] = frozenset(
    {
        "_planning_read_dir",
        "resolve_planning_read_dir",
        "primary_feature_dir_for_mission",
    }
)

# WRITE arm: the coord-aware candidate constructor whose ``meta.json`` lookup
# falls back to protected ``main`` (G-6 prohibition), and the sanctioned
# PRIMARY-anchored constructor that mirrors ``resolve_merge_target_branch``.
_WRITE_CANDIDATE_ANCHOR = "candidate_feature_dir_for_mission"
_WRITE_PRIMARY_ANCHOR = "primary_feature_dir_for_mission"
_META_JSON_LITERAL = "meta.json"


# ---------------------------------------------------------------------------
# CALL-SHAPE arm vocabulary (coord-read-residuals FR-007, WP01).
#
# The two arms above fence PATH-JOIN literals (``dir / "spec.md"`` /
# ``dir / "tasks"`` / ``anchor(...) / "meta.json"``). They are STRUCTURALLY BLIND
# to two read shapes this Mission routes, because neither is a planning path-join
# literal:
#
#   (a) IDENTITY  — ``resolve_mission_identity(dir)`` / ``get_mission_type(dir)``
#       (a ``meta.json`` read expressed as a FUNCTION CALL, not a path join).
#   (b) LANES.JSON — ``read_lanes_json(dir)`` / ``require_lanes_json(dir)``
#       (a LANE_STATE read expressed as a function call).
#
# Both are coord-vs-primary divergences: under coordination topology a ``dir``
# bound from a coord-aware resolver selects the STATUS-only ``-coord`` husk, which
# (post-#2106) carries neither ``meta.json`` nor ``lanes.json``. The call-shape arm
# flags such a call when its FIRST arg is a ``dir`` bound (in the same function)
# from a coord-aware resolver WITHOUT a primary fold.
#
# Scope is bounded PER SHAPE (FR-007 / SC-005) so the arm never red-CIs on
# out-of-scope strangers (``sync/``, ``acceptance/``, ``policy/``,
# ``orchestrator_api/`` — follow-on): identity → ``cli/commands/`` +
# ``agent_utils/status.py``; lanes.json → ``merge/`` + ``lanes/`` +
# ``core/worktree_topology.py``.

# The coord-aware read resolvers whose result, passed to an identity / lanes.json
# read, is the divergence shape (they select the coord husk under coord topology).
#
# FR-001 widening (root cause of the FR-001 hollowness — WP01 T001). The legacy
# 3-name set ({resolve_feature_dir_for_mission, candidate_feature_dir_for_mission,
# resolve_feature_dir_for_slug}) was NARROWER than the read-arm's
# ``_TOPOLOGY_ROUTED_READ_RESOLVERS`` (5 names: the 3 + ``_find_feature_directory`` +
# ``resolve_handle_to_read_path``). The one real one-hop residual —
# ``mission_setup_plan::_run_documentation_wiring`` ← ``setup_plan`` — binds
# ``feature_dir`` from ``_resolve_setup_plan_feature_dir`` (which delegates to
# ``_find_feature_directory``). With the 3-name set that caller binding was NOT
# recognized as coord-aware, so the one-hop check (T003) fired on no live caller and
# FR-001/SC-001/SC-006 were hollow. We therefore align with the read-arm set (so the
# two cannot silently re-diverge — guarded by
# ``test_callshape_coord_aware_set_aligns_with_read_arm``) AND additionally catalog
# the setup-plan wrapper ``_resolve_setup_plan_feature_dir`` — the exact binding name
# the residual's caller uses one hop up.
_COORD_AWARE_CALLSHAPE_RESOLVERS: frozenset[str] = _TOPOLOGY_ROUTED_READ_RESOLVERS | frozenset(
    {
        "_resolve_setup_plan_feature_dir",
    }
)

# The PRIMARY-fold seams. A ``dir`` bound from one of these (or an inline call to
# one) is the SANCTIONED shape and is NEVER flagged: the read lands on the durable
# PRIMARY ``kitty-specs/<slug>-<mid8>/`` home for every handle/topology.
_PRIMARY_FOLD_CALLSHAPE_FUNCS: frozenset[str] = frozenset(
    {
        "_canonicalize_primary_read_handle",
        "primary_feature_dir_for_mission",
        "resolve_planning_read_dir",
    }
)

# Shape (a): identity reads (a meta.json read expressed as a function call).
_IDENTITY_READ_FUNCS: frozenset[str] = frozenset(
    {"resolve_mission_identity", "get_mission_type"}
)

# Shape (b): lanes.json (LANE_STATE) reads.
_LANES_READ_FUNCS: frozenset[str] = frozenset(
    {"read_lanes_json", "require_lanes_json"}
)

# FR-008 (WP01 T002): the SANCTIONED primary attributes. When a kind-read's first
# arg is an ``ast.Attribute`` it is the executor-shape escape (``read_func(run.X)``)
# that the Name/Call branches never saw. Such an attribute is flagged UNLESS its
# member is a sanctioned primary attribute — ``.target_feature_dir`` is the
# primary-surface field on the run/context object (data-model §4). Any other
# coord-bearing attribute (e.g. ``run.feature_dir``) is flagged (SC-006).
_SANCTIONED_PRIMARY_ATTRS: frozenset[str] = frozenset({"target_feature_dir"})

# All read funcs fenced by the call-shape arm expose their first path argument as
# ``feature_dir``. Treat ``read_func(feature_dir=...)`` as equivalent to the first
# positional arg so the gate cannot be bypassed by keyword-call style.
_READ_FIRST_ARG_KEYWORDS: frozenset[str] = frozenset({"feature_dir"})


# ---------------------------------------------------------------------------
# Pinned enumerated surfaces. Adding a NEW gate command (read) or write-branch
# resolver WITHOUT adding it here makes the pin test below FAIL — a ratchet that
# silently skips a new surface is vacuous (T024.3).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Surface:
    """One scanned ``(module, function)`` with its contract citation."""

    rel_path: str
    func: str
    why: str


# READ-arm gate-command entry functions. Each is a planning-lifecycle command that
# reads a planning artifact; each MUST route those reads through the kind-aware seam.
_READ_ARM_SURFACES: tuple[_Surface, ...] = (
    _Surface(
        # #2056 decomposition: ``setup_plan`` relocated from ``mission.py`` into the
        # ``mission_setup_plan`` seam; scan the body where it now lives.
        "src/specify_cli/cli/commands/agent/mission_setup_plan.py",
        "setup_plan",
        "FR-009(a)/#2107 driver: reads spec.md/plan.md via the kind-aware seam, "
        "not the coord-aware feature_dir.",
    ),
    _Surface(
        # #2056 decomposition: ``record_analysis`` relocated from ``mission.py`` into
        # the ``mission_record_analysis`` seam; scan the body where it now lives.
        "src/specify_cli/cli/commands/agent/mission_record_analysis.py",
        "record_analysis",
        "FR-009(b)/#2102: collapses the coord-then-primary double-resolution onto "
        "resolve_planning_read_dir for the spec read.",
    ),
    _Surface(
        "src/specify_cli/cli/commands/agent/tasks.py",
        "map_requirements",
        "FR-009/#2064: WP tasks read surface routes through the seam.",
    ),
    _Surface(
        "src/specify_cli/acceptance/__init__.py",
        "collect_feature_summary",
        "FR-002/#2085 accept cluster: planning reads use planning_read_dir "
        "(seam); status reads stay on status_feature_dir (C-002).",
    ),
    _Surface(
        "src/specify_cli/cli/commands/research.py",
        "research",
        "#2107 residual (closeout): reads plan.md and scaffolds research.md / "
        "data-model.md via the kind-aware seam (RESEARCH / FINALIZED_EXECUTION_PLAN "
        "→ PRIMARY), not the coord-aware resolve_feature_dir_for_slug.",
    ),
)

# WRITE-arm branch resolvers. Each resolves a planning-artifact COMMIT/branch and
# MUST read ``target_branch`` from ``meta.json`` on the PRIMARY surface (G-6).
_WRITE_ARM_SURFACES: tuple[_Surface, ...] = (
    _Surface(
        "src/specify_cli/core/paths.py",
        "get_feature_target_branch",
        "G-6/WP00: meta.json anchored to primary_feature_dir_for_mission, "
        "mirroring resolve_merge_target_branch.",
    ),
    _Surface(
        "src/specify_cli/core/git_ops.py",
        "resolve_target_branch",
        "G-6/WP00: meta.json anchored to primary_feature_dir_for_mission.",
    ),
    _Surface(
        # #2056 decomposition: ``finalize_tasks`` relocated from ``mission.py`` into
        # the ``mission_finalize`` seam; scan the body where it now lives.
        "src/specify_cli/cli/commands/agent/mission_finalize.py",
        "finalize_tasks",
        "G-6/FR-009(e): the finalize-tasks commit-branch resolution reads "
        "planning_dir = primary_feature_dir_for_mission, never the candidate.",
    ),
)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _module_tree(rel_path: str) -> ast.Module:
    return ast.parse((_REPO_ROOT / rel_path).read_text(encoding="utf-8"))


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


# ===========================================================================
# READ-arm scanner.
# ===========================================================================
#
# Within a function, classify the *binding source* of every local name, then flag
# any ``<name> / "<planning artifact>.md"`` join whose name was bound from a
# topology-routed read resolver. A seam-derived dir (bound from _planning_read_dir
# / resolve_planning_read_dir / primary_feature_dir_for_mission) is the sanctioned
# shape and is NEVER flagged. This is precise: it fences the coord-vs-primary
# divergence (the real defect) without false-positiving on legitimate status-dir
# joins (status_feature_dir is bound from _status_read_feature_dir — not in either
# set — so a status read is neither flagged nor required to be seam-derived).


def _call_func_name(call: ast.Call) -> str | None:
    """The simple callee name of a ``Call`` (``f(...)`` or ``mod.f(...)``)."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _names_bound_from(func: ast.AST, callees: frozenset[str]) -> set[str]:
    """Local names assigned (directly) from a call to one of *callees*.

    Catches ``x = resolver(...)`` and ``x = resolver(...).attr`` (e.g.
    ``feature_dir = _find_feature_directory(...)``). Does not chase aliases
    (``y = x``); the consolidated code binds the read dir directly at its read
    site, so single-hop binding is sufficient and avoids false precision.
    """
    bound: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        # Unwrap a trailing attribute access on the call result.
        if isinstance(value, ast.Attribute):
            value = value.value
        if not isinstance(value, ast.Call):
            continue
        callee = _call_func_name(value)
        if callee is None or callee not in callees:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                bound.add(target.id)
    return bound


def _planning_join_base_name(node: ast.BinOp) -> str | None:
    """If *node* is ``<Name> / "<planning artifact>.md"``, return the base name.

    Only the ``pathlib`` ``/`` operator with a planning-artifact string literal on
    the right and a plain ``Name`` on the left qualifies. ``X / SOME_CONST`` (a
    named constant) and ``X / subdir / file`` are not this defect shape.
    """
    if not isinstance(node.op, ast.Div):
        return None
    right = node.right
    if not (isinstance(right, ast.Constant) and right.value in _PLANNING_ARTIFACT_LITERALS):
        return None
    left = node.left
    if isinstance(left, ast.Name):
        return left.id
    return None


def _planning_dir_join_base_name(node: ast.BinOp) -> str | None:
    """If *node* is ``<Name> / "<planning subdir>"``, return the base name.

    The BARE-DIRECTORY analogue of :func:`_planning_join_base_name`: a PRIMARY-
    partition subtree (``tasks`` / ``research`` / ``checklists``) joined onto a
    topology-routed dir. Closeout N+1 (debbie §3): ``_iter_work_packages`` did
    ``feature_path / "tasks"`` off the coord-aware resolver and read the husk. Only
    a plain ``Name / "<dir>"`` shape qualifies — ``X / SUBDIR_CONST`` or a deeper
    ``X / "tasks" / "WP01.md"`` chain (whose top BinOp's right is a ``.md`` file,
    not the dir literal) is not this shape.
    """
    if not isinstance(node.op, ast.Div):
        return None
    right = node.right
    if not (isinstance(right, ast.Constant) and right.value in _PLANNING_DIR_LITERALS):
        return None
    left = node.left
    if isinstance(left, ast.Name):
        return left.id
    return None


def _read_arm_scan(func: ast.AST, *, include_dirs: bool) -> list[str]:
    """Topology-routed planning joins inside *func* (shared scanner core).

    ``include_dirs`` toggles the bare-dir ``tasks/`` / ``research/`` / ``checklists/``
    arm (closeout N+1) ON TOP of the always-on ``.md`` planning-file arm. Returns a
    list of ``"<base_name> / <artifact>"`` descriptors — one per flagged join.

    STATUS dir reads stay clean by construction — they are joined off
    ``status_feature_dir`` (bound from ``_status_read_feature_dir``, NOT a
    topology-routed resolver in the fenced set), so neither arm trips on them.

    **T004 (inline-call shape, WP02):** also detects ``resolver(...) / "<artifact>"``
    where the left operand is a direct :class:`ast.Call` to a coord-aware resolver.
    Prior to T004 the scanner was blind to this shape — ``_find_first_for_review_wp``
    and ``list_tasks`` read ``tasks/`` inline without a two-hop binding.

    **C-008 (sub-path exclusion, WP02):** a dir-literal join (``Name / "tasks"`` or
    ``resolver(...) / "tasks"``) that is itself the left operand of a further
    ``/``-chain (e.g. ``/ "tasks" / wp_slug / …``) is NOT flagged.  These are per-WP
    review-cycle sub-artifact reads that legitimately stay coordination-aware —
    the matched read/write pair in ``review/cycle.py`` and the ``implement`` /
    ``review`` feedback paths (C-008).  The exclusion applies to the dir arm only;
    planning ``.md`` files are always terminal in real pathlib join chains.
    """
    topology_routed = _names_bound_from(func, _TOPOLOGY_ROUTED_READ_RESOLVERS)

    # C-008: pre-collect BinOp node ids that appear as the left operand of
    # another Div BinOp — i.e. they are part of a longer ``/ a / b / …`` chain.
    # Applied to the dir arm only; planning ``.md`` files are terminal.
    chained_binop_ids: set[int] = set()
    if include_dirs:
        for n in ast.walk(func):
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                chained_binop_ids.add(id(n.left))

    violations: list[str] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            continue

        right = node.right
        if not isinstance(right, ast.Constant):
            continue
        value: str = right.value  # type: ignore[assignment]

        is_md = value in _PLANNING_ARTIFACT_LITERALS
        is_dir = include_dirs and value in _PLANNING_DIR_LITERALS
        if not is_md and not is_dir:
            continue

        # C-008: a dir-literal join that is part of a longer path chain is a
        # review-cycle sub-artifact (``tasks / wp_slug / …``), not a bare PRIMARY
        # dir read.  Skip it to avoid flagging ``implement`` / ``review`` /
        # ``review/cycle.py`` review-cycle paths as false-positive residuals.
        if is_dir and id(node) in chained_binop_ids:
            continue

        left = node.left

        # Shape 1 (two-hop): a name explicitly bound from a coord-aware resolver
        # inside this scope is joined with a planning artifact or dir literal.
        if isinstance(left, ast.Name) and left.id in topology_routed:
            violations.append(f"{left.id} / {value}")

        # Shape 2 (T004 — inline-call): the resolver call is the DIRECT left
        # operand of the BinOp, with no intermediate name binding.  Pre-T004
        # this shape was scanner-invisible despite being the same coord-vs-primary
        # divergence as the two-hop form at runtime.
        elif isinstance(left, ast.Call):
            callee = _call_func_name(left)
            if callee is not None and callee in _TOPOLOGY_ROUTED_READ_RESOLVERS:
                violations.append(f"{callee}(...) / {value}")

    return violations


def read_arm_violations(func: ast.AST) -> list[str]:
    """Topology-routed planning-artifact + planning-subdir joins inside *func*.

    The FULL fence (both the ``.md`` planning-file arm and the bare-dir ``tasks/`` /
    ``research/`` / ``checklists/`` arm). Used for the enumerated gate surfaces, the
    accept-package (``acceptance/``) dir-read default-deny scan, and every self-test.

    The bare-dir arm is the closeout N+1 fence: a WORK_PACKAGE_TASK (``tasks/``)
    read off a coord-aware resolver lands on the materialized ``-coord`` husk whose
    ``tasks/`` dir is absent, breaking the accept gate.
    """
    return _read_arm_scan(func, include_dirs=True)


def read_arm_md_violations(func: ast.AST) -> list[str]:
    """``.md`` planning-file arm ONLY (no bare-dir arm).

    Used by the CLI-command default-deny scan, whose scope (the implement/review/
    merge command surface) carries many legitimate-shape WP-task ``tasks/`` dir
    reads that belong to a SEPARATE implement-loop write-surface mission (see
    ``test_dir_read_arm_known_residuals_are_pinned`` for the named cluster). Fencing
    the bare-dir arm there now would be out-of-scope scope-creep for THIS
    behavior-neutral accept-gate closeout (DIRECTIVE_024 / locality).
    """
    return _read_arm_scan(func, include_dirs=False)


# ===========================================================================
# WRITE-arm scanner.
# ===========================================================================
#
# Within a write-branch resolver, flag a ``meta.json`` lookup whose anchor dir is
# bound from ``candidate_feature_dir_for_mission`` (the G-6 bug shape: the
# candidate selects coord, whose dir lacks meta.json, silently falling back to the
# protected repo primary ``main``). The sanctioned shape anchors the meta read to
# ``primary_feature_dir_for_mission``. A function that reads meta.json must use the
# primary anchor; using the candidate anchor for a meta.json read is the violation.


def _builds_meta_path_from(func: ast.AST, anchor: str) -> bool:
    """True iff *func* builds a ``.../meta.json`` Path anchored on *anchor*().

    Matches ``anchor(...) / "meta.json"`` directly and the two-hop form
    ``d = anchor(...); d / "meta.json"`` (the consolidated resolvers use the
    latter). Comments/docstrings mentioning the anchor never match (AST only).
    """
    anchored_names = _names_bound_from(func, frozenset({anchor}))
    for node in ast.walk(func):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            continue
        right = node.right
        if not (isinstance(right, ast.Constant) and right.value == _META_JSON_LITERAL):
            continue
        left = node.left
        # ``anchor(...) / "meta.json"``
        if isinstance(left, ast.Call) and _call_func_name(left) == anchor:
            return True
        # ``d / "meta.json"`` where ``d = anchor(...)``
        if isinstance(left, ast.Name) and left.id in anchored_names:
            return True
    return False


def write_arm_anchors(func: ast.AST) -> tuple[bool, bool]:
    """Return ``(reads_via_candidate, reads_via_primary)`` for *func*.

    ``reads_via_candidate`` is the G-6 violation flag. A write-branch resolver may
    legitimately call ``candidate_feature_dir_for_mission`` for a STATUS purpose;
    the violation is specifically a ``meta.json`` (target_branch) read anchored on
    the candidate.
    """
    return (
        _builds_meta_path_from(func, _WRITE_CANDIDATE_ANCHOR),
        _builds_meta_path_from(func, _WRITE_PRIMARY_ANCHOR),
    )


# ===========================================================================
# CALL-SHAPE arm scanner (coord-read-residuals FR-007 + gate-hardening FR-001/FR-008).
# ===========================================================================
#
# Flag a call ``read_func(dir, ...)`` (identity or lanes.json) whose first arg is a
# coord-aware ``dir`` WITHOUT a primary fold. FOUR first-arg shapes are detected:
#
#   * two-hop (FR-007): ``d = resolve_feature_dir_for_mission(...); read_func(d)`` —
#     ``d`` is a Name bound from a coord-aware resolver and NOT (re)bound from a
#     primary fold in the same function.
#   * inline-call (FR-007): ``read_func(resolve_feature_dir_for_mission(...))`` — the
#     coord-aware resolver call is the DIRECT first argument.
#   * one-hop parameter (FR-001, WP01 T003): the first arg is a function PARAMETER of
#     *func*; following exactly ONE hop to *func*'s caller(s) in the module, the
#     caller binds that arg from a coord-aware resolver WITHOUT a primary fold. This
#     is the ``_run_documentation_wiring`` ← ``setup_plan`` residual shape. Requires
#     the module-scoped ``module`` context AND the FR-001 widening of
#     ``_COORD_AWARE_CALLSHAPE_RESOLVERS``.
#   * attribute (FR-008, WP01 T002): the first arg is an ``ast.Attribute`` (e.g.
#     ``run.feature_dir``) whose member is NOT a sanctioned primary attribute. The
#     executor-shape escape (``read_func(run.feature_dir)``) the Name/Call branches
#     never saw (SC-006).
#
# The SANCTIONED shapes — a primary-fold-bound dir, a plain parameter whose caller
# binding is primary/seam-bound or non-coord-aware, and a sanctioned primary
# attribute (``.target_feature_dir``) — are NEVER flagged.


def _attr_repr(node: ast.Attribute) -> str:
    """Render ``<base>.<attr>`` for a simple attribute access (else just ``attr``)."""
    base = node.value
    if isinstance(base, ast.Name):
        return f"{base.id}.{node.attr}"
    return node.attr


def _param_position(
    func: ast.FunctionDef | ast.AsyncFunctionDef, name: str
) -> int | None:
    """Positional index of parameter *name* in *func*'s signature, or ``None``.

    Covers positional-only + ordinary positional params (the residual passes the
    dir positionally); keyword-only params have no positional index and return
    ``None`` — the one-hop check then conservatively does not fire.
    """
    ordered = [*func.args.posonlyargs, *func.args.args]
    for index, arg in enumerate(ordered):
        if arg.arg == name:
            return index
    return None


def _is_parameter(func: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    """True when *name* is any explicit parameter of *func*."""
    return any(
        arg.arg == name
        for arg in (
            *func.args.posonlyargs,
            *func.args.args,
            *func.args.kwonlyargs,
        )
    )


def _iter_module_functions(
    module: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function defined in *module* (module-scoped caller index source)."""
    return [
        node
        for node in ast.walk(module)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _caller_binds_arg_coord_aware(
    caller: ast.FunctionDef | ast.AsyncFunctionDef,
    callee_name: str,
    pos: int | None,
    param_name: str,
) -> bool:
    """True iff *caller* passes a coord-aware-without-fold dir to *callee_name*.

    The one-hop hop: the arg at positional index *pos* OR keyword *param_name* must
    be a Name bound (in the caller) from a coord-aware resolver and NOT also bound
    from a primary fold — the same coord-vs-primary divergence the two-hop shape
    catches, observed one frame up.
    """
    coord = _names_bound_from(caller, _COORD_AWARE_CALLSHAPE_RESOLVERS)
    primary = _names_bound_from(caller, _PRIMARY_FOLD_CALLSHAPE_FUNCS)
    for node in ast.walk(caller):
        if not isinstance(node, ast.Call) or _call_func_name(node) != callee_name:
            continue
        candidate_args: list[ast.expr] = []
        if pos is not None and pos < len(node.args):
            candidate_args.append(node.args[pos])
        candidate_args.extend(
            kw.value for kw in node.keywords if kw.arg == param_name
        )
        for arg in candidate_args:
            if isinstance(arg, ast.Name) and arg.id in coord and arg.id not in primary:
                return True
    return False


def _one_hop_caller_is_coord_aware(
    callee_func: ast.AST, param_name: str, module: ast.Module
) -> bool:
    """FR-001 one-hop: does any caller of *callee_func* bind *param_name* coord-aware?

    Exactly ONE hop — no transitive/multi-hop walk (C-006 defers that). Handles
    positional and keyword caller bindings; returns ``False`` when *param_name* is
    not an explicit parameter of *callee_func*.
    """
    if not isinstance(callee_func, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if not _is_parameter(callee_func, param_name):
        return False
    pos = _param_position(callee_func, param_name)
    callee_name = callee_func.name
    for caller in _iter_module_functions(module):
        if caller is callee_func:
            continue
        if _caller_binds_arg_coord_aware(caller, callee_name, pos, param_name):
            return True
    return False


def _flag_name_arg(
    callee: str,
    name: str,
    *,
    func: ast.AST,
    coord_bound: set[str],
    primary_bound: set[str],
    module: ast.Module | None,
) -> str | None:
    """Flag a Name first arg via the two-hop (local) OR one-hop (caller) shape."""
    # Two-hop: a locally coord-bound Name, not re-folded onto PRIMARY.
    if name in coord_bound and name not in primary_bound:
        return f"{callee}({name})"
    # One-hop (FR-001): a parameter whose caller binds it coord-aware-without-fold.
    # The existing same-function PARAM-exemption is retained for every other case.
    if module is not None and _one_hop_caller_is_coord_aware(func, name, module):
        return f"{callee}({name})"
    return None


def _flagged_first_arg(
    callee: str,
    first: ast.expr,
    *,
    func: ast.AST,
    coord_bound: set[str],
    primary_bound: set[str],
    module: ast.Module | None,
) -> str | None:
    """Descriptor for a flagged first arg, or ``None`` if it is sanctioned."""
    if isinstance(first, ast.Name):
        return _flag_name_arg(
            callee,
            first.id,
            func=func,
            coord_bound=coord_bound,
            primary_bound=primary_bound,
            module=module,
        )
    if isinstance(first, ast.Call):
        inner = _call_func_name(first)
        if inner is not None and inner in _COORD_AWARE_CALLSHAPE_RESOLVERS:
            return f"{callee}({inner}(...))"
        return None
    if isinstance(first, ast.Attribute):
        # FR-008: a coord-bearing attribute (the first arg of an identity/lanes read
        # IS a feature_dir by position) unless it is a sanctioned primary attribute.
        if first.attr not in _SANCTIONED_PRIMARY_ATTRS:
            return f"{callee}({_attr_repr(first)})"
        return None
    return None


def _read_call_first_arg(node: ast.Call) -> ast.expr | None:
    """Return a fenced read call's first path arg, positional or keyword."""
    if node.args:
        return node.args[0]
    for keyword in node.keywords:
        if keyword.arg in _READ_FIRST_ARG_KEYWORDS:
            return keyword.value
    return None


def callshape_violations(
    func: ast.AST,
    *,
    read_funcs: frozenset[str],
    module: ast.Module | None = None,
) -> list[str]:
    """Coord-aware identity/lanes.json reads inside *func* without a primary fold.

    ``read_funcs`` selects the shape: :data:`_IDENTITY_READ_FUNCS` (identity) or
    :data:`_LANES_READ_FUNCS` (lanes.json). Returns ``"<read_func>(<arg>)"``
    descriptors — one per flagged call.

    ``module`` is the OPTIONAL module-scoped caller index (FR-001, WP01 T003): the
    enclosing :class:`ast.Module` of *func*. When supplied, a kind-read whose first
    arg is a function PARAMETER of *func* is followed exactly ONE hop to its
    caller(s) — flagged iff a caller binds that arg from a coord-aware resolver
    WITHOUT a primary fold. When ``None`` (the legacy per-function call) the one-hop
    check is skipped; the two-hop, inline-call, and attribute shapes still apply.

    A call is flagged iff its first path arg (positional, or ``feature_dir=``) is
    one of:

    * a ``Name`` bound (same function) from a coord-aware resolver and NOT also
      bound from a primary-fold seam (two-hop); or
    * a direct ``Call`` to a coord-aware resolver (inline-call); or
    * a ``Name`` PARAMETER whose one-hop caller binds it coord-aware-without-fold
      (FR-001, only when ``module`` is supplied); or
    * an ``ast.Attribute`` whose member is not a sanctioned primary attribute
      (FR-008 — e.g. ``run.feature_dir``).

    NEVER flagged: a primary-fold-bound first arg; a plain parameter whose caller
    binding is primary/seam-bound or non-coord-aware; the sanctioned primary
    attribute ``.target_feature_dir``.
    """
    coord_bound = _names_bound_from(func, _COORD_AWARE_CALLSHAPE_RESOLVERS)
    primary_bound = _names_bound_from(func, _PRIMARY_FOLD_CALLSHAPE_FUNCS)

    violations: list[str] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        callee = _call_func_name(node)
        if callee is None or callee not in read_funcs:
            continue
        first = _read_call_first_arg(node)
        if first is None:
            continue
        descriptor = _flagged_first_arg(
            callee,
            first,
            func=func,
            coord_bound=coord_bound,
            primary_bound=primary_bound,
            module=module,
        )
        if descriptor is not None:
            violations.append(descriptor)
    return violations


# ===========================================================================
# (1) READ arm — the enumerated gate surfaces are clean on the real tree.
# ===========================================================================


def test_read_arm_gate_surfaces_route_through_seam() -> None:
    """No enumerated gate entry function joins a planning artifact onto a
    topology-routed dir. All planning reads flow through the kind-aware seam.

    A violation here means a gate command reads ``coord/<artifact>.md`` (absent
    since #2106) instead of the PRIMARY surface — the #2107 driver-bug shape and a
    C-005 regression. Route the read through ``_planning_read_dir`` /
    ``resolve_planning_read_dir`` (PRIMARY-partition → primary dir for ALL
    topologies); keep STATUS/lifecycle uses of the coord-aware dir unchanged.
    """
    offenders: dict[str, list[str]] = {}
    for surface in _READ_ARM_SURFACES:
        tree = _module_tree(surface.rel_path)
        func = _find_function(tree, surface.func)
        assert func is not None, (
            f"Pinned READ surface {surface.rel_path}::{surface.func} not found — "
            "the enumerated surface set has drifted from the code (update "
            "_READ_ARM_SURFACES)."
        )
        hits = read_arm_violations(func)
        if hits:
            offenders[f"{surface.rel_path}::{surface.func}"] = hits

    assert not offenders, (
        "Topology-routed planning-artifact join(s) in gate entry function(s): "
        f"{dict(sorted(offenders.items()))}. The named base dir is bound from a "
        "coord-aware resolver (_find_feature_directory / resolve_handle_to_read_path "
        "/ resolve_feature_dir_for_mission) and joined with a planning artifact — "
        "under coordination topology this reads the coord worktree (no spec.md since "
        "#2106). Resolve the read dir via the kind-aware seam "
        "(_planning_read_dir / resolve_planning_read_dir, kind=<artifact>) — PRIMARY "
        "for all topologies (FR-004 / FR-009 / C-005). Keep STATUS uses of the "
        "coord-aware dir unchanged (C-002)."
    )


# ===========================================================================
# (2) WRITE arm (G-6) — the enumerated write-branch resolvers anchor PRIMARY.
# ===========================================================================


def test_write_arm_resolvers_anchor_meta_on_primary() -> None:
    """No write-branch resolver reads ``target_branch`` from a ``meta.json``
    anchored on the coord-aware candidate dir; all anchor on the PRIMARY surface.

    A violation here means the planning-artifact COMMIT/branch resolves to the
    protected repo primary ``main`` under coordination topology (the candidate
    selects coord, whose dir has no ``meta.json``, falling back to ``main``) —
    the finalize-tasks / implement-loop refusal-to-main bug (FR-004 / FR-009(e)).
    Anchor the ``meta.json`` read on ``primary_feature_dir_for_mission``, mirroring
    ``resolve_merge_target_branch``.
    """
    offenders: list[str] = []
    for surface in _WRITE_ARM_SURFACES:
        tree = _module_tree(surface.rel_path)
        func = _find_function(tree, surface.func)
        assert func is not None, (
            f"Pinned WRITE surface {surface.rel_path}::{surface.func} not found — "
            "the enumerated resolver set has drifted from the code (update "
            "_WRITE_ARM_SURFACES)."
        )
        reads_via_candidate, _reads_via_primary = write_arm_anchors(func)
        if reads_via_candidate:
            offenders.append(f"{surface.rel_path}::{surface.func}")

    assert not offenders, (
        "Write-branch resolver(s) read meta.json anchored on the coord-aware "
        f"candidate dir: {sorted(offenders)}. Under coordination topology the "
        "candidate selects the coordination worktree, whose mission dir has no "
        "meta.json — the read finds nothing and silently falls back to the "
        "protected repo primary 'main', so the commit/branch resolves to 'main' "
        "instead of the mission's target_branch (FR-004 / FR-009(e) / G-6). Anchor "
        "the meta.json read on primary_feature_dir_for_mission, mirroring "
        "resolve_merge_target_branch (core/paths.py)."
    )


# ===========================================================================
# (3) Pin test — the enumerated surface set matches the live command surface.
# ===========================================================================
#
# A new gate command (read) or write-branch resolver added to the code WITHOUT
# adding it to the pinned surface set would be silently un-scanned — a vacuous
# ratchet. We anchor the pin to the @app.command-decorated entry functions of the
# two CLI modules (the gate command surface) plus the two known write resolvers,
# and assert each pinned surface still exists. (We do not auto-derive the full
# scan set from @app.command — not every command reads a planning artifact — but
# we DO assert that the pinned functions are real, so a rename/removal that would
# silently empty the scan FAILS here.)


def test_enumerated_surface_set_is_pinned_and_live() -> None:
    """Every pinned read/write surface resolves to a real function.

    A drift (rename, move, deletion) empties part of the scan silently; pinning
    each surface to a live function turns that drift into a hard failure, so the
    ratchet cannot decay into vacuity (T024.3).
    """
    missing: list[str] = []
    for surface in (*_READ_ARM_SURFACES, *_WRITE_ARM_SURFACES):
        tree = _module_tree(surface.rel_path)
        if _find_function(tree, surface.func) is None:
            missing.append(f"{surface.rel_path}::{surface.func}")
    assert not missing, (
        f"Pinned ratchet surface(s) no longer exist: {sorted(missing)}. If a gate "
        "command or write-branch resolver was renamed/moved, update _READ_ARM_SURFACES "
        "/ _WRITE_ARM_SURFACES to match — a silently un-scanned surface is a vacuous "
        "ratchet (FR-010)."
    )


# ===========================================================================
# (3b) READ arm — DEFAULT-DENY discovery over the whole command surface.
# ===========================================================================
#
# The manual ``_READ_ARM_SURFACES`` denylist undersized the planning-lifecycle
# command set THREE times in a row (map-requirements, finalize-tasks-commit, now
# ``research`` — paula closeout). A new/un-listed command that joins a planning
# literal off a topology-routed dir silently bypasses the pinned scan. This
# coverage-derived (default-deny) scan closes that hole: it walks EVERY function in
# the two CLI command packages and flags ANY topology-routed planning-artifact join
# — no hand-enumeration required. The enumerated set above keeps its per-surface
# contract citations and its pin/non-vacuity guarantees; this is the safety net for
# a command nobody remembered to list.
#
# Precision (no false positives): the scanner flags ONLY a ``_PLANNING_ARTIFACT_LITERALS``
# basename joined off a name bound from a TOPOLOGY-ROUTED resolver. A legitimate
# STATUS join (``status_feature_dir / "status.events.jsonl"``,
# ``.../acceptance-matrix.json``) is neither a planning literal nor bound from a
# topology-routed resolver in this set, so it never trips. A bare-dir / non-literal
# join (``feature_dir / "tasks"``) is not a ``.md`` planning literal, so it is
# likewise clean. Verified empirically: zero hits on the post-fix tree.

# The ``.md`` literal default-deny scan walks the CLI command packages
# (``cli/commands/`` — the ``agent`` sub-typer + top-level commands).
_COMMAND_PACKAGE_DIRS: tuple[Path, ...] = (
    _SRC_ROOT / "specify_cli" / "cli" / "commands",
)

# The accept-gate package the closeout N+1 lived in (debbie §3). The bare-dir
# default-deny arm scans HERE — ``_iter_work_packages`` did ``feature_path / "tasks"``
# off the coord-aware resolver and the encoding normalizer scanned the husk's
# ``tasks/research/checklists`` subtrees. The CLI command packages are deliberately
# NOT in this dir-read scope: the implement/review/merge surface carries WP-task
# ``tasks/`` reads off coord-aware resolvers that belong to a SEPARATE implement-loop
# write-surface mission (named, not hidden, in ``_DIR_READ_KNOWN_RESIDUALS``).
_ACCEPT_PACKAGE_DIRS: tuple[Path, ...] = (
    _SRC_ROOT / "specify_cli" / "acceptance",
)

# T005 (WP02): widened scope for the dir-read residual-pin test.  Covers all of
# ``src/specify_cli/`` so the N+7 residuals outside ``cli/commands/`` are surfaced
# and tracked (``workspace/context.py``, ``task_utils/``, ``agent_utils/``,
# ``scripts/tasks/``).  The accept-gate package (``acceptance/``) is included here
# but is verified clean by its own default-deny test
# (``test_dir_read_arm_default_deny_accept_package_clean``).
_WHOLE_SRC_SCAN_DIRS: tuple[Path, ...] = (
    _SRC_ROOT / "specify_cli",
)


def _iter_functions_under(
    pkg_dirs: tuple[Path, ...],
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Every ``(rel_path, function)`` defined under *pkg_dirs*.

    Recurses into ``agent/`` and other subpackages. ``__pycache__`` is skipped.
    """
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for pkg in pkg_dirs:
        for py in sorted(pkg.rglob("*.py")):
            if "__pycache__" in py.parts:
                continue
            rel = _rel(py)
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found.append((rel, node))
    return found


def test_read_arm_default_deny_no_unlisted_topology_join() -> None:
    """DEFAULT-DENY (``.md`` arm): NO function in the CLI command packages joins a
    planning ``.md`` artifact onto a topology-routed dir — not just the enumerated set.

    This is coverage-derived: it discovers the scan set from the command packages
    rather than a hand-maintained denylist, so a NEW planning-lifecycle command
    that re-reads ``coord/<artifact>.md`` (the recurring #2107 N+1) FAILS here even
    if its author forgot to add it to ``_READ_ARM_SURFACES``. Route the read through
    the kind-aware seam (``_planning_read_dir`` / ``resolve_planning_read_dir``,
    PRIMARY for all topologies); keep STATUS/coord-aware dirs for status reads only.
    """
    offenders: dict[str, list[str]] = {}
    for rel_path, func in _iter_functions_under(_COMMAND_PACKAGE_DIRS):
        hits = read_arm_md_violations(func)
        if hits:
            offenders[f"{rel_path}::{func.name}"] = hits

    assert not offenders, (
        "Topology-routed planning-artifact join(s) discovered in CLI command "
        f"function(s): {dict(sorted(offenders.items()))}. A planning read is bound "
        "from a coord-aware resolver (_find_feature_directory / "
        "resolve_handle_to_read_path / resolve_feature_dir_for_mission / "
        "resolve_feature_dir_for_slug / candidate_feature_dir_for_mission) and joined "
        "with a planning artifact — under coordination topology this reads the coord "
        "worktree (no spec.md/plan.md since #2106). Resolve the read dir via the "
        "kind-aware seam (_planning_read_dir / resolve_planning_read_dir, "
        "kind=<artifact>) — PRIMARY for all topologies (FR-004 / FR-009 / C-005). "
        "Keep STATUS uses of the coord-aware dir unchanged (C-002)."
    )


# ---------------------------------------------------------------------------
# (3c) DIR-READ default-deny over the accept-gate package + named-residual pin.
# ---------------------------------------------------------------------------
#
# The closeout N+1 (debbie §3) was a BARE-DIR ``tasks/`` read off a coord-aware
# resolver in ``acceptance/`` — invisible to the ``.md`` arm above. This scan fences
# the WORK_PACKAGE_TASK / RESEARCH / CHECKLIST bare-dir reads on the accept-gate
# surface. After the closeout fix (``_iter_work_packages`` → ``_wp_tasks_read_dir``;
# the encoding normalizer → ``_planning_read_dir``) the accept package is clean.
#
# The broadened dir-read arm ALSO surfaced an N+2 cluster OUTSIDE this mission's
# scope — the implement/review/merge command surface reads WP ``tasks/`` off
# coord-aware resolvers (``workflow.py::implement`` / ``review`` /
# ``_resolve_review_context`` / ``_preview_claimable_wp_for_mission``,
# ``tasks.py::status`` / ``finalize_tasks``, ``merge.py::_mark_wp_merged_done``).
# Those belong to a SEPARATE implement-loop write-surface mission (the #1716
# cluster) and are NAMED here (not silently fixed) so the residual is tracked, not
# hidden — fixing them in THIS behavior-neutral accept-gate closeout would breach
# locality (DIRECTIVE_024).


def test_dir_read_arm_default_deny_accept_package_clean() -> None:
    """DEFAULT-DENY (dir arm): NO function in ``acceptance/`` joins a PRIMARY-partition
    subdir (``tasks`` / ``research`` / ``checklists``) onto a topology-routed dir.

    The closeout N+1 fence: a WORK_PACKAGE_TASK ``tasks/`` read off the coord-aware
    resolver lands on the materialized ``-coord`` husk (no ``tasks/`` dir) and breaks
    the accept gate. Route bare-dir PRIMARY-partition reads through the kind-aware
    seam (``_wp_tasks_read_dir`` / ``_planning_read_dir`` / ``resolve_planning_read_dir``).
    """
    offenders: dict[str, list[str]] = {}
    for rel_path, func in _iter_functions_under(_ACCEPT_PACKAGE_DIRS):
        hits = read_arm_violations(func)
        if hits:
            offenders[f"{rel_path}::{func.name}"] = hits

    assert not offenders, (
        "Topology-routed PRIMARY-partition subdir read(s) in the accept-gate "
        f"package: {dict(sorted(offenders.items()))}. A bare-dir ``tasks/`` / "
        "``research/`` / ``checklists/`` read is bound from a coord-aware resolver "
        "and lands on the -coord husk under coordination topology (closeout N+1, "
        "debbie §3). Route it through the kind-aware seam (_wp_tasks_read_dir / "
        "_planning_read_dir / resolve_planning_read_dir, kind=WORK_PACKAGE_TASK) — "
        "PRIMARY for all topologies. Keep STATUS reads off status_feature_dir (C-002)."
    )


# The implement/review/merge WP-task bare-dir reads the broadened arm surfaced —
# the N+2 cluster OUTSIDE this accept-gate closeout. NAMED so the residual is
# tracked (debbie step 5: "don't silently fix-and-hide"); fenced by a SEPARATE
# implement-loop write-surface mission (the #1716 cluster). The pin below asserts
# this is exactly the set the scan finds, so neither a NEW implement-loop dir-read
# (set grows → FAIL) nor a silent fix (set shrinks → FAIL, prompting removal here)
# slips by unobserved.
# T008 (WP02) — post-widening baseline census:
#   Scope: all of src/specify_cli/ (T005), scanner: two-hop + T004 inline-call,
#   C-008 sub-path exclusion applied (workflow.py::implement / ::review /
#   review/cycle.py::resolve_review_cycle_pointer / ::create_rejected_review_cycle
#   all suppressed — their tasks/ reads are chained sub-artifact paths).
#   Total pinned: 12 (10 category-a in-loop + 2 category-b out-of-scope + 0 category-c).
#   Shrink-only baseline: each WP03–WP06 route removes its entry;
#   any new unrouted site in src/specify_cli/ that the scanner can SEE (a bare
#   `resolver(...) / "<dir|.md>"` two-hop or inline join) FAILS the test (NFR-001).
#   COVERAGE LIMIT (reviewer-renata): this ratchet's vocabulary is dir/.md literals
#   (`_PLANNING_DIR_LITERALS`/`_PLANNING_ARTIFACT_LITERALS`). It does NOT include
#   `lanes.json` (LANE_STATE) — so the in-scope `lanes.json` reads WP05 routes
#   (workspace/context.py) and the out-of-scope merge/+lanes/ cluster (#2185) are
#   NOT gated here; they are covered only by the WP01 coord-topology fixture tests.
_DIR_READ_KNOWN_RESIDUALS: frozenset[str] = frozenset(
    {
        # -------------------------------------------------------------------
        # Category (a): IN-LOOP — ALL ROUTED (WP03–WP06 complete).
        # tasks.py::finalize_tasks, ::list_tasks, ::status were ROUTED by WP03.
        # workflow.py::_find_first_for_review_wp, ::_preview_claimable_wp_for_mission,
        # ::_resolve_review_context were ROUTED by WP04 (FR-002/FR-009).
        # task_utils/support.py::locate_work_package,
        # workspace/context.py::build_normalized_wp_index,
        # workspace/context.py::get_normalized_wp,
        # workspace/context.py::resolve_active_wp_for_branch were ROUTED by WP05
        # (FR-005/FR-009) — removed from this set.
        # tasks_dependency_graph.py::_check_dependent_warnings,
        # tasks_parsing_validation.py::_validate_ready_for_review,
        # validate_tasks.py::validate_tasks_cmd were ROUTED by WP06 (FR-004/FR-006/
        # FR-009).  These three sites were gate-blind (the tasks/ join lives inside
        # helper functions, not at the resolver call site), so no pins were ever added;
        # routing closes the coord-topology defect — zero in-loop residuals remain.
        # -------------------------------------------------------------------
        # Category (b): OUT-OF-SCOPE — pinned with tracking-issue reference;
        # no silent skip.  These are PRIMARY-partition tasks/ reads outside the
        # implement loop or in modules outside this mission's C-009 boundary.
        # -------------------------------------------------------------------
        # DRAINED (#2187, coord-read-residuals WP03): show_kanban_status now routes
        # its ``tasks/`` glob through the kind-aware seam (kind=WORK_PACKAGE_TASK),
        # reading off PRIMARY — so the read-arm no longer flags it. Removed from the
        # set per FR-008 (the sole ratchet-visible Lane A drain; set shrinks by one).
        # -------------------------------------------------------------------
        # Category (c): C-008 PERMANENT-COORD — none.
        # T006 sub-path exclusion fully suppresses workflow.py::implement /
        # ::review and review/cycle.py::resolve_review_cycle_pointer /
        # ::create_rejected_review_cycle at function granularity: all their
        # tasks/ reads are chained (``/ wp_slug / …`` sub-artifact paths) and
        # are excluded by the chained-BinOp gate.  No permanent-coord pins needed.
        # -------------------------------------------------------------------
    }
)


def test_dir_read_arm_known_residuals_are_pinned() -> None:
    """The implement-loop WP-task dir-read residuals match the named set exactly.

    Observability ratchet for the full src/specify_cli/ residual surface (T005,
    WP02): the widened dir-read arm walks ALL of ``src/specify_cli/`` (not just
    ``cli/commands/``) so residuals outside the command package are also surfaced
    and pinned.  Pinning the exact set means:
    - A NEWLY-introduced dir-read off a coord-aware resolver (set grows) FAILS here
      — it cannot hide behind the known cluster.
    - A fix in a follow-up WP (set shrinks) ALSO fails, prompting its removal from
      ``_DIR_READ_KNOWN_RESIDUALS`` so the ratchet stays tight.
    The accept-gate package is fenced separately and stays clean
    (``test_dir_read_arm_default_deny_accept_package_clean``).
    """
    found: dict[str, list[str]] = {}
    for rel_path, func in _iter_functions_under(_WHOLE_SRC_SCAN_DIRS):
        hits = read_arm_violations(func)
        if hits:
            found[f"{rel_path}::{func.name}"] = hits

    flagged = set(found)
    unexpected_new = flagged - _DIR_READ_KNOWN_RESIDUALS
    resolved = _DIR_READ_KNOWN_RESIDUALS - flagged
    assert not unexpected_new, (
        "NEW implement-loop WP-task dir-read off a coord-aware resolver (not in the "
        f"known residual set): {sorted(unexpected_new)} (hits: "
        f"{ {k: found[k] for k in sorted(unexpected_new)} }). Route it through the "
        "kind-aware seam, OR — if it is genuinely a tracked residual of the "
        "implement-loop write-surface mission — add it to _DIR_READ_KNOWN_RESIDUALS "
        "with a tracker reference."
    )
    assert not resolved, (
        "A pinned dir-read residual is no longer flagged (it was fixed): "
        f"{sorted(resolved)}. Remove it from _DIR_READ_KNOWN_RESIDUALS so the pin "
        "stays tight (a stale residual entry rots the ratchet)."
    )


# ===========================================================================
# (4) MANDATORY synthetic-AST self-test — non-vacuity is a runnable assertion.
# ===========================================================================
#
# DIRECTIVE_041: a recorded manual mutation log rots and cannot be re-run. The
# scanners above are exercised here against synthetic snippets so the ratchet
# proves — every run — that it FLAGS a violation and PASSES clean code, for BOTH
# arms. If a future edit accidentally neuters a scanner (e.g. inverts a check),
# these self-tests go RED.


def _func_from_source(src: str, name: str = "f") -> ast.AST:
    func = _find_function(ast.parse(src), name)
    assert func is not None
    return func


def _module_and_func(src: str, name: str) -> tuple[ast.Module, ast.AST]:
    """Parse *src* and return ``(module, function)`` for the module-scoped harness.

    The one-hop FR-001 check needs the enclosing :class:`ast.Module` as the caller
    index, so the cross-function self-tests parse the whole module and hand both the
    callee function and its module to :func:`callshape_violations`.
    """
    module = ast.parse(src)
    func = _find_function(module, name)
    assert func is not None
    return module, func


def _offending_call_lineno(func: ast.AST, callee_name: str) -> int:
    """1-based lineno of the first call to *callee_name* inside *func*.

    Used to CONTENT-ANCHOR a self-mutation test via ``composite_key`` (CT7 / NFR-001)
    instead of a brittle ``file.py:NNN`` key.
    """
    for node in ast.walk(func):
        if isinstance(node, ast.Call) and _call_func_name(node) == callee_name:
            return node.lineno
    raise AssertionError(f"no call to {callee_name!r} found in the snippet")


# ---- READ arm self-test: violating snippets FLAGGED, clean snippet PASSES ----

_READ_VIOLATION_DIRECT_JOIN = '''
def f(repo_root, cwd, feature):
    feature_dir = _find_feature_directory(repo_root, cwd, explicit_feature=feature)
    spec_file = feature_dir / "spec.md"
    return spec_file
'''

_READ_VIOLATION_TOPOLOGY_RESOLVER = '''
def f(repo_root, feature):
    read_dir = resolve_feature_dir_for_mission(repo_root, feature)
    plan_file = read_dir / "plan.md"
    return plan_file
'''

_READ_CLEAN_VIA_SEAM = '''
def f(repo_root, mission_slug):
    spec_read_dir = _planning_read_dir(repo_root, mission_slug, artifact_type="spec")
    spec_file = spec_read_dir / "spec.md"
    # A coord-aware dir bound for STATUS only — never joined with a planning
    # artifact — must NOT trip the scan.
    feature_dir = _find_feature_directory(repo_root, mission_slug)
    status_dir = feature_dir / "status.events.jsonl"
    return spec_file, status_dir
'''


def test_read_arm_self_test_flags_direct_topology_join() -> None:
    """A ``feature_dir = _find_feature_directory(...); feature_dir / 'spec.md'``
    snippet is FLAGGED (the #2107 driver shape)."""
    hits = read_arm_violations(_func_from_source(_READ_VIOLATION_DIRECT_JOIN))
    assert hits == ["feature_dir / spec.md"], hits


def test_read_arm_self_test_flags_topology_resolver_read() -> None:
    """A read dir bound from ``resolve_feature_dir_for_mission`` then joined with a
    planning artifact is FLAGGED."""
    hits = read_arm_violations(_func_from_source(_READ_VIOLATION_TOPOLOGY_RESOLVER))
    assert hits == ["read_dir / plan.md"], hits


def test_read_arm_self_test_passes_clean_seam_read() -> None:
    """A seam-derived planning read PASSES, and a coord-aware dir used purely for a
    STATUS join is NOT flagged (precision: no false-positive on status paths)."""
    hits = read_arm_violations(_func_from_source(_READ_CLEAN_VIA_SEAM))
    assert hits == [], hits


# A synthetic command in the ``research`` defect shape: it binds its dir from
# ``resolve_feature_dir_for_slug`` (the coord-aware resolver the manual denylist
# missed) and validates ``plan.md``. This is exactly the un-listed-command hole the
# default-deny scan exists to close: the scanner flags it WITHOUT the function being
# in ``_READ_ARM_SURFACES``.
_READ_VIOLATION_UNLISTED_SLUG_RESOLVER = '''
def some_brand_new_gate_command(repo_root, mission_slug):
    feature_dir = resolve_feature_dir_for_slug(repo_root, mission_slug)
    plan_path = feature_dir / "plan.md"
    return plan_path
'''


def test_read_arm_default_deny_flags_unlisted_slug_resolver_command() -> None:
    """DEFAULT-DENY non-vacuity: a NEW command joining a planning literal off
    ``resolve_feature_dir_for_slug`` is FLAGGED even though it is NOT enumerated in
    ``_READ_ARM_SURFACES``.

    This is the exact #2107 residual shape (``research`` pre-fix). It proves the
    default-deny discovery + the broadened topology-resolver set catch a command the
    manual denylist would have silently skipped — the recurring N+1 is now fenced at
    the shape, not the name.
    """
    func = _func_from_source(
        _READ_VIOLATION_UNLISTED_SLUG_RESOLVER, name="some_brand_new_gate_command"
    )
    hits = read_arm_violations(func)
    assert hits == ["feature_dir / plan.md"], hits


# A synthetic snippet in the closeout-N+1 shape: a bare ``tasks/`` dir read off the
# coord-aware ``resolve_feature_dir_for_mission`` (the exact ``_iter_work_packages``
# pre-fix shape). The ``.md`` literal arm never saw this — it is a BARE-DIR read — so
# the dir-read arm is what fences it.
_READ_VIOLATION_BARE_TASKS_DIR = '''
def f(repo_root, feature):
    feature_path = resolve_feature_dir_for_mission(repo_root, feature)
    tasks_dir = feature_path / "tasks"
    return tasks_dir
'''

# A clean snippet: the WP-task dir read routed through the kind-aware seam (PRIMARY),
# AND a STATUS dir read off ``status_feature_dir`` (bound from the NON-topology-routed
# ``_status_read_feature_dir``) — neither must trip, proving precision.
_READ_CLEAN_WP_TASKS_VIA_SEAM = '''
def f(repo_root, feature):
    wp_read_dir = resolve_planning_read_dir(repo_root, feature, kind="WORK_PACKAGE_TASK")
    tasks_dir = wp_read_dir / "tasks"
    status_feature_dir = _status_read_feature_dir(repo_root, feature, primary)
    status_tasks = status_feature_dir / "tasks"
    return tasks_dir, status_tasks
'''


def test_read_arm_self_test_flags_bare_tasks_dir_topology_join() -> None:
    """Closeout N+1 non-vacuity: a bare ``feature_path / 'tasks'`` read off the
    coord-aware resolver is FLAGGED (the ``_iter_work_packages`` pre-fix shape).

    This is the dir-read arm the ``.md`` literal scanner could not see. Proves the
    broadened ratchet would have caught the accept-gate WP-task N+1.
    """
    hits = read_arm_violations(_func_from_source(_READ_VIOLATION_BARE_TASKS_DIR))
    assert hits == ["feature_path / tasks"], hits


def test_read_arm_self_test_passes_clean_wp_tasks_seam_and_status_dir() -> None:
    """Precision: a seam-derived WP-task dir read PASSES, and a ``tasks`` dir read
    off ``status_feature_dir`` (NON-topology-routed binding) is NOT flagged.

    Guards against the dir-read arm false-positiving on legitimate STATUS dir reads.
    """
    hits = read_arm_violations(_func_from_source(_READ_CLEAN_WP_TASKS_VIA_SEAM))
    assert hits == [], hits


# ---- T004 inline-call shape + C-008 sub-path exclusion self-tests (WP02 T006) ----
#
# Pre-T004 reasoning (the RED the inline arm closes):
# ``read_arm_violations`` on ``_DIR_READ_VIOLATION_INLINE_CALL`` returned ``[]``
# because the scanner only inspected the left operand for ``ast.Name`` and the
# name ``candidate_feature_dir_for_mission`` is a Call, not a Name.  With T004
# the Call left-operand is matched directly against ``_TOPOLOGY_ROUTED_READ_RESOLVERS``.

# T004: inline-call shape — resolver call is the DIRECT left operand of / "tasks".
# This is the ``_find_first_for_review_wp`` / ``list_tasks`` shape (research.md).
_DIR_READ_VIOLATION_INLINE_CALL = """
def f(repo_root, mission_slug):
    tasks_dir = candidate_feature_dir_for_mission(repo_root, mission_slug) / "tasks"
    return sorted(tasks_dir.glob("WP*.md"))
"""

# Routed shape: dir derived from the sanctioned seam (resolve_planning_read_dir),
# not from a coord-aware resolver.  Must NOT be flagged (precision guard).
_DIR_READ_CLEAN_INLINE_ROUTED = """
def f(repo_root, mission_slug):
    read_dir = resolve_planning_read_dir(repo_root, mission_slug, kind="WORK_PACKAGE_TASK")
    tasks_dir = read_dir / "tasks"
    return sorted(tasks_dir.glob("WP*.md"))
"""

# C-008 sub-path exclusion: the resolver call IS on the left of "tasks", but
# "tasks" is immediately chained into a longer path (/ wp_slug).  This is the
# review-cycle sub-artifact shape (``implement`` / ``review`` / ``review/cycle.py``);
# the scanner must NOT flag it even though the inline-call resolver matches.
_DIR_READ_CLEAN_C008_SUBPATH = """
def f(repo_root, mission_slug, wp_slug):
    sub_artifact_dir = (
        candidate_feature_dir_for_mission(repo_root, mission_slug) / "tasks" / wp_slug
    )
    return sub_artifact_dir
"""


def test_dir_read_arm_self_test_flags_inline_call_shape() -> None:
    """T004 non-vacuity: ``resolver(...) / 'tasks'`` (inline-call) is FLAGGED.

    Without the T004 arm this snippet returned zero hits, even though the defect
    shape is the same coord-vs-primary divergence as the two-hop form at runtime.
    This self-test fails (RED) when T004 is absent and passes (GREEN) when it is
    present, proving the arm is load-bearing.
    """
    hits = read_arm_violations(_func_from_source(_DIR_READ_VIOLATION_INLINE_CALL))
    assert hits == ["candidate_feature_dir_for_mission(...) / tasks"], hits


def test_dir_read_arm_self_test_passes_routed_inline_seam() -> None:
    """Precision: ``resolve_planning_read_dir(...) / 'tasks'`` is NOT flagged.

    The dir is derived from the sanctioned seam (not a coord-aware resolver), so
    the T004 inline-call arm must not false-positive on it.
    """
    hits = read_arm_violations(_func_from_source(_DIR_READ_CLEAN_INLINE_ROUTED))
    assert hits == [], hits


def test_dir_read_arm_self_test_c008_subpath_not_flagged() -> None:
    """C-008 exclusion: ``resolver(...) / 'tasks' / wp_slug`` is NOT flagged.

    The inner ``resolver(...) / 'tasks'`` BinOp is the left operand of a further
    ``/ wp_slug`` chain, so its id is in ``chained_binop_ids`` and is excluded.
    This is the review-cycle sub-artifact shape — ``implement`` / ``review`` /
    ``review/cycle.py`` all use it and legitimately stay coordination-aware (C-008
    matched read/write pair).  Flagging it would force false positives on those
    functions even after their PRIMARY planning-read leg is routed by WP03–WP06.
    """
    hits = read_arm_violations(_func_from_source(_DIR_READ_CLEAN_C008_SUBPATH))
    assert hits == [], hits


# ---- WRITE arm self-test: violating snippet FLAGGED, clean snippet PASSES ----

_WRITE_VIOLATION_CANDIDATE_ANCHOR = '''
def f(repo_root, mission_slug):
    meta_file = candidate_feature_dir_for_mission(repo_root, mission_slug) / "meta.json"
    if meta_file.exists():
        return read_target_branch(meta_file)
    return "main"
'''

_WRITE_CLEAN_PRIMARY_ANCHOR = '''
def f(repo_root, mission_slug):
    main_root = get_main_repo_root(repo_root)
    meta_file = primary_feature_dir_for_mission(main_root, mission_slug) / "meta.json"
    if meta_file.exists():
        return read_target_branch(meta_file)
    return "main"
'''


def test_write_arm_self_test_flags_candidate_meta_anchor() -> None:
    """A ``meta.json`` read anchored on ``candidate_feature_dir_for_mission`` is
    FLAGGED (the G-6 fallback-to-main bug shape)."""
    reads_via_candidate, _ = write_arm_anchors(
        _func_from_source(_WRITE_VIOLATION_CANDIDATE_ANCHOR)
    )
    assert reads_via_candidate is True


def test_write_arm_self_test_passes_primary_meta_anchor() -> None:
    """A ``meta.json`` read anchored on ``primary_feature_dir_for_mission`` PASSES
    (the sanctioned ``resolve_merge_target_branch`` shape)."""
    reads_via_candidate, reads_via_primary = write_arm_anchors(
        _func_from_source(_WRITE_CLEAN_PRIMARY_ANCHOR)
    )
    assert reads_via_candidate is False
    assert reads_via_primary is True


# ===========================================================================
# (5) CALL-SHAPE arm self-tests (coord-read-residuals FR-007, WP01 T003).
# ===========================================================================
#
# MANDATORY synthetic-AST non-vacuity proof for BOTH shapes (identity + lanes.json),
# in BOTH binding forms (two-hop + inline-call). The literal path-join scanners are
# structurally blind to these function-call reads, so this arm is the only detector
# for the coord-vs-primary divergence in identity/lanes.json reads. These self-tests
# prove — every run — that the arm FLAGS the pre-fix shape and PASSES the routed
# shape, so a future edit that neuters ``callshape_violations`` goes RED here
# (DIRECTIVE_041: the teeth are an automated regression, not a manual ritual).

# ---- IDENTITY shape (resolve_mission_identity / get_mission_type) ----

# Two-hop violation: dir bound from a coord-aware resolver, then identity-read.
# This is the pre-fix ``next_cmd._write_issuance_lifecycle_record`` shape.
_IDENTITY_VIOLATION_TWO_HOP = '''
def f(repo_root, mission_slug):
    feature_dir = resolve_feature_dir_for_mission(repo_root, mission_slug)
    identity = resolve_mission_identity(feature_dir)
    return identity.mission_id
'''

# Inline-call violation: the coord-aware resolver call is the direct argument.
# This is the pre-fix ``workflow.py:2739`` shape.
_IDENTITY_VIOLATION_INLINE = '''
def f(main_repo_root, mission_slug):
    return resolve_mission_identity(
        resolve_feature_dir_for_mission(main_repo_root, mission_slug)
    ).mission_id
'''

# Routed (clean): the dir is built by the PRIMARY fold seam. Must NOT be flagged.
# This is the post-fix shape for every routed identity site.
_IDENTITY_CLEAN_PRIMARY_FOLD = '''
def f(repo_root, mission_slug):
    primary_dir = primary_feature_dir_for_mission(
        repo_root, _canonicalize_primary_read_handle(repo_root, mission_slug)
    )
    mission_type = get_mission_type(primary_dir)
    return mission_type
'''

# Precision guard (re-pinned for FR-001 — WP01 T004): a plain parameter
# ``feature_dir`` whose ONE-HOP caller has NO coord-aware binding (it forwards a dir
# it itself received as a parameter) is NOT the divergence shape — the caller did
# not resolve it coord-aware. Must NOT be flagged EVEN under the module-scoped
# one-hop harness (else every helper that ACCEPTS a feature_dir would red-CI). This
# stays consistent with FR-001 (which flags ONLY a param whose caller binding IS
# coord-aware-without-fold — see ``_VIOLATION_CROSS_FUNCTION``), not contradictory.
_IDENTITY_CLEAN_PARAMETER_DIR = '''
def caller(feature_dir, repo_root):
    # No coord-aware binding here: the caller forwards a dir it received as a
    # parameter, so the one-hop check must NOT flag the callee's parameter read.
    return _read_identity(feature_dir, repo_root)

def _read_identity(feature_dir, repo_root):
    identity = resolve_mission_identity(feature_dir)
    return identity.mission_id
'''


def test_callshape_arm_identity_flags_two_hop() -> None:
    """IDENTITY two-hop: ``d = resolve_feature_dir_for_mission(...); resolve_mission_identity(d)``
    is FLAGGED (the pre-fix lifecycle-record shape)."""
    hits = callshape_violations(
        _func_from_source(_IDENTITY_VIOLATION_TWO_HOP), read_funcs=_IDENTITY_READ_FUNCS
    )
    assert hits == ["resolve_mission_identity(feature_dir)"], hits


def test_callshape_arm_identity_flags_keyword_two_hop() -> None:
    """IDENTITY two-hop cannot be bypassed by ``feature_dir=`` keyword style."""
    source = '''
def f(repo_root, mission_slug):
    feature_dir = resolve_feature_dir_for_mission(repo_root, mission_slug)
    identity = resolve_mission_identity(feature_dir=feature_dir)
    return identity.mission_id
'''
    hits = callshape_violations(
        _func_from_source(source), read_funcs=_IDENTITY_READ_FUNCS
    )
    assert hits == ["resolve_mission_identity(feature_dir)"], hits


def test_callshape_arm_identity_flags_inline_call() -> None:
    """IDENTITY inline-call: ``resolve_mission_identity(resolve_feature_dir_for_mission(...))``
    is FLAGGED (the pre-fix ``workflow.py:2739`` shape)."""
    hits = callshape_violations(
        _func_from_source(_IDENTITY_VIOLATION_INLINE), read_funcs=_IDENTITY_READ_FUNCS
    )
    assert hits == ["resolve_mission_identity(resolve_feature_dir_for_mission(...))"], hits


def test_callshape_arm_identity_passes_primary_fold() -> None:
    """Precision: an identity read off ``primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))``
    is NOT flagged (the sanctioned routed shape)."""
    hits = callshape_violations(
        _func_from_source(_IDENTITY_CLEAN_PRIMARY_FOLD), read_funcs=_IDENTITY_READ_FUNCS
    )
    assert hits == [], hits


def test_callshape_arm_identity_passes_parameter_dir() -> None:
    """Precision (FR-001-consistent): an identity read of a parameter ``feature_dir``
    whose one-hop caller has NO coord-aware binding is NOT flagged — even under the
    module-scoped harness that DOES supply caller context.

    This is the FR-001 boundary: the one-hop check fires ONLY when the caller binding
    is coord-aware-without-fold. Re-pinned (WP01 T004) to pass ``module=`` so it
    cannot drift into a vacuous "no caller context" pass.
    """
    module, func = _module_and_func(_IDENTITY_CLEAN_PARAMETER_DIR, "_read_identity")
    hits = callshape_violations(func, read_funcs=_IDENTITY_READ_FUNCS, module=module)
    assert hits == [], hits


# ---- LANES.JSON shape (read_lanes_json / require_lanes_json) ----

# Two-hop violation: dir bound from a coord-aware resolver, then lanes.json read.
# This is the pre-fix ``lanes/merge.py`` / ``core/worktree_topology.py`` shape
# (the #2185 cluster — its remediation lands in WP02, but the arm + self-test
# ship here so the detector exists before the routing).
_LANES_VIOLATION_TWO_HOP = '''
def f(repo_root, mission_slug):
    feature_dir = candidate_feature_dir_for_mission(repo_root, mission_slug)
    lanes_manifest = require_lanes_json(feature_dir)
    return lanes_manifest
'''

# Inline-call violation: coord-aware resolver call is the direct argument.
_LANES_VIOLATION_INLINE = '''
def f(repo_root, mission_slug):
    return read_lanes_json(resolve_feature_dir_for_slug(repo_root, mission_slug))
'''

# Routed (clean): dir built by the PRIMARY fold seam. Must NOT be flagged.
_LANES_CLEAN_PRIMARY_FOLD = '''
def f(repo_root, mission_slug):
    primary_dir = primary_feature_dir_for_mission(
        repo_root, _canonicalize_primary_read_handle(repo_root, mission_slug)
    )
    return read_lanes_json(primary_dir)
'''


def test_callshape_arm_lanes_flags_two_hop() -> None:
    """LANES two-hop: ``d = candidate_feature_dir_for_mission(...); require_lanes_json(d)``
    is FLAGGED (the pre-fix #2185 merge/lanes/core shape the literal vocabulary
    could not see)."""
    hits = callshape_violations(
        _func_from_source(_LANES_VIOLATION_TWO_HOP), read_funcs=_LANES_READ_FUNCS
    )
    assert hits == ["require_lanes_json(feature_dir)"], hits


def test_callshape_arm_lanes_flags_inline_call() -> None:
    """LANES inline-call: ``read_lanes_json(resolve_feature_dir_for_slug(...))``
    is FLAGGED."""
    hits = callshape_violations(
        _func_from_source(_LANES_VIOLATION_INLINE), read_funcs=_LANES_READ_FUNCS
    )
    assert hits == ["read_lanes_json(resolve_feature_dir_for_slug(...))"], hits


def test_callshape_arm_lanes_passes_primary_fold() -> None:
    """Precision: a lanes.json read off the PRIMARY fold seam is NOT flagged."""
    hits = callshape_violations(
        _func_from_source(_LANES_CLEAN_PRIMARY_FOLD), read_funcs=_LANES_READ_FUNCS
    )
    assert hits == [], hits


def test_callshape_arm_shape_isolation() -> None:
    """Scope isolation: the IDENTITY ``read_funcs`` does not flag a lanes.json call
    and vice-versa — each shape's vocabulary is bounded to its own read functions.
    """
    identity_func = _func_from_source(_IDENTITY_VIOLATION_TWO_HOP)
    lanes_func = _func_from_source(_LANES_VIOLATION_TWO_HOP)
    # The identity vocabulary sees the identity violation but not the lanes one.
    assert callshape_violations(identity_func, read_funcs=_IDENTITY_READ_FUNCS)
    assert callshape_violations(lanes_func, read_funcs=_IDENTITY_READ_FUNCS) == []
    # The lanes vocabulary sees the lanes violation but not the identity one.
    assert callshape_violations(lanes_func, read_funcs=_LANES_READ_FUNCS)
    assert callshape_violations(identity_func, read_funcs=_LANES_READ_FUNCS) == []


# ===========================================================================
# (5a) FR-001 alignment guard — the call-shape coord-aware set cannot 3-vs-5 drift.
# ===========================================================================


def test_callshape_coord_aware_set_aligns_with_read_arm() -> None:
    """The call-shape coord-aware set is a SUPERSET of the read-arm's topology-routed
    resolvers, AND catalogs the setup-plan wrapper (FR-001 widening, WP01 T001).

    Root cause of the old FR-001 hollowness was a 3-vs-5 asymmetry: the call-shape
    set held 3 names while the read arm's ``_TOPOLOGY_ROUTED_READ_RESOLVERS`` held 5,
    so the one-hop residual's caller binding (``_resolve_setup_plan_feature_dir`` →
    ``_find_feature_directory``) was not recognized as coord-aware and the one-hop
    check fired on no live caller. Guarding the superset relationship here means a
    future widening of the read arm that forgets the call-shape arm FAILS loudly
    rather than silently re-opening the gap.
    """
    missing = _TOPOLOGY_ROUTED_READ_RESOLVERS - _COORD_AWARE_CALLSHAPE_RESOLVERS
    assert not missing, (
        "Call-shape coord-aware set drifted NARROWER than the read arm's "
        f"topology-routed resolvers: {sorted(missing)} are read-arm coord-aware but "
        "not call-shape coord-aware. Re-align _COORD_AWARE_CALLSHAPE_RESOLVERS with "
        "_TOPOLOGY_ROUTED_READ_RESOLVERS (FR-001) so the one-hop check stays reachable."
    )
    assert "_resolve_setup_plan_feature_dir" in _COORD_AWARE_CALLSHAPE_RESOLVERS, (
        "The setup-plan wrapper _resolve_setup_plan_feature_dir is the exact binding "
        "name the _run_documentation_wiring <- setup_plan one-hop residual uses; it "
        "MUST be cataloged as coord-aware or FR-001 is hollow."
    )


# ===========================================================================
# (5b) FR-001 one-hop cross-function self-mutation (NFR-002 / SC-001 / SC-006).
# ===========================================================================
#
# Synthetic offender → RED; clean counterpart → GREEN. The callee has ZERO
# same-function coord-aware binding (its ``feature_dir`` is a pure parameter), so the
# flag can come ONLY from the one-hop caller index — proving the NEW FR-001 machinery
# (T001 widening + T003 caller index), not the pre-existing two-hop-local branch.

# Caller binds the dir from a coord-aware resolver (the setup-plan wrapper) WITHOUT a
# primary fold, then passes it one hop down. This is the real
# ``mission_setup_plan::_run_documentation_wiring`` ← ``setup_plan`` residual shape.
_VIOLATION_CROSS_FUNCTION = '''
def setup_plan(repo_root, feature):
    feature_dir = _resolve_setup_plan_feature_dir(repo_root, feature, json_output=False)
    return _run_documentation_wiring(feature_dir, repo_root)

def _run_documentation_wiring(feature_dir, repo_root):
    # Proves FR-001: flags only via one-hop caller binding (no same-function binding present)
    mission_type = get_mission_type(feature_dir)
    return mission_type
'''

_VIOLATION_CROSS_FUNCTION_KEYWORD = '''
def setup_plan(repo_root, feature):
    feature_dir = _resolve_setup_plan_feature_dir(repo_root, feature, json_output=False)
    return _run_documentation_wiring(feature_dir=feature_dir, repo_root=repo_root)

def _run_documentation_wiring(feature_dir, repo_root):
    mission_type = get_mission_type(feature_dir=feature_dir)
    return mission_type
'''

# Clean counterpart: the caller binds the dir from a PRIMARY fold seam, so the
# one-hop check clears the flag (the routed shape).
_CLEAN_CROSS_FUNCTION_PRIMARY_FOLD = '''
def setup_plan(repo_root, mission_slug):
    feature_dir = primary_feature_dir_for_mission(
        repo_root, _canonicalize_primary_read_handle(repo_root, mission_slug)
    )
    return _run_documentation_wiring(feature_dir, repo_root)

def _run_documentation_wiring(feature_dir, repo_root):
    mission_type = get_mission_type(feature_dir)
    return mission_type
'''


def test_callshape_arm_flags_one_hop_cross_function_param() -> None:
    """FR-001 non-vacuity: a parameter dir bound ONE HOP UP from a coord-aware
    resolver (no same-function binding present) is FLAGGED.

    The callee ``_run_documentation_wiring`` has no local coord-aware binding — its
    ``feature_dir`` is a pure parameter — so this snippet would NOT flag on the
    pre-existing two-hop-local branch. It flags ONLY because the module-scoped caller
    index (T003) follows one hop to ``setup_plan``'s coord-aware
    ``_resolve_setup_plan_feature_dir`` binding (recognized via the T001 widening).
    """
    module, func = _module_and_func(_VIOLATION_CROSS_FUNCTION, "_run_documentation_wiring")
    # Sanity: the callee has ZERO same-function coord-aware binding — the flag must
    # come solely from the one-hop caller, so without ``module`` there is NO flag.
    assert (
        callshape_violations(func, read_funcs=_IDENTITY_READ_FUNCS) == []
    ), "snippet must not flag without the module-scoped caller index (proves one-hop)"
    hits = callshape_violations(func, read_funcs=_IDENTITY_READ_FUNCS, module=module)
    assert hits == ["get_mission_type(feature_dir)"], hits
    # CT7 (NFR-001): content-anchor the offending site via composite_key — a
    # (qualname, token_line) pair that survives +1 line drift; NO file.py:NNN key.
    qn, token_line = composite_key(
        _VIOLATION_CROSS_FUNCTION,
        _offending_call_lineno(func, "get_mission_type"),
    )
    assert qn == "_run_documentation_wiring", qn
    assert "get_mission_type" in token_line, token_line


def test_callshape_arm_flags_one_hop_keyword_binding() -> None:
    """FR-001 boundary: keyword-call style is the same one-hop violation.

    Without this, ``caller(... feature_dir=feature_dir)`` and
    ``get_mission_type(feature_dir=feature_dir)`` bypass the arm while preserving
    the same runtime wrong-leg read.
    """
    module, func = _module_and_func(
        _VIOLATION_CROSS_FUNCTION_KEYWORD, "_run_documentation_wiring"
    )
    hits = callshape_violations(func, read_funcs=_IDENTITY_READ_FUNCS, module=module)
    assert hits == ["get_mission_type(feature_dir)"], hits


def test_callshape_arm_passes_one_hop_caller_primary_fold() -> None:
    """FR-001 boundary: the SAME parameter shape is NOT flagged when the one-hop
    caller binds the dir from a PRIMARY fold seam (the routed/clean counterpart)."""
    module, func = _module_and_func(
        _CLEAN_CROSS_FUNCTION_PRIMARY_FOLD, "_run_documentation_wiring"
    )
    hits = callshape_violations(func, read_funcs=_IDENTITY_READ_FUNCS, module=module)
    assert hits == [], hits


# ===========================================================================
# (5c) FR-008 attribute-discipline self-mutation (NFR-002 / SC-006).
# ===========================================================================
#
# The executor-shape escape: an identity read reaches through a coord-bearing
# attribute (``run.feature_dir``) the Name/Call branches never saw. Synthetic
# offender → RED; the sanctioned ``.target_feature_dir`` counterpart → GREEN.

_VIOLATION_ATTRIBUTE = '''
def merge_executor_step(run):
    # Executor-shape: reaches through a coord-bearing attribute (NOT a sanctioned
    # primary attribute) — flagged (SC-006 / FR-008).
    identity = resolve_mission_identity(run.feature_dir)
    return identity.mission_id
'''

_CLEAN_ATTRIBUTE_PRIMARY = '''
def merge_executor_step(run):
    identity = resolve_mission_identity(run.target_feature_dir)
    return identity.mission_id
'''


def test_callshape_arm_flags_coord_bearing_attribute() -> None:
    """FR-008 non-vacuity: ``resolve_mission_identity(run.feature_dir)`` in an
    executor-shape function is FLAGGED — the attribute escape the Name/Call branches
    were structurally blind to (SC-006)."""
    func = _func_from_source(_VIOLATION_ATTRIBUTE, name="merge_executor_step")
    hits = callshape_violations(func, read_funcs=_IDENTITY_READ_FUNCS)
    assert hits == ["resolve_mission_identity(run.feature_dir)"], hits
    # CT7 (NFR-001): content-anchor the offending site via composite_key (no :NNN key).
    qn, token_line = composite_key(
        _VIOLATION_ATTRIBUTE,
        _offending_call_lineno(func, "resolve_mission_identity"),
    )
    assert qn == "merge_executor_step", qn
    assert "run . feature_dir" in token_line, token_line


def test_callshape_arm_passes_sanctioned_primary_attribute() -> None:
    """FR-008 boundary: ``resolve_mission_identity(run.target_feature_dir)`` — the
    sanctioned primary attribute — is NOT flagged."""
    func = _func_from_source(_CLEAN_ATTRIBUTE_PRIMARY, name="merge_executor_step")
    hits = callshape_violations(func, read_funcs=_IDENTITY_READ_FUNCS)
    assert hits == [], hits
