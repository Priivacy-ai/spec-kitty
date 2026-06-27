"""Mission-level close-out regression guard — coord-read-residuals (01KW2M8V).

WP05 / T027. Requirements: FR-006, FR-007, FR-010, SC-004, NFR-001, NFR-005.

WP01 shipped the FR-007 ``callshape_violations`` arm together with *synthetic*
self-tests (``test_gate_read_literal_ban.py`` §5) that prove the detector FLAGS the
pre-fix shape and PASSES the routed shape on hand-written snippets. Synthetic
non-vacuity is necessary but NOT sufficient: a gate that only ever runs against
its own fixtures can never catch a real offender (the gate-unmask-cannot-self-
validate trap). This module closes that gap by wiring the arm LIVE as a
production scan over the REAL in-scope ``src/`` tree — the same
``_iter_functions_under`` machinery the dir-read ratchet uses.

Three guards:

1. **Live FR-007 arm (the crux).** Run ``callshape_violations`` over every
   function in the in-scope module families, for BOTH shapes, and assert ZERO
   un-pinned violations:

   * IDENTITY (``resolve_mission_identity`` / ``get_mission_type``) →
     ``cli/commands/`` + ``agent_utils/status.py``.
   * LANES.JSON (``read_lanes_json`` / ``require_lanes_json``) → ``merge/`` +
     ``lanes/`` + ``core/worktree_topology.py``.

   WP01 (identity) + WP02/WP03 (merge / lanes / core) routed every in-scope
   site onto a PRIMARY fold, so the live scan is clean. If ANY in-scope site
   flags, a routing was missed — this test (correctly) goes RED. An anti-vacuity
   floor proves the scan actually SAW the in-scope read call sites (it is not
   green merely because it matched nothing). The ``#2167`` ``scripts/tasks/``
   legacy reader is OUTSIDE these families and is deliberately not scanned.

2. **Floor honesty (FR-010 / SC-004).** ``ROUTED_CANONICALIZER_FLOOR`` matches the
   recorded census. The honest history: **seam-routing did NOT move the
   canonicalizer census.** Only WP01's seven identity ANCHORS (direct
   ``primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))``
   calls) raised it (38 → 45 total; 35 → 42 routed). WP02/WP03 routed the merge /
   lanes / core reads through the kind-aware *seam*
   (``resolve_planning_read_dir`` / the PRIMARY fold passed to identity & lanes
   reads), which the canonicalizer discriminator does not count as a new direct
   primitive anchor — so those WPs left the census unchanged. This guard records
   that plainly: no re-pinned-integer "gain" is claimed for the seam routing.

3. **NFR-001 — zero STATUS legs re-routed to PRIMARY.** The PRIMARY evidence is
   the WP04 STATUS-from-husk behavioral assertions in
   ``tests/integration/test_coord_read_residuals_proof.py`` (the event log via
   ``read_events`` and the executor ``status_feature_dir`` leg STILL resolve the
   coord husk, proven by spies on real runs with executed revert-fails guards).
   This module asserts those named proofs EXIST (a deletion fails here) and adds a
   SECONDARY static cross-check: no STATUS ``read_events`` read in the in-scope
   STATUS-bearing modules is fed by a PRIMARY-fold seam.

Strictness mirrors the sibling ratchets (``pytestmark = pytest.mark.architectural``;
AST-only scans; ``_REPO_ROOT = parents[2]``). The arm machinery and the
canonicalizer census are imported from their canonical homes rather than
re-implemented — this guard COMPOSES the existing gates over the real tree.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.architectural.test_gate_read_literal_ban import (
    _IDENTITY_READ_FUNCS,
    _LANES_READ_FUNCS,
    _PRIMARY_FOLD_CALLSHAPE_FUNCS,
    _call_func_name,
    _find_function,
    _iter_functions_under,
    _names_bound_from,
    callshape_violations,
)
from tests.architectural.test_resolution_authority_gates import (
    CANONICALIZER_FLOOR,
    ROUTED_CANONICALIZER_FLOOR,
    ROUTED_CANONICALIZER_FLOOR_MARGIN,
    scan_canonicalizer_call_sites,
)

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"


# ---------------------------------------------------------------------------
# In-scope module families (FR-007 / SC-005, bounded PER SHAPE so the live arm
# never red-CIs on out-of-scope strangers — sync/, acceptance/, policy/,
# orchestrator_api/ are follow-on).
# ---------------------------------------------------------------------------
_IDENTITY_SCAN_DIRS: tuple[Path, ...] = (_SRC / "specify_cli" / "cli" / "commands",)
_IDENTITY_SCAN_FILES: tuple[Path, ...] = (_SRC / "specify_cli" / "agent_utils" / "status.py",)

_LANES_SCAN_DIRS: tuple[Path, ...] = (
    _SRC / "specify_cli" / "merge",
    _SRC / "specify_cli" / "lanes",
)
_LANES_SCAN_FILES: tuple[Path, ...] = (_SRC / "specify_cli" / "core" / "worktree_topology.py",)

# Anti-vacuity floors: the live scan currently SEES 12 identity and 10 lanes.json
# in-scope read call sites (all routed). The floors are concrete census integers a
# couple below live — tight enough that a scanner that suddenly matched NOTHING
# (vacuous green) fails, loose enough that a benign refactor that drops one read
# site does not. ``> 0`` is explicitly NOT used (it would pass vacuously).
_IDENTITY_READ_SITE_FLOOR = 10
_LANES_READ_SITE_FLOOR = 8

# Genuinely-out-of-scope-but-flagged sites would be pinned here with a tracking
# reference (no silent skip — FR-007). NONE exist in the in-scope families: WP01
# routed every identity site, WP02/WP03 routed every merge/lanes/core site. The
# set is asserted EXACTLY (shrink-only): an unexpected flag fails, and a stale pin
# that no longer flags also fails.
_CALLSHAPE_KNOWN_RESIDUALS: frozenset[str] = frozenset()

# NFR-001 SECONDARY cross-check: the STATUS-bearing in-scope modules whose
# ``read_events`` STATUS reads MUST stay coord-aware (never fed a PRIMARY fold).
_STATUS_BEARING_MODULES: tuple[str, ...] = (
    "src/specify_cli/lanes/recovery.py",
    "src/specify_cli/merge/executor.py",
)
_STATUS_READ_FUNCS: frozenset[str] = frozenset({"read_events"})

# NFR-001 PRIMARY evidence: the WP04 behavioral STATUS-from-husk proofs.
_WP04_PROOF_MODULE = "tests/integration/test_coord_read_residuals_proof.py"
_WP04_STATUS_FROM_HUSK_PROOFS: tuple[str, ...] = (
    "test_recovery_status_leg_reads_coord_husk_not_primary",
    "test_executor_status_feature_dir_stays_coord_aware",
)


def _rel(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _functions_in_family(
    pkg_dirs: tuple[Path, ...], files: tuple[Path, ...]
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Every ``(rel_path, function)`` in *pkg_dirs* plus the standalone *files*."""
    found = list(_iter_functions_under(pkg_dirs))
    for py in files:
        tree = ast.parse(py.read_text(encoding="utf-8"))
        rel = _rel(py)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append((rel, node))
    return found


