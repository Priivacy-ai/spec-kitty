"""WP04 / FR-009 (#2102): record-analysis planning-read double-resolution dedup guard.

**This is a structural AST dedup guard, NOT a behavioral red-first test.**

The record-analysis planning-read collapse is *behavior-neutral*: ``record_analysis``
used to resolve the mission dir twice — once via the coord-aware
``_find_feature_directory`` (which drives the placement-ref + dirty-tree preflight,
a KEEP) and AGAIN via a manual ``primary_feature_dir_for_mission`` call to obtain the
PRIMARY write dir. SPEC is a PRIMARY-partition kind, so routing that second resolve
through WP01's single ``resolve_planning_read_dir`` seam resolves to the SAME primary dir —
there is NO observable behavior delta. A behavioral red-first CANNOT go RED on the
un-collapsed code, and an ``assert read_dir == resolve_planning_read_dir(...)`` /
resolver-spy assertion would be tautological (green-before-and-after, pinning the
implementation to itself). The honest proof is therefore a **structural guard**: the
manual coord-then-primary double-resolution code path is GONE.

The genuine behavioral red-first for WP04 is carried by the map-requirements leg
(``test_map_requirements_read_surface.py`` / T014) — the only observable behavior
delta in this WP.

The guard asserts, by AST-scanning the ``record_analysis`` function body:

1. The planning-read leg no longer calls ``primary_feature_dir_for_mission`` — the
   manual primary double-resolution is removed.
2. The single kind-aware seam ``resolve_planning_read_dir`` IS called (the read flows
   through the one chokepoint).
3. The analysis-report WRITE target is preserved (``write_feature_dir`` is assigned
   from the seam and handed to ``write_analysis_report``).

Non-vacuity (anti-tautology, mirrors WP06's mandatory synthetic-AST self-test): the
scanner is exercised on a SYNTHETIC snippet that DOES contain the manual
double-resolution and MUST flag it, and on the collapsed snippet which MUST pass —
WITHOUT depending on the production mutation.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[5]
# #2056 decomposition: ``record_analysis`` relocated from the monolithic
# ``mission.py`` into the ``mission_record_analysis`` seam (Seam A). The AST guard
# scans the module where the function body now physically lives.
_MISSION_PY = (
    _REPO_ROOT / "src" / "specify_cli" / "cli" / "commands" / "agent" / "mission_record_analysis.py"
)

_PRIMARY_ANCHOR = "primary_feature_dir_for_mission"
# The canonical kind-aware read seam (WP01 chokepoint) — ``tasks.py`` and
# ``_commit_to_branch`` route every planning read/write onto this one authority.
_SEAM = "resolve_planning_read_dir"
_WRITE_TARGET = "write_feature_dir"
_WRITE_CALL = "write_analysis_report"


def _extract_function(source: str, name: str) -> ast.FunctionDef:
    """Return the top-level ``ast.FunctionDef`` named *name* from *source*."""
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found in source")


def _called_names(func: ast.AST) -> set[str]:
    """Collect the simple call-target names invoked anywhere inside *func*.

    Captures both bare-name calls (``foo(...)``) and attribute calls
    (``mod.foo(...)``) by their trailing identifier, so a late-imported helper is
    detected regardless of how it is referenced.
    """
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, ast.Attribute):
                names.add(target.attr)
    return names


def _assigns_write_target_from_seam(func: ast.AST) -> bool:
    """True iff ``write_feature_dir = _planning_read_dir(...)`` appears in *func*.

    Proves the WRITE anchor is preserved (record-analysis still resolves a primary
    dir for the write) AND that it now flows through the single seam rather than a
    bespoke ``primary_feature_dir_for_mission`` call.
    """
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if _WRITE_TARGET not in targets:
                continue
            call_target = node.value.func
            callee = (
                call_target.id
                if isinstance(call_target, ast.Name)
                else call_target.attr
                if isinstance(call_target, ast.Attribute)
                else None
            )
            if callee == _SEAM:
                return True
    return False


def _hands_write_target_to_writer(func: ast.AST) -> bool:
    """True iff ``write_analysis_report(feature_dir=write_feature_dir, ...)`` appears."""
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        call_target = node.func
        callee = (
            call_target.id
            if isinstance(call_target, ast.Name)
            else call_target.attr
            if isinstance(call_target, ast.Attribute)
            else None
        )
        if callee != _WRITE_CALL:
            continue
        for kw in node.keywords:
            if (
                kw.arg == "feature_dir"
                and isinstance(kw.value, ast.Name)
                and kw.value.id == _WRITE_TARGET
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# Non-vacuity self-test (anti-tautology): the scanner MUST flag a synthetic
# double-resolution and MUST pass a synthetic collapsed snippet — proven WITHOUT
# touching the production source.
# ---------------------------------------------------------------------------

_ROGUE_DOUBLE_RESOLUTION = """
def record_analysis():
    feature_dir = _find_feature_directory(repo_root)
    placement_ref = _resolve_record_analysis_placement_ref(repo_root, feature_dir)
    # manual coord-then-primary double-resolution (the defect this WP removes):
    write_feature_dir = primary_feature_dir_for_mission(repo_root, feature_dir.name)
    result = write_analysis_report(feature_dir=write_feature_dir, repo_root=repo_root)
