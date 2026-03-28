"""Test that all templates comply with feature 007 flat tasks/ structure.

These are black-box tests that verify the interaction between specify_cli and
doctrine by going through the public doctrine API (MissionRepository) rather
than hard-coding internal filesystem paths.
"""

import importlib.resources
from pathlib import Path
import pytest
import re

from doctrine.missions.repository import MissionRepository


def _missions_root() -> Path:
    """Return the doctrine package's missions root via the public API."""
    return MissionRepository.default_missions_root()


def find_mission_templates() -> list[Path]:
    """Find all command template and content template files via the doctrine API.

    Searches:
    - doctrine missions: <missions_root>/<mission>/command-templates/*.md
    - doctrine missions: <missions_root>/<mission>/templates/*.md
    """
    missions_root = _missions_root()
    templates = []

    if missions_root.is_dir():
        for mission_dir in missions_root.iterdir():
            if not mission_dir.is_dir() or mission_dir.name.startswith("."):
                continue
            cmd_templates = mission_dir / "command-templates"
            if cmd_templates.exists():
                templates.extend(cmd_templates.glob("*.md"))
            mission_templates = mission_dir / "templates"
            if mission_templates.exists():
                templates.extend(mission_templates.glob("*.md"))

    return templates


def test_no_lane_subdirectories_in_templates():
    """Feature 007: Templates must not instruct agents to create lane subdirectories.

    Feature 007 (FR-003): All WP files MUST reside in flat tasks/ directory.
    Violations cause agents to create tasks/planned/, tasks/doing/, etc.
    """
    templates = find_mission_templates()
    assert len(templates) > 0, "No templates found - check test setup"

    violations = []

    # Patterns that violate flat structure (not in "WRONG" examples)
    forbidden_patterns = [
        r"tasks/planned/",
        r"tasks/doing/",
        r"tasks/for_review/",
        r"tasks/done/",
    ]

    for template_path in templates:
        content = template_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip lines that are showing what NOT to do
            if "WRONG" in line or "do not create" in line.lower() or "❌" in line:
                continue

            for pattern in forbidden_patterns:
                if re.search(pattern, line):
                    violations.append(
                        {
                            "file": template_path.relative_to(template_path.parent.parent.parent),
                            "line": line_num,
                            "content": line.strip(),
                            "pattern": pattern,
                        }
                    )

    if violations:
        msg = "\n\nFeature 007 violations found (templates referencing lane subdirectories):\n"
        for v in violations:
            msg += f"\n{v['file']}:{v['line']}\n  Pattern: {v['pattern']}\n  Line: {v['content'][:100]}\n"
        pytest.fail(msg)


def test_no_phase_subdirectories_in_templates():
    """Feature 007: Templates must not instruct agents to create phase subdirectories.

    Phase organization was eliminated in favor of flat structure.
    """
    templates = find_mission_templates()
    violations = []

    forbidden_phrases = [
        "phase subfolders",
        "phase subdirectories",
        "phase-<n>-<label>",
        "phase-X-name",
        "tasks/planned/phase-",
        "tasks/doing/phase-",
    ]

    for template_path in templates:
        content = template_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip WRONG examples
            if "WRONG" in line or "do not create" in line.lower() or "❌" in line:
                continue

            for phrase in forbidden_phrases:
                if phrase in line:
                    violations.append(
                        {
                            "file": template_path.relative_to(template_path.parent.parent.parent),
                            "line": line_num,
                            "content": line.strip(),
                            "phrase": phrase,
                        }
                    )

    if violations:
        msg = "\n\nPhase subdirectory references found in templates:\n"
        for v in violations:
            msg += f"\n{v['file']}:{v['line']}\n  Phrase: {v['phrase']}\n  Line: {v['content'][:100]}\n"
        pytest.fail(msg)


def test_templates_require_flat_structure():
    """Templates must explicitly require flat tasks/ structure."""
    repo = MissionRepository(_missions_root())
    tasks_path = repo.get_command_template("software-dev", "tasks")

    assert tasks_path is not None, "tasks.md command template not found via MissionRepository"

    content = tasks_path.content

    # Must have explicit instruction about flat structure
    assert "FLAT" in content.upper() or "flat" in content, "tasks.md must explicitly mention flat structure"

    # Must warn against subdirectories
    assert "no subdirectories" in content.lower() or "NO subdirectories" in content, (
        "tasks.md must warn against creating subdirectories"
    )

    # Must have correct example
    assert "tasks/WP01" in content or "tasks/WPxx" in content, "tasks.md must show correct flat path examples"


def test_task_prompt_templates_include_branch_contract_metadata():
    """Every bundled WP prompt template should carry explicit branch-intent metadata."""
    templates = [
        path
        for path in find_mission_templates()
        if path.name == "task-prompt-template.md"
    ]

    assert templates, "No task-prompt-template.md files found"

    missing = []
    for template_path in templates:
        content = template_path.read_text(encoding="utf-8")
        required_tokens = [
            "planning_base_branch",
            "merge_target_branch",
            "branch_strategy",
            "## Branch Strategy",
        ]
        absent = [token for token in required_tokens if token not in content]
        if absent:
            missing.append((template_path, absent))

    if missing:
        msg = "\n\nTask prompt templates missing explicit branch contract metadata:\n"
        for template_path, absent in missing:
            msg += f"\n{template_path}\n  Missing: {', '.join(absent)}\n"
        pytest.fail(msg)


