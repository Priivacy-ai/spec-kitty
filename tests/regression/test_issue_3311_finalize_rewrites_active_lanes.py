"""Red-first reproduction of #3311 — rerunning ``finalize-tasks`` after
implementation has begun rewrites the established lane topology and clears
planning provenance in response to an ownership-only WP amendment.

Open P0: https://github.com/Priivacy-ai/spec-kitty/issues/3311

Root cause (verified against current source): the finalize path
(``_compute_and_write_lanes`` in
``src/specify_cli/cli/commands/agent/mission_finalize.py``) NEVER reads the
existing ``lanes.json`` — it calls ``compute_lanes`` (a pure recompute-from-scratch
whose Rule-1 union-find merges any WPs with overlapping ``owned_files``) and
overwrites ``lanes.json`` + ``planning_commit_sha`` unconditionally on every
non-``--validate-only`` run. So adding one path to a single WP's ``owned_files``
recomputes and renumbers the whole topology, collapses established lanes, and
clears ``planning_commit_sha``.

This drives the REAL ``finalize_tasks`` entry point twice: once to materialize the
established lanes, then again after an ownership-only ``owned_files`` amendment.

Desired post-fix outcome (either resolution turns this green): for a mission whose
lanes are already materialized, finalization preserves the established lane
identities and planning provenance (updating only the amended WP's write scope),
or refuses before writing any bytes — it must NOT regenerate executed topology or
clear ``planning_commit_sha`` as a side effect of an ownership-only amendment.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from specify_cli.lanes.persistence import read_lanes_json, write_lanes_json

from tests.specify_cli.cli.commands.agent.test_feature_finalize_bootstrap import (
    MODULE,
    _common_patches,
    _make_bootstrap_result,
    _setup_lane_based_feature,
)

pytestmark = pytest.mark.regression

_SEEDED_PLANNING_SHA = "deadbeef000deadbeef000deadbeef000deadbeef"


def _run_finalize(mission_slug: str, patches: dict[str, object]) -> None:
    from specify_cli.cli.commands.agent.mission import finalize_tasks

    ctx_patches = {k: patch(k, v) for k, v in patches.items()}
    for p in ctx_patches.values():
        p.start()
    try:
        finalize_tasks(feature=mission_slug, json_output=True, validate_only=False)
    except (typer.Exit, SystemExit):
        pass  # finalize-tasks may exit; the file writes are what we assert on
    finally:
        for p in ctx_patches.values():
            p.stop()


def test_ownership_only_amendment_preserves_established_lanes_and_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Keep finalize-tasks on the offline path: tests/conftest.py enables SaaS sync
    # globally, which can let a machine-local daemon-owner record short-circuit
    # finalize before these assertions run (mirrors the source module's autouse
    # guard, which does not apply to this importing module).
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)

    mission_slug = "061-lane-feature"
    feature_dir = _setup_lane_based_feature(tmp_path, mission_slug)

    patches = _common_patches(tmp_path, mission_slug)
    patches[f"{MODULE}._find_feature_directory"] = MagicMock(return_value=feature_dir)
    patches[f"{MODULE}.bootstrap_canonical_state"] = MagicMock(
        return_value=_make_bootstrap_result()
    )

    # Run 1: materialize the established topology (WP01 and WP02 own disjoint
    # files → two independent lanes).
    _run_finalize(mission_slug, patches)
    established = read_lanes_json(feature_dir)
    baseline_topology = {lane.lane_id: sorted(lane.wp_ids) for lane in established.lanes}
    assert len(baseline_topology) == 2, (
        f"sanity: two disjoint WPs must materialize two lanes; got {baseline_topology}"
    )

    # Stand in a recorded planning provenance SHA (finalize cannot capture one in a
    # non-git tmp workspace), representing an established mission's committed plan.
    established.planning_commit_sha = _SEEDED_PLANNING_SHA
    write_lanes_json(feature_dir, established)

    # Ownership-only amendment: add a path WP02 already owns to WP01's owned_files.
    # Nothing about dependencies, requirements, or lifecycle changes.
    wp01 = feature_dir / "tasks" / "WP01-test.md"
    wp01.write_text(
        wp01.read_text(encoding="utf-8").replace(
            "owned_files:\n  - src/alpha.py\n",
            "owned_files:\n  - src/alpha.py\n  - src/beta.py\n",
        ),
        encoding="utf-8",
    )

    # Run 2: the ownership-only amendment.
    _run_finalize(mission_slug, patches)
    after = read_lanes_json(feature_dir)

    # Sanity: the established lanes.json is what got rewritten (same mission).
    assert after.mission_slug == established.mission_slug

    # RED today: finalization unconditionally recomputes lanes.json and overwrites
    # planning_commit_sha on every re-run — an ownership-only amendment destroys the
    # established planning provenance instead of preserving it (here the recompute
    # cannot re-derive a SHA, so the recorded value is clobbered to None; in a real
    # repo it would be overwritten with the current branch tip, equally destroying
    # the recorded plan provenance).
    assert after.planning_commit_sha == _SEEDED_PLANNING_SHA, (
        "an ownership-only amendment must not clear/overwrite established planning "
        f"provenance; planning_commit_sha went {_SEEDED_PLANNING_SHA!r} -> "
        f"{after.planning_commit_sha!r}"
    )