"""

_COLLAPSED_SINGLE_SEAM = """
def record_analysis():
    feature_dir = _find_feature_directory(repo_root)
    placement_ref = _resolve_record_analysis_placement_ref(repo_root, feature_dir)
    # collapsed onto the single kind-aware seam (the post-WP04 shape):
    write_feature_dir = resolve_planning_read_dir(repo_root, feature_dir.name, kind=_kind_for_artifact("spec"))
    result = write_analysis_report(feature_dir=write_feature_dir, repo_root=repo_root)
"""


def test_scanner_flags_synthetic_double_resolution() -> None:
    """Anti-vacuity: the rogue (manual primary double-resolve) is FLAGGED."""
    func = _extract_function(_ROGUE_DOUBLE_RESOLUTION, "record_analysis")
    called = _called_names(func)
    # The rogue calls the bespoke primary anchor (the double-resolution) and does
    # NOT route through the seam — the scanner must distinguish it.
    assert _PRIMARY_ANCHOR in called
    assert _SEAM not in called
    assert not _assigns_write_target_from_seam(func)


def test_scanner_passes_synthetic_collapsed_snippet() -> None:
    """Anti-vacuity: the collapsed shape PASSES every assertion the guard makes."""
    func = _extract_function(_COLLAPSED_SINGLE_SEAM, "record_analysis")
    called = _called_names(func)
    assert _PRIMARY_ANCHOR not in called
    assert _SEAM in called
    assert _assigns_write_target_from_seam(func)
    assert _hands_write_target_to_writer(func)


# ---------------------------------------------------------------------------
# The production guard: the real ``record_analysis`` must match the collapsed shape.
# ---------------------------------------------------------------------------


def test_record_analysis_double_resolution_collapsed() -> None:
    """The real ``record_analysis`` no longer double-resolves the planning-read leg.

    Structural dedup guard (FR-009): the manual coord-then-primary double-resolution
    is gone — the planning-read leg flows through the single ``resolve_planning_read_dir``
    seam, and the analysis-report WRITE target is preserved.
    """
    source = _MISSION_PY.read_text(encoding="utf-8")
    func = _extract_function(source, "record_analysis")
    called = _called_names(func)

    # (1) The manual primary double-resolution is removed from record_analysis.
    assert _PRIMARY_ANCHOR not in called, (
        "record_analysis still calls primary_feature_dir_for_mission — the manual "
        "coord-then-primary double-resolution was not collapsed onto the seam (FR-009)."
    )
    # (2) The single kind-aware seam carries the planning read.
    assert _SEAM in called, (
        "record_analysis no longer routes the planning read through resolve_planning_read_dir "
        "— the collapse must consume the WP01 chokepoint, not reconstruct a resolution."
    )
    # (3) The WRITE target is preserved and sourced from the seam, then handed to the
    #     writer (record-analysis write-to-primary KEEP, now via the one seam).
    assert _assigns_write_target_from_seam(func), (
        "write_feature_dir must be assigned from resolve_planning_read_dir (the seam) — the "
        "write-to-primary KEEP is preserved, the duplicate resolution removed."
    )
    assert _hands_write_target_to_writer(func), (
        "write_analysis_report must still receive feature_dir=write_feature_dir — the "
        "analysis-report write anchor is unchanged."
    )
