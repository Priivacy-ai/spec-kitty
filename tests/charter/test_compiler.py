"""Scope: mock-boundary tests for charter compiler bundle generation -- no real git."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from charter.catalog import DoctrineCatalog, load_doctrine_catalog
from charter.compiler import _resolve_template_set, compile_charter, write_compiled_charter
from charter.interview import (
    CharterInterview,
    LocalSupportDeclaration,
    apply_answer_overrides,
    default_interview,
    validate_local_support_declarations,
)

pytestmark = pytest.mark.fast


def test_compile_charter_contains_governance_activation_block() -> None:
    """Compiled charter includes mission metadata and governance activation section."""
    # Arrange
    interview = default_interview(mission="software-dev", profile="minimal")

    # Assumption check
    assert interview.mission == "software-dev", "interview must be for software-dev"

    # Act
    compiled = compile_charter(mission="software-dev", interview=interview)

    # Assert
    assert compiled.mission == "software-dev"
    assert compiled.template_set == "software-dev-default"
    assert "## Governance Activation" in compiled.markdown
    assert "selected_directives" in compiled.markdown
    assert "available_tools: [git, spec-kitty]" in compiled.markdown


def test_resolve_template_set_uses_smallest_available_fallback() -> None:
    catalog = DoctrineCatalog(
        template_sets={"zeta-default", "alpha-default"},
        paradigms=[],
        directives=[],
        tactics=[],
        styleguides=[],
        toolguides=[],
        procedures=[],
        agent_profiles=[],
    )

    assert (
        _resolve_template_set(
            mission="software-dev",
            requested_template_set=None,
            catalog=catalog,
        )
        == "alpha-default"
    )


def test_compile_charter_preserves_explicit_empty_selections() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(
        interview,
        selected_paradigms=[],
        selected_directives=[],
        available_tools=[],
    )

    compiled = compile_charter(mission="software-dev", interview=interview)

    assert compiled.selected_paradigms == []
    assert compiled.selected_directives == []
    assert compiled.available_tools == []
    assert "selected_paradigms: []" in compiled.markdown
    assert "selected_directives: []" in compiled.markdown
    assert "available_tools: []" in compiled.markdown


def test_compile_charter_renders_lynn_cole_rules_verbatim() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(
        interview,
        answers={"project_intent": "Use the Lynn Cole."},
    )

    compiled = compile_charter(mission="software-dev", interview=interview)

    assert compiled.selected_directives == ["DIRECTIVE_039"]
    assert compiled.selected_paradigms == ["deep-module-design"]
    assert "Lynn Cole Engineering Culture (`DIRECTIVE_039`)" in compiled.markdown
    assert "Remember the three rules of TDD, and hold them sacred." in compiled.markdown
    assert "Strong typing is a requirement on all projects." in compiled.markdown
    assert "DRY is about preserving a single source of truth" in compiled.markdown
    assert "Your code will be reviewed by the meanest, most inconsiderate QA agent" in compiled.markdown


def test_compile_charter_renders_selected_directive_content() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(
        interview,
        selected_directives=["DIRECTIVE_003"],
    )

    compiled = compile_charter(mission="software-dev", interview=interview)

    assert "Apply doctrine directive `DIRECTIVE_003`" not in compiled.markdown
    assert "Decision Documentation Requirement (`DIRECTIVE_003`)" in compiled.markdown
    assert "Material technical and governance decisions must be captured" in compiled.markdown
    assert "Integrity rule: High-impact decisions cannot remain tribal knowledge." in compiled.markdown


def test_compile_charter_renders_agent_profile_metadata_when_present() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(interview, agent_profile="reviewer", agent_role="reviewer")

    compiled = compile_charter(mission="software-dev", interview=interview)

    assert "agent_profile: reviewer" in compiled.markdown
    assert "agent_role: reviewer" in compiled.markdown


def test_write_compiled_charter_writes_bundle(tmp_path: Path) -> None:
    """write_compiled_charter creates charter.md, references.yaml, and library files."""
    # Arrange
    interview = default_interview(mission="software-dev", profile="minimal")
    compiled = compile_charter(mission="software-dev", interview=interview)

    # Assumption check
    assert not (tmp_path / "charter.md").exists(), "target directory must be empty"

    # Act
    result = write_compiled_charter(tmp_path, compiled, force=True)

    # Assert
    assert "charter.md" in result.files_written
    assert "references.yaml" in result.files_written
    assert (tmp_path / "charter.md").exists()
    assert (tmp_path / "references.yaml").exists()

    # library/ materialization has been removed; no files should exist there.
    assert not (tmp_path / "library").exists()


def test_write_compiled_charter_persists_structured_languages_for_round_trip(tmp_path: Path) -> None:
    """WP02/T008+T009: compiled charter's languages field survives a disk round-trip.

    Compiles a charter from an interview mentioning Rust, writes the bundle,
    then reads ``infer_repo_languages`` against the same repo root -- a fresh
    call, not reused in-memory state -- to prove the structured field is the
    canonical value read back from ``references.yaml`` on disk.
    """
    from charter.language_scope import infer_repo_languages

    interview = apply_answer_overrides(
        default_interview(mission="software-dev", profile="minimal"),
        answers={"languages_frameworks": "Rust services with cargo and rustc tooling"},
    )
    compiled = compile_charter(mission="software-dev", interview=interview)

    assert compiled.active_languages == ["rust"], "compile_charter must compute the structured field"

    charter_dir = tmp_path / ".kittify" / "charter"
    write_compiled_charter(charter_dir, compiled, force=True)

    references_text = (charter_dir / "references.yaml").read_text(encoding="utf-8")
    assert "languages:" in references_text, "languages field must be persisted to references.yaml on disk"

    # Fresh resolution call reading only from disk -- proves the round-trip,
    # not just the in-memory CompiledCharter value from this same call.
    assert infer_repo_languages(tmp_path) == ["rust"]


def test_write_compiled_charter_requires_force_when_existing(tmp_path: Path) -> None:
    """Writing to an existing bundle raises FileExistsError when force=False."""
    # Arrange
    interview = default_interview(mission="software-dev", profile="minimal")
    compiled = compile_charter(mission="software-dev", interview=interview)
    write_compiled_charter(tmp_path, compiled, force=True)

    # Assumption check
    assert (tmp_path / "charter.md").exists(), "first write must have succeeded"

    # Act / Assert
    with pytest.raises(FileExistsError):
        write_compiled_charter(tmp_path, compiled, force=False)


@pytest.mark.requires_symlinks
def test_write_compiled_charter_refuses_symlinked_charter(tmp_path: Path) -> None:
    """Generate must not write through a symlinked charter into an external public doc."""
    public_dir = tmp_path / "spec"
    public_dir.mkdir()
    public_charter = public_dir / "constitution.md"
    public_charter.write_text("# Public Constitution\n", encoding="utf-8")

    output_dir = tmp_path / ".kittify" / "charter"
    output_dir.mkdir(parents=True)
    charter_link = output_dir / "charter.md"
    try:
        charter_link.symlink_to(public_charter)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    interview = default_interview(mission="software-dev", profile="minimal")
    compiled = compile_charter(mission="software-dev", interview=interview)

    with pytest.raises(FileExistsError, match="Refusing to overwrite symlinked charter"):
        write_compiled_charter(output_dir, compiled, force=True)

    assert public_charter.read_text(encoding="utf-8") == "# Public Constitution\n"


def test_compile_with_doctrine_service_none_uses_drg_backed_path() -> None:
    """Calling compile_charter without DoctrineService must NOT emit a YAML
    fallback diagnostic.

    Per C-001 of the excise-doctrine-curation-and-inline-references-01KP54J6
    mission there is no YAML-scanning fallback: the compiler constructs a
    default :class:`DoctrineService` internally and always takes the
    DRG-backed path. The compiled result includes tactics / procedures /
    toolguides resolved via the graph, not just paradigms + directives.
    """
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(
        interview,
        selected_directives=["DIRECTIVE_003"],
    )

    compiled = compile_charter(mission="software-dev", interview=interview, doctrine_service=None)

    fallback_msg = (
        "DoctrineService unavailable; using YAML scanning fallback. "
        "Profile-aware compilation requires DoctrineService."
    )
    assert not any(fallback_msg in d for d in compiled.diagnostics), (
        f"Unexpected legacy fallback diagnostic: {compiled.diagnostics}"
    )
    # The DRG-backed path resolves transitive artifacts. With an explicit shipped
    # directive selection the bundled graph should yield at least one tactic.
    kinds = {reference.kind for reference in compiled.references}
    assert "tactic" in kinds, (
        "DRG-backed path should have resolved transitive tactics; "
        f"got kinds {sorted(kinds)}"
    )


def test_compile_with_repo_root_uses_project_drg_overlay(tmp_path: Path) -> None:
    """When repo_root is passed, the project DRG overlay at
    <repo_root>/.kittify/doctrine/graph.yaml participates in transitive
    resolution (exercises the repo_root branch of _build_references and
    _default_doctrine_service).

    Post-merge fix per P2 of the excise-doctrine-curation-and-inline-references-01KP54J6
    mission review.
    """
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(
        interview,
        selected_directives=["DIRECTIVE_003"],
    )

    # An empty project overlay at .kittify/doctrine/graph.yaml is enough
    # to prove the repo_root branch executes load_validated_graph. We use
    # an empty edges/nodes overlay so shipped edges dominate and the
    # compilation still succeeds end-to-end.
    overlay_dir = tmp_path / ".kittify" / "doctrine"
    overlay_dir.mkdir(parents=True)
    (overlay_dir / "graph.yaml").write_text(
        "schema_version: '1.0'\n"
        "generated_at: '2026-04-14T00:00:00+00:00'\n"
        "generated_by: test-compile-with-repo-root\n"
        "nodes: []\n"
        "edges: []\n"
    )

    # Also create a project doctrine overlay dir so _default_doctrine_service
    # exercises the project-root branch (compiler.py lines 267-269).
    (tmp_path / "src" / "doctrine").mkdir(parents=True)

    compiled = compile_charter(
        mission="software-dev",
        interview=interview,
        doctrine_service=None,
        repo_root=tmp_path,
    )
    kinds = {reference.kind for reference in compiled.references}
    # Shipped graph still supplies tactics even with empty project overlay.
    assert "tactic" in kinds, (
        f"repo_root branch should still resolve shipped tactics; got {sorted(kinds)}"
    )


def test_compile_with_repo_root_handles_missing_shipped_graph(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When repo_root is passed but the shipped graph cannot be loaded,
    _build_references falls back to legacy minimal behavior (directives only,
    no transitive resolution). Exercises compiler.py FileNotFoundError branch.
    """
    from charter import _drg_helpers as drg_helpers_module

    interview = default_interview(mission="software-dev", profile="minimal")

    def _raise_fnf(_repo_root: Path) -> object:
        raise FileNotFoundError("synthetic: shipped graph missing")

    monkeypatch.setattr(drg_helpers_module, "load_validated_graph", _raise_fnf)

    compiled = compile_charter(
        mission="software-dev",
        interview=interview,
        doctrine_service=None,
        repo_root=tmp_path,
    )
    # Fallback path: no transitive artifacts beyond directives/paradigms themselves.
    kinds = {reference.kind for reference in compiled.references}
    assert "tactic" not in kinds, (
        f"FileNotFoundError branch should NOT resolve tactics; got {sorted(kinds)}"
    )


