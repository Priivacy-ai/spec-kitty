"""Test that all templates comply with feature 007 flat tasks/ structure."""

from pathlib import Path
import pytest
import re


def find_mission_templates() -> list[Path]:
    """Find all command template files in missions."""
    spec_kitty_root = Path(__file__).parent.parent
    missions_dir = spec_kitty_root / "src" / "specify_cli" / "missions"

    templates = []
    if missions_dir.exists():
        for mission_dir in missions_dir.iterdir():
            if mission_dir.is_dir():
                cmd_templates = mission_dir / "command-templates"
                if cmd_templates.exists():
                    templates.extend(cmd_templates.glob("*.md"))

                mission_templates = mission_dir / "templates"
                if mission_templates.exists():
                    templates.extend(mission_templates.glob("*.md"))

    # Also check root templates
    root_templates = spec_kitty_root / "src" / "specify_cli" / "templates"
    if root_templates.exists():
        templates.extend(root_templates.glob("**/*.md"))

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
        r'tasks/planned/',
        r'tasks/doing/',
        r'tasks/for_review/',
        r'tasks/done/',
    ]

    for template_path in templates:
        content = template_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip lines that are showing what NOT to do
            if 'WRONG' in line or 'do not create' in line.lower() or '❌' in line:
                continue

            for pattern in forbidden_patterns:
                if re.search(pattern, line):
                    violations.append({
                        'file': template_path.relative_to(template_path.parent.parent.parent),
                        'line': line_num,
                        'content': line.strip(),
                        'pattern': pattern
                    })

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
        'phase subfolders',
        'phase subdirectories',
        'phase-<n>-<label>',
        'phase-X-name',
        'tasks/planned/phase-',
        'tasks/doing/phase-',
    ]

    for template_path in templates:
        content = template_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip WRONG examples
            if 'WRONG' in line or 'do not create' in line.lower() or '❌' in line:
                continue

            for phrase in forbidden_phrases:
                if phrase in line:
                    violations.append({
                        'file': template_path.relative_to(template_path.parent.parent.parent),
                        'line': line_num,
                        'content': line.strip(),
                        'phrase': phrase
                    })

    if violations:
        msg = "\n\nPhase subdirectory references found in templates:\n"
        for v in violations:
            msg += f"\n{v['file']}:{v['line']}\n  Phrase: {v['phrase']}\n  Line: {v['content'][:100]}\n"
        pytest.fail(msg)


def test_templates_require_flat_structure():
    """Templates must explicitly require flat tasks/ structure."""
    spec_kitty_root = Path(__file__).parent.parent
    tasks_template = (
        spec_kitty_root
        / "src"
        / "specify_cli"
        / "missions"
        / "software-dev"
        / "command-templates"
        / "tasks.md"
    )

    assert tasks_template.exists(), "tasks.md template not found"

    content = tasks_template.read_text(encoding='utf-8')

    # Must have explicit instruction about flat structure
    assert 'FLAT' in content.upper() or 'flat' in content, \
        "tasks.md must explicitly mention flat structure"

    # Must warn against subdirectories
    assert 'no subdirectories' in content.lower() or 'NO subdirectories' in content, \
        "tasks.md must warn against creating subdirectories"

    # Must have correct example
    assert 'tasks/WP01' in content or 'tasks/WPxx' in content, \
        "tasks.md must show correct flat path examples"


def test_agents_md_shows_flat_structure():
    """AGENTS.md must document the flat tasks/ structure."""
    spec_kitty_root = Path(__file__).parent.parent
    agents_md = spec_kitty_root / "src" / "specify_cli" / "templates" / "AGENTS.md"

    if not agents_md.exists():
        pytest.skip("AGENTS.md not found")

    content = agents_md.read_text(encoding='utf-8')

    # Should not show old subdirectory structure
    assert 'tasks/planned/WP' not in content, \
        "AGENTS.md should not show old subdirectory structure"


def test_no_deprecated_script_references():
    """Templates must not reference deprecated .kittify/scripts/ paths.

    Issue #68: Templates were referencing old bash/python scripts in .kittify/scripts/
    instead of the spec-kitty CLI command. This caused agents to execute user's local
    cli.py files instead of the spec-kitty entry point.

    All templates must use: spec-kitty agent tasks move-task
    NOT: python3 .kittify/scripts/tasks/tasks_cli.py
    """
    templates = find_mission_templates()
    assert len(templates) > 0, "No templates found - check test setup"

    violations = []

    # Deprecated script patterns
    deprecated_patterns = [
        r'\.kittify/scripts/tasks/tasks_cli\.py',
        r'python3?\s+\.kittify/scripts/',
        r'python3?\s+scripts/tasks/tasks_cli\.py',
        r'\btasks_cli\.py\s+(move|update)',  # Direct reference to tasks_cli.py commands
    ]

    for template_path in templates:
        content = template_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip comments explaining what NOT to do
            if 'deprecated' in line.lower() or 'old' in line.lower() or 'WRONG' in line:
                continue

            for pattern in deprecated_patterns:
                if re.search(pattern, line):
                    violations.append({
                        'file': template_path.relative_to(template_path.parent.parent.parent),
                        'line': line_num,
                        'content': line.strip(),
                        'pattern': pattern
                    })

    if violations:
        msg = "\n\nDeprecated script references found (Issue #68):\n"
        msg += "Templates must use: spec-kitty agent tasks move-task\n"
        msg += "NOT: python3 .kittify/scripts/tasks/tasks_cli.py\n\n"
        for v in violations:
            msg += f"\n{v['file']}:{v['line']}\n  Pattern: {v['pattern']}\n  Line: {v['content'][:100]}\n"
        pytest.fail(msg)


def test_templates_use_spec_kitty_cli():
    """Templates must use spec-kitty CLI commands, not legacy scripts.

    Ensures templates instruct agents to use the correct spec-kitty command format.
    """
    templates = find_mission_templates()

    # Find templates that mention task movement
    task_movement_templates = []
    for template_path in templates:
        content = template_path.read_text(encoding='utf-8')
        if 'move' in content.lower() and ('lane' in content.lower() or 'task' in content.lower()):
            task_movement_templates.append(template_path)

    if not task_movement_templates:
        pytest.skip("No templates found that reference task movement")

    violations = []

    for template_path in task_movement_templates:
        content = template_path.read_text(encoding='utf-8')

        # Check if template uses correct spec-kitty command
        has_correct_command = 'spec-kitty agent tasks move-task' in content

        # Check for deprecated patterns (should be caught by previous test, but double-check)
        has_deprecated = '.kittify/scripts/' in content or 'tasks_cli.py' in content

        if has_deprecated and not has_correct_command:
            violations.append({
                'file': template_path.relative_to(template_path.parent.parent.parent),
                'issue': 'Uses deprecated script reference without spec-kitty alternative'
            })
        elif has_deprecated:
            # Has both - might be showing migration example, verify it's clearly marked
            if 'deprecated' not in content.lower() and 'old' not in content.lower():
                violations.append({
                    'file': template_path.relative_to(template_path.parent.parent.parent),
                    'issue': 'Contains deprecated reference without clear deprecation notice'
                })

    if violations:
        msg = "\n\nTemplates with deprecated script references:\n"
        for v in violations:
            msg += f"\n{v['file']}\n  Issue: {v['issue']}\n"
        pytest.fail(msg)
