---
work_package_id: WP04
title: Post-Init Verification
lane: "doing"
dependencies: [WP02, WP03]
base_branch: 042-agent-skills-installer-infrastructure-WP03
base_commit: fffc6ec2d5dbd24eb746058f5087717457777579
created_at: '2026-03-20T17:29:03.114733+00:00'
subtasks:
- T018
- T019
- T020
phase: Phase 2 - Core Logic
assignee: ''
agent: ''
shell_pid: "13034"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-20T16:29:09Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-014
- FR-015
---

# Work Package Prompt: WP04 – Post-Init Verification

## ⚠️ IMPORTANT: Review Feedback Status

- **Has review feedback?**: Check the `review_status` field above.

---

## Review Feedback

*[This section is empty initially.]*

---

## Implementation Command

```bash
spec-kitty implement WP04 --base WP03
```

Depends on WP02 (skill root resolution) and WP03 (manifest).

---

## Objectives & Success Criteria

1. `verify_installation()` catches all four failure types: missing skill root, missing wrapper root, wrapper count mismatch, duplicate skill names.
2. Returns structured `VerificationResult` with actionable error messages naming the specific agent and resource.
3. Passes cleanly when installation is correct.
4. Passes `mypy --strict` and `ruff check`.

## Context & Constraints

- **Spec**: FR-014, FR-015
- **Plan**: Section 5 (Post-Init Verification)
- **Data model**: VerificationResult, SkillsManifest
- **Depends on**: `resolve_skill_roots()` from WP02, `SkillsManifest` from WP03

## Subtasks & Detailed Guidance

### Subtask T018 – VerificationResult dataclass and verify_installation signature

**Purpose**: Define the return type and function contract.

**Steps**:
1. Create `src/specify_cli/skills/verification.py`
2. Define:
   ```python
   from __future__ import annotations
   from dataclasses import dataclass, field
   from pathlib import Path

   from specify_cli.skills.manifest import SkillsManifest

   @dataclass
   class VerificationResult:
       passed: bool = True
       errors: list[str] = field(default_factory=list)
       warnings: list[str] = field(default_factory=list)

   def verify_installation(
       project_root: Path,
       selected_agents: list[str],
       manifest: SkillsManifest,
   ) -> VerificationResult:
       """Verify that the installed state matches expectations."""
   ```

**Files**: `src/specify_cli/skills/verification.py` (new, ~100 lines)

### Subtask T019 – Implement verification checks

**Purpose**: Four checks that together ensure installation integrity.

**Steps**:
1. **Check 1 — Agent coverage**: Every selected agent has either:
   - A skill root listed in `manifest.installed_skill_roots` that matches its distribution class, OR
   - Managed wrapper files in `manifest.managed_files`
   - Error format: `"Agent '{agent_key}' has no managed skill root or wrapper root"`

2. **Check 2 — Skill root existence**: Every directory in `manifest.installed_skill_roots` exists on disk.
   - Error format: `"Skill root '{root}' listed in manifest but does not exist on disk"`

3. **Check 3 — Wrapper count**: For each agent, count wrapper files of type `"wrapper"` in `manifest.managed_files`. Warn if count is zero (agent selected but no wrappers generated — unusual but possible with `wrappers-only` mode off and no mission).
   - Warning format: `"Agent '{agent_key}' has 0 managed wrapper files"`

4. **Check 4 — No duplicate skill names in overlapping roots**: For Phase 0, skill roots are empty so this check always passes. Implement the structure anyway — iterate installed roots, check for files with same name in roots that the same agent scans. If found, error.
   - Error format: `"Duplicate skill '{name}' in roots scanned by agent '{agent_key}': {root1}, {root2}"`

5. Set `result.passed = len(result.errors) == 0`.

**Files**: `src/specify_cli/skills/verification.py`

### Subtask T020 – Unit tests

**Purpose**: Verify pass case and each distinct failure mode.

**Steps**:
1. Create `tests/specify_cli/test_skills/test_verification.py`
2. Tests:

```python
# Pass case: all checks pass
def test_verification_passes(tmp_path):
    # Create skill roots
    (tmp_path / ".agents" / "skills").mkdir(parents=True)
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0", created_at="", updated_at="",
        skills_mode="auto", selected_agents=["claude", "codex"],
        installed_skill_roots=[".agents/skills/", ".claude/skills/"],
        managed_files=[
            ManagedFile(path=".codex/prompts/spec-kitty.specify.md", sha256="x", file_type="wrapper"),
            ManagedFile(path=".claude/commands/spec-kitty.specify.md", sha256="x", file_type="wrapper"),
        ],
    )
    result = verify_installation(tmp_path, ["claude", "codex"], manifest)
    assert result.passed
    assert result.errors == []

# Fail: missing skill root
def test_missing_skill_root(tmp_path):
    # Don't create .claude/skills/
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0", created_at="", updated_at="",
        skills_mode="auto", selected_agents=["claude"],
        installed_skill_roots=[".claude/skills/"],
        managed_files=[ManagedFile(path=".claude/commands/x.md", sha256="x", file_type="wrapper")],
    )
    result = verify_installation(tmp_path, ["claude"], manifest)
    assert not result.passed
    assert any(".claude/skills/" in e for e in result.errors)

# Fail: agent with no roots or wrappers
def test_agent_no_coverage(tmp_path):
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0", created_at="", updated_at="",
        skills_mode="auto", selected_agents=["claude", "codex"],
        installed_skill_roots=[".claude/skills/"],
        managed_files=[
            ManagedFile(path=".claude/commands/x.md", sha256="x", file_type="wrapper"),
            # No codex wrappers and no .agents/skills/
        ],
    )
    (tmp_path / ".claude" / "skills").mkdir(parents=True)
    result = verify_installation(tmp_path, ["claude", "codex"], manifest)
    assert not result.passed
    assert any("codex" in e for e in result.errors)

# Wrapper-only agent passes without skill root
def test_wrapper_only_agent_no_skill_root(tmp_path):
    manifest = SkillsManifest(
        spec_kitty_version="2.1.0", created_at="", updated_at="",
        skills_mode="auto", selected_agents=["q"],
        installed_skill_roots=[],
        managed_files=[ManagedFile(path=".amazonq/prompts/x.md", sha256="x", file_type="wrapper")],
    )
    result = verify_installation(tmp_path, ["q"], manifest)
    assert result.passed
```

**Files**: `tests/specify_cli/test_skills/test_verification.py` (new, ~80 lines)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Check 4 always passes in Phase 0 (empty roots) | Implement the structure now but mark as "will become active when skill packs are installed" |
| Check 1 logic for wrapper-only agents | Test explicitly that wrapper-only agents pass with wrappers and no skill roots |

## Review Guidance

1. Verify error messages name the specific agent and missing resource.
2. Verify `passed` is `False` when any error exists, `True` when only warnings.
3. Verify wrapper-only agents are not expected to have skill roots.

## Activity Log

- 2026-03-20T16:29:09Z – system – lane=planned – Prompt created.
