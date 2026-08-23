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

import json
import re
from pathlib import Path

import pytest
import typer

from specify_cli.cli.commands.agent import mission_finalize as seam
from specify_cli.ownership import validation as ownership_validation
from specify_cli.ownership.models import OwnershipManifest, WorkProductKind
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


def test_collect_finalize_artifacts_omits_dossiers_candidate_for_unsafe_slug(
    tmp_path: Path,
) -> None:
    """#2037: an unsafe ``--mission`` slug must not escape the dossiers join.

    The dossiers-snapshot candidate is the only entry keyed on ``mission_slug``
    directly; every other candidate is keyed on the already-resolved
    ``feature_dir``/``tasks_dir``. A hostile slug must be dropped (fail-closed
    by omission, not by raising) while the rest of the candidate list is
    collected as usual.
    """
    feature = tmp_path / "kitty-specs" / "001-m"
    tasks = feature / "tasks"
    tasks.mkdir(parents=True)
    (feature / "tasks.md").write_text("x", encoding="utf-8")
    # A file that a traversal payload could plausibly resolve to, so the
    # assertion is "never collected", not just "path string never equal".
    # ``feature/.kittify/dossiers/../evil/snapshot-latest.json`` resolves to
    # ``feature/.kittify/evil/snapshot-latest.json``; the ``dossiers/`` dir must
    # exist for the unguarded join to traverse there, otherwise the test is vacuous.
    (feature / ".kittify" / "dossiers").mkdir(parents=True)
    escape_target = feature / ".kittify" / "evil" / "snapshot-latest.json"
    escape_target.parent.mkdir(parents=True)
    escape_target.write_text("x", encoding="utf-8")

    artifacts = seam._collect_finalize_artifacts(feature, tasks, "../evil")

    assert (feature / "tasks.md") in artifacts
    assert escape_target not in artifacts
    assert not any(".kittify" in p.parts and "dossiers" in p.parts for p in artifacts)


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
# _classify_wp_requirement_refs (WP02 campsite-clean extraction)
# ---------------------------------------------------------------------------


def test_classify_wp_requirement_refs_buckets_missing_unknown_mapped() -> None:
    missing, unknown, mapped = seam._classify_wp_requirement_refs(
        ["WP01", "WP02", "WP03"],
        {"WP01": [], "WP02": ["FR-999"], "WP03": ["FR-001", "FR-002"]},
        {"FR-001", "FR-002"},
    )
    assert missing == ["WP01"]
    assert unknown == {"WP02": ["FR-999"]}
    assert mapped == {"FR-001", "FR-002"}


def test_classify_wp_requirement_refs_dedupes_and_sorts_wp_ids() -> None:
    # Duplicate wp_ids collapse via `sorted(set(...))`; unsorted input still
    # produces deterministic (sorted) bucket membership.
    missing, unknown, mapped = seam._classify_wp_requirement_refs(
        ["WP02", "WP01", "WP01"],
        {},
        set(),
    )
    assert missing == ["WP01", "WP02"]
    assert unknown == {}
    assert mapped == set()


# ---------------------------------------------------------------------------
# _emit_requirement_mapping_report (WP02 campsite-clean extraction)
# ---------------------------------------------------------------------------


def test_emit_requirement_mapping_report_json(capsys: pytest.CaptureFixture[str]) -> None:
    seam._emit_requirement_mapping_report(
        json_output=True,
        missing_requirement_refs_wps=["WP01"],
        unknown_requirement_refs={"WP02": ["FR-999"]},
        unmapped_functional_requirements=["FR-002"],
        bare_prose_requirement_ids=[],
        wp_dependencies={"WP01": []},
        wp_requirement_refs={"WP02": ["FR-999"]},
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "error": "Requirement mapping validation failed",
        "missing_requirement_refs_wps": ["WP01"],
        "unknown_requirement_refs": {"WP02": ["FR-999"]},
        "unmapped_functional_requirements": ["FR-002"],
        "bare_prose_requirement_ids": [],
        "dependencies_parsed": {"WP01": []},
        "requirement_refs_parsed": {"WP02": ["FR-999"]},
    }


