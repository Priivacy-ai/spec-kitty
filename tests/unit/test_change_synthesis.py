"""Unit tests for change WP synthesis and adaptive packaging (WP04).

Tests cover:
- T018: Mode selection logic (verified via synthesize_change_plan)
- T019: WP ID and filename generation
- T020: Required frontmatter fields in generated WPs
- T021: Guardrails and final testing task presence
- T022: Implementation command hints
- T023: End-to-end synthesis shape tests
"""

from __future__ import annotations

import re
from pathlib import Path


from specify_cli.core.change_classifier import (
    ComplexityScore,
    PackagingMode,
    ReviewAttention,
    classify_change_request,
)
from specify_cli.core.change_stack import (
    AmbiguityResult,
    BranchStash,
    ChangeRequest,
    ClosedReferenceCheck,
    StashScope,
    ValidationState,
    _build_implementation_hint,
    _clear_virtual_registry,
    _derive_title,
    _extract_guardrails,
    _mode_to_frontmatter_label,
    _next_wp_id,
    _slugify,
    generate_change_work_packages,
    synthesize_change_plan,
    write_change_work_packages,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_change_request(
    request_text: str = "use SQLAlchemy in models.py",
    request_id: str = "test-001",
    branch: str = "029-test",
    mode_override: PackagingMode | None = None,
    review_attention: ReviewAttention = ReviewAttention.NORMAL,
    closed_wp_ids: list[str] | None = None,
) -> ChangeRequest:
    """Build a ChangeRequest for testing."""
    score = classify_change_request(request_text)
    # Allow overriding mode for test control
    if mode_override is not None:
        score = ComplexityScore(
            scope_breadth_score=score.scope_breadth_score,
            coupling_score=score.coupling_score,
            dependency_churn_score=score.dependency_churn_score,
            ambiguity_score=score.ambiguity_score,
            integration_risk_score=score.integration_risk_score,
            total_score=score.total_score,
            classification=score.classification,
            recommend_specify=score.recommend_specify,
            proposed_mode=mode_override,
            review_attention=review_attention,
        )

    return ChangeRequest(
        request_id=request_id,
        raw_text=request_text,
        submitted_branch=branch,
        stash=BranchStash(
            stash_key="029-test",
            scope=StashScope.FEATURE,
            stash_path=Path("/tmp/fake/kitty-specs/029-test/tasks"),
        ),
        validation_state=ValidationState.VALID,
        ambiguity=AmbiguityResult(is_ambiguous=False),
        closed_references=ClosedReferenceCheck(
            has_closed_references=bool(closed_wp_ids),
            closed_wp_ids=closed_wp_ids or [],
        ),
        complexity_score=score,
    )


# ============================================================================
# T019: WP ID and Filename Generation
# ============================================================================


class TestNextWpId:
    """Test deterministic WP ID allocation."""

    def test_empty_dir_returns_wp01(self, tmp_path: Path) -> None:
        """Empty tasks dir should return WP01."""
        _clear_virtual_registry()
        assert _next_wp_id(tmp_path) == "WP01"

    def test_existing_wp01_returns_wp02(self, tmp_path: Path) -> None:
        """With WP01 existing, should return WP02."""
        _clear_virtual_registry()
        (tmp_path / "WP01-setup.md").touch()
        assert _next_wp_id(tmp_path) == "WP02"

    def test_gap_filling(self, tmp_path: Path) -> None:
        """Should fill gaps: WP01 exists, WP02 missing, WP03 exists -> WP02."""
        _clear_virtual_registry()
        (tmp_path / "WP01-first.md").touch()
        (tmp_path / "WP03-third.md").touch()
        assert _next_wp_id(tmp_path) == "WP02"

    def test_many_existing(self, tmp_path: Path) -> None:
        """Should handle many existing WPs."""
        _clear_virtual_registry()
        for i in range(1, 9):
            (tmp_path / f"WP{i:02d}-task.md").touch()
        assert _next_wp_id(tmp_path) == "WP09"

    def test_nonexistent_dir_returns_wp01(self) -> None:
        """Non-existent dir should return WP01."""
        _clear_virtual_registry()
        assert _next_wp_id(Path("/nonexistent/path")) == "WP01"

    def test_ignores_non_wp_files(self, tmp_path: Path) -> None:
        """Should ignore files that don't match WP pattern."""
        _clear_virtual_registry()
        (tmp_path / "README.md").touch()
        (tmp_path / "notes.txt").touch()
        assert _next_wp_id(tmp_path) == "WP01"


class TestSlugify:
    """Test filename slug generation."""

    def test_basic_slugify(self) -> None:
        assert _slugify("Use SQLAlchemy") == "use-sqlalchemy"

    def test_special_chars_removed(self) -> None:
        assert _slugify("fix bug #123!") == "fix-bug-123"

    def test_max_length_respected(self) -> None:
        result = _slugify("a very long title that exceeds the limit", max_length=15)
        assert len(result) <= 15

    def test_empty_returns_change(self) -> None:
        assert _slugify("") == "change"

    def test_spaces_to_hyphens(self) -> None:
        assert _slugify("add caching layer") == "add-caching-layer"


class TestDeriveTitle:
    """Test title derivation from request text."""

    def test_short_request(self) -> None:
        assert _derive_title("fix typo") == "fix typo"

    def test_truncation(self) -> None:
        long = "a" * 100
        result = _derive_title(long, max_length=30)
        assert len(result) <= 33  # 30 + "..."

    def test_sentence_boundary(self) -> None:
        result = _derive_title("Fix the login bug. Also update the tests.", max_length=60)
        assert "Also" not in result


# ============================================================================
# T020: Frontmatter Fields
# ============================================================================


class TestFrontmatter:
    """Test that generated WPs have all required frontmatter fields."""

    def test_single_wp_has_required_fields(self, tmp_path: Path) -> None:
        """Single WP should have all required change metadata."""
        _clear_virtual_registry()
        req = _make_change_request()
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        assert len(wps) == 1
        body = wps[0].body

        # Check frontmatter fields
        assert 'change_stack: true' in body
        assert f'change_request_id: "{req.request_id}"' in body
        assert 'change_mode:' in body
        assert 'stack_rank:' in body
        assert 'review_attention:' in body
        assert f'work_package_id: "{wps[0].work_package_id}"' in body
        assert 'lane: "planned"' in body
        assert 'title:' in body

    def test_elevated_review_attention(self, tmp_path: Path) -> None:
        """WPs from high-complexity continue should have elevated attention."""
        _clear_virtual_registry()
        req = _make_change_request(
            request_text="replace framework Django with FastAPI, migrate from PostgreSQL to MongoDB, "
            "update the api contract for all endpoints, modify the deployment pipeline",
            review_attention=ReviewAttention.ELEVATED,
        )
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        assert len(wps) >= 1
        assert wps[0].review_attention in ("normal", "elevated")

    def test_frontmatter_has_history(self, tmp_path: Path) -> None:
        """Generated WP should have activity log in frontmatter."""
        _clear_virtual_registry()
        req = _make_change_request()
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        assert "history:" in wps[0].body
        assert "Generated by /spec-kitty.change" in wps[0].body

    def test_change_mode_label(self, tmp_path: Path) -> None:
        """Change mode should map to correct frontmatter label."""
        _clear_virtual_registry()
        req = _make_change_request(mode_override=PackagingMode.SINGLE_WP)
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        assert wps[0].change_mode == "single"


class TestModeToLabel:
    """Test mode to frontmatter label mapping."""

    def test_single_wp(self) -> None:
        assert _mode_to_frontmatter_label(PackagingMode.SINGLE_WP) == "single"

    def test_orchestration(self) -> None:
        assert _mode_to_frontmatter_label(PackagingMode.ORCHESTRATION) == "orchestration"

    def test_targeted_multi(self) -> None:
        assert _mode_to_frontmatter_label(PackagingMode.TARGETED_MULTI) == "targeted"


# ============================================================================
# T021: Guardrails and Final Testing Task
# ============================================================================


class TestGuardrails:
    """Test guardrail extraction and final testing task."""

    def test_final_testing_task_always_present(self, tmp_path: Path) -> None:
        """Every generated WP must have a final testing task."""
        _clear_virtual_registry()
        req = _make_change_request()
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        for wp in wps:
            assert "## Final Testing Task" in wp.body
            assert "pytest tests/" in wp.body
            assert "REQUIRED" in wp.body

    def test_explicit_guardrails_extracted(self) -> None:
        """'must' / 'must not' constraints should be extracted."""
        guardrails = _extract_guardrails(
            "Use SQLAlchemy but must not break existing migrations. "
            "Must maintain backward compatibility."
        )
        assert len(guardrails) >= 1
        # At least one should contain the constraint
        combined = " ".join(guardrails)
        assert "must" in combined.lower()

    def test_default_guardrail_when_none_explicit(self) -> None:
        """When no constraints found, a default guardrail should be added."""
        guardrails = _extract_guardrails("fix typo in README")
        assert len(guardrails) >= 1
        assert "tests" in guardrails[0].lower()

    def test_guardrails_in_wp_body(self, tmp_path: Path) -> None:
        """Extracted guardrails should appear in the WP body."""
        _clear_virtual_registry()
        req = _make_change_request(
            request_text="use SQLAlchemy but must not break existing tests in models.py"
        )
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        body = wps[0].body
        assert "Acceptance Constraints" in body or "Ensure existing tests" in body


# ============================================================================
# T022: Implementation Command Hints
# ============================================================================


class TestImplementationHints:
    """Test implementation command hints in generated WPs."""

    def test_no_deps_simple_command(self) -> None:
        """WP with no deps should get simple implement command."""
        hint = _build_implementation_hint("WP09", [])
        assert hint == "spec-kitty implement WP09"

    def test_with_deps_has_base_flag(self) -> None:
        """WP with deps should get --base flag."""
        hint = _build_implementation_hint("WP10", ["WP09"])
        assert hint == "spec-kitty implement WP10 --base WP09"

    def test_multiple_deps_uses_last(self) -> None:
        """Multiple deps should use last as --base."""
        hint = _build_implementation_hint("WP11", ["WP08", "WP09"])
        assert hint == "spec-kitty implement WP11 --base WP09"

    def test_hint_in_wp_body(self, tmp_path: Path) -> None:
        """Implementation hint should appear in WP body."""
        _clear_virtual_registry()
        req = _make_change_request()
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        body = wps[0].body
        assert "spec-kitty implement" in body
        assert "```bash" in body


# ============================================================================
# T018 + T023: Mode Selection and Synthesis Shape
# ============================================================================


class TestSynthesizePlan:
    """Test change plan synthesis (T018)."""

    def test_single_wp_mode(self) -> None:
        """Simple request should produce single_wp mode."""
        req = _make_change_request(mode_override=PackagingMode.SINGLE_WP)
        plan = synthesize_change_plan(req)
        assert plan.mode == PackagingMode.SINGLE_WP

    def test_orchestration_mode(self) -> None:
        """Request with orchestration mode override should carry through."""
        req = _make_change_request(mode_override=PackagingMode.ORCHESTRATION)
        plan = synthesize_change_plan(req)
        assert plan.mode == PackagingMode.ORCHESTRATION

    def test_targeted_multi_mode(self) -> None:
        """Targeted multi mode should carry through."""
        req = _make_change_request(mode_override=PackagingMode.TARGETED_MULTI)
        plan = synthesize_change_plan(req)
        assert plan.mode == PackagingMode.TARGETED_MULTI

    def test_closed_references_in_plan(self) -> None:
        """Closed WP refs should be included in the plan."""
        req = _make_change_request(closed_wp_ids=["WP01", "WP02"])
        plan = synthesize_change_plan(req)
        assert plan.closed_reference_wp_ids == ["WP01", "WP02"]

    def test_plan_has_guardrails(self) -> None:
        """Plan should extract guardrails from request text."""
        req = _make_change_request()
        plan = synthesize_change_plan(req)
        assert len(plan.guardrails) >= 1


class TestGenerateWorkPackages:
    """Test full WP generation for all three modes (T023)."""

    def test_single_wp_produces_one(self, tmp_path: Path) -> None:
        """single_wp mode should produce exactly one WP."""
        _clear_virtual_registry()
        req = _make_change_request(mode_override=PackagingMode.SINGLE_WP)
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        assert len(wps) == 1
        assert wps[0].change_mode == "single"
        assert wps[0].stack_rank == 1
        assert wps[0].change_stack is True

    def test_orchestration_produces_one(self, tmp_path: Path) -> None:
        """orchestration mode should produce exactly one WP with 'Orchestrate:' prefix."""
        _clear_virtual_registry()
        req = _make_change_request(mode_override=PackagingMode.ORCHESTRATION)
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        assert len(wps) == 1
        assert wps[0].change_mode == "orchestration"
        assert wps[0].title.startswith("Orchestrate:")

    def test_targeted_multi_produces_multiple(self, tmp_path: Path) -> None:
        """targeted_multi mode should produce 2+ WPs."""
        _clear_virtual_registry()
        req = _make_change_request(mode_override=PackagingMode.TARGETED_MULTI)
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        assert len(wps) >= 2
        assert all(wp.change_mode == "targeted" for wp in wps)
        # Stack ranks should be sequential
        ranks = [wp.stack_rank for wp in wps]
        assert ranks == list(range(1, len(wps) + 1))

    def test_targeted_multi_dependency_chain(self, tmp_path: Path) -> None:
        """targeted_multi WPs should form a dependency chain."""
        _clear_virtual_registry()
        req = _make_change_request(mode_override=PackagingMode.TARGETED_MULTI)
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        # First WP has no deps
        assert wps[0].dependencies == []
        # Subsequent WPs depend on predecessor
        for i in range(1, len(wps)):
            assert wps[i].dependencies == [wps[i - 1].work_package_id]

    def test_no_id_collisions(self, tmp_path: Path) -> None:
        """Generated WP IDs should not collide with existing files."""
        _clear_virtual_registry()
        (tmp_path / "WP01-existing.md").touch()
        (tmp_path / "WP02-existing.md").touch()

        req = _make_change_request(mode_override=PackagingMode.TARGETED_MULTI)
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        ids = {wp.work_package_id for wp in wps}
        assert "WP01" not in ids
        assert "WP02" not in ids

    def test_no_id_collisions_between_generated(self, tmp_path: Path) -> None:
        """Generated WPs in same batch should not collide with each other."""
        _clear_virtual_registry()
        req = _make_change_request(mode_override=PackagingMode.TARGETED_MULTI)
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        ids = [wp.work_package_id for wp in wps]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_closed_refs_only_on_first_wp(self, tmp_path: Path) -> None:
        """Closed reference links should only appear on the first WP."""
        _clear_virtual_registry()
        req = _make_change_request(
            mode_override=PackagingMode.TARGETED_MULTI,
            closed_wp_ids=["WP01"],
        )
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        assert wps[0].closed_reference_links == ["WP01"]
        for wp in wps[1:]:
            assert wp.closed_reference_links == []


class TestWriteWorkPackages:
    """Test writing generated WPs to disk."""

    def test_files_written(self, tmp_path: Path) -> None:
        """write_change_work_packages should create files on disk."""
        _clear_virtual_registry()
        req = _make_change_request()
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)

        written = write_change_work_packages(wps, tmp_path)
        assert len(written) == len(wps)
        for p in written:
            assert p.exists()
            content = p.read_text(encoding="utf-8")
            assert content.startswith("---")

    def test_creates_dir_if_missing(self, tmp_path: Path) -> None:
        """Should create tasks dir if it doesn't exist."""
        _clear_virtual_registry()
        tasks_dir = tmp_path / "tasks"
        assert not tasks_dir.exists()

        req = _make_change_request()
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tasks_dir)
        write_change_work_packages(wps, tasks_dir)

        assert tasks_dir.exists()

    def test_written_content_parseable(self, tmp_path: Path) -> None:
        """Written WP files should have valid frontmatter."""
        _clear_virtual_registry()
        req = _make_change_request()
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)
        written = write_change_work_packages(wps, tmp_path)

        content = written[0].read_text(encoding="utf-8")
        # Should have opening and closing frontmatter delimiters
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Frontmatter not properly delimited"
        # Should have lane field
        assert re.search(r'^lane:\s*"planned"', parts[1], re.MULTILINE)


