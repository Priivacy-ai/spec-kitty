"""Unit tests for reconciliation and merge coordination (WP06).

Tests tasks.md reconciliation, consistency reporting, merge coordination
heuristics, and artifact persistence.
"""

from __future__ import annotations

import json
from pathlib import Path

from specify_cli.core.change_classifier import PackagingMode
from specify_cli.core.change_stack import (
    ChangePlan,
    ChangeWorkPackage,
    ConsistencyReport,
    MergeCoordinationJob,
    _build_tasks_doc_section,
    _find_active_wps,
    _fix_broken_prompt_links,
    _parse_wp_sections,
    compute_merge_coordination_jobs,
    persist_merge_coordination_jobs,
    reconcile_change_stack,
    reconcile_tasks_doc,
    validate_all_dependencies,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_wp(
    wp_id: str = "WP09",
    title: str = "Fix caching",
    filename: str = "WP09-fix-caching.md",
    change_mode: str = "single",
    dependencies: list[str] | None = None,
    closed_reference_links: list[str] | None = None,
    change_request_id: str = "req-abc",
) -> ChangeWorkPackage:
    return ChangeWorkPackage(
        work_package_id=wp_id,
        title=title,
        filename=filename,
        lane="planned",
        dependencies=dependencies or [],
        change_stack=True,
        change_request_id=change_request_id,
        change_mode=change_mode,
        stack_rank=1,
        review_attention="normal",
        closed_reference_links=closed_reference_links or [],
        body="---\nwork_package_id: WP09\ntitle: Fix caching\nlane: planned\n---\n",
    )


def _make_plan(
    mode: PackagingMode = PackagingMode.SINGLE_WP,
    requires_merge: bool = False,
) -> ChangePlan:
    return ChangePlan(
        request_id="req-abc",
        mode=mode,
        requires_merge_coordination=requires_merge,
    )


def _create_wp_file(
    tasks_dir: Path,
    wp_id: str,
    lane: str = "planned",
    change_stack: bool = False,
    dependencies: list[str] | None = None,
    stack_rank: int = 0,
) -> None:
    """Create a WP file with minimal frontmatter."""
    tasks_dir.mkdir(parents=True, exist_ok=True)
    deps_yaml = ""
    if dependencies:
        deps_yaml = "\ndependencies:\n" + "\n".join(f'  - "{d}"' for d in dependencies)
    change_yaml = (
        f"\nchange_stack: true\nstack_rank: {stack_rank}" if change_stack else ""
    )
    slug = wp_id.lower().replace("wp", "wp-task")
    content = (
        f"---\n"
        f'work_package_id: "{wp_id}"\n'
        f'title: "Task for {wp_id}"\n'
        f'lane: "{lane}"{deps_yaml}{change_yaml}\n'
        f"---\n\n# {wp_id}\n"
    )
    (tasks_dir / f"{wp_id}-{slug}.md").write_text(content, encoding="utf-8")


# ============================================================================
# T030 - tasks.md reconciliation
# ============================================================================


class TestReconcileTasksDoc:
    """Test tasks.md insert/update with generated change WPs."""

    def test_creates_tasks_doc_when_missing(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        wp = _make_wp()
        report = reconcile_tasks_doc(tasks_dir, feature_dir, [wp])

        assert report.updated_tasks_doc
        assert report.wp_sections_added == 1
        assert (feature_dir / "tasks.md").exists()

    def test_no_change_when_empty_wps(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        report = reconcile_tasks_doc(tasks_dir, tmp_path, [])
        assert not report.updated_tasks_doc
        assert report.wp_sections_added == 0

    def test_inserts_new_section(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        # Create existing tasks.md
        (feature_dir / "tasks.md").write_text(
            "# Tasks\n\n## Existing Section\n\n- [ ] Some item\n",
            encoding="utf-8",
        )

        wp = _make_wp()
        report = reconcile_tasks_doc(tasks_dir, feature_dir, [wp])

        assert report.updated_tasks_doc
        assert report.wp_sections_added == 1
        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        assert "### WP09:" in content
        assert "Fix caching" in content

    def test_preserves_existing_content(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        (feature_dir / "tasks.md").write_text(
            "# Tasks\n\n- [x] Completed item\n- [ ] Open item\n",
            encoding="utf-8",
        )

        wp = _make_wp()
        reconcile_tasks_doc(tasks_dir, feature_dir, [wp])

        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        assert "Completed item" in content
        assert "Open item" in content

    def test_updates_existing_change_stack_section(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        (feature_dir / "tasks.md").write_text(
            "# Tasks\n\n## Change Stack Work Packages\n\n"
            "### WP09: Old title\n\n- **Lane**: planned\n",
            encoding="utf-8",
        )

        wp = _make_wp(title="Updated caching fix")
        report = reconcile_tasks_doc(tasks_dir, feature_dir, [wp])

        assert report.updated_tasks_doc
        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        assert "Updated caching fix" in content

    def test_deterministic_ordering(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        wps = [
            _make_wp(wp_id="WP11", title="Second", filename="WP11-second.md"),
            _make_wp(wp_id="WP09", title="First", filename="WP09-first.md"),
        ]

        reconcile_tasks_doc(tasks_dir, feature_dir, wps)
        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")

        # WP09 should appear before WP11 in the document
        pos_09 = content.find("WP09")
        pos_11 = content.find("WP11")
        assert pos_09 < pos_11

    def test_includes_dependencies_in_section(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        wp = _make_wp(dependencies=["WP03", "WP05"])
        reconcile_tasks_doc(tasks_dir, feature_dir, [wp])

        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        assert "WP03, WP05" in content

    def test_includes_closed_references(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        wp = _make_wp(closed_reference_links=["WP01"])
        reconcile_tasks_doc(tasks_dir, feature_dir, [wp])

        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        assert "WP01" in content
        assert "link-only" in content


class TestParseWpSections:
    def test_empty_content(self) -> None:
        result = _parse_wp_sections("")
        assert result == {}

    def test_single_section(self) -> None:
        content = "### WP09: Fix caching\n\n- **Lane**: planned\n"
        result = _parse_wp_sections(content)
        assert "WP09" in result
        assert "Fix caching" in result["WP09"]

    def test_multiple_sections(self) -> None:
        content = "### WP09: First\n\nDetails\n### WP10: Second\n\nMore details\n"
        result = _parse_wp_sections(content)
        assert "WP09" in result
        assert "WP10" in result


class TestBuildTasksDocSection:
    def test_basic_section(self) -> None:
        wp = _make_wp()
        section = _build_tasks_doc_section(wp)
        assert "### WP09:" in section
        assert "Fix caching" in section
        assert "Change Stack" in section
        assert "single" in section

    def test_section_with_deps(self) -> None:
        wp = _make_wp(dependencies=["WP03"])
        section = _build_tasks_doc_section(wp)
        assert "WP03" in section
        assert "Dependencies" in section


# ============================================================================
# T031 - Consistency report
# ============================================================================


class TestConsistencyReport:
    def test_default_values(self) -> None:
        report = ConsistencyReport()
        assert not report.updated_tasks_doc
        assert report.dependency_validation_passed
        assert report.broken_links_fixed == 0
        assert report.issues == []

    def test_to_dict_has_all_fields(self) -> None:
        report = ConsistencyReport(
            updated_tasks_doc=True,
            broken_links_fixed=2,
            issues=["broken ref"],
        )
        d = report.to_dict()
        assert d["updatedTasksDoc"] is True
        assert d["brokenLinksFixed"] == 2
        assert "broken ref" in d["issues"]
        assert "wpSectionsAdded" in d
        assert "wpSectionsUpdated" in d

    def test_json_serializable(self) -> None:
        report = ConsistencyReport(issues=["test"])
        # Should not raise
        json.dumps(report.to_dict())


class TestValidateAllDependencies:
    def test_empty_dir(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        is_valid, errors = validate_all_dependencies(tasks_dir)
        assert is_valid
        assert errors == []

    def test_valid_dependencies(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="done")
        _create_wp_file(tasks_dir, "WP02", dependencies=["WP01"])

        is_valid, errors = validate_all_dependencies(tasks_dir)
        assert is_valid
        assert errors == []

    def test_detects_missing_reference(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", dependencies=["WP99"])

        is_valid, errors = validate_all_dependencies(tasks_dir)
        assert not is_valid
        assert any("WP99" in e for e in errors)


class TestReconcileChangeStack:
    def test_full_reconciliation(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        wp = _make_wp()
        report = reconcile_change_stack(tasks_dir, feature_dir, [wp])

        assert report.updated_tasks_doc
        assert report.dependency_validation_passed

    def test_idempotent_on_repeated_runs(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        wp = _make_wp()
        report1 = reconcile_change_stack(tasks_dir, feature_dir, [wp])
        report2 = reconcile_change_stack(tasks_dir, feature_dir, [wp])

        # Both should succeed
        assert report1.updated_tasks_doc
        assert report2.updated_tasks_doc

    def test_reports_broken_links(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        # Create tasks.md with a broken link
        (feature_dir / "tasks.md").write_text(
            "# Tasks\n\n**Prompt**: `tasks/WP99-nonexistent.md`\n",
            encoding="utf-8",
        )

        report = reconcile_change_stack(tasks_dir, feature_dir, [])
        assert report.broken_links_fixed == 1


class TestFixBrokenPromptLinks:
    def test_no_broken_links(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        # Create a WP file
        (tasks_dir / "WP01-setup.md").write_text("---\n---\n", encoding="utf-8")
        (feature_dir / "tasks.md").write_text(
            "**Prompt**: `tasks/WP01-setup.md`\n",
            encoding="utf-8",
        )

        count = _fix_broken_prompt_links(tasks_dir, feature_dir)
        assert count == 0
        # Content should be unchanged
        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        assert "`tasks/WP01-setup.md`" in content

    def test_fixes_broken_link_by_removing_line(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        (feature_dir / "tasks.md").write_text(
            "# Tasks\n\n**Prompt**: `tasks/WP99-missing.md`\n\nOther content\n",
            encoding="utf-8",
        )

        count = _fix_broken_prompt_links(tasks_dir, feature_dir)
        assert count == 1
        # Verify the broken link line was actually removed from the file
        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        assert "`tasks/WP99-missing.md`" not in content
        assert "Other content" in content
        assert "# Tasks" in content

    def test_preserves_valid_links_while_removing_broken(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        feature_dir = tmp_path

        (tasks_dir / "WP01-setup.md").write_text("---\n---\n", encoding="utf-8")
        (feature_dir / "tasks.md").write_text(
            "**Prompt**: `tasks/WP01-setup.md`\n**Prompt**: `tasks/WP99-missing.md`\n",
            encoding="utf-8",
        )

        count = _fix_broken_prompt_links(tasks_dir, feature_dir)
        assert count == 1
        content = (feature_dir / "tasks.md").read_text(encoding="utf-8")
        assert "`tasks/WP01-setup.md`" in content
        assert "`tasks/WP99-missing.md`" not in content


# ============================================================================
# T032 - Merge coordination heuristics
# ============================================================================


class TestComputeMergeCoordinationJobs:
    def test_no_jobs_without_risk(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        wp = _make_wp()
        plan = _make_plan()
        jobs = compute_merge_coordination_jobs([wp], tasks_dir, plan)

        # No integration risk, no cross-dep, single WP -> no jobs
        assert jobs == []

    def test_integration_risk_triggers_job(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP03", lane="doing")

        wp = _make_wp()
        plan = _make_plan(requires_merge=True)
        jobs = compute_merge_coordination_jobs([wp], tasks_dir, plan)

        assert len(jobs) >= 1
        integration_jobs = [j for j in jobs if j.risk_indicator == "integration_risk"]
        assert len(integration_jobs) == 1
        assert "WP03" in integration_jobs[0].target_wps

    def test_no_integration_job_without_active_wps(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        wp = _make_wp()
        plan = _make_plan(requires_merge=True)
        jobs = compute_merge_coordination_jobs([wp], tasks_dir, plan)

        integration_jobs = [j for j in jobs if j.risk_indicator == "integration_risk"]
        assert len(integration_jobs) == 0

    def test_cross_dependency_triggers_job(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP03", lane="doing")

        wp = _make_wp(dependencies=["WP03"])
        plan = _make_plan()
        jobs = compute_merge_coordination_jobs([wp], tasks_dir, plan)

        cross_jobs = [j for j in jobs if j.risk_indicator == "cross_dependency"]
        assert len(cross_jobs) == 1
        assert cross_jobs[0].target_wps == ["WP03"]

    def test_no_cross_dep_when_target_planned(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP03", lane="planned")

        wp = _make_wp(dependencies=["WP03"])
        plan = _make_plan()
        jobs = compute_merge_coordination_jobs([wp], tasks_dir, plan)

        cross_jobs = [j for j in jobs if j.risk_indicator == "cross_dependency"]
        assert len(cross_jobs) == 0

    def test_parallel_modification_for_multi_wps(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        wps = [
            _make_wp(wp_id="WP09", filename="WP09-a.md"),
            _make_wp(wp_id="WP10", filename="WP10-b.md"),
        ]
        plan = _make_plan()
        jobs = compute_merge_coordination_jobs(wps, tasks_dir, plan)

        parallel_jobs = [j for j in jobs if j.risk_indicator == "parallel_modification"]
        assert len(parallel_jobs) == 1
        assert "WP10" in parallel_jobs[0].target_wps

    def test_no_parallel_for_single_wp(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        wps = [_make_wp()]
        plan = _make_plan()
        jobs = compute_merge_coordination_jobs(wps, tasks_dir, plan)

        parallel_jobs = [j for j in jobs if j.risk_indicator == "parallel_modification"]
        assert len(parallel_jobs) == 0

    def test_empty_wps_returns_no_jobs(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        plan = _make_plan()
        jobs = compute_merge_coordination_jobs([], tasks_dir, plan)
        assert jobs == []


class TestFindActiveWps:
    def test_empty_dir(self, tmp_path: Path) -> None:
        assert _find_active_wps(tmp_path / "nonexistent") == []

    def test_finds_doing_wps(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="doing")
        _create_wp_file(tasks_dir, "WP02", lane="planned")

        active = _find_active_wps(tasks_dir)
        assert active == ["WP01"]

    def test_finds_for_review_wps(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        _create_wp_file(tasks_dir, "WP01", lane="for_review")

        active = _find_active_wps(tasks_dir)
        assert active == ["WP01"]


# ============================================================================
# T033 - Persist merge coordination artifacts
# ============================================================================


class TestPersistMergeCoordinationJobs:
    def test_no_jobs_returns_none(self, tmp_path: Path) -> None:
        result = persist_merge_coordination_jobs([], tmp_path)
        assert result is None

    def test_creates_json_file(self, tmp_path: Path) -> None:
        job = MergeCoordinationJob(
            job_id="mcj-WP09-integration",
            reason="Integration risk",
            source_wp="WP09",
            target_wps=["WP03"],
            risk_indicator="integration_risk",
        )
        path = persist_merge_coordination_jobs([job], tmp_path)

        assert path is not None
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["version"] == 1
        assert data["jobCount"] == 1
        assert data["jobs"][0]["jobId"] == "mcj-WP09-integration"

    def test_idempotent_merge(self, tmp_path: Path) -> None:
        job1 = MergeCoordinationJob(
            job_id="mcj-1",
            reason="First",
            source_wp="WP09",
        )
        job2 = MergeCoordinationJob(
            job_id="mcj-2",
            reason="Second",
            source_wp="WP10",
        )

        persist_merge_coordination_jobs([job1], tmp_path)
        persist_merge_coordination_jobs([job2], tmp_path)

        path = tmp_path / "change-merge-jobs.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["jobCount"] == 2

    def test_updates_existing_job(self, tmp_path: Path) -> None:
        job_v1 = MergeCoordinationJob(
            job_id="mcj-1",
            reason="Original",
            source_wp="WP09",
        )
        job_v2 = MergeCoordinationJob(
            job_id="mcj-1",
            reason="Updated",
            source_wp="WP09",
        )

        persist_merge_coordination_jobs([job_v1], tmp_path)
        persist_merge_coordination_jobs([job_v2], tmp_path)

        path = tmp_path / "change-merge-jobs.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["jobCount"] == 1
        assert data["jobs"][0]["reason"] == "Updated"

    def test_deterministic_order(self, tmp_path: Path) -> None:
        jobs = [
            MergeCoordinationJob(job_id="mcj-b", reason="B", source_wp="WP10"),
            MergeCoordinationJob(job_id="mcj-a", reason="A", source_wp="WP09"),
        ]

        persist_merge_coordination_jobs(jobs, tmp_path)

        path = tmp_path / "change-merge-jobs.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["jobs"][0]["jobId"] == "mcj-a"
        assert data["jobs"][1]["jobId"] == "mcj-b"


class TestMergeCoordinationJobSerialization:
    def test_to_dict(self) -> None:
        job = MergeCoordinationJob(
            job_id="mcj-1",
            reason="Test reason",
            source_wp="WP09",
            target_wps=["WP03", "WP05"],
            risk_indicator="cross_dependency",
        )
        d = job.to_dict()
        assert d["jobId"] == "mcj-1"
        assert d["reason"] == "Test reason"
        assert d["sourceWP"] == "WP09"
        assert d["targetWPs"] == ["WP03", "WP05"]
        assert d["riskIndicator"] == "cross_dependency"

    def test_json_serializable(self) -> None:
        job = MergeCoordinationJob(
            job_id="mcj-1",
            reason="Test",
            source_wp="WP09",
        )
        json.dumps(job.to_dict())