def test_emit_requirement_mapping_report_console(capsys: pytest.CaptureFixture[str]) -> None:
    seam._emit_requirement_mapping_report(
        json_output=False,
        missing_requirement_refs_wps=["WP01"],
        unknown_requirement_refs={"WP02": ["FR-999"]},
        unmapped_functional_requirements=["FR-002"],
        bare_prose_requirement_ids=[],
        wp_dependencies={"WP01": []},
        wp_requirement_refs={"WP02": ["FR-999"]},
    )
    output = re.sub(r"\x1b\[[0-9;]*m", "", capsys.readouterr().out)
    assert "Requirement mapping validation failed" in output
    assert "Missing requirement refs:" in output
    assert "- WP01" in output
    assert "Unknown requirement refs:" in output
    assert "- WP02: FR-999" in output
    assert "Unmapped functional requirements:" in output
    assert "- FR-002" in output


def test_emit_requirement_mapping_report_json_includes_bare_prose_ids(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """WP06 (#3396): ``bare_prose_requirement_ids`` is additive, never merged
    into ``unmapped_functional_requirements``."""
    seam._emit_requirement_mapping_report(
        json_output=True,
        missing_requirement_refs_wps=[],
        unknown_requirement_refs={},
        unmapped_functional_requirements=[],
        bare_prose_requirement_ids=["FR-001", "FR-002"],
        wp_dependencies={"WP01": []},
        wp_requirement_refs={"WP01": ["NFR-001"]},
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["bare_prose_requirement_ids"] == ["FR-001", "FR-002"]
    assert payload["unmapped_functional_requirements"] == []


def test_emit_requirement_mapping_report_console_includes_bare_prose_ids(
    capsys: pytest.CaptureFixture[str],
) -> None:
    seam._emit_requirement_mapping_report(
        json_output=False,
        missing_requirement_refs_wps=[],
        unknown_requirement_refs={},
        unmapped_functional_requirements=[],
        bare_prose_requirement_ids=["FR-001", "FR-002"],
        wp_dependencies={"WP01": []},
        wp_requirement_refs={"WP01": ["NFR-001"]},
    )
    output = re.sub(r"\x1b\[[0-9;]*m", "", capsys.readouterr().out)
    assert "Bare-prose requirement id(s) found, uncounted:" in output
    assert "- FR-001" in output
    assert "- FR-002" in output


# ---------------------------------------------------------------------------
# WP06 (#3396) T031/T033: bare-prose requirement ids wired into
# _validate_requirement_mapping (Story 1 AC1/AC2 -- the issue's exact repro).
# ---------------------------------------------------------------------------

#: The issue's exact repro Functional Requirements section: FR-001/FR-002
#: written as bare, unbulleted, unbolded prose alongside a properly DECLARED
#: NFR-001 table row in the SAME section.
_BARE_PROSE_REPRO_SPEC = (
    "### Functional Requirements\n\n"
    "FR-001 the loader must reject an unknown pack.\n"
    "FR-002 the error must name the offending path.\n\n"
    "| ID | Requirement |\n"
    "|----|-------------|\n"
    "| NFR-001 | Resolution completes within 200ms |\n"
)


def test_requirement_mapping_rejects_bare_prose_requirement_ids(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Story 1 AC1/AC2: the repro spec.md fails ``finalize-tasks``'s
    requirement-mapping gate even though every WP's own missing/unknown/
    unmapped bucket is otherwise clean -- naming FR-001/FR-002 explicitly in
    a distinct field, never merely appended to
    ``requirement_extraction_warnings`` (which this call site does not even
    see)."""
    with pytest.raises(typer.Exit):
        seam._validate_requirement_mapping(
            ["WP01"],
            {"WP01": ["NFR-001"]},
            {"NFR-001"},
            set(),
            {"WP01": []},
            _BARE_PROSE_REPRO_SPEC,
            json_output=True,
        )
    payload = json.loads(capsys.readouterr().out)
    assert payload["bare_prose_requirement_ids"] == ["FR-001", "FR-002"]
    assert payload["unmapped_functional_requirements"] == []
    assert payload["missing_requirement_refs_wps"] == []
    assert payload["unknown_requirement_refs"] == {}


def test_requirement_mapping_passes_when_spec_content_defaults_empty() -> None:
    """Backward-compat: the pre-existing 5-positional-arg call shape (no
    ``spec_content``) still passes cleanly -- the new parameter's default
    ("") detects zero bare-prose ids."""
    seam._validate_requirement_mapping(
        ["WP01"],
        {"WP01": ["FR-001"]},
        {"FR-001"},
        {"FR-001"},
        {"WP01": []},
        json_output=True,
    )


def test_requirement_mapping_bare_prose_detection_is_fail_loud(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """WP06 (#3396) IC-04 fault injection: a detector exception becomes an
    explicit, non-empty failure (NFR-002) -- never a swallowed "0 uncounted"
    result -- even though every WP mapping bucket is otherwise clean."""
    import specify_cli.requirement_mapping as req_mapping_module

    def _boom(_spec_content: str) -> list[object]:
        raise RuntimeError("boom")

    monkeypatch.setattr(req_mapping_module, "find_bare_prose_requirement_ids", _boom)
    with pytest.raises(typer.Exit):
        seam._validate_requirement_mapping(
            ["WP01"],
            {"WP01": ["FR-001"]},
            {"FR-001"},
            {"FR-001"},
            {"WP01": []},
            "irrelevant spec content",
            json_output=True,
        )
    payload = json.loads(capsys.readouterr().out)
    assert payload["bare_prose_requirement_ids"], "expected a non-empty failure entry"
    assert "boom" in payload["bare_prose_requirement_ids"][0]


# ---------------------------------------------------------------------------
# _read_spec_requirement_ids (WP06 T031 plumbing fix: also returns spec_content)
# ---------------------------------------------------------------------------


def test_read_spec_requirement_ids_also_returns_raw_spec_content(tmp_path: Path) -> None:
    planning_dir = tmp_path
    (planning_dir / "spec.md").write_text(_BARE_PROSE_REPRO_SPEC, encoding="utf-8")
    all_ids, functional_ids, _warnings, spec_content = seam._read_spec_requirement_ids(
        planning_dir, json_output=True
    )
    assert all_ids == {"NFR-001"}
    assert functional_ids == set()
    assert spec_content == _BARE_PROSE_REPRO_SPEC


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
    changed, warnings, contradiction = seam._apply_ownership_inference(bld, meta, "body", "001-m", {})
    assert changed is False
    assert warnings == []
    assert contradiction is None


# ---------------------------------------------------------------------------
# T009: FR-002 direct-seam contradiction descriptor shape
# ---------------------------------------------------------------------------


def test_apply_ownership_inference_flags_code_change_with_explicit_empty_owned_files() -> None:
    """FR-002 (Acceptance Scenario 1): ``execution_mode: code_change`` combined
    with an explicit ``owned_files: []`` is an authoring contradiction, not
    intent -- the seam must detect it and return a non-``None`` descriptor
    naming the WP ID, WITHOUT raising itself (the aggregated raise lives in
    ``_run_bootstrap_loop``, T010)."""
    raw = "---\nwork_package_id: WP03\nexecution_mode: code_change\nowned_files: []\n---\nbody\n"
    meta = WPMetadata(work_package_id="WP03", title="t", execution_mode="code_change")
    bld = meta.builder()
    changed, warnings, contradiction = seam._apply_ownership_inference(bld, meta, raw, "001-m", {})
    assert changed is False
    assert warnings == []
    assert contradiction is not None
    assert "WP03" in contradiction


def test_apply_ownership_inference_accepts_planning_artifact_with_explicit_empty_owned_files() -> None:
    """FR-002 (Acceptance Scenario 3): ``execution_mode: planning_artifact``
    with the SAME explicit ``owned_files: []`` remains the existing,
    legitimate escape hatch -- the fix must not touch this path.
    ``descriptor`` must be exactly ``None`` (the "absent" case), not an empty
    string or empty-list slot."""
    raw = "---\nwork_package_id: WP04\nexecution_mode: planning_artifact\nowned_files: []\n---\nbody\n"
    meta = WPMetadata(work_package_id="WP04", title="t", execution_mode="planning_artifact")
    bld = meta.builder()
    changed, warnings, contradiction = seam._apply_ownership_inference(bld, meta, raw, "001-m", {})
    assert contradiction is None


def _ownership_wp_file(tmp_path: Path, name: str, wp_id: str, *, execution_mode: str, owned_files_yaml: str) -> Path:
    """Write a WP file exercising the FR-002 ownership-contradiction seam.

    ``owned_files_yaml`` is the raw YAML value line(s) (including a trailing
    newline), e.g. ``"owned_files: []\\n"`` or ``"owned_files:\\n  - src/x.py\\n"``.
    """
    f = tmp_path / name
    f.write_text(
        f"---\nwork_package_id: {wp_id}\ntitle: t\nexecution_mode: {execution_mode}\n{owned_files_yaml}---\nbody\n",
        encoding="utf-8",
    )
    return f


def test_run_bootstrap_loop_accepts_planning_artifact_explicit_empty_owned_files(tmp_path: Path) -> None:
    """FR-002 (Acceptance Scenario 3), full pipeline via ``_run_bootstrap_loop``
    ONLY (this file's own module docstring reserves end-to-end
    ``finalize_tasks`` coverage for other files; zero ``CliRunner`` usage here).

    Revert-sensitivity: reverting the FR-002 production fix (which currently
    only ADDS a contradiction branch that ``continue``s away offending WPs --
    a planning_artifact WP is never routed into that branch either way) does
    NOT flip this test red by itself, because a planning_artifact WP was
    already accepted before this mission. What DOES discriminate is asserting
    on ``state.inmemory_frontmatter`` / ``state.ownership_contradictions``
    (populated only AFTER the contradiction check runs) rather than
    ``state.work_packages`` (appended unconditionally at line ~1351, BEFORE
    ``_apply_ownership_inference`` is even called at ~1365 -- a WP that
    ``continue``s on a contradiction has already been appended there, so it
    cannot discriminate accepted-vs-rejected). This test exists to prove the
    legitimate escape hatch keeps working end-to-end through the loop, not
    merely at the direct-seam level (test above).
    """
    wp_id = "WP01"
    wp_file = _ownership_wp_file(
        tmp_path, "WP01.md", wp_id, execution_mode="planning_artifact", owned_files_yaml="owned_files: []\n"
    )
    state = seam._run_bootstrap_loop(
        [wp_file],
        seam._DependencyResolution(),
        None,
        "001-m",
        tmp_path,
        "main",
        [],
        [],
        validate_only=True,
        json_output=True,
    )
    assert wp_id in state.inmemory_frontmatter
    assert state.inmemory_frontmatter[wp_id].owned_files == []
    assert state.inmemory_frontmatter[wp_id].execution_mode == "planning_artifact"
    assert wp_id not in state.ownership_contradictions
    assert all(wp_id not in msg for msg in state.ownership_contradictions)


# ---------------------------------------------------------------------------
# T010: FR-002 aggregated raise via _run_bootstrap_loop
# ---------------------------------------------------------------------------


def test_run_bootstrap_loop_raises_for_single_ownership_contradiction(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-002 (Acceptance Scenarios 1+2): a single ``code_change`` WP with an
    explicit ``owned_files: []`` makes ``_run_bootstrap_loop`` raise once the
    loop completes, naming the offending WP ID and the specific contradiction
    in a stable, machine-readable JSON field.

    Revert: reverting T015's production fix removes the ``ownership_contradiction
    is not None`` branch (and the post-loop aggregated raise) from
    ``_run_bootstrap_loop``, and reverts ``_apply_ownership_inference`` back to
    its old 2-tuple return that never detects this case -- ``_run_bootstrap_loop``
    would then return normally instead of raising, so ``pytest.raises(typer.Exit)``
    fails with "DID NOT RAISE".
    """
    wp_file = _ownership_wp_file(
        tmp_path, "WP01.md", "WP01", execution_mode="code_change", owned_files_yaml="owned_files: []\n"
    )
    with pytest.raises(typer.Exit):
        seam._run_bootstrap_loop(
            [wp_file],
            seam._DependencyResolution(),
            None,
            "001-m",
            tmp_path,
            "main",
            [],
            [],
            validate_only=True,
            json_output=True,
        )
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_code"] == seam.OWNERSHIP_CONTRADICTION_CODE_CHANGE_EMPTY_OWNED_FILES
    assert payload["ownership_contradiction_wp_ids"] == ["WP01"]
    assert "WP01" in payload["error"]
    assert "code_change WP declares no owned files" in payload["error"]


def test_run_bootstrap_loop_raises_naming_every_offender_in_a_batch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-002 (Acceptance Scenario 4): a mission with a MIX of WPs -- two
    contradicting, one validly authored -- fails the run and names EVERY
    offending WP in the single aggregated error, rather than silently
    dropping only the bad WPs and proceeding to compute lanes for the rest.

    Revert-sensitivity: pre-fix, ``_apply_ownership_inference`` never detects
    the contradiction at all (2-tuple return, no descriptor), so every WP --
    including the two ``owned_files: []`` ones -- is silently accepted and
    the loop returns normally; ``pytest.raises(typer.Exit)`` fails with "DID
    NOT RAISE". Post-fix, only WP01/WP02 are named -- WP03 (validly authored)
    must NOT appear in the offender list, proving the aggregation is precise.
    """
    wp1 = _ownership_wp_file(
        tmp_path, "WP01.md", "WP01", execution_mode="code_change", owned_files_yaml="owned_files: []\n"
    )
    wp2 = _ownership_wp_file(
        tmp_path, "WP02.md", "WP02", execution_mode="code_change", owned_files_yaml="owned_files: []\n"
    )
    wp3 = _ownership_wp_file(
        tmp_path,
        "WP03.md",
        "WP03",
        execution_mode="code_change",
        owned_files_yaml="owned_files:\n  - src/x.py\n",
    )
    with pytest.raises(typer.Exit):
        seam._run_bootstrap_loop(
            [wp1, wp2, wp3],
            seam._DependencyResolution(),
            None,
            "001-m",
            tmp_path,
            "main",
            [],
            [],
            validate_only=True,
            json_output=True,
        )
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["ownership_contradiction_wp_ids"]) == {"WP01", "WP02"}
    assert "WP03" not in payload["ownership_contradiction_wp_ids"]


# ---------------------------------------------------------------------------
# T012/T013: FR-003 -- _compute_and_write_lanes raises on both halves of the
# compound guard, instead of silently returning (None, None)
# ---------------------------------------------------------------------------


def test_compute_and_write_lanes_raises_when_wp_manifests_empty(tmp_path: Path) -> None:
    """FR-003 (Acceptance Scenario 1) + T013 step 2's residual-gap coverage
    (Acceptance Scenario 6): an empty ``wp_manifests`` makes
    ``_compute_and_write_lanes`` raise instead of returning ``(None, None)``.

    Revert-sensitivity: pre-fix, the function returns ``(None, None)``
    without ever calling ``write_lanes_json`` -- ``lanes.json`` is already
    absent both before AND after the fix, so an absence-only assertion would
    be VACUOUS (pre-fix == post-fix). The actual revert-sensitive assertion
    is the ``pytest.raises(typer.Exit)`` block itself: reverting FR-003's
    raise back to ``return None, None`` makes this fail with "DID NOT RAISE".
    The absence check below is only a secondary, defense-in-depth assertion.

    Residual-gap note (NFR-004's narrowed scope, ledger SK-71): this test
    does NOT assert WP-frontmatter or event-log absence -- for an FR-003
    reject, the current (frozen) pipeline order in ``finalize_tasks`` already
    ran ``_flush_frontmatter_writes`` and ``_emit_local_canonical_events``
    before this function is ever reached, so those side effects are NOT
    guaranteed absent. Only ``lanes.json`` absence is guaranteed by this fix.
    Asserting the broader guarantee here would be a false claim a future
    reader might "fix" the test into making -- do not add it.
    """
    planning_dir = tmp_path / "kitty-specs" / "001-test"
    planning_dir.mkdir(parents=True)
    with pytest.raises(typer.Exit):
        seam._compute_and_write_lanes(
            planning_dir,
            tmp_path,
            "001-test",
            {},
            {"WP01": []},
            {},
            {},
            None,
            "main",
            json_output=True,
        )
    assert not (planning_dir / "lanes.json").exists()


def test_compute_and_write_lanes_raises_when_wp_dependencies_empty(tmp_path: Path) -> None:
    """FR-003 (Acceptance Scenario 5): ``wp_manifests`` non-empty but
    ``wp_dependencies`` empty ALSO raises -- proves the fix covers the WHOLE
    compound guard (``not (wp_manifests and wp_dependencies)``), not only the
    ``wp_manifests``-empty half exercised above.

    Revert: reverting FR-003's fix restores ``return None, None`` for this
    half of the guard too, so ``pytest.raises(typer.Exit)`` fails with "DID
    NOT RAISE".
    """
    planning_dir = tmp_path / "kitty-specs" / "001-test"
    planning_dir.mkdir(parents=True)
    manifest = OwnershipManifest(
        execution_mode=WorkProductKind.CODE_CHANGE,
        owned_files=("src/x.py",),
        authoritative_surface="src/",
    )
    with pytest.raises(typer.Exit):
        seam._compute_and_write_lanes(
            planning_dir,
            tmp_path,
            "001-test",
            {"WP01": manifest},
            {},
            {},
            {},
            None,
            "main",
            json_output=True,
        )
    assert not (planning_dir / "lanes.json").exists()


# ---------------------------------------------------------------------------
# T014: FR-004 -- authoritative_surface validation runs unconditionally, not
# gated on wp_manifests being non-empty
# ---------------------------------------------------------------------------


def test_validate_ownership_manifests_catches_malformed_authoritative_surface_when_wp_manifests_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """FR-004 (Acceptance Scenario 3): a ``code_change`` WP with a malformed
    (empty-string) ``authoritative_surface`` is rejected even though the
    CALLER's ``wp_manifests`` view is empty -- ``build_wp_manifests`` would
    have included this exact WP (``execution_mode`` + ``owned_files`` both
    truthy) had it been derived directly from ``wp_frontmatters``; passing an
    empty ``wp_manifests`` here proves ``_validate_ownership_manifests`` no
    longer trusts that emptiness as "nothing to check" -- the old
    ``if not wp_manifests: return`` short-circuit silently skipped this.

    Revert-sensitivity: reverting the FR-004 fix restores the short-circuit,
    so the call returns silently instead of raising -- ``pytest.raises``
    fails with "DID NOT RAISE".
    """
    wp_frontmatters = {
        "WP01": WPMetadata(
            work_package_id="WP01",
            title="t",
            execution_mode="code_change",
            owned_files=["src/x.py"],
            authoritative_surface="",
        )
    }
    state = seam._BootstrapState()
    with pytest.raises(typer.Exit):
        seam._validate_ownership_manifests({}, wp_frontmatters, tmp_path, state, json_output=True)
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "Ownership validation failed"
    assert any("WP01" in e and "authoritative_surface" in e for e in payload["ownership_errors"])


def test_validate_ownership_manifests_accepts_valid_authoritative_surface_when_wp_manifests_empty(
    tmp_path: Path,
) -> None:
    """FR-004 (Acceptance Scenario 4): the sibling acceptance direction --
    ``wp_manifests`` empty but every ``authoritative_surface`` value is a
    genuinely valid prefix. The mission must pass exactly as it would with a
    non-empty manifest map -- this proves the fix does not turn a
    legitimately-empty, legitimately-valid mission into a spurious failure.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "x.py").write_text("x", encoding="utf-8")
    wp_frontmatters = {
        "WP01": WPMetadata(
            work_package_id="WP01",
            title="t",
            execution_mode="code_change",
            owned_files=["src/x.py"],
            authoritative_surface="src/",
        )
    }
    state = seam._BootstrapState()
    # Must NOT raise.
    seam._validate_ownership_manifests({}, wp_frontmatters, tmp_path, state, json_output=True)


# ---------------------------------------------------------------------------
# WP02-001 drift guard: _resolve_wp_manifests_for_validation must REUSE
# build_wp_manifests's inclusion predicate, never restate it inline.
# ---------------------------------------------------------------------------


def test_resolve_wp_manifests_for_validation_delegates_to_build_wp_manifests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mechanical proof of delegation, not restatement.

    Replace ``build_wp_manifests`` (imported into this module's namespace)
    with a canary that ignores the real predicate and returns a fixed
    sentinel manifest. If ``_resolve_wp_manifests_for_validation`` calls
    ``build_wp_manifests`` -- as it must -- the canary's output flows
    straight through. If a future edit reverts to an inline copy of the
    ``execution_mode and owned_files`` predicate instead (the exact drift
    WP02-001 flagged), the monkeypatch has no effect: the function derives
    its own answer for "WP01" and the canary's "CANARY" entry never appears,
    so the assertion below fails.
    """
    wp_frontmatters = {
        "WP01": WPMetadata(
            work_package_id="WP01",
            execution_mode="code_change",
            owned_files=["src/x.py"],
            authoritative_surface="src/",
        )
    }
    canary = OwnershipManifest(
        execution_mode=WorkProductKind.CODE_CHANGE,
        owned_files=("canary/only.py",),
        authoritative_surface="canary/",
    )

    def fake_build_wp_manifests(frontmatters: dict) -> dict:
        assert frontmatters is wp_frontmatters
        return {"CANARY": canary}

    monkeypatch.setattr(seam, "build_wp_manifests", fake_build_wp_manifests)

    result = seam._resolve_wp_manifests_for_validation({}, wp_frontmatters)

    assert result == {"CANARY": canary}


def test_resolve_wp_manifests_for_validation_matches_build_wp_manifests_selection(
    tmp_path: Path,
) -> None:
    """Behaviour-preservation: WP selection is identical to calling
    ``build_wp_manifests`` directly on the same frontmatter, for both the
    normal (code_change) case and the SK-24 ``planning_artifact`` /
    ``owned_files: []`` escape hatch. Exercised against the REAL (unpatched)
    predicate, unlike the delegation test above.
    """
    wp_frontmatters = {
        "WP01": WPMetadata(
            work_package_id="WP01",
            execution_mode="code_change",
            owned_files=["src/x.py"],
            authoritative_surface="src/",
        ),
        "WP02": WPMetadata(
            work_package_id="WP02",
            title="planning wp",
            execution_mode="planning_artifact",
            owned_files=[],
            authoritative_surface="",
        ),
        "WP03": WPMetadata(work_package_id="WP03", title="undeclared"),
    }
    expected = ownership_validation.build_wp_manifests(wp_frontmatters)

    resolved_from_empty = seam._resolve_wp_manifests_for_validation({}, wp_frontmatters)
    assert resolved_from_empty == expected
    assert set(resolved_from_empty) == {"WP01"}  # WP02 (escape hatch) and WP03 stay excluded

    # A non-empty wp_manifests view wins the merge for keys it already has,
    # and re-derived entries still land for everything else -- same set as
    # calling build_wp_manifests directly would produce.
    preexisting = {"WP01": OwnershipManifest.from_frontmatter(wp_frontmatters["WP01"])}
    resolved_from_nonempty = seam._resolve_wp_manifests_for_validation(preexisting, wp_frontmatters)
    assert set(resolved_from_nonempty) == set(expected)


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


def test_owned_files_kitty_specs_gate_exempts_confined_planning_wp() -> None:
    """A ``planning_artifact`` WP confined to planning surfaces is exempt from the
    kitty-specs ban and does not raise (#3222 / #2643, FR-001/FR-004)."""
    meta = WPMetadata(
        work_package_id="WP01",
        title="t",
        execution_mode="planning_artifact",
        owned_files=["kitty-specs/001-m/disposition-matrix.md"],
    )
    seam._validate_owned_files_not_in_mission_specs({"WP01": meta}, json_output=True)


def test_owned_files_kitty_specs_gate_rejects_mislabeled_planning_owning_code() -> None:
    """Confinement (FR-004, INV-4): a ``planning_artifact`` WP that also owns a
    ``src/`` path is NOT exempted — the kitty-specs path still trips the ban."""
    meta = WPMetadata(
        work_package_id="WP01",
        title="t",
        execution_mode="planning_artifact",
        owned_files=["kitty-specs/001-m/spec.md", "src/foo.py"],
    )
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
