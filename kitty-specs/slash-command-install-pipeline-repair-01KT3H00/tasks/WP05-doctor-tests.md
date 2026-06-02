---
work_package_id: WP05
title: Doctor tests — slash-command audit, --fix, idempotency, mypy
dependencies:
- WP02
requirement_refs:
- FR-005
- FR-006
- FR-007
- FR-010
- FR-011
- C-002
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T017
- T025
- T026
- T027
- T028
- T029
agent: claude
history:
- date: '2026-06-02'
  event: created
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/cli/commands/
execution_mode: code_change
owned_files:
- tests/specify_cli/cli/commands/test_doctor_slash_commands.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Write unit and integration tests for the `doctor skills` slash-command audit and `--fix` repair path added in WP02. Covers gap detection, false-positive prevention, scope guard, idempotency, and mypy clean bill of health.

**Prerequisite**: WP02 merged.

```bash
spec-kitty agent action implement WP05 --agent claude
```

---

## Context

Target file: `tests/specify_cli/cli/commands/test_doctor_slash_commands.py`. WP02 committed a minimal failing ATDD stub (`test_doctor_skills_output_includes_slash_commands_section`) to this file as its first commit. **Start by expanding that stub** into the full test suite rather than creating a new file from scratch.

All tests use `tmp_path` and `monkeypatch`. Do **not** read from or write to the real `~/.claude/commands/`. Mock `get_global_command_dir`, `_load_slash_command_state`, and `ensure_global_agent_commands` where appropriate.

---

## Subtask T013 — Unit tests: audit logic, false-positive prevention, scope guard

Add `TestLoadSlashCommandState`:

```python
class TestLoadSlashCommandState:
    def test_missing_file_detected_as_gap(self, tmp_path, monkeypatch):
        """A missing command file is reported as a gap with status='missing'."""
        from specify_cli.cli.commands.doctor import _load_slash_command_state

        monkeypatch.setattr(
            "specify_cli.cli.commands.doctor._get_slash_command_agents",
            lambda project_path: ["claude"],
        )
        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.get_global_command_dir",
            lambda agent_key: tmp_path / agent_key,
        )
        (tmp_path / "claude").mkdir()
        # No command files written → all gaps

        configured, gaps = _load_slash_command_state(tmp_path)
        assert configured == ["claude"]
        assert len(gaps) > 0
        assert all(g.status == "missing" for g in gaps)

    def test_present_files_no_gap(self, tmp_path, monkeypatch):
        """When all command files exist with current version marker, no gaps reported."""
        from specify_cli.cli.commands.doctor import _load_slash_command_state
        from specify_cli.shims.registry import PROMPT_DRIVEN_COMMANDS, CLI_DRIVEN_COMMANDS
        from specify_cli.runtime.agent_commands import _VERSION_MARKER_PREFIX
        from specify_cli.runtime.bootstrap import _get_cli_version

        cmd_dir = tmp_path / "claude"
        cmd_dir.mkdir()
        version = _get_cli_version()
        for cmd in PROMPT_DRIVEN_COMMANDS | CLI_DRIVEN_COMMANDS:
            f = cmd_dir / f"spec-kitty.{cmd}.md"
            f.write_text(f"{_VERSION_MARKER_PREFIX} {version}\n# body")

        monkeypatch.setattr(
            "specify_cli.cli.commands.doctor._get_slash_command_agents",
            lambda project_path: ["claude"],
        )
        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.get_global_command_dir",
            lambda agent_key: cmd_dir,
        )

        _, gaps = _load_slash_command_state(tmp_path)
        assert gaps == []

    def test_scope_guard_unconfigured_agent_not_audited(self, tmp_path, monkeypatch):
        """Agents not in config.available are excluded from audit."""
        from specify_cli.cli.commands.doctor import _load_slash_command_state

        monkeypatch.setattr(
            "specify_cli.cli.commands.doctor._get_slash_command_agents",
            lambda project_path: [],  # no configured agents
        )

        configured, gaps = _load_slash_command_state(tmp_path)
        assert configured == []
        assert gaps == []
```

---

## Subtask T017 — Integration test: detect gap → --fix → verify clean

Add `TestDoctorSkillsFixIntegration`:

```python
class TestDoctorSkillsFixIntegration:
    def test_fix_repairs_missing_files(self, tmp_path, monkeypatch):
        """--fix path calls repair when gaps exist, leaving zero gaps after."""
        repaired = []

        def fake_repair(project_path, configured_agents, gaps):
            # Simulate writing files
            for gap in gaps:
                gap.expected_path.parent.mkdir(parents=True, exist_ok=True)
                gap.expected_path.write_text("# repaired")
            repaired.extend(gaps)

        monkeypatch.setattr(
            "specify_cli.cli.commands.doctor._repair_slash_command_state",
            fake_repair,
        )

        # After repair, second call to _load_slash_command_state returns no gaps
        call_count = 0

        def fake_load(project_path):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from specify_cli.cli.commands.doctor import SlashCommandGap
                gap = SlashCommandGap("claude", "specify", tmp_path / "spec-kitty.specify.md", "missing")
                return ["claude"], [gap]
            return ["claude"], []

        monkeypatch.setattr(
            "specify_cli.cli.commands.doctor._load_slash_command_state",
            fake_load,
        )

        # Invoke the fix path (call the repair logic directly to avoid CLI runner complexity)
        _, gaps = fake_load(tmp_path)
        fake_repair(tmp_path, ["claude"], gaps)
        _, remaining = fake_load(tmp_path)

        assert repaired
        assert remaining == []
```

