"""Unit tests for change stack routing, validation, and policy enforcement.

Tests cover:
- T007: Stash resolver (main vs feature branch routing)
- T010: Ambiguity fail-fast detection
- T011: Closed/done link-only policy enforcement
- T024: Dependency candidate extraction
- T025: Change-to-normal dependency policy
- T026: Graph validation and invalid edge rejection
- T027: Closed/done reference linking
- T028: Blocker output for no-ready stack
- T029: Dependency policy tests (comprehensive)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from specify_cli.core.change_stack import (
    ChangeStackError,
    DependencyEdge,
    StashScope,
    ValidationState,
    _extract_feature_slug,
    build_closed_reference_links,
    check_ambiguity,
    check_closed_references,
    extract_dependency_candidates,
    resolve_next_change_wp,
    resolve_stash,
    validate_change_request,
    validate_dependency_graph_integrity,
    validate_dependency_policy,
    validate_no_closed_mutation,
)


# ============================================================================
# T007: Stash Resolver Tests
# ============================================================================


class TestResolveStash:
    """Test branch stash routing logic."""

    def test_main_branch_routes_to_main_stash(self, tmp_path: Path) -> None:
        """main branch should route to kitty-specs/change-stack/main/."""
        with patch("specify_cli.core.change_stack.get_current_branch", return_value="main"), \
             patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            stash = resolve_stash(tmp_path, branch="main")

        assert stash.stash_key == "main"
        assert stash.scope == StashScope.MAIN
        assert stash.stash_path == tmp_path / "kitty-specs" / "change-stack" / "main"

    def test_master_branch_routes_to_main_stash(self, tmp_path: Path) -> None:
        """master branch should also route to main stash."""
        with patch("specify_cli.core.change_stack.get_current_branch", return_value="master"), \
             patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            stash = resolve_stash(tmp_path, branch="master")

        assert stash.stash_key == "main"
        assert stash.scope == StashScope.MAIN

    def test_feature_branch_routes_to_feature_stash(self, tmp_path: Path) -> None:
        """Feature branch should route to kitty-specs/<feature>/tasks/."""
        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            stash = resolve_stash(tmp_path, branch="029-mid-stream-change")

        assert stash.stash_key == "029-mid-stream-change"
        assert stash.scope == StashScope.FEATURE
        assert stash.stash_path == tmp_path / "kitty-specs" / "029-mid-stream-change" / "tasks"

    def test_worktree_branch_routes_to_feature_stash(self, tmp_path: Path) -> None:
        """Worktree branch (###-feature-WP##) should strip WP suffix."""
        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            stash = resolve_stash(tmp_path, branch="029-mid-stream-change-WP01")

        assert stash.stash_key == "029-mid-stream-change"
        assert stash.scope == StashScope.FEATURE

    def test_unrecognized_branch_raises_error(self, tmp_path: Path) -> None:
        """Branches that don't match any pattern should raise ChangeStackError."""
        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            with pytest.raises(ChangeStackError, match="Cannot resolve stash"):
                resolve_stash(tmp_path, branch="some-random-branch")

    def test_auto_detect_branch(self, tmp_path: Path) -> None:
        """When branch is None, should auto-detect from git."""
        with patch("specify_cli.core.change_stack.get_current_branch", return_value="main"), \
             patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            stash = resolve_stash(tmp_path)

        assert stash.stash_key == "main"

    def test_no_branch_detected_raises_error(self, tmp_path: Path) -> None:
        """Should raise error if git branch cannot be determined."""
        with patch("specify_cli.core.change_stack.get_current_branch", return_value=None), \
             patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            with pytest.raises(ChangeStackError, match="Could not determine"):
                resolve_stash(tmp_path)

    def test_main_stash_tasks_doc_when_exists(self, tmp_path: Path) -> None:
        """Should include tasks_doc_path if tasks.md exists."""
        stash_dir = tmp_path / "kitty-specs" / "change-stack" / "main"
        stash_dir.mkdir(parents=True)
        tasks_doc = stash_dir / "tasks.md"
        tasks_doc.write_text("# Tasks", encoding="utf-8")

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            stash = resolve_stash(tmp_path, branch="main")

        assert stash.tasks_doc_path == tasks_doc

    def test_feature_stash_tasks_doc_when_missing(self, tmp_path: Path) -> None:
        """Should have None tasks_doc_path when tasks.md doesn't exist."""
        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            stash = resolve_stash(tmp_path, branch="029-test-feature")

        assert stash.tasks_doc_path is None


class TestExtractFeatureSlug:
    """Test feature slug extraction from branch names."""

    def test_direct_feature_branch(self) -> None:
        assert _extract_feature_slug("029-mid-stream-change") == "029-mid-stream-change"

    def test_worktree_branch(self) -> None:
        assert _extract_feature_slug("029-mid-stream-change-WP01") == "029-mid-stream-change"

    def test_worktree_branch_double_digit(self) -> None:
        assert _extract_feature_slug("001-demo-WP12") == "001-demo"

    def test_non_feature_branch(self) -> None:
        assert _extract_feature_slug("develop") is None

    def test_main_branch(self) -> None:
        assert _extract_feature_slug("main") is None

    def test_release_branch(self) -> None:
        assert _extract_feature_slug("release-v1.0") is None

    def test_three_digit_prefix_only(self) -> None:
        """Branch must have content after the number prefix."""
        assert _extract_feature_slug("029-a") == "029-a"

    def test_hyphenated_feature_name(self) -> None:
        assert _extract_feature_slug("001-my-complex-feature-name") == "001-my-complex-feature-name"


# ============================================================================
# T010: Ambiguity Detection Tests
# ============================================================================


class TestCheckAmbiguity:
    """Test ambiguity fail-fast gate."""

    def test_empty_request_is_ambiguous(self) -> None:
        result = check_ambiguity("")
        assert result.is_ambiguous
        assert "empty request" in result.matched_patterns

    def test_whitespace_only_is_ambiguous(self) -> None:
        result = check_ambiguity("   ")
        assert result.is_ambiguous

    def test_this_block_is_ambiguous(self) -> None:
        result = check_ambiguity("change this block to use async")
        assert result.is_ambiguous
        assert any("this block" in p for p in result.matched_patterns)

    def test_that_section_is_ambiguous(self) -> None:
        result = check_ambiguity("rewrite that section")
        assert result.is_ambiguous

    def test_clear_request_is_not_ambiguous(self) -> None:
        result = check_ambiguity("use SQLAlchemy instead of raw SQL queries")
        assert not result.is_ambiguous

    def test_file_reference_disambiguates(self) -> None:
        """File references should disambiguate vague language."""
        result = check_ambiguity("change this block in change_stack.py")
        assert not result.is_ambiguous

    def test_wp_reference_disambiguates(self) -> None:
        """WP references should disambiguate."""
        result = check_ambiguity("change this block in WP01")
        assert not result.is_ambiguous

    def test_function_reference_disambiguates(self) -> None:
        """Function/class references should disambiguate."""
        result = check_ambiguity("change this block in function resolve_stash")
        assert not result.is_ambiguous

    def test_quoted_identifier_disambiguates(self) -> None:
        """Quoted identifiers should disambiguate."""
        result = check_ambiguity('change this block in "my_function"')
        assert not result.is_ambiguous

    def test_specific_request_is_valid(self) -> None:
        result = check_ambiguity("replace manual JSON parsing with pydantic models in data_model.py")
        assert not result.is_ambiguous

    def test_ambiguity_provides_clarification_prompt(self) -> None:
        result = check_ambiguity("fix this part")
        assert result.is_ambiguous
        assert result.clarification_prompt is not None
        assert "clarify" in result.clarification_prompt.lower()

    def test_here_is_ambiguous(self) -> None:
        result = check_ambiguity("add validation here")
        assert result.is_ambiguous

    def test_directive_with_target_is_valid(self) -> None:
        """FR-002: Directive phrasing like 'use this library instead' should work."""
        result = check_ambiguity("use SQLAlchemy instead of raw SQL")
        assert not result.is_ambiguous

    def test_revert_with_file_is_valid(self) -> None:
        result = check_ambiguity("revert changes to config.yaml")
        assert not result.is_ambiguous

    def test_do_not_remove_with_target_is_valid(self) -> None:
        result = check_ambiguity("do not remove the `validate_input` function")
        assert not result.is_ambiguous


# ============================================================================
# T011: Closed/Done Policy Tests
# ============================================================================


class TestCheckClosedReferences:
    """Test closed/done WP reference detection."""

    def test_no_wp_references(self, tmp_path: Path) -> None:
        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            result = check_closed_references("add caching layer", tmp_path, "001-demo")
        assert not result.has_closed_references
        assert result.closed_wp_ids == []

    def test_reference_to_open_wp(self, tmp_path: Path) -> None:
        """Open WPs should not be flagged."""
        tasks_dir = tmp_path / "kitty-specs" / "001-demo" / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_file = tasks_dir / "WP01-setup.md"
        wp_file.write_text('---\nlane: "doing"\n---\n# Setup', encoding="utf-8")

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            result = check_closed_references("modify WP01 approach", tmp_path, "001-demo")
        assert not result.has_closed_references

    def test_reference_to_done_wp(self, tmp_path: Path) -> None:
        """Done WPs should be flagged as closed references."""
        tasks_dir = tmp_path / "kitty-specs" / "001-demo" / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_file = tasks_dir / "WP01-setup.md"
        wp_file.write_text('---\nlane: "done"\n---\n# Setup', encoding="utf-8")

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            result = check_closed_references("like WP01 but with caching", tmp_path, "001-demo")
        assert result.has_closed_references
        assert "WP01" in result.closed_wp_ids
        assert result.linkable  # Always linkable, never reopenable

    def test_multiple_references_mixed(self, tmp_path: Path) -> None:
        """Should only flag done WPs, not open ones."""
        tasks_dir = tmp_path / "kitty-specs" / "001-demo" / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "WP01-setup.md").write_text('---\nlane: "done"\n---\n', encoding="utf-8")
        (tasks_dir / "WP02-core.md").write_text('---\nlane: "doing"\n---\n', encoding="utf-8")

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            result = check_closed_references(
                "apply WP01 pattern to WP02", tmp_path, "001-demo"
            )
        assert result.has_closed_references
        assert "WP01" in result.closed_wp_ids
        assert "WP02" not in result.closed_wp_ids