def _live_callshape_offenders(
    pkg_dirs: tuple[Path, ...],
    files: tuple[Path, ...],
    read_funcs: frozenset[str],
) -> dict[str, list[str]]:
    """Run the FR-007 arm LIVE over a family; return ``{rel::func: [hits]}``."""
    offenders: dict[str, list[str]] = {}
    for rel_path, func in _functions_in_family(pkg_dirs, files):
        hits = callshape_violations(func, read_funcs=read_funcs)
        if hits:
            offenders[f"{rel_path}::{func.name}"] = hits
    return offenders


def _count_read_call_sites(
    pkg_dirs: tuple[Path, ...],
    files: tuple[Path, ...],
    read_funcs: frozenset[str],
) -> int:
    """Count every in-scope call to a *read_funcs* function (routed or not)."""
    total = 0
    for _rel_path, func in _functions_in_family(pkg_dirs, files):
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Call)
                and _call_func_name(node) in read_funcs
                and node.args
            ):
                total += 1
    return total


# ===========================================================================
# (1) Live FR-007 arm — the crux: zero un-pinned violations on the real tree.
# ===========================================================================


def test_fr007_arm_live_identity_scan_is_clean() -> None:
    """LIVE: no in-scope IDENTITY read resolves off a coord-aware dir without a
    PRIMARY fold (``cli/commands/`` + ``agent_utils/status.py``).

    This is the production realization of the WP01 synthetic self-tests: the arm
    now actively gates the REAL tree. WP01 routed every identity site onto
    ``primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))``, so
    the scan is clean. A flag here means a ``resolve_mission_identity`` /
    ``get_mission_type`` read was left bound to a coord-aware resolver (it would
    read the STATUS-only ``-coord`` husk, which carries no ``meta.json`` since
    #2106) — route it through the PRIMARY fold seam.
    """
    offenders = _live_callshape_offenders(
        _IDENTITY_SCAN_DIRS, _IDENTITY_SCAN_FILES, _IDENTITY_READ_FUNCS
    )
    flagged = set(offenders)
    unexpected = flagged - _CALLSHAPE_KNOWN_RESIDUALS
    stale_pins = _CALLSHAPE_KNOWN_RESIDUALS - flagged
    assert not unexpected, (
        "LIVE FR-007 identity arm flagged un-pinned coord-aware read(s): "
        f"{dict(sorted((k, offenders[k]) for k in unexpected))}. A "
        "resolve_mission_identity / get_mission_type read is bound from a "
        "coord-aware resolver (resolve_feature_dir_for_mission / "
        "candidate_feature_dir_for_mission / resolve_feature_dir_for_slug) without "
        "a PRIMARY fold — it reads the -coord husk (no meta.json since #2106). "
        "Route it through primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...)) "
        "(FR-006 / FR-007). A missed in-scope routing means a prior WP left a site."
    )
    assert not stale_pins, (
        f"stale callshape pin(s) no longer flagged: {sorted(stale_pins)} — remove "
        "them from _CALLSHAPE_KNOWN_RESIDUALS (shrink-only)."
    )


