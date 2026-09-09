"""Main-push CI reaches the fleet through the reporter's existing CLI entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts.ci import fleet_verdict
from tests.ci.test_fleet_verdict import API, IDS, REPO

pytestmark = pytest.mark.fast


def test_main_push_event_selects_main_reporting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = API()
    source = api.runs["ci-modules.yml"][0]
    source.update(event="push", head_branch="main", pull_requests=[])
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"workflow_run": source}))
    output = tmp_path / "output"
    output.touch()
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(fleet_verdict, "GitHub", lambda repository: api)
    monkeypatch.setattr(sys, "argv", ["fleet_verdict.py", "--event", str(event), "--repository", REPO, "--reporter-id", "123", "--attempt", "1"])

    fleet_verdict.main()

    assert "main=true\n" in output.read_text()
    assert IDS["ci-modules.yml"] == source["workflow_id"]
    assert not api.posts
