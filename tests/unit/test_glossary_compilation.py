"""Regression tests for Contextive glossary compilation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML

from tests.utils import REPO_ROOT


def _run_compiler(output_dir: Path, index_path: Path, project_glossary: Path) -> None:
    script = REPO_ROOT / "scripts" / "chores" / "glossary-compilation.py"
    input_dir = REPO_ROOT / "glossary" / "contexts"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--index",
            str(index_path),
            "--project-glossary",
            str(project_glossary),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_compiled_index_uses_import_sequence(tmp_path: Path) -> None:
    output_dir = tmp_path / "memory" / "contexts"
    index_path = tmp_path / "memory" / "spec-kitty.glossary.yml"
    project_glossary = tmp_path / "project.glossary.yml"
    _run_compiler(output_dir, index_path, project_glossary)

    yaml = YAML(typ="safe")
    index_doc = yaml.load(index_path.read_text(encoding="utf-8"))
    assert isinstance(index_doc, dict)
    assert "imports" in index_doc
    assert isinstance(index_doc["imports"], list)
    assert all(isinstance(item, str) for item in index_doc["imports"])
    assert any(item.endswith("doctrine-artifacts.glossary.yml") for item in index_doc["imports"])
    assert "contexts" not in index_doc


def test_project_glossary_entrypoint_is_import_only(tmp_path: Path) -> None:
    output_dir = tmp_path / "memory" / "contexts"
    index_path = tmp_path / "memory" / "spec-kitty.glossary.yml"
    project_glossary = tmp_path / "project.glossary.yml"
    _run_compiler(output_dir, index_path, project_glossary)

    yaml = YAML(typ="safe")
    project_doc = yaml.load(project_glossary.read_text(encoding="utf-8"))
    assert isinstance(project_doc, dict)
    assert sorted(project_doc.keys()) == ["imports"]
    assert isinstance(project_doc["imports"], list)
    assert len(project_doc["imports"]) == 1
    assert isinstance(project_doc["imports"][0], str)


def test_compiled_context_meta_values_are_strings(tmp_path: Path) -> None:
    output_dir = tmp_path / "memory" / "contexts"
    index_path = tmp_path / "memory" / "spec-kitty.glossary.yml"
    project_glossary = tmp_path / "project.glossary.yml"
    _run_compiler(output_dir, index_path, project_glossary)

    yaml = YAML(typ="safe")
    for context_file in output_dir.glob("*.glossary.yml"):
        doc = yaml.load(context_file.read_text(encoding="utf-8"))
        for context in doc.get("contexts", []):
            for term in context.get("terms", []):
                meta = term.get("meta", {})
                for value in meta.values():
                    assert isinstance(value, str), (
                        f"Meta value in {context_file.name} must be string, got {type(value)}"
                    )


def test_compiled_doctrine_artifacts_context_contains_expected_fields(tmp_path: Path) -> None:
    output_dir = tmp_path / "memory" / "contexts"
    index_path = tmp_path / "memory" / "spec-kitty.glossary.yml"
    project_glossary = tmp_path / "project.glossary.yml"
    _run_compiler(output_dir, index_path, project_glossary)

    doctrine_file = output_dir / "doctrine-artifacts.glossary.yml"
    assert doctrine_file.exists()

    yaml = YAML(typ="safe")
    doc = yaml.load(doctrine_file.read_text(encoding="utf-8"))
    contexts = doc.get("contexts", [])
    assert contexts

    terms = contexts[0].get("terms", [])
    assert terms

    ids = set()
    for term in terms:
        assert isinstance(term.get("name"), str)
        assert isinstance(term.get("definition"), str)
        meta = term.get("meta", {})
        assert isinstance(meta.get("id"), str)
        assert isinstance(meta.get("description"), str)
        ids.add(meta["id"])

    assert "zombies-tdd" in ids
    assert "tdd-red-green-refactor" in ids