def test_fr007_arm_live_lanes_scan_is_clean() -> None:
    """LIVE: no in-scope LANES.JSON read resolves off a coord-aware dir without a
    PRIMARY fold (``merge/`` + ``lanes/`` + ``core/worktree_topology.py``).

    WP02 (merge cluster) + WP03 (lanes/core cluster) routed every ``read_lanes_json``
    / ``require_lanes_json`` read onto the PRIMARY fold. A flag here means a
    LANE_STATE read was left coord-aware (it would read the husk, which carries no
    ``lanes.json`` since #2106) — route it through the PRIMARY fold seam.
    """
    offenders = _live_callshape_offenders(
        _LANES_SCAN_DIRS, _LANES_SCAN_FILES, _LANES_READ_FUNCS
    )
    flagged = set(offenders)
    unexpected = flagged - _CALLSHAPE_KNOWN_RESIDUALS
    stale_pins = _CALLSHAPE_KNOWN_RESIDUALS - flagged
    assert not unexpected, (
        "LIVE FR-007 lanes.json arm flagged un-pinned coord-aware read(s): "
        f"{dict(sorted((k, offenders[k]) for k in unexpected))}. A read_lanes_json "
        "/ require_lanes_json read is bound from a coord-aware resolver without a "
        "PRIMARY fold — it reads the -coord husk (no lanes.json since #2106). Route "
        "it through primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...)) "
        "(FR-007). A missed in-scope routing means a prior WP left a site."
    )
    assert not stale_pins, (
        f"stale callshape pin(s) no longer flagged: {sorted(stale_pins)} — remove "
        "them from _CALLSHAPE_KNOWN_RESIDUALS (shrink-only)."
    )


