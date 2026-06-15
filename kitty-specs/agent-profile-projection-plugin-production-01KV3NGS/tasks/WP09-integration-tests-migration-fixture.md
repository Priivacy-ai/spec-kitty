---
work_package_id: WP09
title: Integration Tests, Migration Acceptance Fixture, and CI Gate
dependencies:
- WP01
- WP02
- WP03
- WP07
- WP08
requirement_refs:
- FR-040
- FR-041
- FR-042
tracker_refs: []
planning_base_branch: feat/agent-profile-projection-plugin-production
merge_target_branch: feat/agent-profile-projection-plugin-production
branch_strategy: Planning artifacts for this mission were generated on feat/agent-profile-projection-plugin-production. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-profile-projection-plugin-production unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
agent: "claude:sonnet:reviewer:reviewer"
shell_pid: "28191"
history:
- at: '2026-06-14T00:00:00Z'
  event: created
  actor: claude
agent_profile: engineer
authoritative_surface: tests/specify_cli/
create_intent:
- tests/specify_cli/tool_surface/test_surface_repair_wiring.py
- tests/specify_cli/tool_surface/test_drift_policy.py
- tests/specify_cli/integration/test_rc44_migration_fixture.py
- tests/specify_cli/test_migration_compat.py
execution_mode: code_change
owned_files:
- tests/specify_cli/tool_surface/test_surface_repair_wiring.py
- tests/specify_cli/tool_surface/test_drift_policy.py
- tests/specify_cli/integration/test_rc44_migration_fixture.py
- tests/specify_cli/test_migration_compat.py
role: Senior Python Engineer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading any other section of this prompt, load your agent profile:

```
/ad-hoc-profile-load engineer
```

---

## Objective

Write integration tests for init/upgrade surface wiring and drift policy; implement the rc44-era migration acceptance fixture (a real project-state simulation that exercises the full upgrade path from rc36/rc43 to current); update the doctor JSON stability contract; run the full suite at ≥90% coverage on all new code to satisfy the definition of done for the entire mission.

This is the final WP and is the certification gate (FR-040-042). It must pass before the mission can merge.

---

## Context

Success Criterion 6 (Version A): all new and changed code passes `mypy --strict` (on changed modules), `ruff check`, and the full pytest suite with ≥90% coverage on new paths. This WP is where that criterion is verified and enforced.

The rc44-era migration acceptance fixture simulates a project in the state that existed just before this mission's changes were applied:
- `claude` and `codex` in `config.yaml`
- 11-entry `command-skills-manifest.json` (not the canonical count)
- No `.claude/agents/` directory
- No `.codex/agents/` directory
- No unsafe symlinks cleaned yet

After `spec-kitty upgrade --yes` is run on this fixture, ALL of the following must hold:
- `.claude/agents/` exists and contains profile files
- `.codex/agents/` exists and contains TOML profile files
- `command-skills-manifest.json` has canonical entry count (not 11)
- `doctor tool-surfaces --kind agent-profile --json` shows zero `missing` / `stale` / `drifted` for claude and codex
- `doctor tool-surfaces --kind command-skill --json` shows zero `missing` / `stale` / `drifted`

---

## Subtask Guidance

### T040 — Integration tests for `init`/`upgrade` surface wiring

