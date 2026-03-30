"""Tests for optional structure template generation during init."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from specify_cli.cli.commands import init as init_module
import pytest
pytestmark = pytest.mark.fast



class _MemoryConsole(Console):
    def __init__(self) -> None:
        super().__init__(force_terminal=False, width=120)


def test_skips_generation_in_non_interactive(tmp_path: Path, monkeypatch) -> None:
    structure_dir = tmp_path / "structure"
    structure_dir.mkdir()
    (structure_dir / "REPO_MAP.md").write_text("repo", encoding="utf-8")
    (structure_dir / "SURFACES.md").write_text("surfaces", encoding="utf-8")

    monkeypatch.setattr(init_module, "_get_structure_templates_dir", lambda: structure_dir)

    init_module._maybe_generate_structure_templates(tmp_path, non_interactive=True, console=_MemoryConsole())

    assert not (tmp_path / ".kittify" / "REPO_MAP.md").exists()
    assert not (tmp_path / ".kittify" / "SURFACES.md").exists()


def test_generates_templates_when_user_accepts(tmp_path: Path, monkeypatch) -> None:
    structure_dir = tmp_path / "structure"
    structure_dir.mkdir()
    (structure_dir / "REPO_MAP.md").write_text("repo-template", encoding="utf-8")
    (structure_dir / "SURFACES.md").write_text("surface-template", encoding="utf-8")

    monkeypatch.setattr(init_module, "_get_structure_templates_dir", lambda: structure_dir)
    monkeypatch.setattr(init_module.typer, "confirm", lambda *args, **kwargs: True)

    init_module._maybe_generate_structure_templates(tmp_path, non_interactive=False, console=_MemoryConsole())

    assert (tmp_path / ".kittify" / "REPO_MAP.md").read_text(encoding="utf-8") == "repo-template"
    assert (tmp_path / ".kittify" / "SURFACES.md").read_text(encoding="utf-8") == "surface-template"


def test_generated_repo_map_has_no_unfilled_placeholders(tmp_path: Path, monkeypatch) -> None:
    """REPO_MAP.md and SURFACES.md written by init must have all {{TOKEN}} placeholders substituted."""
    structure_dir = tmp_path / "structure"
    structure_dir.mkdir()
    (structure_dir / "REPO_MAP.md").write_text(
        "# Repo Map\nGenerated: {{DATE}}\nProject: {{PROJECT_NAME}}\nLanguages: {{PRIMARY_LANGUAGES}}\n",
        encoding="utf-8",
    )
    (structure_dir / "SURFACES.md").write_text(
        "# Surfaces\nGenerated: {{DATE}}\nCLI: {{CLI_ENTRYPOINTS}}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(init_module, "_get_structure_templates_dir", lambda: structure_dir)
    monkeypatch.setattr(init_module.typer, "confirm", lambda *args, **kwargs: True)

    init_module._maybe_generate_structure_templates(tmp_path, non_interactive=False, console=_MemoryConsole())

    import re
    placeholder_re = re.compile(r"\{\{[A-Z_]+\}\}")

    repo_map = (tmp_path / ".kittify" / "REPO_MAP.md").read_text(encoding="utf-8")
    assert not placeholder_re.search(repo_map), (
        f"REPO_MAP.md still contains unfilled placeholders: "
        f"{placeholder_re.findall(repo_map)}"
    )

    surfaces = (tmp_path / ".kittify" / "SURFACES.md").read_text(encoding="utf-8")
    assert not placeholder_re.search(surfaces), (
        f"SURFACES.md still contains unfilled placeholders: "
        f"{placeholder_re.findall(surfaces)}"
    )


class TestDetectLanguages:
    def test_python_from_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'", encoding="utf-8")
        assert "Python" in init_module._detect_languages(tmp_path)

    def test_rust_from_cargo(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text("[package]\nname='x'", encoding="utf-8")
        assert "Rust" in init_module._detect_languages(tmp_path)

    def test_typescript_preferred_over_javascript(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        (tmp_path / "tsconfig.json").write_text("{}", encoding="utf-8")
        result = init_module._detect_languages(tmp_path)
        assert "TypeScript" in result
        assert "JavaScript" not in result

    def test_javascript_when_no_tsconfig(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        assert "JavaScript" in init_module._detect_languages(tmp_path)

    def test_no_indicators_returns_fill_in(self, tmp_path: Path) -> None:
        assert init_module._detect_languages(tmp_path) == "_(fill in)_"

    def test_deduplicates_python(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        (tmp_path / "setup.py").write_text("", encoding="utf-8")
        result = init_module._detect_languages(tmp_path)
        assert result.count("Python") == 1


class TestDetectBuildAndTest:
    def test_makefile(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("test:\n\tpytest", encoding="utf-8")
        assert "`make test`" in init_module._detect_build_and_test(tmp_path)

    def test_pyproject(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
        assert "pytest" in init_module._detect_build_and_test(tmp_path)

    def test_cargo(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text("", encoding="utf-8")
        assert "`cargo test`" in init_module._detect_build_and_test(tmp_path)

    def test_npm(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("{}", encoding="utf-8")
        assert "`npm test`" in init_module._detect_build_and_test(tmp_path)

    def test_empty_returns_fill_in(self, tmp_path: Path) -> None:
        assert init_module._detect_build_and_test(tmp_path) == "_(fill in)_"


class TestDetectCliEntrypoints:
    def test_extracts_scripts(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[project.scripts]\nmy-tool = 'mymod:main'\nother = 'other:run'\n",
            encoding="utf-8",
        )
        result = init_module._detect_cli_entrypoints(tmp_path)
        assert "`my-tool`" in result
        assert "`other`" in result

    def test_oserror_returns_fill_in(self, tmp_path: Path, monkeypatch) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("", encoding="utf-8")
        monkeypatch.setattr(Path, "read_text", lambda *a, **kw: (_ for _ in ()).throw(OSError("boom")))
        assert init_module._detect_cli_entrypoints(tmp_path) == "_(fill in)_"

    def test_no_scripts_section_returns_fill_in(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        assert init_module._detect_cli_entrypoints(tmp_path) == "_(fill in)_"

    def test_no_pyproject_returns_fill_in(self, tmp_path: Path) -> None:
        assert init_module._detect_cli_entrypoints(tmp_path) == "_(fill in)_"


class TestReadFirstParagraph:
    def test_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        assert init_module._read_first_paragraph(tmp_path / "missing.md") == ""

    def test_skips_heading_and_returns_first_paragraph(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# Title\n\nFirst paragraph content.\nSecond line.\n\n## Section\n",
            encoding="utf-8",
        )
        result = init_module._read_first_paragraph(tmp_path / "README.md")
        assert "First paragraph content." in result
        assert "Second line." in result
        assert "Section" not in result

    def test_stops_at_blank_line(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "First para.\n\nSecond para.\n", encoding="utf-8"
        )
        result = init_module._read_first_paragraph(tmp_path / "README.md")
        assert "First para." in result
        assert "Second para." not in result

    def test_heading_mid_paragraph_breaks(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "First para.\n# Heading\n", encoding="utf-8"
        )
        result = init_module._read_first_paragraph(tmp_path / "README.md")
        assert "First para." in result
        assert "Heading" not in result


class TestBuildTreeSnippet:
    def test_lists_non_hidden_entries(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "README.md").write_text("", encoding="utf-8")
        (tmp_path / ".hidden").mkdir()
        result = init_module._build_tree_snippet(tmp_path)
        assert "src/" in result
        assert "README.md" in result
        assert ".hidden" not in result

    def test_marks_directories_with_slash(self, tmp_path: Path) -> None:
        (tmp_path / "mydir").mkdir()
        result = init_module._build_tree_snippet(tmp_path)
        assert "mydir/" in result

    def test_empty_dir_returns_fill_in(self, tmp_path: Path) -> None:
        result = init_module._build_tree_snippet(tmp_path)
        assert result == "_(fill in)_"

    def test_oserror_on_iterdir_returns_fill_in(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(Path, "iterdir", lambda self: (_ for _ in ()).throw(OSError("boom")))
        result = init_module._build_tree_snippet(tmp_path)
        assert result == "_(fill in)_"


class TestGatherStructureTemplateVars:
    def test_all_tokens_present(self, tmp_path: Path) -> None:
        vars = init_module._gather_structure_template_vars(tmp_path)
        required = [
            "{{DATE}}", "{{PROJECT_NAME}}", "{{PRIMARY_LANGUAGES}}", "{{BUILD_AND_TEST}}",
            "{{TREE_SNIPPET}}", "{{SRC_PURPOSE}}", "{{TESTS_PURPOSE}}", "{{DOCS_PURPOSE}}",
            "{{README_SUMMARY}}", "{{PYPROJECT_SUMMARY}}", "{{AGENTS_SUMMARY}}",
            "{{REPO_NOTES}}", "{{CLI_ENTRYPOINTS}}", "{{SERVICE_ENTRYPOINTS}}",
            "{{LIBRARY_ENTRYPOINTS}}", "{{EXTERNAL_INTEGRATIONS}}", "{{PUBLIC_INTERFACES}}",
            "{{LOG_SURFACES}}", "{{METRIC_SURFACES}}", "{{TRACE_SURFACES}}",
            "{{SECURITY_BOUNDARIES}}", "{{SURFACE_NOTES}}",
        ]
        for token in required:
            assert token in vars, f"Missing token: {token}"

    def test_project_name_uses_resolved_path(self, tmp_path: Path) -> None:
        vars = init_module._gather_structure_template_vars(tmp_path)
        assert vars["{{PROJECT_NAME}}"] == tmp_path.resolve().name

    def test_pyproject_description_extracted(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndescription = "My great project"\n', encoding="utf-8"
        )
        vars = init_module._gather_structure_template_vars(tmp_path)
        assert vars["{{PYPROJECT_SUMMARY}}"] == "My great project"

    def test_pyproject_oserror_falls_back_to_fill_in(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
        monkeypatch.setattr(Path, "read_text", lambda *a, **kw: (_ for _ in ()).throw(OSError("boom")))
        vars = init_module._gather_structure_template_vars(tmp_path)
        assert vars["{{PYPROJECT_SUMMARY}}"] == "_(fill in)_"

    def test_no_values_contain_unfilled_token_syntax(self, tmp_path: Path) -> None:
        import re
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("A project.\n", encoding="utf-8")
        vars = init_module._gather_structure_template_vars(tmp_path)
        placeholder_re = re.compile(r"\{\{[A-Z_]+\}\}")
        for token, value in vars.items():
            assert not placeholder_re.search(value), (
                f"Token {token} has value with unfilled placeholder: {value!r}"
            )


def test_skips_when_user_declines(tmp_path: Path, monkeypatch) -> None:
    structure_dir = tmp_path / "structure"
    structure_dir.mkdir()
    (structure_dir / "REPO_MAP.md").write_text("repo", encoding="utf-8")
    (structure_dir / "SURFACES.md").write_text("surfaces", encoding="utf-8")
    monkeypatch.setattr(init_module, "_get_structure_templates_dir", lambda: structure_dir)
    monkeypatch.setattr(init_module.typer, "confirm", lambda *args, **kwargs: False)
    init_module._maybe_generate_structure_templates(tmp_path, non_interactive=False, console=_MemoryConsole())
    assert not (tmp_path / ".kittify" / "REPO_MAP.md").exists()
    assert not (tmp_path / ".kittify" / "SURFACES.md").exists()


def test_does_nothing_when_structure_dir_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(init_module, "_get_structure_templates_dir", lambda: None)
    init_module._maybe_generate_structure_templates(tmp_path, non_interactive=False, console=_MemoryConsole())
    assert not (tmp_path / ".kittify" / "REPO_MAP.md").exists()
    assert not (tmp_path / ".kittify" / "SURFACES.md").exists()


def test_respects_existing_files(tmp_path: Path, monkeypatch) -> None:
    structure_dir = tmp_path / "structure"
    structure_dir.mkdir()
    (structure_dir / "REPO_MAP.md").write_text("repo-template", encoding="utf-8")
    (structure_dir / "SURFACES.md").write_text("surface-template", encoding="utf-8")

    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()
    (kittify_dir / "REPO_MAP.md").write_text("existing", encoding="utf-8")

    monkeypatch.setattr(init_module, "_get_structure_templates_dir", lambda: structure_dir)
    monkeypatch.setattr(init_module.typer, "confirm", lambda *args, **kwargs: True)

    init_module._maybe_generate_structure_templates(tmp_path, non_interactive=False, console=_MemoryConsole())

    assert (kittify_dir / "REPO_MAP.md").read_text(encoding="utf-8") == "existing"
    assert (kittify_dir / "SURFACES.md").read_text(encoding="utf-8") == "surface-template"