class TestValidateNoClosedMutation:
    """Test that closed WPs cannot be mutated."""

    def test_no_closed_wps(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "WP01-setup.md").write_text('---\nlane: "doing"\n---\n', encoding="utf-8")

        blocked = validate_no_closed_mutation(["WP01"], tasks_dir)
        assert blocked == []

    def test_closed_wp_blocked(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "WP01-setup.md").write_text('---\nlane: "done"\n---\n', encoding="utf-8")

        blocked = validate_no_closed_mutation(["WP01"], tasks_dir)
        assert blocked == ["WP01"]

    def test_missing_wp_not_blocked(self, tmp_path: Path) -> None:
        """Non-existent WPs should not be blocked."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        blocked = validate_no_closed_mutation(["WP99"], tasks_dir)
        assert blocked == []


# ============================================================================
# Integration: validate_change_request
# ============================================================================


class TestValidateChangeRequest:
    """Test the combined validation pipeline."""

    def test_valid_request_on_feature_branch(self, tmp_path: Path) -> None:
        with patch("specify_cli.core.change_stack.get_current_branch", return_value="029-test"), \
             patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            req = validate_change_request(
                "use pydantic models in data_model.py",
                tmp_path,
                branch="029-test",
            )

        assert req.validation_state == ValidationState.VALID
        assert req.stash.scope == StashScope.FEATURE
        assert req.stash.stash_key == "029-test"
        assert not req.ambiguity.is_ambiguous

    def test_ambiguous_request_fails_fast(self, tmp_path: Path) -> None:
        with patch("specify_cli.core.change_stack.get_current_branch", return_value="029-test"), \
             patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            req = validate_change_request(
                "change this block",
                tmp_path,
                branch="029-test",
            )

        assert req.validation_state == ValidationState.AMBIGUOUS
        assert req.ambiguity.is_ambiguous

    def test_main_branch_routing(self, tmp_path: Path) -> None:
        with patch("specify_cli.core.change_stack.get_current_branch", return_value="main"), \
             patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            req = validate_change_request(
                "add retry logic to API calls",
                tmp_path,
                branch="main",
            )

        assert req.stash.scope == StashScope.MAIN
        assert req.stash.stash_key == "main"

    def test_request_id_generated(self, tmp_path: Path) -> None:
        with patch("specify_cli.core.change_stack.get_current_branch", return_value="main"), \
             patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            req = validate_change_request("add caching", tmp_path, branch="main")

        assert req.request_id
        assert len(req.request_id) == 8  # UUID prefix


# ============================================================================
# T024: Dependency Candidate Extraction Tests
# ============================================================================


def _make_wp_file(
    tasks_dir: Path,
    wp_id: str,
    lane: str = "planned",
    change_stack: bool = False,
    dependencies: list[str] | None = None,
    stack_rank: int = 0,
) -> Path:
    """Helper to create a WP file with frontmatter."""
    deps = dependencies or []
    deps_str = ", ".join(f'"{d}"' for d in deps)
    content = f"""---
