"""ATDD: status doctor must flag an uninitialized mission, not report Healthy.

Upstream #1589 (facet 2): when a mission has WP definitions but canonical status
was never bootstrapped (e.g. finalize-tasks aborted on a dependency cycle),
``run_doctor`` skips every WP-level check (``if snapshot:``) and returns zero
findings, so ``is_healthy`` is True. Operators see "Healthy" for a mission whose
runtime is completely wedged.

These tests drive the real ``run_doctor`` and fail on the unfixed code because no
finding is emitted for the uninitialized state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.status.doctor import Category, run_doctor

pytestmark = [pytest.mark.unit]


def _wp(tasks_dir: Path, wp_id: str, deps: list[str]) -> None:
    dep_block = "dependencies: []\n" if not deps else (
        "dependencies:\n" + "".join(f"- {d}\n" for d in deps)
    )
    tasks_dir.joinpath(f"{wp_id}-x.md").write_text(
        f"---\nwork_package_id: {wp_id}\ntitle: {wp_id}\n{dep_block}---\n\n# {wp_id}\n",
        encoding="utf-8",
    )


def _feature_with_wps(tmp_path: Path, deps: dict[str, list[str]]) -> Path:
    feature_dir = tmp_path / "kitty-specs" / "demo-mission"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    for wp_id, d in deps.items():
        _wp(tasks_dir, wp_id, d)
    # No status.json, no status.events.jsonl → uninitialized canonical status.
    return feature_dir


def test_doctor_flags_uninitialized_mission(tmp_path: Path) -> None:
    feature_dir = _feature_with_wps(tmp_path, {"WP01": [], "WP02": ["WP01"]})
    result = run_doctor(feature_dir, "demo-mission", tmp_path)
    cats = [f.category for f in result.findings]
    assert Category.UNINITIALIZED_STATUS in cats, (
        f"doctor should flag the uninitialized mission; findings={result.findings}"
    )
    assert not result.is_healthy


def test_doctor_uninitialized_finding_names_cycle(tmp_path: Path) -> None:
    feature_dir = _feature_with_wps(tmp_path, {"WP09": ["WP10"], "WP10": ["WP09"]})
    result = run_doctor(feature_dir, "demo-mission", tmp_path)
    uninit = [f for f in result.findings if f.category == Category.UNINITIALIZED_STATUS]
    assert uninit, "expected an uninitialized-status finding"
    msg = (uninit[0].message + " " + uninit[0].recommended_action).lower()
    assert "circular" in msg or "cycle" in msg
    assert "WP09" in uninit[0].message + uninit[0].recommended_action