def test_compile_with_doctrine_service_uses_repositories() -> None:
    """When DoctrineService is provided, its repositories are queried."""
    interview = default_interview(mission="software-dev", profile="minimal")

    # Build a minimal mock DoctrineService whose repositories return nothing
    # (empty lists / None gets), so the code paths that call .get() and
    # the DRG-backed transitive resolution path is exercised.
    mock_service = MagicMock()
    mock_service.directives.list_all.return_value = []
    mock_service.directives.get.return_value = None
    mock_service.tactics.get.return_value = None
    mock_service.styleguides.get.return_value = None
    mock_service.toolguides.get.return_value = None
    mock_service.procedures.get.return_value = None

    compiled = compile_charter(
        mission="software-dev",
        interview=interview,
        doctrine_service=mock_service,
    )

    # The fallback diagnostic must NOT be present when service is provided
    fallback_msg = "DoctrineService unavailable"
    assert not any(fallback_msg in d for d in compiled.diagnostics), (
        f"Unexpected fallback diagnostic when DoctrineService is present: {compiled.diagnostics}"
    )
    # The compilation still succeeds and produces a valid bundle
    assert compiled.mission == "software-dev"
    assert "## Governance Activation" in compiled.markdown


def test_compile_with_doctrine_service_unknown_directive_in_diagnostics() -> None:
    """Unknown directives surface as a user-visible diagnostic.

    Post-WP03 the DRG is the sole authority for transitive references; any
    directive not in the catalog is dropped by
    ``_sanitize_catalog_selection`` before transitive resolution fires, so
    the diagnostic is emitted by the sanitizer rather than the walker.
    The user-visible signal (a non-silent diagnostic about the bad
    selection) is preserved.
    """
    mock_service = MagicMock()
    mock_service.directives.get.return_value = None
    mock_service.tactics.get.return_value = None
    mock_service.styleguides.get.return_value = None
    mock_service.toolguides.get.return_value = None
    mock_service.procedures.get.return_value = None

    interview_with_directive = default_interview(mission="software-dev", profile="minimal")
    object.__setattr__(
        interview_with_directive, "selected_directives", ["DIRECTIVE_MISSING"]
    )

    compiled = compile_charter(
        mission="software-dev",
        interview=interview_with_directive,
        doctrine_service=mock_service,
    )

    assert any(
        "DIRECTIVE_MISSING" in d for d in compiled.diagnostics
    ), f"Expected a diagnostic about DIRECTIVE_MISSING; got: {compiled.diagnostics}"


