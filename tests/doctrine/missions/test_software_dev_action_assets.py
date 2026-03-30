"""Tests for software-dev action doctrine assets (WP04).

Verifies:
- All 4 action directories exist with required files (guidelines.md + index.yaml)
- index.yaml references only valid shipped doctrine IDs
- Bootstrap blocks remain intact in command templates
- Governance heading sections are absent from command templates after extraction
"""

from pathlib import Path

import pytest
import yaml

WORKTREE = Path(__file__).parents[3]

ACTIONS_DIR = WORKTREE / "src" / "doctrine" / "missions" / "software-dev" / "actions"
TEMPLATES_DIR = (
    WORKTREE / "src" / "doctrine" / "missions" / "software-dev" / "command-templates"
)
DIRECTIVES_DIR = WORKTREE / "src" / "doctrine" / "directives" / "shipped"
TACTICS_DIR = WORKTREE / "src" / "doctrine" / "tactics" / "shipped"
TOOLGUIDES_DIR = WORKTREE / "src" / "doctrine" / "toolguides" / "shipped"

ACTIONS = ["specify", "plan", "implement", "review"]


# ---------------------------------------------------------------------------
# Helper: derive shipped IDs from filenames
# ---------------------------------------------------------------------------


def _shipped_directive_ids() -> set[str]:
    return {
        p.name.removesuffix(".directive.yaml")
        for p in DIRECTIVES_DIR.glob("*.directive.yaml")
        if p.is_file()
    }


def _shipped_tactic_ids() -> set[str]:
    return {
        p.name.removesuffix(".tactic.yaml")
        for p in TACTICS_DIR.glob("*.tactic.yaml")
        if p.is_file()
    }


def _shipped_toolguide_ids() -> set[str]:
    return {
        p.name.removesuffix(".toolguide.yaml")
        for p in TOOLGUIDES_DIR.glob("*.toolguide.yaml")
        if p.is_file()
    }


# ---------------------------------------------------------------------------
# T023a: Action asset existence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ACTIONS)
def test_action_directory_exists(action):
    """Each action must have a dedicated directory under actions/."""
    assert (ACTIONS_DIR / action).is_dir(), (
        f"Missing action directory: actions/{action}/"
    )


@pytest.mark.parametrize("action", ACTIONS)
def test_action_guidelines_exists(action):
    """Each action must ship a guidelines.md file."""
    guidelines = ACTIONS_DIR / action / "guidelines.md"
    assert guidelines.is_file(), f"Missing: actions/{action}/guidelines.md"


@pytest.mark.parametrize("action", ACTIONS)
def test_action_index_yaml_exists(action):
    """Each action must ship an index.yaml file."""
    index = ACTIONS_DIR / action / "index.yaml"
    assert index.is_file(), f"Missing: actions/{action}/index.yaml"


@pytest.mark.parametrize("action", ACTIONS)
def test_action_guidelines_not_empty(action):
    """guidelines.md must contain substantive content (> 50 characters)."""
    content = (ACTIONS_DIR / action / "guidelines.md").read_text(encoding="utf-8")
    assert len(content.strip()) > 50, (
        f"actions/{action}/guidelines.md appears to be empty or trivial"
    )


# ---------------------------------------------------------------------------
# T023b: index.yaml schema validity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ACTIONS)
def test_action_index_yaml_parseable(action):
    """index.yaml must be parseable YAML."""
    index_path = ACTIONS_DIR / action / "index.yaml"
    content = index_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    assert isinstance(data, dict), (
        f"actions/{action}/index.yaml must be a YAML mapping"
    )


@pytest.mark.parametrize("action", ACTIONS)
def test_action_index_yaml_has_action_field(action):
    """index.yaml must have an 'action' field matching the directory name."""
    index_path = ACTIONS_DIR / action / "index.yaml"
    data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    assert data.get("action") == action, (
        f"actions/{action}/index.yaml: expected action={action!r}, "
        f"got {data.get('action')!r}"
    )


@pytest.mark.parametrize("action", ACTIONS)
def test_action_index_yaml_required_lists(action):
    """index.yaml must contain directives, tactics, styleguides, toolguides keys."""
    index_path = ACTIONS_DIR / action / "index.yaml"
    data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    for key in ("directives", "tactics", "styleguides", "toolguides"):
        assert key in data, (
            f"actions/{action}/index.yaml missing required key: {key!r}"
        )
        assert isinstance(data[key], list), (
            f"actions/{action}/index.yaml: {key!r} must be a list"
        )


# ---------------------------------------------------------------------------
# T022: Validate doctrine IDs against shipped catalog
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ACTIONS)
def test_action_index_directives_are_shipped(action):
    """All directive IDs in index.yaml must reference shipped directives."""
    index_path = ACTIONS_DIR / action / "index.yaml"
    data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    shipped = _shipped_directive_ids()
    for directive_id in data.get("directives", []):
        assert directive_id in shipped, (
            f"actions/{action}/index.yaml references unknown directive: "
            f"{directive_id!r}. Shipped directives: {sorted(shipped)}"
        )


