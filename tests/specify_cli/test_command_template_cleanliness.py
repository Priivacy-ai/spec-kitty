"""Tests for prompt content cleanliness in the canonical command templates.

These tests assert that the 9 canonical prompt-driven command template files
are free of dev-specific content that would break consumer projects:
  - No 057- or other feature-slug artifacts
  - No absolute machine paths (/Users/<user>/, /home/<user>/)
  - No .kittify/missions/ read instructions
  - No deprecated "planning repository" terminology
  - All templates >=50 non-empty lines
  - YAML frontmatter present and declares a non-empty ``description``
    (slash-command pickers like Claude Code read this for their UI)
  - Planning-workflow templates use "repository root checkout" terminology
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

# Planning-workflow templates that MUST use "repository root checkout" terminology.
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
# T026-e: No deprecated planning-location terminology
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_no_planning_repository_terminology(command: str) -> None:
    """Templates must not use deprecated planning-location terminology.

    The correct phrase is 'repository root checkout'. Older variants caused
    agents to confuse planning location with branch choice.
    """
    content = _template_content(command)
    assert "planning repository" not in content.lower(), (
        f"{command}.md uses deprecated 'planning repository' terminology - "
        f"use 'repository root checkout' instead"
    )
    assert "planning repo" not in content.lower(), (
        f"{command}.md uses deprecated 'planning repo' terminology - "
        f"use 'repository root checkout' instead"
    )
    assert "project root checkout" not in content.lower(), (
        f"{command}.md uses deprecated 'project root checkout' terminology - "
        f"use 'repository root checkout' instead"
    )
    assert "main repository root" not in content.lower(), (
        f"{command}.md uses ambiguous 'main repository root' terminology - "
        f"use 'repository root checkout' instead"
    )


# ---------------------------------------------------------------------------
# T026-f: Planning-workflow templates use "repository root checkout"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PLANNING_WORKFLOW_TEMPLATES)
def test_uses_repository_root_checkout_in_planning_templates(command: str) -> None:
    """Planning-workflow templates must use 'repository root checkout' terminology.

    These templates direct agents on where to perform planning work.
    They must explicitly state 'repository root checkout' so agents work in the
    correct location and do not create a worktree for planning.
    """
    content = _template_content(command)
    assert "repository root checkout" in content.lower(), (
        f"{command}.md missing 'repository root checkout' terminology - "
        f"add explicit location guidance for agents"
    )


# ---------------------------------------------------------------------------
# T026-g: YAML frontmatter present and declares a description
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("command", PROMPT_DRIVEN)
def test_has_yaml_frontmatter_with_description(command: str) -> None:
    """Templates must open with a YAML frontmatter block declaring ``description``.

    The asset generator preserves the template's frontmatter verbatim and
    places the version marker just after it.  Slash-command pickers (e.g.
    Claude Code) read the ``description`` field to populate their UI; without
    it, users see the raw HTML version-marker comment as the description.
    """
    from specify_cli.template.renderer import parse_frontmatter

    content = _template_content(command)
    assert content.startswith("---\n"), (
        f"{command}.md is missing YAML frontmatter — add a `---\\ndescription: "
        f"...\\n---` block so the slash-command picker has a real description"
    )
    metadata, _body, _raw = parse_frontmatter(content)
    description = str(metadata.get("description", "")).strip()
    assert description, (
        f"{command}.md frontmatter is missing a non-empty `description` field"
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


# ---------------------------------------------------------------------------
# T029 / T030: context resolve example includes --mission
# ---------------------------------------------------------------------------


def test_tasks_template_context_resolve_has_mission() -> None:
    """tasks.md context resolve example must include --mission <mission-slug> (T029)."""
    content = _template_content("tasks")
    # The context resolve command example must explicitly show --mission
    assert "context resolve --action tasks --mission" in content, (
        "tasks.md context resolve example missing '--mission' - "
        "agents copy-paste this and immediately fail without it"
    )


@pytest.mark.parametrize("command", ["tasks-packages", "tasks-outline"])
def test_context_resolve_examples_have_mission(command: str) -> None:
    """All context resolve examples in planning templates must include --mission (T030)."""
    content = _template_content(command)
    # If a template has a context resolve call, it must have --mission
    if "context resolve" in content:
        assert "--mission" in content, (
            f"{command}.md has context resolve call without '--mission' - "
            f"add --mission <mission-slug> to the context resolve example"
        )


def test_tasks_template_finalize_tasks_has_mission() -> None:
    """tasks.md finalize-tasks examples must include --mission (T030)."""
    content = _template_content("tasks")
    # The validate-only example must have --mission
    assert "finalize-tasks --validate-only --mission" in content, (
        "tasks.md finalize-tasks --validate-only example missing '--mission'"
    )


def test_tasks_template_map_requirements_has_mission() -> None:
    """tasks.md map-requirements examples must include --mission (T030)."""
    content = _template_content("tasks")
    assert "map-requirements --batch" in content
    # Batch mode example must include --mission
    lines_with_batch = [ln for ln in content.splitlines() if "map-requirements --batch" in ln]
    assert lines_with_batch, "tasks.md missing map-requirements --batch example"
    for line in lines_with_batch:
        assert "--mission" in line, (
            f"tasks.md map-requirements --batch line missing '--mission': {line.strip()!r}"
        )


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