work_package_id: "{wp_id}"
title: "{wp_id} test"
lane: "{lane}"
change_stack: {'true' if change_stack else 'false'}
stack_rank: {stack_rank}
dependencies: [{deps_str}]
---

# {wp_id}
"""
    wp_file = tasks_dir / f"{wp_id}-test.md"
    wp_file.write_text(content, encoding="utf-8")
    return wp_file


class TestExtractDependencyCandidates:
    """Test candidate dependency edge extraction (T024)."""

    def test_empty_affected_list(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        candidates = extract_dependency_candidates([], "WP10", tasks_dir)
        assert candidates == []

    def test_skips_self_reference(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP10", lane="doing")
        candidates = extract_dependency_candidates(["WP10"], "WP10", tasks_dir)
        assert candidates == []

    def test_skips_closed_wps(self, tmp_path: Path) -> None:
        """Closed WPs should not become dependency edges (they become links)."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="done")
        candidates = extract_dependency_candidates(["WP01"], "WP10", tasks_dir)
        assert candidates == []

    def test_creates_edge_to_open_wp(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="doing")
        candidates = extract_dependency_candidates(["WP01"], "WP10", tasks_dir)
        assert len(candidates) == 1
        assert candidates[0].source == "WP10"
        assert candidates[0].target == "WP01"
        assert candidates[0].edge_type == "change_to_normal"

    def test_detects_change_to_change_edge(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP08", lane="planned", change_stack=True)
        candidates = extract_dependency_candidates(["WP08"], "WP10", tasks_dir)
        assert len(candidates) == 1
        assert candidates[0].edge_type == "change_to_change"

    def test_deterministic_ordering(self, tmp_path: Path) -> None:
        """Candidates should be in sorted WP ID order."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP03", lane="doing")
        _make_wp_file(tasks_dir, "WP01", lane="planned")
        _make_wp_file(tasks_dir, "WP02", lane="for_review")

        candidates = extract_dependency_candidates(
            ["WP03", "WP01", "WP02"], "WP10", tasks_dir
        )
        assert [c.target for c in candidates] == ["WP01", "WP02", "WP03"]

    def test_skips_missing_wps(self, tmp_path: Path) -> None:
        """WPs not found in tasks dir should be silently skipped."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        candidates = extract_dependency_candidates(["WP99"], "WP10", tasks_dir)
        assert candidates == []


# ============================================================================
# T025: Dependency Policy Validation Tests
# ============================================================================


class TestValidateDependencyPolicy:
    """Test dependency policy rule enforcement (T025)."""

    def test_allows_change_to_normal_edge(self, tmp_path: Path) -> None:
        """FR-005A: change WP -> normal open WP is allowed."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="doing")

        edge = DependencyEdge(source="WP10", target="WP01", edge_type="change_to_normal")
        result = validate_dependency_policy([edge], tasks_dir)

        assert result.is_valid
        assert len(result.valid_edges) == 1
        assert len(result.rejected_edges) == 0

    def test_allows_change_to_change_edge(self, tmp_path: Path) -> None:
        """Change-to-change ordering is also allowed."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP08", lane="planned", change_stack=True)

        edge = DependencyEdge(source="WP10", target="WP08", edge_type="change_to_change")
        result = validate_dependency_policy([edge], tasks_dir)

        assert result.is_valid
        assert len(result.valid_edges) == 1

    def test_rejects_edge_to_closed_wp(self, tmp_path: Path) -> None:
        """Edges to closed/done WPs must be rejected."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="done")

        edge = DependencyEdge(source="WP10", target="WP01", edge_type="change_to_normal")
        result = validate_dependency_policy([edge], tasks_dir)

        assert result.is_valid  # No critical errors, just rejected edges
        assert len(result.valid_edges) == 0
        assert len(result.rejected_edges) == 1
        assert "closed/done" in result.rejected_edges[0][1]

    def test_rejects_edge_to_missing_wp(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()

        edge = DependencyEdge(source="WP10", target="WP99", edge_type="change_to_normal")
        result = validate_dependency_policy([edge], tasks_dir)

        assert len(result.rejected_edges) == 1
        assert "not found" in result.rejected_edges[0][1]

    def test_mixed_valid_and_rejected(self, tmp_path: Path) -> None:
        """Some edges valid, some rejected - result reflects both."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="doing")
        _make_wp_file(tasks_dir, "WP02", lane="done")

        edges = [
            DependencyEdge(source="WP10", target="WP01", edge_type="change_to_normal"),
            DependencyEdge(source="WP10", target="WP02", edge_type="change_to_normal"),
        ]
        result = validate_dependency_policy(edges, tasks_dir)

        assert result.is_valid
        assert len(result.valid_edges) == 1
        assert result.valid_edges[0].target == "WP01"
        assert len(result.rejected_edges) == 1
        assert result.rejected_edges[0][0].target == "WP02"

    def test_policy_diagnostics_include_reason(self, tmp_path: Path) -> None:
        """Rejected edges should include actionable reason text."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="done")

        edge = DependencyEdge(source="WP10", target="WP01", edge_type="change_to_normal")
        result = validate_dependency_policy([edge], tasks_dir)

        _, reason = result.rejected_edges[0]
        assert "closed_reference_links" in reason


# ============================================================================
# T026: Graph Validation Tests
# ============================================================================


class TestValidateDependencyGraphIntegrity:
    """Test full graph validation with cycle and missing ref detection (T026)."""

    def test_valid_linear_chain(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="doing")
        _make_wp_file(tasks_dir, "WP02", lane="planned", dependencies=["WP01"])

        is_valid, errors = validate_dependency_graph_integrity(
            "WP03", ["WP02"], tasks_dir
        )
        assert is_valid
        assert errors == []

    def test_rejects_self_dependency(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="doing")

        is_valid, errors = validate_dependency_graph_integrity(
            "WP10", ["WP10"], tasks_dir
        )
        assert not is_valid
        assert any("self" in e.lower() for e in errors)

    def test_rejects_cycle(self, tmp_path: Path) -> None:
        """Adding WP10 -> WP02 when WP02 -> WP01 and WP01 would depend on WP10."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="doing", dependencies=["WP10"])
        _make_wp_file(tasks_dir, "WP02", lane="planned", dependencies=["WP01"])

        # WP10 depends on WP02, but WP01 depends on WP10 -> cycle
        is_valid, errors = validate_dependency_graph_integrity(
            "WP10", ["WP02"], tasks_dir
        )
        assert not is_valid
        assert any("circular" in e.lower() or "cycle" in e.lower() for e in errors)

    def test_rejects_missing_reference(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="doing")

        is_valid, errors = validate_dependency_graph_integrity(
            "WP10", ["WP99"], tasks_dir
        )
        assert not is_valid
        assert any("WP99" in e for e in errors)

    def test_valid_fan_out_pattern(self, tmp_path: Path) -> None:
        """Multiple WPs depending on one common base is valid."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="done")
        _make_wp_file(tasks_dir, "WP02", lane="doing", dependencies=["WP01"])
        _make_wp_file(tasks_dir, "WP03", lane="planned", dependencies=["WP01"])

        is_valid, errors = validate_dependency_graph_integrity(
            "WP10", ["WP01"], tasks_dir
        )
        assert is_valid
        assert errors == []

    def test_aborts_atomically_on_failure(self, tmp_path: Path) -> None:
        """All errors should be collected, not just the first."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="doing")

        is_valid, errors = validate_dependency_graph_integrity(
            "WP10", ["WP10", "WP99"], tasks_dir
        )
        assert not is_valid
        assert len(errors) >= 2  # Both self-dep and missing ref


