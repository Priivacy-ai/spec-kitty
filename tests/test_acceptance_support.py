from __future__ import annotations

import os
from pathlib import Path

import pytest

import acceptance_support as acc
import task_helpers as th


def test_collect_feature_summary_reports_metadata_issue(feature_repo: Path, feature_slug: str) -> None:
    # WP files now live in flat tasks/ directory
    wp_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "WP01.md"
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    from tests.utils import run_tasks_cli

    # Use 'update' command (renamed from 'move')
    run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)

    summary = acc.collect_feature_summary(feature_repo, feature_slug)
    assert any("missing assignee" in issue for issue in summary.metadata_issues)


def test_detect_feature_slug_prefers_env(feature_repo: Path, feature_slug: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPECIFY_FEATURE", "999-from-env")
    assert acc.detect_feature_slug(feature_repo) == "999-from-env"


def test_detect_feature_slug_from_branch(feature_repo: Path, feature_slug: str) -> None:
    cwd_before = Path.cwd()
    os.chdir(feature_repo)
    try:
        acc.run_git(["checkout", "-b", feature_slug], cwd=feature_repo)
        os.environ.pop("SPECIFY_FEATURE", None)
        assert acc.detect_feature_slug(feature_repo) == feature_slug
    finally:
        os.chdir(cwd_before)


def test_perform_acceptance_without_commit(feature_repo: Path, feature_slug: str) -> None:
    from tests.utils import run_tasks_cli

    from tests.utils import run

    # Use 'update' command (renamed from 'move')
    run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)
    run_tasks_cli(["update", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)

    summary = acc.collect_feature_summary(feature_repo, feature_slug, strict_metadata=True)
    assert summary.lanes["planned"] == []
    assert summary.lanes["doing"] == []
    assert summary.lanes["for_review"] == []
    assert summary.metadata_issues == []
    assert summary.activity_issues == []

    result = acc.perform_acceptance(summary, mode="checklist", actor="Tester", auto_commit=False)
    payload = result.to_dict()
    assert payload["accepted_by"] == "Tester"
    assert payload["mode"] == "checklist"


def test_collect_feature_summary_encoding_error(feature_repo: Path, feature_slug: str) -> None:
    plan_path = feature_repo / "kitty-specs" / feature_slug / "plan.md"
    data = plan_path.read_bytes() + b"\x92"
    plan_path.write_bytes(data)

    with pytest.raises(acc.ArtifactEncodingError) as excinfo:
        acc.collect_feature_summary(feature_repo, feature_slug)

    assert str(plan_path) in str(excinfo.value)


def test_normalize_feature_encoding(feature_repo: Path, feature_slug: str) -> None:
    plan_path = feature_repo / "kitty-specs" / feature_slug / "plan.md"
    data = plan_path.read_bytes() + b"\x92"
    plan_path.write_bytes(data)

    cleaned = acc.normalize_feature_encoding(feature_repo, feature_slug)
    assert plan_path in cleaned
    # Should now be readable as UTF-8 without errors.
    plan_path.read_text(encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, feature_slug)
    assert summary.feature == feature_slug


# T039: Test that done WPs don't require assignee (Bug #119)
def test_acceptance_succeeds_for_done_wp_without_assignee(feature_repo: Path, feature_slug: str) -> None:
    """Done WPs should not require assignee."""
    from tests.utils import run_tasks_cli, run

    # Move WP01 to done without assignee
    wp_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "WP01.md"
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    # Move to doing first (will fail without assignee - that's expected)
    run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Update to doing"], cwd=feature_repo)

    # Move to done
    run_tasks_cli(["update", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)

    # Verify that collection succeeds without metadata issues for missing assignee
    summary = acc.collect_feature_summary(feature_repo, feature_slug, strict_metadata=True)
    # Should NOT report missing assignee for done WP
    assert not any("missing assignee" in issue for issue in summary.metadata_issues), \
        f"Done WP should not require assignee, but got: {summary.metadata_issues}"


# T040: Test strict check still works for active WPs (doing and for_review)
def test_assignee_still_required_for_doing_and_for_review(feature_repo: Path, feature_slug: str) -> None:
    """Assignee should still be required for doing and for_review lanes."""
    from tests.utils import run_tasks_cli

    wp_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "WP01.md"
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    # Test "doing" lane
    run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    summary = acc.collect_feature_summary(feature_repo, feature_slug, strict_metadata=True)
    assert any("missing assignee" in issue for issue in summary.metadata_issues), \
        "Doing lane should still require assignee"

    # Test "for_review" lane
    run_tasks_cli(["update", feature_slug, "WP01", "for_review", "--force"], cwd=feature_repo)
    summary = acc.collect_feature_summary(feature_repo, feature_slug, strict_metadata=True)
    assert any("missing assignee" in issue for issue in summary.metadata_issues), \
        "For_review lane should still require assignee"


# T041: Test required fields still enforced for all lanes
def test_required_fields_still_enforced(feature_repo: Path, feature_slug: str) -> None:
    """Lane, agent, and shell_pid should still be required for all lanes."""
    from tests.utils import run_tasks_cli, run

    wp_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "WP01.md"

    # Test missing lane
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines_no_lane = [line for line in front.splitlines() if not line.startswith("lane:")]
    wp_path.write_text(th.build_document("\n".join(lines_no_lane), body, padding), encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, feature_slug, strict_metadata=True)
    assert any("missing lane" in issue for issue in summary.metadata_issues), \
        "Lane should still be required"

    # Test missing agent - move to doing first, then remove agent field manually
    front_orig = wp_path.read_text(encoding="utf-8")
    run_tasks_cli(["update", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)

    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines_no_agent = [line for line in front.splitlines() if not line.startswith("agent:")]
    wp_path.write_text(th.build_document("\n".join(lines_no_agent), body, padding), encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, feature_slug, strict_metadata=True)
    assert any("missing agent" in issue for issue in summary.metadata_issues), \
        "Agent should still be required"

    # Test missing shell_pid - restore agent, remove shell_pid
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines_with_agent = front.splitlines()
    if not any(line.startswith("agent:") for line in lines_with_agent):
        lines_with_agent.insert(0, "agent: test-agent")
    lines_no_pid = [line for line in lines_with_agent if not line.startswith("shell_pid:")]
    wp_path.write_text(th.build_document("\n".join(lines_no_pid), body, padding), encoding="utf-8")
    summary = acc.collect_feature_summary(feature_repo, feature_slug, strict_metadata=True)
    assert any("missing shell_pid" in issue for issue in summary.metadata_issues), \
        "Shell_pid should still be required"