def test_fr007_arm_live_scan_is_non_vacuous() -> None:
    """The clean scans above are not vacuously green: the arm SAW the in-scope read
    call sites it is meant to gate.

    A regression that renamed the read funcs, emptied the scan dirs, or broke
    ``_iter_functions_under`` would make the live arm match NOTHING — and report a
    false-clean. This guard pins the live count of in-scope identity / lanes.json
    read CALL SITES (routed or not) to a concrete floor a couple below the live
    census (12 identity / 10 lanes), so a vacuous scan FAILS.
    """
    identity_sites = _count_read_call_sites(
        _IDENTITY_SCAN_DIRS, _IDENTITY_SCAN_FILES, _IDENTITY_READ_FUNCS
    )
    lanes_sites = _count_read_call_sites(
        _LANES_SCAN_DIRS, _LANES_SCAN_FILES, _LANES_READ_FUNCS
    )
    assert identity_sites >= _IDENTITY_READ_SITE_FLOOR, (
        f"in-scope identity read call sites dropped to {identity_sites}; expected "
        f">= {_IDENTITY_READ_SITE_FLOOR}. A shrinking count likely means the live "
        "arm scan stopped matching read call sites (vacuous green)."
    )
    assert lanes_sites >= _LANES_READ_SITE_FLOOR, (
        f"in-scope lanes.json read call sites dropped to {lanes_sites}; expected "
        f">= {_LANES_READ_SITE_FLOOR}. A shrinking count likely means the live arm "
        "scan stopped matching read call sites (vacuous green)."
    )


# ===========================================================================
# (2) Floor honesty — seam-routing did NOT move the canonicalizer census.
# ===========================================================================


def test_routed_canonicalizer_floor_matches_recorded_census() -> None:
    """``ROUTED_CANONICALIZER_FLOOR`` is consistent with the live routed census,
    and the floor honesty story is recorded plainly.

    HONESTY (FR-010): seam-routing did NOT move the canonicalizer census. The
    census moved 35 → 42 routed (38 → 45 total) because of WP01's SEVEN identity
    ANCHORS — direct ``primary_feature_dir_for_mission(_canonicalize_primary_read_handle(...))``
    calls the canonicalizer discriminator counts. WP02/WP03 routed merge / lanes /
    core reads through the kind-aware *seam* (the PRIMARY fold passed to identity &
    lanes reads), which is NOT a new direct primitive anchor — so those WPs left
    the census UNCHANGED. No re-pinned-integer "gain" is claimed for them.

    The bounds mirror ``test_routed_count_floor`` (the floor is a concrete integer
    strictly below live, within ``ROUTED_CANONICALIZER_FLOOR_MARGIN``).
    """
    assert ROUTED_CANONICALIZER_FLOOR == 38, (
        "ROUTED_CANONICALIZER_FLOOR drifted from the recorded WP01 census (38 = "
        "42 live routed − MARGIN 4). If it changed, a WP moved the census; record "
        "the honest before/after rather than re-pinning the integer."
    )
    assert CANONICALIZER_FLOOR == 45, (
        "CANONICALIZER_FLOOR drifted from the recorded total census (45)."
    )
    sites = scan_canonicalizer_call_sites(_SRC)
    routed = [s for s in sites if s.is_canonical]
    # The recorded floor must remain a tight, non-vacuous concrete integer.
    assert len(routed) > ROUTED_CANONICALIZER_FLOOR, (
        f"live routed canonicalizer census ({len(routed)}) must stay strictly above "
        f"the floor ({ROUTED_CANONICALIZER_FLOOR}); seam-routing must not have "
        "silently dropped routed anchors."
    )
    assert len(routed) - ROUTED_CANONICALIZER_FLOOR <= ROUTED_CANONICALIZER_FLOOR_MARGIN, (
        f"live routed census ({len(routed)}) is more than MARGIN "
        f"({ROUTED_CANONICALIZER_FLOOR_MARGIN}) above the floor "
        f"({ROUTED_CANONICALIZER_FLOOR}); tighten the floor to the honest census."
    )


