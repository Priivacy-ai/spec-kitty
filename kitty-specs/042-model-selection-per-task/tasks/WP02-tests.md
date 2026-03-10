---
work_package_id: WP02
title: Tests
lane: "done"
dependencies: [WP01]
base_branch: 042-model-selection-per-task-WP01
base_commit: e1eb8bb8122403f0c764b9c202b183bf5306a441
created_at: '2026-03-09T11:47:46.904328+00:00'
subtasks:
- T005
- T006
phase: Phase 2 - Validation
assignee: ''
agent: "claude-sonnet-4-6"
shell_pid: "41689"
review_status: "approved"
reviewed_by: "Zohar Stolar"
history:
- timestamp: '2026-03-09T11:13:06Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
---

# Work Package Prompt: WP02 – Tests

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check `review_status` above. If `has_feedback`, read the Review Feedback section first.
- **Mark as acknowledged**: Set `review_status: acknowledged` when you start addressing feedback.

---

## Review Feedback

*[Empty — reviewers will populate if work is returned.]*

---

## Objectives & Success Criteria

Write full test coverage for `global_config.py` and the `m_2_0_4_model_injection.py` migration.

**Done when**:
- `pytest tests/specify_cli/test_model_injection_migration.py -v` passes with all tests green
- Unit tests cover all `global_config.py` branches
- Integration tests prove the migration injects, updates, and removes `model:` correctly across multiple agents
- Idempotency is verified

## Context & Constraints

- **Implement command** (depends on WP01): `spec-kitty implement WP02 --base WP01`
- **Test file**: `tests/specify_cli/test_model_injection_migration.py`
- Use `tmp_path` and `monkeypatch` pytest fixtures — no filesystem side effects
- Monkeypatch `Path.home` in the `global_config` module, not globally
- Run tests from repo root: `cd src && pytest tests/specify_cli/test_model_injection_migration.py -v`

## Subtasks & Detailed Guidance

### Subtask T005 – Unit tests for `global_config.py`

**Purpose**: Verify every branch of `load_model_mapping()` and `get_unknown_commands()` in isolation.

**Steps**:

1. Create the test file `tests/specify_cli/test_model_injection_migration.py` and add a `TestGlobalConfig` class.

2. Write the following test cases:

```python
import pytest
from pathlib import Path
from specify_cli.global_config import (
    GlobalConfigError,
    KNOWN_COMMANDS,
    get_unknown_commands,
    load_model_mapping,
)


class TestGlobalConfig:

    def test_missing_config_returns_empty(self, tmp_path):
        """No config file → empty dict, no error."""
        result = load_model_mapping(home=tmp_path)
        assert result == {}

    def test_valid_mapping_returned(self, tmp_path):
        """Config with models: → correct dict returned."""
        config = tmp_path / ".spec-kitty" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("models:\n  specify: claude-opus-4-6\n  implement: claude-sonnet-4-6\n")

        result = load_model_mapping(home=tmp_path)
        assert result == {"specify": "claude-opus-4-6", "implement": "claude-sonnet-4-6"}

    def test_config_without_models_key(self, tmp_path):
        """Config file exists but has no models: key → empty dict."""
        config = tmp_path / ".spec-kitty" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("other_key: value\n")

        result = load_model_mapping(home=tmp_path)
        assert result == {}

    def test_empty_config_file(self, tmp_path):
        """Empty config file → empty dict."""
        config = tmp_path / ".spec-kitty" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("")

        result = load_model_mapping(home=tmp_path)
        assert result == {}

    def test_malformed_yaml_raises(self, tmp_path):
        """Malformed YAML → GlobalConfigError with file path in message."""
        config = tmp_path / ".spec-kitty" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("models:\n  bad: [unclosed\n")

        with pytest.raises(GlobalConfigError, match=str(tmp_path)):
            load_model_mapping(home=tmp_path)

    def test_models_not_a_dict_raises(self, tmp_path):
        """models: is a list instead of dict → GlobalConfigError."""
        config = tmp_path / ".spec-kitty" / "config.yaml"
        config.parent.mkdir(parents=True)
        config.write_text("models:\n  - item1\n  - item2\n")

        with pytest.raises(GlobalConfigError):
            load_model_mapping(home=tmp_path)

    def test_get_unknown_commands_empty(self):
        """All known commands → no unknowns."""
        mapping = {cmd: "model-x" for cmd in KNOWN_COMMANDS}
        assert get_unknown_commands(mapping) == []

    def test_get_unknown_commands_detects_typo(self):
        """Typo in command name → returned in unknowns list."""
        mapping = {"spceify": "model-x", "specify": "model-y"}
        unknowns = get_unknown_commands(mapping)
        assert "spceify" in unknowns
        assert "specify" not in unknowns
```