# ---------------------------------------------------------------------------
# T006: LocalSupportDeclaration + CharterInterview.local_supporting_files
# ---------------------------------------------------------------------------


def test_charter_interview_local_supporting_files_defaults_to_empty() -> None:
    """local_supporting_files defaults to empty list when not provided."""
    interview = default_interview(mission="software-dev", profile="minimal")
    assert interview.local_supporting_files == []


def test_charter_interview_from_dict_parses_local_supporting_files() -> None:
    data = {
        "mission": "software-dev",
        "profile": "minimal",
        "answers": {},
        "selected_paradigms": [],
        "selected_directives": [],
        "available_tools": [],
        "local_supporting_files": [
            {
                "path": "docs/governance/project-planning.md",
                "action": "plan",
                "target_kind": "directive",
                "target_id": "003-decision-documentation-requirement",
            }
        ],
    }
    interview = CharterInterview.from_dict(data)
    assert len(interview.local_supporting_files) == 1
    decl = interview.local_supporting_files[0]
    assert decl.path == "docs/governance/project-planning.md"
    assert decl.action == "plan"
    assert decl.target_kind == "directive"
    assert decl.target_id == "003-decision-documentation-requirement"


def test_charter_interview_from_dict_ignores_missing_local_supporting_files() -> None:
    data: dict[str, object] = {
        "mission": "software-dev",
        "profile": "minimal",
        "answers": {},
        "selected_paradigms": [],
        "selected_directives": [],
        "available_tools": [],
    }
    interview = CharterInterview.from_dict(data)
    assert interview.local_supporting_files == []