@pytest.mark.parametrize("action", ACTIONS)
def test_action_index_tactics_are_shipped(action):
    """All tactic IDs in index.yaml must reference shipped tactics."""
    index_path = ACTIONS_DIR / action / "index.yaml"
    data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    shipped = _shipped_tactic_ids()
    for tactic_id in data.get("tactics", []):
        assert tactic_id in shipped, (
            f"actions/{action}/index.yaml references unknown tactic: "
            f"{tactic_id!r}. Shipped tactics: {sorted(shipped)}"
        )


@pytest.mark.parametrize("action", ACTIONS)
def test_action_index_toolguides_are_shipped(action):
    """All toolguide IDs in index.yaml must reference shipped toolguides."""
    index_path = ACTIONS_DIR / action / "index.yaml"
    data = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    shipped = _shipped_toolguide_ids()
    for toolguide_id in data.get("toolguides", []):
        assert toolguide_id in shipped, (
            f"actions/{action}/index.yaml references unknown toolguide: "
            f"{toolguide_id!r}. Shipped toolguides: {sorted(shipped)}"
        )


# ---------------------------------------------------------------------------
# T021: Bootstrap blocks still present in templates
# ---------------------------------------------------------------------------

BOOTSTRAP_ACTIONS = {
    "specify": "specify",
    "plan": "plan",
    "implement": "implement",
    "review": "review",
}


@pytest.mark.parametrize("template_name,action", BOOTSTRAP_ACTIONS.items())
def test_bootstrap_block_present_in_template(template_name, action):
    """Constitution Context Bootstrap section must remain in each command template."""
    template_path = TEMPLATES_DIR / f"{template_name}.md"
    assert template_path.is_file(), f"Template not found: {template_name}.md"
    content = template_path.read_text(encoding="utf-8")
    assert "Constitution Context Bootstrap" in content, (
        f"{template_name}.md is missing the 'Constitution Context Bootstrap' section. "
        "Do not strip bootstrap blocks when extracting governance prose."
    )
    assert f"--action {action}" in content, (
        f"{template_name}.md is missing the '--action {action}' CLI invocation "
        "inside the bootstrap block."
    )


# ---------------------------------------------------------------------------
# T021: Governance headings absent from templates after extraction
# ---------------------------------------------------------------------------


def test_specify_template_no_quick_guidelines():
    """'Quick Guidelines' heading must be absent from specify.md after extraction."""
    content = (TEMPLATES_DIR / "specify.md").read_text(encoding="utf-8")
    assert "## Quick Guidelines" not in content, (
        "specify.md still contains '## Quick Guidelines' — "
        "this section should have been extracted to actions/specify/guidelines.md"
    )


def test_specify_template_no_section_requirements():
    """'Section Requirements' heading must be absent from specify.md after extraction."""
    content = (TEMPLATES_DIR / "specify.md").read_text(encoding="utf-8")
    assert "### Section Requirements" not in content, (
        "specify.md still contains '### Section Requirements' — "
        "this section should have been extracted to actions/specify/guidelines.md"
    )


def test_specify_template_no_for_ai_generation():
    """'For AI Generation' heading must be absent from specify.md after extraction."""
    content = (TEMPLATES_DIR / "specify.md").read_text(encoding="utf-8")
    assert "### For AI Generation" not in content, (
        "specify.md still contains '### For AI Generation' — "
        "this section should have been extracted to actions/specify/guidelines.md"
    )


def test_specify_template_no_success_criteria_guidelines():
    """'Success Criteria Guidelines' heading must be absent from specify.md."""
    content = (TEMPLATES_DIR / "specify.md").read_text(encoding="utf-8")
    assert "### Success Criteria Guidelines" not in content, (
        "specify.md still contains '### Success Criteria Guidelines' — "
        "this section should have been extracted to actions/specify/guidelines.md"
    )


def test_plan_template_no_key_rules():
    """'Key rules' heading must be absent from plan.md after extraction."""
    content = (TEMPLATES_DIR / "plan.md").read_text(encoding="utf-8")
    assert "## Key rules" not in content, (
        "plan.md still contains '## Key rules' — "
        "this section should have been extracted to actions/plan/guidelines.md"
    )


# ---------------------------------------------------------------------------
# T021: Workflow steps and $ARGUMENTS still present in templates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("template_name", ["specify", "plan"])
def test_arguments_block_still_in_template(template_name):
    """$ARGUMENTS placeholder must remain in templates that accept user input."""
    content = (TEMPLATES_DIR / f"{template_name}.md").read_text(encoding="utf-8")
    assert "$ARGUMENTS" in content, (
        f"{template_name}.md is missing the '$ARGUMENTS' placeholder. "
        "Do not strip $ARGUMENTS blocks when extracting governance prose."
    )


def test_specify_template_retains_discovery_gate():
    """Discovery Gate section must remain in specify.md (workflow, not governance)."""
    content = (TEMPLATES_DIR / "specify.md").read_text(encoding="utf-8")
    assert "## Discovery Gate" in content, (
        "specify.md is missing the '## Discovery Gate' section. "
        "Workflow steps must not be stripped."
    )


def test_plan_template_retains_mandatory_stop():
    """MANDATORY STOP POINT must remain in plan.md (workflow boundary)."""
    content = (TEMPLATES_DIR / "plan.md").read_text(encoding="utf-8")
    assert "MANDATORY STOP POINT" in content, (
        "plan.md is missing the 'MANDATORY STOP POINT' section. "
        "Workflow boundaries must not be stripped."
    )
