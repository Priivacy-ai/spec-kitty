"""Parity: both MissionCreated surfaces share one canonical payload builder (#2270).

Before #2270 the local lifecycle path (``emit_mission_created_local``) and the
sync emitter (``EventEmitter.emit_mission_created``) each derived the payload
independently and could drift (default friendly_name, created_at, None-field
shape). Both now route through ``build_mission_created_payload``; these tests
pin that they produce the identical payload for the same source facts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from specify_cli.core.mission_payload import build_mission_created_payload
from specify_cli.status.lifecycle_events import emit_mission_created_local
from specify_cli.sync.emitter import EventEmitter

# Fixed created_at so the ``created_at -> now`` default does not vary between
# the two call sites; friendly_name/purpose left None to exercise the shared
# default derivation.
_FACTS: dict[str, Any] = {
    # Numeric-prefixed so it passes the emitter's _FEATURE_SLUG_PATTERN gate as
    # well as the local path (which has no such gate) — both surfaces then
    # produce a payload to compare.
    "mission_slug": "070-field-identity-cutover",
    "target_branch": "main",
    "mission_type": "software-dev",
    "wp_count": 3,
    "mission_id": "01JEXAMPLE0000000000000000",
    "mission_number": None,
    "friendly_name": None,
    "purpose_tldr": None,
    "purpose_context": None,
    "created_at": "2026-07-05T00:00:00+00:00",
}


def _canonical() -> dict[str, Any]:
    return build_mission_created_payload(**_FACTS)


def test_builder_default_derivation_and_wire_shape() -> None:
    payload = _canonical()
    # Titleized display-name default (space-joined slug), not the raw slug.
    assert payload["friendly_name"] == "070 field identity cutover"
    assert payload["purpose_tldr"] == "070 field identity cutover"
    # mission_number None is wire-required -> kept.
    assert payload["mission_number"] is None
    # mission_id present passes through.
    assert payload["mission_id"] == _FACTS["mission_id"]
    # mission_id None is dropped from the wire payload.
    dropped = build_mission_created_payload(**{**_FACTS, "mission_id": None})
    assert "mission_id" not in dropped


def test_local_lifecycle_payload_matches_canonical(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / _FACTS["mission_slug"]
    feature_dir.mkdir(parents=True)

    emit_mission_created_local(
        feature_dir,
        mission_slug=_FACTS["mission_slug"],
        mission_id=_FACTS["mission_id"],
        mission_number=_FACTS["mission_number"],
        mission_type=_FACTS["mission_type"],
        target_branch=_FACTS["target_branch"],
        wp_count=_FACTS["wp_count"],
        created_at=_FACTS["created_at"],
    )

    log = feature_dir / "status.events.jsonl"
    rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
    mission_created = [r for r in rows if r.get("event_type") == "MissionCreated"]
    assert len(mission_created) == 1
    assert mission_created[0]["payload"] == _canonical()


def test_emitter_payload_matches_canonical(
    temp_queue: Any, temp_clock: Any, mock_config: Any, mock_identity: Any, mock_auth: Any
) -> None:
    del mock_auth  # side-effect-only fixture
    from specify_cli.sync.git_metadata import GitMetadata, GitMetadataResolver

    resolver = MagicMock(spec=GitMetadataResolver)
    resolver.resolve.return_value = GitMetadata()

    emitter = EventEmitter(
        clock=temp_clock,
        config=mock_config,
        queue=temp_queue,
        ws_client=None,
        _identity=mock_identity,
        _git_resolver=resolver,
    )
    event = emitter.emit_mission_created(
        _FACTS["mission_slug"],
        _FACTS["mission_number"],
        _FACTS["target_branch"],
        _FACTS["wp_count"],
        mission_type=_FACTS["mission_type"],
        mission_id=_FACTS["mission_id"],
        created_at=_FACTS["created_at"],
    )
    assert event is not None
    assert event["payload"] == _canonical()