def test_charter_interview_to_dict_omits_local_supporting_files_when_empty() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    d = interview.to_dict()
    assert "local_supporting_files" not in d


def test_charter_interview_to_dict_includes_local_supporting_files_when_present() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    decl = LocalSupportDeclaration(path="docs/my-guide.md", action="implement")
    interview = apply_answer_overrides(interview, local_supporting_files=[decl])
    d = interview.to_dict()
    assert "local_supporting_files" in d
    assert d["local_supporting_files"] == [{"path": "docs/my-guide.md", "action": "implement"}]


def test_local_support_declaration_from_dict_valid() -> None:
    raw = {"path": "docs/guide.md", "action": "review", "target_kind": "tactic", "target_id": "some-tactic"}
    decl = LocalSupportDeclaration.from_dict(raw)
    assert decl is not None
    assert decl.path == "docs/guide.md"
    assert decl.action == "review"
    assert decl.target_kind == "tactic"
    assert decl.target_id == "some-tactic"


def test_local_support_declaration_from_dict_missing_path_returns_none() -> None:
    raw: dict[str, object] = {"action": "plan"}
    assert LocalSupportDeclaration.from_dict(raw) is None


def test_local_support_declaration_from_dict_non_dict_returns_none() -> None:
    assert LocalSupportDeclaration.from_dict("not-a-dict") is None
    assert LocalSupportDeclaration.from_dict(None) is None


