"""Fast agent-shard coverage for agent_utils status warnings."""

from __future__ import annotations

import json
import textwrap
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from specify_cli.agent_utils.status import show_kanban_status

pytestmark = pytest.mark.fast


def _write_project_root(project: Path) -> None:
    kittify = project / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("version: 1\n", encoding="utf-8")


def _write_meta(feature_dir: Path, mission_slug: str) -> None:
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "mission_slug": mission_slug,
                "mission_number": "080",
                "mission_type": "software-dev",
                "phase": 2,
            }
        ),
        encoding="utf-8",
    )


def _write_wp(tasks_dir: Path, wp_id: str, title: str) -> Path:
    tasks_dir.mkdir(parents=True, exist_ok=True)
    wp_file = tasks_dir / f"{wp_id}-stub.md"
    wp_file.write_text(
        textwrap.dedent(
            f"""\
            ---
            work_package_id: {wp_id}
            title: '{title}'
            ---
            # {wp_id}: {title}
            """
        ),
        encoding="utf-8",
    )
    return wp_file


def _write_events(feature_dir: Path, events: list[dict]) -> None:
    (feature_dir / "status.events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )


def _event(
    mission_slug: str,
    wp_id: str,
    to_lane: str,
    *,
    at: str,
    from_lane: str = "planned",
) -> dict:
    return {
        "event_id": "01HXYZ0000000000000000TEST",
        "at": at,
        "feature_slug": mission_slug,
        "wp_id": wp_id,
        "from_lane": from_lane,
        "to_lane": to_lane,
        "actor": "test",
        "force": True,
        "reason": None,
        "evidence": None,
        "review_ref": None,
        "execution_mode": "worktree",
    }


def _patch_project(monkeypatch: pytest.MonkeyPatch, project: Path) -> None:
    monkeypatch.chdir(project)
    monkeypatch.setattr("specify_cli.agent_utils.status.locate_project_root", lambda cwd: project)
    monkeypatch.setattr("specify_cli.agent_utils.status.get_main_repo_root", lambda repo_root: project)


def test_show_kanban_status_reports_rejected_artifact_under_wp_slug_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approved/done WPs warn on rejected review artifacts in tasks/<WP-slug>/."""
    mission_slug = "test-stale-verdict"
    _write_project_root(tmp_path)
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    _write_meta(feature_dir, mission_slug)
    wp_file = _write_wp(tasks_dir, "WP01", "Done work")

    wp_artifact_dir = tasks_dir / wp_file.stem
    wp_artifact_dir.mkdir()
    (wp_artifact_dir / "review-cycle-1.md").write_text(
        "---\nverdict: rejected\n---\n# Review\n",
        encoding="utf-8",
    )
    _write_events(
        feature_dir,
        [
            _event(
                mission_slug,
                "WP01",
                "done",
                from_lane="approved",
                at="2026-01-01T00:00:00+00:00",
            )
        ],
    )
    _patch_project(monkeypatch, tmp_path)

    result = show_kanban_status(mission_slug)

    assert "error" not in result
    assert result["stale_verdicts"] == [
        {"wp_id": "WP01", "artifact": "review artifact: verdict=rejected"}
    ]


def test_show_kanban_status_reports_stalled_in_review_wp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In-review WPs older than the configured threshold are flagged as stalled."""
    mission_slug = "test-stalled-review"
    _write_project_root(tmp_path)
    feature_dir = tmp_path / "kitty-specs" / mission_slug
    tasks_dir = feature_dir / "tasks"
    _write_meta(feature_dir, mission_slug)
    _write_wp(tasks_dir, "WP01", "Review work")

    fake_now = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)
    event_time = fake_now - timedelta(minutes=45)
    _write_events(
        feature_dir,
        [
            _event(
                mission_slug,
                "WP01",
                "in_review",
                from_lane="for_review",
                at=event_time.isoformat(),
            )
        ],
    )
    _patch_project(monkeypatch, tmp_path)

    import specify_cli.agent_utils.status as status_mod

    monkeypatch.setattr(status_mod, "datetime", _FakeDatetime(fake_now))

    result = show_kanban_status(mission_slug)

    assert "error" not in result
    assert result["stalled_wps"] == [
        {"wp_id": "WP01", "age_minutes": 45, "mission_slug": mission_slug}
    ]


class _FakeDatetime:
    """Fake datetime replacement that returns a fixed now."""

    def __init__(self, fixed_now: datetime) -> None:
        self._now = fixed_now

    def now(self, tz: timezone | None = None) -> datetime:
        if tz is not None:
            return self._now.astimezone(tz)
        return self._now

    def fromisoformat(self, value: str) -> datetime:
        return datetime.fromisoformat(value)
