"""Unit tests for merge-time hollow review warnings."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.cli.commands.merge import (
    _collect_hollow_review_warnings,
    _warn_or_confirm_hollow_reviews,
)
from specify_cli.status.lifecycle_events import REVIEWER_SELF_APPROVAL

pytestmark = pytest.mark.fast


def test_collect_hollow_review_warnings_reads_force_count_and_self_approval(tmp_path: Path) -> None:
    feature_dir = tmp_path / "kitty-specs" / "034-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "status.json").write_text(
        json.dumps({"work_packages": {"WP01": {"force_count": 3}, "WP02": {"force_count": 0}}}),
        encoding="utf-8",
    )
    event = {
        "event_id": "evt-reviewer-self-approval",
        "event_type": REVIEWER_SELF_APPROVAL,
        "aggregate_id": "WP02",
        "payload": {
            "wp_id": "WP02",
            "implementing_actor": "codex",
            "intended_reviewer": "claude",
            "failure_reason": "exit 1",
        },
    }
    (feature_dir / "status.events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")

    warnings = _collect_hollow_review_warnings(feature_dir, ["WP01", "WP02", "WP03"])

    assert warnings["WP01"] == ["force_count=3"]
    assert warnings["WP02"] == ["ReviewerSelfApproval (claude failed: exit 1; codex self-reviewed)"]
    assert "WP03" not in warnings


def test_warn_or_confirm_hollow_reviews_assume_yes_does_not_prompt(tmp_path: Path, capsys) -> None:
    feature_dir = tmp_path / "kitty-specs" / "034-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "status.json").write_text(
        json.dumps({"work_packages": {"WP01": {"force_count": 2}}}),
        encoding="utf-8",
    )

    _warn_or_confirm_hollow_reviews(feature_dir=feature_dir, wp_ids=["WP01"], assume_yes=True)

    out = capsys.readouterr().out
    assert "Hollow reviews detected" in out
    assert "Proceeding without interactive confirmation" in out
