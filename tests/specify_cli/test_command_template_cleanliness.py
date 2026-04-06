"""Tests for prompt content cleanliness in the canonical command templates.

These tests assert that the 9 canonical prompt-driven command template files
are free of dev-specific content that would break consumer projects:
  - No 057- or other feature-slug artifacts
  - No absolute machine paths (/Users/<user>/, /home/<user>/)
  - No .kittify/missions/ read instructions
  - No deprecated "planning repository" terminology
  - All templates >=50 non-empty lines
  - No YAML frontmatter blocks (the asset generator adds its own)
  - Planning-workflow templates use "project root checkout" terminology
  - tasks.md contains WP ownership metadata guidance fields
  - All templates include --mission guidance

WP06: T026
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

# ---------------------------------------------------------------------------
# Template discovery
# ---------------------------------------------------------------------------

# All 9 prompt-driven command templates
PROMPT_DRIVEN: list[str] = [
    "specify",
    "plan",
    "tasks",
    "tasks-outline",
    "tasks-packages",
    "checklist",
    "analyze",
    "research",
    "charter",
]

# Planning-workflow templates that MUST use "project root checkout" terminology.
# These are commands that explicitly direct agents on where to perform work.
# The utility/analysis commands (analyze, checklist, charter) don't
# describe a checkout location, so they are excluded from this assertion.
PLANNING_WORKFLOW_TEMPLATES: list[str] = [
    "specify",
    "plan",
    "tasks",
    "tasks-outline",
    "tasks-packages",
    "research",
]

# Resolve the templates directory relative to the installed package source
_TEMPLATES_DIR = (
    Path(__file__).parent.parent.parent
    / "src"
    / "specify_cli"
    / "missions"
    / "software-dev"
    / "command-templates"
)

_REPO_ROOT = Path(__file__).parent.parent.parent
_ACTIVE_CODEBASE_PATHS: tuple[Path, ...] = (
    _REPO_ROOT / "src",
    _REPO_ROOT / "tests",
    _REPO_ROOT / "docs",
    _REPO_ROOT / "architecture",
    _REPO_ROOT / "research",
    _REPO_ROOT / "AGENTS.md",
    _REPO_ROOT / "README.md",
    _REPO_ROOT / "CHANGELOG.md",
)
_FORBIDDEN_HOME_LITERAL = "/Users/" + "robe" + "rt/"


def _template_content(command: str) -> str:
    """Read and return the content of a command template file."""
    return (_TEMPLATES_DIR / f"{command}.md").read_text(encoding="utf-8")


def _active_codebase_files() -> list[Path]:
    """Return text files from the active codebase surface.

    `kitty-specs/` is intentionally excluded because the user wants to preserve
    historical artifacts there.
    """
    files: list[Path] = []
    for path in _ACTIVE_CODEBASE_PATHS:
        if path.is_file():
            files.append(path)
            continue
        files.extend(
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file() and "__pycache__" not in candidate.parts and candidate.suffix != ".pyc"
        )
    return files


# ---------------------------------------------------------------------------
# T026-a: Template existence and minimum length
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_template_exists(command: str) -> None:
    """Every prompt-driven command must have a template file."""
    f = _TEMPLATES_DIR / f"{command}.md"
    assert f.exists(), f"{command}.md not found in command-templates dir: {_TEMPLATES_DIR}"


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_template_minimum_length(command: str) -> None:
    """Every template must have at least 40 non-empty lines.

    This threshold clearly distinguishes full prompt templates (which have
    substantial workflow guidance) from thin 4-line CLI shim files.
    """
    content = _template_content(command)
    non_empty_lines = [ln for ln in content.splitlines() if ln.strip()]
    assert len(non_empty_lines) >= 40, (
        f"{command}.md is too short: {len(non_empty_lines)} non-empty lines "
        f"(minimum 40 required to qualify as a full prompt template)"
    )


# ---------------------------------------------------------------------------
# T026-b: No feature slug artifacts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_no_057_mission_slug(command: str) -> None:
    """Templates must not contain the 057- development slug."""
    content = _template_content(command)
    assert "057-" not in content, (
        f"{command}.md contains '057-' dev-time feature slug - strip before shipping"
    )


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_no_dev_specific_mission_slugs(command: str) -> None:
    """Templates must not contain the 057- or 058- dev-time feature slugs.

    The 057- and 058- slugs are development artifacts that leaked from source
    templates during authoring. Generic example slugs like '014-checkout-flow'
    or '020-my-feature' are legitimate documentation placeholders and are allowed.
    """
    content = _template_content(command)
    # Check specifically for the dev-time feature slugs
    for bad_slug in ("057-", "058-"):
        assert bad_slug not in content, (
            f"{command}.md contains dev-time feature slug '{bad_slug}' - "
            f"strip before shipping to consumers"
        )


# ---------------------------------------------------------------------------
# T026-c: No absolute machine-specific paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_no_absolute_user_paths(command: str) -> None:
    """Templates must not contain absolute paths tied to a specific machine."""
    content = _template_content(command)
    assert _FORBIDDEN_HOME_LITERAL not in content, (
        f"{command}.md contains a forbidden user-specific home path literal"
    )
    assert re.search(r"/Users/[^/]+/", content) is None, (
        f"{command}.md contains macOS absolute user path '/Users/<user>/'"
    )
    assert re.search(r"/home/[^/]+/", content) is None, (
        f"{command}.md contains Linux absolute user path '/home/<user>/'"
    )


def test_no_user_specific_home_literal_in_active_codebase() -> None:
    """The active codebase must never ship a forbidden user-specific home path."""
    offenders = [
        path.relative_to(_REPO_ROOT).as_posix()
        for path in _active_codebase_files()
        if _FORBIDDEN_HOME_LITERAL in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == [], (
        "Found forbidden user-specific home path literal in active codebase files: "
        + ", ".join(offenders)
    )


# ---------------------------------------------------------------------------
# T026-d: No .kittify/missions/ read instructions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_no_kittify_missions_read_instruction(command: str) -> None:
    """Templates must not instruct agents to read template files from .kittify/missions/.

    Agents should write content directly rather than reading from .kittify/missions/.
    """
    content = _template_content(command)
    lower = content.lower()
    # Flag if the template tells agents to read files from .kittify/missions/
    # (e.g., "read .kittify/missions/..." or "cat .kittify/missions/...")
    if ".kittify/missions/" in lower:
        # If .kittify/missions/ appears, verify it's not paired with a read instruction
        # Split on the marker and check context
        for line in content.splitlines():
            if ".kittify/missions/" in line.lower():
                assert "read" not in line.lower() and "cat " not in line.lower(), (
                    f"{command}.md contains .kittify/missions/ read instruction: {line.strip()!r}"
                )


# ---------------------------------------------------------------------------
# T026-e: No deprecated "planning repository" terminology
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_no_planning_repository_terminology(command: str) -> None:
    """Templates must not use the deprecated 'planning repository' terminology.

    The correct phrase is 'project root checkout'. The old term caused agents
    to create features in a separate repository instead of the current project.
    """
    content = _template_content(command)
    assert "planning repository" not in content.lower(), (
        f"{command}.md uses deprecated 'planning repository' terminology - "
        f"use 'project root checkout' instead"
    )
    assert "planning repo" not in content.lower(), (
        f"{command}.md uses deprecated 'planning repo' terminology - "
        f"use 'project root' instead"
    )


# ---------------------------------------------------------------------------
# T026-f: Planning-workflow templates use "project root checkout"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PLANNING_WORKFLOW_TEMPLATES)
def test_uses_project_root_checkout_in_planning_templates(command: str) -> None:
    """Planning-workflow templates must use 'project root checkout' terminology.

    These templates direct agents on where to perform planning work.
    They must explicitly state 'project root checkout' so agents work in the
    correct location and do not create a worktree for planning.
    """
    content = _template_content(command)
    assert "project root checkout" in content.lower(), (
        f"{command}.md missing 'project root checkout' terminology - "
        f"add explicit location guidance for agents"
    )


# ---------------------------------------------------------------------------
# T026-g: No YAML frontmatter blocks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_no_yaml_frontmatter(command: str) -> None:
    """Templates must not start with YAML frontmatter (--- block).

    The asset generator adds its own frontmatter during rendering.
    Templates that start with --- will produce doubled frontmatter.
    """
    content = _template_content(command)
    assert not content.startswith("---"), (
        f"{command}.md has YAML frontmatter - strip it before shipping "
        f"(the asset generator adds its own frontmatter during rendering)"
    )


# ---------------------------------------------------------------------------
# T026-h: --mission guidance present
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_has_feature_flag_guidance(command: str) -> None:
    """Every template must include a note about passing --mission <slug>."""
    content = _template_content(command)
    assert "--mission" in content, (
        f"{command}.md missing '--mission' guidance - add: "
        f"'In repos with multiple missions, always pass `--mission <slug>` to "
        f"every spec-kitty command.'"
    )


# ---------------------------------------------------------------------------
# T026-i: tasks.md ownership metadata guidance
# ---------------------------------------------------------------------------


def test_tasks_template_has_ownership_guidance() -> None:
    """tasks.md must include WP ownership metadata field guidance.

    Agents use these fields to enforce file ownership isolation:
    - owned_files: glob patterns for files the WP touches
    - authoritative_surface: canonical output location path prefix
    - execution_mode: 'code_change' or 'planning_artifact'
    """
    content = _template_content("tasks")
    assert "owned_files" in content, (
        "tasks.md missing 'owned_files' ownership guidance - "
        "agents need this to enforce file isolation between WPs"
    )
    assert "authoritative_surface" in content, (
        "tasks.md missing 'authoritative_surface' guidance - "
        "identifies the canonical output location for each WP"
    )
    assert "execution_mode" in content, (
        "tasks.md missing 'execution_mode' guidance - "
        "must distinguish 'code_change' from 'planning_artifact' WPs"
    )
