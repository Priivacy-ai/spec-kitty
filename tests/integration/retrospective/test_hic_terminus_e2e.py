"""T057 — HiC terminus end-to-end integration tests (run + skip cases).

Two sub-cases:

1. Run — operator answers "Y"; asserts:
   - Event sequence: requested(actor=human) -> started -> completed.
   - retrospective.yaml persisted with status=completed.
   - mission marked done (no exception).

2. Skip — operator answers "n" with a skip reason; asserts:
   - Event sequence: requested(actor=human) -> skipped (with skip_reason).
   - retrospective.yaml persisted with status=skipped.
   - mission marked done (HiC permits explicit skip).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from specify_cli.next._internal_runtime.retrospective_terminus import run_terminus
from specify_cli.retrospective.reader import read_record

from tests.integration.retrospective.conftest import (
    HUMAN_ACTOR,
    event_names,
    make_completed_record,
    read_events,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_hic_repo(tmp_path: Path, slug: str) -> tuple[Path, str]:
    """Create a minimal repo for HiC tests.

    Returns (feature_dir, mission_id).
    """
    import ulid as _ulid

    mission_id = str(_ulid.ULID())
    feature_dir = tmp_path / "kitty-specs" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "mission_id": mission_id,
        "mission_slug": slug,
        "mission_type": "software-dev",
    }
    (feature_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return feature_dir, mission_id


# ---------------------------------------------------------------------------
# T057 sub-case 1: HiC run
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_hic_run_emits_correct_event_sequence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HiC run: operator confirms -> requested(human), started, completed; record persisted."""
    monkeypatch.setenv("SPEC_KITTY_MODE", "human_in_command")

    slug = "hic-run-mission-e2e"
    feature_dir, mission_id = _setup_hic_repo(tmp_path, slug)

    record = make_completed_record(
        mission_id=mission_id,
        mission_slug=slug,
        mode_value="human_in_command",
    )

    def facilitator(**kwargs: Any) -> Any:
        return record

    def hic_prompt_run() -> tuple[bool, str | None]:
        return True, None

    # Must not raise — gate allows operator-driven completion.
    run_terminus(
        mission_id=mission_id,
        mission_type="software-dev",
        feature_dir=feature_dir,
        repo_root=tmp_path,
        operator_actor=HUMAN_ACTOR,
        facilitator_callback=facilitator,
        hic_prompt=hic_prompt_run,
    )

    # Event sequence.
    names = event_names(feature_dir)
    assert names == [
        "retrospective.requested",
        "retrospective.started",
        "retrospective.completed",
    ], f"Unexpected event sequence: {names}"

    # requested event must carry actor.kind=human.
    events = read_events(feature_dir)
    requested = next(e for e in events if e["event_name"] == "retrospective.requested")
    assert requested["actor"]["kind"] == "human", f"Expected actor.kind='human' on requested event, got: {requested['actor']}"
    assert requested["actor"]["id"] == HUMAN_ACTOR.id

    # retrospective.yaml must exist with status=completed.
    canonical = tmp_path / ".kittify" / "missions" / mission_id / "retrospective.yaml"
    assert canonical.exists(), f"retrospective.yaml not found: {canonical}"
    loaded = read_record(canonical)
    assert loaded.status == "completed"
    assert loaded.mission.mission_id == mission_id


# ---------------------------------------------------------------------------
# T057 sub-case 2: HiC skip
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_hic_skip_emits_skipped_event_and_persists_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HiC skip: operator skips -> requested(human), skipped; record status=skipped; gate allows."""
    monkeypatch.setenv("SPEC_KITTY_MODE", "human_in_command")

    slug = "hic-skip-mission-e2e"
    feature_dir, mission_id = _setup_hic_repo(tmp_path, slug)

    skip_reason = "docs-only change; retrospective adds no value"

    def hic_prompt_skip() -> tuple[bool, str | None]:
        return False, skip_reason

    # Must not raise — HiC mode permits explicit skip.
    run_terminus(
        mission_id=mission_id,
        mission_type="software-dev",
        feature_dir=feature_dir,
        repo_root=tmp_path,
        operator_actor=HUMAN_ACTOR,
        facilitator_callback=None,  # not called in skip path
        hic_prompt=hic_prompt_skip,
    )

    # Event sequence: no started/completed in skip path.
    names = event_names(feature_dir)
    assert names == [
        "retrospective.requested",
        "retrospective.skipped",
    ], f"Unexpected event sequence: {names}"

    # requested event carries human actor.
    events = read_events(feature_dir)
    requested = next(e for e in events if e["event_name"] == "retrospective.requested")
    assert requested["actor"]["kind"] == "human"

    # skipped event carries skip_reason.
    skipped = next(e for e in events if e["event_name"] == "retrospective.skipped")
    assert skipped["payload"]["skip_reason"] == skip_reason

    # retrospective.yaml must exist with status=skipped and matching reason.
    canonical = tmp_path / ".kittify" / "missions" / mission_id / "retrospective.yaml"
    assert canonical.exists(), f"retrospective.yaml not found: {canonical}"
    loaded = read_record(canonical)
    assert loaded.status == "skipped"
    assert loaded.skip_reason == skip_reason
    assert loaded.mission.mission_id == mission_id