# ============================================================================
# T027: Closed Reference Linking Tests
# ============================================================================


class TestBuildClosedReferenceLinks:
    """Test closed/done reference link construction (T027)."""

    def test_no_wp_refs_returns_empty(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "kitty-specs" / "001-demo" / "tasks"
        tasks_dir.mkdir(parents=True)

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            links = build_closed_reference_links(
                "add caching layer", tasks_dir, "001-demo", tmp_path
            )
        assert links == []

    def test_open_wp_refs_not_linked(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "kitty-specs" / "001-demo" / "tasks"
        tasks_dir.mkdir(parents=True)
        _make_wp_file(tasks_dir, "WP01", lane="doing")

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            links = build_closed_reference_links(
                "extend WP01 approach", tasks_dir, "001-demo", tmp_path
            )
        assert links == []

    def test_closed_wp_refs_linked(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "kitty-specs" / "001-demo" / "tasks"
        tasks_dir.mkdir(parents=True)
        _make_wp_file(tasks_dir, "WP01", lane="done")

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            links = build_closed_reference_links(
                "like WP01 but with caching", tasks_dir, "001-demo", tmp_path
            )
        assert links == ["WP01"]

    def test_multiple_closed_refs_sorted(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "kitty-specs" / "001-demo" / "tasks"
        tasks_dir.mkdir(parents=True)
        _make_wp_file(tasks_dir, "WP03", lane="done")
        _make_wp_file(tasks_dir, "WP01", lane="done")
        _make_wp_file(tasks_dir, "WP02", lane="doing")

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            links = build_closed_reference_links(
                "combine WP01 and WP03 patterns, extend WP02",
                tasks_dir, "001-demo", tmp_path,
            )
        assert links == ["WP01", "WP03"]

    def test_no_lane_transition_on_closed(self, tmp_path: Path) -> None:
        """Closed WPs must remain closed - linking doesn't reopen them."""
        tasks_dir = tmp_path / "kitty-specs" / "001-demo" / "tasks"
        tasks_dir.mkdir(parents=True)
        wp_file = _make_wp_file(tasks_dir, "WP01", lane="done")

        with patch("specify_cli.core.change_stack._get_main_repo_root", return_value=tmp_path):
            build_closed_reference_links(
                "like WP01 but different", tasks_dir, "001-demo", tmp_path
            )

        # Verify WP01 is still done
        content = wp_file.read_text(encoding="utf-8")
        assert 'lane: "done"' in content


# ============================================================================
# T028: Stack-First Selection and Blocker Output Tests
# ============================================================================


class TestResolveNextChangeWP:
    """Test stack-first WP selection with blocker reporting (T028)."""

    def test_no_change_wps_selects_normal(self, tmp_path: Path) -> None:
        """No change stack -> normal backlog selection."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="planned")

        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert result.selected_source == "normal_backlog"
        assert result.next_wp_id == "WP01"
        assert not result.normal_progression_blocked

    def test_ready_change_wp_selected_first(self, tmp_path: Path) -> None:
        """Ready change WP takes priority over normal backlog."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="planned")
        _make_wp_file(tasks_dir, "WP08", lane="planned", change_stack=True, stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert result.selected_source == "change_stack"
        assert result.next_wp_id == "WP08"

    def test_blocked_change_wp_blocks_normal(self, tmp_path: Path) -> None:
        """Pending but blocked change WPs block normal backlog."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="planned")
        _make_wp_file(tasks_dir, "WP02", lane="doing")
        _make_wp_file(tasks_dir, "WP08", lane="planned", change_stack=True,
                      dependencies=["WP02"])

        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert result.selected_source == "blocked"
        assert result.normal_progression_blocked
        assert result.next_wp_id is None
        assert len(result.blockers) > 0
        assert "WP08" in result.blockers[0]

    def test_all_change_wps_done_allows_normal(self, tmp_path: Path) -> None:
        """All change WPs completed -> normal backlog resumes."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="planned")
        _make_wp_file(tasks_dir, "WP08", lane="done", change_stack=True)

        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert result.selected_source == "normal_backlog"
        assert result.next_wp_id == "WP01"

    def test_highest_priority_change_wp_selected(self, tmp_path: Path) -> None:
        """When multiple change WPs ready, select lowest stack_rank."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP08", lane="planned", change_stack=True, stack_rank=3)
        _make_wp_file(tasks_dir, "WP09", lane="planned", change_stack=True, stack_rank=1)

        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert result.selected_source == "change_stack"
        assert result.next_wp_id == "WP09"  # Lower rank = higher priority

    def test_active_change_wp_blocks_normal(self, tmp_path: Path) -> None:
        """Change WP in doing/for_review also blocks normal progression."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP01", lane="planned")
        _make_wp_file(tasks_dir, "WP08", lane="doing", change_stack=True)

        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert result.selected_source == "blocked"
        assert result.normal_progression_blocked
        assert any("doing" in b for b in result.blockers)

    def test_empty_tasks_dir(self, tmp_path: Path) -> None:
        """Non-existent tasks dir defaults to normal backlog."""
        tasks_dir = tmp_path / "nonexistent"
        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert result.selected_source == "normal_backlog"
        assert result.next_wp_id is None

    def test_blocker_includes_dependency_ids(self, tmp_path: Path) -> None:
        """Blocker messages should include the blocking dependency WP IDs."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP02", lane="doing")
        _make_wp_file(tasks_dir, "WP03", lane="planned")
        _make_wp_file(tasks_dir, "WP08", lane="planned", change_stack=True,
                      dependencies=["WP02", "WP03"])

        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert result.selected_source == "blocked"
        # Blocker should mention the unsatisfied dependencies
        blocker_text = " ".join(result.blockers)
        assert "WP02" in blocker_text
        assert "WP03" in blocker_text

    def test_pending_change_wps_reported(self, tmp_path: Path) -> None:
        """Blocked result should list pending change WP IDs."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        _make_wp_file(tasks_dir, "WP02", lane="doing")
        _make_wp_file(tasks_dir, "WP08", lane="planned", change_stack=True,
                      dependencies=["WP02"])
        _make_wp_file(tasks_dir, "WP09", lane="for_review", change_stack=True)

        result = resolve_next_change_wp(tasks_dir, "001-demo")
        assert "WP08" in result.pending_change_wps
        assert "WP09" in result.pending_change_wps
