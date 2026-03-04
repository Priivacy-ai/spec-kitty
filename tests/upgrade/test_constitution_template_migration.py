"""Tests for constitution template migrations."""

import pytest

from doctrine.missions import MissionRepository
from specify_cli.upgrade.migrations.m_0_13_0_update_constitution_templates import (
    UpdateConstitutionTemplatesMigration,
)
from specify_cli.upgrade.migrations.m_2_0_2_constitution_context_bootstrap import (
    ConstitutionContextBootstrapMigration,
    _bootstrap_sentinel,
    _insert_bootstrap_md,
    _insert_bootstrap_toml,
    _process_file,
    _strip_inline_governance,
)

pytestmark = pytest.mark.fast


@pytest.fixture
def migration():
    """Return the migration instance."""
    return UpdateConstitutionTemplatesMigration()


# All 12 supported agents
ALL_AGENTS = [
    ("claude", ".claude", "commands"),
    ("copilot", ".github", "prompts"),
    ("gemini", ".gemini", "commands"),
    ("cursor", ".cursor", "commands"),
    ("qwen", ".qwen", "commands"),
    ("opencode", ".opencode", "command"),
    ("windsurf", ".windsurf", "workflows"),
    ("codex", ".codex", "prompts"),
    ("kilocode", ".kilocode", "workflows"),
    ("auggie", ".augment", "commands"),
    ("roo", ".roo", "commands"),
    ("q", ".amazonq", "prompts"),
]


def _load_canonical_constitution_template() -> str:
    """Return the current packaged software-dev constitution template content."""
    repo = MissionRepository(MissionRepository.default_missions_root())
    path = repo.get_command_template("software-dev", "constitution")
    if path is None:
        raise FileNotFoundError("constitution command template not found via MissionRepository")
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("agent_key,agent_dir,subdir", ALL_AGENTS)
def test_constitution_template_updated_for_agent(tmp_path, migration, agent_key, agent_dir, subdir):
    """Test that constitution template is updated for a specific agent."""
    # Setup: Create .kittify directory
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    # Create config with this agent
    config_file = kittify_dir / "config.yaml"
    config_file.write_text(f"agents:\n  available:\n    - {agent_key}\n", encoding="utf-8")

    # Create agent directory with old constitution template
    agent_path = tmp_path / agent_dir / subdir
    agent_path.mkdir(parents=True)

    old_content = """# Constitution Command

## Next steps

After writing, provide:
- Location of the file
- Phases completed and questions answered
- Next steps (review, share with team, run /spec-kitty.plan)
"""

    slash_cmd = agent_path / "spec-kitty.constitution.md"
    slash_cmd.write_text(old_content, encoding="utf-8")

    # Detect should return True
    assert migration.detect(tmp_path) is True

    # Apply migration
    result = migration.apply(tmp_path, dry_run=False)

    # Verify success
    assert result.success is True
    assert len(result.errors) == 0

    # Verify file updated
    updated_content = slash_cmd.read_text(encoding="utf-8")
    assert updated_content == _load_canonical_constitution_template()
    assert "spec-kitty constitution interview --defaults --profile minimal --json" in updated_content
    assert "spec-kitty constitution context --action specify --json" in updated_content
    assert "run /spec-kitty.plan" not in updated_content


def test_migration_skips_already_updated(tmp_path, migration):
    """Test that migration skips agents that are already updated."""
    # Setup: Create .kittify directory with opencode config
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    # Create agent directory with canonical up-to-date constitution template
    agent_path = tmp_path / ".opencode" / "command"
    agent_path.mkdir(parents=True)

    correct_content = _load_canonical_constitution_template()

    slash_cmd = agent_path / "spec-kitty.constitution.md"
    slash_cmd.write_text(correct_content, encoding="utf-8")

    # Detect should return False (no update needed)
    # Note: This may return True if template content is different
    # The actual migration will skip if content matches exactly

    # Apply migration (should skip)
    result = migration.apply(tmp_path, dry_run=False)

    # Verify success
    assert result.success is True

    # Content should remain unchanged
    updated_content = slash_cmd.read_text(encoding="utf-8")
    assert updated_content == correct_content


