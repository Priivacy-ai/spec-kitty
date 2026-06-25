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
    """
    topology_routed = _names_bound_from(func, _TOPOLOGY_ROUTED_READ_RESOLVERS)
    violations: list[str] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.BinOp):
            continue
        base = _planning_join_base_name(node)
        if base is None and include_dirs:
            base = _planning_dir_join_base_name(node)
        if base is not None and base in topology_routed:
            artifact = node.right.value  # type: ignore[attr-defined]
            violations.append(f"{base} / {artifact}")
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
_DIR_READ_KNOWN_RESIDUALS: frozenset[str] = frozenset(
    {
        "src/specify_cli/cli/commands/agent/tasks.py::finalize_tasks",
        "src/specify_cli/cli/commands/agent/tasks.py::status",
        "src/specify_cli/cli/commands/agent/workflow.py::_preview_claimable_wp_for_mission",
        "src/specify_cli/cli/commands/agent/workflow.py::_resolve_review_context",
        "src/specify_cli/cli/commands/agent/workflow.py::implement",
        "src/specify_cli/cli/commands/agent/workflow.py::review",
        # NB(#2057): ``merge.py::_mark_wp_merged_done`` was relocated into the
        # ``specify_cli/merge/done_bookkeeping.py`` seam by the merge-decomposition
        # mission; ``merge.py`` now only re-exports it. The dir-read scan scopes
        # ``cli/commands/`` only, so the residual left this surface — unpin it so
        # the ratchet stays tight (the test instructs this exact removal).
    }
)


def test_dir_read_arm_known_residuals_are_pinned() -> None:
    """The implement/review/merge WP-task dir-read residuals match the named set.

    Observability ratchet for the OUT-OF-SCOPE N+2 cluster: the broadened dir-read
    arm flags these implement-loop sites, which belong to a separate implement-loop
    write-surface mission. Pinning the exact set means a NEWLY-introduced
    implement-loop dir-read (set grows) FAILS here — it cannot hide behind the known
    cluster — and a fix in the follow-up mission (set shrinks) ALSO fails, prompting
    its removal from this pin. The accept-gate package is fenced separately and stays
    clean (``test_dir_read_arm_default_deny_accept_package_clean``).
    """
    found: dict[str, list[str]] = {}
    for rel_path, func in _iter_functions_under(_COMMAND_PACKAGE_DIRS):
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
