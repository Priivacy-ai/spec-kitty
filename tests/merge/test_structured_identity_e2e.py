"""End-to-end integration for the structured identity pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.frontmatter import FrontmatterManager
from specify_cli.identity import ActorIdentity, parse_agent_identity
from specify_cli.status.emit import emit_status_transition
from specify_cli.status.store import read_events

pytestmark = pytest.mark.fast


def test_structured_identity_flows_from_frontmatter_to_event_log(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    feature_dir = repo_root / "kitty-specs" / "048-test-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    wp_path = tasks_dir / "WP01.md"
    actor = parse_agent_identity(agent="claude:opus-4:implementer:implementer")
    assert actor is not None

    manager = FrontmatterManager()
    manager.write(
        wp_path,
        {
            "work_package_id": "WP01",
            "title": "Structured identity pipeline",
            "lane": "planned",
            "dependencies": [],
            "agent": actor,
        },
        "# WP01\n",
    )

    frontmatter, _ = manager.read(wp_path)
    assert frontmatter["agent"] == {
        "tool": "claude",
        "model": "opus-4",
        "profile": "implementer",
        "role": "implementer",
    }

    event = emit_status_transition(
        feature_dir=feature_dir,
        feature_slug="048-test-feature",
        wp_id="WP01",
        to_lane="claimed",
        actor=actor,
        repo_root=repo_root,
    )

    assert isinstance(event.actor, ActorIdentity)
    assert event.actor.tool == "claude"
    assert event.actor.model == "opus-4"
    assert event.actor.profile == "implementer"
    assert event.actor.role == "implementer"

    events = read_events(feature_dir)
    assert len(events) == 1
    assert events[0].actor == actor