```python
# tests/specify_cli/tool_surface/test_surface_repair_wiring.py

def test_init_creates_missing_profile_dirs(tmp_path):
    """spec-kitty init creates missing agent profile dirs via the CLI (not direct function call)."""
    import subprocess, sys, json as _json
    # Setup: tmp project with config.yaml for claude only
    # Config shape must use agents.available, not flat agents list
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n"
    )
    # Ensure .claude/agents/ does not exist
    assert not (tmp_path / ".claude" / "agents").exists()
    # Run via CLI — NOT direct function call. This tests actual init/upgrade wiring (FR-001).
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "init", "--ai", "claude", "--yes"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    assert result.returncode == 0, f"init --yes failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    assert (tmp_path / ".claude" / "agents").exists(), ".claude/agents/ must be created by init"
    # Verify doctor is clean
    dr = subprocess.run(
        [sys.executable, "-m", "specify_cli", "doctor", "tool-surfaces", "--kind", "agent-profile", "--json"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    assert dr.returncode == 0, f"doctor exited non-zero: {dr.stderr}"

def test_upgrade_repairs_stale_manifest(tmp_path):
    """spec-kitty upgrade auto-repairs stale 11-entry manifests."""
    ...

def test_upgrade_with_yes_does_not_overwrite_drifted(tmp_path):
    """--yes flag must NOT overwrite drifted files (Rule 4: report-only in non-interactive)."""
    import subprocess, sys
    # Setup: first run init to create the managed profile
    (tmp_path / ".kittify").mkdir()
    (tmp_path / ".kittify" / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n"
    )
    subprocess.run(
        [sys.executable, "-m", "specify_cli", "init", "--ai", "claude", "--yes"],
        capture_output=True, text=True, cwd=tmp_path, check=True,
    )
    # Drift: overwrite the managed profile with custom content
    agents_dir = tmp_path / ".claude" / "agents"
    custom_content = "# Hand-modified agent\n\nCustom content.\n"
    for md in agents_dir.glob("*.md"):
        md.write_text(custom_content)
        drifted_path = md
        break
    else:
        pytest.skip("No managed profile files found after init")
    # Run upgrade --yes (non-interactive; must NOT overwrite drifted files)
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "upgrade", "--yes"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    # upgrade --yes must exit non-zero when drift is detected (FR-006)
    assert result.returncode != 0, "--yes must exit non-zero on unresolved drift"
    # The file must remain unchanged (not overwritten)
    assert drifted_path.read_text() == custom_content, "Drifted file must not be overwritten by --yes"

def test_upgrade_with_repair_drift_overwrites_drifted(tmp_path):
    """--repair-drift=overwrite overwrites drifted files (Rule 5)."""
    ...

def test_second_upgrade_is_idempotent(tmp_path):
    """Running upgrade twice produces zero counts on the second run."""
    import subprocess, sys

    _setup_project_for_rule(tmp_path, "rule1_missing_created")
    first = subprocess.run(
        [sys.executable, "-m", "specify_cli", "upgrade", "--yes"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    assert first.returncode == 0, first.stderr

    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    second = subprocess.run(
        [sys.executable, "-m", "specify_cli", "upgrade", "--yes"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    assert second.returncode == 0, second.stderr
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before
```

Write concrete implementations for all stubs above. Each test must be independently executable without shared state.

### T041 — rc44-era migration acceptance fixture

```python
# tests/specify_cli/integration/test_rc44_migration_fixture.py
import json
import pytest
from pathlib import Path

# Simulate a stale rc36/rc43 manifest in the CURRENT SkillsManifest schema
# (schema_version: 1, entries: [{path, content_hash, installed_at, agents}])
# with only 11 entries — rc36/rc43 projects had fewer commands than the canonical set.
_STALE_COMMANDS = [
    "spec-kitty.specify", "spec-kitty.plan", "spec-kitty.tasks",
    "spec-kitty.implement", "spec-kitty.review", "spec-kitty.accept",
    "spec-kitty.merge", "spec-kitty.next", "spec-kitty.advise",
    "spec-kitty.status", "spec-kitty.help",
]

def _make_stale_entry(cmd: str) -> dict:
    return {
        "path": f".agents/skills/{cmd}/SKILL.md",
        "content_hash": "aabbcc0011223344" * 4,  # placeholder hash
        "installed_at": "2024-01-01T00:00:00+00:00",
        "agents": ["codex"],
    }

RC44_MANIFEST_11_ENTRIES = {
    "schema_version": 1,
    "entries": [_make_stale_entry(cmd) for cmd in _STALE_COMMANDS],
}

@pytest.fixture
def rc44_project(tmp_path):
    """Simulate a project in rc44 state: claude+codex, 11-entry manifest, no agent profile dirs."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n    - codex\n"
    )
    skills_dir = tmp_path / ".agents" / "skills"
    skills_dir.mkdir(parents=True)
    manifest_path = tmp_path / ".kittify" / "command-skills-manifest.json"
    manifest_path.write_text(json.dumps(RC44_MANIFEST_11_ENTRIES, indent=2))
    # No .claude/agents/ or .codex/agents/ — they haven't been created yet
    return tmp_path

def test_upgrade_heals_rc44_project(rc44_project):
    """Full upgrade path from rc44 state heals all surfaces via actual spec-kitty upgrade CLI."""
    import subprocess, sys, json as _json

    # Invoke the real CLI — NOT repair_stale_manifest() or run_surface_repair() directly.
    # Calling functions directly bypasses init/upgrade wiring and would pass even if
    # the commands are never connected to the repair service (FR-001, FR-002).
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "upgrade", "--yes"],
        capture_output=True, text=True, cwd=rc44_project,
    )
    assert result.returncode == 0, (
        f"upgrade --yes failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )

    # Assert profile dirs created for configured agents
    claude_agents = rc44_project / ".claude" / "agents"
    codex_agents = rc44_project / ".codex" / "agents"
    assert claude_agents.exists(), ".claude/agents/ must be created by upgrade"
    assert codex_agents.exists(), ".codex/agents/ must be created by upgrade"

    # Assert profile files are present and non-empty
    claude_mds = list(claude_agents.glob("*.md"))
    assert claude_mds, ".claude/agents/ must contain at least one .md profile file"
    # Check that each .md file has YAML frontmatter (starts with ---)
    for md in claude_mds:
        content = md.read_text(encoding="utf-8")
        assert content.startswith("---"), f"{md.name} must have YAML frontmatter"

    codex_tomls = list(codex_agents.glob("*.toml"))
    assert codex_tomls, ".codex/agents/ must contain at least one .toml profile file"

    # Assert manifest repaired to canonical count (entries list, not commands list)
    canonical_commands = _get_canonical_commands()
    manifest = json.loads((rc44_project / ".kittify" / "command-skills-manifest.json").read_text())
    assert "entries" in manifest, "Repaired manifest must use 'entries' key (schema_version: 1)"
    assert manifest.get("schema_version") == 1
    assert len(manifest["entries"]) == len(canonical_commands), (
        f"Manifest has {len(manifest['entries'])} entries, expected {len(canonical_commands)}"
    )

def _get_canonical_commands():
    # CANONICAL_COMMANDS is defined in command_installer, not command_renderer
    from specify_cli.skills.command_installer import CANONICAL_COMMANDS
    return CANONICAL_COMMANDS
```