def test_planning_templates_use_deterministic_branch_helpers():
    """Planning-stage templates should rely on Python helpers, not manual git probing."""
    repo = MissionRepository(_missions_root())
    missions = repo.list_missions()

    missing_branch_helper = []
    forbidden_git_probes = []

    for mission in missions:
        for cmd_name in ("specify", "plan", "tasks"):
            result = repo.get_command_template(mission, cmd_name)
            if result is None:
                continue
            content = result.content

            if cmd_name == "specify" and "branch-context --json" not in content:
                missing_branch_helper.append(result.origin)

            if "git branch --show-current" in content or "git rev-parse --abbrev-ref HEAD" in content:
                forbidden_git_probes.append(result.origin)

    if missing_branch_helper:
        msg = "\n\nSpecify templates missing deterministic branch-context helper:\n"
        for origin in missing_branch_helper:
            msg += f"\n{origin}\n"
        pytest.fail(msg)

    if forbidden_git_probes:
        msg = "\n\nPlanning templates still probe git directly instead of helper JSON:\n"
        for origin in forbidden_git_probes:
            msg += f"\n{origin}\n"
        pytest.fail(msg)


def test_agents_md_shows_flat_structure():
    """AGENTS.md must document the flat tasks/ structure."""
    try:
        agents_md = Path(str(importlib.resources.files("doctrine") / "templates" / "AGENTS.md"))
    except Exception:
        pytest.skip("AGENTS.md not found in doctrine package")
        return

    if not agents_md.exists():
        pytest.skip("AGENTS.md not found")
        return

    content = agents_md.read_text(encoding="utf-8")

    # Should not show old subdirectory structure
    assert "tasks/planned/WP" not in content, "AGENTS.md should not show old subdirectory structure"


def test_no_deprecated_script_references():
    """Templates must not reference deprecated .kittify/scripts/ paths.

    Issue #68: Templates were referencing old bash/python scripts in .kittify/scripts/
    instead of the spec-kitty CLI command. This caused agents to execute user's local
    cli.py files instead of the spec-kitty entry point.

    All templates must use workflow commands (spec-kitty agent workflow implement/review)
    NOT: python3 .kittify/scripts/tasks/tasks_cli.py
    """
    templates = find_mission_templates()
    assert len(templates) > 0, "No templates found - check test setup"

    violations = []

    # Deprecated script patterns
    deprecated_patterns = [
        r"\.kittify/scripts/tasks/tasks_cli\.py",
        r"python3?\s+\.kittify/scripts/",
        r"python3?\s+scripts/tasks/tasks_cli\.py",
        r"\btasks_cli\.py\s+(move|update)",  # Direct reference to tasks_cli.py commands
    ]

    for template_path in templates:
        content = template_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments explaining what NOT to do
            if "deprecated" in line.lower() or "old" in line.lower() or "WRONG" in line:
                continue

            for pattern in deprecated_patterns:
                if re.search(pattern, line):
                    violations.append(
                        {
                            "file": template_path.relative_to(template_path.parent.parent.parent),
                            "line": line_num,
                            "content": line.strip(),
                            "pattern": pattern,
                        }
                    )

    if violations:
        msg = "\n\nDeprecated script references found (Issue #68):\n"
        msg += "Templates must use: spec-kitty agent workflow implement/review\n"
        msg += "NOT: python3 .kittify/scripts/tasks/tasks_cli.py\n\n"
        for v in violations:
            msg += f"\n{v['file']}:{v['line']}\n  Pattern: {v['pattern']}\n  Line: {v['content'][:100]}\n"
        pytest.fail(msg)


def test_templates_do_not_instruct_manual_lane_moves_to_doing():
    """Templates should not instruct manual moves to 'doing' lane.

    The 'spec-kitty agent workflow implement' command auto-moves WPs to 'doing'.
    Templates should not instruct agents to manually move-task --to doing.

    However, move-task --to for_review is allowed (completion step after implementation).
    """
    templates = find_mission_templates()

    violations = []

    for template_path in templates:
        content = template_path.read_text(encoding="utf-8")

        # Only flag move-task to "doing" since workflow implement handles that automatically
        # move-task to "for_review" is allowed (completion step after implementation)
        if "move-task" in content and "--to doing" in content and "deprecated" not in content.lower():
            violations.append(
                {
                    "file": template_path.relative_to(template_path.parent.parent.parent),
                    "issue": "Manual move-task --to doing is deprecated (use workflow implement instead)",
                }
            )

    if violations:
        msg = "\n\nTemplates with deprecated manual 'doing' lane moves:\n"
        msg += "Use 'spec-kitty agent workflow implement' instead of manual move-task --to doing\n"
        for v in violations:
            msg += f"\n{v['file']}\n  Issue: {v['issue']}\n"
        pytest.fail(msg)