def test_migration_respects_agent_config(tmp_path, migration):
    """Test that migration only updates configured agents."""
    # Setup: Create .kittify directory with only opencode configured
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    # Create two agent directories
    # 1. Configured: opencode (should be updated)
    opencode_path = tmp_path / ".opencode" / "command"
    opencode_path.mkdir(parents=True)

    old_content = """Next steps (review, share with team, run /spec-kitty.plan)"""

    (opencode_path / "spec-kitty.constitution.md").write_text(old_content, encoding="utf-8")

    # 2. NOT configured: claude (should be skipped - orphaned)
    claude_path = tmp_path / ".claude" / "commands"
    claude_path.mkdir(parents=True)
    (claude_path / "spec-kitty.constitution.md").write_text(old_content, encoding="utf-8")

    # Apply migration
    result = migration.apply(tmp_path, dry_run=False)

    # Verify success
    assert result.success is True

    # Only changes for opencode should be reported
    assert any(".opencode" in change for change in result.changes_made)

    # Claude should NOT be in changes (not configured)
    assert not any(".claude" in change for change in result.changes_made)


def test_migration_handles_missing_directories(tmp_path, migration):
    """Test that migration handles missing agent directories gracefully."""
    # Setup: Create .kittify directory with opencode configured
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    # Don't create agent directory (simulate deleted directory)

    # Apply migration (should not crash)
    result = migration.apply(tmp_path, dry_run=False)

    # Verify success (no errors, just skipped)
    assert result.success is True
    assert len(result.errors) == 0


def test_migration_dry_run(tmp_path, migration):
    """Test migration in dry-run mode."""
    # Setup: Create .kittify directory with opencode config
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir()

    config_file = kittify_dir / "config.yaml"
    config_file.write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    # Create agent directory with old template
    agent_path = tmp_path / ".opencode" / "command"
    agent_path.mkdir(parents=True)

    old_content = """Next steps (review, share with team, run /spec-kitty.plan)"""
    slash_cmd = agent_path / "spec-kitty.constitution.md"
    slash_cmd.write_text(old_content, encoding="utf-8")

    # Apply in dry-run mode
    result = migration.apply(tmp_path, dry_run=True)

    # Verify success
    assert result.success is True

    # Verify changes are reported
    assert any("Would update" in change for change in result.changes_made)

    # Verify file NOT actually updated
    assert slash_cmd.read_text(encoding="utf-8") == old_content


# =============================================================================
# Tests for ConstitutionContextBootstrapMigration (m_2_0_2)
# =============================================================================

ALL_AGENTS_BOOTSTRAP = [
    ("claude", ".claude", "commands"),
    ("copilot", ".github", "prompts"),
    ("gemini", ".gemini", "commands"),
    ("cursor", ".cursor", "commands"),
    ("qwen", ".qwen", "commands"),
    ("opencode", ".opencode", "command"),
    ("windsurf", ".windsurf", "workflows"),
    ("codex", ".codex", "prompts"),
    ("kilocode", ".kilocode", "workflows"),
    ("auggie", ".augment", "commands"),
    ("roo", ".roo", "commands"),
    ("q", ".amazonq", "prompts"),
]


@pytest.fixture
def bootstrap_migration():
    """Return a ConstitutionContextBootstrapMigration instance."""
    return ConstitutionContextBootstrapMigration()


