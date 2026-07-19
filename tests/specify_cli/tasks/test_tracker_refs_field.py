"""Tests for T040 / FR-011 (F-10): tracker_refs field on WPMetadata.

Covers:
- Backward compatibility — WP frontmatter without ``tracker_refs`` still loads.
- Field present and populated round-trips correctly.
- Legacy scalar-string form is normalised to a list.
- ``map-requirements --tracker-ref '#1298' --wp WP01`` persists into the
  event-sourced snapshot (tracker_refs is evicted from frontmatter; #2684).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]


from specify_cli.frontmatter import write_frontmatter
from specify_cli.status.wp_metadata import WPMetadata, read_wp_frontmatter


def _make_wp_file(path: Path, **extra: object) -> None:
    """Create a minimal WP frontmatter file under ``path``."""
    body = "## Activity Log\n"
    fm: dict[str, object] = {
        "work_package_id": "WP01",
        "title": "test wp",
        "dependencies": [],
        **extra,
    }
    write_frontmatter(path, fm, body)


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_wp_without_tracker_refs_loads(self, tmp_path: Path) -> None:
        wp_file = tmp_path / "WP01.md"
        _make_wp_file(wp_file)

        meta, _ = read_wp_frontmatter(wp_file)

        assert meta.work_package_id == "WP01"
        # Default factory ⇒ empty list, NOT None.
        assert meta.tracker_refs == []

    def test_default_via_constructor(self) -> None:
        meta = WPMetadata(work_package_id="WP02")
        assert meta.tracker_refs == []


# ---------------------------------------------------------------------------
# Field accepted and persisted
# ---------------------------------------------------------------------------


class TestTrackerRefsField:
    def test_field_populated_loads(self, tmp_path: Path) -> None:
        wp_file = tmp_path / "WP01.md"
        _make_wp_file(wp_file, tracker_refs=["#1298", "JIRA-123"])

        meta, _ = read_wp_frontmatter(wp_file)

        assert meta.tracker_refs == ["#1298", "JIRA-123"]

    def test_legacy_scalar_string_normalised(self, tmp_path: Path) -> None:
        """Older WPs may have stored tracker_refs as a comma-separated string."""
        meta = WPMetadata.model_validate(
            {
                "work_package_id": "WP03",
                "tracker_refs": "#1298, JIRA-123",
            }
        )
        assert meta.tracker_refs == ["#1298", "JIRA-123"]

    def test_update_preserves_other_fields(self) -> None:
        meta = WPMetadata(
            work_package_id="WP04",
            requirement_refs=["FR-001"],
        )
        updated = meta.update(tracker_refs=["#42"])
        assert updated.tracker_refs == ["#42"]
        assert updated.requirement_refs == ["FR-001"]
        # original is immutable
        assert meta.tracker_refs == []


# ---------------------------------------------------------------------------
# map-requirements CLI persists --tracker-ref
# ---------------------------------------------------------------------------


def _make_mission_repo(tmp_path: Path, mission_slug: str = "test-tracker-mission") -> Path:
    """Build a minimal mission directory layout the map-requirements command needs."""
    repo = tmp_path / "repo"
    kitty = repo / "kitty-specs" / mission_slug
    (kitty / "tasks").mkdir(parents=True)
    # Required by locate_project_root to recognise the repo as a spec-kitty project.
    (repo / ".kittify").mkdir()

    # spec.md with one requirement so refs validation passes if we ever pass --refs.
    (kitty / "spec.md").write_text(
        "# Spec\n\n## Requirements\n\n- FR-001: example\n",
        encoding="utf-8",
    )
    (kitty / "meta.json").write_text(
        '{"mission_slug": "' + mission_slug + '", "mission_id": "01TESTMISSION0000000000000"}',
        encoding="utf-8",
    )

    wp_file = kitty / "tasks" / "WP01.md"
    _make_wp_file(wp_file)

    # initialise as a git repo so locate_project_root can find it
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)

    return repo


class TestMapRequirementsTrackerRef:
    def test_persists_tracker_ref_into_frontmatter(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mission_slug = "test-tracker-mission"
        repo = _make_mission_repo(tmp_path, mission_slug)

        # Run the typer command in-process.
        from typer.testing import CliRunner

        from specify_cli.cli.commands.agent.tasks import app

        monkeypatch.chdir(repo)
        runner = CliRunner()
        # Bypass live-CI guards.
        monkeypatch.setenv("SPEC_KITTY_TEST_MODE", "1")

        result = runner.invoke(
            app,
            [
                "map-requirements",
                "--wp",
                "WP01",
                "--tracker-ref",
                "#1298",
                "--mission",
                mission_slug,
                "--no-auto-commit",
                "--json",
            ],
        )
        # #2684 re-point: ``tracker_refs`` is event-sourced, NOT a frontmatter
        # field. It was intentionally evicted from the WP frontmatter to the
        # canonical event log (WP07/T029, FR-006/FR-013); dual-homing it in
        # frontmatter is the #2093 violation the WP10 arch gate catches, so this
        # holds at flag OFF too (there is no legacy frontmatter write to restore).
        # The reducer owns the tracker_refs union, so assert on the reduced
        # snapshot's WP slot — the surface production readers consume — rather
        # than a frontmatter field.
        from specify_cli.status import read_event_stream, reduce

        feature_dir = repo / "kitty-specs" / mission_slug
        stream = read_event_stream(feature_dir)
        snapshot = reduce(stream.transitions, stream.annotations)
        wp01 = snapshot.work_packages.get("WP01", {})
        assert "#1298" in wp01.get("tracker_refs", []), (
            "--tracker-ref did not persist to the event-sourced snapshot. "
            f"CLI exit={result.exit_code} stdout={result.stdout!r} wp01={wp01!r}"
        )