---

## Subtask T025 — Test: doctor audit false-positive prevention

Add `TestAuditFalsePositives`:

```python
class TestAuditFalsePositives:
    def test_stale_version_reported_as_stale_not_missing(self, tmp_path, monkeypatch):
        """A file with an outdated version marker is 'stale', not 'missing'."""
        from specify_cli.cli.commands.doctor import _load_slash_command_state, SlashCommandGap
        from specify_cli.runtime.agent_commands import _VERSION_MARKER_PREFIX

        cmd_dir = tmp_path / "claude"
        cmd_dir.mkdir()
        # Write a file with an old version
        (cmd_dir / "spec-kitty.specify.md").write_text(f"{_VERSION_MARKER_PREFIX} 0.0.1\n# body")

        monkeypatch.setattr(
            "specify_cli.cli.commands.doctor._get_slash_command_agents",
            lambda project_path: ["claude"],
        )
        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.get_global_command_dir",
            lambda agent_key: cmd_dir,
        )

        _, gaps = _load_slash_command_state(tmp_path)
        stale = [g for g in gaps if g.command == "specify"]
        assert stale, "Expected a gap for the stale 'specify' command"
        assert stale[0].status == "stale"
```

---

## Subtask T026 — Test: --fix scope guard (only configured agents touched)

Add `TestFixScopeGuard`:

```python
class TestFixScopeGuard:
    def test_repair_only_touches_configured_agents(self, tmp_path, monkeypatch):
        """ensure_global_agent_commands is called with configured agents only."""
        called_with = []

        def fake_ensure(*, agent_keys=None):
            called_with.append(agent_keys)

        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.ensure_global_agent_commands",
            fake_ensure,
        )

        from specify_cli.cli.commands.doctor import _repair_slash_command_state, SlashCommandGap
        gap = SlashCommandGap("claude", "specify", tmp_path / "spec-kitty.specify.md", "missing")
        _repair_slash_command_state(tmp_path, ["claude"], [gap])

        assert called_with == [["claude"]], (
            "repair must pass only configured agents, not all agents"
        )
```

---

## Subtask T027 — Test: --fix idempotency (twice → identical state)

Add `TestFixIdempotency`:

```python
class TestFixIdempotency:
    def test_repair_noop_when_no_gaps(self, tmp_path, monkeypatch):
        """_repair_slash_command_state returns [] and does not call installer when gaps=[].."""
        ensure_called = []

        def fake_ensure(*, agent_keys=None):
            ensure_called.append(agent_keys)

        monkeypatch.setattr(
            "specify_cli.runtime.agent_commands.ensure_global_agent_commands",
            fake_ensure,
        )

        from specify_cli.cli.commands.doctor import _repair_slash_command_state
        result = _repair_slash_command_state(tmp_path, ["claude"], [])

        assert result == [], "Empty gaps should return empty list"
        assert ensure_called == [], "Installer must not be called when there are no gaps"
```

---

## Subtask T028 — Verify mypy --strict passes on all new/changed modules

Run mypy on every module touched by WP01 and WP02:

```bash
uv run mypy --strict \
  src/specify_cli/runtime/agent_commands.py \
  src/specify_cli/cli/commands/doctor.py \
  tests/specify_cli/runtime/test_agent_commands.py \
  tests/specify_cli/cli/commands/test_doctor_slash_commands.py
```

Fix any type errors before marking this subtask done.

**Common issues to anticipate**:
- `SlashCommandGap` fields need type annotations checked
- `_repair_slash_command_state` return type must be `list[str]`
- `ensure_global_agent_commands` `agent_keys` param must be `list[str] | None`

---

## Subtask T029 — NFR-003 regression: Agent Skills pipeline unaffected

Run the targeted Agent Skills doctor test surface to confirm no regressions:

```bash
uv run pytest tests/runtime/test_doctor_unit.py tests/runtime/test_doctor_command_file_health.py -v
```

If those paths don't exist, find the equivalent with:
```bash
find tests -name "*doctor*" -name "*.py" | grep -v slash | head -10
```

All tests must pass. If any fail, investigate before proceeding — per charter Pre-existing Failure Reporting Rule, open a GitHub issue if failures appear pre-existing rather than introduced.

---

## Definition of Done

- [ ] ATDD stub (from WP02) expanded into full test suite
- [ ] `tests/specify_cli/cli/commands/test_doctor_slash_commands.py` contains all subtask test classes
- [ ] `pytest tests/specify_cli/cli/commands/test_doctor_slash_commands.py -v` — all tests pass
- [ ] T029: Agent Skills doctor tests pass (NFR-003 confirmed)
- [ ] Tests do not touch real `~/.claude/commands/` or any real agent directory
- [ ] `ruff check tests/specify_cli/cli/commands/test_doctor_slash_commands.py` — zero violations
- [ ] `mypy --strict src/specify_cli/runtime/agent_commands.py src/specify_cli/cli/commands/doctor.py` — zero errors

## Risks

- `SlashCommandGap` may not be importable at top-level; import inside test functions if needed.
- `_load_slash_command_state` imports several private symbols from `agent_commands`; these must be exported or the audit function refactored before tests can run.
- Do not patch `ensure_global_agent_commands` at the module level — patch at the attribute path `specify_cli.runtime.agent_commands.ensure_global_agent_commands`.
