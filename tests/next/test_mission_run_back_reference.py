"""Backward-compatibility and plumbing tests for MissionRun back-references.

WP05 (FR-024/FR-025/FR-026/FR-027/FR-028/FR-029/FR-030):
- MissionRunSnapshot gains optional mission_id and mission_slug fields
- MissionRunRef gains optional mission_id and mission_slug fields
- start_mission_run accepts and plumbs mission_id/mission_slug into snapshot/ref
- All snapshot-copy sites carry the new fields through
- Existing on-disk state.json files (no mission_id/mission_slug) load with None defaults
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from specify_cli.next._internal_runtime import (
    MissionPolicySnapshot,
    NullEmitter,
    start_mission_run,
)
from specify_cli.next._internal_runtime.engine import MissionRunRef
from specify_cli.next._internal_runtime.schema import MissionRunSnapshot

pytestmark = [pytest.mark.unit]


# ---------------------------------------------------------------------------
# T031 – Backward-compatibility: existing state.json files load with None defaults
# ---------------------------------------------------------------------------


def test_mission_run_snapshot_loads_without_mission_id():
    """Existing state.json files (no mission_id/mission_slug) load with None defaults."""
    legacy_data = {
        "run_id": "abc123",
        "mission_key": "software-dev",
        "template_path": "/tmp/mission.yaml",
        "template_hash": "deadbeef" * 8,
        "policy_snapshot": {"strictness": "medium", "default_route": "same_llm_context", "extras": {}},
        "completed_steps": [],
        "issued_step_id": None,
        "inputs": {},
        "decisions": {},
        "pending_decisions": {},
        "blocked_reason": None,
        # mission_id and mission_slug intentionally absent
    }
    snapshot = MissionRunSnapshot(**legacy_data)
    assert snapshot.mission_id is None
    assert snapshot.mission_slug is None


def test_mission_run_snapshot_loads_without_mission_id_model_validate():
    """model_validate path also handles missing fields with None defaults."""
    legacy_json = {
        "run_id": "abc456",
        "mission_key": "research",
        "template_path": "/tmp/mission.yaml",
        "template_hash": "cafebabe" * 8,
        # mission_id and mission_slug are absent
    }
    snapshot = MissionRunSnapshot.model_validate(legacy_json)
    assert snapshot.mission_id is None
    assert snapshot.mission_slug is None


def test_mission_run_ref_loads_without_mission_id():
    """MissionRunRef backward-compat: missing mission_id/mission_slug default to None."""
    ref = MissionRunRef(run_id="x", run_dir="/tmp/run", mission_key="software-dev")
    assert ref.mission_id is None
    assert ref.mission_slug is None


def test_mission_run_snapshot_with_new_fields():
    """New fields round-trip correctly when provided."""
    snapshot = MissionRunSnapshot(
        run_id="run1",
        mission_key="software-dev",
        template_path="/tmp/mission.yaml",
        template_hash="a" * 64,
        mission_id="01HABCDEFGHIJKLMNOPQRSTUVWX",
        mission_slug="my-feature-01KT6HVH",
    )
    assert snapshot.mission_id == "01HABCDEFGHIJKLMNOPQRSTUVWX"
    assert snapshot.mission_slug == "my-feature-01KT6HVH"


def test_mission_run_ref_with_new_fields():
    """MissionRunRef new fields round-trip correctly when provided."""
    ref = MissionRunRef(
        run_id="r1",
        run_dir="/tmp/runs/r1",
        mission_key="software-dev",
        mission_id="01HABCDEFGHIJKLMNOPQRSTUVWX",
        mission_slug="my-feature",
    )
    assert ref.mission_id == "01HABCDEFGHIJKLMNOPQRSTUVWX"
    assert ref.mission_slug == "my-feature"


# ---------------------------------------------------------------------------
# T028 – start_mission_run plumbs mission_id/mission_slug through
# ---------------------------------------------------------------------------


def _make_mission_yaml(tmp_path: Path, key: str = "test-mission") -> Path:
    mission_dir = tmp_path / key
    mission_dir.mkdir(parents=True, exist_ok=True)
    content = {
        "mission": {"key": key, "name": "Test Mission", "version": "1.0.0"},
        "steps": [
            {"id": "step-1", "title": "Step One", "prompt": "Do something."},
        ],
    }
    mission_yaml = mission_dir / "mission.yaml"
    mission_yaml.write_text(yaml.dump(content))
    return mission_dir


def test_start_mission_run_plumbs_mission_slug_and_id(tmp_path: Path):
    """start_mission_run passes mission_slug and mission_id into snapshot and ref."""
    mission_dir = _make_mission_yaml(tmp_path)
    run_store = tmp_path / "runs"

    ref = start_mission_run(
        template_key=str(mission_dir),
        inputs=None,
        policy_snapshot=MissionPolicySnapshot(),
        run_store=run_store,
        emitter=NullEmitter(),
        mission_slug="my-mission-01KT6HVH",
        mission_id="01KT6HVHEXAMPLEULID000000",
    )

    assert ref.mission_slug == "my-mission-01KT6HVH"
    assert ref.mission_id == "01KT6HVHEXAMPLEULID000000"


def test_start_mission_run_writes_mission_slug_to_snapshot(tmp_path: Path):
    """start_mission_run writes mission_slug/mission_id into the persisted state.json."""
    import json

    mission_dir = _make_mission_yaml(tmp_path)
    run_store = tmp_path / "runs"

    ref = start_mission_run(
        template_key=str(mission_dir),
        inputs=None,
        policy_snapshot=MissionPolicySnapshot(),
        run_store=run_store,
        emitter=NullEmitter(),
        mission_slug="slug-written-to-disk",
        mission_id="01TESTULID000000000000000",
    )

    run_dir = Path(ref.run_dir)
    state = json.loads((run_dir / "state.json").read_text())
    assert state["mission_slug"] == "slug-written-to-disk"
    assert state["mission_id"] == "01TESTULID000000000000000"


def test_start_mission_run_defaults_mission_fields_to_none(tmp_path: Path):
    """When mission_slug/mission_id are not provided, they default to None."""
    import json

    mission_dir = _make_mission_yaml(tmp_path)
    run_store = tmp_path / "runs"

    ref = start_mission_run(
        template_key=str(mission_dir),
        inputs=None,
        policy_snapshot=MissionPolicySnapshot(),
        run_store=run_store,
        emitter=NullEmitter(),
        # mission_slug and mission_id not passed
    )

    assert ref.mission_slug is None
    assert ref.mission_id is None

    run_dir = Path(ref.run_dir)
    state = json.loads((run_dir / "state.json").read_text())
    assert state.get("mission_slug") is None
    assert state.get("mission_id") is None
