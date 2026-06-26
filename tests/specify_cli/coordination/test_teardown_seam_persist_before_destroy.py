"""FR-005 destroy-step fault injection: persist-before-destroy on both paths.

The shared seam ``teardown_coordination_topology`` must persist the
retrospective to its durable PRIMARY home (``kitty-specs/<slug>/retrospective
.yaml``) BEFORE it destroys the coordination worktree — with persist running
OUTSIDE the destroy best-effort swallow. These tests inject a fault at the
DESTROY step (force ``CoordinationWorkspace.teardown`` to raise) on BOTH the
merge cleanup path AND the mission-close / ``--discard`` path, and assert the
retrospective already exists despite the destroy failure.

Red-first evidence: on pre-WP04 code the destroy ran first (or no persist ran at
all), so the assertion ``retrospective.yaml exists after a destroy fault`` was
RED. After WP04 it is GREEN because the seam persists first, outside the swallow.

Design (NFR-002): the fault is at the DESTROY step (not persist) on a
genuinely-divergent coord topology (the coord worktree never materialized — only
the primary ``kitty-specs/<slug>/`` home exists), with a real ULID mission_id and
a pending (not-yet-written) retrospective. The persist leg is exercised through
the REAL ``run_retrospective_postcondition`` authority; only the heavy generator
(``_invoke_capture``) is stubbed to write the durable record the way a real
capture would, so the home-resolution + write-before-destroy ordering is real.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Drives the REAL teardown seam end-to-end with destroy-step fault injection
# through the live retrospective postcondition authority. Lives in the gated
# `tests/specify_cli/coordination/` home (`integration-tests-status` +
# `specify-cli-rest` shards) — `integration` is the marker those shards select.
# Its prior `unit` marker is selected by NO CI gate, and the former top-level
# `tests/coordination/` directory is selected by no shard at all, so this file
# ran in zero gates (gate-coverage orphan ratchet).
pytestmark = [pytest.mark.integration]

MISSION_SLUG = "durable-home-demo-01KVYM1W"
MID8 = "01KVYM1W"
MISSION_ID = "01KVYM1WZZZ0000000000000AB"


def _make_primary_home(repo_root: Path) -> Path:
    """Build a real primary ``kitty-specs/<slug>/`` home with meta.json.

    No coordination worktree is created — the topology is genuinely divergent
    (the coord husk never materialized), so home-resolution must land on the
    durable primary home regardless.
    """
    home = repo_root / "kitty-specs" / MISSION_SLUG
    home.mkdir(parents=True)
    (home / "meta.json").write_text(
        json.dumps(
            {
                "mission_id": MISSION_ID,
                "mid8": MID8,
                "mission_slug": MISSION_SLUG,
            }
        ),
        encoding="utf-8",
    )
    return home


def _capture_writes_record(home: Path):
    """Patch the heavy generator so a 'capture' writes the durable record.

    Mirrors what the real capture does — lands ``retrospective.yaml`` in the
    resolved durable home — without dragging in the runtime bridge generator.
    """

    def _fake_capture(**kwargs: object) -> None:
        feature_dir = kwargs["feature_dir"]
        assert isinstance(feature_dir, Path)
        (feature_dir / "retrospective.yaml").write_text(
            "schema_version: 1\nmission_slug: " + MISSION_SLUG + "\n",
            encoding="utf-8",
        )

    return patch(
        "specify_cli.post_merge.retrospective_terminus._invoke_capture",
        side_effect=_fake_capture,
    )


def _teardown_raises():
    """Force the DESTROY primitive to raise (fault-injection at destroy)."""
    return patch(
        "specify_cli.coordination.workspace.CoordinationWorkspace.teardown",
        side_effect=RuntimeError("simulated destroy failure (worktree locked)"),
    )


# ---------------------------------------------------------------------------
# Seam-level: persist runs before (and survives) a destroy fault
# ---------------------------------------------------------------------------


def test_seam_persists_retrospective_before_destroy_fault(tmp_path: Path) -> None:
    """The seam writes retrospective.yaml to the durable home despite a destroy fault."""
    from specify_cli.coordination.teardown import teardown_coordination_topology

    home = _make_primary_home(tmp_path)
    retro = home / "retrospective.yaml"
    assert not retro.exists()  # pending — not yet written

    with _capture_writes_record(home), _teardown_raises():
        # Destroy is swallowed inside the seam → returns False, does NOT raise.
        ok = teardown_coordination_topology(tmp_path, MISSION_SLUG, MID8)

    assert ok is False, "destroy fault must be swallowed (non-fatal), seam returns False"
    assert retro.exists(), (
        "retrospective.yaml must already exist at the durable home — persist runs "
        "BEFORE destroy, outside the swallow (FR-005)"
    )


def test_seam_persist_failure_surfaces_outside_swallow(tmp_path: Path) -> None:
    """A persist-step failure is NOT absorbed by the destroy swallow — it surfaces."""
    from specify_cli.coordination.teardown import teardown_coordination_topology

    _make_primary_home(tmp_path)

    boom = RuntimeError("persist machinery exploded")
    with (
        patch(
            "specify_cli.coordination.teardown._persist_retrospective",
            side_effect=boom,
        ),
        _teardown_raises(),  # even if destroy would also fail, persist surfaces first
        pytest.raises(RuntimeError, match="persist machinery exploded"),
    ):
        teardown_coordination_topology(tmp_path, MISSION_SLUG, MID8)


# ---------------------------------------------------------------------------
# Merge cleanup path: ordering bug fixed (persist before destroy)
# ---------------------------------------------------------------------------


def test_merge_cleanup_path_persists_before_destroy_fault(tmp_path: Path) -> None:
    """Driving the merge-cleanup seam call: retro persisted despite a destroy fault.

    The merge cleanup site (``cli/commands/merge.py``) routes through the seam, so
    the previously-buggy destroy-before-persist ordering is now persist-before-
    destroy. We exercise the seam exactly as the merge cleanup site invokes it.
    """
    from specify_cli.coordination.teardown import teardown_coordination_topology

    home = _make_primary_home(tmp_path)
    retro = home / "retrospective.yaml"

    with _capture_writes_record(home), _teardown_raises():
        teardown_coordination_topology(tmp_path, MISSION_SLUG, MID8)

    assert retro.exists(), (
        "merge cleanup must persist the retrospective to the durable home before "
        "destroying the coordination worktree (FR-005)"
    )


# ---------------------------------------------------------------------------
# Close / --discard path: persists before destroy via the mission_type helper
# ---------------------------------------------------------------------------


def test_close_discard_path_persists_before_destroy_fault(tmp_path: Path) -> None:
    """The mission-close/--discard helper persists the retro despite a destroy fault.

    Drives ``mission_type._teardown_coordination_worktree`` — the close/``--discard``
    production call site — end-to-end with the destroy primitive forced to raise.
    """
    from specify_cli.cli.commands.mission_type import _teardown_coordination_worktree

    home = _make_primary_home(tmp_path)
    retro = home / "retrospective.yaml"
    assert not retro.exists()

    # is_present is read after the (failed) destroy for the operator message;
    # with the worktree absent it returns False (clean) — that is fine, the
    # assertion under test is that the retrospective was persisted first.
    with _capture_writes_record(home), _teardown_raises():
        # Must NOT raise — destroy is best-effort inside the seam.
        _teardown_coordination_worktree(tmp_path, MISSION_SLUG, MID8)

    assert retro.exists(), (
        "mission close/--discard must persist the retrospective to the durable "
        "home before destroying the coordination worktree (FR-005)"
    )
