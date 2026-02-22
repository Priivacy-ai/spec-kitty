"""Constitution draft generation adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.constitution.catalog import DoctrineCatalog
from specify_cli.constitution.compiler import compile_constitution
from specify_cli.constitution.interview import ConstitutionInterview, default_interview


@dataclass(frozen=True)
class ConstitutionDraft:
    """Draft constitution with deterministic doctrine selections."""

    mission: str
    template_set: str
    selected_paradigms: list[str]
    selected_directives: list[str]
    available_tools: list[str]
    markdown: str
    diagnostics: list[str] = field(default_factory=list)


def build_constitution_draft(
    *,
    mission: str,
    template_set: str | None = None,
    doctrine_catalog: DoctrineCatalog | None = None,
    interview: ConstitutionInterview | None = None,
) -> ConstitutionDraft:
    """Build deterministic constitution markdown for a mission."""
    interview_data = interview or default_interview(mission=mission)
    compiled = compile_constitution(
        mission=mission,
        interview=interview_data,
        template_set=template_set,
        doctrine_catalog=doctrine_catalog,
    )

    return ConstitutionDraft(
        mission=compiled.mission,
        template_set=compiled.template_set,
        selected_paradigms=compiled.selected_paradigms,
        selected_directives=compiled.selected_directives,
        available_tools=compiled.available_tools,
        markdown=compiled.markdown,
        diagnostics=compiled.diagnostics,
    )


def write_constitution(path: Path, markdown: str, *, force: bool = False) -> None:
    """Write constitution markdown to disk."""
    if path.exists() and not force:
        raise FileExistsError(f"Constitution already exists at {path}. Use --force to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