# ===========================================================================
# (3) NFR-001 — zero STATUS legs re-routed to PRIMARY.
# ===========================================================================


def test_wp04_status_from_husk_proofs_exist() -> None:
    """NFR-001 PRIMARY evidence: the WP04 behavioral STATUS-from-husk proofs exist.

    These are the load-bearing NFR-001 evidence — they assert (on real runs, with
    executed revert-fails guards) that the STATUS event log (``read_events``) and
    the executor ``status_feature_dir`` leg STILL resolve the coord husk, never
    PRIMARY. Deleting/renaming them would silently remove the primary proof, so
    this close-out guard pins their existence.
    """
    proof_path = _REPO_ROOT / _WP04_PROOF_MODULE
    assert proof_path.exists(), (
        f"WP04 behavioral proof module missing: {_WP04_PROOF_MODULE} — the NFR-001 "
        "STATUS-from-husk primary evidence is gone."
    )
    tree = ast.parse(proof_path.read_text(encoding="utf-8"))
    missing = [
        name for name in _WP04_STATUS_FROM_HUSK_PROOFS if _find_function(tree, name) is None
    ]
    assert not missing, (
        f"WP04 STATUS-from-husk proof function(s) missing: {missing}. These are the "
        "NFR-001 primary evidence (the STATUS legs still read the coord husk on a "
        "real run); restore them."
    )


def test_no_status_leg_rerouted_to_primary() -> None:
    """NFR-001 SECONDARY cross-check: no in-scope STATUS ``read_events`` read is fed
    a PRIMARY-fold dir.

    This is a static cross-check ONLY — the PRIMARY evidence is the WP04 behavioral
    proofs (``test_wp04_status_from_husk_proofs_exist``). A STATUS event-log read
    that was silently re-pointed to ``primary_feature_dir_for_mission`` /
    ``resolve_planning_read_dir`` (the NFR-001 regression) would surface here as a
    ``read_events`` call whose first arg is bound from / built by a PRIMARY-fold
    seam. The STATUS legs must stay coord-aware (read the ``-coord`` husk).
    """
    offenders: dict[str, list[str]] = {}
    for rel_path in _STATUS_BEARING_MODULES:
        tree = ast.parse((_REPO_ROOT / rel_path).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            primary_bound = _names_bound_from(node, _PRIMARY_FOLD_CALLSHAPE_FUNCS)
            hits: list[str] = []
            for call in ast.walk(node):
                if (
                    not isinstance(call, ast.Call)
                    or _call_func_name(call) not in _STATUS_READ_FUNCS
                    or not call.args
                ):
                    continue
                first = call.args[0]
                if isinstance(first, ast.Name) and first.id in primary_bound:
                    hits.append(f"read_events({first.id})  # PRIMARY-fold bound")
                elif isinstance(first, ast.Call) and (
                    _call_func_name(first) in _PRIMARY_FOLD_CALLSHAPE_FUNCS
                ):
                    hits.append(f"read_events({_call_func_name(first)}(...))")
            if hits:
                offenders[f"{rel_path}::{node.name}"] = hits

    assert not offenders, (
        "NFR-001 REGRESSION: a STATUS read_events leg was re-routed to PRIMARY: "
        f"{dict(sorted(offenders.items()))}. The STATUS event log must stay "
        "coord-aware (read the -coord husk via candidate_feature_dir_for_mission); "
        "see the WP04 behavioral proofs for the primary evidence (C-001 KEEP)."
    )
