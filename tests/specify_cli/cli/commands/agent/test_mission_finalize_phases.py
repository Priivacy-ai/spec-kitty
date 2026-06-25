"""Direct unit tests for the finalize-tasks phase helpers (#2056 WP07, T029/T030).

The pre-decomposition ``finalize_tasks`` was a 1227-LOC monolith — the worst
offender in ``mission.py``. WP07 relocated it to ``mission_finalize`` and split
the body into ≤15-CC phase helpers. These tests exercise each deterministic
helper's branches in isolation: artifact collection + branch-tree path mapping,
the 3-tier dependency/requirement resolution, the cycle + requirement-mapping
gates, the disagree-loud conflict gate, the 8-field bootstrap-mutation applies
(including the INV-6 zero-mutation invariant), the owned-files / kitty-specs
gate, and the validation-frontmatter acquisition.

The end-to-end command stays pinned by ``test_mission_finalize_tasks.py``,
``test_feature_finalize_bootstrap.py``, the validate-only readonly suite, and
the WP01 golden harness. The relocated ``_collect_finalize_artifacts`` /
``_branch_tree_relative_path`` keep their existing integration coverage via
``test_finalize_coord_staging.py`` (which still imports them off ``mission``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands.agent import mission_finalize as seam
from specify_cli.status import WPMetadata

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# _branch_tree_relative_path
# ---------------------------------------------------------------------------


def test_branch_tree_relative_path_plain(tmp_path: Path) -> None:
    repo = tmp_path
    f = repo / "kitty-specs" / "m" / "tasks.md"
    f.parent.mkdir(parents=True)
    f.write_text("x", encoding="utf-8")
    assert seam._branch_tree_relative_path(f, repo) == "kitty-specs/m/tasks.md"


def test_branch_tree_relative_path_strips_worktree_prefix(tmp_path: Path) -> None:
    repo = tmp_path
    wt = repo / ".worktrees" / "lane-a"
    target = wt / "kitty-specs" / "m" / "tasks.md"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    # ``.worktrees/<name>`` is a real dir → the prefix is dropped.
    assert seam._branch_tree_relative_path(target, repo) == "kitty-specs/m/tasks.md"


# ---------------------------------------------------------------------------
# _collect_finalize_artifacts
# ---------------------------------------------------------------------------


def test_collect_finalize_artifacts_dedupes_and_filters_missing(tmp_path: Path) -> None:
    feature = tmp_path / "kitty-specs" / "001-m"
    tasks = feature / "tasks"
    tasks.mkdir(parents=True)
    (feature / "tasks.md").write_text("x", encoding="utf-8")
    (feature / "status.json").write_text("{}", encoding="utf-8")
    (tasks / "WP01.md").write_text("x", encoding="utf-8")
    lanes = feature / "lanes.json"
    lanes.write_text("{}", encoding="utf-8")

    artifacts = seam._collect_finalize_artifacts(feature, tasks, "001-m", lanes_path=lanes)

    # Only existing files; no duplicates; missing candidates (events log, matrices) skipped.
    assert (feature / "tasks.md") in artifacts
    assert (feature / "status.json") in artifacts
    assert (tasks / "WP01.md") in artifacts
    assert lanes in artifacts
    assert len(artifacts) == len(set(artifacts))
    assert all(p.exists() for p in artifacts)


# ---------------------------------------------------------------------------
# _branch_strategy_text
# ---------------------------------------------------------------------------


def test_branch_strategy_text_embeds_target_branch() -> None:
    text = seam._branch_strategy_text("prog/x")
    assert "generated on prog/x" in text
    assert "merge back into prog/x" in text


# ---------------------------------------------------------------------------
# _validate_dependency_graph
# ---------------------------------------------------------------------------


def test_validate_dependency_graph_passes_for_acyclic() -> None:
    # No exception for a valid DAG.
    seam._validate_dependency_graph({"WP02": ["WP01"], "WP01": []}, json_output=True)


def test_validate_dependency_graph_rejects_cycle() -> None:
    with pytest.raises(typer.Exit):
        seam._validate_dependency_graph({"WP01": ["WP02"], "WP02": ["WP01"]}, json_output=True)


def test_validate_dependency_graph_noop_when_empty() -> None:
    seam._validate_dependency_graph({}, json_output=True)


# ---------------------------------------------------------------------------
# _validate_requirement_mapping
# ---------------------------------------------------------------------------


def test_requirement_mapping_passes_when_all_functional_covered() -> None:
    seam._validate_requirement_mapping(
        ["WP01"],
        {"WP01": ["FR-001"]},
        {"FR-001"},
        {"FR-001"},
        {"WP01": []},
        json_output=True,
    )


def test_requirement_mapping_rejects_unmapped_functional() -> None:
    with pytest.raises(typer.Exit):
        seam._validate_requirement_mapping(
            ["WP01"],
            {"WP01": ["FR-001"]},
            {"FR-001", "FR-002"},
            {"FR-001", "FR-002"},
            {"WP01": []},
            json_output=True,
        )


def test_requirement_mapping_rejects_missing_refs() -> None:
    with pytest.raises(typer.Exit):
        seam._validate_requirement_mapping(
            ["WP01"],
            {},
            {"FR-001"},
            {"FR-001"},
            {"WP01": []},
            json_output=True,
        )


def test_requirement_mapping_rejects_unknown_ref() -> None:
    with pytest.raises(typer.Exit):
        seam._validate_requirement_mapping(
            ["WP01"],
            {"WP01": ["FR-999"]},
            {"FR-001"},
            {"FR-001"},
            {"WP01": []},
            json_output=True,
        )


# ---------------------------------------------------------------------------
# _detect_dependency_conflicts (disagree-loud, T004)
# ---------------------------------------------------------------------------


def _wp_file(tmp_path: Path, name: str, deps: list[str]) -> Path:
    f = tmp_path / name
    dep_yaml = "[]" if not deps else "[" + ", ".join(deps) + "]"
    f.write_text(
        f"---\nwork_package_id: {name[:4]}\ntitle: t\ndependencies: {dep_yaml}\n---\nbody\n",
        encoding="utf-8",
    )
    return f


def test_detect_dependency_conflicts_noop_when_agree(tmp_path: Path) -> None:
    wp = _wp_file(tmp_path, "WP02.md", ["WP01"])
    seam._detect_dependency_conflicts([wp], {"WP02": ["WP01"]}, json_output=True)


def test_detect_dependency_conflicts_raises_on_disagreement(tmp_path: Path) -> None:
    wp = _wp_file(tmp_path, "WP02.md", ["WP01"])
    with pytest.raises(typer.Exit):
        seam._detect_dependency_conflicts([wp], {"WP02": ["WP03"]}, json_output=True)


# ---------------------------------------------------------------------------
# _apply_bootstrap_fields + _apply_ownership_inference
# ---------------------------------------------------------------------------


def test_apply_bootstrap_fields_marks_changes() -> None:
    meta = WPMetadata(work_package_id="WP01", title="t")
    bld = meta.builder()
    changed, fields = seam._apply_bootstrap_fields(
        bld,
        meta,
        deps=["WP00"],
        has_dependencies_line=False,
        requirement_refs=["FR-001"],
        has_requirement_refs_line=False,
        target_branch="prog/x",
    )
    assert changed is True
    assert fields["dependencies"] == ["WP00"]
    assert fields["merge_target_branch"] == "prog/x"
    built = bld.build()
    assert list(built.dependencies) == ["WP00"]
    assert built.merge_target_branch == "prog/x"


def test_apply_bootstrap_fields_noop_when_already_set() -> None:
    branch = "prog/x"
    meta = WPMetadata(
        work_package_id="WP01",
        title="t",
        dependencies=["WP00"],
        requirement_refs=["FR-001"],
        planning_base_branch=branch,
        merge_target_branch=branch,
        branch_strategy=seam._branch_strategy_text(branch),
    )
    bld = meta.builder()
    changed, fields = seam._apply_bootstrap_fields(
        bld,
        meta,
        deps=["WP00"],
        has_dependencies_line=True,
        requirement_refs=["FR-001"],
        has_requirement_refs_line=True,
        target_branch=branch,
    )
    assert changed is False
    assert fields == {}


def test_apply_ownership_inference_skips_when_present() -> None:
    meta = WPMetadata(
        work_package_id="WP01",
        title="t",
        execution_mode="code_change",
        owned_files=["src/x.py"],
        authoritative_surface="src/x.py",
    )
    bld = meta.builder()
    changed, warnings = seam._apply_ownership_inference(bld, meta, "body", "001-m", {})
    assert changed is False
    assert warnings == []


# ---------------------------------------------------------------------------
# INV-6: --validate-only zero-mutation invariant
# ---------------------------------------------------------------------------


def test_assert_no_write_in_validate_only_passes_when_empty() -> None:
    state = seam._BootstrapState()
    seam._assert_no_write_in_validate_only(state, validate_only=True)


def test_assert_no_write_in_validate_only_raises_when_queued() -> None:
    state = seam._BootstrapState()
    meta = WPMetadata(work_package_id="WP01", title="t")
    state.pending_writes.append((Path("WP01.md"), meta, "body"))
    with pytest.raises(AssertionError):
        seam._assert_no_write_in_validate_only(state, validate_only=True)


def test_assert_no_write_outside_validate_only_is_noop() -> None:
    state = seam._BootstrapState()
    meta = WPMetadata(work_package_id="WP01", title="t")
    state.pending_writes.append((Path("WP01.md"), meta, "body"))
    # No assertion fires when not validate_only — writes are legitimate.
    seam._assert_no_write_in_validate_only(state, validate_only=False)


def test_flush_frontmatter_writes_skips_in_validate_only(tmp_path: Path) -> None:
    state = seam._BootstrapState()
    target = tmp_path / "WP01.md"
    meta = WPMetadata(work_package_id="WP01", title="t")
    state.pending_writes.append((target, meta, "body"))
    seam._flush_frontmatter_writes(state, validate_only=True)
    assert not target.exists()  # INV-6: zero disk mutation in validate-only.


def test_flush_frontmatter_writes_persists_when_committing(tmp_path: Path) -> None:
    state = seam._BootstrapState()
    target = tmp_path / "WP01.md"
    meta = WPMetadata(work_package_id="WP01", title="t")
    state.pending_writes.append((target, meta, "body"))
    seam._flush_frontmatter_writes(state, validate_only=False)
    assert target.exists()


# ---------------------------------------------------------------------------
# _validate_owned_files_not_in_kitty_specs
# ---------------------------------------------------------------------------


def test_owned_files_kitty_specs_gate_passes_for_source_paths() -> None:
    meta = WPMetadata(work_package_id="WP01", title="t", owned_files=["src/x.py"])
    seam._validate_owned_files_not_in_mission_specs({"WP01": meta}, json_output=True)


def test_owned_files_kitty_specs_gate_rejects_kitty_specs_path() -> None:
    meta = WPMetadata(work_package_id="WP01", title="t", owned_files=["kitty-specs/001-m/spec.md"])
    with pytest.raises(typer.Exit):
        seam._validate_owned_files_not_in_mission_specs({"WP01": meta}, json_output=True)


# ---------------------------------------------------------------------------
# _gather_validation_frontmatter (prefer-in-memory-then-disk, FR-031)
# ---------------------------------------------------------------------------


def test_gather_validation_frontmatter_prefers_inmemory(tmp_path: Path) -> None:
    wp = _wp_file(tmp_path, "WP01.md", [])
    state = seam._BootstrapState()
    inmemory = WPMetadata(work_package_id="WP01", title="t", dependencies=["WP00"])
    state.inmemory_frontmatter["WP01"] = inmemory
    state.inmemory_bodies["WP01"] = "inmem-body"

    fms, bodies = seam._gather_validation_frontmatter([wp], state)
    assert list(fms["WP01"].dependencies) == ["WP00"]
    assert bodies["WP01"] == "inmem-body"


def test_gather_validation_frontmatter_falls_back_to_disk(tmp_path: Path) -> None:
    wp = _wp_file(tmp_path, "WP01.md", ["WP00"])
    state = seam._BootstrapState()
    fms, _bodies = seam._gather_validation_frontmatter([wp], state)
    assert list(fms["WP01"].dependencies) == ["WP00"]