**Files**:
- `tests/specify_cli/test_model_injection_migration.py` (new)

---

### Subtask T006 – Integration tests for the migration

**Purpose**: Verify the migration correctly injects, updates, and removes `model:` across realistic agent directory structures.

**Steps**:

1. Add a `TestModelInjectionMigration` class to the same test file.

2. Create a helper fixture that sets up a minimal fake project with agent command directories:

```python
import pytest
from pathlib import Path
from unittest.mock import patch
from specify_cli.upgrade.migrations.m_2_0_4_model_injection import ModelInjectionMigration


def _write_command_file(path: Path, content: str = "") -> None:
    """Write a minimal command file with optional frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_project(tmp_path: Path, agents: list[tuple[str, str]]) -> Path:
    """Create a minimal fake project with agent directories."""
    for agent_root, subdir in agents:
        (tmp_path / agent_root / subdir).mkdir(parents=True, exist_ok=True)
    return tmp_path


class TestModelInjectionMigration:

    @pytest.fixture
    def migration(self):
        return ModelInjectionMigration()

    @pytest.fixture
    def project(self, tmp_path):
        """Fake project with Claude Code and Codex directories."""
        agents = [(".claude", "commands"), (".codex", "prompts")]
        return _make_project(tmp_path, agents)

    def test_no_config_is_noop(self, migration, project, tmp_path):
        """No ~/.spec-kitty/config.yaml → no changes made."""
        # Write a command file without model:
        cmd = project / ".claude" / "commands" / "spec-kitty.specify.md"
        cmd.write_text("---\ndescription: Specify\n---\n\nContent\n")

        with patch("specify_cli.global_config.Path.home", return_value=tmp_path / "home"):
            result = migration.apply(project)

        assert result.success
        assert result.changes_made == []
        assert "model:" not in cmd.read_text()

    def test_model_injected_into_matching_command(self, migration, project, tmp_path):
        """Model mapping → model: injected into matching command file."""
        config_dir = tmp_path / "home" / ".spec-kitty"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("models:\n  specify: claude-opus-4-6\n")

        cmd = project / ".claude" / "commands" / "spec-kitty.specify.md"
        cmd.write_text("---\ndescription: Specify\n---\n\nContent\n")

        with patch("specify_cli.global_config.Path.home", return_value=tmp_path / "home"):
            result = migration.apply(project)

        assert result.success
        assert any("specify" in c for c in result.changes_made)
        assert "model: claude-opus-4-6" in cmd.read_text()

    def test_unmapped_command_untouched(self, migration, project, tmp_path):
        """Command not in config → file unchanged (no model: added)."""
        config_dir = tmp_path / "home" / ".spec-kitty"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("models:\n  specify: claude-opus-4-6\n")

        plan_cmd = project / ".claude" / "commands" / "spec-kitty.plan.md"
        plan_cmd.write_text("---\ndescription: Plan\n---\n\nContent\n")

        with patch("specify_cli.global_config.Path.home", return_value=tmp_path / "home"):
            migration.apply(project)

        assert "model:" not in plan_cmd.read_text()

    def test_stale_model_removed_when_command_absent(self, migration, project, tmp_path):
        """Command removed from config → model: removed from frontmatter."""
        config_dir = tmp_path / "home" / ".spec-kitty"
        config_dir.mkdir(parents=True)
        # Config no longer has 'plan' mapped
        (config_dir / "config.yaml").write_text("models:\n  specify: claude-opus-4-6\n")

        plan_cmd = project / ".claude" / "commands" / "spec-kitty.plan.md"
        plan_cmd.write_text("---\ndescription: Plan\nmodel: claude-opus-4-6\n---\n\nContent\n")

        with patch("specify_cli.global_config.Path.home", return_value=tmp_path / "home"):
            result = migration.apply(project)

        assert result.success
        assert "model:" not in plan_cmd.read_text()

    def test_model_updated_when_value_changes(self, migration, project, tmp_path):
        """Config changed to new model → frontmatter updated correctly."""
        config_dir = tmp_path / "home" / ".spec-kitty"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("models:\n  specify: claude-sonnet-4-6\n")

        cmd = project / ".claude" / "commands" / "spec-kitty.specify.md"
        cmd.write_text("---\ndescription: Specify\nmodel: claude-opus-4-6\n---\n\nContent\n")

        with patch("specify_cli.global_config.Path.home", return_value=tmp_path / "home"):
            migration.apply(project)

        assert "model: claude-sonnet-4-6" in cmd.read_text()
        assert "claude-opus-4-6" not in cmd.read_text()

    def test_idempotent_when_model_already_correct(self, migration, project, tmp_path):
        """Running migration twice with same config → no changes on second run."""
        config_dir = tmp_path / "home" / ".spec-kitty"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("models:\n  specify: claude-opus-4-6\n")

        cmd = project / ".claude" / "commands" / "spec-kitty.specify.md"
        cmd.write_text("---\ndescription: Specify\nmodel: claude-opus-4-6\n---\n\nContent\n")

        with patch("specify_cli.global_config.Path.home", return_value=tmp_path / "home"):
            result1 = migration.apply(project)
            result2 = migration.apply(project)

        assert result2.changes_made == []

    def test_unknown_command_produces_warning(self, migration, project, tmp_path):
        """Unknown command key in config → warning in result, no error."""
        config_dir = tmp_path / "home" / ".spec-kitty"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("models:\n  spceify: claude-opus-4-6\n")

        with patch("specify_cli.global_config.Path.home", return_value=tmp_path / "home"):
            result = migration.apply(project)

        assert result.success
        assert any("spceify" in w for w in result.warnings)

    @pytest.mark.parametrize("agent_root,subdir", [
        (".claude", "commands"),
        (".codex", "prompts"),
        (".opencode", "command"),
    ])
    def test_injection_applies_to_multiple_agents(self, tmp_path, agent_root, subdir):
        """Model injection works for each supported agent directory."""
        migration = ModelInjectionMigration()
        project = _make_project(tmp_path / "project", [(agent_root, subdir)])

        config_dir = tmp_path / "home" / ".spec-kitty"
        config_dir.mkdir(parents=True)
        (config_dir / "config.yaml").write_text("models:\n  implement: claude-sonnet-4-6\n")

        cmd = project / agent_root / subdir / "spec-kitty.implement.md"
        cmd.write_text("---\ndescription: Implement\n---\n\nContent\n")

        with patch("specify_cli.global_config.Path.home", return_value=tmp_path / "home"):
            result = migration.apply(project)

        assert result.success
        assert "model: claude-sonnet-4-6" in cmd.read_text()
```