# ---------------------------------------------------------------------------
# T007: validate_local_support_declarations
# ---------------------------------------------------------------------------


def test_validate_rejects_glob_star() -> None:
    decls = [LocalSupportDeclaration(path="docs/*.md")]
    valid, errors = validate_local_support_declarations(decls)
    assert valid == []
    assert any("glob" in e for e in errors)


def test_validate_rejects_glob_question_mark() -> None:
    decls = [LocalSupportDeclaration(path="docs/file?.md")]
    valid, errors = validate_local_support_declarations(decls)
    assert valid == []
    assert errors


def test_validate_rejects_glob_bracket() -> None:
    decls = [LocalSupportDeclaration(path="docs/[abc].md")]
    valid, errors = validate_local_support_declarations(decls)
    assert valid == []
    assert errors


def test_validate_rejects_directory_trailing_slash() -> None:
    decls = [LocalSupportDeclaration(path="docs/governance/")]
    valid, errors = validate_local_support_declarations(decls)
    assert valid == []
    assert any("directory" in e for e in errors)


def test_validate_accepts_valid_explicit_path() -> None:
    decls = [LocalSupportDeclaration(path="docs/governance/project-planning.md")]
    valid, errors = validate_local_support_declarations(decls)
    assert len(valid) == 1
    assert errors == []


def test_validate_normalizes_unknown_action_to_none() -> None:
    decls = [LocalSupportDeclaration(path="docs/guide.md", action="deploy")]
    valid, errors = validate_local_support_declarations(decls)
    assert len(valid) == 1
    assert valid[0].action is None
    # An error/warning message should describe the unknown action
    assert any("deploy" in e for e in errors)


def test_validate_accepts_known_actions() -> None:
    for action in ("specify", "plan", "implement", "review"):
        decls = [LocalSupportDeclaration(path="docs/guide.md", action=action)]
        valid, errors = validate_local_support_declarations(decls)
        assert len(valid) == 1
        assert valid[0].action == action
        assert errors == []


def test_validate_mixed_valid_and_invalid() -> None:
    decls = [
        LocalSupportDeclaration(path="docs/guide.md"),
        LocalSupportDeclaration(path="docs/**"),
    ]
    valid, errors = validate_local_support_declarations(decls)
    assert len(valid) == 1
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# T008: Compiler builds additive references with overlap warnings
# ---------------------------------------------------------------------------


def test_compile_with_local_support_file_creates_local_reference() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    decl = LocalSupportDeclaration(path="docs/governance/project-planning.md")
    interview = apply_answer_overrides(interview, local_supporting_files=[decl])

    compiled = compile_charter(mission="software-dev", interview=interview)

    local_refs = [r for r in compiled.references if r.kind == "local_support"]
    assert len(local_refs) == 1
    ref = local_refs[0]
    assert ref.id == "LOCAL:docs/governance/project-planning.md"
    assert ref.source_path == "docs/governance/project-planning.md"


