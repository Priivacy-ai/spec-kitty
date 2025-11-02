from __future__ import annotations

import os
from pathlib import Path

import pytest

import acceptance_support as acc
import task_helpers as th


def test_collect_feature_summary_reports_metadata_issue(feature_repo: Path, feature_slug: str) -> None:
    wp_path = feature_repo / "kitty-specs" / feature_slug / "tasks" / "planned" / "WP01.md"
    front, body, padding = th.split_frontmatter(wp_path.read_text(encoding="utf-8"))
    lines = [line for line in front.splitlines() if not line.startswith("assignee:")]
    wp_path.write_text(th.build_document("\n".join(lines), body, padding), encoding="utf-8")

    from tests.utils import run_tasks_cli

    run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)

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

    run_tasks_cli(["move", feature_slug, "WP01", "doing", "--force"], cwd=feature_repo)
    run(["git", "commit", "-am", "Move to doing"], cwd=feature_repo)
    run_tasks_cli(["move", feature_slug, "WP01", "done", "--force"], cwd=feature_repo)

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