def _make_project(tmp_path, agent_key, agent_dir, subdir):
    """Set up a minimal project with a single configured agent."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(f"agents:\n  available:\n    - {agent_key}\n", encoding="utf-8")
    cmd_dir = tmp_path / agent_dir / subdir
    cmd_dir.mkdir(parents=True)
    return cmd_dir


def _old_md_content(action: str) -> str:
    """Return a plausible stale Markdown prompt without the bootstrap call."""
    return (
        "---\n"
        f"description: Run spec-kitty.{action}\n"
        "---\n\n"
        f"# /spec-kitty.{action}\n\n"
        "## Directives\n\n"
        "- Follow all rules\n"
        "- Obey the governance document\n\n"
        "Do the work here.\n"
    )


# ---------------------------------------------------------------------------
# T034 – Parametrized 12-agent coverage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("agent_key,agent_dir,subdir", ALL_AGENTS_BOOTSTRAP)
@pytest.mark.parametrize("action", ["specify", "plan", "implement", "review"])
def test_bootstrap_inserted_for_all_agents(tmp_path, bootstrap_migration, agent_key, agent_dir, subdir, action):
    """Bootstrap block is inserted into each action file for every supported agent."""
    cmd_dir = _make_project(tmp_path, agent_key, agent_dir, subdir)

    # Write stale file without bootstrap call
    prompt_file = cmd_dir / f"spec-kitty.{action}.md"
    prompt_file.write_text(_old_md_content(action), encoding="utf-8")

    assert bootstrap_migration.detect(tmp_path) is True

    result = bootstrap_migration.apply(tmp_path, dry_run=False)

    assert result.success is True
    assert len(result.errors) == 0

    updated = prompt_file.read_text(encoding="utf-8")
    assert _bootstrap_sentinel(action) in updated
    # Inline governance section stripped
    assert "## Directives" not in updated
    assert any(agent_dir in ch for ch in result.changes_made)


# ---------------------------------------------------------------------------
# T035 – Idempotency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("action", ["specify", "plan", "implement", "review"])
def test_migration_is_idempotent(tmp_path, bootstrap_migration, action):
    """Running the migration twice produces no additional changes on the second run."""
    cmd_dir = _make_project(tmp_path, "opencode", ".opencode", "command")

    prompt_file = cmd_dir / f"spec-kitty.{action}.md"
    prompt_file.write_text(_old_md_content(action), encoding="utf-8")

    # First run
    result1 = bootstrap_migration.apply(tmp_path, dry_run=False)
    assert result1.success is True
    content_after_first = prompt_file.read_text(encoding="utf-8")

    # Second run should be a no-op
    result2 = bootstrap_migration.apply(tmp_path, dry_run=False)
    assert result2.success is True
    content_after_second = prompt_file.read_text(encoding="utf-8")

    assert content_after_first == content_after_second
    # No file changes reported on second run
    assert not any("Updated:" in ch for ch in result2.changes_made)


# ---------------------------------------------------------------------------
# T035 – Config filtering
# ---------------------------------------------------------------------------


def test_migration_only_processes_configured_agents(tmp_path, bootstrap_migration):
    """Only agents listed in config.yaml are processed; orphaned dirs are ignored."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    # Only opencode is configured
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    old_content = _old_md_content("specify")

    # Configured agent directory
    opencode_dir = tmp_path / ".opencode" / "command"
    opencode_dir.mkdir(parents=True)
    (opencode_dir / "spec-kitty.specify.md").write_text(old_content, encoding="utf-8")

    # Orphaned agent directory (NOT in config)
    claude_dir = tmp_path / ".claude" / "commands"
    claude_dir.mkdir(parents=True)
    (claude_dir / "spec-kitty.specify.md").write_text(old_content, encoding="utf-8")

    result = bootstrap_migration.apply(tmp_path, dry_run=False)

    assert result.success is True
    assert any(".opencode" in ch for ch in result.changes_made)
    assert not any(".claude" in ch for ch in result.changes_made)

    # Orphaned file should remain unchanged
    assert (claude_dir / "spec-kitty.specify.md").read_text(encoding="utf-8") == old_content


# ---------------------------------------------------------------------------
# T035 – Missing directory resilience
# ---------------------------------------------------------------------------


def test_migration_handles_missing_agent_directory(tmp_path, bootstrap_migration):
    """Migration does not crash when a configured agent's directory does not exist."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")
    # Deliberately do NOT create the .opencode/command directory

    result = bootstrap_migration.apply(tmp_path, dry_run=False)

    assert result.success is True
    assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# Library directory cleanup (T033)
# ---------------------------------------------------------------------------


def test_migration_removes_library_directory(tmp_path, bootstrap_migration):
    """Obsolete .kittify/constitution/library/ is removed during apply."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    library_dir = tmp_path / ".kittify" / "constitution" / "library"
    library_dir.mkdir(parents=True)
    (library_dir / "some-asset.yaml").write_text("key: value\n", encoding="utf-8")

    assert bootstrap_migration.detect(tmp_path) is True

    result = bootstrap_migration.apply(tmp_path, dry_run=False)

    assert result.success is True
    assert not library_dir.exists()
    assert any("Removed" in ch for ch in result.changes_made)