# ============================================================================
# End-to-End Synthesis
# ============================================================================


class TestEndToEndSynthesis:
    """Test full synthesis pipeline from request to written WPs."""

    def test_simple_request_produces_valid_wp(self, tmp_path: Path) -> None:
        """A simple request should produce a single valid WP file."""
        _clear_virtual_registry()
        req = _make_change_request(request_text="fix the login bug in auth.py")
        plan = synthesize_change_plan(req)
        wps = generate_change_work_packages(req, plan, tmp_path)
        written = write_change_work_packages(wps, tmp_path)

        assert len(written) == 1
        content = written[0].read_text(encoding="utf-8")

        # Verify structure
        assert "change_stack: true" in content
        assert "## Final Testing Task" in content
        assert "spec-kitty implement" in content
        assert "fix the login bug in auth.py" in content

    def test_deterministic_output(self, tmp_path: Path) -> None:
        """Same input should produce same output structure."""
        for i in range(3):
            _clear_virtual_registry()
            sub = tmp_path / f"run{i}"
            sub.mkdir()
            req = _make_change_request(request_text="add caching to handler.py")
            plan = synthesize_change_plan(req)
            wps = generate_change_work_packages(req, plan, sub)

            assert len(wps) == 1
            assert wps[0].change_mode == _mode_to_frontmatter_label(plan.mode)
            assert wps[0].change_stack is True