### T042 — Drift policy parametric test covering Rules 1-5

```python
# tests/specify_cli/tool_surface/test_drift_policy.py
import pytest
from pathlib import Path

@pytest.mark.parametrize("rule,interactive,repair_drift,expect_overwrite,expect_report", [
    ("rule1_missing_created",         False, False, True,  False),  # Rule 1: auto-create
    ("rule2_stale_repaired",          False, False, True,  False),  # Rule 2: auto-repair
    ("rule3_drifted_interactive_yes", True,  False, True,  False),  # Rule 3: interactive, user says y
    ("rule4_drifted_noninteractive",  False, False, False, True),   # Rule 4: non-interactive report-only
    ("rule5_drifted_overwrite_flag",  False, True,  True,  False),  # Rule 5: --repair-drift=overwrite
])
def test_drift_policy_rule(rule, interactive, repair_drift, expect_overwrite, expect_report, tmp_path, monkeypatch):
    """Verify each of the 6 drift policy rules."""
    import subprocess, sys
    from specify_cli.tool_surface.repair import run_surface_repair

    # Setup: project state appropriate for the rule being tested
    _setup_project_for_rule(tmp_path, rule)

    if rule == "rule3_drifted_interactive_yes":
        # Mock stdin to answer 'y' when prompted
        monkeypatch.setattr("sys.stdin", _MockStdin("y\n"))

    summary = run_surface_repair(tmp_path, interactive=interactive, repair_drift=repair_drift)

    if expect_overwrite:
        assert len(summary.drifted_overwritten) > 0 or len(summary.created) > 0 or len(summary.repaired) > 0
    if expect_report:
        assert len(summary.drifted_reported) > 0

    # Assert that `spec-kitty doctor tool-surfaces --json` exits 0 after repair
    result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "doctor", "tool-surfaces", "--json"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    assert result.returncode == 0, (
        f"doctor exited {result.returncode} after rule {rule!r}: {result.stderr}"
    )

def _setup_project_for_rule(tmp_path: Path, rule: str) -> None:
    """Set up appropriate project state for each rule."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text("agents:\n  available:\n    - claude\n")
    if "missing" in rule:
        pass  # no .claude/agents/ — is missing
    elif "stale" in rule:
        # Create .claude/agents/ with an outdated file
        agents = tmp_path / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "analyst-core.md").write_text("# Old version\n<!-- stale -->\n")
    elif "drifted" in rule:
        # Create .claude/agents/ with a user-modified file
        agents = tmp_path / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "analyst-core.md").write_text("# Hand-modified by user\n\nCustom content.\n")
```

This test is the most critical in the suite — it is the machine-readable specification of the drift policy. If a rule fails here, it is a blocking regression.

### T043 — Update doctor JSON stability contract

In `tests/specify_cli/test_migration_compat.py`, find the baseline `expected_surface_kinds` list (or similar) and add `"agent_profile"`:

```python
# Expected surface kinds in doctor --kind output (additive-only contract)
EXPECTED_SURFACE_KINDS = frozenset({
    "command_skill",
    "command_file",
    "doctrine_skill",
    "context_file",
    "hook",
    "rule",
    "native_config",
    "plugin_manifest",
    "agent_profile",  # added in this mission
})

def test_doctor_surface_kinds_are_additive(tmp_path):
    """doctor tool-surfaces --json must include all expected surface kinds."""
    import subprocess, json
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "agents:\n  available:\n    - claude\n    - codex\n    - vibe\n"
    )
    result = subprocess.run(
        ["spec-kitty", "doctor", "tool-surfaces", "--json"],
        capture_output=True, text=True, cwd=tmp_path,
    )
    data = json.loads(result.stdout)
    actual_kinds = {surface["kind"] for surface in data.get("surfaces", [])}
    missing = EXPECTED_SURFACE_KINDS - actual_kinds
    assert not missing, f"doctor output missing expected surface kinds: {missing}"
```