def test_migration_library_removal_dry_run(tmp_path, bootstrap_migration):
    """Dry-run reports library removal without deleting it."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - opencode\n", encoding="utf-8")

    library_dir = tmp_path / ".kittify" / "constitution" / "library"
    library_dir.mkdir(parents=True)

    result = bootstrap_migration.apply(tmp_path, dry_run=True)

    assert result.success is True
    assert library_dir.exists()  # Not removed in dry-run
    assert any("Would remove" in ch for ch in result.changes_made)


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


def test_bootstrap_dry_run_does_not_modify_files(tmp_path, bootstrap_migration):
    """Dry-run reports changes without modifying any files."""
    cmd_dir = _make_project(tmp_path, "opencode", ".opencode", "command")

    old_content = _old_md_content("specify")
    prompt_file = cmd_dir / "spec-kitty.specify.md"
    prompt_file.write_text(old_content, encoding="utf-8")

    result = bootstrap_migration.apply(tmp_path, dry_run=True)

    assert result.success is True
    assert any("Would update" in ch for ch in result.changes_made)
    assert prompt_file.read_text(encoding="utf-8") == old_content


# ---------------------------------------------------------------------------
# TOML format handling
# ---------------------------------------------------------------------------


def test_bootstrap_inserted_into_toml_file(tmp_path, bootstrap_migration):
    """Bootstrap call is inserted into the prompt string of a TOML command file."""
    cmd_dir = _make_project(tmp_path, "gemini", ".gemini", "commands")

    toml_content = 'description = "Specify command"\n\nprompt = """\n# /spec-kitty.specify\n\nDo the work.\n"""\n'
    prompt_file = cmd_dir / "spec-kitty.specify.toml"
    prompt_file.write_text(toml_content, encoding="utf-8")

    result = bootstrap_migration.apply(tmp_path, dry_run=False)

    assert result.success is True
    updated = prompt_file.read_text(encoding="utf-8")
    assert _bootstrap_sentinel("specify") in updated


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


def test_insert_bootstrap_md_after_frontmatter():
    """Bootstrap block is inserted immediately after YAML frontmatter."""
    content = "---\ndescription: test\n---\n\n# Body\n"
    updated = _insert_bootstrap_md(content, "specify")
    assert updated.startswith("---\ndescription: test\n---")
    assert _bootstrap_sentinel("specify") in updated
    # Body is still present and comes after the block
    assert "# Body" in updated
    block_pos = updated.index(_bootstrap_sentinel("specify"))
    body_pos = updated.index("# Body")
    assert block_pos < body_pos


def test_insert_bootstrap_md_no_frontmatter():
    """Bootstrap block is prepended when there is no frontmatter."""
    content = "# Body\n\nSome content.\n"
    updated = _insert_bootstrap_md(content, "plan")
    assert updated.startswith("\n## Governance Context")
    assert _bootstrap_sentinel("plan") in updated
    assert "# Body" in updated


def test_insert_bootstrap_toml_inside_prompt():
    """Bootstrap block is inserted at the start of the TOML prompt string."""
    content = 'description = "x"\n\nprompt = """\n# Body\n"""\n'
    updated = _insert_bootstrap_toml(content, "implement")
    assert _bootstrap_sentinel("implement") in updated
    idx_sentinel = updated.index(_bootstrap_sentinel("implement"))
    idx_body = updated.index("# Body")
    assert idx_sentinel < idx_body


def test_strip_inline_governance_removes_sections():
    """_strip_inline_governance removes matched heading sections."""
    content = (
        "# Main\n\n"
        "## Directives\n\n- rule 1\n- rule 2\n\n"
        "## Styleguides\n\nFollow these styles.\n\n"
        "## Workflow\n\nDo the work.\n"
    )
    result = _strip_inline_governance(content)
    assert "## Directives" not in result
    assert "## Styleguides" not in result
    assert "## Workflow" in result
    assert "Do the work." in result


def test_process_file_idempotent():
    """Applying _process_file twice yields the same result."""
    content = _old_md_content("review")
    first, changed1 = _process_file(content, "review", is_toml=False)
    assert changed1 is True
    second, changed2 = _process_file(first, "review", is_toml=False)
    assert changed2 is False
    assert first == second
