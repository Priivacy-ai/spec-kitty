"""Charter draft generation adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.charter.catalog import DoctrineCatalog
from specify_cli.charter.compiler import compile_charter
from specify_cli.charter.interview import CharterInterview, default_interview


@dataclass(frozen=True)
class CharterDraft:
    """Draft charter with deterministic doctrine selections."""

    mission: str
    template_set: str
    selected_paradigms: list[str]
    selected_directives: list[str]
    available_tools: list[str]
    markdown: str
    diagnostics: list[str] = field(default_factory=list)


def build_charter_draft(
    *,
    mission: str,
    template_set: str | None = None,
    doctrine_catalog: DoctrineCatalog | None = None,
    interview: CharterInterview | None = None,
) -> CharterDraft:
    """Build deterministic charter markdown for a mission."""
    interview_data = interview or default_interview(mission=mission)
    compiled = compile_charter(
        mission=mission,
        interview=interview_data,
        template_set=template_set,
        doctrine_catalog=doctrine_catalog,
    )

    return CharterDraft(
        mission=compiled.mission,
        template_set=compiled.template_set,
        selected_paradigms=compiled.selected_paradigms,
        selected_directives=compiled.selected_directives,
        available_tools=compiled.available_tools,
        markdown=compiled.markdown,
        diagnostics=compiled.diagnostics,
    )


def write_charter(path: Path, markdown: str, *, force: bool = False) -> None:
    """Write charter markdown to disk."""
    if path.exists() and not force:
        raise FileExistsError(f"Charter already exists at {path}. Use --force to overwrite.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