def test_compile_local_support_reference_is_additive_not_replacement() -> None:
    """Local support reference must not replace the shipped directive reference."""
    interview = default_interview(mission="software-dev", profile="minimal")
    directive_id = sorted(load_doctrine_catalog().directives)[0]
    decl = LocalSupportDeclaration(
        path="docs/custom-directive.md",
        target_kind="directive",
        target_id=directive_id,
    )
    interview = apply_answer_overrides(
        interview,
        selected_directives=[directive_id],
        local_supporting_files=[decl],
    )

    compiled = compile_charter(mission="software-dev", interview=interview)

    local_refs = [r for r in compiled.references if r.kind == "local_support"]
    shipped_refs = [r for r in compiled.references if r.kind != "local_support"]
    assert len(local_refs) == 1
    # Shipped refs must still be present
    assert len(shipped_refs) > 0


def test_compile_local_support_overlap_emits_warning_diagnostic() -> None:
    """When local file targets a shipped directive, a diagnostic warning is emitted."""
    interview = default_interview(mission="software-dev", profile="minimal")
    directive_id = sorted(load_doctrine_catalog().directives)[0]
    decl = LocalSupportDeclaration(
        path="docs/custom.md",
        target_kind="directive",
        target_id=directive_id,
    )
    interview = apply_answer_overrides(
        interview,
        selected_directives=[directive_id],
        local_supporting_files=[decl],
    )

    compiled = compile_charter(mission="software-dev", interview=interview)

    assert any("built-in content remains primary" in d for d in compiled.diagnostics), (
        f"Expected overlap warning; diagnostics: {compiled.diagnostics}"
    )


def test_compile_local_support_no_warning_when_no_overlap() -> None:
    """No overlap warning when local file does not target any shipped artifact."""
    interview = default_interview(mission="software-dev", profile="minimal")
    decl = LocalSupportDeclaration(path="docs/custom-note.md")
    interview = apply_answer_overrides(interview, local_supporting_files=[decl])

    compiled = compile_charter(mission="software-dev", interview=interview)

    assert not any("built-in content remains primary" in d for d in compiled.diagnostics)


def test_compile_invalid_local_support_paths_emit_diagnostics() -> None:
    """Glob/dir paths rejected during compilation with diagnostics."""
    interview = default_interview(mission="software-dev", profile="minimal")
    bad_decl = LocalSupportDeclaration(path="docs/**/*.md")
    interview = apply_answer_overrides(interview, local_supporting_files=[bad_decl])

    compiled = compile_charter(mission="software-dev", interview=interview)

    # Invalid declaration must not produce a local_support reference
    local_refs = [r for r in compiled.references if r.kind == "local_support"]
    assert local_refs == []
    # A diagnostic must record the rejection
    assert any("glob" in d for d in compiled.diagnostics)


# ---------------------------------------------------------------------------
# T010: write_compiled_charter does NOT produce library/ directory
# ---------------------------------------------------------------------------


def test_yaml_fallback_resolves_directives_from_shipped_subdirectory() -> None:
    """YAML fallback path must find directives stored in shipped/ subdirectory.

    Regression: _index_yaml_assets scanned the flat doctrine_root/directives/ dir
    but all shipped directives live in doctrine_root/directives/built-in/.  The
    result was every directive reference getting summary='Definition unavailable
    in bundled doctrine.' when DoctrineService was absent.
    """
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(
        interview,
        selected_directives=["DIRECTIVE_003"],
    )

    # Exercise the YAML scanning fallback explicitly (no DoctrineService)
    compiled = compile_charter(mission="software-dev", interview=interview, doctrine_service=None)

    directive_refs = [r for r in compiled.references if r.kind == "directive"]
    assert directive_refs, "Expected at least one directive reference in the compiled bundle"

    unresolved = [r for r in directive_refs if r.summary == "Definition unavailable in bundled doctrine."]
    assert not unresolved, (
        f"Directive(s) not found in shipped/ during YAML fallback: "
        f"{[r.id for r in unresolved]}"
    )


def test_write_compiled_charter_no_library_materialization(tmp_path: Path) -> None:
    """write_compiled_charter must not create library/ directory."""
    interview = default_interview(mission="software-dev", profile="minimal")
    compiled = compile_charter(mission="software-dev", interview=interview)

    result = write_compiled_charter(tmp_path, compiled, force=True)

    assert not (tmp_path / "library").exists()
    # Only charter.md and references.yaml should be written
    assert set(result.files_written) == {"charter.md", "references.yaml"}