**Files**:
- `tests/specify_cli/test_model_injection_migration.py` (continued from T005)

**Notes**:
- `monkeypatch` on `Path.home` must target the module where it's called from (`specify_cli.global_config`), not the global `Path`. Using `unittest.mock.patch` as shown is cleaner for this.
- If `get_agent_dirs_for_project` reads the project's `config.yaml` and finds no configured agents, it falls back to all agents — that's fine for tests since we create dirs manually.

---

## Risks & Mitigations

- **`Path.home()` patch scope**: If `global_config.py` stores `Path.home() / ...` at module level (as a constant), monkeypatching won't work. The implementation uses `Path.home()` lazily inside the function — verify this before writing tests.
- **`FrontmatterManager` writes real files**: Tests use `tmp_path`, so no real filesystem is touched. Verify frontmatter write produces valid YAML by re-reading and parsing in the test.

## Review Guidance

Reviewers should verify:
- [ ] All `TestGlobalConfig` tests pass
- [ ] All `TestModelInjectionMigration` tests pass
- [ ] Parametrized multi-agent test covers at least 3 agents
- [ ] Idempotency test confirms second run produces no changes
- [ ] No real filesystem reads/writes (all in `tmp_path`)

## Activity Log

- 2026-03-09T11:13:06Z – system – lane=planned – Prompt created.
- 2026-03-09T11:47:47Z – claude-sonnet-4-6 – shell_pid=41689 – lane=doing – Assigned agent via workflow command
- 2026-03-09T12:14:35Z – claude-sonnet-4-6 – shell_pid=41689 – lane=for_review – All 18 tests passing
- 2026-03-09T12:15:05Z – claude-sonnet-4-6 – shell_pid=41689 – lane=done – 18/18 tests passing. All cases covered: inject, update, remove, idempotency, no-config no-op, malformed config error, multi-agent parametrized.
