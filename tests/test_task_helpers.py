from __future__ import annotations

from pathlib import Path


import task_helpers as th


def test_set_scalar_inserts_and_updates() -> None:
    original = 'agent: "system"\n'
    updated = th.set_scalar(original, "lane", "planned")
    assert 'lane: "planned"' in updated

    replaced = th.set_scalar(updated, "lane", "doing")
    assert 'lane: "doing"' in replaced
    assert replaced.count("lane:") == 1


def test_split_frontmatter_handles_padding() -> None:
    text = "---\nkey: value\n---\n\nBody text\n"
    front, body, padding = th.split_frontmatter(text)
    assert front.strip() == "key: value"
    assert body.strip() == "Body text"
    assert padding == "\n\n"


def test_append_activity_log_creates_section() -> None:
    entry = "- 2025-01-01T00:00:00Z – system – shell_pid=1 – lane=planned – Created"
    body = th.append_activity_log("", entry)
    assert "## Activity Log" in body
    assert entry in body

    second = th.append_activity_log(body, "- 2025-01-02T00:00:00Z – agent – shell_pid=2 – lane=doing – Moved")
    assert second.count("Activity Log") == 1
    assert "lane=doing" in second


def test_detect_conflicting_wp_status() -> None:
    status_lines = [
        " M kitty-specs/001-demo/tasks/planned/WP01.md",
        " M kitty-specs/001-demo/tasks/doing/WP02.md",
        "?? README.md",
    ]
    conflicts = th.detect_conflicting_wp_status(
        status_lines,
        "001-demo",
        Path("kitty-specs/001-demo/tasks/planned/WP01.md"),
        Path("kitty-specs/001-demo/tasks/doing/WP01.md"),
    )
    assert conflicts == [" M kitty-specs/001-demo/tasks/doing/WP02.md"]


def test_locate_work_package(feature_repo: Path, feature_slug: str) -> None:
    th.ensure_lane("planned")  # smoke call
    path = th.locate_work_package(feature_repo, feature_slug, "WP01")
    assert path.work_package_id == "WP01"
    assert path.current_lane == "planned"


def test_locate_work_package_exact_match(feature_repo: Path, feature_slug: str) -> None:
    """Test that WP04 doesn't match WP04b - exact ID matching is required."""
    from tests.utils import write_wp

    # Create WP04 and WP04b in the same lane
    write_wp(feature_repo, feature_slug, "planned", "WP04")
    write_wp(feature_repo, feature_slug, "planned", "WP04b")

    # Looking for WP04 should NOT match WP04b
    wp = th.locate_work_package(feature_repo, feature_slug, "WP04")
    assert wp.work_package_id == "WP04"

    # Looking for WP04b should NOT match WP04
    wp_b = th.locate_work_package(feature_repo, feature_slug, "WP04b")
    assert wp_b.work_package_id == "WP04b"

    # Ensure they are different files
    assert wp.path != wp_b.path
