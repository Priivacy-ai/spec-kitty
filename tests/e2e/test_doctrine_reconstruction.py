"""E2E probes for reconstructing checked-in assets from doctrine artifacts.

These are intentionally non-blocking probes. The current repository state is
not expected to round-trip cleanly yet because doctrine extraction has not been
applied to all existing constitution and generated prompt assets.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from constitution.compiler import compile_constitution
from constitution.interview import apply_answer_overrides, default_interview
from specify_cli.template import generate_agent_assets, prepare_command_templates


REPO_ROOT = Path(__file__).resolve().parents[2]


def _normalize_constitution(text: str) -> str:
    lines = [line for line in text.splitlines() if not line.startswith("Generated: ")]
    return "\n".join(lines).strip()


@pytest.mark.e2e
def test_compiler_surfaces_curated_constitution_parity_batch() -> None:
    interview = default_interview(mission="software-dev", profile="minimal")
    interview = apply_answer_overrides(
        interview,
        selected_directives=["DIRECTIVE_028", "DIRECTIVE_029", "DIRECTIVE_030"],
    )

    compiled = compile_constitution(mission="software-dev", interview=interview)

    assert compiled.selected_directives == ["DIRECTIVE_028", "DIRECTIVE_029", "DIRECTIVE_030"]
    assert "selected_directives: [DIRECTIVE_028, DIRECTIVE_029, DIRECTIVE_030]" in compiled.markdown
    assert "Apply doctrine directive `DIRECTIVE_028`" in compiled.markdown
    assert "Apply doctrine directive `DIRECTIVE_029`" in compiled.markdown
    assert "Apply doctrine directive `DIRECTIVE_030`" in compiled.markdown

    reference_ids = {reference.id for reference in compiled.references}
    assert "DIRECTIVE:DIRECTIVE_028" in reference_ids
    assert "DIRECTIVE:DIRECTIVE_029" in reference_ids
    assert "DIRECTIVE:DIRECTIVE_030" in reference_ids


@pytest.mark.e2e
@pytest.mark.xfail(
    strict=False,
    reason=(
        "Rationale: current checked-in constitution was authored/synced outside the doctrine-backed compiler path. "
        "TODO: re-extract interview/governance inputs and regenerate constitution.md from doctrine artifacts, "
        "then flip this probe to a hard assertion."
    ),
)
def test_reconstruct_current_constitution_from_doctrine_assets() -> None:
    current_constitution = REPO_ROOT / ".kittify" / "constitution" / "constitution.md"
    assert current_constitution.exists(), "Expected checked-in constitution.md to exist"

    compiled = compile_constitution(
        mission="software-dev",
        interview=default_interview(mission="software-dev", profile="minimal"),
    )

    assert _normalize_constitution(compiled.markdown) == _normalize_constitution(
        current_constitution.read_text(encoding="utf-8")
    )


@pytest.mark.e2e
@pytest.mark.xfail(
    strict=False,
    reason=(
        "Rationale: current generated Codex prompts predate full doctrine extraction and overlay normalization. "
        "TODO: regenerate mission command assets from doctrine templates, reconcile naming/content drift, "
        "then convert this probe into a required exact-match test."
    ),
)
def test_reconstruct_current_codex_prompts_from_doctrine_templates(tmp_path: Path) -> None:
    base_templates = REPO_ROOT / "src" / "doctrine" / "templates" / "command-templates"
    mission_templates = REPO_ROOT / "src" / "doctrine" / "missions" / "software-dev" / "command-templates"
    generated_project = tmp_path / "generated-project"
    generated_project.mkdir()

    merged_templates = prepare_command_templates(base_templates, mission_templates)
    generate_agent_assets(merged_templates, generated_project, "codex", "sh")

    generated_dir = generated_project / ".codex" / "prompts"
    current_dir = REPO_ROOT / ".codex" / "prompts"

    generated_files = sorted(path.name for path in generated_dir.glob("*.md"))
    current_files = sorted(path.name for path in current_dir.glob("*.md"))
    assert generated_files == current_files

    for filename in generated_files:
        generated_text = (generated_dir / filename).read_text(encoding="utf-8")
        current_text = (current_dir / filename).read_text(encoding="utf-8")
        assert generated_text == current_text, f"Prompt mismatch for {filename}"