The contract is **additive-only** — new surface kinds are welcome; existing ones must not disappear.

### T044 — Full test suite gate: `mypy --strict`, `ruff check`, pytest ≥90%

Run in order:

```bash
# 1. Terminology guard (doctrine changes)
.venv/bin/pytest tests/architectural/test_no_legacy_terminology.py -v

# 2. Ruff check on all changed modules
.venv/bin/ruff check \
  src/specify_cli/tool_surface/ \
  src/specify_cli/cli/commands/plugin.py \
  src/specify_cli/cli/commands/init.py \
  src/specify_cli/upgrade/ \
  src/specify_cli/skills/ \
  src/specify_cli/core/config.py

# 3. mypy --strict on changed modules
.venv/bin/mypy --strict \
  src/specify_cli/tool_surface/ \
  src/specify_cli/cli/commands/plugin.py \
  src/specify_cli/upgrade/migrations/m_0_9_3_surface_repair_wiring.py \
  src/specify_cli/upgrade/migrations/m_0_9_4_roo_deprecation.py \
  src/specify_cli/skills/manifest_store.py \
  src/specify_cli/core/config.py

# 4. Full test suite with coverage
.venv/bin/pytest tests/ \
  --cov=specify_cli.tool_surface \
  --cov=specify_cli.skills \
  --cov-report=term-missing \
  --cov-branch \
  -x  # stop on first failure

# 5. Coverage assertion: new paths must be ≥90%
# Check the --cov-report output for the new modules:
# - specify_cli/tool_surface/profiles/codex_renderer.py
# - specify_cli/tool_surface/profiles/amazon_q_renderer.py
# - specify_cli/tool_surface/profiles/augment_renderer.py
# - specify_cli/tool_surface/profiles/capability_matrix.py
# - specify_cli/tool_surface/repair.py (updated)
# - specify_cli/tool_surface/bundles/claude.py
# - specify_cli/tool_surface/bundles/codex.py
```

If any of these fail, fix the issue before claiming this WP done. Do NOT add `# noqa` or `# type: ignore` to silence checks. Fix the underlying code instead.

For mypy strictness issues in new modules, common fixes:
- Add `from __future__ import annotations` at top
- Use `Optional[X]` or `X | None` instead of bare `None` defaults
- Add `-> None` return type to all methods
- Use `list[str]` not `List[str]` (Python 3.11+ preferred)

---

## Branch Strategy

- **Planning base branch**: `feat/agent-profile-projection-plugin-production`
- **Final merge target**: `feat/agent-profile-projection-plugin-production`
- **Depends on**: ALL prior WPs (WP01-WP08) must be merged first

To start work: `spec-kitty agent action implement WP09 --agent claude`

---

## Definition of Done

- [ ] `test_surface_repair_wiring.py`: missing→created, stale→repaired, drifted+`--yes`→report-only, drifted+`--repair-drift=overwrite`→overwritten, second-run→zero counts
- [ ] `test_rc44_migration_fixture.py`: full upgrade from rc44 state heals all surfaces and repairs manifest
- [ ] `test_drift_policy.py`: parametric test covering Rules 1-5 all pass
- [ ] `test_migration_compat.py`: `"agent_profile"` added to baseline; doctor JSON contract passes
- [ ] `mypy --strict` passes on all changed modules (zero errors)
- [ ] `ruff check` passes on all changed modules (zero issues)
- [ ] `pytest tests/` passes with ≥90% branch coverage on new code paths
- [ ] Terminology guard passes

---

## Risks

- Integration tests using `tmp_path` may be slow if they invoke real CLI subprocesses — prefer calling Python functions directly where possible; use subprocess only when testing CLI output format
- `spec-kitty upgrade` in tests requires a real or test-double migration framework — check if there is an existing test harness in `tests/specify_cli/` for triggering upgrade runs
- `mypy --strict` on `tool_surface/` may surface pre-existing type issues not introduced by this mission — note and file issues for pre-existing errors; fix only this mission's new code
- Coverage thresholds are measured on "new paths" not overall coverage — identify the new modules and check their individual coverage reports

## Activity Log

- 2026-06-15T04:50:26Z – claude:sonnet:reviewer:reviewer – shell_pid=28191 – Started review via action command
