"""WP06 (#2937 / FR-009): finalize versions ``wps.yaml`` (D-001 default).

The bug: ``finalize-tasks`` READS ``wps.yaml`` (regenerating ``tasks.md`` from
it) but never COMMITS it, so the "finalized" checkpoint cannot reproduce its own
state — INV-5 is broken for ``wps.yaml`` (read from PRIMARY, never written
back). D-001 is resolved to the DEFAULT: version ``wps.yaml``.

Three legs, red-before / green-after the fix:

1. **Classifier (unit)** — ``kind_for_mission_file("…/wps.yaml")`` must classify
   to ``TASKS_INDEX`` (a PRIMARY-partition kind) rather than ``None``. A
   membership ADD for a currently-unclassified file — not a predicate fork.
2. **Collection (unit)** — ``_collect_finalize_artifacts`` must include
   ``feature_dir/"wps.yaml"`` so it reaches the commit router.
3. **Commit (integration, real git)** — a live finalize commit over a real
   repository must leave ``wps.yaml`` COMMITTED to the PRIMARY surface with a
   clean tree, exercised on BOTH a coord-topology mission (NFR-001) and a flat
   (non-coord) control that must behave identically.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mission_runtime import MissionArtifactKind, is_primary_artifact_kind
from mission_runtime.artifacts import kind_for_mission_file
from specify_cli.cli.commands.agent.mission_finalize import (
    _collect_finalize_artifacts,
    _commit_finalize_artifacts,
)
from specify_cli.core.constants import KITTY_SPECS_DIR
from tests.integration.coord_topology_fixture import (  # noqa: F401 — pytest fixture re-export
    CoordTopologyContext,
    FlatTopologyContext,
    coord_topology_mission,
    flat_topology_mission,
)

# Re-export so pytest discovers the imported fixtures in this module.
__all__ = ["coord_topology_mission", "flat_topology_mission"]


# ---------------------------------------------------------------------------
# Leg 1 — classifier (pure unit)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_wps_yaml_classifies_to_tasks_index_primary_partition() -> None:
    """``wps.yaml`` classifies to the PRIMARY-partition ``TASKS_INDEX`` kind.

    RED before the fix: ``kind_for_mission_file`` returns ``None`` (unclassified),
    so the partition seam only routes it PRIMARY by the ``None``→PRIMARY
    fallback coincidence rather than a derivable membership.
    """
    path = f"{KITTY_SPECS_DIR}/some-mission-01ABCDEF/wps.yaml"

    kind = kind_for_mission_file(path)

    assert kind is MissionArtifactKind.TASKS_INDEX, (
        f"wps.yaml must classify to TASKS_INDEX, got {kind!r}"
    )
    assert is_primary_artifact_kind(kind), "TASKS_INDEX must be a PRIMARY-partition kind"


# ---------------------------------------------------------------------------
# Leg 2 — collection (pure unit)
# ---------------------------------------------------------------------------


@pytest.mark.fast
def test_collect_finalize_artifacts_includes_wps_yaml(tmp_path: Path) -> None:
    """``_collect_finalize_artifacts`` must return ``feature_dir/wps.yaml``.

    RED before the fix: ``wps.yaml`` is never a finalize-commit candidate, so it
    is absent from the returned artifact set and never reaches the router.
    """
    feature_dir = tmp_path / "kitty-specs" / "some-mission-01ABCDEF"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "tasks.md").write_text("# tasks\n", encoding="utf-8")
    (tasks_dir / "WP01-x.md").write_text("---\nwork_package_id: WP01\n---\n", encoding="utf-8")
    wps_yaml = feature_dir / "wps.yaml"
    wps_yaml.write_text("work_packages: []\n", encoding="utf-8")

    artifacts = _collect_finalize_artifacts(feature_dir, tasks_dir)

    assert wps_yaml in artifacts, f"wps.yaml missing from collected artifacts: {artifacts}"


# ---------------------------------------------------------------------------
# Leg 3 — commit (integration, real git)
# ---------------------------------------------------------------------------

pytestmark: list[pytest.MarkDecorator] = []


def _git_out(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _disable_branch_protection(repo: Path) -> None:
    """Write a ``.kittify/config.yaml`` that protects NO branch.

    The fixtures commit their planning artifacts on ``main`` via raw git (which
    bypasses policy), but ``commit_for_mission`` enforces
    :class:`ProtectionPolicy`, whose default protected set is ``{main, master}``.
    An explicit empty ``protected_branches`` list lets the real commit land on the
    fixture's ``main`` — this test exercises the wps.yaml VERSIONING path, not the
    protected-branch guard (which has its own coverage).
    """
    kittify = repo / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(
        "protection:\n  protected_branches: []\n", encoding="utf-8"
    )


def _assert_wps_yaml_versioned(repo: Path, feature_dir: Path) -> None:
    """Assert ``wps.yaml`` is tracked by git AND not dirty/untracked (clean tree)."""
    rel = str((feature_dir / "wps.yaml").relative_to(repo))
    tracked = _git_out(repo, "ls-files", "--", rel)
    assert tracked == rel, (
        f"wps.yaml is NOT tracked by git after finalize.\n"
        f"  expected ls-files -> {rel!r}\n"
        f"  got               -> {tracked!r}\n"
        "INV-5 broken: the finalized checkpoint cannot reproduce its own wps.yaml state."
    )
    dirty = _git_out(repo, "status", "--porcelain", "--", rel)
    assert dirty == "", f"wps.yaml left dirty/uncommitted after finalize: {dirty!r}"


@pytest.mark.integration
@pytest.mark.git_repo
def test_finalize_versions_wps_yaml_coord_topology(
    coord_topology_mission: CoordTopologyContext,  # noqa: F811 — pytest fixture
) -> None:
    """Live coord-topology e2e (NFR-001): finalize commits ``wps.yaml`` to PRIMARY.

    RED before the fix: ``wps.yaml`` is never collected, so it stays UNTRACKED on
    the primary checkout after finalize (dirty tree, INV-5 broken). GREEN after:
    it is committed to the PRIMARY surface and the tree is clean.
    """
    ctx = coord_topology_mission
    _disable_branch_protection(ctx.repo)
    wps_yaml = ctx.primary_feature_dir / "wps.yaml"
    wps_yaml.write_text("work_packages: []\n", encoding="utf-8")

    # Precondition: wps.yaml is untracked before finalize.
    assert _git_out(ctx.repo, "status", "--porcelain", "--", str(wps_yaml.relative_to(ctx.repo))), (
        "fixture precondition: wps.yaml must start untracked/dirty"
    )

    _commit_finalize_artifacts(
        ctx.primary_feature_dir,
        ctx.primary_feature_dir / "tasks",
        ctx.repo,
        ctx.slug,
        "main",
        ctx.primary_feature_dir / "lanes.json",
        set(),
        json_output=True,
        updated_count=0,
    )

    _assert_wps_yaml_versioned(ctx.repo, ctx.primary_feature_dir)


@pytest.mark.integration
@pytest.mark.git_repo
def test_finalize_versions_wps_yaml_flat_control(
    flat_topology_mission: FlatTopologyContext,  # noqa: F811 — pytest fixture
) -> None:
    """Non-coord control: identical wps.yaml-versioning behavior on a flat mission."""
    ctx = flat_topology_mission
    _disable_branch_protection(ctx.repo)
    wps_yaml = ctx.primary_feature_dir / "wps.yaml"
    wps_yaml.write_text("work_packages: []\n", encoding="utf-8")

    _commit_finalize_artifacts(
        ctx.primary_feature_dir,
        ctx.primary_feature_dir / "tasks",
        ctx.repo,
        ctx.slug,
        "main",
        ctx.primary_feature_dir / "lanes.json",
        set(),
        json_output=True,
        updated_count=0,
    )

    _assert_wps_yaml_versioned(ctx.repo, ctx.primary_feature_dir)
