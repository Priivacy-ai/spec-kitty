"""Regression pin: `sync diagnose` consumes ProjectOutboxTask envelopes, not dicts.

The per-project cutover changed ``OfflineQueue.drain_queue`` to return
``list[ProjectOutboxTask]`` dataclasses. ``diagnose_events`` still validates
plain envelope dicts, so the command must unwrap ``task.event`` — passing the
tasks straight through raised ``AttributeError: 'ProjectOutboxTask' object has
no attribute 'get'`` on the first pending event and `sync diagnose` crashed on
every non-empty queue (found during the #3262 WP09 regularization).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.sync import app
from specify_cli.migration.envelope_seam import build_teamspace_envelope
from specify_cli.sync.layout_generation import LayoutMode
from specify_cli.sync.project_store import ProjectSyncStore
from specify_cli.sync.queue import OfflineQueue

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

PROJECT = "55555555-5555-4555-8555-555555555555"


def _envelope(event_id: str) -> dict[str, object]:
    return build_teamspace_envelope(
        event_id=event_id,
        event_type="MissionCreated",
        aggregate_id=event_id,
        aggregate_type="Mission",
        payload={
            "mission_slug": "099-diagnose-regression",
            "mission_number": None,
            "mission_type": "software-dev",
            "target_branch": "main",
            "wp_count": 1,
            "friendly_name": "Diagnose Regression",
            "purpose_tldr": "regression pin for sync diagnose outbox unwrap",
            "purpose_context": "sync diagnose must unwrap ProjectOutboxTask envelopes",
        },
        timestamp="2026-08-13T00:00:00+00:00",
        build_id="diagnose-regression-test",
        node_id="diagnose-regression-test",
        lamport_clock=1,
        project_uuid=PROJECT,
        project_slug="diagnose-regression",
        repo_slug=None,
        correlation_id=event_id,
    ).model_dump()


def _queue_one_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".kittify").mkdir(parents=True)
    (repo / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {PROJECT}\n  slug: diagnose-regression\n  node_id: node\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(repo)

    store = ProjectSyncStore(PROJECT)
    authority = store.layout_generation()
    if authority.read_state().mode is LayoutMode.LEGACY:
        authority.begin_cutover("diagnose-regression-test")
        authority.publish_project_only("diagnose-regression-test", verify_exact=lambda: True)
    with store.unit_of_work() as unit:
        queued = OfflineQueue(unit, authority).queue_event(_envelope("01K00000000000000000000001"))
    assert queued, "seeding the outbox is the test's precondition"


def test_diagnose_validates_pending_outbox_envelopes(
    canonical_home: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del canonical_home  # the ONE SPEC_KITTY_HOME owner (R1a #3121) pins the home
    _queue_one_event(monkeypatch, tmp_path)

    result = CliRunner().invoke(app, ["diagnose", "--json"])

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["total"] == 1
    assert report["valid"] == 1, report
    assert report["invalid"] == 0
